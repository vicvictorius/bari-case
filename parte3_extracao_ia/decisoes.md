# Decisões de modelagem — Parte 3 (extração dos laudos)

## Abordagem escolhida

LLM (Claude, via API) com saída forçada por schema (Anthropic "tool use"),
validada por Pydantic, com retry quando a validação falha. Regex não foi
usado como extrator principal: nos 17 laudos, os mesmos campos aparecem em
formatos suficientemente diferentes (valor por extenso, matrícula com/sem
cartório, área em hectares vs. m²) para que uma lista de regex vire uma
sequência de casos especiais que quebra no 18º laudo. Regras determinísticas
entram como **auditoria pós-extração** (ex: checar se `valor` é numérico
plausível), não como o extrator em si.

## Critério de acerto: gabarito manual

Optamos por medir acurácia contra um gabarito construído por leitura humana
dos 17 laudos (`construir_gabarito.py`), em vez de medir só a consistência
do modelo entre execuções repetidas. Consistência mede estabilidade, não
correção — um modelo pode errar da mesma forma em duas rodadas e "parecer"
confiável. Acurácia por campo contra um gabarito lido com atenção é o que
dá para defender concretamente na banca.

**Limitação registrada**: o rascunho do gabarito (`GABARITO_BRUTO` em
`construir_gabarito.py`) foi produzido em conjunto com a IA nesta sessão —
não é uma leitura 100% independente. Os campos com decisão de modelagem não
trivial estão marcados com `# DECISÃO:` no próprio script, exatamente para
serem revisados antes de virar gabarito final da entrega.

## Campo ausente ou conflitante: `status` + `trecho_bruto`

Cada campo carrega `status` (`presente` / `ausente` / `conflitante`) e,
quando não é `presente`, um `trecho_bruto` obrigatório — o texto literal do
laudo que justifica a classificação. Preferimos isso a um campo de
observação em texto livre gerado pela própria IA, porque uma explicação da
IA sobre o próprio erro é uma segunda camada de interpretação: se ela errar
na explicação, isso não aparece sem reler o laudo de qualquer forma. Trecho
bruto é evidência primária, auditável sem reabrir o documento original.

## Decisões de normalização (globais, aplicadas em todos os laudos)

- **Valores em R$**: convertidos para string numérica com ponto decimal,
  sem separador de milhar (ex: `"642000.00"`). Valores por extenso só são
  convertidos quando não há ambiguidade com o valor numérico ao lado
  (ex: laudo_2, "seiscentos e oitenta mil reais (R$ 680.000)").
- **Datas**: convertidas para ISO `AAAA-MM-DD`.
- **Áreas**: sempre em m². Uma área em hectares (laudo_5) foi convertida
  (4,8 ha = 48.000 m²) em vez de mantida na unidade original.
- **Área privativa/total em casas e terrenos**: quando o laudo não usa os
  termos "privativa"/"total" (comuns em apartamentos), mapeamos
  área construída/edificada → `area_privativa_m2` e área de
  terreno/lote → `area_total_m2`. É uma analogia, não uma equivalência
  perfeita — um terreno de 600 m² com uma casa de 285 m² não é "totalmente
  privativo mais áreas comuns" no mesmo sentido que um apartamento.
  Alternativa não adotada por falta de tempo: um schema com campos
  separados por tipo de imóvel (ex: `area_terreno_m2` só para
  casas/terrenos). Ver autocrítica no Diário.

## Casos em que optamos por "ausente" mesmo havendo texto sobre o campo

- **Idade aproximada em vez de ano** (laudo_3, laudo_14): "idade aparente:
  11 anos" não é "ano de construção: 2014". Calcular o ano a partir da
  idade seria inferência (e a idade é explicitamente qualificada como
  "aparente"/"aproximada"), não extração. Marcado `ausente`.
- **Termo ambíguo "ano de referência"** (laudo_8): pode significar o
  ano-base da avaliação de mercado usada como comparativo, não
  necessariamente o ano de construção do imóvel. Marcado `ausente` em vez
  de assumir a leitura mais óbvia.
- **Área sem total explícito** (laudo_3): o laudo dá área útil e área comum
  *proporcional* separadamente, mas nunca soma. Não somamos por conta
  própria — isso seria inventar um número que o documento não afirma.

