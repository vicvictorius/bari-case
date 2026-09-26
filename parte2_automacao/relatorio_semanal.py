"""Gera o relatório semanal do funil a partir do CSV bruto, sem chamar modelos."""

import argparse
import csv
from datetime import date, timedelta
from html import escape
import json
import logging
import math
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from pipeline.tratamento import tratar_dados

COLUNAS = (
    "id_proposta", "data_entrada", "canal_origem", "cidade", "uf", "tipo_imovel",
    "valor_imovel", "valor_solicitado", "prazo_meses", "score_credito",
    "idade_cliente", "renda_mensal_declarada", "flag_cliente_recorrente",
    "consultor_id", "etapa_max_funil", "status_final", "tempo_analise_dias",
    "data_assinatura_contrato", "taxa_juros_aa",
)
NUMERICAS = (
    "valor_imovel", "valor_solicitado", "prazo_meses", "score_credito",
    "idade_cliente", "renda_mensal_declarada", "flag_cliente_recorrente",
    "etapa_max_funil", "tempo_analise_dias", "taxa_juros_aa",
)
STATUS = {
    "Contratada", "Sem retorno", "Desistiu", "Reprovada crédito",
    "Problema garantia", "Documentação pendente",
}
ETAPAS = {1: "Simulação", 2: "Lead", 3: "Análise de crédito",
          4: "Avaliação do imóvel", 5: "Formalização", 6: "Contratação"}
LOG = logging.getLogger("bari.semanal")


class ErroEntrada(ValueError):
    """Arquivo incompatível com o contrato de entrada documentado."""


def ler_e_tratar(caminho: Path) -> pd.DataFrame:
    """Valida o contrato e aplica, sem alterar, as regras compartilhadas."""
    try:
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            primeira = arquivo.readline()
            separador = ";" if primeira.count(";") > primeira.count(",") else ","
            arquivo.seek(0)
            leitor = csv.reader(arquivo, delimiter=separador, strict=True)
            cabecalho = next(leitor, [])
            if len(set(cabecalho)) != len(cabecalho):
                raise ErroEntrada("Cabeçalho contém colunas duplicadas.")
            faltantes = sorted(set(COLUNAS) - set(cabecalho))
            if faltantes:
                raise ErroEntrada("Colunas obrigatórias ausentes: " + ", ".join(faltantes))
            for numero, linha in enumerate(leitor, 2):
                if len(linha) != len(cabecalho):
                    raise ErroEntrada(f"Registro {numero}: quantidade de campos diferente do cabeçalho.")
        bruto = pd.read_csv(caminho, sep=separador, encoding="utf-8-sig", dtype=str)
    except (UnicodeError, csv.Error, pd.errors.ParserError) as exc:
        raise ErroEntrada("CSV inválido: use UTF-8, separador vírgula ou ponto e vírgula.") from exc

    if bruto.empty:
        raise ErroEntrada("CSV sem registros; não é possível verificar a cobertura da base.")
    extras = sorted(set(bruto.columns) - set(COLUNAS))
    LOG.info("Leitura: %d registros, %d colunas, separador %r", len(bruto), len(bruto.columns), separador)
    if extras:
        LOG.warning("Colunas adicionais preservadas, sem uso nas métricas: %s", ", ".join(extras))

    # Os únicos nulos estruturais admitidos na entrada são os já documentados.
    for coluna in COLUNAS:
        if coluna not in {"data_assinatura_contrato", "taxa_juros_aa"}:
            if bruto[coluna].fillna("").str.strip().eq("").any():
                raise ErroEntrada(f"Coluna {coluna}: valor obrigatório ausente.")
    if bruto["id_proposta"].duplicated().any():
        raise ErroEntrada("id_proposta duplicado; execução interrompida para não inflar as métricas.")
    desconhecidos = set(bruto["status_final"]) - STATUS
    if desconhecidos:
        raise ErroEntrada("status_final não reconhecido: " + ", ".join(sorted(desconhecidos)))

    # Evita que errors='coerce' do pipeline esconda formatos novos não vazios.
    for coluna in NUMERICAS:
        texto = bruto[coluna]
        if coluna == "valor_imovel":
            texto = texto.str.replace("R$", "", regex=False).str.strip()
        convertido = pd.to_numeric(texto, errors="coerce")
        invalido = texto.notna() & ~convertido.map(lambda x: pd.notna(x) and math.isfinite(x))
        if invalido.any():
            raise ErroEntrada(f"Coluna {coluna}: número inválido; esperado ponto decimal, sem milhar.")
    for coluna in ("data_entrada", "data_assinatura_contrato"):
        texto = bruto[coluna]
        formatos = texto.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
        if coluna == "data_entrada":
            formatos |= texto.str.fullmatch(r"\d{2}/\d{2}/\d{4}").fillna(False)
            texto = texto.str.replace(r"^(\d{2})/(\d{2})/(\d{4})$", r"\3-\2-\1", regex=True)
        valido = pd.to_datetime(texto, format="%Y-%m-%d", errors="coerce").notna()
        if (bruto[coluna].notna() & ~(formatos & valido)).any():
            raise ErroEntrada(f"Coluna {coluna}: data inválida ou formato não suportado.")
    try:
        tratado = tratar_dados(bruto)
    except (ValueError, TypeError, AssertionError) as exc:
        raise ErroEntrada(f"Tratamento incompatível com a entrada: {exc}") from exc
    if not tratado["etapa_max_funil"].isin(ETAPAS).all():
        raise ErroEntrada("etapa_max_funil deve ser um inteiro entre 1 e 6 após o tratamento.")
    if (tratado[["valor_imovel", "valor_solicitado"]] <= 0).any().any():
        raise ErroEntrada("Valores de imóvel e crédito solicitado devem ser positivos.")
    LOG.info("Tratamento concluído: %d registros mantidos; regras do pipeline compartilhado", len(tratado))
    return tratado


