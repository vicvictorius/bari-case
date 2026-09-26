# Parte 1 — Diagnóstico do funil

Métricas usadas: conversão = Contratada / total de propostas (19,39%); valor solicitado não contratado =
soma de `valor_solicitado` das propostas não contratadas (ver `definicao_metricas.md`).
Evidência completa em `03_diagnostico_funil.py` / `03_diagnostico_output.txt`.

## 1. Onde o funil perde mais valor?

| Etapa | Propostas não contratadas | Valor solicitado não contratado | % do total não contratado |
|---|---:|---:|---:|
| 3 — Análise de crédito | 1.799 | **R$ 703,0 mi** | **35,1%** |
| 4 — Avaliação do imóvel | 1.267 | R$ 497,0 mi | 24,8% |
| 2 — Lead | 984 | R$ 375,0 mi | 18,7% |
| 5 — Formalização | 836 | R$ 322,8 mi | 16,1% |
| 1 — Simulação | 273 | R$ 104,6 mi | 5,2% |

**Etapa 3 (Análise de crédito) é o maior ponto de perda**, tanto em quantidade de propostas
quanto em valor — não é só "onde mais gente desiste", é onde o ticket médio das perdidas
(R$ 390.798) também é ligeiramente acima da média geral (R$ 384.244), então não há efeito
de "perde muita gente, mas de ticket pequeno" disfarçando o problema.

Olhando por **motivo** de perda, um achado que contraria a leitura mais óbvia: somando
`Sem retorno` (31,5% do valor) e `Desistiu` (29,3%), **60,8% do valor solicitado não contratado está
associado a desengajamento do cliente — não reprovação de crédito** (17,6%).

Cruzando etapa × status, na própria etapa 3 as três causas (`Desistiu`, `Reprovada crédito`
e `Sem retorno`) aparecem quase empatadas: **614 / 608 / 577 propostas**, respectivamente.

Ou seja, mesmo no gargalo mais caro do funil, o problema não é predominantemente
"a política de crédito reprova demais". Existe também uma parcela relevante de propostas
que sai por desistência ou falta de retorno.

---

## 2. A percepção da liderança se confirma?

> "A conversão caiu nos últimos meses e o canal de correspondentes não está performando."

**Parcialmente confirmada — com ressalvas importantes.**

### Conversão caiu?

Sim, existe um sinal de queda nos dados, mas sua magnitude é moderada.

- Conversão de 2024: **20,4%**
- Conversão de 2025, considerando meses maduros de janeiro a outubro: **18,7%**
- Diferença: **-1,7 ponto percentual**
- 1º semestre de 2025: **19,3%**
- Julho a outubro de 2025: **16,9%**
- Tendência linear estimada: aproximadamente **-0,078 p.p. por mês**

Novembro e dezembro foram excluídos dessa comparação porque existem propostas recentes
que ainda podem não ter tido tempo suficiente para chegar ao final do funil. O campo
`tempo_analise_dias` chega a aproximadamente 78 dias, portanto incluir esses meses poderia
reduzir artificialmente a conversão observada por efeito de maturação da coorte.

O período de julho a outubro apresenta conversão inferior ao primeiro semestre, o que
reforça o sinal de queda. Entretanto, a série disponível não é suficiente para concluir
que existe uma aceleração estrutural dessa queda.

A leitura mais defensável é: **há sinal de deterioração, mas ele é moderado**, não uma
queda brusca. Vale tratar como sinal de atenção, não como crise.

### Canal de correspondentes não está performando?

Os dados confirmam uma **conversão observada inferior nos Correspondentes**:

- Conversão do canal Correspondente: **14,3%**, contra aproximadamente **20,7%–22,3%**
  dos demais canais.
- A diferença aparece de forma recorrente ao longo da série mensal.
- A participação do canal Correspondente no mix aumentou de **26,5% em 2024 para
  28,5% em 2025**.

Com maior participação de um canal que apresenta menor conversão observada, aumenta também
sua influência sobre a conversão agregada.

