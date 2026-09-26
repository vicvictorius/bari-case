# Parte 3 — Extração com IA

Extrai 10 campos estruturados de cada um dos 17 laudos em texto livre
(`../dados_brutos/laudos_avaliacao/`): tipo de imóvel, endereço, área
privativa, área total, ano de construção, valor de avaliação, matrícula,
ônus, data da vistoria e responsável técnico.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `schema.py` | Contrato de dados (Pydantic): cada campo possui `valor`, `status` (`presente`, `ausente` ou `conflitante`) e `trecho_bruto` de evidência. Áreas e valor são `float`, ano é `int` e data é `date` |
| `normalizacao.py` | Parsers estritos de número, ano e data; limpeza de símbolos nas extremidades dos campos textuais e rejeição de prefixos artificiais |
| `extrator.py` | Pipeline alternativo via API da Anthropic, com saída estruturada, validação e nova tentativa quando a resposta é inválida |
| `extrator_local.py` | Pipeline utilizado na execução real da entrega, via modelos locais com Ollama |
| `construir_gabarito.py` | Contém o gabarito de referência revisado e gera `gabarito.json` validando os registros pelo schema oficial |
| `avaliador.py` | Compara a saída do extrator com `gabarito.json` e calcula acurácia por campo |
| `gabarito.json` | Referência utilizada para avaliar as extrações |
| `saida_extracao_local_qwen25-7b.json` | Resultado da execução dos 17 laudos com Qwen2.5 7B e schema antigo |
| `relatorio_acuracia_qwen25-7b.md` | Avaliação por campo e divergências da execução com schema antigo |
| `saida_extracao_local_qwen25-7b-tipado-prompt-v2.json` | Saída atual: schema tipado + prompt V2, com 16/17 laudos processados |
| `relatorio_acuracia_qwen25-7b-tipado-prompt-v2-normalizado.md` | Avaliação atual: métrica conservadora e equivalência textual complementar de endereco e matricula |
| `testes/test_avaliador.py` | Testes automatizados do avaliador e da normalização dos valores |
| `testes/test_extrator_local.py` | Testes do extrator local com cliente Ollama simulado |
| `testes/test_schema.py` | Testes das regras de validação do schema, incluindo regressão de erro encontrado durante a execução real |
| `testes/test_schema_tipado.py` | Testes do parser e dos campos tipados, usando as saídas reais que antes passavam pela validação |
| `testes/test_schema_textual.py` | Regressões das saídas textuais, preservação da evidência e validação integral do gabarito sem alterar seus textos |
| `decisoes.md` | Registro das decisões de modelagem, experimentos, limitações e trade-offs |

## Como rodar

### Instalar as dependências

```bash
pip install -r requirements.txt
```

### 1. Gerar o gabarito

```bash
python construir_gabarito.py --saida gabarito.json
```

### 2. Executar a extração local

Pré-requisito: possuir o Ollama instalado e um modelo disponível localmente.

Exemplo com Qwen2.5 7B:

```bash
ollama pull qwen2.5:7b-instruct
```

Depois:

```bash
python extrator_local.py \
  --entrada ../dados_brutos/laudos_avaliacao \
  --saida saida_extracao_local.json \
  --modelo qwen2.5:7b-instruct
```

Também foi utilizado `qwen3:1.7b` durante o desenvolvimento para permitir
a execução em hardware com menor quantidade de VRAM.

### 3. Avaliar a extração

```bash
python avaliador.py \
  --extracao saida_extracao_local.json \
  --gabarito gabarito.json \
  --relatorio relatorio_acuracia.md
```

O mesmo avaliador pode ser utilizado para comparar diferentes modelos
contra o mesmo gabarito.

### 4. Executar os testes

```bash
python -m pytest testes/ -v
```

Os testes não exigem Ollama nem acesso à API da Anthropic, pois utilizam
clientes simulados e dados sintéticos quando necessário. Após a inclusão da
validação textual, passaram **107 testes da Parte 3** e **144 testes na suíte
completa**.

## Pipeline alternativo — Anthropic

