"""
Profiling bruto de propostas_credito.csv
Objetivo: mapear a sujeira dos dados ANTES de qualquer tratamento.
Nada aqui decide nada ainda — só descreve o que existe.
"""
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)

df = pd.read_csv("../propostas_credito.csv", encoding="utf-8-sig", dtype=str)
# Profiling bruto: lemos tudo como string de propósito, para não deixar o
# pandas "resolver" silenciosamente problemas de formato (ex: "R$ 574857.06").
# Conversões numéricas abaixo são só para inspeção, não é o tratamento final.
df["valor_imovel_num"] = pd.to_numeric(
    df["valor_imovel"].str.replace("R$", "", regex=False).str.strip(), errors="coerce"
)
df["valor_solicitado_num"] = pd.to_numeric(df["valor_solicitado"], errors="coerce")
for c in ["prazo_meses", "score_credito", "idade_cliente", "renda_mensal_declarada",
          "flag_cliente_recorrente", "etapa_max_funil", "tempo_analise_dias", "taxa_juros_aa"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

print("=" * 70)
print("SHAPE")
print("=" * 70)
print(df.shape)

print("\n" + "=" * 70)
print("DTYPES (como o pandas leu, sem forçar nada)")
print("=" * 70)
print(df.dtypes)

print("\n" + "=" * 70)
print("NULOS por coluna (contagem e %)")
print("=" * 70)
nulls = df.isnull().sum()
pct = (nulls / len(df) * 100).round(2)
print(pd.DataFrame({"nulos": nulls, "pct": pct}).sort_values("nulos", ascending=False))

print("\n" + "=" * 70)
print("DUPLICATAS")
print("=" * 70)
print("id_proposta duplicado:", df["id_proposta"].duplicated().sum())
print("linhas 100% duplicadas:", df.duplicated().sum())

print("\n" + "=" * 70)
print("id_proposta — formato e continuidade")
print("=" * 70)
print(df["id_proposta"].head())
print("valores únicos:", df["id_proposta"].nunique(), "de", len(df))

print("\n" + "=" * 70)
print("canal_origem — valores únicos")
print("=" * 70)
print(df["canal_origem"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("tipo_imovel — valores únicos")
print("=" * 70)
print(df["tipo_imovel"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("status_final — valores únicos")
print("=" * 70)
print(df["status_final"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("etapa_max_funil — valores únicos")
print("=" * 70)
print(df["etapa_max_funil"].value_counts(dropna=False).sort_index())

print("\n" + "=" * 70)
print("uf — valores únicos")
print("=" * 70)
print(df["uf"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("flag_cliente_recorrente — valores únicos")
print("=" * 70)
print(df["flag_cliente_recorrente"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("Estatísticas descritivas — colunas numéricas")
print("=" * 70)
num_cols = ["valor_imovel_num", "valor_solicitado_num", "prazo_meses", "score_credito",
            "idade_cliente", "renda_mensal_declarada", "tempo_analise_dias", "taxa_juros_aa"]
print(df[num_cols].describe())

print("\n" + "=" * 70)
print("data_entrada — range e formato")
print("=" * 70)
print("min:", df["data_entrada"].min(), "| max:", df["data_entrada"].max())
print("amostra:", df["data_entrada"].head(3).tolist())

print("\n" + "=" * 70)
print("data_assinatura_contrato — range e formato (só quando status = Contratada?)")
print("=" * 70)
print("preenchido:", df["data_assinatura_contrato"].notna().sum())
print("status_final quando data_assinatura preenchida:")
print(df.loc[df["data_assinatura_contrato"].notna(), "status_final"].value_counts())
print("\nstatus_final == 'Contratada' mas SEM data de assinatura:")
mask = (df["status_final"] == "Contratada") & (df["data_assinatura_contrato"].isna())
print(mask.sum())

print("\n" + "=" * 70)
print("Checagem: valor_solicitado > valor_imovel (LTV > 100%)")
print("=" * 70)
ltv_calc = df["valor_solicitado_num"] / df["valor_imovel_num"]
print("LTV > 1.0:", (ltv_calc > 1.0).sum())
print("LTV > 0.60 (acima do máximo de política):", (ltv_calc > 0.60).sum())
print("LTV describe:")
print(ltv_calc.describe())

print("\n" + "=" * 70)
print("Valores negativos ou zero em colunas que não deveriam ter")
print("=" * 70)
for col in ["valor_imovel_num", "valor_solicitado_num", "idade_cliente", "renda_mensal_declarada",
            "prazo_meses", "score_credito", "tempo_analise_dias"]:
    neg = (df[col] < 0).sum()
    zero = (df[col] == 0).sum()
    if neg or zero:
        print(f"{col}: negativos={neg}, zeros={zero}")

print("\n" + "=" * 70)
print("idade_cliente — outliers plausíveis")
print("=" * 70)
print(df["idade_cliente"].sort_values().head(5))
print(df["idade_cliente"].sort_values().tail(5))

print("\n" + "=" * 70)
print("score_credito — range plausível (bureaus BR geralmente 0-1000)")
print("=" * 70)
print(df["score_credito"].min(), df["score_credito"].max())

print("\n" + "=" * 70)
print("cidade/uf — inconsistência (cidade não bate com uf?)")
print("=" * 70)
print(df.groupby("cidade")["uf"].nunique().sort_values(ascending=False).head(10))

print("\n" + "=" * 70)
print("consultor_id — valores únicos")
print("=" * 70)
print("qtd consultores:", df["consultor_id"].nunique())
print(df["consultor_id"].value_counts(dropna=False).head(10))