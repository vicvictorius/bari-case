# Parte 1 — Diagnóstico do funil

Métricas usadas: conversão = Contratada / total de propostas (19,39%); dinheiro perdido =
soma de `valor_solicitado` das propostas não contratadas (ver `definicao_metricas.md`).
Evidência completa em `02_diagnostico_funil.py` / `diagnostico_output.txt`.

## 1. Onde o funil perde mais valor?

| Etapa | Propostas perdidas | Valor perdido | % do total perdido |
|---|---|---|---|
| 3 — Análise de crédito | 1.799 | **R$ 703,0 mi** | **35,1%** |
| 4 — Avaliação do imóvel | 1.267 | R$ 497,0 mi | 24,8% |
| 2 — Lead | 984 | R$ 375,0 mi | 18,7% |
| 5 — Formalização | 836 | R$ 322,8 mi | 16,1% |
| 1 — Simulação | 273 | R$ 104,6 mi | 5,2% |

**Etapa 3 (Análise de crédito) é o maior ponto de perda**, tanto em quantidade de propostas
quanto em valor — não é só "onde mais gente desiste", é onde o ticket médio das perdidas
(R$ 390.798) também é ligeiramente acima da média geral (R$ 384.244), então não tem efeito
de "perde muita gente, mas de ticket pequeno" disfarçando o problema.

Olhando por **motivo** de perda, um achado que contraria a leitura mais óbvia: somando
`Sem retorno` (31,5% do valor) e `Desistiu` (29,3%), **60,8% do valor perdido é
desengajamento do cliente — não reprovação de crédito** (17,6%). Cruzando etapa × status,
na própria etapa 3 as três causas (desistiu, reprovada crédito, sem retorno) aparecem quase
empatadas (614 / 608 / 577 propostas) — ou seja, mesmo no gargalo mais caro do funil, o
problema não é predominantemente "a política de crédito reprova demais", é também (e talvez
mais) "o cliente esfria/some enquanto espera".

## 2. A percepção da liderança se confirma?

> "A conversão caiu nos últimos meses e o canal de correspondentes não está performando."

**Parcialmente confirmada — com ressalvas importantes.**

**Conversão caiu?** Sim, mas de forma modesta, não abrupta:
- 2024 (ano cheio): 20,4% | 2025 (jan–out, período maduro): 18,7% → queda de **1,7 p.p.**
- 1º semestre de 2025: 19,3% | 2º semestre (jul–out): 16,9% → a queda parece estar
  **acelerando no período mais recente**
- Tendência linear mês a mês: -0,078 p.p./mês (leve, mas consistente com direção de queda)

Excluí novembro e dezembro/2025 desse cálculo porque `tempo_analise_dias` chega a 78 dias —
propostas muito recentes podem não ter tido tempo hábil de fechar, o que inflaria uma queda
artificial nesses meses (censura à direita). Mesmo maduro, o sinal de queda é real, mas
**moderado**, não uma queda brusca — vale tratar como sinal de atenção, não como crise.

**Canal de correspondentes não está performando?** Sim, isso está bem confirmado:
- Conversão do canal Correspondente: **14,3%**, contra 20,7%–22,3% dos outros 4 canais —
  a diferença é grande e consistente ao longo de quase todos os meses da série (a maioria
  entre 8% e 18%, sempre abaixo dos outros canais).
- **Mas atenção ao que a liderança pode estar presumindo errado**: o volume do canal
  Correspondente não está encolhendo — pelo contrário, sua participação no mix cresceu de
  26,5% (2024) para 28,5% (2025). Ou seja, o canal não está "perdendo força" em volume,
  está **crescendo em participação e arrastando a conversão geral para baixo** justamente
  por isso. É um problema de qualidade do canal, não de abandono do canal.

**Confiança nessa resposta:** moderada. A amostra mensal é pequena em alguns meses (ex:
70–27 propostas em nov/dez de 2025), o que aumenta ruído estatístico na cauda da série. A
tendência de queda de conversão é consistente mas não é grande o suficiente para afirmar com
certeza alta que é uma mudança estrutural — poderia também ser sazonalidade não observada em
só ~2 anos de dados. O achado do canal Correspondente é mais robusto (diferença grande,
padrão estável ao longo do tempo).

## 3. Quais características mais se associam à contratação?

Ranqueado por força do efeito na conversão (maior variação entre categorias = mais associado):

