"""Regressões da validação textual, sem alterar os artefatos históricos."""

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from normalizacao import normalizar_texto  # noqa: E402
from schema import CampoExtraido, LaudoExtraido  # noqa: E402


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (": 184.772 do 14º CRI de São Paulo", "184.772 do 14º CRI de São Paulo"),
        ("]-> 70.008", "70.008"),
        (" - : 70.008 : - ", "70.008"),
        ("70.008 ]->", "70.008"),
    ],
)
def test_limpa_simbolos_sem_alterar_evidencia(entrada, esperado):
    assert normalizar_texto(entrada) == esperado
    campo = CampoExtraido(valor=entrada, status="presente", trecho_bruto=entrada)
    assert campo.valor == esperado
    assert campo.trecho_bruto == entrada


@pytest.mark.parametrize(
    "entrada",
    [
        "strconv:45.981",
        "The 201.443",
        "value: 9.876, 2º RGI do Recife",
        "name: Fulano",
        "id_70.008",
        "STRCONV(45.981)",
        " : VALUE: 9.876 - ",
        "the 201.443",
    ],
)
def test_rejeita_prefixos_artificiais(entrada):
    with pytest.raises(ValueError, match="prefixo artificial"):
        normalizar_texto(entrada)
    with pytest.raises(ValidationError, match="prefixo artificial"):
        CampoExtraido(valor=entrada, status="presente")


@pytest.mark.parametrize(
    "entrada",
    [
        "Rua do Sol, 14, Curitiba/PR",
        "184.772 (14º CRI de São Paulo)",
        "14, Rua do Sol",
        "Rua Theodoro, 20",
        "Edifício The Garden, 14",
        "[certidão desatualizada]",
        "nenhum identificado.",
    ],
)
def test_preserva_textos_legitimos(entrada):
    assert normalizar_texto(entrada) == entrada
    assert CampoExtraido(valor=entrada, status="presente").valor == entrada


def test_apenas_simbolos_nao_satisfaz_valor_presente():
    with pytest.raises(ValidationError, match="valor é obrigatório"):
        CampoExtraido(valor=" : ]-> - ", status="presente")


def test_gabarito_inteiro_valida_e_preserva_valores_textuais():
    registros = json.loads((RAIZ / "gabarito.json").read_text(encoding="utf-8"))
    assert registros
    for dados in registros:
        registro = LaudoExtraido.model_validate(dados)
        for nome, campo in LaudoExtraido.model_fields.items():
            if campo.annotation is CampoExtraido:
                assert getattr(registro, nome).valor == dados[nome]["valor"]
