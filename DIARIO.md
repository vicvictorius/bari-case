# Diário de bordo — Desafio Prático AI & Data Lab | Bari

## a) Registro de uso de IA

**Ferramenta usada:** Claude, para: planejamento de sequência de trabalho, geração de scripts de
profiling/tratamento, e como par de discussão nas decisões de limpeza de dados.

**Situações concretas de uso crítico:**

- No profiling inicial, pedi um script de checagem de `valor_imovel` e ele quebrou com
  `TypeError` porque a IA (eu mesmo revisando o script gerado) não tinha lido a coluna como
  string primeiro — ela estava sendo silenciosamente coagida a `object`/`str` pelo pandas por
  causa de 3 linhas com prefixo `"R$ "`. Se eu tivesse deixado o pandas inferir o tipo sem
  checar, teria perdido esse achado (e ele é relevante: é um problema real de extração, não
  ruído).
- Na dúvida sobre `etapa_max_funil = 7`, a IA sugeriu diretamente "corrigir para 6" sem antes
  mostrar a linha completa. Pedi para investigar a linha inteira antes de decidir — e só depois
  disso a correção ficou defensável (a linha bate 100% com o padrão de propostas contratadas).
  Sem essa checagem, a correção teria sido uma suposição, não uma conclusão baseada em evidência.
- No caso de `idade_cliente = 14`, a IA recomendou não imputar um valor "plausível" (como a
  mediana), argumentando que isso seria inventar dado. Concordei e apliquei esse mesmo
  princípio — mas achei importante confrontar a lógica: por que corrigir `etapa_max_funil` (que
  também é uma "adivinhação" de 7→6) e não a idade? A diferença que validei: no caso do funil
  havia evidência cruzada forte (3 outras colunas confirmando), no caso da idade não havia
  nenhuma pista sobre o valor real. Isso me fez perceber que "corrigir vs. nulificar" não é uma
  regra fixa — depende de quanta evidência colateral existe na própria linha.

*(seção em construção — mais entradas conforme a Parte 1, 2 e 3 avançam)*

## b) O que aprendi do zero

*(a preencher — escolher 1 conceito novo até o fim do desafio, com fonte e tempo gasto)*

## c) Autocrítica

*(a preencher no final)*