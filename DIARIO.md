# Parte 4 — Diário de bordo

## a) Registro de uso de IA

Durante o desafio utilizei IA de duas formas: como **assistente de desenvolvimento** e como **componente da solução**. Usei principalmente Claude para apoiar discussões sobre profiling, tratamento dos dados, análise do funil, automação e arquitetura da extração. Na Parte 3, utilizei modelos locais via Ollama: Qwen3 1.7B e Qwen2.5 7B.

Procurei não assumir que uma resposta estava correta apenas porque o código executava. Na normalização de `canal_origem`, por exemplo, uma solução sugerida rodava sem erros, mas a inspeção do CSV mostrou que algumas variantes continuavam existindo. Identifiquei que os espaços precisavam ser tratados antes do mapeamento e corrigi a ordem da transformação.

Na extração dos laudos, o modelo chegou a produzir `status=presente` com `valor=None`. Em vez de corrigir apenas o prompt, adicionei validação no schema Pydantic e um teste de regressão. Também encontrei um erro no avaliador: valores equivalentes em representações numéricas ou formatos de data diferentes eram classificados como divergências. Corrigi a normalização e criei testes. Já erros reais do modelo, como a confusão entre `area_privativa_m2` e `area_total_m2`, foram mantidos na avaliação em vez de criar regras específicas para fazer a amostra passar.

A IA também apoiou o rascunho inicial do gabarito, posteriormente revisado manualmente. Por isso, documentei que ele não constitui um *gold standard* humano independente.

O principal aprendizado foi que a IA acelerou investigação e implementação, mas não substituiu **validação, testes, comparação dos resultados e responsabilidade técnica sobre a solução**.

## b) O que aprendi do zero

Aprendi **como avaliar de forma estruturada um extrator baseado em LLM**. Antes do projeto, eu sabia que um modelo poderia transformar texto em dados estruturados, mas não tinha uma metodologia clara para tornar essa avaliação mensurável e auditável.

Passei a separar três responsabilidades:

```text
LLM       → interpreta o documento
schema    → define e valida o contrato
avaliador → mede o resultado
```

Criei um gabarito de comparação e passei a distinguir **status correto** de **valor correto**. O Qwen2.5 7B, por exemplo, obteve 92,9% de acurácia de status nos 17 laudos, mas isso não significa que 92,9% dos valores foram extraídos corretamente.

Também aprendi que o próprio avaliador precisa ser testado: o bug de normalização mostrou que uma métrica incorreta pode levar a uma conclusão incorreta sobre o modelo. Ao final, deixei de enxergar uma integração com LLM apenas como `prompt → resposta` e passei a tratá-la como um sistema com contrato, validação, retry, referência de comparação e auditoria.

Não registrei separadamente as horas dedicadas exclusivamente a esse aprendizado, pois ele ocorreu junto à implementação e às rodadas de avaliação. Por isso, não atribuo uma estimativa que não foi medida.

## c) Autocrítica e o que faria com mais 40 horas

Com mais **40 horas**, minha primeira prioridade seria aumentar a confiabilidade da Parte 3. O benchmark possui apenas 17 laudos e o gabarito teve rascunho assistido por IA e revisão de uma única pessoa. Eu ampliaria a amostra, separaria dados de desenvolvimento e avaliação e utilizaria revisão humana independente.

Também evoluiria o schema para representar melhor informações presentes, mas não documentalmente verificadas, e revisaria a modelagem das diferentes áreas dos imóveis.

Na Parte 1, buscaria histórico de eventos do funil para investigar tempo entre etapas, períodos de espera, retornos e motivos operacionais de abandono. O dataset atual mostra melhor o resultado final do que o processo que levou até ele, limitando conclusões causais.

Na Parte 2, aproximaria a automação de um cenário operacional com agendamento, monitoramento das execuções, alertas de falha e histórico dos relatórios.

Minha principal autocrítica é que algumas decisões foram tomadas com amostra pequena e dados limitados sobre o processo. Com mais tempo, eu priorizaria **validar melhor as conclusões antes de aumentar a complexidade da solução**.

## d) Pergunta de negócio que eu faria ao Bari

> **Quais eventos e motivos operacionais acontecem entre a entrada de uma proposta na análise de crédito e sua saída dessa etapa, especialmente nos casos classificados como "Sem retorno" ou "Desistiu"?**

A análise identificou a etapa de Análise de Crédito como o maior ponto de valor solicitado não contratado e mostrou quantidade relevante de propostas terminando como `Sem retorno` ou `Desistiu`. Entretanto, o dataset não explica completamente o processo anterior a esses desfechos.

Eu buscaria entender quem precisava responder, tempo de espera, documentos pendentes, tentativas de contato, SLAs e motivos reais de desistência. Isso permitiria diferenciar falta de resposta do cliente, demora documental, perda de competitividade e atrasos internos.

Com esse contexto, a recomendação poderia evoluir de uma oportunidade descritiva para uma intervenção específica de comunicação, processo, SLA, documentação, produto ou acompanhamento comercial. **Eu não atribuiria uma causa apenas a partir do dataset fornecido; validaria o mecanismo com as pessoas que conhecem a operação.**