"""Extrai campos estruturados dos laudos de avaliação usando a API da Anthropic.

Uso:
    export ANTHROPIC_API_KEY="sk-..."
    python extrator.py --entrada ../dados_brutos/laudos_avaliacao --saida saida_extracao.json

Design:
    - A saída é forçada a obedecer um schema fixo via "tool use": em vez de
      pedir para o modelo "escrever JSON" em texto livre (frágil -- markdown,
      texto antes/depois, chaves faltando), declaramos uma tool cujo
      input_schema é gerado a partir do schema Pydantic (schema.py) e
      forçamos tool_choice para essa tool. O modelo é obrigado a preencher
      exatamente esses campos.
    - Toda saída do modelo passa por validação Pydantic antes de ser aceita.
      Se a validação falhar (ex: status="ausente" sem trecho_bruto), o erro
      é reenviado ao modelo como feedback e uma nova tentativa é feita --
      até MAX_TENTATIVAS. Isso é o "não confie cegamente na IA" aplicado ao
      próprio pipeline de IA.
    - Erros de rede/rate limit da API usam backoff exponencial simples.
    - Tudo é logado (logging, não print) para permitir auditoria de uma
      execução em produção (ex: rodando toda segunda-feira via cron).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import anthropic
from pydantic import ValidationError

from schema import CAMPOS_LAUDO, LaudoExtraido, json_schema_campos

logger = logging.getLogger("extrator_laudos")

MODEL = "claude-sonnet-4-5"
MAX_TENTATIVAS = 3
BACKOFF_BASE_SEGUNDOS = 2

TOOL_NAME = "registrar_extracao_laudo"

PROMPT_SISTEMA = """\
Você extrai campos estruturados de laudos de avaliação imobiliária em texto \
livre, cada um com um formato diferente (não existe template único).

Para CADA campo (tipo_imovel, endereco, area_privativa_m2, area_total_m2, \
ano_construcao, valor_avaliacao_reais, matricula, onus, data_vistoria, \
responsavel_tecnico), classifique o status como:
- "presente": o laudo informa o campo de forma clara e sem contradição.
- "ausente": o laudo não menciona o campo (ex: terreno sem ano de \
construção, ou "não se aplica"/"não há informação").
- "conflitante": o laudo menciona valores diferentes para o mesmo campo \
(ex: área total diverge entre o cabeçalho e o corpo do texto).

Regras obrigatórias:
1. Quando status for "ausente" ou "conflitante", o campo "trecho_bruto" é \
OBRIGATÓRIO e deve ser uma cópia literal do trecho do laudo que justifica \
essa classificação (não parafraseie).

2. Quando status for "presente", "valor" deve ser a informação normalizada: \
áreas e valores em R$ como número puro (ex: 1275000.00, 78.4), ano como \
inteiro de 4 dígitos (ex: 2014) e datas em formato ISO AAAA-MM-DD. Nada de \
texto, unidade ou prefixo junto do número.

3. NUNCA "chute" um valor plausível para um campo ausente ou conflitante. \
Um extrator que erra "sabendo que não sabe" é melhor que um que inventa. \
Se você não tem certeza, use "ausente" ou "conflitante" -- nunca invente.

4. Valores por extenso (ex: "seiscentos e oitenta mil reais") devem ser \
convertidos para número quando não houver ambiguidade.

5. Quando status for "ausente" ou "conflitante", deixe "valor" como null. \
Para campos numéricos e datas, qualquer valor enviado nesses casos é \
descartado; a evidência vai em "trecho_bruto".

6. Para os campos de área, diferencie a área da edificação da área do terreno:
   - "area_privativa_m2" representa a área privativa, construída, edificada, \
coberta ou de benfeitorias do imóvel, quando explicitamente informada.
   - "area_total_m2" representa a área total associada ao imóvel, especialmente \
a área do terreno ou lote.
   - Quando o laudo informar separadamente área construída, edificada, coberta \
ou de benfeitorias e área do terreno ou lote, use a área da edificação em \
"area_privativa_m2" e a área do terreno ou lote em "area_total_m2".
   - Não use a área construída, edificada, coberta ou de benfeitorias como \
"area_total_m2" quando uma área de terreno ou lote estiver explicitamente \
informada.

