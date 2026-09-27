"""Checagens de robustez das associações das Perguntas 2 e 3.

Por que existe:
    1. A Pergunta 2 conclui que o canal Correspondente converte menos, mas o
       canal recebe propostas com score médio menor. Se a diferença viesse só
       desse mix, ela sumiria ao comparar propostas de score parecido.
    2. A Pergunta 3 compara amplitudes entre grupos. Variáveis com muitos
       grupos (UF tem 10) tendem a ter amplitude maior só por acaso, então a
       amplitude é complementada por um teste qui-quadrado de independência.

Método:
    - Conversão de Correspondente x demais canais dentro de cada faixa de
      score (mesmas faixas usadas em 03_diagnostico_funil.py, com a faixa
      501-750 subdividida para ter grupos de tamanho comparável).
    - Qui-quadrado de independência entre cada variável categórica e
      contratação (scipy.stats.chi2_contingency).

Limitação:
    A estratificação controla uma variável por vez. Não é um modelo
    multivariado e não prova causalidade.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import chi2_contingency

CSV_PATH = Path(__file__).resolve().parent / "propostas_credito_tratado.csv"
FAIXAS_SCORE = [0, 500, 600, 650, 700, 750, 1000]
ROTULOS_SCORE = ["<=500", "501-600", "601-650", "651-700", "701-750", ">750"]


def conversao_por_faixa(df: pd.DataFrame) -> pd.DataFrame:
    """Conversão (%) e volume de Correspondente x demais canais por faixa de score."""
    dados = df.assign(
        faixa_score=pd.cut(df["score_credito"], bins=FAIXAS_SCORE, labels=ROTULOS_SCORE),
        grupo=df["canal_origem"].eq("Correspondente").map(
            {True: "Correspondente", False: "Demais canais"}
        ),
        contratada=df["status_final"].eq("Contratada"),
    )
    tabela = dados.groupby(["faixa_score", "grupo"], observed=True)["contratada"].agg(
        ["mean", "size"]
    ).unstack("grupo")
    resultado = pd.DataFrame({
        "n_corresp": tabela[("size", "Correspondente")],
        "conv_corresp_%": (tabela[("mean", "Correspondente")] * 100).round(1),
        "n_demais": tabela[("size", "Demais canais")],
        "conv_demais_%": (tabela[("mean", "Demais canais")] * 100).round(1),
    })
    resultado["diferenca_pp"] = (resultado["conv_corresp_%"] - resultado["conv_demais_%"]).round(1)
    return resultado


def conversao_padronizada(df: pd.DataFrame) -> tuple[float, float, float]:
    """Conversão do Correspondente reponderada pelo mix de score dos demais canais.

    Responde: se o Correspondente recebesse propostas com a mesma distribuição
    de score dos demais canais, mantendo sua conversão dentro de cada faixa,
    qual seria sua conversão geral? A diferença entre o valor observado e o
    padronizado é a parte do gap explicada pelo mix de score.
    """
    tabela = conversao_por_faixa(df)
    peso_demais = tabela["n_demais"] / tabela["n_demais"].sum()
    padronizada = float((tabela["conv_corresp_%"] * peso_demais).sum())
    corresp = df["canal_origem"].eq("Correspondente")
    contratada = df["status_final"].eq("Contratada")
    observada = float(contratada[corresp].mean() * 100)
    demais = float(contratada[~corresp].mean() * 100)
    return observada, padronizada, demais


def qui_quadrado(df: pd.DataFrame, coluna: str) -> tuple[float, int, float]:
    """Retorna (estatística, graus de liberdade, p-valor) de coluna x contratação."""
    tabela = pd.crosstab(df[coluna], df["status_final"].eq("Contratada"))
    estatistica, p_valor, gl, _ = chi2_contingency(tabela)
    return float(estatistica), int(gl), float(p_valor)


def main() -> None:
    df = pd.read_csv(CSV_PATH)

    print("--- Correspondente x demais canais, por faixa de score ---")
    medias = df.groupby(df["canal_origem"].eq("Correspondente"))["score_credito"].mean()
    print(f"Score médio: Correspondente {medias[True]:.0f} | demais canais {medias[False]:.0f}")
    print(conversao_por_faixa(df).to_string())

    observada, padronizada, demais = conversao_padronizada(df)
    print("\nConversão do Correspondente com o mix de score dos demais canais:")
    print(f"  observada {observada:.1f}% | padronizada {padronizada:.1f}% | demais canais {demais:.1f}%")
    print(f"  gap total {observada - demais:+.1f} p.p. | gap após padronizar {padronizada - demais:+.1f} p.p.")

    print("\n--- Qui-quadrado de independência: variável x contratação ---")
    for coluna in ["canal_origem", "uf", "tipo_imovel"]:
        estatistica, gl, p_valor = qui_quadrado(df, coluna)
        p_txt = "< 0,0001" if p_valor < 0.0001 else f"{p_valor:.4f}".replace(".", ",")
        print(f"{coluna}: qui2 = {estatistica:.1f}, gl = {gl}, p = {p_txt}")


if __name__ == "__main__":
    main()