def periodo(referencia: date) -> tuple[date, date]:
    """Retorna segunda inclusiva e segunda exclusiva da última semana completa."""
    fim = referencia - timedelta(days=referencia.weekday())
    return fim - timedelta(days=7), fim


def resumir(df: pd.DataFrame) -> dict:
    total = len(df)
    contratadas = int(df["status_final"].eq("Contratada").sum())
    return {
        "total": total, "contratadas": contratadas,
        "conversao": contratadas / total if total else None,
        "solicitado": float(df["valor_solicitado"].sum()),
        "perdido": float(df.loc[df["status_final"].ne("Contratada"), "valor_solicitado"].sum()),
    }


def calcular(df: pd.DataFrame, referencia: date) -> dict:
    inicio, fim = periodo(referencia)
    datas = df["data_entrada"]
    semana = df.loc[datas.ge(pd.Timestamp(inicio)) & datas.lt(pd.Timestamp(fim))]
    anterior = df.loc[datas.ge(pd.Timestamp(inicio - timedelta(days=7))) & datas.lt(pd.Timestamp(inicio))]
    historico = df.loc[datas.lt(pd.Timestamp(fim))]
    perdas = semana.loc[semana["status_final"].ne("Contratada")].groupby("etapa_max_funil").agg(
        propostas=("id_proposta", "size"), valor=("valor_solicitado", "sum"))
    canais = [{"canal": canal, **resumir(grupo)} for canal, grupo in semana.groupby("canal_origem")]
    avisos = [
        "Análise retrospectiva por data de entrada: os desfechos são os disponíveis no arquivo, "
        "inclusive os posteriores à semana selecionada. Não representa o status conhecido naquela data.",
        "Coortes recentes podem estar imaturas. Conversão observada não é previsão de conversão final "
        "nem taxa de contratos assinados durante a semana.",
    ]
    if semana.empty:
        avisos.append("Sem propostas com entrada na semana. Conversão não aplicável; ausência de registros não comprova ausência de atividade.")
    if datas.max() < pd.Timestamp(inicio):
        avisos.append("Possível base desatualizada: a última entrada é anterior à semana selecionada. Confirme a atualização do arquivo.")
    if datas.min() > pd.Timestamp(inicio):
        avisos.append("A primeira entrada da base é posterior ao início da semana; a cobertura do período pode ser parcial.")
    return {
        "inicio": inicio, "fim": fim, "referencia": referencia,
        "primeira_entrada": datas.min().date(), "ultima_entrada": datas.max().date(),
        "semana": resumir(semana), "anterior": resumir(anterior), "historico": resumir(historico),
        "perdas": perdas, "canais": canais, "avisos": avisos, "linhas": len(df),
        "filtros": preparar_filtros(semana),
    }


def numero(valor: float, casas: int = 0) -> str:
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def percentual(valor: float | None) -> str:
    return "Não aplicável" if valor is None else numero(valor * 100, 2) + "%"


def preparar_filtros(semana: pd.DataFrame) -> dict:
    """Resumos mínimos da coorte; cálculo e arredondamento continuam no Python.

    Índice zero significa todos. Índices evitam usar nomes de canais como chaves
    JavaScript e nenhuma informação individual precisa viajar no HTML.
    """
    canais = sorted(semana["canal_origem"].dropna().unique().tolist())
    resultados = []
    for canal in [None, *canais]:
        grupo = semana if canal is None else semana.loc[semana["canal_origem"].eq(canal)]
        por_etapa = []
        for etapa in [None, *ETAPAS]:
            recorte = grupo if etapa is None else grupo.loc[grupo["etapa_max_funil"].eq(etapa)]
            resumo = resumir(recorte)
            por_etapa.append([
                numero(resumo["total"]), numero(resumo["contratadas"]),
                percentual(resumo["conversao"]), numero(resumo["solicitado"], 2),
                numero(resumo["perdido"], 2),
            ])
        resultados.append(por_etapa)
    return {"canais": canais, "resultados": resultados}


