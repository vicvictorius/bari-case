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

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import extrator_local  # noqa: E402
from extrator_local import (  # noqa: E402
    MAX_TENTATIVAS,
    caminho_falhas,
    extrair_um_laudo,
    processar_diretorio,
)


def _resposta_ollama(payload: dict) -> dict:
    return {"message": {"content": json.dumps(payload, ensure_ascii=False)}}


REGISTRO_VALIDO = {
    "tipo_imovel": {
        "valor": "apartamento",
        "status": "presente",
        "trecho_bruto": None,
    },
    "endereco": {
        "valor": "Rua X, 1",
        "status": "presente",
        "trecho_bruto": None,
    },
    "area_privativa_m2": {
        "valor": "50.00",
        "status": "presente",
        "trecho_bruto": None,
    },
    "area_total_m2": {
        "valor": "70.00",
        "status": "presente",
        "trecho_bruto": None,
    },
    "ano_construcao": {
        "valor": "2010",
        "status": "presente",
        "trecho_bruto": None,
    },
    "valor_avaliacao_reais": {
        "valor": "300000.00",
        "status": "presente",
        "trecho_bruto": None,
    },
    "matricula": {
        "valor": "123",
        "status": "presente",
        "trecho_bruto": None,
    },
    "onus": {
        "valor": "nenhum",
        "status": "presente",
        "trecho_bruto": None,
    },
    "data_vistoria": {
        "valor": "2025-01-01",
        "status": "presente",
        "trecho_bruto": None,
    },
    "responsavel_tecnico": {
        "valor": "Fulano",
        "status": "presente",
        "trecho_bruto": None,
    },
}


def test_primeira_resposta_valida_e_aceita():
    client = MagicMock()
    client.chat.return_value = _resposta_ollama(REGISTRO_VALIDO)

    registro = extrair_um_laudo(
        client,
        "modelo-fake",
        "texto do laudo",
        "laudo_teste.txt",
    )

    assert registro.arquivo_origem == "laudo_teste.txt"
    assert registro.tipo_imovel.valor == "apartamento"
    assert client.chat.call_count == 1


def test_resposta_invalida_depois_valida_aciona_retry():
    invalido = dict(REGISTRO_VALIDO)
    invalido["onus"] = {
        "valor": None,
        "status": "ausente",
        "trecho_bruto": None,
    }

    client = MagicMock()
    client.chat.side_effect = [
        _resposta_ollama(invalido),
        _resposta_ollama(REGISTRO_VALIDO),
    ]

    registro = extrair_um_laudo(
        client,
        "modelo-fake",
        "texto do laudo",
        "laudo_teste.txt",
    )

    assert registro.onus.valor == "nenhum"
    assert client.chat.call_count == 2


def test_json_malformado_aciona_retry():
    client = MagicMock()
    client.chat.side_effect = [
        {
            "message": {
                "content": "isso não é um json { quebrado",
            }
        },
        _resposta_ollama(REGISTRO_VALIDO),
    ]

    registro = extrair_um_laudo(
        client,
        "modelo-fake",
        "texto do laudo",
        "laudo_teste.txt",
    )

    assert registro is not None
    assert client.chat.call_count == 2


def test_falha_persistente_levanta_runtime_error():
    client = MagicMock()
    client.chat.return_value = {
        "message": {
            "content": "sempre quebrado {",
        }
    }

    try:
        extrair_um_laudo(
            client,
            "modelo-fake",
            "texto do laudo",
            "laudo_teste.txt",
        )
        assert False, "deveria ter levantado RuntimeError"

    except RuntimeError as exc:
        assert "laudo_teste.txt" in str(exc)

    assert client.chat.call_count == 3


def test_processamento_parcial_retorna_resultados_e_lista_de_falhas(
    tmp_path,
):
    """Preserva resultados válidos e registra os detalhes da falha."""
    (tmp_path / "laudo_1.txt").write_text(
        "laudo válido",
        encoding="utf-8",
    )

    (tmp_path / "laudo_2.txt").write_text(
        "laudo que falhará",
        encoding="utf-8",
    )

    client = MagicMock()

    client.chat.side_effect = [
        _resposta_ollama(REGISTRO_VALIDO),
        {
            "message": {
                "content": "json inválido {",
            }
        },
        {
            "message": {
                "content": "json inválido {",
            }
        },
        {
            "message": {
                "content": "json inválido {",
            }
        },
    ]

    resultados, falhas = processar_diretorio(
        tmp_path,
        client,
        "modelo-fake",
    )

    assert len(resultados) == 1
    assert resultados[0]["arquivo_origem"] == "laudo_1.txt"

    assert len(falhas) == 1
    assert falhas[0]["arquivo_origem"] == "laudo_2.txt"
    assert falhas[0]["ultimo_erro"]
    assert "Expecting value" in falhas[0]["ultimo_erro"]

    assert client.chat.call_count == 4


