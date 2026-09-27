"""Extrai campos estruturados dos laudos usando um modelo local via Ollama.

Alternativa 100% gratuita a `extrator.py` (que usa a API paga da Anthropic).
Mesmo schema, mesmo prompt, mesma lógica de validação/retry -- só troca o
"motor" de LLM. Ver decisoes.md para a justificativa de por que essa troca
foi feita (restrição de orçamento) e o trade-off de qualidade esperado.

Pré-requisitos (rodam na SUA máquina, não em nenhum servidor externo):
    1. Instalar o Ollama: https://ollama.com/download
    2. Rodar o servidor local (geralmente inicia sozinho como serviço,
       senão: `ollama serve`)
    3. Baixar um modelo, ex: `ollama pull qwen2.5:7b-instruct`
       (ver decisoes.md para orientação de qual modelo escolher conforme
       a RAM disponível)

Uso:
    python extrator_local.py --entrada ../dados_brutos/laudos_avaliacao \
        --saida saida_extracao_local.json --modelo qwen2.5:7b-instruct
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import ollama
from pydantic import ValidationError

from extrator import PROMPT_SISTEMA
from schema import CAMPOS_LAUDO, LaudoExtraido, json_schema_campos

logger = logging.getLogger("extrator_laudos_local")

MODELO_PADRAO = "qwen2.5:7b-instruct"
MAX_TENTATIVAS = 3


def montar_json_schema() -> dict:
    """Schema JSON (formato "format" do Ollama) equivalente ao tool_schema da versão API.

    Mesma fonte de verdade (schema.py) -- só muda o formato de declaração
    exigido pelo cliente do Ollama.
    """
    return {
        "type": "object",
        "properties": json_schema_campos(),
        "required": CAMPOS_LAUDO,
    }


def caminho_falhas(saida: Path) -> Path:
    """Monta o caminho do JSON versionável com as falhas da execução."""
    return saida.with_name(f"falhas_{saida.name}")


def extrair_um_laudo(
    client: ollama.Client,
    modelo: str,
    texto_laudo: str,
    nome_arquivo: str,
) -> LaudoExtraido:
    """Extrai os campos de um laudo via modelo local, com retry em caso de saída inválida.

    Diferente da versão via API (que usa "tool use" para forçar a estrutura
    no nível do provedor), aqui a validação Pydantic carrega mais peso: o
    `format` do Ollama restringe a FORMA do JSON, mas não valida as regras
    semânticas (ex: trecho_bruto obrigatório quando status != presente) --
    isso só o Pydantic garante.
    """
    schema = montar_json_schema()

    mensagens: list[dict] = [
        {
            "role": "system",
            "content": PROMPT_SISTEMA,
        },
        {
            "role": "user",
            "content": texto_laudo,
        },
    ]

    ultimo_erro: Exception | None = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resposta = client.chat(
                model=modelo,
                messages=mensagens,
                format=schema,
            )

        except Exception as exc:
            ultimo_erro = exc

            logger.warning(
                "%s: erro ao chamar o Ollama "
                "(tentativa %d/%d) -- %s",
                nome_arquivo,
                tentativa,
                MAX_TENTATIVAS,
                exc,
            )

            continue

        conteudo = resposta["message"]["content"]

        try:
            dados = json.loads(conteudo)
            dados["arquivo_origem"] = nome_arquivo

            return LaudoExtraido.model_validate(dados)

        except (json.JSONDecodeError, ValidationError) as exc:
            ultimo_erro = exc

            detalhe = (
                exc.errors()
                if isinstance(exc, ValidationError)
                else str(exc)
            )

            logger.warning(
                "%s: saída inválida na tentativa %d/%d -- %s",
                nome_arquivo,
                tentativa,
                MAX_TENTATIVAS,
                detalhe,
            )

            mensagens = mensagens + [
                {
                    "role": "assistant",
                    "content": conteudo,
                },
                {
                    "role": "user",
                    "content": (
                        "A saída não é um JSON válido para o "
                        f"schema pedido: {detalhe}. "
                        "Gere novamente, só o JSON, "
                        "sem texto antes ou depois."
                    ),
                },
            ]

    raise RuntimeError(
        f"Falha ao extrair {nome_arquivo} após "
        f"{MAX_TENTATIVAS} tentativas: {ultimo_erro}"
    )


def processar_diretorio(
    entrada: Path,
    client: ollama.Client,
    modelo: str,
) -> tuple[list[dict], list[dict]]:
    """Processa todos os .txt de um diretório, isolando falhas por arquivo.

    Retorna os resultados válidos e os registros das falhas. Isso permite
    preservar resultados parciais para auditoria sem sinalizar uma execução
    incompleta como sucesso.
    """
    arquivos = sorted(entrada.glob("*.txt"))

    if not arquivos:
        logger.error(
            "Nenhum .txt encontrado em %s",
            entrada,
        )
        return [], []

    resultados: list[dict] = []
    falhas: list[dict] = []

    for caminho in arquivos:
        texto = caminho.read_text(
            encoding="utf-8",
        )

        try:
            registro = extrair_um_laudo(
                client,
                modelo,
                texto,
                caminho.name,
            )

            resultados.append(
                registro.model_dump(
                    mode="json",
                )
            )

            logger.info(
                "OK: %s",
                caminho.name,
            )

        except RuntimeError as exc:
            falhas.append(
                {
                    "arquivo_origem": caminho.name,
                    "ultimo_erro": str(exc),
                }
            )

            logger.error(
                "FALHOU: %s -- %s",
                caminho.name,
                exc,
            )

    logger.info(
        "Processamento concluído: %d ok, %d falhas, %d total",
        len(resultados),
        len(falhas),
        len(arquivos),
    )

    return resultados, falhas


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--entrada",
        type=Path,
        required=True,
        help="Diretório com os .txt dos laudos",
    )

    parser.add_argument(
        "--saida",
        type=Path,
        required=True,
        help="Caminho do JSON consolidado de saída",
    )

    parser.add_argument(
        "--modelo",
        default=MODELO_PADRAO,
        help=(
            "Nome do modelo no Ollama "
            "(ex: qwen2.5:7b-instruct)"
        ),
    )

    parser.add_argument(
        "--host",
        default="http://localhost:11434",
        help="Endereço do servidor Ollama local",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    client = ollama.Client(
        host=args.host,
    )

    try:
        client.list()

    except Exception as exc:
        logger.error(
            "Não consegui conectar ao Ollama em %s -- "
            "ele está rodando? (%s)",
            args.host,
            exc,
        )
        return 1

    if not args.entrada.is_dir():
        logger.error(
            "Diretório de entrada não existe: %s",
            args.entrada,
        )
        return 1

    resultados, falhas = processar_diretorio(
        args.entrada,
        client,
        args.modelo,
    )

    args.saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.saida.write_text(
        json.dumps(
            resultados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info(
        "Saída gravada em %s",
        args.saida,
    )

    arquivo_falhas = caminho_falhas(args.saida)

    arquivo_falhas.write_text(
        json.dumps(
            falhas,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info(
        "Falhas gravadas em %s",
        arquivo_falhas,
    )

    if falhas:
        logger.error(
            "Execução incompleta: %d arquivo(s) falharam. "
            "A saída parcial foi preservada para auditoria.",
            len(falhas),
        )
        return 1

    if not resultados:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())