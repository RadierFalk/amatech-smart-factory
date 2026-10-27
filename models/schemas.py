"""
Schemas DTO (Data Transfer Objects) para a camada de serviços e API REST JSON.
"""
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StatusApiSchema:
    sistema: str = "Controle da Manutencao"
    status: str = "online"
    versao: str = "1.0.0"
    responsavel: str = "Equipe Orlando"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EquipamentoApiSchema:
    id: int
    codigo_tag: str
    nome: str
    setor: str
    posto_trabalho: str
    status_operacional: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PecaTrocadaApiSchema:
    codigo_peca: str
    nome: str
    quantidade: float
    unidade: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChamadoApiSchema:
    id_chamado: int
    equipamento_tag: str
    equipamento_nome: str
    setor: str
    operador: str
    tecnico: str | None
    prioridade: str
    tipo_manutencao: str
    status_chamado: str
    descricao_falha: str
    diagnostico_tecnico: str | None
    causa_raiz: str | None
    data_hora_abertura: str | None
    data_hora_inicio: str | None
    data_hora_fim: str | None
    downtime_minutos: int | None
    pecas_trocadas: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndicadoresApiSchema:
    sistema: str
    downtime_total_minutos: int
    mttr_minutos: float
    mtta_resposta_minutos: float
    total_chamados: int
    chamados_abertos: int
    chamados_em_andamento: int
    chamados_concluidos: int
    maquinas_operacionais: int
    maquinas_em_manutencao: int
    maquinas_paradas: int
    disponibilidade_geral_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
