"""Tratamento compartilhado das propostas, conforme o registro da Parte 1.

As regras são genéricas (por condição), não por id_proposta: assim a mesma
rotina funciona na base da próxima semana, trate a origem ou não os casos já
conhecidos, e um erro igual em outra linha é detectado e registrado no log.
"""

import logging

import numpy as np
import pandas as pd

LOG = logging.getLogger("bari.pipeline")

IDADE_MINIMA = 18
IDADE_MAXIMA = 100
ETAPA_FINAL = 6


def _ids(df: pd.DataFrame, mascara: pd.Series, limite: int = 10) -> str:
    """Lista curta de IDs afetados, para o log não crescer sem limite."""
    ids = df.loc[mascara, "id_proposta"].tolist()
    extra = f" (+{len(ids) - limite})" if len(ids) > limite else ""
    return ", ".join(ids[:limite]) + extra


def tratar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Trata uma cópia do CSV bruto lido com dtype=str, sem fazer leitura/escrita.

    Aplica as regras de parte1_diagnostico/registro_tratamento.md. Cada correção
    ou inconsistência encontrada gera um WARNING no logger "bari.pipeline" com
    os IDs afetados. Levanta ValueError se o resultado violar as checagens finais.
    """
    df = df.copy()
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
    # 3. canal_origem: normalizar espaços extras e capitalização (4 linhas)
    #    Achado na primeira rodada: 3 dessas 4 linhas tinham espaço em
    #    branco à direita ("mídia paga " != "mídia paga"), o que fez o
    #    primeiro mapeamento (sem .str.strip()) falhar silenciosamente.
    # ---------------------------------------------------------------
    df["canal_origem"] = df["canal_origem"].str.strip()
    mapa_canal = {
        "mídia paga": "Mídia paga",
        "indicação": "Indicação",
        "organico": "Orgânico",
        "Organico": "Orgânico",  # acento padronizado com os demais canais
    }
    df["canal_origem"] = df["canal_origem"].replace(mapa_canal)

    # ---------------------------------------------------------------
    # 4. etapa_max_funil acima da etapa final (caso original: PR-000081, 7).
    #    Só é corrigida para 6 quando a linha inteira confirma a contratação
    #    (status Contratada + assinatura + taxa). Sem essa evidência, o valor
    #    fica como está e a validação de quem consome o pipeline decide.
    # ---------------------------------------------------------------
    df["etapa_max_funil"] = pd.to_numeric(df["etapa_max_funil"], errors="raise")
    acima = df["etapa_max_funil"] > ETAPA_FINAL
    contratada_confirmada = (
        df["status_final"].eq("Contratada")
        & df["data_assinatura_contrato"].notna()
        & pd.to_numeric(df["taxa_juros_aa"], errors="coerce").notna()
    )
    corrigir = acima & contratada_confirmada
    if corrigir.any():
        LOG.warning("etapa_max_funil > %d em contratadas confirmadas, corrigida para %d: %s",
                    ETAPA_FINAL, ETAPA_FINAL, _ids(df, corrigir))
        df.loc[corrigir, "etapa_max_funil"] = ETAPA_FINAL
    if (acima & ~corrigir).any():
        LOG.warning("etapa_max_funil > %d sem evidência de contratação, mantida: %s",
                    ETAPA_FINAL, _ids(df, acima & ~corrigir))

    # ---------------------------------------------------------------
    # 5. idade_cliente implausível (caso original: PR-000079, 14 anos).
    #    Valor vira nulo e a linha é mantida: não há como saber a idade real.
    # ---------------------------------------------------------------
    df["idade_cliente"] = pd.to_numeric(df["idade_cliente"], errors="raise")
    idade_invalida = ~df["idade_cliente"].between(IDADE_MINIMA, IDADE_MAXIMA) & df["idade_cliente"].notna()
    if idade_invalida.any():
        LOG.warning("idade_cliente fora de %d-%d anos, marcada como nula (linha mantida): %s",
                    IDADE_MINIMA, IDADE_MAXIMA, _ids(df, idade_invalida))
        df.loc[idade_invalida, "idade_cliente"] = np.nan

    # ---------------------------------------------------------------
    # 9. assinatura anterior à entrada (caso original: PR-001556).
    #    Só sinaliza: não se sabe qual das datas está errada (ver registro).
    # ---------------------------------------------------------------
    assinatura_antes = df["data_assinatura_contrato"] < df["data_entrada"]
    if assinatura_antes.any():
        LOG.warning("data_assinatura_contrato anterior à data_entrada, mantida para revisão na origem: %s",
                    _ids(df, assinatura_antes))

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
    # Exceções explícitas em vez de assert: assert some com "python -O".
    if len(df) != n_inicial:
        raise ValueError("Nenhuma linha deveria ter sido descartada no tratamento.")
    if df["valor_imovel"].dtype != float:
        raise ValueError("valor_imovel não foi convertido para número.")
    if not df["ltv"].between(0, 1.5).all():
        raise ValueError("ltv fora de faixa plausível após cálculo: " + _ids(df, ~df["ltv"].between(0, 1.5)))

    return df