def test_caminho_falhas_preserva_diretorio_e_prefixa_nome():
    saida = Path("dir/saida_x.json")

    assert caminho_falhas(saida) == Path(
        "dir/falhas_saida_x.json"
    )


def test_prefixo_textual_artificial_aciona_retry_com_feedback():
    invalido = dict(REGISTRO_VALIDO)
    invalido["matricula"] = {
        "valor": "strconv:45.981",
        "status": "presente",
        "trecho_bruto": "45.981",
    }

    client = MagicMock()
    client.chat.side_effect = [
        _resposta_ollama(invalido),
        _resposta_ollama(REGISTRO_VALIDO),
    ]

    registro = extrair_um_laudo(
        client,
        "modelo-fake",
        "texto",
        "laudo_teste.txt",
    )

    assert registro.matricula.valor == "123"
    assert client.chat.call_count == 2

    feedback = (
        client.chat.call_args_list[1]
        .kwargs["messages"][-1]["content"]
    )

    assert "prefixo artificial" in feedback
    assert "matricula" in feedback


def test_prefixo_textual_persistente_nao_entrega_registro():
    invalido = dict(REGISTRO_VALIDO)
    invalido["matricula"] = {
        "valor": "value: 123",
        "status": "presente",
    }

    client = MagicMock()
    client.chat.return_value = _resposta_ollama(invalido)

    with pytest.raises(
        RuntimeError,
        match="prefixo artificial",
    ):
        extrair_um_laudo(
            client,
            "modelo-fake",
            "texto",
            "laudo_teste.txt",
        )

    assert client.chat.call_count == MAX_TENTATIVAS


def test_falha_preserva_mensagem_final_da_runtime_error(tmp_path, monkeypatch):
    (tmp_path / "laudo_4.txt").write_text("texto", encoding="utf-8")
    mensagem = "Falha ao extrair laudo_4.txt: erro simulado de validação"
    extrair = MagicMock(side_effect=RuntimeError(mensagem))
    monkeypatch.setattr(extrator_local, "extrair_um_laudo", extrair)

    resultados, falhas = processar_diretorio(tmp_path, MagicMock(), "modelo-fake")

    assert resultados == []
    assert falhas == [{"arquivo_origem": "laudo_4.txt", "ultimo_erro": mensagem}]


@pytest.mark.parametrize("quantidade_falhas", [0, 1, 2])
def test_main_grava_falhas_e_preserva_saida_parcial(
    tmp_path, monkeypatch, caplog, quantidade_falhas
):
    """Exercita sucesso, lote parcial e falha total com cliente simulado."""
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    for numero in (1, 2):
        (entrada / f"laudo_{numero}.txt").write_text("texto", encoding="utf-8")
    saida = tmp_path / "resultados" / "saida_x.json"
    saida.parent.mkdir()
    arquivo_falhas = caminho_falhas(saida)
    arquivo_falhas.write_text(
        '[{"arquivo_origem": "antigo.txt", "ultimo_erro": "erro antigo"}]',
        encoding="utf-8",
    )
    client = MagicMock()
    respostas = []
    for numero in (1, 2):
        if numero <= quantidade_falhas:
            respostas.extend([RuntimeError("erro simulado de conexão")] * MAX_TENTATIVAS)
        else:
            respostas.append(_resposta_ollama(REGISTRO_VALIDO))
    client.chat.side_effect = respostas
    monkeypatch.setattr(extrator_local.ollama, "Client", MagicMock(return_value=client))
    monkeypatch.setattr(
        sys, "argv",
        ["extrator_local.py", "--entrada", str(entrada), "--saida", str(saida)],
    )
    caplog.set_level("INFO", logger="extrator_laudos_local")

    retorno = extrator_local.main()

    assert retorno == (1 if quantidade_falhas else 0)
    resultados = json.loads(saida.read_text(encoding="utf-8"))
    assert [r["arquivo_origem"] for r in resultados] == [
        f"laudo_{numero}.txt" for numero in (1, 2) if numero > quantidade_falhas
    ]
    falhas = json.loads(arquivo_falhas.read_text(encoding="utf-8"))
    assert falhas == [
        {
            "arquivo_origem": f"laudo_{numero}.txt",
            "ultimo_erro": (
                f"Falha ao extrair laudo_{numero}.txt após "
                f"{MAX_TENTATIVAS} tentativas: erro simulado de conexão"
            ),
        }
        for numero in range(1, quantidade_falhas + 1)
    ]
    assert f"Falhas gravadas em {arquivo_falhas}" in caplog.text
    assert (
        f"Processamento concluído: {2 - quantidade_falhas} ok, "
        f"{quantidade_falhas} falhas, 2 total"
    ) in caplog.text
