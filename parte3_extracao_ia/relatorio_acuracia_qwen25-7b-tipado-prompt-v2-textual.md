# Relatório de acurácia — extração dos laudos

Acurácia geral de status (presente/ausente/conflitante correto): **90.0%**

Acurácia geral de valor (valor certo quando gabarito e extração dizem presente): **82.5%** (113/137)

A métrica de valor acima permanece como comparação conservadora principal.

A equivalência textual normalizada é uma métrica complementar aplicada apenas a `endereco` e `matricula`. Ela remove diferenças superficiais de representação e não substitui a métrica principal.

Equivalência textual normalizada geral (`endereco` + `matricula`): **70.0%** (21/30)

Laudos no gabarito: 17 | Laudos na extração: 16

## Acurácia por campo

| Campo | Acurácia de status | Acurácia de valor (quando presente) | Equivalência textual normalizada | n |
|---|---|---|---|---|
| tipo_imovel | 88.2% | 86.7% | — | 17 |
| endereco | 88.2% | 26.7% | 73.3% | 17 |
| area_privativa_m2 | 94.1% | 100.0% | — | 17 |
| area_total_m2 | 94.1% | 100.0% | — | 17 |
| ano_construcao | 88.2% | 100.0% | — | 17 |
| valor_avaliacao_reais | 94.1% | 100.0% | — | 17 |
| matricula | 94.1% | 40.0% | 66.7% | 17 |
| onus | 70.6% | 66.7% | — | 17 |
| data_vistoria | 94.1% | 100.0% | — | 17 |
| responsavel_tecnico | 94.1% | 100.0% | — | 17 |

## Laudos ausentes na extração (falha do pipeline)

- laudo_1.txt

## Equivalências recuperadas pela normalização textual

Os casos abaixo falharam na comparação conservadora, mas foram considerados equivalentes após a normalização textual complementar.

| Arquivo | Campo | Esperado | Obtido | Normalizado |
|---|---|---|---|---|
| laudo_2.txt | endereco | Av. Central, 900, bloco B, Belo Horizonte/MG | Av. Central, 900, bloco B, Belo Horizonte - MG | av central 900 bloco b belo horizonte mg |
| laudo_3.txt | matricula | 77.201 (5º Registro de Imóveis) | 77.201 - 5º Registro de Imóveis | 77 201 5o registro imoveis |
| laudo_5.txt | matricula | 32.110 | => 32.110 | 32 110 |
| laudo_6.txt | matricula | 9.876 (2º RGI do Recife) | id:9.876, 2º RGI do Recife | 9 876 2o rgi recife |
| laudo_7.txt | endereco | Rua Azul, 33, bairro Jardim Europa, Porto Alegre/RS | Rua Azul, 33, bairro Jardim Europa, Porto Alegre - RS | rua azul 33 bairro jardim europa porto alegre rs |
| laudo_9.txt | endereco | Alameda das Flores, 88, Florianópolis/SC | Alameda das Flores 88, Florianópolis/SC | alameda das flores 88 florianopolis sc |
| laudo_11.txt | endereco | Rua Projetada 4, s/n, Santos/SP | Rua Projetada 4, s/n, Santos, SP | rua projetada 4 s n santos sp |
| laudo_12.txt | endereco | Rua das Bromélias, 500, Lago Sul, Brasília/DF | Rua das Bromélias, 500, Lago Sul, Brasília - DF | rua das bromelias 500 lago sul brasilia df |
| laudo_13.txt | endereco | Av. Brasil, 1770, ap. 1201, Rio de Janeiro/RJ | Av. Brasil 1770, ap. 1201, Rio de Janeiro/RJ | av brasil 1770 ap 1201 rio janeiro rj |
| laudo_13.txt | matricula | 145.230 (7º RGI) | 145.230 do 7º RGI | 145 230 7o rgi |
| laudo_15.txt | endereco | Rua Monte Verde, 19, Curitiba/PR | Rua Monte Verde, 19, Curitiba-PR | rua monte verde 19 curitiba pr |

## Divergências (auditoria linha a linha)

