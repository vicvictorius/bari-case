"""
Tratamento de propostas_credito.csv
Aplica as decisões documentadas em registro_tratamento.md.
Gera propostas_credito_tratado.csv como saída.
"""
import pandas as pd
import numpy as np

RAW_PATH = "../propostas_credito.csv"
OUT_PATH = "propostas_credito_tratado.csv"

df = pd.read_csv(RAW_PATH, encoding="utf-8-sig", dtype=str)
n_inicial = len(df)

# ---------------------------------------------------------------
# 1. valor_imovel: remover prefixo "R$ " (3 linhas) e converter p/ float
# ---------------------------------------------------------------
df["valor_imovel"] = (
    df["valor_imovel"].str.replace("R$", "", regex=False).str.strip()
)
df["valor_imovel"] = pd.to_numeric(df["valor_imovel"], errors="raise")
df["valor_solicitado"] = pd.to_numeric(df["valor_solicitado"], errors="raise")

# ---------------------------------------------------------------
# 2. data_entrada: normalizar dd/mm/yyyy -> yyyy-mm-dd (3 linhas)
# ---------------------------------------------------------------
def normaliza_data(x):
    if pd.isna(x) or x == "":
        return x
    if "/" in x:
        d, m, y = x.split("/")
        return f"{y}-{m}-{d}"
    return x

df["data_entrada"] = df["data_entrada"].apply(normaliza_data)
df["data_entrada"] = pd.to_datetime(df["data_entrada"], format="%Y-%m-%d")
df["data_assinatura_contrato"] = pd.to_datetime(
    df["data_assinatura_contrato"], format="%Y-%m-%d", errors="coerce"
)

# ---------------------------------------------------------------
# 3. canal_origem: normalizar capitalização (4 linhas)
# ---------------------------------------------------------------
mapa_canal = {
    "mídia paga": "Mídia paga",
    "indicação": "Indicação",
    "organico": "Organico",
}
df["canal_origem"] = df["canal_origem"].replace(mapa_canal)

# ---------------------------------------------------------------
# 4. etapa_max_funil: corrigir PR-000081 (7 -> 6), erro de digitação
#    confirmado por consistência com status_final == Contratada
# ---------------------------------------------------------------
df["etapa_max_funil"] = pd.to_numeric(df["etapa_max_funil"], errors="raise")
mask_81 = df["id_proposta"] == "PR-000081"
assert (df.loc[mask_81, "etapa_max_funil"] == 7).all(), "PR-000081 não encontrada ou valor mudou"
df.loc[mask_81, "etapa_max_funil"] = 6

# ---------------------------------------------------------------
# 5. idade_cliente: PR-000079 (14 anos) -> nula/inválida, linha mantida
# ---------------------------------------------------------------
df["idade_cliente"] = pd.to_numeric(df["idade_cliente"], errors="raise")
mask_79 = df["id_proposta"] == "PR-000079"
assert (df.loc[mask_79, "idade_cliente"] == 14).all(), "PR-000079 não encontrada ou valor mudou"
df.loc[mask_79, "idade_cliente"] = np.nan

# ---------------------------------------------------------------
# 6. ltv: coluna não existe no CSV bruto, calculada conforme dicionário
#    de dados: ltv = valor_solicitado / valor_imovel
# ---------------------------------------------------------------
df["ltv"] = (df["valor_solicitado"] / df["valor_imovel"]).round(4)

# ---------------------------------------------------------------
# demais colunas numéricas (sem problemas identificados no profiling)
# ---------------------------------------------------------------
for c in ["prazo_meses", "score_credito", "renda_mensal_declarada",
          "flag_cliente_recorrente", "tempo_analise_dias", "taxa_juros_aa"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ---------------------------------------------------------------
# checagens finais
# ---------------------------------------------------------------
assert len(df) == n_inicial, "Nenhuma linha deveria ter sido descartada"
assert df["valor_imovel"].dtype == float
assert df["ltv"].between(0, 1.5).all(), "ltv fora de faixa plausível após cálculo"

df.to_csv(OUT_PATH, index=False)
print(f"OK — {len(df)} linhas mantidas (igual ao bruto: {n_inicial}).")
print(f"Salvo em {OUT_PATH}")
print(df[["id_proposta", "valor_imovel", "data_entrada", "canal_origem",
          "etapa_max_funil", "idade_cliente", "ltv"]].head(3))