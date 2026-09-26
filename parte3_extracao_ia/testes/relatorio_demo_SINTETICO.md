# Relatório de acurácia — extração dos laudos

Acurácia geral de status (presente/ausente/conflitante correto): **98.2%**
Laudos no gabarito: 17 | Laudos na extração: 17

## Acurácia por campo

| Campo | Acurácia de status | Acurácia de valor (quando presente) | n |
|---|---|---|---|
| tipo_imovel | 100.0% | 100.0% | 17 |
| endereco | 100.0% | 100.0% | 17 |
| area_privativa_m2 | 100.0% | 100.0% | 17 |
| area_total_m2 | 88.2% | 100.0% | 17 |
| ano_construcao | 94.1% | 100.0% | 17 |
| valor_avaliacao_reais | 100.0% | 100.0% | 17 |
| matricula | 100.0% | 100.0% | 17 |
| onus | 100.0% | 100.0% | 17 |
| data_vistoria | 100.0% | 100.0% | 17 |
| responsavel_tecnico | 100.0% | 100.0% | 17 |

## Divergências (auditoria linha a linha)

| Arquivo | Campo | Tipo | Esperado (gabarito) | Obtido (extração) |
|---|---|---|---|---|
| laudo_3.txt | area_total_m2 | status | ausente | presente |
| laudo_14.txt | ano_construcao | status | ausente | presente |
| laudo_17.txt | area_total_m2 | status | conflitante | presente |