| Arquivo | Campo | Tipo | Esperado (gabarito) | Obtido (extração) |
|---|---|---|---|---|
| laudo_2.txt | endereco | valor | Av. Central, 900, bloco B, Belo Horizonte/MG | Av. Central, 900, bloco B, Belo Horizonte - MG |
| laudo_2.txt | matricula | valor | 45.981 (Cartório do 3º Ofício) | série 45.981 |
| laudo_2.txt | onus | status | presente | ausente |
| laudo_3.txt | endereco | valor | Sala 503, Edifício Horizonte, Rua do Comércio, 77, Curitiba/PR | Rua do Comércio, 77, Curitiba/PR |
| laudo_3.txt | matricula | valor | 77.201 (5º Registro de Imóveis) | 77.201 - 5º Registro de Imóveis |
| laudo_3.txt | onus | valor | alienação fiduciária em favor de instituição financeira (certidão desatualizada) | alienação fiduciária em favor de instituição financeira |
| laudo_5.txt | tipo_imovel | valor | imóvel rural (Sítio Boa Vista) | imóvel rural |
| laudo_5.txt | endereco | status | presente | ausente |
| laudo_5.txt | matricula | valor | 32.110 | => 32.110 |
| laudo_5.txt | onus | valor | reserva legal registrada; sem hipoteca apontada | reserva legal registrada; não foi apontada hipoteca |
| laudo_6.txt | endereco | valor | Rua das Palmeiras, 1210, Recife/PE, CEP 50000-100 | Rua das Palmeiras, 1.210, Recife/PE, CEP 50000-100 |
| laudo_6.txt | matricula | valor | 9.876 (2º RGI do Recife) | id:9.876, 2º RGI do Recife |
| laudo_7.txt | endereco | valor | Rua Azul, 33, bairro Jardim Europa, Porto Alegre/RS | Rua Azul, 33, bairro Jardim Europa, Porto Alegre - RS |
| laudo_7.txt | matricula | valor | 66.504 (Registro de Imóveis da 4ª Zona) | s66.504 |
| laudo_8.txt | ano_construcao | status | ausente | presente |
| laudo_9.txt | endereco | valor | Alameda das Flores, 88, Florianópolis/SC | Alameda das Flores 88, Florianópolis/SC |
| laudo_9.txt | matricula | valor | 12.909 (1º Ofício) | E12.909,1º Ofício |
| laudo_9.txt | onus | status | presente | ausente |
| laudo_10.txt | endereco | valor | Condomínio Parque Norte, SQN 214, bloco C, apto 407, Brasília/DF | Condomínio Parque Norte, Brasília/DF, SQN 214, bloco C, apto 407 |
| laudo_11.txt | tipo_imovel | status | presente | ausente |
| laudo_11.txt | endereco | valor | Rua Projetada 4, s/n, Santos/SP | Rua Projetada 4, s/n, Santos, SP |
| laudo_12.txt | endereco | valor | Rua das Bromélias, 500, Lago Sul, Brasília/DF | Rua das Bromélias, 500, Lago Sul, Brasília - DF |
| laudo_13.txt | endereco | valor | Av. Brasil, 1770, ap. 1201, Rio de Janeiro/RJ | Av. Brasil 1770, ap. 1201, Rio de Janeiro/RJ |
| laudo_13.txt | matricula | valor | 145.230 (7º RGI) | 145.230 do 7º RGI |
| laudo_13.txt | onus | status | presente | ausente |
| laudo_14.txt | matricula | valor | 70.008 | N70008 |
| laudo_15.txt | endereco | valor | Rua Monte Verde, 19, Curitiba/PR | Rua Monte Verde, 19, Curitiba-PR |
| laudo_15.txt | matricula | valor | 39.240 | s39.240 |
| laudo_16.txt | tipo_imovel | valor | unidade comercial | comercial |
| laudo_16.txt | endereco | valor | Rua do Sol, 250, unidade 14, Campinas/SP | 14, Rua do Sol, 250, Campinas/SP |
| laudo_17.txt | onus | status | presente | ausente |