| Variável | Faixa/categoria com melhor conversão | Faixa/categoria com pior conversão | Amplitude |
|---|---|---|---|
| **Score de crédito** | >750: **31,6%** | ≤500: 1,2% | **30,4 p.p.** — de longe o maior efeito |
| **LTV** | 40–50%: 23,0% | >60% (fora da política): **12,6%** | 10,4 p.p. |
| **Canal de origem** | Parceria: 22,3% | Correspondente: 14,3% | 8,0 p.p. |
| **Cliente recorrente** | Sim: 23,5% | Não: 18,4% | 5,1 p.p. |
| **Tipo de imóvel** | Terreno: 21,1% | Casa: 18,2% | 2,9 p.p. |
| **Ticket (valor solicitado)** | Q1 (menor): 20,8% | Q4 (maior): 17,5% | 3,3 p.p. |
| **Prazo** | 181–240 meses: 20,7% | 121–180: 18,8% | 1,9 p.p. |

`score_credito` domina isoladamente — é o fator mais associado à contratação, e por uma
margem grande. `LTV` confirma a lógica da política: propostas acima do limite de 60%
convertem quase metade do que as na faixa 40–50%. Região (UF) tem alguma variação (GO 23,4%
vs RJ 17,6%) mas com volumes menores por estado, então tratei como sinal mais fraco/menos
confiável que os cinco primeiros.

## 4. Três recomendações priorizadas

### 1ª prioridade — Reduzir "sem retorno" e "desistência" com follow-up ativo na análise de crédito
**O quê:** SLA de resposta mais curto e contato proativo (não passivo) durante a etapa 3,
que hoje concentra o maior volume de `Sem retorno` (577) e `Desistiu` (614) combinados.

**Impacto estimado:** se 10% das propostas hoje perdidas por `Sem retorno` + `Desistiu`
(3.131 propostas) passassem a contratar, seriam ~313 propostas adicionais × ticket médio
(R$ 384 mil) ≈ **R$ 120 milhões** em valor de crédito adicional capturado ao longo do
período da base (~2 anos).

**Premissa assumida:** 10% é uma estimativa conservadora de melhoria por intervenção de
processo (SLA/cadência), não uma medição — não há dado de "motivo de sem retorno/desistência"
na base para calibrar melhor. É o número mais frágil das três recomendações, mas o maior
volume de propostas afetadas também torna qualquer ganho, mesmo pequeno, financeiramente
relevante.

### 2ª prioridade — Reformar o canal Correspondente (treinamento + triagem de lead na entrada)
**O quê:** o canal converte a 14,3% contra 20,7%–22,3% dos demais, e está crescendo em
participação (26,5% → 28,5%). Ação: padronizar critério de qualificação do lead antes do
envio ao Bari (reduzir volume de propostas mal ajustadas desde a origem) e/ou treinar
parceiros correspondentes nos critérios de política de crédito.

**Impacto estimado:** se a conversão do canal subisse de 14,3% para a média dos outros 4
canais (~21,4%), seriam 1.772 × (21,4% − 14,3%) ≈ **126 propostas adicionais** × ticket
médio ≈ **R$ 48 milhões** em valor de crédito adicional capturado.

**Premissa assumida:** que a diferença de conversão é majoritariamente qualidade/origem do
lead, não composição de perfil de cliente diferente por canal — não testei isso
estatisticamente (ex: correspondente poderia atrair clientes com score/LTV
sistematicamente piores por natureza do canal, e não por falha operacional). Vale validar
antes de investir pesado na reforma.

### 3ª prioridade — Pré-filtro de LTV acima de 60% antes da etapa de análise de crédito
**O quê:** 981 propostas (15,3% da base) já entram com LTV acima do limite de política e
convertem a apenas 12,6% — abaixo até da faixa >750 de score inverso. Hoje elas consomem
capacidade de análise na etapa mais cara do funil (etapa 3) antes de serem reprovadas.
Ação: sinalizar/barrar essas propostas já na simulação (etapa 1) ou orientar renegociação de
valor solicitado/imóvel antes de formalizar entrada.

**Impacto estimado:** não é ganho direto de conversão (a maioria dessas propostas
provavelmente não fecharia de qualquer forma), mas libera capacidade operacional na etapa 3
— o maior gargalo do funil (35,1% do valor perdido, 1.799 propostas) — para propostas com
LTV saudável, potencialmente acelerando o ciclo (`tempo_analise_dias`) de todas as demais.

**Premissa assumida:** que o gargalo de etapa 3 é, ao menos em parte, de capacidade/tempo de
analista (não só de critério de aprovação) — não há dado direto de capacidade/headcount na
base para confirmar isso; é uma inferência a partir do volume concentrado na etapa.