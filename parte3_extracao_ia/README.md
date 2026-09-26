# Parte 3 — Extração com IA

Extrai 10 campos estruturados de cada um dos 17 laudos em texto livre
(`../dados_brutos/laudos_avaliacao/`): tipo de imóvel, endereço, área
privativa, área total, ano de construção, valor de avaliação, matrícula,
ônus, data da vistoria, responsável técnico.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `schema.py` | Contrato de dados (Pydantic): cada campo tem `valor` + `status` (presente/ausente/conflitante) + `trecho_bruto` de evidência |
| `extrator.py` | Pipeline via API da Anthropic (paga) — saída forçada por schema, valida, tenta de novo se inválido |
| `extrator_local.py` | **Pipeline usado nesta entrega**: mesmo schema/prompt, mas via modelo local (Ollama), sem custo |
| `construir_gabarito.py` | Gera `gabarito.json` a partir de uma leitura manual dos 17 laudos (rascunho para revisão — ver `decisoes.md`) |
| `avaliador.py` | Compara a saída do extrator contra `gabarito.json` e gera um relatório de acurácia por campo |
| `testes/test_avaliador.py` | Testes automatizados do avaliador, incluindo 3 erros típicos simulados e a normalização de valores |
| `testes/test_extrator_local.py` | Testes do extrator local com um cliente Ollama simulado (parsing/validação/retry) |
| `testes/test_schema.py` | Testes das regras de validação do schema (inclui regressão do bug do laudo_15) |
| `decisoes.md` | Todas as decisões de modelagem e suas justificativas, incluindo a troca API→local |

## Como rodar

```bash
pip install -r requirements.txt

# 1. gerar o gabarito
python construir_gabarito.py --saida gabarito.json

# 2a. rodar a extração via modelo local (gratuito — caminho usado nesta entrega)
#     pré-requisito: instalar Ollama (https://ollama.com) e baixar um modelo
#     -- ver decisoes.md para escolha de modelo conforme sua RAM
ollama pull qwen2.5:7b-instruct
python extrator_local.py --entrada ../dados_brutos/laudos_avaliacao --saida saida_extracao_local.json

# 2b. alternativa: extração via API da Anthropic (paga, mais precisa)
export ANTHROPIC_API_KEY="sua-chave"
python extrator.py --entrada ../dados_brutos/laudos_avaliacao --saida saida_extracao.json

# 3. medir a acurácia (mesmo avaliador para os dois caminhos)
python avaliador.py --extracao saida_extracao_local.json --gabarito gabarito.json --relatorio relatorio_acuracia.md

# testes (não precisam de Ollama nem de API key — usam clientes simulados/dados sintéticos)
python -m pytest testes/ -v
```

## Status nesta entrega

`gabarito.json` gerado e validado. Dois pipelines de extração escritos e
com a lógica de parsing/validação/retry testada: `extrator.py` (API da
Anthropic, paga) e `extrator_local.py` (Ollama, gratuito — caminho
escolhido para esta entrega por restrição de orçamento, ver `decisoes.md`).

**Nenhum dos dois foi executado contra um modelo real nesta sessão de
desenvolvimento** — o ambiente sandbox usado não tem `ANTHROPIC_API_KEY`
configurada nem acesso ao domínio `ollama.com`/GPU para baixar e rodar um
modelo local de verdade. `avaliador.py` foi testado com dados sintéticos
(`testes/fixture_extracao_com_erros_sinteticos.json`, claramente marcado
como não-real) para provar que o critério de acurácia detecta erros de
fato — ver `testes/relatorio_demo_SINTETICO.md` para um exemplo do formato
do relatório.

**Pendência antes da entrega final**: instalar o Ollama, baixar o modelo,
rodar `extrator_local.py` de verdade e substituir a demonstração sintética
pelo `relatorio_acuracia.md` real.