Também foi implementado um extrator utilizando a API da Anthropic:

```bash
export ANTHROPIC_API_KEY="sua-chave"

python extrator.py \
  --entrada ../dados_brutos/laudos_avaliacao \
  --saida saida_extracao.json
```

Esse pipeline foi implementado e testado com clientes simulados, mas não
foi executado contra a API real durante o desafio.

A decisão de utilizar Ollama na execução final permitiu realizar o
experimento localmente sem depender de uma API paga.

---

## Execuções realizadas

### Qwen3 1.7B

A primeira execução completa utilizou `qwen3:1.7b`.

O modelo foi escolhido devido a uma limitação de hardware: na máquina
inicial, equipada com uma NVIDIA GT 1030 de 2 GB de VRAM, o modelo
Qwen2.5 7B executava majoritariamente em CPU e levava aproximadamente
1–6 minutos por laudo.

O Qwen3 1.7B permitiu executar os **17/17 laudos sem falha de pipeline**.

A acurácia de status observada foi de:

**92,4%**

A auditoria das divergências revelou três tipos importantes de problema:

1. uma falha de validação no schema, posteriormente corrigida;
2. uma falha no método de comparação de valores do avaliador;
3. uma limitação real do modelo ao diferenciar `area_privativa_m2` e
   `area_total_m2` em determinados documentos.

Esses casos levaram a alterações no schema, no avaliador e nos testes.

### Qwen2.5 7B

Posteriormente, uma segunda máquina com NVIDIA RTX 3050 de 4 GB permitiu
executar o `qwen2.5:7b-instruct` de forma mais viável.

O modelo foi avaliado utilizando os mesmos **17 laudos** e o mesmo
gabarito.

| Execução — Qwen2.5 7B | Acurácia de status | Acurácia de valor condicional | Laudos processados |
|---|---:|---:|---:|
| Schema antigo (`valor` sempre texto) | 92,9% (158/170) | 63,6% (91/143) | 17/17 |
| Schema tipado | 84,7% | 77,3% (99/128) | 16/17 |
| **Schema tipado + prompt V2 — resultado atual** | **90,6%** | **80,9% (114/141)** | **16/17** |

A acurácia de valor condicional evoluiu de **63,6% → 77,3% → 80,9%**.
A execução intermediária com schema tipado está registrada em [`decisoes.md`](decisoes.md); sua saída não está versionada.
Os resultados do schema antigo e do V2 possuem saída e relatório versionados.

#### Resultado atual — schema tipado + prompt V2

| Campo | Status | Valor condicional — métrica conservadora |
|---|---:|---:|
| `tipo_imovel` | 88,2% | 86,7% |
| `endereco` | 88,2% | 26,7% |
| `area_privativa_m2` | 94,1% | 100,0% |
| `area_total_m2` | 94,1% | 100,0% |
| `ano_construcao` | 88,2% | 100,0% |
| `valor_avaliacao_reais` | 94,1% | 100,0% |
| `matricula` | 94,1% | 33,3% |
| `onus` | 76,5% | 50,0% |
| `data_vistoria` | 94,1% | 100,0% |
| `responsavel_tecnico` | 94,1% | 100,0% |

Os artefatos do resultado atual estão disponíveis em:

- [`saida_extracao_local_qwen25-7b-tipado-prompt-v2.json`](saida_extracao_local_qwen25-7b-tipado-prompt-v2.json)
- [`relatorio_acuracia_qwen25-7b-tipado-prompt-v2-normalizado.md`](relatorio_acuracia_qwen25-7b-tipado-prompt-v2-normalizado.md)

Para consultar a execução com schema antigo:

- [`saida_extracao_local_qwen25-7b.json`](saida_extracao_local_qwen25-7b.json)
- [`relatorio_acuracia_qwen25-7b.md`](relatorio_acuracia_qwen25-7b.md)

## Interpretação dos resultados

O status correto não garante um valor correto. Por isso, o avaliador reporta
as duas métricas lado a lado e mantém as divergências disponíveis para auditoria.

