"""Regressões do contrato de entrada, coortes e execução da rotina semanal."""

from datetime import date
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from parte2_automacao.relatorio_semanal import (
    ErroEntrada, SCRIPT_FILTROS, calcular, gerar_html, gravar_html, ler_e_tratar, main, periodo,
    preparar_filtros,
)
from pipeline.tratamento import tratar_dados


@pytest.fixture
def bruto():
    # Inclui as duas correções documentadas (PR-000079 e PR-000081).
    return pd.read_csv(RAIZ / "dados_brutos/Propostas_credito.csv", dtype=str,
                       encoding="utf-8-sig").head(100)


def salvar(tmp_path, df, sep=","):
    caminho = tmp_path / "entrada.csv"
    df.to_csv(caminho, index=False, sep=sep)
    return caminho


@pytest.mark.parametrize("sep", [",", ";"])
def test_leitura_preserva_resultado_do_pipeline(tmp_path, bruto, sep):
    resultado = ler_e_tratar(salvar(tmp_path, bruto, sep))
    pd.testing.assert_frame_equal(resultado, tratar_dados(bruto), check_exact=True)


def test_coluna_ausente_e_identificada(tmp_path, bruto):
    with pytest.raises(ErroEntrada, match="valor_solicitado"):
        ler_e_tratar(salvar(tmp_path, bruto.drop(columns="valor_solicitado")))


@pytest.mark.parametrize("coluna,valor", [
    ("renda_mensal_declarada", "1.234,56"), ("score_credito", "inválido"),
    ("valor_imovel", "inf"), ("data_entrada", "2025/12/01"),
    ("data_entrada", "31/02/2025"), ("data_assinatura_contrato", "2025-02-30"),
    ("status_final", "Em andamento"), ("etapa_max_funil", "3.5"),
    ("valor_solicitado", "-10"), ("canal_origem", "   "),
])
def test_formato_ou_valor_incompativel_falha_explicitamente(tmp_path, bruto, coluna, valor):
    bruto.loc[0, coluna] = valor
    with pytest.raises(ErroEntrada):
        ler_e_tratar(salvar(tmp_path, bruto))


def test_id_duplicado_nao_infla_metricas(tmp_path, bruto):
    bruto.loc[1, "id_proposta"] = bruto.loc[0, "id_proposta"]
    with pytest.raises(ErroEntrada, match="duplicado"):
        ler_e_tratar(salvar(tmp_path, bruto))


def test_coluna_extra_preservada(tmp_path, bruto):
    bruto["nova_coluna"] = "novo dado"
    resultado = ler_e_tratar(salvar(tmp_path, bruto))
    assert resultado["nova_coluna"].eq("novo dado").all()


def test_cabecalho_duplicado_rejeitado(tmp_path, bruto):
    caminho = salvar(tmp_path, bruto)
    texto = caminho.read_text(encoding="utf-8").replace("cidade,uf", "cidade,cidade", 1)
    caminho.write_text(texto, encoding="utf-8")
    with pytest.raises(ErroEntrada, match="duplicadas"):
        ler_e_tratar(caminho)


def test_registro_com_campos_a_menos_rejeitado(tmp_path, bruto):
    caminho = salvar(tmp_path, bruto)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write("registro,incompleto\n")
    with pytest.raises(ErroEntrada, match="quantidade de campos"):
        ler_e_tratar(caminho)


def test_csv_sem_registros_rejeitado(tmp_path, bruto):
    with pytest.raises(ErroEntrada, match="sem registros"):
        ler_e_tratar(salvar(tmp_path, bruto.iloc[:0]))


@pytest.mark.parametrize("referencia", [date(2026, 1, 5), date(2026, 1, 11)])
def test_ultima_semana_completa_inclusive_na_virada_do_ano(referencia):
    assert periodo(referencia) == (date(2025, 12, 29), date(2026, 1, 5))


