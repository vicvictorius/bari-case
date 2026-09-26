"""
Tratamento de Propostas_credito.csv.
Aplica o pipeline compartilhado e gera propostas_credito_tratado.csv.
"""
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
# Permite executar este arquivo diretamente, a partir de qualquer diretório.
sys.path.insert(0, str(RAIZ))

from pipeline.tratamento import tratar_dados

RAW_PATH = RAIZ / "dados_brutos" / "Propostas_credito.csv"
OUT_PATH = Path(__file__).resolve().parent / "propostas_credito_tratado.csv"


def main() -> None:
    bruto = pd.read_csv(RAW_PATH, encoding="utf-8-sig", dtype=str)
    df = tratar_dados(bruto)
    df.to_csv(OUT_PATH, index=False)
    print(f"OK — {len(df)} linhas mantidas (igual ao bruto: {len(bruto)}).")
    print(f"Salvo em {OUT_PATH}")
    print(df[["id_proposta", "valor_imovel", "data_entrada", "canal_origem",
              "etapa_max_funil", "idade_cliente", "ltv"]].head(3))


if __name__ == "__main__":
    main()