## Limitação conhecida do modelo de status (3 estados): informação não verificada

Pelo menos 2 dos 17 laudos declaram um valor de forma explícita, mas sem
lastro documental — não são casos isolados, são um padrão:

- **laudo_7**: "Ano de construção informado **pelo proprietário**: 2011" —
  não é o perito quem afirma, é uma declaração de parte interessada.
- **laudo_17**: "não há ônus, segundo **declaração do proprietário**;
  certidão não anexada" — mesma estrutura: afirmação sem documento que a
  sustente.

O schema atual só tem `presente` / `ausente` / `conflitante`, e nenhum dos
três descreve bem "informado, mas por fonte não verificada" — não é
ausência de informação, não é conflito entre duas informações, e tratar
como `presente` simples esconde que a fonte é diferente de um dado aferido
pelo próprio avaliador. Nos dois casos registramos como `presente`, com a
ressalva de procedência embutida no próprio valor (ex: `"nenhum, segundo
declaração do proprietário (certidão não anexada)"`), em vez de inventar
uma categoria fora do schema documentado.

**Correção arquitetural, não implementada agora**: um 4º status
(`nao_verificado`) resolveria isso de forma limpa. Não foi implementado
neste momento porque `extrator_local.py` está com o schema de 3 status em
execução — mudar o contrato de dados no meio de uma extração já rodando
invalidaria o que já foi gerado. Fica registrado como o item mais concreto
de "o que eu faria com mais 40 horas" no Diário (Parte 4): já sabemos
exatamente qual mudança fazer e por que ela importa, só não foi prioridade
frente ao prazo.

## Mudança de motor de IA: API paga → modelo local (Ollama)

