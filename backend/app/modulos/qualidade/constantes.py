"""Valores fixos do módulo de Qualidade (portados de qualidade/ocorrencia.py e integracao.py)."""
from enum import StrEnum

from app.modulos.manutencao.constantes import Prioridade


class Classificacao(StrEnum):
    CRITICO = "CRITICO"
    MAIOR = "MAIOR"
    MENOR = "MENOR"


class SituacaoProduto(StrEnum):
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"
    EM_REPROCESSO = "EM_REPROCESSO"


class StatusOcorrencia(StrEnum):
    ABERTA = "ABERTA"
    EM_ANALISE = "EM_ANALISE"
    RESOLVIDA = "RESOLVIDA"


ROTULOS_CLASSIFICACAO = {Classificacao.CRITICO: "Crítico", Classificacao.MAIOR: "Maior", Classificacao.MENOR: "Menor"}
ROTULOS_SITUACAO = {
    SituacaoProduto.APROVADO: "Aprovado",
    SituacaoProduto.REPROVADO: "Reprovado",
    SituacaoProduto.EM_REPROCESSO: "Em reprocesso",
}
ROTULOS_STATUS = {
    StatusOcorrencia.ABERTA: "Aberta",
    StatusOcorrencia.EM_ANALISE: "Em análise",
    StatusOcorrencia.RESOLVIDA: "Resolvida",
}

# Valores gravados pelo sistema antigo (SQLite) -> valores novos. Usado pelo script de migração.
LEGADO_CLASSIFICACAO = {"Critico": Classificacao.CRITICO, "Maior": Classificacao.MAIOR, "Menor": Classificacao.MENOR}
LEGADO_SITUACAO = {
    "Aprovado": SituacaoProduto.APROVADO,
    "Reprovado": SituacaoProduto.REPROVADO,
    "Em_reprocesso": SituacaoProduto.EM_REPROCESSO,
}
LEGADO_STATUS = {
    "Aberta": StatusOcorrencia.ABERTA,
    "Em_analise": StatusOcorrencia.EM_ANALISE,
    "Resolvida": StatusOcorrencia.RESOLVIDA,
}

# Defeito causado pela máquina vira chamado na Manutenção com prioridade pela gravidade.
PRIORIDADE_CHAMADO = {
    Classificacao.CRITICO: Prioridade.CRITICA,
    Classificacao.MAIOR: Prioridade.ALTA,
    Classificacao.MENOR: Prioridade.MEDIA,
}
ORIGEM_CHAMADO = "qualidade"


def id_externo(ocorrencia_id: int) -> str:
    """Identificador da ocorrência no chamado da Manutenção (o mesmo do sistema antigo)."""
    return f"QLD-{ocorrencia_id}"