def dados_metricas():
    return pd.DataFrame({
        "id_proposta": ["a", "b", "c", "d", "e"],
        "data_entrada": pd.to_datetime(["2025-12-28", "2025-12-29", "2026-01-04", "2026-01-05", "2025-12-20"]),
        "status_final": ["Contratada", "Contratada", "Desistiu", "Contratada", "Desistiu"],
        "valor_solicitado": [100., 200., 300., 400., 500.],
        "etapa_max_funil": [6, 6, 3, 6, 2],
        "canal_origem": ["A", "A", "B", "B", "A"],
    })


def test_limites_denominadores_perdas_e_historico():
    m = calcular(dados_metricas(), date(2026, 1, 5))
    assert m["semana"] == {"total": 2, "contratadas": 1, "conversao": .5,
                           "solicitado": 500., "perdido": 300.}
    assert m["anterior"]["total"] == 1
    assert m["historico"]["total"] == 4  # Exclui a entrada de segunda-feira 05/01.
    assert m["historico"]["conversao"] == .5
    assert m["perdas"].loc[3, "valor"] == 300.
    assert {c["canal"]: c["conversao"] for c in m["canais"]} == {"A": 1., "B": 0.}


def test_semana_vazia_e_base_antiga_nao_sugerem_conversao_zero():
    m = calcular(dados_metricas(), date(2026, 9, 28))
    assert m["semana"]["conversao"] is None
    assert any("desatualizada" in a for a in m["avisos"])
    html = gerar_html(m, "entrada.csv")
    assert "Não aplicável" in html
    assert "Sem propostas na semana" in html


def test_html_escapa_texto_do_csv():
    df = dados_metricas()
    canal = '</script><script>alert(1)</script> & "ação" \\ \u2028\u2029'
    df.loc[1, "canal_origem"] = canal
    html = gerar_html(calcular(df, date(2026, 1, 5)), "<entrada>.csv")
    documento = analisar_html(html)
    assert set(documento.scripts) == {"dados-filtros", "interacao-filtros"}
    assert canal in json.loads(documento.scripts["dados-filtros"])["canais"]
    assert "&lt;script&gt;" in html
    assert "&lt;entrada&gt;" in html
    assert "Não representa o status conhecido naquela data" in html


