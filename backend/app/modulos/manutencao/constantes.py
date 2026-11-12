"""Valores fixos do módulo de Manutenção (portados de manutencao/config.py)."""
from enum import StrEnum


class StatusEquipamento(StrEnum):
    OPERACIONAL = "OPERACIONAL"
    EM_MANUTENCAO = "EM_MANUTENCAO"
    PARADA = "PARADA"


class StatusChamado(StrEnum):
    ABERTO = "ABERTO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class Prioridade(StrEnum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class TipoManutencao(StrEnum):
    CORRETIVA = "CORRETIVA"
    PREVENTIVA = "PREVENTIVA"


STATUS_ATIVOS = (StatusChamado.ABERTO, StatusChamado.EM_ANDAMENTO)
ORDEM_PRIORIDADE = {Prioridade.CRITICA: 1, Prioridade.ALTA: 2, Prioridade.MEDIA: 3, Prioridade.BAIXA: 4}

ROTULOS_STATUS_EQUIPAMENTO = {
    StatusEquipamento.OPERACIONAL: "Funcionando",
    StatusEquipamento.EM_MANUTENCAO: "Em manutenção",
    StatusEquipamento.PARADA: "Indisponível",
}

SETORES_PADRAO = [
    "SMT",
    "Inserção Manual",
    "Montagem Final",
    "Instalação de Software",
    "Testes Funcionais",
    "Inspeção da Qualidade",
    "Embalagem",
    "Almoxarifado",
    "Expedição",
]

CAUSAS_RAIZ_PADRAO = [
    "Desgaste natural do componente",
    "Desgaste mecânico / Fadiga de componente",
    "Falta de lubrificação",
    "Componente eletrônico queimado",
    "Falha elétrica em resistor de potência",
    "Falha de sensor / calibração",
    "Sobreaquecimento",
    "Erro de operação",
    "Falta de manutenção preventiva",
    "Falha de energia elétrica",
    "Desalinhamento mecânico",
    "Software / firmware desatualizado",
    "Programa de manutenção preventiva",
]

# Tempo programado por máquina para o cálculo de disponibilidade (1 turno = 600 min)
TEMPO_PROGRAMADO_POR_MAQUINA_MIN = 600

DESCRICAO_MINIMA = 5