SCRIPT_FILTROS = """
(() => {
    "use strict";

    const dados = JSON.parse(
        document.getElementById("dados-filtros").textContent
    );

    const canal = document.getElementById("filtro-canal");
    const etapa = document.getElementById("filtro-etapa");

    const tabela = document.getElementById("resumo-semanal");
    const titulo = tabela.tHead.rows[0].cells[1];

    const celulas = Array.from(
        tabela.tBodies[0].rows,
        linha => linha.cells[1]
    );

    const cards = [
        document.getElementById("kpi-total"),
        document.getElementById("kpi-contratadas"),
        document.getElementById("kpi-conversao"),
        document.getElementById("kpi-solicitado"),
        document.getElementById("kpi-perdido")
    ];

    const situacao = document.getElementById("situacao-filtros");

    function atualizar() {
        const valores =
            dados.resultados[
                Number(canal.value)
            ][
                Number(etapa.value)
            ];

        celulas.forEach(
            (celula, indice) => {
                celula.textContent = valores[indice];
            }
        );

        cards.forEach(
            (card, indice) => {
                if (indice >= 3) {
                    card.textContent = "R$ " + valores[indice];
                } else {
                    card.textContent = valores[indice];
                }
            }
        );

        const ativo =
            canal.value !== "0"
            || etapa.value !== "0";

        titulo.textContent = ativo
            ? "Semana selecionada — filtros aplicados"
            : "Semana selecionada";

        situacao.textContent = ativo
            ? "Filtro ativo: "
                + canal.options[
                    canal.selectedIndex
                ].textContent
                + " / "
                + etapa.options[
                    etapa.selectedIndex
                ].textContent
                + (
                    valores[0] === "0"
                        ? ". Sem propostas para esta combinação."
                        : "."
                )
            : "Sem filtros: indicadores da semana completa.";
    }

    canal.addEventListener("change", atualizar);
    etapa.addEventListener("change", atualizar);

    document
        .getElementById("limpar-filtros")
        .addEventListener(
            "click",
            () => {
                canal.value = "0";
                etapa.value = "0";
                atualizar();
            }
        );

    canal.value = "0";
    etapa.value = "0";

    atualizar();

    document.getElementById(
        "controles-filtros"
    ).disabled = false;
})();
"""


# Notas metodológicas permanentes emitidas por calcular(). Usadas só para decidir
# ONDE cada aviso aparece no HTML; a regra que gera os avisos continua em calcular().
# Qualquer aviso fora desta lista é tratado como alerta dinâmico e sobe para o topo.
AVISOS_METODOLOGICOS = (
    "Análise retrospectiva por data de entrada: os desfechos são os disponíveis no arquivo, "
    "inclusive os posteriores à semana selecionada. Não representa o status conhecido naquela data.",
    "Coortes recentes podem estar imaturas. Conversão observada não é previsão de conversão final "
    "nem taxa de contratos assinados durante a semana.",
)

