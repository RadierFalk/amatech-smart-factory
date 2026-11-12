"""Valores fixos do Dashboard (portados de dashboard/database/banco_dashboard_industrial.sql e servicos/)."""
from datetime import time
from enum import StrEnum


class Indicador(StrEnum):
    """Indicadores com semáforo (limites ajustáveis pelo Supervisor, RN08)."""

    ATENDIMENTO_META = "atendimento_meta"
    INDICE_DEFEITOS = "indice_defeitos"
    INDICE_RETRABALHO = "indice_retrabalho"


class Sentido(StrEnum):
    MAIOR_MELHOR = "maior_melhor"
    MENOR_MELHOR = "menor_melhor"


class Semaforo(StrEnum):
    VERDE = "verde"
    AMARELO = "amarelo"
    VERMELHO = "vermelho"


NOMES_INDICADORES = {
    Indicador.ATENDIMENTO_META: "Atendimento da meta",
    Indicador.INDICE_DEFEITOS: "Índice de defeitos",
    Indicador.INDICE_RETRABALHO: "Índice de retrabalho",
}

LIMITES_PADRAO = [  # indicador, verde, amarelo, sentido
    (Indicador.ATENDIMENTO_META, 95, 75, Sentido.MAIOR_MELHOR),
    (Indicador.INDICE_DEFEITOS, 2, 5, Sentido.MENOR_MELHOR),
    (Indicador.INDICE_RETRABALHO, 2, 5, Sentido.MENOR_MELHOR),
]

TURNOS_PADRAO = [("1º turno", time(6), time(14)), ("2º turno", time(14), time(22))]

TIPOS_PERDA_PADRAO = ["Componente danificado", "Material descartado", "Embalagem danificada"]

# Etapas da Rastreabilidade que contam como produção realizada (o mesmo da sincronização antiga).
ETAPA_APROVADO = "Aprovado"
ETAPA_REPROVADO = "Reprovado"

MAX_LINHAS_CSV = 5000
