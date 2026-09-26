"""Testes do schema tipado (normalizacao.py + CampoNumero/CampoAno/CampoData).

Os casos rejeitados abaixo são saídas REAIS do qwen2.5:7b que passavam pela
validação quando todo `valor` era `str` (ver relatorio_acuracia_qwen25-7b.md).
"""

import json
import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from normalizacao import parse_ano, parse_data, parse_numero  # noqa: E402
from schema import (  # noqa: E402
    CampoAno,
    CampoData,
    CampoNumero,
    LaudoExtraido,
    json_schema_campos,
)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1.275.000,00", 1275000.0),
        ("R$ 455.000,00", 455000.0),
        ("218.000", 218000.0),
        ("1.450", 1450.0),
        ("54,8 m²", 54.8),
        ("155,00m²", 155.0),
        ("78.40", 78.4),
        ("96.3", 96.3),
        ("360", 360.0),
        (1020, 1020.0),
        (78.4, 78.4),
    ],
)
def test_parse_numero_aceita_formatos_brasileiros_e_numero_json(entrada, esperado):
    assert parse_numero(entrada) == pytest.approx(esperado)


@pytest.mark.parametrize(
    "entrada",
    [
        ".275.000,00",  # esperado 1.275.000,00: o "1" sumiu
        ".8",  # esperado 48000
        ".00 m²",
        "Possui 61m²",
        "id_146.00",
        "strconv(285)",
        "${1020.00}",
        "logar(395.500,00) = 395500.00",
        "falta o número, mas é mencionada como área útil 54,8 m²",
        "nameError: 'area_total_m2' can only contain numeric values, but found '118 m²'",
        "0",
        "-10",
        True,
    ],
)
def test_parse_numero_rejeita_texto_em_volta_e_valores_invalidos(entrada):
    with pytest.raises(ValueError):
        parse_numero(entrada)


@pytest.mark.parametrize(("entrada", "esperado"), [("2014", 2014), (1999, 1999), (2008.0, 2008)])
def test_parse_ano_aceita_ano_de_4_digitos(entrada, esperado):
    assert parse_ano(entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    ["/2014", ".99", "name: 2020", ": aproximadamente 18 anos", "1750", "2999", 2014.5],
)
def test_parse_ano_rejeita_idade_lixo_e_fora_da_faixa(entrada):
    with pytest.raises(ValueError):
        parse_ano(entrada)


def test_parse_data_aceita_iso_e_formato_brasileiro():
    assert parse_data("2025-03-12") == date(2025, 3, 12)
    assert parse_data("12/03/2025") == date(2025, 3, 12)


@pytest.mark.parametrize("entrada", ["12 de março de 2025", "2025-02-30", "março/2025"])
def test_parse_data_rejeita_formatos_nao_suportados(entrada):
    with pytest.raises(ValueError):
        parse_data(entrada)


def test_campo_numero_presente_com_lixo_gera_erro_de_validacao():
    """Erro de validação é o que dispara o retry no extrator."""
    with pytest.raises(ValidationError, match="número isolado"):
        CampoNumero(valor="Possui 61m²", status="presente")


def test_campo_numero_serializa_como_numero():
    campo = CampoNumero(valor="1.080.000,00", status="presente")
    assert campo.model_dump(mode="json")["valor"] == 1080000.0


def test_campo_data_serializa_em_iso():
    campo = CampoData(valor="12/03/2025", status="presente")
    assert campo.model_dump(mode="json")["valor"] == "2025-03-12"


def test_conflitante_descarta_valor_e_mantem_trecho():
    """Caso real do laudo_17: o modelo pôs as duas áreas em `valor`."""
    campo = CampoNumero(
        valor="cabeçalho: 95 m², tabela interna: 92 m²",
        status="conflitante",
        trecho_bruto="Área total: 95 m² (cabeçalho) / 92 m² (tabela)",
    )
    assert campo.valor is None
    assert campo.trecho_bruto


def test_ausente_continua_exigindo_trecho_bruto():
    with pytest.raises(ValidationError, match="trecho_bruto é obrigatório"):
        CampoAno(valor=None, status="ausente")


def test_json_schema_declara_tipos_ao_modelo():
    campos = json_schema_campos()
    assert campos["valor_avaliacao_reais"]["properties"]["valor"]["type"] == ["number", "null"]
    assert campos["area_total_m2"]["properties"]["valor"]["type"] == ["number", "null"]
    assert campos["ano_construcao"]["properties"]["valor"]["type"] == ["integer", "null"]
    assert campos["endereco"]["properties"]["valor"]["type"] == ["string", "null"]


def test_gabarito_valida_no_schema_tipado():
    registros = json.loads((RAIZ / "gabarito.json").read_text(encoding="utf-8"))
    assert len(registros) == 17
    for registro in registros:
        LaudoExtraido.model_validate(registro)


def test_saida_historica_qwen25_seria_barrada_pelo_schema_tipado():
    """Regressão documental: com o schema antigo, 17/17 laudos passavam.

    Com o schema tipado, 13 dos 17 laudos da execução histórica do
    qwen2.5:7b falham na validação (40 valores numéricos/datas com texto em
    volta). No extrator, isso vira retry em vez de saída aceita com lixo.
    """
    registros = json.loads(
        (RAIZ / "saida_extracao_local_qwen25-7b.json").read_text(encoding="utf-8")
    )
    invalidos = []
    for registro in registros:
        try:
            LaudoExtraido.model_validate(registro)
        except ValidationError:
            invalidos.append(registro["arquivo_origem"])
    assert len(invalidos) == 13
