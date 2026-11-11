"""Contratos de entrada e saída da API de Manutenção (/api/mnt)."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core import tempo
from app.modulos.manutencao.constantes import (
    DESCRICAO_MINIMA,
    STATUS_ATIVOS,
    Prioridade,
    StatusChamado,
    StatusEquipamento,
    TipoManutencao,
)
from app.modulos.manutencao.modelos import Chamado, Equipamento, HistoricoStatus, Peca

# ---------------------------------------------------------------- entrada


class ChamadoAbrir(BaseModel):
    equipamento_id: int
    prioridade: Prioridade = Prioridade.MEDIA
    descricao_falha: str = Field(min_length=DESCRICAO_MINIMA, max_length=2000)


class PreventivaProgramar(BaseModel):
    equipamento_id: int
    prioridade: Prioridade = Prioridade.BAIXA
    descricao_falha: str = Field(
        default="Manutenção preventiva programada conforme plano de manutenção do ativo.",
        min_length=DESCRICAO_MINIMA,
        max_length=2000,
    )


class LaudoSalvar(BaseModel):
    diagnostico_tecnico: str = Field(default="", max_length=4000)
    causa_raiz: str = Field(default="", max_length=150)
    tipo_manutencao: TipoManutencao = TipoManutencao.CORRETIVA


class ChamadoConcluir(BaseModel):
    diagnostico_tecnico: str = Field(min_length=1, max_length=4000)
    causa_raiz: str = Field(min_length=1, max_length=150)
    tipo_manutencao: TipoManutencao


class ChamadoCancelar(BaseModel):
    motivo: str = Field(min_length=DESCRICAO_MINIMA, max_length=500)


class PecaAdicionar(BaseModel):
    peca_id: int
    quantidade: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class EquipamentoCriar(BaseModel):
    codigo_tag: str = Field(min_length=1, max_length=30)
    nome: str = Field(min_length=1, max_length=100)
    setor: str = Field(min_length=1, max_length=50)
    posto_trabalho: str | None = Field(default=None, max_length=50)


class EquipamentoAlterar(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    setor: str | None = Field(default=None, min_length=1, max_length=50)
    posto_trabalho: str | None = Field(default=None, max_length=50)
    ativo: bool | None = None


class PecaCriar(BaseModel):
    codigo_peca: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=1, max_length=100)
    unidade_medida: str = Field(default="UN", min_length=1, max_length=10)


class PecaAlterar(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    unidade_medida: str | None = Field(default=None, min_length=1, max_length=10)
    ativo: bool | None = None


# ---------------------------------------------------------------- saída


class PecaSaida(BaseModel):
    id: int
    codigo_peca: str
    nome: str
    unidade_medida: str
    ativo: bool

    @classmethod
    def de(cls, p: Peca) -> "PecaSaida":
        return cls(id=p.id, codigo_peca=p.codigo_peca, nome=p.nome, unidade_medida=p.unidade_medida, ativo=p.ativo)


class PecaTrocadaSaida(BaseModel):
    id: int
    peca_id: int
    codigo_peca: str
    nome: str
    unidade_medida: str
    quantidade: float


class ChamadoSaida(BaseModel):
    id: int
    equipamento_id: int
    equipamento_tag: str
    equipamento_nome: str
    setor: str
    posto_trabalho: str | None
    status_equipamento: StatusEquipamento
    prioridade: Prioridade
    tipo_manutencao: TipoManutencao
    status_chamado: StatusChamado
    descricao_falha: str
    diagnostico_tecnico: str | None
    causa_raiz: str | None
    motivo_cancelamento: str | None
    operador_id: int
    operador_nome: str
    tecnico_id: int | None
    tecnico_nome: str | None
    data_hora_abertura: datetime
    data_hora_inicio_atendimento: datetime | None
    data_hora_fim_atendimento: datetime | None
    downtime_minutos: int | None
    minutos_desde_abertura: int | None = Field(description="Só em OS ativa: tempo de espera/parada até agora")
    minutos_em_atendimento: int | None = Field(description="Só em OS em andamento: tempo desde que o técnico assumiu")
    origem_sistema: str | None
    id_externo: str | None
    pecas: list[PecaTrocadaSaida]

    @classmethod
    def de(cls, c: Chamado) -> "ChamadoSaida":
        agora = tempo.agora()
        ativo = c.status_chamado in STATUS_ATIVOS
        return cls(
            id=c.id,
            equipamento_id=c.equipamento_id,
            equipamento_tag=c.equipamento.codigo_tag,
            equipamento_nome=c.equipamento.nome,
            setor=c.equipamento.setor,
            posto_trabalho=c.equipamento.posto_trabalho,
            status_equipamento=c.equipamento.status_operacional,
            prioridade=c.prioridade,
            tipo_manutencao=c.tipo_manutencao,
            status_chamado=c.status_chamado,
            descricao_falha=c.descricao_falha,
            diagnostico_tecnico=c.diagnostico_tecnico,
            causa_raiz=c.causa_raiz,
            motivo_cancelamento=c.motivo_cancelamento,
            operador_id=c.operador_abertura_id,
            operador_nome=c.operador.nome,
            tecnico_id=c.tecnico_responsavel_id,
            tecnico_nome=c.tecnico.nome if c.tecnico else None,
            data_hora_abertura=tempo.utc(c.data_hora_abertura),
            data_hora_inicio_atendimento=tempo.utc(c.data_hora_inicio_atendimento),
            data_hora_fim_atendimento=tempo.utc(c.data_hora_fim_atendimento),
            downtime_minutos=c.downtime_minutos,
            minutos_desde_abertura=tempo.minutos_entre(c.data_hora_abertura, agora) if ativo else None,
            minutos_em_atendimento=(
                tempo.minutos_entre(c.data_hora_inicio_atendimento, agora)
                if c.status_chamado == StatusChamado.EM_ANDAMENTO
                else None
            ),
            origem_sistema=c.origem_sistema,
            id_externo=c.id_externo,
            pecas=[
                PecaTrocadaSaida(
                    id=i.id,
                    peca_id=i.peca_id,
                    codigo_peca=i.peca.codigo_peca,
                    nome=i.peca.nome,
                    unidade_medida=i.peca.unidade_medida,
                    quantidade=float(i.quantidade),
                )
                for i in c.pecas
            ],
        )


class OsAtivaResumo(BaseModel):
    id: int
    status_chamado: StatusChamado
    prioridade: Prioridade
    tipo_manutencao: TipoManutencao
    descricao_falha: str
    tecnico_nome: str | None
    data_hora_abertura: datetime
    minutos_desde_abertura: int


class EquipamentoSaida(BaseModel):
    id: int
    codigo_tag: str
    nome: str
    setor: str
    posto_trabalho: str | None
    status_operacional: StatusEquipamento
    ativo: bool
    os_ativa: OsAtivaResumo | None = None

    @classmethod
    def de(cls, e: Equipamento, ativa: Chamado | None = None) -> "EquipamentoSaida":
        resumo = None
        if ativa is not None:
            resumo = OsAtivaResumo(
                id=ativa.id,
                status_chamado=ativa.status_chamado,
                prioridade=ativa.prioridade,
                tipo_manutencao=ativa.tipo_manutencao,
                descricao_falha=ativa.descricao_falha,
                tecnico_nome=ativa.tecnico.nome if ativa.tecnico else None,
                data_hora_abertura=tempo.utc(ativa.data_hora_abertura),
                minutos_desde_abertura=tempo.minutos_entre(ativa.data_hora_abertura, tempo.agora()),
            )
        return cls(
            id=e.id,
            codigo_tag=e.codigo_tag,
            nome=e.nome,
            setor=e.setor,
            posto_trabalho=e.posto_trabalho,
            status_operacional=e.status_operacional,
            ativo=e.ativo,
            os_ativa=resumo,
        )


class AuditoriaSaida(BaseModel):
    id: int
    equipamento_id: int
    equipamento_tag: str
    chamado_id: int | None
    usuario_nome: str
    usuario_perfil: str
    status_anterior: StatusEquipamento
    status_novo: StatusEquipamento
    alterado_em: datetime

    @classmethod
    def de(cls, h: HistoricoStatus) -> "AuditoriaSaida":
        return cls(
            id=h.id,
            equipamento_id=h.equipamento_id,
            equipamento_tag=h.equipamento.codigo_tag,
            chamado_id=h.chamado_id,
            usuario_nome=h.usuario.nome,
            usuario_perfil=h.usuario.perfil,
            status_anterior=h.status_anterior,
            status_novo=h.status_novo,
            alterado_em=tempo.utc(h.alterado_em),
        )


class OpcoesSaida(BaseModel):
    prioridades: list[Prioridade]
    tipos_manutencao: list[TipoManutencao]
    status_chamado: list[StatusChamado]
    status_equipamento: dict[str, str]
    setores: list[str]
    causas_raiz: list[str]
    permissoes: dict[str, bool] = Field(description="O que a persona logada pode fazer neste módulo (para a tela)")
