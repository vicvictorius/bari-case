"""Teste de significância das duas diferenças de conversão da Pergunta 2.

Por que existe:
    A Parte 1 mostrou a queda de conversão (20,4% em 2024 contra 18,7% em
    jan-out/2025) e a diferença do canal Correspondente, mas sem dizer se
    essas diferenças poderiam ser só ruído amostral.

Método:
    Teste z para diferença entre duas proporções (bilateral) e intervalo de
    confiança de 95% da diferença. Só usa a biblioteca padrão para o cálculo.

Limitação:
    O teste diz se a diferença é maior do que o acaso explicaria. Não diz
    por que ela existe (mix de canal, score, sazonalidade etc.).
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parent / "propostas_credito_tratado.csv"


def teste_duas_proporcoes(
    sucessos_a: int, total_a: int, sucessos_b: int, total_b: int
) -> dict[str, float]:
    """Teste z bilateral para p_a - p_b, com IC 95% da diferença."""
    p_a = sucessos_a / total_a
    p_b = sucessos_b / total_b
    p_comb = (sucessos_a + sucessos_b) / (total_a + total_b)

    erro_teste = math.sqrt(p_comb * (1 - p_comb) * (1 / total_a + 1 / total_b))
    z = (p_a - p_b) / erro_teste
    p_valor = math.erfc(abs(z) / math.sqrt(2))

    erro_ic = math.sqrt(p_a * (1 - p_a) / total_a + p_b * (1 - p_b) / total_b)
    diferenca = p_a - p_b

    return {
        "p_a": p_a,
        "p_b": p_b,
        "diferenca_pp": diferenca * 100,
        "ic95_inf_pp": (diferenca - 1.96 * erro_ic) * 100,
        "ic95_sup_pp": (diferenca + 1.96 * erro_ic) * 100,
        "z": z,
        "p_valor": p_valor,
    }


def imprimir(titulo: str, rotulo_a: str, rotulo_b: str, contagens: tuple[int, int, int, int]) -> None:
    r = teste_duas_proporcoes(*contagens)
    print(f"\n--- {titulo} ---")
    print(f"{rotulo_a}: {contagens[0]}/{contagens[1]} = {r['p_a']:.1%}")
    print(f"{rotulo_b}: {contagens[2]}/{contagens[3]} = {r['p_b']:.1%}")
    print(
        f"Diferença: {r['diferenca_pp']:+.2f} p.p. "
        f"(IC 95%: {r['ic95_inf_pp']:+.2f} a {r['ic95_sup_pp']:+.2f} p.p.)"
    )
    print(f"z = {r['z']:.2f} | p-valor = {r['p_valor']:.4f}")


def main() -> None:
    df = pd.read_csv(CSV_PATH, parse_dates=["data_entrada"])
    df["contratada"] = df["status_final"] == "Contratada"

    # Mesmo recorte da Pergunta 2: 2024 inteiro contra jan-out/2025
    # (nov e dez/2025 fora por maturação da coorte).
    a = df[df["data_entrada"].dt.year == 2024]
    b = df[(df["data_entrada"].dt.year == 2025) & (df["data_entrada"].dt.month <= 10)]
    imprimir(
        "Queda de conversão: 2024 x jan-out/2025",
        "2024",
        "jan-out/2025",
        (int(a["contratada"].sum()), len(a), int(b["contratada"].sum()), len(b)),
    )

    corr = df[df["canal_origem"] == "Correspondente"]
    demais = df[df["canal_origem"] != "Correspondente"]
    imprimir(
        "Canal: Correspondente x demais canais (base toda)",
        "Correspondente",
        "Demais",
        (int(corr["contratada"].sum()), len(corr), int(demais["contratada"].sum()), len(demais)),
    )


if __name__ == "__main__":
    main()
