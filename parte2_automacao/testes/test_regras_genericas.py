"""Regras genéricas do pipeline e comportamento da rotina com colunas opcionais.

Cobre os cenários de uma base semanal real: a origem corrige os casos já
conhecidos, o mesmo erro aparece em outra linha, ou chega uma coluna a menos.
"""

import logging
from pathlib import Path
import sys

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from parte2_automacao.relatorio_semanal import (
    CODIGO_BASE_DESATUALIZADA, ErroEntrada, ler_e_tratar, main,
)
from pipeline.tratamento import tratar_dados


@pytest.fixture
def bruto():
    """Base bruta completa: contém PR-000079, PR-000081 e PR-001556."""
    return pd.read_csv(RAIZ / "dados_brutos/Propostas_credito.csv", dtype=str, encoding="utf-8-sig")


def salvar(tmp_path, df):
    caminho = tmp_path / "entrada.csv"
    df.to_csv(caminho, index=False)
    return caminho


def linha(df, id_proposta):
    return df["id_proposta"] == id_proposta


# ---------------------------------------------------------------- pipeline

def test_casos_originais_sao_tratados_e_registrados(bruto, caplog):
    with caplog.at_level(logging.WARNING, logger="bari.pipeline"):
        tratado = tratar_dados(bruto)
    assert tratado.loc[linha(tratado, "PR-000081"), "etapa_max_funil"].item() == 6
    assert tratado.loc[linha(tratado, "PR-000079"), "idade_cliente"].isna().item()
    for id_proposta in ("PR-000081", "PR-000079", "PR-001556"):
        assert id_proposta in caplog.text


def test_origem_ja_corrigida_nao_quebra(bruto, caplog):
    bruto.loc[linha(bruto, "PR-000081"), "etapa_max_funil"] = "6"
    bruto.loc[linha(bruto, "PR-000079"), "idade_cliente"] = "41"
    with caplog.at_level(logging.WARNING, logger="bari.pipeline"):
        tratado = tratar_dados(bruto)
    assert tratado.loc[linha(tratado, "PR-000079"), "idade_cliente"].item() == 41
    assert "PR-000081" not in caplog.text and "PR-000079" not in caplog.text


def test_ids_originais_ausentes_nao_quebram(bruto):
    sem_casos = bruto[~bruto["id_proposta"].isin(["PR-000079", "PR-000081"])]
    assert len(tratar_dados(sem_casos)) == len(sem_casos)


def test_mesmo_erro_de_etapa_em_outra_contratada_e_corrigido(bruto, caplog):
    contratada = bruto.loc[bruto["status_final"].eq("Contratada"), "id_proposta"].iloc[5]
    bruto.loc[linha(bruto, contratada), "etapa_max_funil"] = "7"
    with caplog.at_level(logging.WARNING, logger="bari.pipeline"):
        tratado = tratar_dados(bruto)
    assert tratado.loc[linha(tratado, contratada), "etapa_max_funil"].item() == 6
    assert contratada in caplog.text


def test_etapa_acima_sem_contratacao_nao_e_corrigida_e_rotina_falha(tmp_path, bruto):
    perdida = bruto.loc[bruto["status_final"].eq("Desistiu"), "id_proposta"].iloc[0]
    bruto.loc[linha(bruto, perdida), "etapa_max_funil"] = "7"
    assert tratar_dados(bruto).loc[lambda d: linha(d, perdida), "etapa_max_funil"].item() == 7
    with pytest.raises(ErroEntrada, match="etapa_max_funil"):
        ler_e_tratar(salvar(tmp_path, bruto))


@pytest.mark.parametrize("idade", ["12", "130"])
def test_idade_implausivel_em_outra_linha_vira_nula(bruto, caplog, idade):
    bruto.loc[linha(bruto, "PR-000200"), "idade_cliente"] = idade
    with caplog.at_level(logging.WARNING, logger="bari.pipeline"):
        tratado = tratar_dados(bruto)
    assert tratado.loc[linha(tratado, "PR-000200"), "idade_cliente"].isna().item()
    assert len(tratado) == len(bruto)
    assert "PR-000200" in caplog.text


def test_assinatura_antes_da_entrada_e_sinalizada_sem_alterar(bruto, caplog):
    original = bruto.loc[linha(bruto, "PR-001556"), "data_assinatura_contrato"].item()
    with caplog.at_level(logging.WARNING, logger="bari.pipeline"):
        tratado = tratar_dados(bruto)
    valor = tratado.loc[linha(tratado, "PR-001556"), "data_assinatura_contrato"].item()
    assert valor == pd.Timestamp(original)
    assert "anterior à data_entrada" in caplog.text


# ------------------------------------------------------- rotina semanal

@pytest.mark.parametrize("coluna", ["consultor_id", "uf", "score_credito", "idade_cliente"])
def test_coluna_opcional_ausente_gera_aviso_e_segue(tmp_path, bruto, caplog, coluna):
    with caplog.at_level(logging.WARNING, logger="bari.semanal"):
        tratado = ler_e_tratar(salvar(tmp_path, bruto.drop(columns=coluna)))
    assert len(tratado) == len(bruto)
    assert tratado[coluna].isna().all()
    assert coluna in caplog.text


@pytest.mark.parametrize("coluna", ["status_final", "valor_imovel", "taxa_juros_aa"])
def test_coluna_essencial_ausente_falha(tmp_path, bruto, coluna):
    with pytest.raises(ErroEntrada, match=coluna):
        ler_e_tratar(salvar(tmp_path, bruto.drop(columns=coluna)))


def test_avisos_do_pipeline_vao_para_o_log_da_execucao(tmp_path):
    retorno = main(["--saida", str(tmp_path), "--data-referencia", "2025-10-27"])
    assert retorno == 0
    log = (tmp_path / "relatorio_2025-10-20_2025-10-26.log").read_text(encoding="utf-8")
    assert "PR-000081" in log and "PR-001556" in log


def test_base_desatualizada_gera_html_com_codigo_proprio(tmp_path):
    retorno = main(["--saida", str(tmp_path), "--data-referencia", "2026-09-21"])
    assert retorno == CODIGO_BASE_DESATUALIZADA
    assert (tmp_path / "relatorio_2026-09-14_2026-09-20.html").exists()
