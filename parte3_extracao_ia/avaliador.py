"""Mede a acurácia da extração comparando contra o gabarito manual.

Critério de acerto (ver decisoes.md para a justificativa completa):
    - Acerto de STATUS: o extrator classificou o campo como presente/ausente/
      conflitante da mesma forma que o gabarito? Isso captura o requisito
      mais importante do desafio -- "não chutar" quando não sabe.
    - Acerto de VALOR: quando ambos (gabarito e extração) dizem "presente",
      o valor extraído bate com o valor do gabarito (após normalização)?
      Só faz sentido comparar valor quando o status bate em "presente";
      comparar valores de campos ausentes/conflitantes não tem significado.

Uso:
    python avaliador.py --extracao saida_extracao.json --gabarito gabarito.json --relatorio relatorio_acuracia.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from schema import CAMPOS_LAUDO


def _tentar_parse_numero(texto: str) -> float | None:
    """Interpreta `texto` como número (formato BR ou US), ou None se não for.

    Trata os casos que apareceram na prática: "78,40" (BR decimal),
    "218.000" (BR milhar), "1.275.000,00" (BR milhar+decimal), "642000.00"
    (US decimal), "R$ 2.180.000,00" (com prefixo de moeda). Sem isso,
    diferenças puramente de formatação (que não são erro de extração)
    inflavam a taxa de divergência do relatório.
    """
    texto = re.sub(r"^R\$\s*", "", texto.strip(), flags=re.IGNORECASE).strip()
    if not re.fullmatch(r"[\d.,]+", texto):
        return None

    tem_ponto, tem_virgula = "." in texto, "," in texto
    if tem_ponto and tem_virgula:
        texto = texto.replace(".", "").replace(",", ".")  # BR: milhar . / decimal ,
    elif tem_virgula:
        texto = texto.replace(",", ".")  # só vírgula -> decimal
    elif tem_ponto:
        partes = texto.split(".")
        if len(partes) > 2 or len(partes[-1]) == 3:
            texto = texto.replace(".", "")  # múltiplos pontos, ou 3 dígitos após -> milhar

    try:
        return float(texto)
    except ValueError:
        return None


def _tentar_parse_data(texto: str) -> str | None:
    """Interpreta `texto` como data em qualquer formato usado nos laudos,
    devolve ISO AAAA-MM-DD, ou None se não for uma data reconhecível."""
    texto = texto.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalizar_valor(valor: str | None) -> str | None:
    """Normaliza um valor para comparação, tolerando diferenças de formato.

    Número e data são comparados pelo valor real (78,40 == 78.40; 12/03/2025
    == 2025-03-12), não pela representação em string -- isso é o que separa
    "o modelo errou a informação" de "o modelo não normalizou como o prompt
    pedia", que são achados bem diferentes num relatório de acurácia.
    Qualquer outro texto cai no fallback: minúsculas, espaços colapsados.
    """
    if valor is None:
        return None
    texto = valor.strip()

    data_iso = _tentar_parse_data(texto)
    if data_iso is not None:
        return f"data:{data_iso}"

    numero = _tentar_parse_numero(texto)
    if numero is not None:
        return f"num:{round(numero, 2)}"

    return re.sub(r"\s+", " ", texto.lower())


def carregar(caminho: Path) -> dict[str, dict]:
    """Carrega um JSON de registros e indexa por arquivo_origem."""
    registros = json.loads(caminho.read_text(encoding="utf-8"))
    return {r["arquivo_origem"]: r for r in registros}


def avaliar(extracao: dict[str, dict], gabarito: dict[str, dict]) -> dict:
    """Compara extração x gabarito e retorna métricas + divergências.

    Arquivos presentes no gabarito mas ausentes na extração (ex: falha da
    API para aquele laudo) contam como erro em todos os campos -- não são
    silenciosamente ignorados, porque isso inflaria a acurácia escondendo
    falhas de cobertura.
    """
    por_campo = {campo: {"status_ok": 0, "valor_ok": 0, "valor_aplicavel": 0, "total": 0} for campo in CAMPOS_LAUDO}
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
            obtido = registro_extraido.get(campo, {"valor": None, "status": None, "trecho_bruto": None})
            por_campo[campo]["total"] += 1

            status_ok = obtido.get("status") == esperado["status"]
            if status_ok:
                por_campo[campo]["status_ok"] += 1
            else:
                divergencias.append({
                    "arquivo": arquivo, "campo": campo, "tipo": "status",
                    "esperado": esperado["status"], "obtido": obtido.get("status"),
                })

            if esperado["status"] == "presente" and status_ok:
                por_campo[campo]["valor_aplicavel"] += 1
                if normalizar_valor(obtido.get("valor")) == normalizar_valor(esperado["valor"]):
                    por_campo[campo]["valor_ok"] += 1
                else:
                    divergencias.append({
                        "arquivo": arquivo, "campo": campo, "tipo": "valor",
                        "esperado": esperado["valor"], "obtido": obtido.get("valor"),
                    })

    resumo = {}
    for campo, contagens in por_campo.items():
        total = contagens["total"] or 1
        aplicavel = contagens["valor_aplicavel"] or 1
        resumo[campo] = {
            "acuracia_status": round(contagens["status_ok"] / total, 3),
            "acuracia_valor_quando_presente": round(contagens["valor_ok"] / aplicavel, 3)
            if contagens["valor_aplicavel"] > 0 else None,
            "n": contagens["total"],
        }

    acuracia_status_geral = sum(c["status_ok"] for c in por_campo.values()) / sum(c["total"] for c in por_campo.values())

    return {
        "acuracia_status_geral": round(acuracia_status_geral, 3),
        "por_campo": resumo,
        "divergencias": divergencias,
        "arquivos_faltando_na_extracao": arquivos_faltando_na_extracao,
        "total_laudos_gabarito": len(gabarito),
        "total_laudos_extraidos": len(extracao),
    }


def gerar_relatorio_md(resultado: dict) -> str:
    linhas = [
        "# Relatório de acurácia — extração dos laudos",
        "",
        f"Acurácia geral de status (presente/ausente/conflitante correto): "
        f"**{resultado['acuracia_status_geral']:.1%}**",
        f"Laudos no gabarito: {resultado['total_laudos_gabarito']} | "
        f"Laudos na extração: {resultado['total_laudos_extraidos']}",
        "",
        "## Acurácia por campo",
        "",
        "| Campo | Acurácia de status | Acurácia de valor (quando presente) | n |",
        "|---|---|---|---|",
    ]
    for campo, m in resultado["por_campo"].items():
        acc_valor = f"{m['acuracia_valor_quando_presente']:.1%}" if m["acuracia_valor_quando_presente"] is not None else "n/a"
        linhas.append(f"| {campo} | {m['acuracia_status']:.1%} | {acc_valor} | {m['n']} |")

    if resultado["arquivos_faltando_na_extracao"]:
        linhas += ["", "## Laudos ausentes na extração (falha do pipeline)", ""]
        linhas += [f"- {a}" for a in resultado["arquivos_faltando_na_extracao"]]

    if resultado["divergencias"]:
        linhas += ["", "## Divergências (auditoria linha a linha)", "",
                    "| Arquivo | Campo | Tipo | Esperado (gabarito) | Obtido (extração) |",
                    "|---|---|---|---|---|"]
        for d in resultado["divergencias"]:
            linhas.append(f"| {d['arquivo']} | {d['campo']} | {d['tipo']} | {d['esperado']} | {d['obtido']} |")
    else:
        linhas += ["", "Nenhuma divergência encontrada."]

    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracao", type=Path, required=True)
    parser.add_argument("--gabarito", type=Path, required=True)
    parser.add_argument("--relatorio", type=Path, default=Path("relatorio_acuracia.md"))
    args = parser.parse_args()

    extracao = carregar(args.extracao)
    gabarito = carregar(args.gabarito)
    resultado = avaliar(extracao, gabarito)

    args.relatorio.write_text(gerar_relatorio_md(resultado), encoding="utf-8")
    print(f"Acurácia geral de status: {resultado['acuracia_status_geral']:.1%}")
    print(f"Relatório gravado em {args.relatorio}")


if __name__ == "__main__":
    main()
