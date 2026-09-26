# Parte 4 — Diário de bordo

## a) Registro de uso de IA

Durante o desafio utilizei IA de duas formas: como **assistente de desenvolvimento** e como **componente da solução**. Usei principalmente Claude para discutir profiling, tratamento dos dados, análise do funil, automação e arquitetura da extração. Na Parte 3, utilizei modelos locais via Ollama: primeiro Qwen3 1.7B e depois Qwen2.5 7B.

Procurei não assumir que uma resposta estava correta apenas porque o código executava. Na normalização de `canal_origem`, por exemplo, o tratamento sugerido rodava sem erros, mas a inspeção do CSV mostrou que algumas variantes continuavam existindo. Identifiquei que os espaços precisavam ser tratados antes do mapeamento e corrigi a ordem da transformação.

Na extração dos laudos encontrei outro problema: o modelo conseguiu produzir `status=presente` com `valor=None`. Em vez de tentar resolver apenas pelo prompt, adicionei validação no schema Pydantic e um teste de regressão. Isso reforçou que **o prompt orienta o modelo, mas a aplicação continua responsável por validar sua saída**.

Também descobri um erro no próprio avaliador: valores equivalentes em representações numéricas ou formatos de data diferentes eram classificados como divergências. Ajustei a normalização e criei testes para esses casos. Já erros como a confusão entre `area_privativa_m2` e `area_total_m2` pelo Qwen3 foram preservados no relatório, em vez de criar regras específicas para fazer a amostra passar.

A IA também apoiou o rascunho inicial do gabarito, posteriormente revisado manualmente. Por isso, documentei que ele não constitui um *gold standard* humano totalmente independente.

Meu principal aprendizado foi que a IA acelerou investigação e implementação, mas não substituiu **validação, testes, comparação dos resultados e responsabilidade técnica sobre a solução**.

## b) O que aprendi do zero

Um conceito que aprendi durante o desafio foi **como avaliar de forma estruturada um extrator baseado em LLM**.

Antes do projeto, eu sabia que um modelo poderia transformar texto em uma resposta estruturada, mas não tinha uma metodologia clara para transformar a percepção de que uma extração "parece correta" em algo mensurável e auditável.

Durante a Parte 3, passei a separar as responsabilidades:

```text
LLM       → interpreta o documento
schema    → define e valida o contrato
avaliador → mede o resultado
```

Criei um gabarito para comparação e passei a distinguir **status correto** de **valor correto**. Essa diferença foi importante: o Qwen2.5 7B obteve 92,9% de acurácia geral de status nos 17 laudos, mas isso não significa que 92,9% dos valores foram extraídos perfeitamente.

Também aprendi que o próprio processo de avaliação precisa ser testado. O bug de normalização mostrou que uma métrica incorreta pode produzir uma conclusão incorreta sobre o modelo.

Meu aprendizado ocorreu principalmente no ciclo:

```text
implementação → execução → inspeção das divergências
→ identificação da causa → correção → teste → nova avaliação
```

Não registrei separadamente as horas dedicadas exclusivamente a esse conceito; ele foi aprendido ao longo da implementação e das rodadas de avaliação. Por isso, prefiro não apresentar uma estimativa de tempo que não foi medida.

Ao final, deixei de enxergar uma integração com LLM apenas como `prompt → resposta` e passei a enxergá-la como um sistema que precisa de contrato, validação, retry, referência de comparação e auditoria.

## c) Autocrítica e o que faria com mais 40 horas

O projeto atende ao objetivo do desafio, mas ainda existem limitações importantes antes de aproximá-lo de um cenário de produção.

Com mais **40 horas**, minha primeira prioridade seria aumentar a confiabilidade da Parte 3. O benchmark possui apenas 17 laudos e o gabarito teve rascunho assistido por IA e revisão de uma única pessoa. Eu ampliaria a amostra, separaria dados de desenvolvimento e avaliação e utilizaria revisão humana independente do gabarito.

Também evoluiria o schema. Durante a análise encontrei informações presentes, mas não documentalmente verificadas. Um estado como `nao_verificado` representaria melhor esses casos. Revisaria ainda a modelagem das áreas para diferenciar conceitos como área construída, terreno, privativa e total.

Na Parte 1, aprofundaria a análise com histórico de eventos do funil. O dataset atual permite observar o resultado final, mas não reconstruir completamente tempo entre etapas, períodos de espera, retornos e motivos operacionais de abandono. Esses dados seriam importantes para testar as hipóteses levantadas sem transformar associação em causalidade.

Por fim, aproximaria a Parte 2 de uma rotina operacional, adicionando agendamento, monitoramento das execuções, alertas de falha e histórico dos relatórios.

Minha principal autocrítica é que algumas decisões foram necessariamente tomadas com uma amostra pequena e dados que mostram o resultado das propostas melhor do que o processo que levou até ele. Com mais tempo, eu priorizaria **validar melhor as conclusões antes de aumentar a complexidade da solução**.

## d) Pergunta de negócio que eu faria ao Bari

> **Quais eventos e motivos operacionais acontecem entre a entrada de uma proposta na análise de crédito e sua saída dessa etapa, especialmente nos casos classificados como "Sem retorno" ou "Desistiu"?**

A análise identificou a etapa de análise de crédito como o maior ponto de perda de valor do funil e mostrou uma quantidade relevante de propostas terminando como `Sem retorno` ou `Desistiu`. Entretanto, o dataset não explica completamente o processo que aconteceu antes desse resultado.

Eu gostaria de entender quem precisava responder, quanto tempo a proposta permaneceu parada, quais documentos estavam pendentes, quantas tentativas de contato ocorreram, se existia SLA e qual foi o motivo real da desistência.

Isso permitiria separar situações diferentes que hoje podem aparecer sob o mesmo status: falta de resposta do cliente, demora documental, perda de competitividade da proposta ou atraso interno.

Com esse contexto, a recomendação sobre a etapa 3 poderia deixar de ser apenas "reduzir perdas na análise de crédito" e se transformar em uma intervenção específica de comunicação, processo, SLA, documentação, produto ou acompanhamento comercial.

Eu não tentaria inferir esse mecanismo apenas a partir do dataset fornecido. Antes de atribuir uma causa à perda observada, validaria o contexto com as pessoas que conhecem a operação.