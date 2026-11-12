"""Valores fixos do módulo de Rastreabilidade (portados de rastreabilidade/app/config.py e seed.py)."""
from enum import StrEnum

PREFIXO_SERIE = "AMT"          # número de série: AMT-000245
ESTOQUE_CRITICO = 50           # estoque menor ou igual a isso aparece como crítico
ORDEM_LATERAL = 90             # etapas com ordem >= 90 (Parado, Reprovado) ficam fora do fluxo principal

# Etapas com significado nas regras (o nome é o que está cadastrado em ras.etapas).
ETAPA_REPROVADO = "Reprovado"
ETAPA_APROVADO = "Aprovado"
ETAPA_MONTAGEM = "Em Montagem"
ETAPA_FINAL = "Expedição"

ETAPAS_PADRAO = [  # nome, ordem
    ("Em Fila", 1), ("Em Montagem", 2), ("Em Teste", 3), ("Aprovado", 4), ("Embalagem", 5),
    ("Expedição", 6), ("Parado", 90), ("Reprovado", 91),
]


class StatusSolicitacao(StrEnum):
    PENDENTE = "PENDENTE"
    PARCIAL = "PARCIAL"
    ATENDIDA = "ATENDIDA"
    CANCELADA = "CANCELADA"


SOLICITACAO_ABERTA = (StatusSolicitacao.PENDENTE, StatusSolicitacao.PARCIAL)


class Origem(StrEnum):
    """Quem provocou a passagem de etapa."""

    MANUAL = "MANUAL"
    MAQUINA = "MAQUINA/IOT"
    QUALIDADE = "QUALIDADE"
