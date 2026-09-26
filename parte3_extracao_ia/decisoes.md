# Decisões de modelagem — Parte 3 (extração dos laudos)

## Abordagem escolhida

LLM com saída estruturada por schema, validada por Pydantic, com retry quando
a validação falha.

A primeira implementação (`extrator.py`) foi construída para utilizar Claude
via API da Anthropic com saída estruturada. Posteriormente, devido à restrição
de custo da API, foi criada uma segunda implementação (`extrator_local.py`)
utilizando modelos locais através do Ollama.

Regex não foi usado como extrator principal: nos 17 laudos, os mesmos campos
aparecem em formatos suficientemente diferentes — valor por extenso,
matrícula com/sem cartório, áreas em unidades e contextos diferentes — para
que uma estratégia baseada principalmente em regex exigisse diversos casos
especiais.

Regras determinísticas entram como **auditoria pós-extração**, por exemplo,
para validar tipos, formatos e consistência da estrutura retornada pelo
modelo, e não como o extrator principal.

---

## Critério de acerto: gabarito manual

Optamos por medir acurácia contra um gabarito construído a partir da leitura
dos 17 laudos e posteriormente revisado manualmente (`construir_gabarito.py`),
em vez de medir apenas a consistência do modelo entre execuções repetidas.

Consistência mede estabilidade, não necessariamente correção: um modelo pode
errar da mesma maneira em execuções diferentes e ainda assim parecer
consistente.

A comparação por campo contra um gabarito revisado permite avaliar de forma
mais concreta onde a extração acertou ou divergiu.

**Limitação registrada**: o rascunho do gabarito (`GABARITO_BRUTO` em
`construir_gabarito.py`) foi produzido com apoio de IA durante o
desenvolvimento e posteriormente revisado manualmente.

Portanto, não se trata de uma leitura inicial 100% independente.

Os campos com decisões de modelagem não triviais foram explicitamente
documentados para que essas escolhas possam ser auditadas.

---

## Campo ausente ou conflitante: `status` + `trecho_bruto`

Cada campo carrega:

```text
valor
status
trecho_bruto
```

O `status` pode assumir:

```text
presente
ausente
conflitante
```

Quando o campo não está simplesmente presente, `trecho_bruto` preserva o
texto literal do laudo que justifica a classificação.

Preferimos isso a uma observação livre produzida pela própria IA porque uma
explicação gerada pelo modelo adicionaria uma segunda camada de interpretação.

O trecho original funciona como evidência primária e permite revisar a
classificação sem depender apenas da explicação produzida pelo modelo.

---

## Decisões de normalização

As seguintes regras foram aplicadas de maneira consistente ao conjunto de
laudos.

### Valores em R$

Valores monetários são convertidos para representação numérica com ponto
decimal e sem separador de milhar.

Exemplo:

```text
R$ 642.000,00
→
642000.00
```

Valores escritos por extenso são convertidos somente quando não existe
ambiguidade com o valor apresentado no documento.

---

### Datas

Datas são normalizadas para:

```text
AAAA-MM-DD
```

Exemplo:

```text
12/03/2025
→
2025-03-12
```

---

### Áreas

As áreas são representadas em metros quadrados.

Quando o documento utiliza hectares, a unidade é convertida.

Exemplo observado:

```text
4,8 ha
→
48000 m²
```

---

### Área privativa e área total em casas e terrenos

Quando o laudo não utiliza diretamente os termos `privativa` e `total`,
adotamos:

```text
área construída / edificada
→ area_privativa_m2

área do terreno / lote
→ area_total_m2
```

Essa é uma decisão de modelagem e não uma equivalência conceitual perfeita.

Em um apartamento, área privativa e área total possuem significado diferente
da relação entre área construída e área de terreno de uma casa.

Uma alternativa seria utilizar schemas diferentes por tipo de imóvel, por
exemplo:

```text
area_construida_m2
area_terreno_m2
```

Essa mudança não foi implementada no escopo atual.

---

## Casos em que optamos por `ausente` mesmo havendo texto relacionado

