# Parte 3 — Extração com IA

Extrai 10 campos estruturados de cada um dos 17 laudos em texto livre
(`../dados_brutos/laudos_avaliacao/`): tipo de imóvel, endereço, área
privativa, área total, ano de construção, valor de avaliação, matrícula,
ônus, data da vistoria e responsável técnico.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `schema.py` | Contrato de dados (Pydantic): cada campo possui `valor`, `status` (`presente`, `ausente` ou `conflitante`) e `trecho_bruto` de evidência. Áreas e valor são `float`, ano é `int` e data é `date` |
| `normalizacao.py` | Parser estrito que converte texto em número, ano ou data e rejeita qualquer texto em volta |
| `extrator.py` | Pipeline alternativo via API da Anthropic, com saída estruturada, validação e nova tentativa quando a resposta é inválida |
| `extrator_local.py` | Pipeline utilizado na execução real da entrega, via modelos locais com Ollama |
| `construir_gabarito.py` | Contém o gabarito de referência revisado e gera `gabarito.json` validando os registros pelo schema oficial |
| `avaliador.py` | Compara a saída do extrator com `gabarito.json` e calcula acurácia por campo |
| `gabarito.json` | Referência utilizada para avaliar as extrações |
| `saida_extracao_local_qwen25-7b.json` | Resultado da execução dos 17 laudos com Qwen2.5 7B |
| `relatorio_acuracia_qwen25-7b.md` | Avaliação por campo e divergências da execução com Qwen2.5 7B |
| `testes/test_avaliador.py` | Testes automatizados do avaliador e da normalização dos valores |
| `testes/test_extrator_local.py` | Testes do extrator local com cliente Ollama simulado |
| `testes/test_schema.py` | Testes das regras de validação do schema, incluindo regressão de erro encontrado durante a execução real |
| `testes/test_schema_tipado.py` | Testes do parser e dos campos tipados, usando as saídas reais que antes passavam pela validação |
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
clientes simulados e dados sintéticos quando necessário.

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

Resultado:

| Métrica | Resultado |
|---|---:|
| Acurácia de status | **92,9%** (158/170) |
| Acurácia de valor | **63,6%** (91/143) |

Resultado por campo:

| Campo | Status | Valor (quando presente) |
|---|---:|---:|
| `tipo_imovel` | 94,1% | 93,8% |
| `endereco` | 100,0% | 29,4% |
| `area_privativa_m2` | 70,6% | 50,0% |
| `area_total_m2` | 94,1% | 42,9% |
| `ano_construcao` | 88,2% | 54,5% |
| `valor_avaliacao_reais` | 100,0% | 64,7% |
| `matricula` | 100,0% | 50,0% |
| `onus` | 88,2% | 33,3% |
| `data_vistoria` | 94,1% | 100,0% |
| `responsavel_tecnico` | 100,0% | 94,1% |

A acurácia de valor é a que importa para quem consome o dado. Um campo
com status 100% e valor 64,7%, como `valor_avaliacao_reais`, significa
que o modelo sempre achou o valor, mas errou ou formatou mal um em cada
três.

Os artefatos dessa execução estão disponíveis em:

- [`saida_extracao_local_qwen25-7b.json`](saida_extracao_local_qwen25-7b.json)
- [`relatorio_acuracia_qwen25-7b.md`](relatorio_acuracia_qwen25-7b.md)

## Interpretação dos resultados

A diferença de acurácia de status entre os dois experimentos foi
pequena:

| Modelo | Acurácia de status |
|---|---:|
| Qwen3 1.7B | 92,4% |
| Qwen2.5 7B | 92,9% |

O resultado reforça que uma única métrica agregada não é suficiente para
avaliar a qualidade de um extrator.

Um campo pode apresentar o `status` correto e ainda possuir um `valor`
incorreto. Por isso, o avaliador reporta as duas métricas lado a lado e
mantém as divergências disponíveis para auditoria.

Boa parte dos erros de valor era de formato: números com texto em volta
(`"Possui 61m²"`, `"strconv(285)"`, `".275.000,00"`). Isso levou ao
schema tipado: áreas e valor como `float`, ano como `int`, data como
`date`, convertidos por um parser estrito em `normalizacao.py`. Com ele,
13 dos 17 laudos da execução histórica seriam rejeitados e reenviados
ao modelo, em vez de aceitos com lixo. O schema tipado ainda não foi
reexecutado contra o modelo; ver `decisoes.md`.

Os experimentos também mostraram um trade-off entre **tamanho do modelo,
qualidade da extração, tempo de execução e hardware disponível**.

## Limitações

A avaliação possui algumas limitações conhecidas:

- o conjunto contém apenas 17 laudos;
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
- o schema tipado ainda não foi reexecutado contra o modelo;
- a acurácia de valor (63,6%) não permite uso do dado sem revisão humana.

As decisões completas e os problemas encontrados durante o desenvolvimento
estão documentados em [`decisoes.md`](decisoes.md).