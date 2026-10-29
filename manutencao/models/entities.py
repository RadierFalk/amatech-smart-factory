"""
Entidades de domínio do Sistema de Controle da Manutenção (AMATECH).
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Usuario:
    id: int
    nome: str
    matricula: str
    perfil: str
    ativo: bool = True
    criado_em: Optional[str] = None


@dataclass
class Equipamento:
    id: int
    codigo_tag: str
    nome: str
    setor: str
    posto_trabalho: Optional[str]
    status_operacional: str = "OPERACIONAL"
    ativo: bool = True
    os_ativa_id: Optional[int] = None
    os_ativa_status: Optional[str] = None
    os_ativa_prioridade: Optional[str] = None
    os_ativa_abertura: Optional[str] = None
    os_ativa_descricao: Optional[str] = None
    os_ativa_tecnico: Optional[str] = None
    tempo_decorrido_min: Optional[int] = None


@dataclass
class Peca:
    id: int
    codigo_peca: str
    nome: str
    unidade_medida: str = "UN"
    ativo: bool = True


@dataclass
class PecaTrocada:
    id: int
    chamado_id: int
    peca_id: int
    codigo_peca: str
    nome: str
    quantidade: float
    unidade_medida: str = "UN"


@dataclass
class ChamadoManutencao:
    id: int
    equipamento_id: int
    operador_abertura_id: int
    prioridade: str
    tipo_manutencao: str
    status_chamado: str
    descricao_falha: str
    data_hora_abertura: str
    tecnico_responsavel_id: Optional[int] = None
    diagnostico_tecnico: Optional[str] = None
    causa_raiz: Optional[str] = None
    data_hora_inicio_atendimento: Optional[str] = None
    data_hora_fim_atendimento: Optional[str] = None
    downtime_minutos: Optional[int] = None
    equipamento_tag: Optional[str] = None
    equipamento_nome: Optional[str] = None
    setor: Optional[str] = None
    posto_trabalho: Optional[str] = None
    operador_nome: Optional[str] = None
    tecnico_nome: Optional[str] = None
    pecas_trocadas: list[PecaTrocada] = field(default_factory=list)


@dataclass
class HistoricoStatus:
    id: int
    equipamento_id: int
    usuario_id: int
    status_anterior: str
    status_novo: str
    alterado_em: str
    chamado_id: Optional[int] = None
    equipamento_tag: Optional[str] = None
    equipamento_nome: Optional[str] = None
    usuario_nome: Optional[str] = None
