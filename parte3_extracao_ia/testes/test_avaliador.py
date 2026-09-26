"""Testes do avaliador de acurácia.

O ponto central destes testes é provar que `avaliador.py` REALMENTE detecta
erros -- não basta rodar contra uma extração idêntica ao gabarito e ver
100%. Por isso `extracao_com_erros_tipicos` simula os 3 erros mais prováveis
de uma extração por LLM que não segue as regras à risca:
  1. calcular um valor derivado que o documento não afirma (soma de áreas);
  2. resolver uma divergência escolhendo um dos dois valores em vez de
     marcar como conflitante;
  3. inferir um ano a partir de uma idade aproximada.

Os testes de normalização também cobrem artefatos reais observados durante
o benchmark com qwen2.5:7b-instruct. O objetivo é permitir diferenças
puramente representacionais sem tornar o avaliador permissivo a ponto de
esconder erros semânticos reais.

A normalização textual complementar cobre especificamente diferenças de
representação nos campos `endereco` e `matricula`, preservando casos em que
há perda real de informação.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from avaliador import (
    avaliar,
    normalizar_texto_comparacao,
    normalizar_valor,
)


@pytest.mark.parametrize(
    "a, b",
    [
        # Casos reais do relatório com qwen3:1.7b:
        # formatação diferente, mesmo valor.
        ("78.40", "78,40"),
        ("642000.00", "642000"),
        ("218000.00", "218.000"),
        ("1275000.00", "1.275.000,00"),
        ("2180000.00", "R$ 2.180.000,00"),
        ("201.443", "201443"),
        ("2025-03-12", "12/03/2025"),
        ("2025-04-07", "07/04/2025"),

        # Artefatos reais observados no benchmark com qwen2.5:7b-instruct.
        # O conteúdo numérico é equivalente; apenas existem wrappers
        # artificiais ao redor do valor.
        ("/78.40", "78.40"),
        ("id_146.00", "146.00"),
        ("${1020.00}", "1020.00"),
        ("strconv(285)", "285.00"),
        ("log(910000)", "910000.00"),
        ("name: 420,00 m²", "420.00"),
    ],
)
def test_normalizar_valor_trata_formatacao_equivalente_como_igual(a, b):
    assert normalizar_valor(a) == normalizar_valor(b)


@pytest.mark.parametrize(
    "a, b",
    [
        # Estes SÃO diferenças de valor reais e não podem virar iguais.
        ("92.50", "125.00"),  # troca área privativa/total (laudo_7)
        ("2025-03-12", "2025-03-13"),
        (
            "45.981 (Cartório do 3º Ofício)",
            "45.981",
        ),  # contexto a mais não é só formatação

        # Proteções contra uma normalização excessivamente permissiva.
        #
        # Mesmo contendo um número reconhecível, o valor é diferente.
        ("name: 125.00 m²", "92.50"),

        # Existem dois números candidatos. O avaliador não deve simplesmente
        # pegar o primeiro número da frase e declarar equivalência.
        ("area 125.00 e terreno 420.00", "125.00"),
    ],
)
def test_normalizar_valor_preserva_diferencas_reais(a, b):
    assert normalizar_valor(a) != normalizar_valor(b)


def test_normalizacao_textual_ignora_separador_uf():
    """Separadores diferentes de cidade/UF não mudam o endereço."""
    esperado = normalizar_texto_comparacao(
        "Rua Monte Verde, 19, Curitiba/PR"
    )
    obtido = normalizar_texto_comparacao(
        "Rua Monte Verde, 19, Curitiba-PR"
    )

    assert esperado == obtido


def test_normalizacao_textual_ignora_pontuacao_matricula():
    """Pontuação e conectores não devem alterar a matrícula."""
    esperado = normalizar_texto_comparacao(
        "145.230 (7º RGI)"
    )
    obtido = normalizar_texto_comparacao(
        "145.230 do 7º RGI"
    )

    assert esperado == obtido


def test_normalizacao_textual_remove_wrapper_artificial():
    """Wrapper produzido pelo modelo não deve alterar o conteúdo."""
    esperado = normalizar_texto_comparacao(
        "9.876 (2º RGI do Recife)"
    )
    obtido = normalizar_texto_comparacao(
        "value: 9.876, 2º RGI do Recife"
    )

    assert esperado == obtido


def test_normalizacao_textual_nao_esconde_informacao_ausente():
    """Perda de complemento do endereço deve continuar sendo erro."""
    esperado = normalizar_texto_comparacao(
        "Sala 503, Edifício Horizonte, Rua do Comércio, 77, Curitiba/PR"
    )
    obtido = normalizar_texto_comparacao(
        "Rua do Comércio, 77, Curitiba/PR"
    )

    assert esperado != obtido


def test_normalizacao_textual_nao_ignora_cartorio_ausente():
    """Perda dos dados do registro não pode virar equivalência."""
    esperado = normalizar_texto_comparacao(
        "66.504 (Registro de Imóveis da 4ª Zona)"
    )
    obtido = normalizar_texto_comparacao(
        "66.504"
    )

    assert esperado != obtido


def test_extracao_identica_ao_gabarito_da_100_por_cento():
    gabarito = json.loads(
        Path(__file__)
        .resolve()
        .parent.parent
        .joinpath("gabarito.json")
        .read_text(encoding="utf-8")
    )
    gabarito_idx = {r["arquivo_origem"]: r for r in gabarito}

    resultado = avaliar(
        extracao=gabarito_idx,
        gabarito=gabarito_idx,
    )

    assert resultado["acuracia_status_geral"] == 1.0
    assert resultado["divergencias"] == []


def test_extracao_com_erros_tipicos_e_detectada():
    gabarito = json.loads(
        Path(__file__)
        .resolve()
        .parent.parent
        .joinpath("gabarito.json")
        .read_text(encoding="utf-8")
    )
    gabarito_idx = {r["arquivo_origem"]: r for r in gabarito}

    extracao_idx = json.loads(json.dumps(gabarito_idx))  # cópia profunda

    # Erro 1: "IA" soma área útil + comum do laudo_3 em vez de marcar ausente.
    extracao_idx["laudo_3.txt"]["area_total_m2"] = {
        "valor": "73.00",
        "status": "presente",
        "trecho_bruto": None,
    }

    # Erro 2: "IA" resolve a divergência do laudo_17 escolhendo o valor do
    # cabeçalho, em vez de marcar como conflitante.
    extracao_idx["laudo_17.txt"]["area_total_m2"] = {
        "valor": "95.00",
        "status": "presente",
        "trecho_bruto": None,
    }

    # Erro 3: "IA" infere ano de construção a partir da idade aproximada do
    # laudo_14 (2025 - 18 ≈ 2007), quando deveria marcar ausente.
    extracao_idx["laudo_14.txt"]["ano_construcao"] = {
        "valor": "2007",
        "status": "presente",
        "trecho_bruto": None,
    }

    resultado = avaliar(
        extracao=extracao_idx,
        gabarito=gabarito_idx,
    )

    assert resultado["acuracia_status_geral"] < 1.0

    campos_com_erro = {
        d["campo"]
        for d in resultado["divergencias"]
    }

    assert "area_total_m2" in campos_com_erro
    assert "ano_construcao" in campos_com_erro
    assert len(resultado["divergencias"]) == 3


def test_laudo_faltando_na_extracao_nao_e_ignorado_silenciosamente():
    gabarito = json.loads(
        Path(__file__)
        .resolve()
        .parent.parent
        .joinpath("gabarito.json")
        .read_text(encoding="utf-8")
    )
    gabarito_idx = {r["arquivo_origem"]: r for r in gabarito}

    extracao_incompleta = {
        k: v
        for k, v in gabarito_idx.items()
        if k != "laudo_5.txt"
    }

    resultado = avaliar(
        extracao=extracao_incompleta,
        gabarito=gabarito_idx,
    )

    assert "laudo_5.txt" in resultado["arquivos_faltando_na_extracao"]

    # 16 dos 17 laudos com todos os campos corretos -> geral cai
    # proporcionalmente.
    assert resultado["acuracia_status_geral"] < 1.0


def test_acuracia_de_valor_geral_separa_status_certo_de_valor_certo():
    """Status certo com valor errado não pode contar como acerto de valor."""
    gabarito = {
        "l.txt": {
            campo: {
                "valor": "10",
                "status": "presente",
                "trecho_bruto": None,
            }
            for campo in [
                "tipo_imovel",
                "endereco",
                "area_privativa_m2",
                "area_total_m2",
                "ano_construcao",
                "valor_avaliacao_reais",
                "matricula",
                "onus",
                "data_vistoria",
                "responsavel_tecnico",
            ]
        }
    }

    extracao = {
        "l.txt": {
            campo: dict(valor)
            for campo, valor in gabarito["l.txt"].items()
        }
    }

    extracao["l.txt"]["area_total_m2"]["valor"] = "99"

    resultado = avaliar(
        extracao,
        gabarito,
    )

    assert resultado["acuracia_status_geral"] == 1.0
    assert resultado["valores_corretos"] == 9
    assert resultado["valores_aplicaveis"] == 10
    assert resultado["acuracia_valor_geral"] == 0.9