# Apresentação apenas. Paleta INSPIRADA na identidade visual do site do Banco Bari,
# com valores aproximados (não oficiais). Sem fontes ou recursos externos.
ESTILO = """/* ==========================================================
   Paleta INSPIRADA na referência visual do site do Banco Bari.
   Valores aproximados a partir de captura de tela — não são
   as cores oficiais da marca.
   ========================================================== */
:root {
    --canvas: #f2f5f9;
    --surface: #ffffff;
    --sunken: #f5f7fb;
    --line: #dde3ec;
    --line-strong: #7a879c;
    --ink: #0f1f3d;
    --muted: #55627a;
    --navy: #0b1f44;
    --on-navy: #ffffff;
    --on-navy-muted: #b9c6dd;
    --blue-vivid: #2e90ff;
    --blue: #0f5fd6;
    --blue-soft: #e8f0fd;
    --data-1: #34568f;
    --data-track: #e9eef5;
    --warn: #8a5a00;
    --warn-soft: #fdf3d8;
    --warn-line: #e2c26f;
    --critical: #b3261e;

    --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px;
    --s6: 24px; --s8: 32px; --s10: 40px;
    --r-sm: 4px; --r-md: 8px; --r-lg: 12px;
    --pad: 40px;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: var(--canvas);
    color: var(--ink);
    font: 15px/1.5 "Source Sans 3", "Segoe UI", system-ui, sans-serif;
}

main {
    max-width: 1180px;
    margin: var(--s8) auto;
    padding: 0 var(--pad) var(--s8);
    background: var(--surface);
    border-radius: var(--r-lg);
    box-shadow: 0 0 0 1px var(--line);
    overflow: hidden;
}

td, .kpi-valor, .barra-cabecalho strong, .periodo-datas, .meta-periodo dd {
    font-variant-numeric: tabular-nums;
}

/* ---------- 1. Cabeçalho ---------- */
.cabecalho {
    margin: 0 calc(-1 * var(--pad));
    padding: var(--s8) var(--pad) var(--s6);
    background: var(--navy);
    color: var(--on-navy);
    border-bottom: 3px solid var(--blue-vivid);
}

.selo {
    font-size: 12px;
    line-height: 16px;
    font-weight: 700;
    letter-spacing: .08em;
    color: var(--blue-vivid);
}

h1 {
    font-size: 30px;
    line-height: 36px;
    font-weight: 600;
    margin: var(--s1) 0 var(--s4);
}

.periodo {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s3) var(--s8);
    align-items: center;
}

.periodo-principal {
    border: 1px solid rgba(185, 198, 221, .45);
    border-radius: var(--r-md);
    padding: var(--s2) var(--s4);
}

.periodo-rotulo {
    font-size: 12px;
    font-weight: 600;
    color: var(--on-navy-muted);
}

.periodo-datas {
    font-size: 22px;
    line-height: 28px;
    font-weight: 700;
}

.meta-periodo {
    display: grid;
    grid-template-columns: auto auto;
    gap: 2px var(--s4);
    margin: 0;
    font-size: 13px;
    line-height: 19px;
}

.meta-periodo dt { color: var(--on-navy-muted); }
.meta-periodo dd { margin: 0; font-weight: 600; }

/* ---------- 2. Alertas dinâmicos (quando existirem) ---------- */
.alertas { margin-top: var(--s6); display: grid; gap: var(--s2); }

.alerta {
    display: flex;
    gap: var(--s3);
    align-items: baseline;
    padding: var(--s3) var(--s4);
    border: 1px solid var(--warn-line);
    border-radius: var(--r-md);
    background: var(--warn-soft);
    font-size: 14px;
    line-height: 21px;
}

.alerta-icone {
    flex: none;
    color: var(--warn);
    font-weight: 700;
}

.alerta p { margin: 0; }

.alerta strong { color: var(--warn); }

/* ---------- Zonas ---------- */
.zona-rotulo {
    display: flex;
    align-items: center;
    gap: var(--s3);
    margin: var(--s10) 0 var(--s4);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--muted);
}

.zona-rotulo::after {
    content: "";
    flex: 1;
    border-top: 1px solid var(--line);
}

.zona-rotulo .marca {
    padding: 2px var(--s2);
    border-radius: var(--r-sm);
    background: var(--blue-soft);
    color: var(--blue);
    letter-spacing: .02em;
}

.zona-rotulo .marca.fixa {
    background: var(--sunken);
    color: var(--muted);
    border: 1px solid var(--line);
}

/* ---------- 3. Filtros ---------- */
.filtros {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--s2) var(--s8);
    align-items: end;
    padding: var(--s4) var(--s6);
    border-radius: var(--r-md);
    background: var(--sunken);
    border: 1px solid var(--line);
}

.filtros h2 {
    grid-column: 1 / -1;
    margin: 0;
    font-size: 16px;
    line-height: 22px;
}

.filtros fieldset {
    border: 0;
    margin: 0;
    padding: 0;
    display: flex;
    gap: var(--s3);
    flex-wrap: wrap;
    align-items: end;
}

.filtros label {
    display: flex;
    flex-direction: column;
    gap: var(--s1);
    font-size: 13px;
    font-weight: 600;
}

.filtros select,
.filtros button {
    font: inherit;
    font-size: 14px;
    font-weight: 400;
    min-height: 40px;
    padding: 0 var(--s3);
    border: 1px solid var(--line-strong);
    border-radius: var(--r-md);
    background: var(--surface);
    color: var(--ink);
    max-width: 100%;
}

.filtros select { min-width: 200px; }

.filtros button {
    cursor: pointer;
    font-weight: 600;
    color: var(--blue);
    border-color: var(--blue);
}

.filtros fieldset:disabled select,
.filtros fieldset:disabled button { opacity: .55; cursor: not-allowed; }

.filtros p {
    margin: 0;
    font-size: 13px;
    line-height: 19px;
    color: var(--muted);
}

#situacao-filtros {
    color: var(--ink);
    font-weight: 600;
}

:focus-visible {
    outline: 3px solid var(--blue);
    outline-offset: 2px;
}

/* ---------- 4. KPIs ---------- */
.kpis {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--s4);
    margin-top: var(--s6);
}

.kpi-grupo h3 {
    margin: 0 0 var(--s2);
    font-size: 13px;
    line-height: 18px;
    font-weight: 700;
    color: var(--muted);
}

.kpi-linha { display: grid; gap: var(--s3); }
.kpi-grupo.volume .kpi-linha { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.kpi-grupo.valores .kpi-linha { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.kpi-grupo { display: grid; grid-template-columns: 150px 1fr; gap: var(--s4); align-items: center; }
.kpi-grupo h3 { margin: 0; }

.kpi {
    min-width: 0;
    padding: var(--s4);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--surface);
    display: flex;
    flex-direction: column;
    gap: var(--s1);
}

.kpi-label {
    font-size: 14px;
    line-height: 20px;
    font-weight: 600;
    color: var(--ink);
}

.kpi-valor {
    display: block;
    font-size: 34px;
    line-height: 40px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
}

.kpi-dinheiro { font-size: 28px; }

.kpi small { font-size: 13px; line-height: 18px; color: var(--muted); }

/* ---------- Seções e tabelas ---------- */
h2 {
    font-size: 19px;
    line-height: 26px;
    margin: var(--s8) 0 var(--s1);
}

.sub {
    margin: 0 0 var(--s4);
    font-size: 13px;
    line-height: 19px;
    color: var(--muted);
    max-width: 80ch;
}

.tabela { overflow-x: auto; }

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    line-height: 20px;
}

th, td {
    text-align: right;
    padding: 10px var(--s3);
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}

th:first-child, td:first-child {
    text-align: left;
    white-space: normal;
}

th {
    white-space: normal;
    font-size: 12px;
    line-height: 16px;
    font-weight: 700;
    color: var(--muted);
    border-bottom: 2px solid var(--line);
    vertical-align: bottom;
}

/* coluna "Semana selecionada" = a única que responde aos filtros */
#resumo-semanal th:nth-child(2),
#resumo-semanal td:nth-child(2) {
    background: var(--blue-soft);
}

#resumo-semanal th:nth-child(2) { color: var(--blue); }
#resumo-semanal td:nth-child(2) { font-weight: 700; }

/* ---------- 6. Perdas por etapa ---------- */
.perdas td:first-child { white-space: nowrap; }
.perdas {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--s8);
    align-items: start;
}

.grafico-perdas { margin: 0; }

.barra-item + .barra-item { margin-top: var(--s4); }

.barra-cabecalho {
    display: flex;
    justify-content: space-between;
    gap: var(--s4);
    margin-bottom: 6px;
    font-size: 14px;
    line-height: 20px;
}

.barra-cabecalho span { font-weight: 600; }
.barra-cabecalho strong { white-space: nowrap; }

.barra-trilho {
    width: 100%;
    height: 10px;
    overflow: hidden;
    border-radius: var(--r-sm);
    background: var(--data-track);
}

.barra-preenchimento {
    height: 100%;
    border-radius: inherit;
    background: var(--data-1);
}

.barra-item small {
    display: block;
    margin-top: var(--s1);
    font-size: 13px;
    color: var(--muted);
}

.estado-vazio {
    padding: var(--s4);
    border: 1px dashed var(--line-strong);
    border-radius: var(--r-md);
    background: var(--sunken);
}

.estado-vazio p { margin: 2px 0 0; color: var(--muted); }

/* ---------- 8. Metodologia ---------- */
.metodologia {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--s8);
    margin-top: var(--s10);
    padding-top: var(--s6);
    border-top: 1px solid var(--line);
}

.aviso {
    padding: var(--s4) var(--s6);
    border-radius: var(--r-md);
    background: var(--blue-soft);
    border: 1px solid #c9dbf6;
    font-size: 14px;
    line-height: 21px;
}

.aviso > strong { font-size: 16px; line-height: 22px; }
.aviso ul { margin: var(--s2) 0 0; padding-left: 18px; }
.aviso li + li { margin-top: var(--s2); }

.definicoes h2 { margin-top: 0; font-size: 16px; line-height: 22px; }
.definicoes p { font-size: 14px; line-height: 21px; margin: var(--s2) 0 0; }

footer {
    margin-top: var(--s8);
    padding-top: var(--s4);
    border-top: 1px solid var(--line);
    font-size: 12px;
    line-height: 18px;
    color: var(--muted);
}

/* ---------- Responsivo ---------- */
@media (max-width: 1000px) {
    .kpis { grid-template-columns: 1fr; }
    .perdas, .metodologia { grid-template-columns: 1fr; gap: var(--s6); }
    .kpi-grupo { grid-template-columns: 1fr; gap: var(--s2); }
    .filtros { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
    :root { --pad: 16px; }
    main { margin: 0; border-radius: 0; box-shadow: none; }
    .cabecalho { padding-top: var(--s6); }
    h1 { font-size: 24px; line-height: 30px; }
    .periodo-datas { font-size: 19px; }
    .filtros { padding: var(--s4); }
    .filtros label, .filtros select, .filtros button { width: 100%; }
    .kpi-grupo.volume .kpi-linha { grid-template-columns: 1fr 1fr; }
    .kpi-grupo.volume .kpi:last-child { grid-column: 1 / -1; }
    .kpi-grupo.valores .kpi-linha { grid-template-columns: 1fr; }
    .kpi-valor { font-size: 30px; line-height: 36px; }
    .kpi-dinheiro { font-size: 24px; }
    .barra-cabecalho { flex-direction: column; gap: 0; }
    .zona-rotulo { flex-wrap: wrap; gap: var(--s2); }
    .zona-rotulo::after { display: none; }
    .zona-rotulo .marca { white-space: nowrap; }
    /* primeira coluna fixa ao rolar a tabela */
    .tabela td:first-child, .tabela th:first-child {
        position: sticky; left: 0; background: var(--surface);
        min-width: 140px; box-shadow: 1px 0 0 var(--line);
    }
    .tabela { margin: 0 calc(-1 * var(--pad)); padding: 0 var(--pad); }
}

/* ---------- Impressão / PDF A4 ---------- */
@page { size: A4; margin: 14mm 12mm; }

@media print {
    :root { --pad: 0px; }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { background: #fff; font-size: 10.5pt; }
    main { margin: 0; max-width: none; box-shadow: none; border-radius: 0; overflow: visible; }
    .cabecalho { background: none; color: var(--ink); padding: 0 0 var(--s3); border-bottom: 3px solid var(--navy); }
    .selo { color: var(--blue); }
    .periodo-principal { border-color: var(--line); }
    .periodo-rotulo, .meta-periodo dt { color: var(--muted); }
    /* controles somem; o estado dos filtros (texto que o JS já atualiza) permanece */
    .filtros h2, .filtros fieldset, .filtros noscript { display: none; }
    .filtros { display: block; padding: var(--s2) var(--s3); background: none; }
    .filtros p + p { margin-top: var(--s1); }
    .kpis { gap: var(--s2); }
    .kpi-grupo { grid-template-columns: 110px 1fr; gap: var(--s2); }
    .kpi { padding: var(--s2) var(--s3); }
    .kpi-valor { font-size: 22px; line-height: 28px; }
    .kpi-dinheiro { font-size: 20px; }
    .perdas { grid-template-columns: 1fr 1fr; gap: var(--s6); }
    .metodologia { grid-template-columns: 1fr 1fr; }
    th, td { padding: 6px var(--s2); }
    .kpi, .alerta, .barra-item, tr, .aviso, .estado-vazio { break-inside: avoid; }
    h2, .zona-rotulo { break-after: avoid; }
    .perdas, .metodologia { break-inside: avoid; }
    .tabela { overflow: visible; }
}
"""


