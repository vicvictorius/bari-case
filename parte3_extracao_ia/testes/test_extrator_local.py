"""Testa extrator_local.py com um cliente Ollama FALSO (sem servidor real).

Este sandbox de desenvolvimento não tem acesso ao domínio ollama.com nem
GPU para baixar/rodar um modelo de verdade -- então este teste substitui
`ollama.Client.chat` por uma função que devolve respostas pré-definidas,
para provar que a lógica de parsing + validação Pydantic + retry está
correta. NÃO testa a qualidade do modelo real -- isso só se mede rodando
de fato na sua máquina.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extrator_local import extrair_um_laudo  # noqa: E402


def _resposta_ollama(payload: dict) -> dict:
    return {"message": {"content": json.dumps(payload, ensure_ascii=False)}}


REGISTRO_VALIDO = {
    "tipo_imovel": {"valor": "apartamento", "status": "presente", "trecho_bruto": None},
    "endereco": {"valor": "Rua X, 1", "status": "presente", "trecho_bruto": None},
    "area_privativa_m2": {"valor": "50.00", "status": "presente", "trecho_bruto": None},
    "area_total_m2": {"valor": "70.00", "status": "presente", "trecho_bruto": None},
    "ano_construcao": {"valor": "2010", "status": "presente", "trecho_bruto": None},
    "valor_avaliacao_reais": {"valor": "300000.00", "status": "presente", "trecho_bruto": None},
    "matricula": {"valor": "123", "status": "presente", "trecho_bruto": None},
    "onus": {"valor": "nenhum", "status": "presente", "trecho_bruto": None},
    "data_vistoria": {"valor": "2025-01-01", "status": "presente", "trecho_bruto": None},
    "responsavel_tecnico": {"valor": "Fulano", "status": "presente", "trecho_bruto": None},
}


def test_primeira_resposta_valida_e_aceita():
    client = MagicMock()
    client.chat.return_value = _resposta_ollama(REGISTRO_VALIDO)

    registro = extrair_um_laudo(client, "modelo-fake", "texto do laudo", "laudo_teste.txt")

    assert registro.arquivo_origem == "laudo_teste.txt"
    assert registro.tipo_imovel.valor == "apartamento"
    assert client.chat.call_count == 1


def test_resposta_invalida_depois_valida_aciona_retry():
    # 1ª tentativa: status="ausente" sem trecho_bruto -> viola a regra do schema.py
    invalido = dict(REGISTRO_VALIDO)
    invalido["onus"] = {"valor": None, "status": "ausente", "trecho_bruto": None}

    client = MagicMock()
    client.chat.side_effect = [
        _resposta_ollama(invalido),
        _resposta_ollama(REGISTRO_VALIDO),  # 2ª tentativa: corrigido
    ]

    registro = extrair_um_laudo(client, "modelo-fake", "texto do laudo", "laudo_teste.txt")

    assert registro.onus.valor == "nenhum"
    assert client.chat.call_count == 2


def test_json_malformado_aciona_retry():
    client = MagicMock()
    client.chat.side_effect = [
        {"message": {"content": "isso não é um json { quebrado"}},
        _resposta_ollama(REGISTRO_VALIDO),
    ]

    registro = extrair_um_laudo(client, "modelo-fake", "texto do laudo", "laudo_teste.txt")
    assert registro is not None
    assert client.chat.call_count == 2


def test_falha_persistente_levanta_runtime_error():
    client = MagicMock()
    client.chat.return_value = {"message": {"content": "sempre quebrado {"}}

    try:
        extrair_um_laudo(client, "modelo-fake", "texto do laudo", "laudo_teste.txt")
        assert False, "deveria ter levantado RuntimeError"
    except RuntimeError as exc:
        assert "laudo_teste.txt" in str(exc)
    assert client.chat.call_count == 3  # MAX_TENTATIVAS