class DocumentoHTML(HTMLParser):
    """Inspeção estrutural sem navegador ou dependências adicionais."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elementos = {}
        self.scripts = {}
        self.script_atual = None
        self.pilha = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        assert tag not in {"iframe", "object", "embed", "link", "base"}
        assert not any(nome in attrs for nome in ("src", "srcset", "href"))
        assert not any(nome.startswith("on") for nome in attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.elementos
            self.elementos[attrs["id"]] = (tag, attrs)
        if tag == "script":
            self.script_atual = attrs["id"]
            self.scripts[self.script_atual] = ""
        if tag not in {"meta", "br"}:
            self.pilha.append(tag)

    def handle_endtag(self, tag):
        assert self.pilha.pop() == tag
        if tag == "script":
            self.script_atual = None

    def handle_data(self, data):
        if self.script_atual is not None:
            self.scripts[self.script_atual] += data


def analisar_html(html):
    documento = DocumentoHTML()
    documento.feed(html)
    documento.close()
    assert not documento.pilha
    return documento


def test_html_contem_controles_json_minimo_e_nenhum_recurso_externo():
    html = gerar_html(calcular(dados_metricas(), date(2026, 1, 5)), "entrada.csv")
    doc = analisar_html(html)
    assert doc.elementos["filtro-canal"][0] == "select"
    assert doc.elementos["filtro-etapa"][0] == "select"
    assert doc.elementos["limpar-filtros"][0] == "button"
    assert '<option value="0">Todos</option>' in html
    assert '<option value="0">Todas</option>' in html
    assert doc.elementos["dados-filtros"][1]["type"] == "application/json"
    dados = json.loads(doc.scripts["dados-filtros"])
    assert set(dados) == {"canais", "resultados"}
    assert dados["resultados"][0][0] == ["2", "1", "50,00%", "500,00", "300,00"]
    assert "id_proposta" not in doc.scripts["dados-filtros"]
    assert not any(s in html.lower() for s in ("http://", "https://", "fetch(", "xmlhttprequest", "@import", "url("))
    assert "Semana anterior, acumulado e tabelas abaixo permanecem sem filtros" in html


def test_filtros_intersecao_uma_proposta_e_zero_resultados():
    dados = calcular(dados_metricas(), date(2026, 1, 5))["filtros"]
    assert dados["canais"] == ["A", "B"]
    # Canal A, todas as etapas: uma proposta, inteiramente contratada.
    assert dados["resultados"][1][0] == ["1", "1", "100,00%", "200,00", "0,00"]
    assert dados["resultados"][1][6] == dados["resultados"][1][0]
    # Canal B + etapa 3: apenas a proposta não contratada.
    assert dados["resultados"][2][3] == ["1", "0", "0,00%", "300,00", "300,00"]
    assert dados["resultados"][1][3] == ["0", "0", "Não aplicável", "0,00", "0,00"]
    assert dados["resultados"][0][3] == dados["resultados"][2][3]


def test_coorte_vazia_e_campos_opcionais_ausentes():
    df = dados_metricas()
    df["taxa_juros_aa"] = None
    df["data_assinatura_contrato"] = pd.NaT
    assert calcular(df, date(2026, 1, 5))["filtros"] == calcular(dados_metricas(), date(2026, 1, 5))["filtros"]
    dados = calcular(df, date(2026, 9, 28))["filtros"]
    assert dados["canais"] == []
    assert all(v == ["0", "0", "Não aplicável", "0,00", "0,00"] for v in dados["resultados"][0])


def test_arredondamento_dos_filtros_usa_o_mesmo_formatador_python():
    df = dados_metricas().iloc[[1]].copy()
    df["valor_solicitado"] = 1234.125  # Empate: Python apresenta 1.234,12.
    assert preparar_filtros(df)["resultados"][0][0] == ["1", "1", "100,00%", "1.234,12", "0,00"]


def test_exemplo_sem_filtros_preserva_os_cinco_indicadores():
    df = ler_e_tratar(RAIZ / "dados_brutos/Propostas_credito.csv")
    m = calcular(df, date(2025, 10, 27))
    esperado = ["29", "5", "17,24%", "11.240.777,45", "9.710.882,51"]
    assert m["filtros"]["resultados"][0][0] == esperado
    html = gerar_html(m, "entrada.csv")
    for valor in esperado:
        assert f"<td>{valor}</td>" in html


@pytest.mark.parametrize("vazia", [False, True])
def test_javascript_aplica_combina_limpa_e_preserva_colunas_historicas(vazia):
    # Opcional: usa somente um Node já disponível; nunca instala um runtime.
    node = os.environ.get("BARI_NODE") or shutil.which("node")
    if not node:
        pytest.skip("Node não disponível; cálculos e contrato HTML cobertos pelos testes Python.")
    m = calcular(dados_metricas(), date(2026, 9, 28) if vazia else date(2026, 1, 5))
    runner = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const entrada = JSON.parse(fs.readFileSync(0, 'utf8'));
const nodes = {};
function select(labels) {
    return {value: '0', options: labels.map(textContent => ({textContent})),
        get selectedIndex() { return Number(this.value); },
        addEventListener(event, callback) { this[event] = callback; }};
}
nodes['dados-filtros'] = {textContent: JSON.stringify(entrada.dados)};
nodes['filtro-canal'] = select(['Todos', ...entrada.dados.canais]);
nodes['filtro-etapa'] = select(['Todas', '1', '2', '3', '4', '5', '6']);
nodes['limpar-filtros'] = {addEventListener(event, callback) { this[event] = callback; }};
nodes['situacao-filtros'] = {textContent: ''};
nodes['controles-filtros'] = {disabled: true};
const rows = Array.from({length: 5}, () => ({cells: [
    {textContent: 'Indicador'}, {textContent: ''},
    {textContent: 'Anterior intacto'}, {textContent: 'Acumulado intacto'}]}));
const header = {textContent: 'Semana selecionada'};
nodes['resumo-semanal'] = {tHead: {rows: [{cells: [{}, header]}]}, tBodies: [{rows}]};
vm.runInNewContext(entrada.script, {document: {getElementById(id) { return nodes[id]; }}});
const valores = () => rows.map(r => r.cells[1].textContent);
const zero = ['0', '0', 'Não aplicável', '0,00', '0,00'];
const original = entrada.vazia ? zero : ['2', '1', '50,00%', '500,00', '300,00'];
assert.deepEqual(valores(), original);
assert.equal(nodes['controles-filtros'].disabled, false);
if (!entrada.vazia) {
    nodes['filtro-canal'].value = '1';
    nodes['filtro-canal'].change();
    assert.deepEqual(valores(), ['1', '1', '100,00%', '200,00', '0,00']);
    nodes['filtro-etapa'].value = '3';
    nodes['filtro-etapa'].change();
    assert.deepEqual(valores(), zero);
    assert.match(nodes['situacao-filtros'].textContent, /Sem propostas/);
    assert.equal(header.textContent, 'Semana selecionada — filtros aplicados');
    nodes['filtro-canal'].value = '2';
    nodes['filtro-canal'].change();
    assert.deepEqual(valores(), ['1', '0', '0,00%', '300,00', '300,00']);
}
nodes['limpar-filtros'].click();
assert.equal(nodes['filtro-canal'].value, '0');
assert.equal(nodes['filtro-etapa'].value, '0');
assert.equal(header.textContent, 'Semana selecionada');
assert.deepEqual(valores(), original);
rows.forEach(r => {
    assert.equal(r.cells[2].textContent, 'Anterior intacto');
    assert.equal(r.cells[3].textContent, 'Acumulado intacto');
});
"""
    resultado = subprocess.run([node, "-e", runner], input=json.dumps({
        "dados": m["filtros"], "script": SCRIPT_FILTROS, "vazia": vazia,
    }), capture_output=True, text=True, encoding="utf-8")
    assert resultado.returncode == 0, resultado.stderr