def tabela(cabecalhos: list[str], linhas: list[list], id_tabela: str | None = None) -> str:
    head = "".join(f"<th scope='col'>{escape(str(c))}</th>" for c in cabecalhos)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in linha) + "</tr>" for linha in linhas)
    identificador = f' id="{escape(id_tabela, quote=True)}"' if id_tabela else ""
    return f"<div class='tabela'><table{identificador}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def grafico_perdas(perdas: pd.DataFrame) -> str:
    """Cria barras horizontais proporcionais ao valor não contratado."""
    if perdas.empty:
        return ""

    ordenadas = perdas.sort_values(
        "valor",
        ascending=False,
    )

    maior_valor = float(
        ordenadas["valor"].max()
    )

    barras = []

    for etapa, linha in ordenadas.iterrows():
        valor = float(linha.valor)
        propostas = int(linha.propostas)

        largura = (
            valor / maior_valor * 100
            if maior_valor > 0
            else 0
        )

        nome_etapa = ETAPAS[etapa]
        valor_formatado = numero(valor, 2)

        plural_proposta = (
            "propostas"
            if propostas != 1
            else "proposta"
        )

        plural_contratada = (
            "contratadas"
            if propostas != 1
            else "contratada"
        )

        barras.append(
            f"""
            <div class="barra-item">

                <div class="barra-cabecalho">
                    <span>
                        {etapa} — {escape(nome_etapa)}
                    </span>

                    <strong>
                        R$ {valor_formatado}
                    </strong>
                </div>

                <div
                    class="barra-trilho"
                    role="img"
                    aria-label="{escape(nome_etapa)}: R$ {valor_formatado}"
                >
                    <div
                        class="barra-preenchimento"
                        style="width:{largura:.2f}%"
                    ></div>
                </div>

                <small>
                    {numero(propostas)}
                    {plural_proposta}
                    não {plural_contratada}
                </small>

            </div>
            """
        )

    return (
        '<div class="grafico-perdas">'
        + "".join(barras)
        + "</div>"
    )


