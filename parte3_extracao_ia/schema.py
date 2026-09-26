"""Schema de saída para a extração estruturada dos laudos de avaliação.

O contrato de dados é o núcleo da solução: cada campo extraído carrega não só
o valor, mas também um `status` (presente / ausente / conflitante) e, quando
não está simplesmente presente, o trecho bruto do laudo que justifica essa
classificação. Isso é o que permite auditar a extração sem reabrir o laudo
original -- e o que impede o extrator de "chutar" um valor plausível quando
não tem certeza (ver decisão registrada em parte3_extracao_ia/decisoes.md).
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from normalizacao import parse_ano, parse_data, parse_numero


class StatusCampo(str, Enum):
    """Classificação de confiabilidade de um campo extraído."""

    PRESENTE = "presente"        # o laudo informa o campo sem ambiguidade
    AUSENTE = "ausente"          # o laudo não menciona o campo
    CONFLITANTE = "conflitante"  # o laudo menciona valores diferentes para o mesmo campo


class CampoExtraido(BaseModel):
    """Um único campo extraído, com evidência.

    `valor` só é confiável quando `status == PRESENTE`. Nos demais casos,
    o campo não deve ser tratado como informação confiável: em `ausente`,
    `valor` pode ser None; em `conflitante`, a ambiguidade deve permanecer
    explícita. Nesses casos, `trecho_bruto` é obrigatório porque preserva
    a evidência necessária para auditoria.
    """

    # Tipo JSON declarado ao LLM (tool schema / format do Ollama).
    TIPO_JSON: ClassVar[dict[str, Any]] = {"type": ["string", "null"]}

    valor: Optional[str] = None
    status: StatusCampo
    trecho_bruto: Optional[str] = Field(
        default=None,
        description="Trecho literal do laudo que sustenta o status. "
        "Obrigatório quando status != presente.",
    )

    @model_validator(mode="after")
    def trecho_obrigatorio_se_nao_presente(self) -> "CampoExtraido":
        # model_validator(mode="after") roda sempre, mesmo quando trecho_bruto
        # usa o valor default (None) -- diferente de field_validator, que pula
        # campos não explicitamente fornecidos a menos que validate_default=True.
        if self.status in (StatusCampo.AUSENTE, StatusCampo.CONFLITANTE) and not self.trecho_bruto:
            raise ValueError(
                f"trecho_bruto é obrigatório quando status={self.status!r}, "
                "para permitir auditoria sem reabrir o laudo original."
            )
        return self

    @model_validator(mode="after")
    def valor_obrigatorio_se_presente(self) -> "CampoExtraido":
        # Contraparte da regra acima. Adicionada depois de observar, numa
        # extração real via Ollama (laudo_15, modelo qwen3:1.7b), que o
        # modelo às vezes marca status="presente" mas devolve valor=None,
        # colocando a informação certa em trecho_bruto por engano. Sem essa
        # checagem esse tipo de saída passava despercebido pela validação
        # (e portanto nunca disparava retry) -- ver decisoes.md.
        vazio = self.valor is None or (
            isinstance(self.valor, str) and not self.valor.strip()
        )
        if self.status == StatusCampo.PRESENTE and vazio:
            raise ValueError(
                'valor é obrigatório quando status="presente" -- se a '
                "informação está incerta, use ausente ou conflitante em vez "
                "de presente com valor vazio."
            )
        return self


class _CampoTipado(CampoExtraido):
    """Base dos campos com tipo definido (número, ano, data).

    Duas regras além das de CampoExtraido:

    1. O valor texto é convertido por um parser estrito (normalizacao.py).
       Se não converter, a validação falha e o extrator faz retry, em vez de
       deixar passar algo como "Possui 61m²".
    2. Quando status != presente, o valor é descartado (vira None). Um
       campo ausente ou conflitante não tem UM valor confiável; a evidência
       fica em `trecho_bruto`, que continua obrigatório nesses casos.
    """

    @model_validator(mode="before")
    @classmethod
    def descartar_valor_se_nao_presente(cls, dados: Any) -> Any:
        if isinstance(dados, dict):
            status = dados.get("status")
            if status not in (StatusCampo.PRESENTE, StatusCampo.PRESENTE.value):
                return {**dados, "valor": None}
        return dados


class CampoNumero(_CampoTipado):
    """Área em m² ou valor em R$: float positivo."""

    TIPO_JSON: ClassVar[dict[str, Any]] = {"type": ["number", "null"]}

    valor: Optional[float] = None

    @field_validator("valor", mode="before")
    @classmethod
    def converter(cls, v: Any) -> Optional[float]:
        return None if v is None else parse_numero(v)


class CampoAno(_CampoTipado):
    """Ano de construção: int entre 1800 e o ano atual."""

    TIPO_JSON: ClassVar[dict[str, Any]] = {"type": ["integer", "null"]}

    valor: Optional[int] = None

    @field_validator("valor", mode="before")
    @classmethod
    def converter(cls, v: Any) -> Optional[int]:
        return None if v is None else parse_ano(v)


class CampoData(_CampoTipado):
    """Data da vistoria: serializada como AAAA-MM-DD."""

    TIPO_JSON: ClassVar[dict[str, Any]] = {
        "type": ["string", "null"],
        "description": "Data no formato AAAA-MM-DD.",
    }

    valor: Optional[date] = None

    @field_validator("valor", mode="before")
    @classmethod
    def converter(cls, v: Any) -> Optional[date]:
        return None if v is None else parse_data(v)


class LaudoExtraido(BaseModel):
    """Registro estruturado extraído de um laudo de avaliação em texto livre."""

    arquivo_origem: str
    tipo_imovel: CampoExtraido
    endereco: CampoExtraido
    area_privativa_m2: CampoNumero
    area_total_m2: CampoNumero
    ano_construcao: CampoAno
    valor_avaliacao_reais: CampoNumero
    matricula: CampoExtraido
    onus: CampoExtraido
    data_vistoria: CampoData
    responsavel_tecnico: CampoExtraido

    def to_flat_dict(self) -> dict:
        """Achata o registro para uma linha de tabela (CSV/planilha).

        Cada campo vira duas colunas: `<campo>` (valor) e `<campo>__status`.
        O trecho bruto fica de fora do achatamento — ele serve para auditoria
        pontual, não para análise tabular em massa.
        """
        flat: dict = {"arquivo_origem": self.arquivo_origem}
        for nome_campo in self.model_fields:
            if nome_campo == "arquivo_origem":
                continue
            campo: CampoExtraido = getattr(self, nome_campo)
            flat[nome_campo] = campo.valor
            flat[f"{nome_campo}__status"] = campo.status.value
        return flat


# Nomes dos campos de conteúdo (exclui arquivo_origem), na ordem do enunciado.
CAMPOS_LAUDO: list[str] = [
    "tipo_imovel",
    "endereco",
    "area_privativa_m2",
    "area_total_m2",
    "ano_construcao",
    "valor_avaliacao_reais",
    "matricula",
    "onus",
    "data_vistoria",
    "responsavel_tecnico",
]


def json_schema_campos() -> dict[str, dict]:
    """Schema JSON de cada campo, derivado dos tipos acima.

    Fonte única para o tool schema da API Anthropic (extrator.py) e para o
    `format` do Ollama (extrator_local.py). Declarar `number`/`integer` aqui
    restringe a saída do modelo já na geração; a validação Pydantic continua
    sendo a garantia final.
    """
    propriedades: dict[str, dict] = {}
    for campo in CAMPOS_LAUDO:
        classe = LaudoExtraido.model_fields[campo].annotation
        propriedades[campo] = {
            "type": "object",
            "properties": {
                "valor": dict(classe.TIPO_JSON),
                "status": {
                    "type": "string",
                    "enum": [s.value for s in StatusCampo],
                },
                "trecho_bruto": {"type": ["string", "null"]},
            },
            "required": ["status"],
        }
    return propriedades