def test_falha_de_gravacao_atomica_preserva_relatorio(tmp_path, monkeypatch):
    destino = tmp_path / "relatorio.html"
    destino.write_text("anterior", encoding="utf-8")
    def falhar(*args):
        raise PermissionError("arquivo bloqueado")
    monkeypatch.setattr(os, "replace", falhar)
    with pytest.raises(PermissionError):
        gravar_html(destino, "novo")
    assert destino.read_text(encoding="utf-8") == "anterior"
    assert not list(tmp_path.glob("*.tmp"))


def test_falha_de_entrada_preserva_saida_anterior_e_registra_log(tmp_path):
    destino = tmp_path / "relatorio_2025-12-29_2026-01-04.html"
    destino.write_text("anterior", encoding="utf-8")
    retorno = main(["--entrada", str(tmp_path / "inexistente.csv"), "--saida", str(tmp_path),
                    "--data-referencia", "2026-01-05"])
    assert retorno == 1
    assert destino.read_text(encoding="utf-8") == "anterior"
    assert "FALHA" in destino.with_suffix(".log").read_text(encoding="utf-8")


def test_cli_fora_do_repositorio_e_reexecucao(tmp_path):
    comando = [sys.executable, str(RAIZ / "parte2_automacao/relatorio_semanal.py"),
               "--data-referencia", "2025-10-27", "--saida", str(tmp_path / "saida")]
    for _ in range(2):
        resultado = subprocess.run(comando, cwd=tmp_path, capture_output=True)
        assert resultado.returncode == 0, resultado.stderr.decode(errors="replace")
    arquivos = list((tmp_path / "saida").glob("*.html"))
    assert len(arquivos) == 1
    assert "20/10/2025 a 26/10/2025" in arquivos[0].read_text(encoding="utf-8")
    log = arquivos[0].with_suffix(".log").read_text(encoding="utf-8")
    assert log.count("SUCESSO") == 2


def test_saida_nunca_escreve_nos_dados_brutos():
    with pytest.raises(SystemExit) as erro:
        main(["--saida", "dados_brutos"])
    assert erro.value.code == 2
