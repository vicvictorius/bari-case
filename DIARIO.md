# Parte 4 — Diário de bordo

## a) Registro de uso de IA

**Ferramentas e para quê**

- **Claude (chat):** principal assistente. Usei para discutir o profiling e as decisões de tratamento, escrever boa parte do código e dos testes das três partes e, no fim, revisar o repositório inteiro contra o enunciado. As decisões de negócio (o que corrigir, o que manter, qual métrica usar) foram minhas; a IA propunha e eu aceitava, recusava ou pedia outra abordagem.
- **ChatGPT:** usado na etapa final, a partir de um prompt com a lista de correções levantadas na revisão.
- **Ollama com Qwen3 1.7B e Qwen2.5 7B:** não como assistente, mas como componente da solução na Parte 3.

**Situações em que a IA errou ou entregou algo incompleto**

1. **Normalização de canal.** Pedi para padronizar `canal_origem`. O código veio certo na aparência e rodou sem erro, mas, ao reabrir o CSV tratado, as variantes continuavam lá: três delas tinham espaço no final, e o mapeamento comparava `"mídia paga "` com `"mídia paga"`. Coloquei o `.str.strip()` antes do mapeamento e registrei o caso. Desde então passei a conferir a saída, não só a ausência de erro.
2. **Gabarito da Parte 3.** A IA fez o rascunho do gabarito dos 17 laudos. Na revisão, os laudos 7 (ano "informado pelo proprietário") e 17 (sem ônus "segundo o proprietário", sem certidão) tinham sido tratados como casos isolados. Percebi que eram o mesmo padrão, informação presente mas não verificada, e documentei isso como uma única limitação do schema. Não criei um quarto status porque a extração já estava rodando e mudar o contrato no meio invalidaria a comparação.
3. **Código "pronto" que nunca rodou.** A primeira versão da Parte 3 usava a API da Anthropic. O código tinha testes com cliente simulado, mas nunca foi executado de verdade, e eu não tinha como pagar a API. Pedi uma versão com Ollama e rodei na minha máquina. A GT 1030 (2 GB) só conseguia carregar uma fração do Qwen2.5 7B, então a primeira rodada completa foi com o Qwen3 1.7B. Foi essa execução real que revelou o `status=presente` com `valor=None` no laudo_15 e o bug de normalização do avaliador. Aprendi que teste com mock prova o encanamento, não o resultado.
4. **A própria revisão da IA errou.** Na revisão final, a IA afirmou que a região teria uma amplitude de conversão maior que ticket e tipo de imóvel, sugerindo mais importância. Quando a análise foi implementada, o teste qui-quadrado deu p ≈ 0,23: a diferença entre UFs não é significativa, e uma amplitude grande é esperada só por acaso com 10 grupos. Mantive a linha na tabela, mas com essa ressalva.
5. **Código da revisão final.** As correções da última rodada (regras genéricas no pipeline, script de estratificação, registro de falha na Parte 3) foram escritas pela IA. Eu revisei o diff, rodei a suíte completa (169 testes) e confirmei que o CSV tratado continuou idêntico byte a byte ao anterior antes de fazer o merge.

## b) O que aprendi do zero

Aprendi **como avaliar de forma estruturada um extrator baseado em LLM**. Eu sabia que um modelo podia transformar texto em dados, mas não tinha um método para medir se ele acertou.

Passei a separar três responsabilidades:

```text
LLM       → interpreta o documento
schema    → define e valida o contrato
avaliador → mede o resultado contra uma referência
```

A distinção mais importante foi entre **status correto** e **valor correto**. O Qwen2.5 7B chegou a 92,9% de acurácia de status, mas só 63,6% de acurácia de valor na mesma execução: acertar que o campo existe não é acertar o conteúdo. Também aprendi que o avaliador precisa de testes: o bug de normalização classificava `78.40` e `78,40` como diferentes, e eu teria concluído que o modelo era pior do que era.

**Onde aprendi:** principalmente nas execuções reais contra os 17 laudos, complementadas por conversas com o Claude sobre como validar saídas de LLM.

**Quanto tempo levou:** não cronometrei. Reconstruindo pelos commits, estimo cerca de **3h** dedicadas especificamente a esse aprendizado, boa parte na madrugada de 26/09, enquanto os modelos rodavam: estudar como validar saídas de LLM, desenhar o critério de avaliação, investigar o bug do `valor=None` e corrigir o avaliador. Esse tempo está dentro das ~7h–8h da Parte 3.

## c) Autocrítica

**O que está fraco:**

- A avaliação da Parte 3 usa só 17 laudos, e o prompt foi ajustado olhando para os mesmos laudos. Os números são otimistas para laudos novos.
- O gabarito teve rascunho da IA e revisão de uma única pessoa, eu.
- A Parte 1 é descritiva: a estratificação do Correspondente controla só o score, e nenhuma análise prova causa.
- O volume de código cresceu mais rápido do que a minha revisão linha a linha. Domino as decisões e o comportamento, e os testes cobrem os casos críticos, mas partes do HTML e do JavaScript do relatório eu conheço pelo comportamento, não linha por linha.

**Com mais 40 horas:**

1. Ampliar a amostra de laudos, separar desenvolvimento de avaliação e ter um segundo revisor independente para o gabarito.
2. Implementar o status `nao_verificado` no schema.
3. Na Parte 1, um modelo multivariado (score, LTV, canal e ticket juntos) e, com acesso a eventos do funil, analisar o tempo entre etapas.
4. Na Parte 2, agendamento real, alerta de falha e histórico dos relatórios.

**Pergunta que eu faria ao time de negócios antes de começar:**

> **O que acontece entre a entrada de uma proposta na análise de crédito e a saída como "Sem retorno" ou "Desistiu"?**

A etapa 3 concentra a maior perda de valor, e a maior parte não é reprovação. Mas a base mostra o desfecho, não o processo: quem precisava responder, quanto tempo esperou, que documento faltou, quantas tentativas de contato houve. Com isso, a recomendação de follow-up deixaria de ser uma estimativa descritiva e viraria uma intervenção específica. Eu não atribuiria uma causa só com o dataset; validaria com quem opera o funil.
