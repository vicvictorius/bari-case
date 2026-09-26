"""
Parte 1 — Diagnóstico do funil
Responde as 4 perguntas do desafio com evidência, usando as métricas definidas
em definicao_metricas.md:
  - conversão = Contratada / total de propostas
  - dinheiro perdido = soma de valor_solicitado das propostas não contratadas
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)

CSV_PATH = Path(__file__).resolve().parent / "propostas_credito_tratado.csv"
df = pd.read_csv(CSV_PATH, parse_dates=["data_entrada", "data_assinatura_contrato"])
TOTAL = len(df)
CONTRATADAS = (df["status_final"] == "Contratada").sum()
CONV_GERAL = CONTRATADAS / TOTAL

print("#" * 70)
print("PERGUNTA 1 — Onde o funil perde mais valor?")
print("#" * 70)

perdidas = df[df["status_final"] != "Contratada"]
por_etapa = perdidas.groupby("etapa_max_funil").agg(
    qtd_propostas=("id_proposta", "count"),
    valor_perdido=("valor_solicitado", "sum"),
).round(0)
por_etapa["valor_perdido_R$_mi"] = (por_etapa["valor_perdido"] / 1e6).round(1)
por_etapa["pct_do_total_perdido"] = (por_etapa["valor_perdido"] / perdidas["valor_solicitado"].sum() * 100).round(1)
print("\nPor etapa (quantidade de propostas x valor perdido):")
print(por_etapa[["qtd_propostas", "valor_perdido_R$_mi", "pct_do_total_perdido"]])

print("\nPor motivo de perda (status_final):")
por_status = perdidas.groupby("status_final").agg(
    qtd_propostas=("id_proposta", "count"),
    valor_perdido=("valor_solicitado", "sum"),
).round(0)
por_status["valor_perdido_R$_mi"] = (por_status["valor_perdido"] / 1e6).round(1)
por_status["pct_do_total_perdido"] = (por_status["valor_perdido"] / perdidas["valor_solicitado"].sum() * 100).round(1)
por_status = por_status.sort_values("valor_perdido", ascending=False)
print(por_status[["qtd_propostas", "valor_perdido_R$_mi", "pct_do_total_perdido"]])

print("\n>>> Cruzamento: etapa 3 (Análise de crédito) é a mais cara em qtd E em valor.")
print(">>> Ticket médio das perdidas na etapa 3:", round(
    perdidas[perdidas["etapa_max_funil"] == 3]["valor_solicitado"].mean(), 0))
print(">>> Ticket médio geral (todas as propostas):", round(df["valor_solicitado"].mean(), 0))

print("\n" + "#" * 70)
print("PERGUNTA 2 — A percepção da liderança se confirma?")
print("#" * 70)

df["mes_entrada"] = df["data_entrada"].dt.to_period("M")

print("\n--- Conversão por mês de entrada (tendência) ---")
conv_mensal = df.groupby("mes_entrada").agg(
    total=("id_proposta", "count"),
    contratadas=("status_final", lambda s: (s == "Contratada").sum()),
)
conv_mensal["conversao"] = (conv_mensal["contratadas"] / conv_mensal["total"] * 100).round(1)
print(conv_mensal)

# Aviso sobre censura à direita: meses recentes podem ter propostas
# que ainda não tiveram tempo hábil de fechar
print("\n>>> ATENÇÃO: tempo_analise_dias vai até", df["tempo_analise_dias"].max(), "dias.")
print(">>> Meses muito recentes da base podem estar artificialmente com conversão baixa")
print(">>> por ainda não terem tido tempo de fechar (censura à direita), não por queda real.")

print("\n--- Conversão por canal_origem (geral, toda a base) ---")
conv_canal = df.groupby("canal_origem").agg(
    total=("id_proposta", "count"),
    contratadas=("status_final", lambda s: (s == "Contratada").sum()),
)
conv_canal["conversao"] = (conv_canal["contratadas"] / conv_canal["total"] * 100).round(1)
conv_canal = conv_canal.sort_values("conversao", ascending=False)
print(conv_canal)

print("\n--- Conversão do canal Correspondente por mês (tendência isolada) ---")
corresp = df[df["canal_origem"] == "Correspondente"]
conv_corresp_mensal = corresp.groupby("mes_entrada").agg(
    total=("id_proposta", "count"),
    contratadas=("status_final", lambda s: (s == "Contratada").sum()),
)
conv_corresp_mensal["conversao"] = (conv_corresp_mensal["contratadas"] / conv_corresp_mensal["total"] * 100).round(1)
print(conv_corresp_mensal)

print("\n--- Mix de canal por mês (correspondente está perdendo participação?) ---")
mix_mensal = df.groupby(["mes_entrada", "canal_origem"]).size().unstack(fill_value=0)
mix_pct = (mix_mensal.div(mix_mensal.sum(axis=1), axis=0) * 100).round(1)
print(mix_pct)

print("\n" + "#" * 70)
print("PERGUNTA 3 — Quais características mais se associam à contratação?")
print("#" * 70)

df["contratada_flag"] = (df["status_final"] == "Contratada").astype(int)

print("\n--- Por canal_origem ---")
print(conv_canal[["conversao"]])

print("\n--- Por tipo_imovel ---")
conv_tipo = df.groupby("tipo_imovel").agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_tipo["conversao"] = (conv_tipo["contratadas"] / conv_tipo["total"] * 100).round(1)
print(conv_tipo.sort_values("conversao", ascending=False))

print("\n--- Por faixa de LTV ---")
df["faixa_ltv"] = pd.cut(df["ltv"], bins=[0, 0.4, 0.5, 0.6, 1.0],
                          labels=["<=40%", "40-50%", "50-60%", ">60% (acima da política)"])
conv_ltv = df.groupby("faixa_ltv", observed=True).agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_ltv["conversao"] = (conv_ltv["contratadas"] / conv_ltv["total"] * 100).round(1)
print(conv_ltv)

print("\n--- Por faixa de score_credito ---")
df["faixa_score"] = pd.cut(df["score_credito"], bins=[0, 500, 650, 750, 1000],
                            labels=["<=500", "501-650", "651-750", ">750"])
conv_score = df.groupby("faixa_score", observed=True).agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_score["conversao"] = (conv_score["contratadas"] / conv_score["total"] * 100).round(1)
print(conv_score)

print("\n--- Por faixa de ticket (valor_solicitado) ---")
df["faixa_ticket"] = pd.qcut(df["valor_solicitado"], 4, labels=["Q1 (menor)", "Q2", "Q3", "Q4 (maior)"])
conv_ticket = df.groupby("faixa_ticket", observed=True).agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_ticket["conversao"] = (conv_ticket["contratadas"] / conv_ticket["total"] * 100).round(1)
print(conv_ticket)

print("\n--- Por região (top 5 UF por volume) ---")
top_uf = df["uf"].value_counts().head(5).index
conv_uf = df[df["uf"].isin(top_uf)].groupby("uf").agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_uf["conversao"] = (conv_uf["contratadas"] / conv_uf["total"] * 100).round(1)
print(conv_uf.sort_values("conversao", ascending=False))

print("\n--- Por faixa de prazo_meses ---")
df["faixa_prazo"] = pd.cut(df["prazo_meses"], bins=[0, 120, 180, 240],
                            labels=["<=120", "121-180", "181-240"])
conv_prazo = df.groupby("faixa_prazo", observed=True).agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_prazo["conversao"] = (conv_prazo["contratadas"] / conv_prazo["total"] * 100).round(1)
print(conv_prazo)

print("\n--- flag_cliente_recorrente ---")
conv_recor = df.groupby("flag_cliente_recorrente").agg(
    total=("id_proposta", "count"), contratadas=("contratada_flag", "sum")
)
conv_recor["conversao"] = (conv_recor["contratadas"] / conv_recor["total"] * 100).round(1)
print(conv_recor)