Os dados, porém, **não permitem atribuir essa diferença diretamente à qualidade do canal**.
Correspondentes podem receber propostas com distribuições diferentes de score, LTV, ticket
ou outras características. Portanto, a diferença observada deve ser investigada antes de
ser interpretada como falha operacional do canal.

**Confiança nessa resposta: moderada.**

A tendência de queda da conversão é consistente, mas a série cobre aproximadamente dois
anos e não permite separar completamente efeitos estruturais de possíveis efeitos de
sazonalidade.

O achado descritivo do canal Correspondente é mais consistente, pois a diferença observada
é maior e aparece ao longo do tempo. Ainda assim, esta análise não controla simultaneamente
as demais características das propostas.

---

## 3. Quais características mais se associam à contratação?

Para comparar características com escalas diferentes, usei como medida descritiva a
**amplitude da taxa de contratação entre grupos** de cada variável.

| Característica | Grupo com maior conversão | Grupo com menor conversão | Amplitude observada |
|---|---:|---:|---:|
| **Score de crédito** | >750: **31,6%** | ≤500: 1,2% | **30,4 p.p.** |
| **LTV** | 40–50%: 23,0% | >60%: **12,6%** | **10,4 p.p.** |
| **Canal de origem** | Parceria: 22,3% | Correspondente: 14,3% | **8,0 p.p.** |
| **Cliente recorrente** | Sim: 23,5% | Não: 18,4% | **5,1 p.p.** |
| **Ticket** | Q1: 20,8% | Q4: 17,5% | **3,3 p.p.** |
| **Tipo de imóvel** | Terreno: 21,1% | Casa: 18,2% | **2,9 p.p.** |
| **Prazo** | 181–240 meses: 20,7% | 121–180 meses: 18,8% | **1,9 p.p.** |

Pela métrica utilizada, **score de crédito apresenta a maior associação descritiva com
contratação** entre as características analisadas.

A diferença entre propostas com score acima de 750 e aquelas com score até 500 chega a
**30,4 pontos percentuais**, amplitude muito superior às demais variáveis.

LTV e canal de origem aparecem em seguida.

É importante separar **associação de causalidade**. Essa análise compara grupos de forma
descritiva e univariada. Ela não controla simultaneamente score, LTV, canal, ticket e demais
características.

Portanto, esses resultados ajudam a identificar segmentos que merecem investigação e
priorização, mas não demonstram que alterar isoladamente uma dessas características
causaria o aumento observado na contratação.

---

## 4. Três recomendações acionáveis

### 1ª prioridade — Follow-up ativo durante a Análise de Crédito

**O quê:** criar acompanhamento específico para propostas na etapa 3 que apresentam risco
de saída por `Sem retorno` ou `Desistiu`, priorizando inicialmente propostas de maior valor
solicitado.

Na etapa 3, esses dois motivos somam:

- **1.191 propostas**
- aproximadamente **R$ 471,7 milhões em valor solicitado**

Isso concentra a ação no mesmo estágio identificado como a maior concentração de valor
solicitado não contratado do funil.

**Impacto estimado:** em um cenário de sensibilidade no qual uma intervenção de processo
recuperasse **10% do valor associado a essas propostas**, a oportunidade seria equivalente
a aproximadamente:

- **119 propostas**
- **R$ 47,2 milhões** em crédito adicional ao longo do período da base (~2 anos)

**Premissa assumida:** os 10% representam uma hipótese de sensibilidade para dimensionar a
oportunidade. Não há experimento na base que permita afirmar que uma ação de follow-up
causaria essa recuperação.

Portanto, **R$ 47,2 milhões não é uma previsão de receita nem um efeito causal medido**;
deve ser interpretado como dimensão de oportunidade sob essa hipótese.

---

### 2ª prioridade — Revisar o canal Correspondente (qualificação + investigação do perfil das propostas)

**O quê:** o canal converte a **14,3%**, contra aproximadamente **20,7%–22,3%** dos demais,
e sua participação aumentou de **26,5% para 28,5%**.

A primeira ação deveria ser investigar se existem diferenças sistemáticas no perfil das
propostas recebidas pelo canal.

