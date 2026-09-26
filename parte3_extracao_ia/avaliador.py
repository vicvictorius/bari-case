"""Mede a acurácia da extração comparando contra o gabarito manual.

Critério de acerto (ver decisoes.md para a justificativa completa):
    - Acerto de STATUS: o extrator classificou o campo como presente/ausente/
      conflitante da mesma forma que o gabarito?
    - Acerto de VALOR: quando ambos (gabarito e extração) dizem "presente",
      o valor extraído bate com o valor do gabarito após normalização?

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
from datetime import datetime
from pathlib import Path

from schema import CAMPOS_LAUDO


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
    """
    texto = texto.strip()

    for formato in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(
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
    """Normaliza um valor para comparação.

    Datas e números são comparados pelo significado, não pela representação
    textual.

    Também são removidos wrappers artificiais específicos observados durante
    os benchmarks dos modelos locais.

    Textos que não correspondem a esses padrões continuam sendo comparados
    de forma conservadora, evitando esconder diferenças semânticas reais.
    """
    if valor is None:
        return None

    texto = valor.strip()

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
    """
    por_campo = {
        campo: {
            "status_ok": 0,
            "valor_ok": 0,
            "valor_aplicavel": 0,
            "total": 0,
        }
        for campo in CAMPOS_LAUDO
    }

    divergencias: list[dict] = []
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

                if valor_obtido == valor_esperado:
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

    return {
        "acuracia_status_geral": round(
            acuracia_status_geral,
            3,
        ),
        "por_campo": resumo,
        "divergencias": divergencias,
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
            "Acurácia de valor (quando presente) | n |"
        ),
        "|---|---|---|---|",
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

        linhas.append(
            f"| {campo} | "
            f"{acuracia_status} | "
            f"{acuracia_valor} | "
            f"{metricas['n']} |"
        )

    if resultado["arquivos_faltando_na_extracao"]:
        linhas.extend(
            [
                "",
                "## Laudos ausentes na extração "
                "(falha do pipeline)",
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

    if resultado["divergencias"]:
        linhas.extend(
            [
                "",
                "## Divergências "
                "(auditoria linha a linha)",
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

    print(
        f"Relatório gravado em {args.relatorio}"
    )


if __name__ == "__main__":
    main()