def gerar_html(m: dict, fonte: str) -> str:
    dados_filtros = json.dumps(
        m["filtros"],
        ensure_ascii=True,
        allow_nan=False,
    ).replace("<", "\\u003c")

    opcoes_canal = "".join(
        f'<option value="{i}">{escape(canal)}</option>'
        for i, canal in enumerate(
            m["filtros"]["canais"],
            1,
        )
    )

    opcoes_etapa = "".join(
        f'<option value="{i}">'
        f'{etapa} — {escape(nome)}'
        f"</option>"
        for i, (etapa, nome) in enumerate(
            ETAPAS.items(),
            1,
        )
    )

    intervalo = (
        f"{m['inicio']:%d/%m/%Y} a "
        f"{m['fim'] - timedelta(days=1):%d/%m/%Y}"
    )

    cards = f"""
    <section class="kpis" aria-label="Indicadores da semana selecionada">

      <div class="kpi-grupo volume">
        <h3>Volume e conversão</h3>
        <div class="kpi-linha">

        <article class="kpi">
            <span class="kpi-label">Propostas</span>
            <strong class="kpi-valor" id="kpi-total">
                {numero(m["semana"]["total"])}
            </strong>
            <small>recebidas na coorte</small>
        </article>

        <article class="kpi">
            <span class="kpi-label">Contratadas</span>
            <strong class="kpi-valor" id="kpi-contratadas">
                {numero(m["semana"]["contratadas"])}
            </strong>
            <small>na coorte semanal</small>
        </article>

        <article class="kpi">
            <span class="kpi-label">Conversão observada</span>
            <strong class="kpi-valor" id="kpi-conversao">
                {percentual(m["semana"]["conversao"])}
            </strong>
            <small>contratadas / propostas</small>
        </article>

        </div>
      </div>

      <div class="kpi-grupo valores">
        <h3>Valores</h3>
        <div class="kpi-linha">

        <article class="kpi kpi-largo">
            <span class="kpi-label">Crédito solicitado</span>
            <strong class="kpi-valor kpi-dinheiro" id="kpi-solicitado">
                R$ {numero(m["semana"]["solicitado"], 2)}
            </strong>
            <small>volume da coorte</small>
        </article>

        <article class="kpi kpi-largo">
            <span class="kpi-label">Não contratado</span>
            <strong class="kpi-valor kpi-dinheiro" id="kpi-perdido">
                R$ {numero(m["semana"]["perdido"], 2)}
            </strong>
            <small>valor solicitado</small>
        </article>

        </div>
      </div>

    </section>
    """

    resumo = tabela(
        [
            "Indicador",
            "Semana selecionada",
            "Semana anterior",
            "Acumulado até domingo",
        ],
        [
            [rotulo]
            + [
                formato(m[grupo][chave])
                for grupo in (
                    "semana",
                    "anterior",
                    "historico",
                )
            ]
            for rotulo, chave, formato in [
                (
                    "Propostas recebidas",
                    "total",
                    numero,
                ),
                (
                    "Contratadas na coorte",
                    "contratadas",
                    numero,
                ),
                (
                    "Conversão observada",
                    "conversao",
                    percentual,
                ),
                (
                    "Crédito solicitado (R$)",
                    "solicitado",
                    lambda v: numero(v, 2),
                ),
                (
                    "Valor solicitado não contratado (R$)",
                    "perdido",
                    lambda v: numero(v, 2),
                ),
            ]
        ],
        id_tabela="resumo-semanal",
    )

    perdas = tabela(
        [
            "Última etapa alcançada",
            "Propostas não contratadas",
            "Valor solicitado (R$)",
        ],
        [
            [
                f"{etapa} — {ETAPAS[etapa]}",
                numero(linha.propostas),
                numero(linha.valor, 2),
            ]
            for etapa, linha in (
                m["perdas"]
                .sort_values(
                    "valor",
                    ascending=False,
                )
                .iterrows()
            )
        ],
    )

    grafico = grafico_perdas(
        m["perdas"]
    )

    canais = tabela(
        [
            "Canal",
            "Propostas",
            "Contratadas",
            "Conversão observada",
        ],
        [
            [
                c["canal"],
                numero(c["total"]),
                numero(c["contratadas"]),
                percentual(c["conversao"]),
            ]
            for c in m["canais"]
        ],
    )

    # Mesmos textos e mesma regra de calcular(); muda só o lugar de exibição:
    # notas permanentes em "Como interpretar", alertas dinâmicos no topo.
    avisos = "".join(
        f"<li>{escape(aviso)}</li>"
        for aviso in m["avisos"]
        if aviso in AVISOS_METODOLOGICOS
    )

    alertas_dinamicos = [
        aviso
        for aviso in m["avisos"]
        if aviso not in AVISOS_METODOLOGICOS
    ]

    alertas = (
        '<section class="alertas" aria-label="Alertas do período">'
        + "".join(
            '<div class="alerta">'
            '<span class="alerta-icone" aria-hidden="true">⚠</span>'
            f"<p><strong>Atenção:</strong> {escape(aviso)}</p>"
            "</div>"
            for aviso in alertas_dinamicos
        )
        + "</section>"
        if alertas_dinamicos
        else ""
    )

    sem_perdas = (
        "<div class='estado-vazio'>"
        "<strong>Sem valor não contratado nesta coorte.</strong>"
        "<p>Não há propostas não contratadas para apresentar neste período.</p>"
        "</div>"
        if m["perdas"].empty
        else '<div class="perdas">' + grafico + perdas + "</div>"
    )

    sem_canais = (
        "<div class='estado-vazio'>"
        "<strong>Sem propostas na semana.</strong>"
        "<p>Não há dados suficientes para segmentar o período por canal.</p>"
        "</div>"
        if not m["canais"]
        else canais
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>Bari — Relatório semanal | {intervalo}</title>

<style>
{ESTILO}
</style>
</head>

<body>

<main>

<header class="cabecalho">

<div class="selo">
    BARI · AI &amp; DATA LAB · DADOS SINTÉTICOS
</div>

<h1>Relatório semanal do funil</h1>

<div class="periodo">
    <div class="periodo-principal">
        <div class="periodo-rotulo">Entradas de</div>
        <div class="periodo-datas">{intervalo}</div>
    </div>
    <dl class="meta-periodo">
        <dt>Referência</dt>
        <dd>{m['referencia']:%d/%m/%Y}</dd>
        <dt>Semana anterior</dt>
        <dd>{m['inicio'] - timedelta(days=7):%d/%m/%Y} a {m['inicio'] - timedelta(days=1):%d/%m/%Y}</dd>
        <dt>Entradas disponíveis</dt>
        <dd>{m['primeira_entrada']:%d/%m/%Y} a {m['ultima_entrada']:%d/%m/%Y}</dd>
    </dl>
</div>

</header>

{alertas}

<div class="zona-rotulo">
    <span>Semana selecionada</span>
    <span class="marca">responde aos filtros</span>
</div>

<section
    class="filtros"
    aria-labelledby="titulo-filtros"
>

<h2 id="titulo-filtros">
    Explorar a semana
</h2>

<fieldset
    id="controles-filtros"
    disabled
    aria-label="Filtros da coorte semanal"
>

<label for="filtro-canal">
    Canal de origem

    <select id="filtro-canal">
        <option value="0">Todos</option>
        {opcoes_canal}
    </select>
</label>

<label for="filtro-etapa">
    Última etapa alcançada

    <select id="filtro-etapa">
        <option value="0">Todas</option>
        {opcoes_etapa}
    </select>
</label>

<button
    id="limpar-filtros"
    type="button"
>
    Limpar filtros
</button>

</fieldset>

<div class="filtros-estado">

<p
    id="situacao-filtros"
    role="status"
    aria-live="polite"
>
    Sem filtros: indicadores da semana completa.
</p>

<p>
    Os filtros afetam os indicadores da semana selecionada.
    Semana anterior, acumulado e tabelas analíticas abaixo
    permanecem sem filtros.
</p>

<noscript>
<p>
    Ative o JavaScript para explorar os filtros.
    Os valores exibidos representam a semana completa.
</p>
</noscript>

</div>

</section>

{cards}

<h2>Comparação do período</h2>

<p class="sub">
    Semana anterior:
    {m['inicio'] - timedelta(days=7):%d/%m/%Y}
    a
    {m['inicio'] - timedelta(days=1):%d/%m/%Y}.
    O acumulado considera todas as entradas anteriores a
    {m['fim']:%d/%m/%Y}.
</p>

{resumo}

<div class="zona-rotulo">
    <span>Semana completa</span>
    <span class="marca fixa">sem filtros</span>
</div>

<h2>
    Onde se concentra o valor não contratado
</h2>

<p class="sub">
    Coorte da semana completa — sem filtros.
    O comprimento das barras é relativo à etapa de maior valor
    não contratado no período.
</p>

{sem_perdas}

<h2>
    Desempenho por canal de origem
</h2>

<p class="sub">
    Coorte da semana completa — sem filtros.
</p>

{sem_canais}

<div class="metodologia">

<section class="aviso">

<strong>
    Como interpretar este relatório
</strong>

<ul>
    {avisos}
</ul>

</section>

<section class="definicoes">

<h2>Definições e limites</h2>

<p>
    Conversão = propostas com status Contratada ÷ total
    de propostas da coorte.
    Valor perdido = soma do valor solicitado nas propostas
    com status diferente de Contratada, conforme a Parte 1.
    Representa principal solicitado não contratado,
    não receita ou prejuízo contábil.
    As perdas são atribuídas à última etapa alcançada,
    não à data em que ocorreram.
</p>

<p>
    O arquivo não contém histórico de status nem data de
    extração. A última entrada não comprova a atualização
    do arquivo. Comparações semanais são descritivas
    e não demonstram causalidade.
</p>

</section>

</div>

<footer>
    Fonte: {escape(fonte)}
    · {numero(m['linhas'])} registros tratados,
    sem descarte.
    <br>
    Entradas disponíveis:
    {m['primeira_entrada']:%d/%m/%Y}
    a
    {m['ultima_entrada']:%d/%m/%Y}.
    <br>
    Gerado pela rotina da Parte 2,
    reutilizando o tratamento da Parte 1.
</footer>

</main>

<script
    type="application/json"
    id="dados-filtros"
>
{dados_filtros}
</script>

<script id="interacao-filtros">
{SCRIPT_FILTROS}
</script>

</body>
</html>"""


def gravar_html(destino: Path, conteudo: str) -> None:
    """Só substitui a saída anterior depois de escrever o HTML inteiro."""
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destino.parent,
                                         suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
        os.replace(temporario, destino)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=RAIZ / "dados_brutos/Propostas_credito.csv")
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parent / "saidas",
                        help="Diretório para HTML e log. Caminhos relativos partem da raiz do repositório.")
    parser.add_argument("--data-referencia", type=date.fromisoformat, default=date.today(), metavar="AAAA-MM-DD")
    args = parser.parse_args(argv)
    entrada = (RAIZ / args.entrada).resolve()
    saida = (RAIZ / args.saida).resolve()
    if saida.is_relative_to(RAIZ / "dados_brutos"):
        parser.error("A saída não pode ficar dentro de dados_brutos.")
    inicio, fim = periodo(args.data_referencia)
    nome = f"relatorio_{inicio.isoformat()}_{(fim - timedelta(days=1)).isoformat()}"
    handlers = []
    LOG.setLevel(logging.INFO)
    LOG.propagate = False
    try:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        LOG.addHandler(console)
        handlers.append(console)
        saida.mkdir(parents=True, exist_ok=True)
        arquivo_log = logging.FileHandler(saida / f"{nome}.log", encoding="utf-8")
        arquivo_log.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOG.addHandler(arquivo_log)
        handlers.append(arquivo_log)
        LOG.info("INÍCIO referência=%s entrada=%s", args.data_referencia, entrada)
        dados = ler_e_tratar(entrada)
        metricas = calcular(dados, args.data_referencia)
        for aviso in metricas["avisos"]:
            LOG.warning(aviso)
        destino = saida / f"{nome}.html"
        gravar_html(destino, gerar_html(metricas, entrada.name))
        LOG.info("SUCESSO relatório=%s propostas_semana=%d", destino, metricas["semana"]["total"])
        return 0
    except (OSError, ValueError, pd.errors.EmptyDataError) as exc:
        LOG.error("FALHA: %s. Nenhum relatório novo foi publicado; eventual HTML anterior permanece inalterado.", exc)
        return 1
    except Exception:
        LOG.exception("FALHA inesperada; nenhum relatório novo foi publicado.")
        return 1
    finally:
        for handler in handlers:
            LOG.removeHandler(handler)
            handler.close()


if __name__ == "__main__":
    sys.exit(main())