Em paralelo, podem ser avaliadas ações como:

- padronização dos critérios de qualificação do lead;
- revisão da triagem antes do envio ao Bari;
- treinamento dos parceiros correspondentes nos critérios da política de crédito.

**Impacto estimado:** se a conversão do canal subisse de **14,3%** para aproximadamente
a média observada nos demais canais (**~21,4%**), isso equivaleria a cerca de:

- **126 propostas adicionais**
- aproximadamente **R$ 48 milhões** em crédito adicional

Esse cálculo representa um **cenário de oportunidade**, não uma previsão de resultado.

**Premissa assumida:** uma parcela da diferença de conversão pode estar relacionada à
qualificação/origem do lead.

Essa hipótese **não foi testada de forma multivariada**. O canal Correspondente pode receber
clientes com score, LTV ou outros perfis sistematicamente diferentes dos demais.

Essa composição deve ser investigada antes de atribuir a diferença a uma falha operacional
ou realizar investimento relevante no canal.

---

### 3ª prioridade — Validar e operacionalizar a política de LTV de 60%

**O quê:** **981 propostas (15,3% da base)** apresentam LTV calculado acima de 60%, apesar
de o enunciado informar que o LTV máximo permitido é 60%.

Entretanto, **124 dessas propostas aparecem como `Contratada`**.

Entre essas contratações com LTV acima de 60%:

- LTV mínimo: **60,07%**
- LTV mediano: **63,29%**
- LTV médio: **64,15%**
- LTV máximo: **79,0%**

A distribuição também mostra que o fenômeno não está restrito apenas a valores muito
próximos de 60%, portanto não parece ser explicado apenas por arredondamento.

Antes de implementar qualquer bloqueio automático, é necessário validar com as áreas de
negócio e crédito:

1. se o LTV calculado na análise (`valor_solicitado / valor_imovel`) corresponde exatamente
   à medida utilizada pela política;
2. se existem exceções formais à regra de 60%;
3. se o valor solicitado ou o valor do imóvel pode ser renegociado durante o processo;
4. se há alguma diferença entre o valor disponível na base e o valor utilizado na decisão
   final de crédito.

**Impacto esperado:** a primeira entrega dessa recomendação não é necessariamente aumento
de conversão, mas **redução de ambiguidade operacional e prevenção de uma automação baseada
em uma interpretação possivelmente incompleta da regra**.

Depois da validação, a política pode ser operacionalizada de forma adequada por meio de
alerta, renegociação ou bloqueio na entrada, conforme a regra real utilizada pelo negócio.

**Premissa assumida:** o LTV foi calculado como `valor_solicitado / valor_imovel`, conforme
a interpretação adotada a partir dos campos disponíveis e do dicionário de dados.

A base, isoladamente, **não explica por que existem 124 contratos acima de 60%**. Portanto,
exceção de política, renegociação, diferença de definição ou problema semântico dos dados
permanecem hipóteses e não conclusões.

---

## Conclusão da Parte 1

A análise mostra que a maior concentração de valor solicitado não contratado está na
**Análise de Crédito**, responsável por **35,1% do valor solicitado não contratado**.

A percepção da liderança também encontra suporte parcial nos dados: existe um sinal de
queda da conversão e o canal Correspondente apresenta conversão observada inferior aos
demais, mas a magnitude da tendência e as causas da diferença exigem cautela.

Entre as características analisadas, **score de crédito apresenta a maior associação
descritiva com contratação**, seguido por LTV e canal de origem. Essas relações não devem
ser interpretadas como efeitos causais.

As recomendações priorizam:

1. atuar sobre desistência e falta de retorno no maior gargalo financeiro;
2. investigar e melhorar a operação do canal Correspondente sem assumir previamente que
   o canal é a causa da diferença;
3. esclarecer a aparente inconsistência entre a política de LTV de 60% e os contratos
   observados antes de automatizar qualquer regra de bloqueio.

Os impactos financeiros apresentados são **cenários de oportunidade condicionados às
premissas utilizadas**, e não previsões de receita.