7. Todas as áreas devem ser retornadas em metros quadrados. Quando o laudo \
informar explicitamente uma área em outra unidade de superfície e a conversão \
for inequívoca, converta para m². Para hectares, use 1 ha = 10.000 m².
"""


def montar_tool_schema() -> dict:
    """Deriva o schema da tool Anthropic a partir do schema Pydantic.

    Mantemos uma única fonte de verdade (schema.py) para o formato de saída,
    em vez de duplicar a definição dos campos aqui.
    """
    properties = json_schema_campos()
    return {
        "name": TOOL_NAME,
        "description": "Registra a extração estruturada de um laudo de avaliação.",
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": CAMPOS_LAUDO,
        },
    }


def extrair_um_laudo(
    client: anthropic.Anthropic, texto_laudo: str, nome_arquivo: str
) -> LaudoExtraido:
    """Extrai os campos de um laudo, com retry em caso de saída inválida.

    Raises:
        RuntimeError: se todas as tentativas falharem (erro de API ou
            validação Pydantic persistente).
    """
    tool = montar_tool_schema()
    mensagens: list[dict] = [{"role": "user", "content": texto_laudo}]

    ultimo_erro: Exception | None = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resposta = client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=PROMPT_SISTEMA,
                tools=[tool],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=mensagens,
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            ultimo_erro = exc
            espera = BACKOFF_BASE_SEGUNDOS ** tentativa
            logger.warning(
                "Erro de API em %s (tentativa %d/%d): %s -- aguardando %ds",
                nome_arquivo, tentativa, MAX_TENTATIVAS, exc, espera,
            )
            time.sleep(espera)
            continue

        bloco_tool = next(
            (b for b in resposta.content if b.type == "tool_use"), None
        )
        if bloco_tool is None:
            ultimo_erro = RuntimeError("modelo não retornou tool_use")
            logger.warning("%s: sem tool_use na resposta (tentativa %d)", nome_arquivo, tentativa)
            continue

        try:
            dados = dict(bloco_tool.input)
            dados["arquivo_origem"] = nome_arquivo
            return LaudoExtraido.model_validate(dados)
        except ValidationError as exc:
            ultimo_erro = exc
            logger.warning(
                "%s: saída inválida na tentativa %d/%d -- %s",
                nome_arquivo, tentativa, MAX_TENTATIVAS, exc.errors(),
            )
            # devolve o erro ao modelo para a próxima tentativa se corrigir
            mensagens = mensagens + [
                {"role": "assistant", "content": resposta.content},
                {
                    "role": "user",
                    "content": (
                        f"A saída não passou na validação: {exc.errors()}. "
                        "Corrija e chame a tool novamente."
                    ),
                },
            ]

    raise RuntimeError(
        f"Falha ao extrair {nome_arquivo} após {MAX_TENTATIVAS} tentativas: {ultimo_erro}"
    )


def processar_diretorio(entrada: Path, client: anthropic.Anthropic) -> list[dict]:
    """Processa todos os .txt de um diretório, isolando falhas por arquivo.

    Uma falha em um laudo não derruba o lote inteiro -- fica registrada em
    log e o processamento segue para o próximo arquivo, para que uma rotina
    semanal automatizada não pare por causa de um único documento problemático.
    """
    arquivos = sorted(entrada.glob("*.txt"))
    if not arquivos:
        logger.error("Nenhum .txt encontrado em %s", entrada)
        return []

    resultados: list[dict] = []
    falhas = 0
    for caminho in arquivos:
        texto = caminho.read_text(encoding="utf-8")
        try:
            registro = extrair_um_laudo(client, texto, caminho.name)
            resultados.append(registro.model_dump(mode="json"))
            logger.info("OK: %s", caminho.name)
        except RuntimeError as exc:
            falhas += 1
            logger.error("FALHOU: %s -- %s", caminho.name, exc)

    logger.info(
        "Processamento concluído: %d ok, %d falhas, %d total",
        len(resultados), falhas, len(arquivos),
    )
    return resultados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, required=True, help="Diretório com os .txt dos laudos")
    parser.add_argument("--saida", type=Path, required=True, help="Caminho do JSON consolidado de saída")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    except anthropic.AnthropicError as exc:
        logger.error("Não foi possível inicializar o cliente Anthropic: %s", exc)
        return 1

    if not args.entrada.is_dir():
        logger.error("Diretório de entrada não existe: %s", args.entrada)
        return 1

    resultados = processar_diretorio(args.entrada, client)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saída gravada em %s", args.saida)
    return 0 if resultados else 1


if __name__ == "__main__":
    sys.exit(main())
