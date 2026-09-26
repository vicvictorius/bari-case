# Parte 4 — Diário de bordo

## a) Registro de uso de IA

Durante o desafio utilizei IA de duas formas diferentes: como **assistente de desenvolvimento** e como **componente da solução**. Usei principalmente **Claude** para discutir profiling, tratamento dos dados, análise do funil e arquitetura da solução de extração. Na Parte 3, utilizei **Ollama com Qwen3 1.7B** para realizar efetivamente a extração estruturada dos 17 laudos.

Procurei não assumir que uma resposta estava correta apenas porque o código executava. Um exemplo ocorreu na normalização de `canal_origem`: o tratamento sugerido rodava sem erros, mas, ao conferir o CSV resultante, percebi que algumas variantes continuavam existindo. O problema estava nos espaços em branco, que precisavam ser removidos antes do mapeamento. Corrigi a ordem do tratamento e registrei a decisão. Esse caso reforçou que **código que executa sem erro não significa resultado correto**.

Outro problema apareceu na extração dos laudos. O modelo conseguiu produzir `status=presente` enquanto `valor=None`, um estado contraditório que o schema inicialmente aceitava. Em vez de tentar resolver somente pelo prompt, adicionei uma validação no schema para impedir essa combinação e um teste de regressão. Aprendi que **o prompt orienta o modelo, mas a aplicação ainda precisa validar sua saída**.

Também encontrei um problema no próprio processo de avaliação. Inicialmente, valores equivalentes representados de formas diferentes, como `1.234,5` e `1234.5`, ou datas em formatos distintos, eram classificados como erros. Ajustei a normalização para comparar o significado dos valores em vez das strings originais.

Nem todo problema pôde ser corrigido em código. O Qwen3 1.7B apresentou casos em que confundiu `area_privativa_m2` e `area_total_m2`. Preferi documentar essa limitação em vez de criar regras específicas para os documentos do desafio, diferenciando uma falha da aplicação de uma limitação do modelo utilizado.

## b) O que aprendi do zero

Um conceito que aprendi do zero foi **como avaliar a qualidade de um extrator baseado em LLM**. Antes do desafio, eu não sabia transformar a percepção de que uma extração “parece correta” em um critério objetivo de acerto.

Aprendi a criar um gabarito de referência, comparar os campos individualmente e normalizar os valores antes da comparação. Durante o desenvolvimento percebi também que a própria métrica pode introduzir erros: números e datas escritos de maneiras diferentes estavam sendo classificados como incorretos mesmo quando representavam a mesma informação.

Isso me mostrou que não basta validar a saída do modelo; também preciso validar **a maneira como estou medindo sua qualidade**. Aprendi principalmente com o **Claude**, aplicando e testando os conceitos diretamente no projeto, em aproximadamente **3 horas**.

## c) Autocrítica

O principal ponto que considero fraco é a validação quantitativa de algumas conclusões. As estimativas de impacto financeiro dependem de premissas e devem ser interpretadas como estimativas de oportunidade, não como projeções. Além disso, identifiquei uma variação de conversão de 20,4% para 18,7%, mas não realizei um teste de significância estatística para avaliar essa diferença.

Na Parte 3, também reconheço limitações: são apenas 17 laudos, o gabarito foi revisado por uma única pessoa e o modelo local apresentou erros recorrentes em determinados campos. Isso limita o quanto a acurácia observada pode ser generalizada.

Com mais **40 horas**, aprofundaria a validação estatística da conversão e faria uma análise de coortes para separar uma possível queda real do efeito de propostas recentes ainda em andamento. Na extração, implementaria o estado `nao_verificado`, testaria modelos maiores em hardware adequado e compararia o modelo local com a API da Anthropic, avaliando qualidade, custo e tempo de execução.

A principal pergunta que gostaria de ter feito ao negócio antes de começar seria: **nas propostas que ainda não chegaram à avaliação do imóvel, de onde vem o `valor_imovel`: é declarado pelo cliente ou já validado pelo Bari?** O dicionário chama esse campo de valor de avaliação, embora a avaliação do imóvel apareça apenas na etapa 4 do funil. Essa resposta mudaria o grau de confiança que atribuo ao LTV e à estimativa de dinheiro potencial perdido nas primeiras etapas.
