"""Constrói o gabarito (ground truth) usado para medir a acurácia da extração.

IMPORTANTE: este gabarito é o rascunho de uma leitura cuidadosa dos 17 laudos,
feita como ponto de partida para revisão manual -- não é uma verdade absoluta
e automática. Alguns campos exigem uma decisão de modelagem (ex: o que conta
como "área total" quando o laudo não usa esse termo) e estão marcados com
`# DECISÃO:` explicando o raciocínio, para que sejam revisados e,
se necessário, corrigidos antes de virar o gabarito final da entrega.

Rodar:
    python construir_gabarito.py --saida gabarito.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema import LaudoExtraido

# Cada entrada é (valor, status, trecho_bruto). trecho_bruto só é obrigatório
# quando status != "presente" (ver schema.CampoExtraido).
GABARITO_BRUTO: dict[str, dict[str, tuple]] = {
    "laudo_1.txt": {
        "tipo_imovel": ("apartamento residencial", "presente", None),
        "endereco": ("Rua das Acácias, 145, ap. 82 - Vila Mariana, São Paulo/SP", "presente", None),
        "area_privativa_m2": ("78.40", "presente", None),
        "area_total_m2": ("102.10", "presente", None),
        "ano_construcao": ("2014", "presente", None),
        "valor_avaliacao_reais": ("642000.00", "presente", None),
        "matricula": ("184.772 (14º CRI de São Paulo)", "presente", None),
        "onus": ("nenhum identificado", "presente", None),
        "data_vistoria": ("2025-03-12", "presente", None),
        "responsavel_tecnico": ("Eng. Marina Albuquerque - CREA-SP 5061234567", "presente", None),
    },
    "laudo_2.txt": {
        "tipo_imovel": ("casa térrea", "presente", None),
        "endereco": ("Av. Central, 900, bloco B, Belo Horizonte/MG", "presente", None),
        # DECISÃO: para casas/terrenos sem termo explícito "privativa/total",
        # mapeamos área construída -> privativa, área do lote/terreno -> total.
        # É uma analogia com apartamentos, não uma equivalência perfeita.
        "area_privativa_m2": ("146.00", "presente", None),
        "area_total_m2": ("250.00", "presente", None),
        "ano_construcao": ("2008", "presente", None),
        # Valor por extenso + numérico coincidem -> sem ambiguidade, converte.
        "valor_avaliacao_reais": ("680000.00", "presente", None),
        "matricula": ("45.981 (Cartório do 3º Ofício)", "presente", None),
        "onus": ("sem gravames conhecidos", "presente", None),
        "data_vistoria": ("2025-03-18", "presente", None),
        "responsavel_tecnico": ("Carlos Henrique Moura, CAU A123456-7", "presente", None),
    },
    "laudo_3.txt": {
        "tipo_imovel": ("sala comercial", "presente", None),
        "endereco": ("Sala 503, Edifício Horizonte, Rua do Comércio, 77, Curitiba/PR", "presente", None),
        "area_privativa_m2": ("54.8", "presente", None),
        # DECISÃO: o laudo dá "área útil" (54,8) e "área comum proporcional"
        # (18,2) separadamente, mas nunca declara uma "área total" somada.
        # Não somamos automaticamente -- isso seria a IA "chutando" um total
        # que o documento não afirma. Marcado ausente, com a evidência bruta.
        "area_total_m2": (None, "ausente", "Área útil 54,8 m²; área comum proporcional 18,2 m²."),
        # DECISÃO: "idade aparente" não é "ano de construção" -- é uma
        # estimativa aproximada. Calcular 2025-11=2014 seria inferência,
        # não extração. Mantido ausente.
        "ano_construcao": (None, "ausente", "Idade aparente: 11 anos."),
        "valor_avaliacao_reais": ("395500.00", "presente", None),
        "matricula": ("77.201 (5º Registro de Imóveis)", "presente", None),
        "onus": ("alienação fiduciária em favor de instituição financeira (certidão desatualizada)", "presente", None),
        "data_vistoria": ("2025-03-22", "presente", None),
        "responsavel_tecnico": ("Arq. Beatriz Nunes (CAU A987654-3)", "presente", None),
    },
    "laudo_4.txt": {
        "tipo_imovel": ("terreno urbano", "presente", None),
        "endereco": ("Lote 18, Quadra F, Rua Ipê Amarelo, Goiânia/GO", "presente", None),
        # Terreno sem edificação: não existe área privativa/construída.
        "area_privativa_m2": (None, "ausente", "Área do terreno: 360 m2 (não há edificação/área construída mencionada)."),
        "area_total_m2": ("360.00", "presente", None),
        "ano_construcao": (None, "ausente", "Ano: não se aplica"),
        "valor_avaliacao_reais": ("218000.00", "presente", None),
        "matricula": ("102.334", "presente", None),
        "onus": (None, "ausente", "Ônus e restrições: nada informado no documento apresentado"),
        "data_vistoria": ("2025-04-02", "presente", None),
        "responsavel_tecnico": ("Paulo Sérgio Reis, CREA 12345/D-GO", "presente", None),
    },
    "laudo_5.txt": {
        "tipo_imovel": ("imóvel rural (Sítio Boa Vista)", "presente", None),
        "endereco": ("Sítio Boa Vista, Município de Campinas/SP", "presente", None),
        "area_privativa_m2": ("310.00", "presente", None),
        # DECISÃO: unidade original em hectares (4,8 ha); convertida para m²
        # (regra de normalização: áreas sempre em m²). 4,8 ha = 48.000 m².
        "area_total_m2": ("48000.00", "presente", None),
        "ano_construcao": ("1999", "presente", None),
        "valor_avaliacao_reais": ("1275000.00", "presente", None),
        "matricula": ("32.110", "presente", None),
        "onus": ("reserva legal registrada; sem hipoteca apontada", "presente", None),
        "data_vistoria": ("2025-04-07", "presente", None),
        "responsavel_tecnico": ("João A. Farias, CREA-SP 5076543210", "presente", None),
    },
    "laudo_6.txt": {
        "tipo_imovel": ("apartamento", "presente", None),
        "endereco": ("Rua das Palmeiras, 1210, Recife/PE, CEP 50000-100", "presente", None),
        "area_privativa_m2": ("61.00", "presente", None),
        "area_total_m2": ("84.00", "presente", None),
        "ano_construcao": ("2018", "presente", None),
        "valor_avaliacao_reais": ("455000.00", "presente", None),
        "matricula": ("9.876 (2º RGI do Recife)", "presente", None),
        "onus": (None, "ausente", "Não consta informação sobre ônus."),
        "data_vistoria": ("2025-04-15", "presente", None),
        "responsavel_tecnico": ("Fernanda Lins, CREA 18001/PE", "presente", None),
    },
    "laudo_7.txt": {
        "tipo_imovel": ("casa geminada", "presente", None),
        "endereco": ("Rua Azul, 33, bairro Jardim Europa, Porto Alegre/RS", "presente", None),
        "area_privativa_m2": ("92.50", "presente", None),
        "area_total_m2": ("125.00", "presente", None),
        # DECISÃO: ano informado pelo proprietário, não aferido pelo perito.
        # Aceito como presente por não haver contradição no laudo; risco
        # registrado em decisoes.md (fonte não é o próprio avaliador).
        "ano_construcao": ("2011", "presente", None),
        "valor_avaliacao_reais": ("372000.00", "presente", None),
        "matricula": ("66.504 (Registro de Imóveis da 4ª Zona)", "presente", None),
        "onus": ("penhora averbada", "presente", None),
        "data_vistoria": ("2025-04-20", "presente", None),
        "responsavel_tecnico": ("Eng. Rafael Costa, CREA-RS 222333", "presente", None),
    },
    "laudo_8.txt": {
        "tipo_imovel": ("loja térrea com sobreloja", "presente", None),
        "endereco": ("Rua Sete de Setembro, 410, Salvador/BA", "presente", None),
        "area_privativa_m2": ("118.00", "presente", None),
        "area_total_m2": (None, "ausente", "Área construída aproximada: 118 m² (nenhuma área total distinta é mencionada)."),
        # DECISÃO: "ano de referência" não é necessariamente sinônimo de
        # "ano de construção" (pode ser o ano-base da avaliação de mercado
        # usada como comparativo). Termo ambíguo -> não extraído como ano
        # de construção.
        "ano_construcao": (None, "ausente", "Ano de referência: 2005"),
        "valor_avaliacao_reais": ("910000.00", "presente", None),
        "matricula": (None, "ausente", "Matrícula não apresentada."),
        "onus": (None, "ausente", "Ônus: não foi possível verificar por ausência de certidão."),
        "data_vistoria": ("2025-04-29", "presente", None),
        "responsavel_tecnico": ("Luciana Prado - CNAI 12345", "presente", None),
    },
    "laudo_9.txt": {
        "tipo_imovel": ("casa residencial", "presente", None),
        "endereco": ("Alameda das Flores, 88, Florianópolis/SC", "presente", None),
        "area_privativa_m2": ("198.00", "presente", None),
        "area_total_m2": ("420.00", "presente", None),
        "ano_construcao": ("2020", "presente", None),
        "valor_avaliacao_reais": ("1080000.00", "presente", None),
        "matricula": ("12.909 (1º Ofício)", "presente", None),
        "onus": ("nenhum / inexistência de ônus reais", "presente", None),
        "data_vistoria": ("2025-05-03", "presente", None),
        "responsavel_tecnico": ("Eng. Thiago Martins, CREA-SC 7654321", "presente", None),
    },
    "laudo_10.txt": {
        "tipo_imovel": ("apartamento", "presente", None),
        "endereco": ("Condomínio Parque Norte, SQN 214, bloco C, apto 407, Brasília/DF", "presente", None),
        "area_privativa_m2": ("96.30", "presente", None),
        "area_total_m2": ("127.60", "presente", None),
        "ano_construcao": ("2016", "presente", None),
        "valor_avaliacao_reais": ("735000.00", "presente", None),
        "matricula": ("201.443", "presente", None),
        "onus": ("alienação fiduciária mencionada na matrícula", "presente", None),
        "data_vistoria": ("2025-05-09", "presente", None),
        "responsavel_tecnico": ("Denise Carvalho, CREA-DF 112233", "presente", None),
    },
    "laudo_11.txt": {
        "tipo_imovel": ("terreno para incorporação", "presente", None),
        "endereco": ("Rua Projetada 4, s/n, Santos/SP", "presente", None),
        "area_privativa_m2": (None, "ausente", "Sem edificação; ano de construção: inexistente."),
        "area_total_m2": ("1020.00", "presente", None),
        "ano_construcao": (None, "ausente", "Sem edificação; ano de construção: inexistente."),
        "valor_avaliacao_reais": ("2450000.00", "presente", None),
        "matricula": ("88.710", "presente", None),
        "onus": (None, "ausente", "Ônus reais não informados."),
        "data_vistoria": ("2025-05-16", "presente", None),
        "responsavel_tecnico": ("Marcos Vieira, Eng. Civil, CREA-SP 5099988776", "presente", None),
    },
    "laudo_12.txt": {
        "tipo_imovel": ("casa de alto padrão", "presente", None),
        "endereco": ("Rua das Bromélias, 500, Lago Sul, Brasília/DF", "presente", None),
        "area_privativa_m2": ("285.00", "presente", None),
        "area_total_m2": ("600.00", "presente", None),
        "ano_construcao": ("2012", "presente", None),
        "valor_avaliacao_reais": ("2180000.00", "presente", None),
        "matricula": ("54.122", "presente", None),
        "onus": ("servidão de passagem registrada", "presente", None),
        "data_vistoria": ("2025-05-23", "presente", None),
        "responsavel_tecnico": ("Arq. Andréa Melo, CAU A445566-1", "presente", None),
    },
    "laudo_13.txt": {
        "tipo_imovel": ("apartamento", "presente", None),
        "endereco": ("Av. Brasil, 1770, ap. 1201, Rio de Janeiro/RJ", "presente", None),
        "area_privativa_m2": ("112.00", "presente", None),
        "area_total_m2": ("155.00", "presente", None),
        "ano_construcao": ("1987", "presente", None),
        "valor_avaliacao_reais": ("1320000.00", "presente", None),
        "matricula": ("145.230 (7º RGI)", "presente", None),
        "onus": ("penhora cancelada (data do cancelamento não informada)", "presente", None),
        "data_vistoria": ("2025-05-30", "presente", None),
        "responsavel_tecnico": ("Eduardo Sampaio, CNAI 67890", "presente", None),
    },
    "laudo_14.txt": {
        "tipo_imovel": ("galpão industrial", "presente", None),
        "endereco": ("Rodovia BR-116, km 12, Betim/MG", "presente", None),
        "area_privativa_m2": ("1450.00", "presente", None),
        "area_total_m2": ("3000.00", "presente", None),
        "ano_construcao": (None, "ausente", "Idade: aproximadamente 18 anos"),
        "valor_avaliacao_reais": ("3900000.00", "presente", None),
        "matricula": ("70.008", "presente", None),
        "onus": (None, "ausente", "Não há menção a ônus."),
        "data_vistoria": ("2025-06-05", "presente", None),
        "responsavel_tecnico": ("Sérgio Tavares, CREA-MG 998877", "presente", None),
    },
    "laudo_15.txt": {
        "tipo_imovel": ("casa", "presente", None),
        "endereco": ("Rua Monte Verde, 19, Curitiba/PR", "presente", None),
        "area_privativa_m2": ("135.00", "presente", None),
        "area_total_m2": ("200.00", "presente", None),
        "ano_construcao": ("2003", "presente", None),
        "valor_avaliacao_reais": ("590000.00", "presente", None),
        "matricula": ("39.240", "presente", None),
        "onus": ("hipoteca ativa", "presente", None),
        "data_vistoria": ("2025-06-12", "presente", None),
        "responsavel_tecnico": ("Patrícia Gomes, Eng. Civil, CREA-PR 123123", "presente", None),
    },
    "laudo_16.txt": {
        "tipo_imovel": ("unidade comercial", "presente", None),
        "endereco": ("Rua do Sol, 250, unidade 14, Campinas/SP", "presente", None),
        "area_privativa_m2": ("42.00", "presente", None),
        "area_total_m2": ("67.00", "presente", None),
        "ano_construcao": ("2010", "presente", None),
        "valor_avaliacao_reais": ("288000.00", "presente", None),
        "matricula": ("101.010", "presente", None),
        "onus": (None, "ausente", "Ônus: sem informação."),
        "data_vistoria": ("2025-06-19", "presente", None),
        "responsavel_tecnico": ("Guilherme Rocha, CREA-SP 501010", "presente", None),
    },
    "laudo_17.txt": {
        "tipo_imovel": ("apartamento residencial", "presente", None),
        "endereco": ("Rua Harmonia, 44, Vila Madalena, São Paulo/SP", "presente", None),
        "area_privativa_m2": ("70.00", "presente", None),
        # Caso-âncora do desafio: o próprio laudo pede para manter a
        # divergência para conferência. Não escolhemos 95 nem 92.
        "area_total_m2": (
            None, "conflitante",
            "No cabeçalho consta área total 95 m², porém a tabela interna "
            "registra 92 m²; manter a divergência para conferência.",
        ),
        "ano_construcao": ("2015", "presente", None),
        "valor_avaliacao_reais": ("610000.00", "presente", None),
        "matricula": ("176.543", "presente", None),
        # DECISÃO: "não há ônus" é uma declaração do proprietário, não uma
        # certidão anexada -- ou seja, é presente-mas-não-verificado. O
        # schema atual só tem presente/ausente/conflitante (sem um 4º status
        # "não verificado"); registrado como limitação em decisoes.md e no
        # Diário (autocrítica). Optamos por "presente" com a ressalva no
        # próprio valor, em vez de forçar em uma categoria que não existe.
        "onus": ("nenhum, segundo declaração do proprietário (certidão não anexada)", "presente", None),
        "data_vistoria": ("2025-06-25", "presente", None),
        "responsavel_tecnico": ("Marina Albuquerque, CREA-SP 5061234567", "presente", None),
    },
}


def montar_registros() -> list[LaudoExtraido]:
    """Converte GABARITO_BRUTO em registros validados pelo schema oficial."""
    registros = []
    for arquivo, campos in GABARITO_BRUTO.items():
        dados = {"arquivo_origem": arquivo}
        for nome_campo, (valor, status, trecho) in campos.items():
            dados[nome_campo] = {"valor": valor, "status": status, "trecho_bruto": trecho}
        registros.append(LaudoExtraido.model_validate(dados))
    return registros


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path("gabarito.json"))
    args = parser.parse_args()

    registros = montar_registros()
    saida = [r.model_dump(mode="json") for r in registros]
    args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gabarito com {len(registros)} laudos gravado em {args.saida}")


if __name__ == "__main__":
    main()
