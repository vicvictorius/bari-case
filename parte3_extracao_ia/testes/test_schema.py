"""Testes das regras de validação em schema.py.

O par de regras aqui (trecho_bruto obrigatório se não-presente / valor
obrigatório se presente) é o que garante que uma saída "presente com valor
vazio" ou "ausente sem evidência" nunca passa despercebida -- ver
decisoes.md para o caso real que motivou a segunda regra (laudo_15,
extração via qwen3:1.7b).
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schema import CampoExtraido, StatusCampo  # noqa: E402


def test_presente_com_valor_e_aceito():
    campo = CampoExtraido(valor="2003", status=StatusCampo.PRESENTE)
    assert campo.valor == "2003"


def test_presente_sem_valor_e_rejeitado():
    """Regressão: bug real encontrado no laudo_15 (extração via qwen3:1.7b) --
    o modelo marcava status="presente" com valor=None e colocava a resposta
    certa em trecho_bruto por engano. Sem esta regra, essa saída passava
    despercebida pela validação."""
    with pytest.raises(ValidationError, match="valor é obrigatório"):
        CampoExtraido(valor=None, status=StatusCampo.PRESENTE, trecho_bruto="Ano 2003.")


def test_ausente_com_trecho_e_aceito():
    campo = CampoExtraido(valor=None, status=StatusCampo.AUSENTE, trecho_bruto="não mencionado")
    assert campo.status == StatusCampo.AUSENTE


def test_ausente_sem_trecho_e_rejeitado():
    with pytest.raises(ValidationError, match="trecho_bruto é obrigatório"):
        CampoExtraido(valor=None, status=StatusCampo.AUSENTE)


def test_conflitante_sem_trecho_e_rejeitado():
    with pytest.raises(ValidationError, match="trecho_bruto é obrigatório"):
        CampoExtraido(valor=None, status=StatusCampo.CONFLITANTE)