### Idade aproximada em vez de ano

Nos laudos em que aparece algo como:

```text
idade aparente: 11 anos
```

não calculamos automaticamente o ano de construção.

Transformar uma idade aproximada em um ano exato exigiria inferência adicional
que o documento não afirma explicitamente.

O campo foi classificado como:

```text
ausente
```

---

### Termo ambíguo "ano de referência"

Em um dos laudos aparece o termo:

```text
ano de referência
```

Esse termo pode representar o ano-base utilizado na avaliação e não
necessariamente o ano de construção do imóvel.

Optamos por não assumir a interpretação mais conveniente.

O campo foi classificado como:

```text
ausente
```

---

### Área sem total explícito

Quando o documento apresenta componentes de área separadamente, mas não
informa explicitamente a soma, não criamos um valor total por conta própria.

Isso evita introduzir no dataset um número que não foi declarado pelo
documento.

---

## Limitação conhecida do modelo de status: informação não verificada

Durante a leitura dos laudos apareceu uma situação que não é representada
adequadamente pelos três estados atuais.

Em pelo menos dois documentos existe uma informação explícita, mas cuja
origem não foi documentalmente verificada.

### Laudo 7

O documento informa:

```text
Ano de construção informado pelo proprietário: 2011
```

A informação existe, mas sua fonte é uma declaração do proprietário.

### Laudo 17

O documento informa que não existem ônus segundo declaração do proprietário,
mas também informa que a certidão não foi anexada.

Novamente, existe informação, porém com uma procedência diferente de um dado
documentalmente verificado.

O schema atual possui apenas:

```text
presente
ausente
conflitante
```

Nenhum desses estados descreve perfeitamente:

```text
informação presente, mas não verificada
```

Nos casos atuais, mantivemos `presente` e preservamos a ressalva de
procedência no próprio conteúdo extraído.

---

## Evolução arquitetural considerada: `nao_verificado`

Uma solução mais adequada seria adicionar um quarto estado:

```text
nao_verificado
```

O schema passaria a representar:

```text
presente
ausente
conflitante
nao_verificado
```

Essa mudança não foi implementada porque alteraria o contrato de dados
utilizado durante as execuções já realizadas.

Ela foi registrada como uma das principais evoluções que seriam realizadas
com mais tempo disponível.

---

# Mudança de motor de IA: API paga → modelo local

`extrator.py`, utilizando a API da Anthropic, foi desenvolvido primeiro.

Durante o desenvolvimento, entretanto, o uso da API exigia crédito pago e
essa despesa não foi adotada para o desafio.

Em vez de remover a Parte 3 ou apresentar uma execução que não ocorreu, essa
restrição foi tratada como uma decisão de engenharia.

Foi criado:

```text
extrator_local.py
```

A implementação utiliza o mesmo contrato de dados e as mesmas regras
principais de extração, mas envia as solicitações para um modelo executado
localmente através do Ollama.

O `extrator.py` foi mantido no projeto como uma implementação alternativa,
mas **não foi executado contra a API real nos 17 laudos**.

---

## Trade-off esperado ao utilizar modelos locais

Ao optar por modelos locais menores, considerei como hipótese que limitações
de capacidade poderiam aparecer principalmente em instruções semanticamente
sutis, como distinguir informação presente de informação conflitante.

Em vez de assumir essa diferença como fato, o `avaliador.py` foi criado
justamente para medir o comportamento observado e tornar os erros visíveis.

Como a implementação via API da Anthropic não foi executada contra os 17
laudos, este projeto não produz evidência experimental para afirmar que ela
teria acurácia superior aos modelos locais utilizados.

---

## Como rodar

Primeiro, instalar o Ollama e baixar um modelo compatível.

Exemplo:

```bash
ollama pull qwen2.5:7b-instruct
```

Executar a extração:

```bash
python extrator_local.py \
    --entrada ../dados_brutos/laudos_avaliacao \
    --saida saida_extracao_local.json \
    --modelo qwen2.5:7b-instruct
```

Depois executar o avaliador:

```bash
python avaliador.py \
    --extracao saida_extracao_local.json \
    --gabarito gabarito.json \
    --relatorio relatorio_acuracia_local.md
```

---

## Escolha de modelo e hardware

A escolha do modelo depende diretamente dos recursos disponíveis.

Durante o desenvolvimento, foram testadas duas configurações principais:

| Ambiente | Modelo | Contexto |
|---|---|---|
| GT 1030 — 2 GB VRAM | Qwen3 1.7B | Modelo menor utilizado para viabilizar a primeira execução completa |
| RTX 3050 — 4 GB VRAM | Qwen2.5 7B | Utilizada posteriormente para executar o benchmark com o modelo maior |

Depois de baixado, o modelo pode ser executado localmente através do Ollama,
sem enviar os laudos para uma API externa.

---

# Limitação inicial do ambiente de desenvolvimento

Durante uma etapa inicial do desenvolvimento, o ambiente utilizado para
construção e teste do pipeline não permitia executar um modelo real através
do Ollama.

Nesse momento, `extrator_local.py` foi validado utilizando um cliente Ollama
simulado em:

```text
testes/test_extrator_local.py
```

Esses testes validavam:

```text
parsing
validação Pydantic
retry
tratamento de respostas inválidas
```

mas não permitiam concluir nada sobre a qualidade real das extrações
produzidas pelo modelo.

Naquele momento do desenvolvimento, isso significava que a qualidade do
modelo real ainda precisava ser medida na máquina local.

Posteriormente, essa etapa foi concluída: o pipeline foi executado nos 17
laudos com `qwen3:1.7b` e, depois, com `qwen2.5:7b-instruct`.

Os resultados dessas execuções estão documentados nas seções seguintes.

A implementação via Anthropic permaneceu sem execução contra a API real;
portanto, não foi feita comparação experimental de acurácia entre a API
paga e os modelos locais.

---

# Execução real com Qwen3 1.7B

A primeira execução real completa utilizou:

```text
qwen3:1.7b
```

Foram processados:

```text
17/17 laudos
```

sem falha do pipeline.

O relatório inicial apresentou:

```text
92,4% de acurácia geral de status
```

A análise das divergências revelou três tipos diferentes de problema.

---

## 1. Bug de validação do schema

No `laudo_15`, o modelo produziu campos com:

```text
status = "presente"
valor = None
```

enquanto a informação correta aparecia em `trecho_bruto`.

Exemplo conceitual:

```text
status: presente
valor: null
trecho_bruto: "Ano 2003."
```

O schema original exigia `trecho_bruto` quando o status não era `presente`,
mas não verificava a regra inversa:

```text
status = presente
→ valor deve existir
```

Assim, uma resposta semanticamente inválida conseguia passar pela validação
Pydantic.

A correção foi adicionada em `schema.py` através de um segundo
`model_validator`.

Também foi criado o teste de regressão:

```text
testes/test_schema.py::test_presente_sem_valor_e_rejeitado
```

Depois da mudança, esse estado contraditório deixa de ser aceito
silenciosamente e passa a acionar o mecanismo de retry ou falhar
explicitamente.

---

## 2. Problema no próprio avaliador

Parte das divergências inicialmente classificadas como erro de valor não
representava erros reais de extração.

Exemplos:

```text
78,40
78.40

642000
642000.00

12/03/2025
2025-03-12

201.443
201443
```

O avaliador comparava representações textuais em situações em que deveria
comparar o significado numérico ou temporal.

`avaliador.py` foi atualizado para normalizar números e datas antes da
comparação.

Essa mudança não altera a acurácia de `status`.

Ela melhora a avaliação dos valores extraídos, evitando classificar
diferenças puramente de formatação como erros do modelo.

Casos reais encontrados durante a avaliação foram transformados em testes em:

```text
testes/test_avaliador.py
```

---

## 3. Limitação observada no modelo

Nos laudos 5, 7 e 9, o Qwen3 1.7B apresentou trocas entre:

```text
area_privativa_m2
area_total_m2
```