`extrator.py` (API da Anthropic) foi escrito primeiro, mas a API é paga
(mínimo de US$5 de compra, cartão internacional habilitado) e essa despesa
não era viável. Em vez de pular a Parte 3 ou fraudar uma execução,
registramos a restrição como uma decisão de engenharia: construímos
`extrator_local.py`, uma segunda implementação que usa o mesmo `schema.py`
e o mesmo `PROMPT_SISTEMA`, mas chama um modelo rodando localmente via
[Ollama](https://ollama.com) em vez da API. Mantivemos `extrator.py`
funcional e documentado (não foi descartado) — é o caminho a seguir se
houver acesso a crédito de API no futuro.

**Trade-off esperado e assumido conscientemente**: um modelo local de 7-14B
parâmetros é significativamente menos capaz em raciocínio e em seguir
instruções sutis (como marcar `conflitante` no laudo_17 em vez de "resolver"
a divergência sozinho) do que um modelo de fronteira via API. Isso é
esperado — e é exatamente o tipo de limitação que o `avaliador.py` existe
para medir e tornar visível, não para esconder.

### Como rodar

```bash
# 1. instalar o Ollama (uma vez): https://ollama.com/download
# 2. baixar um modelo (uma vez) -- ver escolha de modelo abaixo
ollama pull qwen2.5:7b-instruct

# 3. rodar a extração
python extrator_local.py --entrada ../dados_brutos/laudos_avaliacao \
    --saida saida_extracao_local.json --modelo qwen2.5:7b-instruct

# 4. medir a acurácia (mesmo avaliador da versão via API)
python avaliador.py --extracao saida_extracao_local.json --gabarito gabarito.json \
    --relatorio relatorio_acuracia_local.md
```

### Escolha de modelo (ajustar conforme a RAM disponível)

| RAM livre | Modelo sugerido | Observação |
|---|---|---|
| 8 GB | `llama3.2:3b` ou `qwen2.5:3b-instruct` | Mais rápido, mais provável de errar nos campos ambíguos (laudo_3, laudo_8, laudo_17) |
| 16 GB | `qwen2.5:7b-instruct` (padrão do script) | Bom equilíbrio para extração estruturada |
| 32 GB+ / GPU dedicada | `qwen2.5:14b-instruct` | Melhor chance de seguir as regras de "não chutar" corretamente |

Qualquer um roda 100% offline depois de baixado — sem custo por chamada,
sem limite de requisições, sem dado saindo da sua máquina.

### Limitação de execução nesta sessão de desenvolvimento

Este sandbox de desenvolvimento não tem acesso ao domínio `ollama.com` nem
GPU para baixar/rodar um modelo de verdade, então `extrator_local.py` foi
validado com um **cliente Ollama simulado**
(`testes/test_extrator_local.py`) que prova que o parsing, a validação
Pydantic e a lógica de retry funcionam corretamente — não que o modelo
real produz boas extrações. Isso só se mede rodando de fato na sua
máquina. Antes da entrega final, rode o pipeline real (passos acima) e
revise o `relatorio_acuracia_local.md` gerado — é bem provável que a
acurácia fique abaixo da que se obteria com a API paga, especialmente nos
campos com decisão sutil (`area_total_m2`, `ano_construcao`, `onus`). Isso
não é um problema a esconder: é material direto para a autocrítica do
Diário ("o que eu faria com mais 40 horas" = acesso a um modelo melhor).

## Execução real com `qwen3:1.7b`: 92,4% de acurácia de status, três achados

A extração real rodou (17/17 sem falha de pipeline) usando `qwen3:1.7b`
(2B parâmetros — o menor dos dois modelos baixados, não o `qwen2.5:7b`
que era o padrão do script, por limitação de GPU — ver abaixo). O
relatório inicial mostrou 92,4% de acurácia de status, mas a lista de
divergências linha a linha revelou três achados de naturezas bem
diferentes, que teriam ficado misturados num único número:

**1. Bug de validação nosso, corrigido**: o laudo_15 voltou com quase todo
campo `status="presente"` mas `valor=None` — o modelo colocava a resposta
certa em `trecho_bruto` (ex: `trecho_bruto: "Ano 2003."` com `valor: null`
para `ano_construcao`) em vez de em `valor`. O schema original só exigia
`trecho_bruto` quando o status NÃO era `presente` — nunca exigiu o
inverso (`valor` obrigatório quando `presente`), então essa saída
semanticamente inválida passava pela validação Pydantic sem disparar
retry. Corrigido em `schema.py` com um segundo `model_validator`
(`valor_obrigatorio_se_presente`) e coberto por teste de regressão em
`testes/test_schema.py::test_presente_sem_valor_e_rejeitado`. Rodando de
novo, esse laudo específico agora deve forçar o modelo a corrigir a saída
via retry, ou falhar explicitamente — não mais aceitar silenciosamente.

**2. Falha nossa de medição, corrigida**: boa parte das divergências de
"valor" reportadas não eram erro de extração — eram formatação que
`normalizar_valor` não tratava como equivalente (`78,40` vs `78.40`,
`642000` vs `642000.00`, `12/03/2025` vs `2025-03-12`, `201.443` vs
`201443`). `avaliador.py` foi atualizado para interpretar número (formato
BR e US) e data antes de comparar, em vez de comparar string crua. Isso
não muda a acurácia de *status* (já estava correta), só a de *valor* —
que deve subir depois desse ajuste. Testado em
`testes/test_avaliador.py` com os pares reais que apareceram no
relatório.

**3. Limitação real do modelo, não corrigível em código**: nos laudos 5,
7 e 9, o modelo trocou `area_privativa_m2` ↔ `area_total_m2` — sempre nos
casos em que o laudo menciona "terreno/lote" *antes* de
"construída/edificada" no texto. Padrão consistente com o modelo mapeando
os números pela ordem em que aparecem no documento, não pelo significado
semântico (que é exatamente a regra de `decisoes.md` sobre área
privativa/total em casas e terrenos). Isso é uma limitação de raciocínio
do modelo de 2B parâmetros, não um bug de código — citado como candidato
a melhorar com um modelo maior (`qwen2.5:14b` ou a API paga).

### Limitação de hardware que forçou o modelo menor

O modelo padrão do script (`qwen2.5:7b-instruct`, 5,1GB) só conseguiu
rodar ~4% na GPU (NVIDIA GT 1030, 2GB de VRAM — insuficiente para o
modelo inteiro) e ~96% na CPU, levando 1-6 min por laudo. A extração
reportada acima usou `qwen3:1.7b` (1,3GB, cabe na GPU) por ser
significativamente mais rápido nesse hardware — outro trade-off
custo/tempo vs. qualidade assumido conscientemente, documentado aqui em
vez de escondido atrás de um número de acurácia sem contexto.
