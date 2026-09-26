"""Mede a acurácia da extração comparando contra o gabarito manual.

Critério de acerto (ver decisoes.md para a justificativa completa):
    - Acerto de STATUS: o extrator classificou o campo como presente/ausente/
      conflitante da mesma forma que o gabarito?
    - Acerto de VALOR: quando ambos (gabarito e extração) dizem "presente",
      o valor extraído bate com o valor do gabarito após normalização?
    - EQUIVALÊNCIA TEXTUAL: métrica complementar aplicada somente a campos
      textuais selecionados. Ela não substitui a métrica conservadora.

Uso:
    python avaliador.py \
        --extracao saida_extracao.json \
        --gabarito gabarito.json \
        --relatorio relatorio_acuracia.md
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from schema import CAMPOS_LAUDO

CAMPOS_TEXTO_NORMALIZAVEIS = {
    "endereco",
    "matricula",
}


def _tentar_parse_numero(texto: str) -> float | None:
    """Interpreta texto como número em formato BR ou US.

    Exemplos aceitos:
        78,40
        78.40
        218.000
        1.275.000,00
        642000.00
        R$ 2.180.000,00
    """
    texto = re.sub(
        r"^R\$\s*",
        "",
        texto.strip(),
        flags=re.IGNORECASE,
    ).strip()

    if not re.fullmatch(r"[\d.,]+", texto):
        return None

    tem_ponto = "." in texto
    tem_virgula = "," in texto

    if tem_ponto and tem_virgula:
        # Formato brasileiro:
        # 1.275.000,00 -> 1275000.00
        texto = texto.replace(".", "").replace(",", ".")

    elif tem_virgula:
        # 78,40 -> 78.40
        texto = texto.replace(",", ".")

    elif tem_ponto:
        partes = texto.split(".")

        # 218.000 -> 218000
        # 1.275.000 -> 1275000
        if len(partes) > 2 or len(partes[-1]) == 3:
            texto = texto.replace(".", "")

    try:
        return float(texto)
    except ValueError:
        return None


def _tentar_parse_data(texto: str) -> str | None:
    """Interpreta formatos de data encontrados nos laudos.

    Retorna sempre no formato ISO AAAA-MM-DD.

    Timezone não se aplica aqui porque os valores representam datas civis
    do documento, e não instantes temporais.
    """
    texto = texto.strip()

    for formato in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(  # noqa: DTZ007
                texto,
                formato,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def _limpar_wrapper_modelo(texto: str) -> str:
    """Remove wrappers artificiais observados nas respostas dos modelos.

    A função é deliberadamente conservadora. Ela reconhece somente padrões
    específicos observados durante os benchmarks e só aceita wrappers cujo
    conteúdo interno representa um único valor numérico.

    Isso evita transformar frases ambíguas contendo vários números em um
    único valor e, consequentemente, inflar artificialmente a acurácia.
    """
    texto = texto.strip()

    numero = r"[\d.,]+"

    padroes = (
        # /78.40
        rf"^/({numero})$",

        # id_146.00
        rf"^id_({numero})$",

        # ${1020.00}
        rf"^\$\{{({numero})\}}$",

        # strconv(285)
        # log(910000)
        rf"^(?:strconv|log)\(({numero})\)$",

        # name: 420,00 m²
        rf"^name:\s*({numero})\s*m²$",
    )

    for padrao in padroes:
        correspondencia = re.fullmatch(
            padrao,
            texto,
            flags=re.IGNORECASE,
        )

        if correspondencia:
            return correspondencia.group(1)

    return texto


def normalizar_valor(valor: str | None) -> str | None:
    """Normaliza um valor para a comparação conservadora principal.

    Datas e números são comparados pelo significado, não pela representação
    textual.

    Também são removidos wrappers artificiais específicos observados durante
    os benchmarks dos modelos locais.

    Textos que não correspondem a esses padrões continuam sendo comparados
    de forma conservadora, evitando esconder diferenças semânticas reais.
    """
    if valor is None:
        return None

    # A partir do schema tipado, a extração traz números como número JSON
    # (ex: 78.4). O gabarito histórico guarda texto (ex: "78.40").
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return f"num:{round(float(valor), 2)}"

    texto = str(valor).strip()

    # Primeiro tenta interpretar o valor original como data.
    data_iso = _tentar_parse_data(texto)

    if data_iso is not None:
        return f"data:{data_iso}"

    # Remove somente wrappers conhecidos e não ambíguos.
    texto_limpo = _limpar_wrapper_modelo(texto)

    numero = _tentar_parse_numero(texto_limpo)

    if numero is not None:
        return f"num:{round(numero, 2)}"

    # Fallback textual conservador.
    return re.sub(
        r"\s+",
        " ",
        texto.lower(),
    )


def normalizar_texto_comparacao(valor: str | None) -> str | None:
    """Normaliza texto para uma métrica complementar de equivalência.

    Essa função é deliberadamente separada de normalizar_valor(). Assim,
    a métrica histórica/conservadora continua intacta.

    A normalização busca remover diferenças superficiais de representação,
    como acentuação, pontuação, separadores e alguns conectores.

    Ela é utilizada apenas nos campos definidos em
    CAMPOS_TEXTO_NORMALIZAVEIS.
    """
    if valor is None:
        return None

    texto = str(valor).strip().lower()

    # Remove acentuação sem alterar letras/números.
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    # Remove wrappers simples observados em saídas de modelos.
    texto = re.sub(
        r"^(?:strconv|value|name|id)\s*[:=]?\s*",
        "",
        texto,
    )

    # Remove caracteres artificiais nas extremidades.
    texto = re.sub(
        r"^[^\w\d]+|[^\w\d]+$",
        "",
        texto,
    )

    # Conectores simples não determinam equivalência de representação.
    texto = re.sub(
        r"\b(?:do|da|de)\b",
        " ",
        texto,
    )

    # Pontuação e separadores são transformados em espaços.
    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto,
    )

    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def carregar(caminho: Path) -> dict[str, dict]:
    """Carrega um JSON de registros e indexa por arquivo_origem."""
    registros = json.loads(
        caminho.read_text(encoding="utf-8")
    )

    return {
        registro["arquivo_origem"]: registro
        for registro in registros
    }


def avaliar(
    extracao: dict[str, dict],
    gabarito: dict[str, dict],
) -> dict:
    """Compara extração x gabarito e retorna métricas e divergências.

    Arquivos presentes no gabarito mas ausentes na extração contam como erro
    em todos os campos. Isso impede que falhas de cobertura sejam
    silenciosamente ignoradas.

    A métrica textual normalizada é complementar e não substitui a métrica
    conservadora de valor.
    """
    por_campo = {
        campo: {
            "status_ok": 0,
            "valor_ok": 0,
            "valor_aplicavel": 0,
            "texto_normalizado_ok": 0,
            "texto_normalizado_aplicavel": 0,
            "total": 0,
        }
        for campo in CAMPOS_LAUDO
    }

    divergencias: list[dict] = []
    equivalencias_textuais: list[dict] = []
    arquivos_faltando_na_extracao: list[str] = []

    for arquivo, registro_gabarito in gabarito.items():
        registro_extraido = extracao.get(arquivo)

        if registro_extraido is None:
            arquivos_faltando_na_extracao.append(arquivo)

            for campo in CAMPOS_LAUDO:
                por_campo[campo]["total"] += 1

            continue

        for campo in CAMPOS_LAUDO:
            esperado = registro_gabarito[campo]

            obtido = registro_extraido.get(
                campo,
                {
                    "valor": None,
                    "status": None,
                    "trecho_bruto": None,
                },
            )

            por_campo[campo]["total"] += 1

            status_ok = (
                obtido.get("status")
                == esperado["status"]
            )

            if status_ok:
                por_campo[campo]["status_ok"] += 1

            else:
                divergencias.append(
                    {
                        "arquivo": arquivo,
                        "campo": campo,
                        "tipo": "status",
                        "esperado": esperado["status"],
                        "obtido": obtido.get("status"),
                    }
                )

            if (
                esperado["status"] == "presente"
                and status_ok
            ):
                por_campo[campo]["valor_aplicavel"] += 1

                valor_obtido = normalizar_valor(
                    obtido.get("valor")
                )

                valor_esperado = normalizar_valor(
                    esperado["valor"]
                )

                valor_exato_ok = (
                    valor_obtido == valor_esperado
                )

                if valor_exato_ok:
                    por_campo[campo]["valor_ok"] += 1

                else:
                    divergencias.append(
                        {
                            "arquivo": arquivo,
                            "campo": campo,
                            "tipo": "valor",
                            "esperado": esperado["valor"],
                            "obtido": obtido.get("valor"),
                        }
                    )

                if campo in CAMPOS_TEXTO_NORMALIZAVEIS:
                    por_campo[campo][
                        "texto_normalizado_aplicavel"
                    ] += 1

                    texto_esperado = normalizar_texto_comparacao(
                        esperado["valor"]
                    )

                    texto_obtido = normalizar_texto_comparacao(
                        obtido.get("valor")
                    )

                    texto_normalizado_ok = (
                        texto_esperado == texto_obtido
                    )

                    if texto_normalizado_ok:
                        por_campo[campo][
                            "texto_normalizado_ok"
                        ] += 1

                        # Registra apenas os casos em que a comparação
                        # conservadora falhou, mas a normalizada considerou
                        # os textos equivalentes. Isso facilita auditoria.
                        if not valor_exato_ok:
                            equivalencias_textuais.append(
                                {
                                    "arquivo": arquivo,
                                    "campo": campo,
                                    "esperado": esperado["valor"],
                                    "obtido": obtido.get("valor"),
                                    "esperado_normalizado": texto_esperado,
                                    "obtido_normalizado": texto_obtido,
                                }
                            )

    resumo = {}

    for campo, contagens in por_campo.items():
        total = contagens["total"]

        if contagens["valor_aplicavel"] > 0:
            acuracia_valor = round(
                contagens["valor_ok"]
                / contagens["valor_aplicavel"],
                3,
            )
        else:
            acuracia_valor = None

        if contagens["texto_normalizado_aplicavel"] > 0:
            acuracia_texto_normalizado = round(
                contagens["texto_normalizado_ok"]
                / contagens["texto_normalizado_aplicavel"],
                3,
            )
        else:
            acuracia_texto_normalizado = None

        resumo[campo] = {
            "acuracia_status": (
                round(
                    contagens["status_ok"] / total,
                    3,
                )
                if total > 0
                else None
            ),
            "acuracia_valor_quando_presente": acuracia_valor,
            "acuracia_texto_normalizado":
                acuracia_texto_normalizado,
            "valor_ok": contagens["valor_ok"],
            "valor_aplicavel":
                contagens["valor_aplicavel"],
            "texto_normalizado_ok":
                contagens["texto_normalizado_ok"],
            "texto_normalizado_aplicavel":
                contagens["texto_normalizado_aplicavel"],
            "n": total,
        }

    total_status = sum(
        contagens["total"]
        for contagens in por_campo.values()
    )

    status_corretos = sum(
        contagens["status_ok"]
        for contagens in por_campo.values()
    )

    acuracia_status_geral = (
        status_corretos / total_status
        if total_status > 0
        else 0
    )

    valores_aplicaveis = sum(
        contagens["valor_aplicavel"]
        for contagens in por_campo.values()
    )

    valores_corretos = sum(
        contagens["valor_ok"]
        for contagens in por_campo.values()
    )

    # Acurácia de valor mede:
    # dos campos que o gabarito diz "presente" e o modelo também,
    # quantos vieram com o valor correto pela comparação conservadora.
    acuracia_valor_geral = (
        valores_corretos / valores_aplicaveis
        if valores_aplicaveis > 0
        else None
    )

    textos_normalizados_aplicaveis = sum(
        contagens["texto_normalizado_aplicavel"]
        for campo, contagens in por_campo.items()
        if campo in CAMPOS_TEXTO_NORMALIZAVEIS
    )

    textos_normalizados_corretos = sum(
        contagens["texto_normalizado_ok"]
        for campo, contagens in por_campo.items()
        if campo in CAMPOS_TEXTO_NORMALIZAVEIS
    )

    acuracia_texto_normalizado_geral = (
        textos_normalizados_corretos
        / textos_normalizados_aplicaveis
        if textos_normalizados_aplicaveis > 0
        else None
    )

    return {
        "acuracia_status_geral": round(
            acuracia_status_geral,
            3,
        ),
        "acuracia_valor_geral": (
            round(acuracia_valor_geral, 3)
            if acuracia_valor_geral is not None
            else None
        ),
        "valores_corretos": valores_corretos,
        "valores_aplicaveis": valores_aplicaveis,
        "acuracia_texto_normalizado_geral": (
            round(acuracia_texto_normalizado_geral, 3)
            if acuracia_texto_normalizado_geral is not None
            else None
        ),
        "textos_normalizados_corretos":
            textos_normalizados_corretos,
        "textos_normalizados_aplicaveis":
            textos_normalizados_aplicaveis,
        "por_campo": resumo,
        "divergencias": divergencias,
        "equivalencias_textuais": equivalencias_textuais,
        "arquivos_faltando_na_extracao":
            arquivos_faltando_na_extracao,
        "total_laudos_gabarito": len(gabarito),
        "total_laudos_extraidos": len(extracao),
    }


def gerar_relatorio_md(resultado: dict) -> str:
    """Gera relatório Markdown auditável com as métricas."""
    linhas = [
        "# Relatório de acurácia — extração dos laudos",
        "",
        (
            "Acurácia geral de status "
            "(presente/ausente/conflitante correto): "
            f"**{resultado['acuracia_status_geral']:.1%}**"
        ),
        "",
        (
            "Acurácia geral de valor "
            "(valor certo quando gabarito e extração dizem presente): "
            + (
                f"**{resultado['acuracia_valor_geral']:.1%}** "
                f"({resultado['valores_corretos']}/"
                f"{resultado['valores_aplicaveis']})"
                if resultado["acuracia_valor_geral"] is not None
                else "n/a"
            )
        ),
        "",
        (
            "A métrica de valor acima permanece como comparação "
            "conservadora principal."
        ),
        "",
        (
            "A equivalência textual normalizada é uma métrica "
            "complementar aplicada apenas a `endereco` e `matricula`. "
            "Ela remove diferenças superficiais de representação e "
            "não substitui a métrica principal."
        ),
        "",
        (
            "Equivalência textual normalizada geral "
            "(`endereco` + `matricula`): "
            + (
                f"**{resultado['acuracia_texto_normalizado_geral']:.1%}** "
                f"({resultado['textos_normalizados_corretos']}/"
                f"{resultado['textos_normalizados_aplicaveis']})"
                if resultado[
                    "acuracia_texto_normalizado_geral"
                ] is not None
                else "n/a"
            )
        ),
        "",
        (
            f"Laudos no gabarito: "
            f"{resultado['total_laudos_gabarito']} | "
            f"Laudos na extração: "
            f"{resultado['total_laudos_extraidos']}"
        ),
        "",
        "## Acurácia por campo",
        "",
        (
            "| Campo | Acurácia de status | "
            "Acurácia de valor (quando presente) | "
            "Equivalência textual normalizada | n |"
        ),
        "|---|---|---|---|---|",
    ]

    for campo, metricas in resultado["por_campo"].items():
        acuracia_valor = (
            f"{metricas['acuracia_valor_quando_presente']:.1%}"
            if metricas[
                "acuracia_valor_quando_presente"
            ] is not None
            else "n/a"
        )

        acuracia_status = (
            f"{metricas['acuracia_status']:.1%}"
            if metricas["acuracia_status"] is not None
            else "n/a"
        )

        acuracia_texto = (
            f"{metricas['acuracia_texto_normalizado']:.1%}"
            if metricas["acuracia_texto_normalizado"] is not None
            else "—"
        )

        linhas.append(
            f"| {campo} | "
            f"{acuracia_status} | "
            f"{acuracia_valor} | "
            f"{acuracia_texto} | "
            f"{metricas['n']} |"
        )

    if resultado["arquivos_faltando_na_extracao"]:
        linhas.extend(
            [
                "",
                (
                    "## Laudos ausentes na extração "
                    "(falha do pipeline)"
                ),
                "",
            ]
        )

        linhas.extend(
            f"- {arquivo}"
            for arquivo
            in resultado[
                "arquivos_faltando_na_extracao"
            ]
        )

    if resultado["equivalencias_textuais"]:
        linhas.extend(
            [
                "",
                "## Equivalências recuperadas pela normalização textual",
                "",
                (
                    "Os casos abaixo falharam na comparação conservadora, "
                    "mas foram considerados equivalentes após a "
                    "normalização textual complementar."
                ),
                "",
                (
                    "| Arquivo | Campo | Esperado | Obtido | "
                    "Normalizado |"
                ),
                "|---|---|---|---|---|",
            ]
        )

        for item in resultado["equivalencias_textuais"]:
            linhas.append(
                f"| {item['arquivo']} | "
                f"{item['campo']} | "
                f"{item['esperado']} | "
                f"{item['obtido']} | "
                f"{item['esperado_normalizado']} |"
            )

    if resultado["divergencias"]:
        linhas.extend(
            [
                "",
                (
                    "## Divergências "
                    "(auditoria linha a linha)"
                ),
                "",
                (
                    "| Arquivo | Campo | Tipo | "
                    "Esperado (gabarito) | "
                    "Obtido (extração) |"
                ),
                "|---|---|---|---|---|",
            ]
        )

        for divergencia in resultado["divergencias"]:
            linhas.append(
                f"| {divergencia['arquivo']} | "
                f"{divergencia['campo']} | "
                f"{divergencia['tipo']} | "
                f"{divergencia['esperado']} | "
                f"{divergencia['obtido']} |"
            )

    else:
        linhas.extend(
            [
                "",
                "Nenhuma divergência encontrada.",
            ]
        )

    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--extracao",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--gabarito",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--relatorio",
        type=Path,
        default=Path("relatorio_acuracia.md"),
    )

    args = parser.parse_args()

    extracao = carregar(args.extracao)
    gabarito = carregar(args.gabarito)

    resultado = avaliar(
        extracao,
        gabarito,
    )

    args.relatorio.write_text(
        gerar_relatorio_md(resultado),
        encoding="utf-8",
    )

    print(
        "Acurácia geral de status: "
        f"{resultado['acuracia_status_geral']:.1%}"
    )

    if resultado["acuracia_valor_geral"] is not None:
        print(
            "Acurácia geral de valor: "
            f"{resultado['acuracia_valor_geral']:.1%}"
        )

    if resultado["acuracia_texto_normalizado_geral"] is not None:
        print(
            "Equivalência textual normalizada "
            "(endereco + matricula): "
            f"{resultado['acuracia_texto_normalizado_geral']:.1%}"
        )

    print(
        f"Relatório gravado em {args.relatorio}"
    )


if __name__ == "__main__":
    main()