Esses casos aparecem em documentos nos quais os conceitos de terreno/lote e
área construída/edificada precisam ser associados aos campos definidos pelo
schema.

O padrão observado é compatível com uma dificuldade do modelo em aplicar a
regra semântica de mapeamento de áreas nesses documentos.

Como o pipeline estava estruturalmente correto e o erro aparecia no conteúdo
extraído, esse comportamento foi registrado como uma limitação observada do
modelo, e não corrigido artificialmente após a geração.

---

# Limitação de hardware da primeira execução

O modelo inicialmente previsto:

```text
qwen2.5:7b-instruct
```

ocupava aproximadamente 5,1 GB.

Na máquina inicial, equipada com:

```text
NVIDIA GT 1030
2 GB VRAM
```

apenas uma pequena fração do modelo conseguia permanecer na GPU, enquanto a
maior parte da execução ocorria na CPU.

Na execução observada, aproximadamente 4% ficava na GPU e 96% na CPU,
resultando em tempos de aproximadamente:

```text
1–6 minutos por laudo
```

Por esse motivo, a primeira execução completa utilizou:

```text
qwen3:1.7b
```

com aproximadamente 1,3 GB, adequado ao hardware disponível.

Essa foi uma decisão explícita de engenharia envolvendo:

```text
tempo de execução
hardware disponível
tamanho do modelo
qualidade da extração
```

---

# Migração de hardware: GT 1030 → RTX 3050

Depois da primeira rodada, foi identificada uma segunda máquina disponível:

```text
NVIDIA RTX 3050
4 GB VRAM
```

Embora o Qwen2.5 7B ainda não coubesse integralmente nos 4 GB de VRAM, essa
configuração tornou sua execução mais viável do que na GT 1030.

Isso permitiu realizar o benchmark que inicialmente não era prático no
hardware anterior.

---

# Resultado do benchmark com Qwen2.5 7B

O benchmark foi posteriormente executado no PC Windows com RTX 3050 de 4 GB,
utilizando o mesmo conjunto de 17 laudos e o mesmo gabarito da execução
anterior.

O:

```text
qwen2.5:7b-instruct
```

processou:

```text
17/17 laudos
```

e apresentou:

```text
92,9% de acurácia geral de status
```

contra:

```text
92,4%
```

observados anteriormente com o Qwen3 1.7B.

A diferença na métrica agregada foi, portanto, de:

```text
0,5 ponto percentual
```

Apesar do modelo maior, essa diferença pequena reforçou que a escolha de
modelo não deve ser baseada apenas no número de parâmetros ou em uma única
métrica agregada.

---

## Resultado por campo

A avaliação por campo mostrou diferenças importantes.

No Qwen2.5 7B:

| Campo | Acurácia de status |
|---|---:|
| `tipo_imovel` | 94,1% |
| `endereco` | 100,0% |
| `area_privativa_m2` | 70,6% |
| `area_total_m2` | 94,1% |
| `ano_construcao` | 88,2% |
| `valor_avaliacao_reais` | 100,0% |
| `matricula` | 100,0% |
| `onus` | 88,2% |
| `data_vistoria` | 94,1% |
| `responsavel_tecnico` | 100,0% |

`area_privativa_m2`, por exemplo, apresentou apenas 70,6% de acurácia de
status, enquanto endereço, valor de avaliação, matrícula e responsável
técnico atingiram 100% neste conjunto.

Isso demonstra por que a métrica agregada não é suficiente para avaliar o
comportamento do extrator.

---

## Status correto não significa valor correto

Além do `status`, o avaliador compara o valor extraído quando a informação
está presente.

Essa análise revelou uma distinção importante:

```text
status correto
≠
valor necessariamente correto
```

Por exemplo, um modelo pode identificar corretamente que uma área está
presente no documento, mas associar o número à área errada.

Por isso, o relatório preserva a análise das divergências por campo e não
utiliza apenas a acurácia agregada como critério de qualidade.

---

## Artefatos preservados

Os artefatos da execução com Qwen2.5 7B foram preservados em:

```text
saida_extracao_local_qwen25-7b.json
relatorio_acuracia_qwen25-7b.md
```

Esses arquivos permitem revisar tanto a saída produzida pelo modelo quanto
as divergências identificadas pelo avaliador.

---

# Interpretação final do benchmark

A comparação entre as duas execuções tornou explícito o trade-off entre:

```text
tamanho do modelo
qualidade por campo
tempo de execução
hardware disponível
```

O Qwen3 1.7B tornou possível executar o pipeline de forma mais adequada no
hardware inicial.

Posteriormente, a disponibilidade da RTX 3050 permitiu avaliar o Qwen2.5 7B
utilizando os mesmos 17 laudos e o mesmo gabarito.

Os resultados não são tratados como evidência de que um dos modelos seja
universalmente superior ao outro.

A amostra contém apenas:

```text
17 laudos
```

e existem diferenças relevantes entre:

```text
acurácia de status
acurácia dos valores extraídos
qualidade por campo
tempo de execução
requisitos de hardware
```

Além disso, como a implementação Anthropic não foi executada nos mesmos 17
laudos, não existe neste projeto um benchmark experimental que permita
comparar diretamente sua acurácia com a dos modelos locais.

A principal conclusão da Parte 3 não é que determinado modelo "vence", mas
que uma solução de extração estruturada precisa combinar:

```text
LLM
+
schema explícito
+
validação determinística
+
retry
+
gabarito
+
métrica de avaliação
+
auditoria das divergências
```

Isso permite que erros do modelo, erros do próprio código e erros da métrica
de avaliação sejam identificados separadamente, em vez de escondidos dentro
de um único número de acurácia.

---

# Pontos defensáveis e interpretação dos resultados

Esta seção registra explicitamente o que os resultados da Parte 3 permitem
concluir e quais limites devem ser considerados ao apresentar o experimento.

## O que significa a acurácia de 92,9%

O resultado de **92,9%** obtido com o `qwen2.5:7b-instruct` representa a
**acurácia geral de status dos campos** no conjunto de 17 laudos utilizado
neste desafio.

Para cada campo, o avaliador verifica a classificação:

```text
presente
ausente
conflitante
```

Portanto, o resultado não deve ser interpretado como:

```text
92,9% dos valores foram extraídos perfeitamente
```

Um campo pode ter o `status` corretamente identificado como `presente` e,
ainda assim, possuir um valor extraído incorretamente.

Por esse motivo, o `avaliador.py` mantém separadas:

```text
acurácia de status
acurácia dos valores
divergências por campo
```

A métrica agregada é utilizada como um indicador do comportamento do
extrator, e não como prova isolada da qualidade completa da extração.

---

## Limitação do gabarito

O `gabarito.json` não deve ser tratado como um gold standard produzido por
uma avaliação humana totalmente independente.

O rascunho inicial (`GABARITO_BRUTO`) teve apoio de IA durante o
desenvolvimento e foi posteriormente revisado manualmente com base nos
17 laudos.

Consequentemente, a avaliação possui uma limitação metodológica:

```text
gabarito assistido por IA
+
revisão humana
```

e não:

```text
dupla revisão humana independente
```

Para um cenário de produção ou benchmark mais rigoroso, uma evolução seria
utilizar revisão independente por duas ou mais pessoas e estabelecer um
procedimento para resolução de divergências entre avaliadores.

No escopo deste desafio, a decisão foi preservar essa limitação de forma
explícita em vez de apresentar o gabarito como uma referência independente
que ele não é.

---

## O benchmark é reproduzível

A acurácia apresentada não foi inserida manualmente no relatório.

Ela pode ser recalculada utilizando:

```text
gabarito.json
+
saida_extracao_local_qwen25-7b.json
+
avaliador.py
```

produzindo novamente:

```text
relatorio_acuracia_qwen25-7b.md
```

Na auditoria final do projeto, o relatório foi regenerado a partir desses
artefatos e comparado com o arquivo versionado, sem divergências.

Isso permite rastrear:

```text
entrada de referência
→ saída do modelo
→ regra de avaliação
→ resultado reportado
```

---

## 17 laudos não permitem generalização

Os resultados observados pertencem ao conjunto de:

```text
17 laudos
```

fornecido para o desafio.

A amostra é suficiente para testar o pipeline, encontrar falhas de schema,
avaliar decisões de modelagem e observar erros do modelo neste conjunto,
mas não permite afirmar que a mesma acurácia será obtida em laudos de outras
origens, formatos ou distribuições.

Portanto, os resultados são tratados como evidência do comportamento
observado neste experimento, e não como estimativa universal de desempenho
do modelo.

---

## Comparação entre Qwen3 1.7B e Qwen2.5 7B

Os dois modelos foram executados sobre os mesmos 17 laudos e avaliados
utilizando o mesmo gabarito.

Foram observadas acurácias gerais de status de:

```text
Qwen3 1.7B      → 92,4%
Qwen2.5 7B      → 92,9%
```

A diferença observada foi de aproximadamente:

```text
0,5 ponto percentual
```

Esse resultado descreve apenas este benchmark.

Ele não demonstra que o Qwen2.5 7B seja universalmente superior ao
Qwen3 1.7B.

Além da métrica agregada, a escolha de modelo precisa considerar:

```text
qualidade por campo
tempo de execução
hardware disponível
consumo de recursos
robustez das respostas
```

---

## A implementação Anthropic não faz parte do benchmark

O `extrator.py` implementa uma alternativa utilizando a API da Anthropic,
mas essa implementação não foi executada contra os mesmos 17 laudos durante
o experimento.

Por isso, o projeto não apresenta evidência experimental para afirmar que
a API da Anthropic teria desempenho melhor ou pior que os modelos locais.

Sua presença no repositório representa uma alternativa arquitetural
implementada, e não um resultado de benchmark.

---

## Informação presente não significa informação verificada

Os laudos 7 e 17 mostraram uma limitação do schema atual.

Existem situações em que uma informação aparece explicitamente no documento,
mas sua origem não foi documentalmente verificada.

Exemplos observados incluem:

```text
ano de construção informado pelo proprietário
```

e:

```text
ausência de ônus declarada pelo proprietário sem certidão anexada
```

O schema atual possui apenas:

```text
presente
ausente
conflitante
```

Por isso, esses casos foram mantidos como `presente`, preservando a ressalva
de procedência quando aplicável.

Uma evolução considerada seria introduzir:

```text
nao_verificado
```

Essa alteração não foi aplicada retrospectivamente para evitar modificar o
contrato de dados depois das execuções utilizadas no benchmark.

---

## O pipeline diferencia falha operacional de erro de extração

Uma execução tecnicamente concluída não significa que todas as informações
foram extraídas corretamente.

São problemas diferentes:

```text
falha operacional
→ arquivo não pôde ser processado corretamente

erro de extração
→ arquivo foi processado, mas algum campo foi interpretado incorretamente
```

O pipeline utiliza validação Pydantic e retry para reduzir respostas
estruturalmente inválidas.

Após a auditoria final, o processamento em lote também passou a sinalizar
execução incompleta quando um ou mais arquivos falham, preservando os
resultados válidos já produzidos para auditoria, mas retornando código de
saída diferente de zero.

Isso evita que um lote parcialmente processado seja interpretado como uma
execução completamente bem-sucedida.

---

## Interpretação defendida para a Parte 3

A principal evidência produzida nesta etapa não é que um determinado LLM
possua uma taxa universal de acerto.

O experimento demonstra a construção de um processo de extração auditável:

```text
laudo não estruturado
        ↓
LLM
        ↓
schema explícito
        ↓
validação determinística
        ↓
retry quando necessário
        ↓
saída estruturada
        ↓
comparação com gabarito
        ↓
métricas por campo
        ↓
análise das divergências
```

Essa arquitetura permite distinguir problemas provenientes:

```text
do modelo
do schema
do código
do avaliador
do próprio gabarito
```

em vez de resumir todo o comportamento do sistema em uma única métrica.