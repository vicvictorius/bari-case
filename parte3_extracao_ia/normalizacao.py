"""Conversão estrita dos valores extraídos para tipos de verdade.

Por que existe:
    Na primeira versão do schema, todo `valor` era `str`. O formato do
    envelope (valor/status/trecho_bruto) era garantido, mas o conteúdo não:
    o relatório do qwen2.5:7b mostrou saídas como "logar(395.500,00) =
    395500.00", "Possui 61m²", "name: 2020" e ".275.000,00" (esperado
    1.275.000,00) passando pela validação.

Princípio:
    A conversão texto -> número/data é feita em código determinístico, não
    pelo LLM. O parser é ESTRITO: aceita só o número (com "R$" antes ou "m²"
    depois) e rejeita qualquer texto em volta. Rejeitar gera ValidationError,
    que o extrator devolve ao modelo como feedback (retry). Depois das
    tentativas, o laudo falha de forma explícita em vez de sair com lixo.

    Ele NÃO tenta "adivinhar" o número dentro de uma frase: ".275.000,00"
    poderia virar 275000 por engano. Um extrator que chuta é pior do que um
    que assume que não sabe.

Convenção de separadores (laudos brasileiros):
    - "1.275.000,00", "218.000", "1.450" -> ponto como milhar
    - "54,8"                            -> vírgula como decimal
    - "78.40", "96.3"                   -> ponto como decimal (sem grupo de 3)
    Um ponto seguido de exatamente 3 dígitos é lido como milhar. Isso segue o
    padrão dos laudos, mas é uma convenção: "92.500" vira 92500, não 92,5.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime

_MILHAR_BR = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?")
_DECIMAL_VIRGULA = re.compile(r"\d+(?:,\d+)?")
_DECIMAL_PONTO = re.compile(r"\d+\.\d+")

ANO_MINIMO = 1800


def parse_numero(valor: object) -> float:
    """Converte um valor monetário ou de área para float positivo.

    Aceita número JSON ou texto com o número isolado, opcionalmente com
    "R$" antes ou "m²"/"m2" depois.

    Raises:
        ValueError: se o texto tiver qualquer outra coisa além do número,
            ou se o número não for finito e positivo.
    """
    if isinstance(valor, bool):
        raise ValueError("booleano não é um número válido")

    if isinstance(valor, (int, float)):
        numero = float(valor)
    elif isinstance(valor, str):
        texto = valor.strip()
        texto = re.sub(r"^R\$\s*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\s*m(?:²|2)$", "", texto, flags=re.IGNORECASE)

        if _MILHAR_BR.fullmatch(texto):
            numero = float(texto.replace(".", "").replace(",", "."))
        elif _DECIMAL_VIRGULA.fullmatch(texto):
            numero = float(texto.replace(",", "."))
        elif _DECIMAL_PONTO.fullmatch(texto):
            numero = float(texto)
        else:
            raise ValueError(
                f"{valor!r} não é um número isolado. Devolva só o número "
                "(ex: 1275000.00), sem texto antes ou depois."
            )
    else:
        raise ValueError(f"tipo {type(valor).__name__} não é número")

    if not math.isfinite(numero) or numero <= 0:
        raise ValueError(f"{valor!r} precisa ser um número positivo")

    return numero


def parse_ano(valor: object) -> int:
    """Converte um ano de construção para int entre 1800 e o ano atual.

    Raises:
        ValueError: se não for um ano de 4 dígitos plausível. Idades
            ("aproximadamente 18 anos") são rejeitadas: converter idade em
            ano seria cálculo, não extração.
    """
    if isinstance(valor, bool):
        raise ValueError("booleano não é um ano válido")

    if isinstance(valor, int):
        ano = valor
    elif isinstance(valor, float) and valor.is_integer():
        ano = int(valor)
    elif isinstance(valor, str) and re.fullmatch(r"\d{4}", valor.strip()):
        ano = int(valor.strip())
    else:
        raise ValueError(
            f"{valor!r} não é um ano de 4 dígitos. Devolva só o ano (ex: 2014)."
        )

    ano_atual = date.today().year
    if not ANO_MINIMO <= ano <= ano_atual:
        raise ValueError(f"ano {ano} fora da faixa {ANO_MINIMO}-{ano_atual}")

    return ano


def parse_data(valor: object) -> date:
    """Converte uma data para `date`. Aceita AAAA-MM-DD ou DD/MM/AAAA.

    Raises:
        ValueError: para qualquer outro formato ou data inexistente.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor

    if isinstance(valor, str):
        texto = valor.strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                continue

    raise ValueError(
        f"{valor!r} não é uma data válida. Use o formato AAAA-MM-DD."
    )