A métrica principal de valor permanece **conservadora** e considera os campos
em que gabarito e extração indicam `presente`. Portanto, os **80,9% (114/141)**
são uma acurácia condicional, que deve ser lida junto dos **16/17 laudos processados**.

A equivalência textual normalizada de `endereco` + `matricula` é de
**76,7% (23/30)**. Essa métrica é complementar, cobre apenas esses dois campos
e não substitui a métrica conservadora nem é diretamente comparável ao resultado
geral, pois utiliza outro conjunto de campos e outro denominador.

O extrator ainda requer **revisão humana**, principalmente nos campos textuais:
`endereco` apresenta **26,7%**, `matricula` **33,3%** e `onus` **50,0%** de acurácia
de valor pela métrica conservadora.

Boa parte dos erros de valor era de formato: números com texto em volta
(`"Possui 61m²"`, `"strconv(285)"`, `".275.000,00"`). Isso levou ao
schema tipado: áreas e valor como `float`, ano como `int`, data como
`date`, convertidos por um parser estrito em `normalizacao.py`. Com ele,
13 dos 17 laudos da execução histórica seriam rejeitados e reenviados
ao modelo, em vez de aceitos com lixo. O schema tipado foi reexecutado
com o prompt anterior e com o prompt V2, conforme a tabela de evolução
e o registro em [`decisoes.md`](decisoes.md). A tipagem garante o formato,
mas não a correção do conteúdo extraído.

Os experimentos também mostraram um trade-off entre **tamanho do modelo,
qualidade da extração, tempo de execução e hardware disponível**.

## Validação dos campos textuais

O schema limpa espaços externos e os marcadores `:`, `>`, `-` e `]->` nas
extremidades de `valor`, preservando pontuação interna e `trecho_bruto`.
Prefixos `strconv`, `value:`, `name:`, `id_` e `The ` no início são rejeitados
sem diferenciar maiúsculas de minúsculas, acionando o retry existente.

Essa regra trata padrões conhecidos, mas não garante correção semântica.
O prefixo `The ` também pode ocorrer em nomes legítimos e é uma limitação
explícita da regra. Consulte [`decisoes.md`](decisoes.md#validação-dos-campos-textuais-na-saída).

O efeito no modelo real **ainda exige nova execução**. Os resultados
históricos do V2 não incluem essa validação; suas saídas e relatórios foram
preservados, assim como as métricas do avaliador.

## Limitações

A avaliação possui algumas limitações conhecidas:

- o conjunto contém apenas 17 laudos;
- o prompt V2 foi refinado a partir dos erros dos mesmos 17 laudos usados na avaliação. Isso introduz viés de ajuste e torna o resultado otimista como estimativa de desempenho em laudos novos; os 100% de acurácia de valor nas áreas são um resultado dentro da amostra, não uma demonstração de generalização;
- uma avaliação sem esse viés de reutilização exigiria laudos nunca usados para ajustar o prompt, reservados desde o início ou obtidos posteriormente. Com apenas 17 laudos, uma separação deixaria pouquíssimos casos de teste; por isso, ela não foi realizada;
- o rascunho inicial do gabarito teve apoio de IA e foi posteriormente
  revisado manualmente por uma única pessoa, não constituindo um gold
  standard humano totalmente independente;
- alguns campos exigem interpretação semântica mais complexa;
- modelos menores apresentaram dificuldade na distinção entre áreas em
  determinados formatos de laudo;
- a acurácia observada neste conjunto não deve ser generalizada
  automaticamente para documentos fora da amostra;
- o pipeline via Anthropic não foi comparado experimentalmente com os
  modelos locais;
- a execução atual com schema tipado + prompt V2 processou 16/17 laudos;
- a acurácia de valor condicional de 80,9% (114/141) não dispensa revisão
  humana, principalmente nos campos textuais: endereco 26,7%, matricula
  33,3% e onus 50,0% na métrica conservadora.

As decisões completas e os problemas encontrados durante o desenvolvimento
estão documentados em [`decisoes.md`](decisoes.md).