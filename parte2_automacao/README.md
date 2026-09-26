# Parte 2 — Relatório semanal do funil

A rotina lê o CSV bruto, valida a entrada, chama `pipeline.tratamento.tratar_dados`
e exporta um HTML independente de internet, pronto para abrir no navegador e
compartilhar. Nenhum modelo de IA é executado e nenhum e-mail é enviado.

## Definições adotadas

- **Semana:** última semana completa, segunda a domingo, anterior à semana da
  data de referência. Tanto 05/01/2026 quanto 11/01/2026 selecionam
  29/12/2025–04/01/2026. Sem argumento, usa a data local da máquina.
- **Coorte:** propostas cuja `data_entrada` pertence à semana. O limite final é
  exclusivo (segunda-feira seguinte), inclusive na virada do ano.
- **Conversão observada:** `status_final == Contratada` dividido por todas as
  propostas da coorte, como na Parte 1. Sem propostas, é **não aplicável**.
- **Valor solicitado não contratado:** soma de `valor_solicitado` nas propostas não contratadas,
  atribuída à `etapa_max_funil`. É principal solicitado não contratado, não
  receita, prejuízo contábil ou perdas ocorridas durante a semana.
- **Comparação:** semana anterior e acumulado das entradas até o domingo
  selecionado. Entradas posteriores não entram nesses indicadores.
- **Canais:** quantidade, contratadas e conversão na coorte da semana. Novos
  nomes de canais são exibidos como vierem após a normalização compartilhada.

### Limitação temporal

O CSV fornecido é uma fotografia com desfechos, não um histórico de mudanças de
status. O relatório é **retrospectivo**, usando os desfechos disponíveis no
arquivo, mesmo quando posteriores ao período. Não reconstrói o que era conhecido
na data de referência e não mede contratos assinados na semana. Coortes recentes
podem estar imaturas; não se deve interpretar sua conversão como definitiva.

O relatório informa a primeira e a última data de entrada. Uma semana vazia gera
HTML com aviso; se a última entrada antecede a semana, sinaliza possível base
desatualizada. A última entrada, isoladamente, não comprova atualização ou
cobertura integral. Um CSV totalmente vazio é considerado erro de entrada.

### Filtros offline no HTML

O bloco **Explorar a semana** permite combinar canal de origem e última etapa
alcançada. Os filtros afetam somente os cinco indicadores da semana selecionada
na visão geral. Semana anterior, acumulado e as duas tabelas continuam mostrando
seus universos completos, identificados no relatório como **sem filtros**.
O botão **Limpar filtros** restaura os valores originais. Uma combinação vazia
mostra contagens e valores zero, com conversão **Não aplicável**.

Para manter o mesmo arredondamento e as mesmas definições, o Python calcula os
resumos de todas as combinações usando as funções existentes. O HTML incorpora
apenas esses resumos formatados e os nomes dos canais em JSON seguro, sem IDs,
dados individuais ou registros de outras semanas. O JavaScript próprio apenas
seleciona os valores e atualiza textos: não replica fórmulas nem lê o CSV.
Não há servidor, bibliotecas externas, CDN ou requisições de rede. Basta abrir
o HTML; sem JavaScript, o relatório completo permanece legível e os controles
ficam desabilitados. Essa abordagem prioriza os KPIs e mantém as tabelas simples.

## Instalação e execução no PowerShell

