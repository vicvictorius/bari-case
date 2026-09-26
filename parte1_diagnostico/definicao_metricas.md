# Definição de métricas operacionais — justificativa

Antes de responder as 4 perguntas da Parte 1 (diagnóstico do funil), duas métricas
precisavam de definição própria, já que não vêm prontas no dicionário de dados:
**conversão** e **dinheiro perdido por etapa**. Ambas foram calculadas em duas versões
candidatas e comparadas com números reais antes da escolha (ver
`02_comparacao_metricas.py`).

## 1. Conversão

| Opção | Cálculo | Resultado |
|---|---|---|
| [A] Contratada / total de propostas | 1.241 / 6.400 | **19,39%** |
| [B] Contratada / propostas que passaram da etapa 1 (Simulação) | 1.241 / 6.127 | 20,25% |

**Decisão: [A] — Contratada / total de propostas.**

- A diferença entre as duas é de apenas 0,86 p.p.: só 273 propostas (4,3% da base) ficam
  presas na etapa 1, então o denominador quase não muda o resultado.
- [A] responde diretamente à pergunta que a liderança fez ("a conversão caiu nos últimos
  meses?") — essa pergunta é sobre o funil de ponta a ponta, não sobre um subconjunto dele.
  Usar [B] exigiria justificar por que a etapa 1 foi excluída, o que é uma camada extra de
  argumentação sem ganho de precisão relevante.
- Conversão de ponta a ponta também é o padrão mais comum em relatórios de funil comercial —
  mais fácil de comparar com benchmarks externos, se necessário.

## 2. Dinheiro perdido por etapa

| Base de valor | Cálculo | Total perdido |
|---|---|---|
| [A] `valor_solicitado` | soma direta do principal pedido | **R$ 2.002,4 milhões** |
| [B] `valor_solicitado × taxa_juros_aa × prazo_meses` (receita potencial estimada) | usa a taxa média dos contratos fechados como proxy para quem não contratou | R$ 3.582,7 milhões |

**Decisão: [A] — `valor_solicitado`.**

- O ranking de "onde o funil mais perde valor" é **idêntico** nas duas versões
  (etapa 3 > etapa 4 > etapa 2 > etapa 5 > etapa 1) — ou seja, a escolha não muda a
  conclusão de negócio, só a magnitude em R$.
- [B] é conceitualmente mais completo (capta que juros diferentes representam receita
  diferente para o Bari), mas depende de uma premissa frágil: `taxa_juros_aa` só existe
  para as 1.241 propostas contratadas — para as demais 5.159, a taxa foi *estimada* usando
  a média dos contratos fechados, e o cálculo de receita usou juros simples sobre o prazo,
  sem amortização real. Isso empilha suposição sobre suposição.
- [A] é dado bruto do CSV, sem nenhuma estimativa — mais simples de defender linha por linha
  na banca, e como o ranking não muda, não há custo de diagnóstico em usar a versão mais
  simples.

## Princípio geral aplicado

Nos dois casos, a métrica mais simples foi preferida porque **não sacrificava poder de
diagnóstico** em troca de simplicidade — quando duas definições levam à mesma conclusão de
negócio, a que exige menos premissas auxiliares é a mais defensável.

Se em algum momento da análise o ranking de "etapa mais cara" ou a leitura de conversão se
mostrar sensível a essa escolha (por exemplo, ao segmentar por canal ou por tipo de imóvel),
isso será reavaliado e registrado aqui.