# Relatório de acurácia — extração dos laudos

Acurácia geral de status (presente/ausente/conflitante correto): **92.9%**
Laudos no gabarito: 17 | Laudos na extração: 17

## Acurácia por campo

| Campo | Acurácia de status | Acurácia de valor (quando presente) | n |
|---|---|---|---|
| tipo_imovel | 94.1% | 93.8% | 17 |
| endereco | 100.0% | 29.4% | 17 |
| area_privativa_m2 | 70.6% | 50.0% | 17 |
| area_total_m2 | 94.1% | 42.9% | 17 |
| ano_construcao | 88.2% | 54.5% | 17 |
| valor_avaliacao_reais | 100.0% | 64.7% | 17 |
| matricula | 100.0% | 50.0% | 17 |
| onus | 88.2% | 33.3% | 17 |
| data_vistoria | 94.1% | 100.0% | 17 |
| responsavel_tecnico | 100.0% | 94.1% | 17 |

## Divergências (auditoria linha a linha)

| Arquivo | Campo | Tipo | Esperado (gabarito) | Obtido (extração) |
|---|---|---|---|---|
| laudo_1.txt | matricula | valor | 184.772 (14º CRI de São Paulo) | 184.772 do 14º CRI de São Paulo |
| laudo_1.txt | onus | valor | nenhum identificado | não foram identificados ônus na certidão analisada. |
| laudo_2.txt | endereco | valor | Av. Central, 900, bloco B, Belo Horizonte/MG | Av. Central, 900, bloco B, Belo Horizonte - MG |
| laudo_2.txt | matricula | valor | 45.981 (Cartório do 3º Ofício) | 45.981 |
| laudo_2.txt | onus | status | presente | ausente |
| laudo_3.txt | endereco | valor | Sala 503, Edifício Horizonte, Rua do Comércio, 77, Curitiba/PR | Edifício Horizonte, Rua do Comércio, 77, Curitiba/PR |
| laudo_3.txt | area_privativa_m2 | valor | 54.8 | falta o número, mas é mencionada como área útil 54,8 m² |
| laudo_3.txt | valor_avaliacao_reais | valor | 395500.00 | logar(395.500,00) = 395500.00 |
| laudo_3.txt | matricula | valor | 77.201 (5º Registro de Imóveis) | 77.201 - 5º Registro de Imóveis |
| laudo_3.txt | onus | valor | alienação fiduciária em favor de instituição financeira (certidão desatualizada) | Consta alienação fiduciária em favor de instituição financeira |
| laudo_5.txt | tipo_imovel | valor | imóvel rural (Sítio Boa Vista) | imóvel rural |
| laudo_5.txt | endereco | valor | Sítio Boa Vista, Município de Campinas/SP | Sítio Boa Vista, Município de Campinas, UF SP |
| laudo_5.txt | area_privativa_m2 | status | presente | ausente |
| laudo_5.txt | area_total_m2 | valor | 48000.00 | .8 |
| laudo_5.txt | ano_construcao | valor | 1999 | .99 |
| laudo_5.txt | valor_avaliacao_reais | valor | 1275000.00 | .275.000,00 |
| laudo_5.txt | onus | valor | reserva legal registrada; sem hipoteca apontada | reserva legal registrada; não foi apontada hipoteca |
| laudo_6.txt | endereco | valor | Rua das Palmeiras, 1210, Recife/PE, CEP 50000-100 | Rua das Palmeiras, 1.210, Recife/PE, CEP 50000-100 |
| laudo_6.txt | area_privativa_m2 | valor | 61.00 | Possui 61m² |
| laudo_6.txt | area_total_m2 | valor | 84.00 | Possui 84m² |
| laudo_6.txt | ano_construcao | valor | 2018 | Possui 2018 |
| laudo_6.txt | valor_avaliacao_reais | valor | 455000.00 | Possui R$ 455.000,00 |
| laudo_6.txt | matricula | valor | 9.876 (2º RGI do Recife) | 9.876, 2º RGI do Recife |
| laudo_7.txt | endereco | valor | Rua Azul, 33, bairro Jardim Europa, Porto Alegre/RS | Rua Azul, 33, bairro Jardim Europa, Porto Alegre - RS |
| laudo_7.txt | area_privativa_m2 | status | presente | ausente |
| laudo_7.txt | area_total_m2 | valor | 125.00 | 92.50 |
| laudo_7.txt | matricula | valor | 66.504 (Registro de Imóveis da 4ª Zona) | 66.504 |
| laudo_7.txt | onus | valor | penhora averbada | Há penhora averbada, conforme documento consultado em 20/04/2025. |
| laudo_8.txt | area_privativa_m2 | status | presente | ausente |
| laudo_8.txt | area_total_m2 | status | ausente | presente |
| laudo_9.txt | endereco | valor | Alameda das Flores, 88, Florianópolis/SC | Alameda das Flores 88, Florianópolis/SC |
| laudo_9.txt | ano_construcao | valor | 2020 | name: 2020 |
| laudo_9.txt | valor_avaliacao_reais | valor | 1080000.00 | name: R$ 1.080.000,00 |
| laudo_9.txt | matricula | valor | 12.909 (1º Ofício) | name: 12.909, 1º Ofício |
| laudo_9.txt | onus | valor | nenhum / inexistência de ônus reais | name: Inexistência de ônus reais |
| laudo_10.txt | endereco | valor | Condomínio Parque Norte, SQN 214, bloco C, apto 407, Brasília/DF | Condomínio Parque Norte, Brasília/DF, SQN 214, bloco C, apto 407 |
| laudo_10.txt | area_privativa_m2 | valor | 96.30 | id=96.3 |
| laudo_10.txt | area_total_m2 | valor | 127.60 | id=127.6 |
| laudo_10.txt | ano_construcao | status | presente | ausente |
| laudo_10.txt | valor_avaliacao_reais | valor | 735000.00 | id=735000.00 |
| laudo_10.txt | matricula | valor | 201.443 | id=201.443 |
| laudo_11.txt | tipo_imovel | status | presente | ausente |
| laudo_11.txt | endereco | valor | Rua Projetada 4, s/n, Santos/SP | Rua Projetada 4, s/n, Santos, SP |
| laudo_11.txt | data_vistoria | status | presente | ausente |
| laudo_12.txt | endereco | valor | Rua das Bromélias, 500, Lago Sul, Brasília/DF | Rua das Bromélias, 500, Lago Sul, Brasília - DF |
| laudo_13.txt | endereco | valor | Av. Brasil, 1770, ap. 1201, Rio de Janeiro/RJ | Av. Brasil 1770, ap. 1201, Rio de Janeiro/RJ |
| laudo_13.txt | area_privativa_m2 | status | presente | ausente |
| laudo_13.txt | area_total_m2 | valor | 155.00 | a. 155,00m² |
| laudo_13.txt | ano_construcao | valor | 1987 | a. 1987 |
| laudo_13.txt | valor_avaliacao_reais | valor | 1320000.00 | a. 1.320.000,00 |
| laudo_13.txt | matricula | valor | 145.230 (7º RGI) | 145.230 do 7º RGI |
| laudo_13.txt | onus | status | presente | conflitante |
| laudo_14.txt | area_privativa_m2 | valor | 1450.00 | : 1.450 |
| laudo_14.txt | area_total_m2 | valor | 3000.00 | : 3.000 |
| laudo_14.txt | ano_construcao | status | ausente | presente |
| laudo_14.txt | responsavel_tecnico | valor | Sérgio Tavares, CREA-MG 998877 | Sérgio Tavares, CREA-MG 998877. |
| laudo_15.txt | endereco | valor | Rua Monte Verde, 19, Curitiba/PR | Rua Monte Verde, 19, Curitiba-PR |
| laudo_15.txt | area_privativa_m2 | status | presente | ausente |
| laudo_15.txt | area_total_m2 | valor | 200.00 | 135 |
| laudo_16.txt | endereco | valor | Rua do Sol, 250, unidade 14, Campinas/SP | 14, Rua do Sol, 250, Campinas/SP |
| laudo_16.txt | area_privativa_m2 | valor | 42.00 | .00 m² |
| laudo_16.txt | area_total_m2 | valor | 67.00 | .00 m² |
| laudo_16.txt | ano_construcao | valor | 2010 | .00 |
| laudo_17.txt | onus | valor | nenhum, segundo declaração do proprietário (certidão não anexada) | não há ônus |