Na raiz do repositório, instale as dependências já declaradas (não foram
acrescentadas bibliotecas para a Parte 2):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe parte2_automacao\relatorio_semanal.py --data-referencia 2025-10-27
```

O exemplo usa datas cobertas pela base e produz:

```text
parte2_automacao/saidas/relatorio_2025-10-20_2025-10-26.html
parte2_automacao/saidas/relatorio_2025-10-20_2025-10-26.log
```

Para a execução semanal real, omita `--data-referencia` e forneça uma extração
atualizada compatível com o contrato. A base sintética termina em 2025: executar
com a data atual produzirá aviso de base possivelmente desatualizada.

```powershell
& "C:\Users\vekn\Desktop\BARI\BARI\.venv\Scripts\python.exe" "C:\Users\vekn\Desktop\BARI\BARI\parte2_automacao\relatorio_semanal.py"
```

Opções: `--entrada CAMINHO_CSV`, `--saida DIRETORIO` e
`--data-referencia AAAA-MM-DD`. Os caminhos padrão derivam de `__file__`;
caminhos relativos fornecidos como argumentos são relativos à raiz do projeto,
nunca ao diretório do terminal. Caminhos absolutos também são aceitos.
Não é permitido gravar saídas dentro de `dados_brutos/`.

## Execução toda segunda-feira

No **Agendador de Tarefas do Windows**, crie uma tarefa com:

1. Gatilho semanal: segunda-feira às 08:00, horário local da máquina.
2. Programa: caminho absoluto de `.venv\Scripts\python.exe`.
3. Argumentos: caminho absoluto de `parte2_automacao\relatorio_semanal.py`, entre
   aspas. Se necessário, acrescente `--entrada` e `--saida` com caminhos absolutos.
   **Não fixe `--data-referencia` na tarefa recorrente.**
4. Use uma conta com leitura da entrada e escrita na pasta de saída; habilite
   executar assim que possível após um início agendado perdido e não iniciar
   nova instância se a tarefa já estiver em execução.
5. Execute manualmente uma vez, abra o HTML e confira o log e o código de saída.

O agendamento é uma instrução de instalação: esta implementação não cria tarefas
no computador. O responsável precisa atualizar o CSV antes da execução e conferir
o log antes de compartilhar o relatório. Uma execução tardia usa sua data efetiva;
para reprocessar uma semana antiga, informe `--data-referencia` manualmente.

## Contrato de entrada e falhas

Aceita CSV UTF-8 (com ou sem BOM), separado por vírgula ou ponto e vírgula, com
cabeçalhos exatos iguais aos 19 campos originais. Colunas adicionais são
preservadas e registradas no log, mas não participam das métricas.

Os números usam ponto decimal sem separador de milhar. O prefixo `R$` em
`valor_imovel` continua sendo tratado pelo pipeline. `data_entrada` aceita
`AAAA-MM-DD` e `DD/MM/AAAA`; assinatura aceita `AAAA-MM-DD`. Taxa e assinatura
podem estar ausentes, conforme os nulos estruturais documentados na Parte 1.

Antes do pipeline, a rotina rejeita coluna faltante/duplicada, registro com
quantidade incorreta de campos, ID duplicado, nulo obrigatório, número não
finito ou não reconhecido, data inválida e status fora das categorias originais.
Depois do tratamento, verifica etapas inteiras entre 1 e 6 e valores monetários
positivos. Isso interrompe a automação para revisão, **sem corrigir ou descartar
dados silenciosamente**. Formatos novos não suportados exigem decisão explícita
e teste antes de alterar o contrato. As regras da Parte 1 permanecem intactas.

O pipeline espera entrada bruta e mantém as correções específicas de PR-000079
e PR-000081. Se essas propostas reaparecerem com valores diferentes dos esperados,
a execução falhará; não é uma rotina para reaplicar sobre o CSV já tratado.

Cada execução acrescenta ao log início, entrada, contagens, avisos e sucesso ou
falha. Os logs não incluem linhas completas nem dados individuais da base.
Código de saída **0**: HTML gerado (pode conter avisos); **1**: falha de
processamento ou escrita; **2**: argumentos inválidos. Se nem o log puder ser
criado, o erro aparece no terminal. Não há fallback silencioso para outra base.

O HTML é escrito em arquivo temporário e substituído atomicamente ao concluir.
Reexecutar a mesma semana atualiza o mesmo HTML e acrescenta ao mesmo log.
Se ocorrer uma falha, um HTML anterior pode continuar existindo: sua existência
não comprova sucesso da execução atual. Consulte o último registro do log.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest parte2_automacao\testes parte3_extracao_ia\testes -q
```

Cobrem fronteiras da semana/ano, denominadores e perdas, semana vazia,
formatos suportados, entradas inválidas, preservação do pipeline, escape de HTML,
falhas sem sobrescrever resultados anteriores e execução fora do repositório.
Também verificam os filtros combinados, resumos vazios, precisão da formatação,
JSON seguro, controles e ausência de recursos externos no HTML.
Dois testes opcionais executam o JavaScript com um DOM mínimo simulado em Node
**já instalado**, localizado no PATH ou indicado pela variável `BARI_NODE`.
Sem esse runtime, apenas esses dois testes são pulados; nenhum pacote é instalado.
