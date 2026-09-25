# Plano de Execução — Desafio Prático AI & Data Lab | Bari

## Contexto de negócio

Bari trabalha com crédito com garantia de imóvel (home equity). Ciclo da proposta:

**1. Simulação → 2. Lead → 3. Análise de crédito → 4. Avaliação do imóvel → 5. Formalização → 6. Contratação**

Cada etapa perde propostas por reprovação de crédito, problema na garantia, desistência ou documentação que não chega.

**Hipótese da liderança (não verificada) a confirmar/refutar/refinar:**
> "A conversão caiu nos últimos meses e o canal de correspondentes não está performando."

**Regra de negócio:** LTV máximo permitido = 60%.

**O que está sendo avaliado:** não o artefato final isolado, e sim o raciocínio — decisões tomadas, o que foi questionado, o que não se sabia e foi aprendido, e a capacidade de defender cada linha entregue. Uso crítico de IA pontua mais do que não usar IA.

---

## Etapas, prioridade e impacto

| # | Etapa | Prioridade | Impacto | Justificativa |
|---|---|---|---|---|
| 1 | **Profiling bruto do CSV** — nulos, duplicatas, tipos, valores únicos de `status_final`, `canal_origem`, `tipo_imovel` | Alta | Alto | Base para tudo. Sem mapear a sujeira, qualquer número da Parte 1 é frágil na defesa oral. |
| 2 | **Registro de tratamento de dados** — decisão de limpeza, linha a linha, com justificativa | Alta | Alto | Pedido explicitamente no enunciado; "toda decisão de limpeza é uma decisão de negócio disfarçada". Fazer junto com a etapa 1, não depois. |
| 3 | **Definir métricas operacionais** — o que é "conversão", "dinheiro perdido por etapa", como estimar impacto | Alta | Alto | Sem isso não dá para responder nenhuma das 4 perguntas da Parte 1 com solidez. É decisão de negócio, não código. |
| 4 | **Parte 1 — Diagnóstico do funil** (4 perguntas + 3 recomendações priorizadas com impacto estimado e premissas) | Alta | Alto | Core do case de negócio; maior peso avaliativo provável. |
| 5 | **Parte 3 — Extração dos laudos com IA** (17 laudos, campos estruturados, critério próprio de acerto, tratamento de campo ausente/contraditório) | Média | Médio-Alto | Independente das Partes 1/2, pode rodar em paralelo. É onde o uso crítico de IA fica mais visível. |
| 6 | **Parte 2 — Automação/RPA** (relatório semanal automatizado, tratamento de erro, log, robustez a mudanças no arquivo) | Média | Médio | Reaproveita a lógica da Parte 1, fica mais rápida se feita depois. Peso maior em engenharia/robustez do que em insight. |
| 7 | **Resumo executivo** (1 página, para liderança comercial, sem abrir código) | Baixo esforço / Alta visibilidade | Médio-Alto | Curto de fazer, mas é o que o avaliador ("liderança") provavelmente lê primeiro. |
| 8 | **DIARIO.md** (uso de IA, aprendizado do zero, autocrítica) | Alta (contínua) | Alto | Precisa ser alimentado durante as etapas 1–6, não reconstruído de memória no fim. |
| 9 | **README.md final** (como rodar, estrutura, tempo gasto) | Baixa | Baixo-Médio | Rápido, mas não esquecer de registrar tempo gasto por etapa. |

---

## Sequência recomendada de trabalho

1. **Etapas 1 + 2 + 3 juntas**, num único notebook/script de exploração inicial — já anotando achados para o DIARIO.
2. **Etapa 4** — Parte 1 completa.
3. **Etapa 8** roda em paralelo o tempo todo (documento vivo, não uma etapa isolada no fim).
4. **Etapas 5 e 6** podem ser paralelizadas; priorizar 5 antes de 6 se o tempo apertar, pelo maior peso no critério de uso de IA.
5. **Etapas 7 e 9** por último — mais rápidas, fecham a entrega.

---

## Entregáveis finais (checklist)

- [ ] `README.md` — como rodar, estrutura dos arquivos, tempo total gasto
- [ ] Script/Código/Notebook — Parte 1
- [ ] Script/Código/Notebook — Parte 2
- [ ] Script/Código/Notebook — Parte 3
- [ ] `DIARIO.md` — Parte 4 (máx. 2 páginas)
- [ ] Resumo executivo (1 página, PDF/slide/markdown) para liderança comercial
- [ ] Citação de dados/gráficos/fontes externas usados