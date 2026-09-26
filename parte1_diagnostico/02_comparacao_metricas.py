"""
Comparação das definições candidatas de métricas operacionais.
Não decide nada — só gera os números para decisão informada.
"""
import pandas as pd

df = pd.read_csv("propostas_credito_tratado.csv", parse_dates=["data_entrada", "data_assinatura_contrato"])

TOTAL = len(df)
CONTRATADAS = (df["status_final"] == "Contratada").sum()

print("=" * 70)
print("MÉTRICA 1 — CONVERSÃO: qual denominador?")
print("=" * 70)

conv_total = CONTRATADAS / TOTAL
print(f"\n[A] Contratada / total de propostas")
print(f"    {CONTRATADAS} / {TOTAL} = {conv_total:.2%}")

pos_etapa1 = df[df["etapa_max_funil"] > 1]
conv_pos_etapa1 = CONTRATADAS / len(pos_etapa1)
print(f"\n[B] Contratada / propostas que passaram da etapa 1 (Simulação)")
print(f"    etapa_max_funil == 1 (ficaram só na simulação): {(df['etapa_max_funil']==1).sum()} propostas")
print(f"    {CONTRATADAS} / {len(pos_etapa1)} = {conv_pos_etapa1:.2%}")

print(f"\nDiferença: {conv_pos_etapa1 - conv_total:.2%} pontos percentuais")

print("\n" + "=" * 70)
print("MÉTRICA 2 — DINHEIRO PERDIDO POR ETAPA: qual base de valor?")
print("=" * 70)

perdidas = df[df["status_final"] != "Contratada"].copy()

# taxa média dos contratos fechados, para estimar receita potencial
# de quem não contratou (premissa a declarar)
taxa_media = df.loc[df["status_final"] == "Contratada", "taxa_juros_aa"].mean()
print(f"\nTaxa média de contratos fechados: {taxa_media:.2f}% a.m. (usada como estimativa p/ perdidas)")

# aproximação simples de receita potencial: valor_solicitado * taxa_juros_aa(%) * prazo_meses
# (juros simples sobre o principal ao longo do prazo, só para efeito de ranking de impacto —
#  não é um cálculo financeiro de amortização real)
perdidas["receita_potencial_estimada"] = (
    perdidas["valor_solicitado"] * (taxa_media / 100) * perdidas["prazo_meses"]
)

print("\n[A] Base = valor_solicitado (principal pedido)")
resumo_a = perdidas.groupby("etapa_max_funil")["valor_solicitado"].agg(["count", "sum"]).round(0)
resumo_a["sum_R$_mi"] = (resumo_a["sum"] / 1e6).round(1)
print(resumo_a[["count", "sum_R$_mi"]])
print(f"TOTAL perdido (valor_solicitado): R$ {perdidas['valor_solicitado'].sum()/1e6:.1f} milhões")

print("\n[B] Base = valor_solicitado × taxa_juros_aa estimada × prazo (receita potencial)")
resumo_b = perdidas.groupby("etapa_max_funil")["receita_potencial_estimada"].agg(["count", "sum"]).round(0)
resumo_b["sum_R$_mi"] = (resumo_b["sum"] / 1e6).round(1)
print(resumo_b[["count", "sum_R$_mi"]])
print(f"TOTAL perdido (receita potencial estimada): R$ {perdidas['receita_potencial_estimada'].sum()/1e6:.1f} milhões")

print("\n--- Ranking de etapas mais 'caras' muda entre A e B? ---")
rank_a = resumo_a["sum"].sort_values(ascending=False).index.tolist()
rank_b = resumo_b["sum"].sort_values(ascending=False).index.tolist()
print("Ranking A (valor_solicitado):", rank_a)
print("Ranking B (receita potencial):", rank_b)
print("Mesmo ranking?", rank_a == rank_b)