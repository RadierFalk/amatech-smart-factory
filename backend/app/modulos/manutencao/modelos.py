"""Tabelas do módulo de Manutenção (schema mnt). Os usuários vêm de usr.usuarios."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modulos.manutencao.constantes import Prioridade, StatusChamado, StatusEquipamento, TipoManutencao
from app.modulos.usuarios.modelos import Usuario


def _valores(enum) -> str:
    return ", ".join(f"'{e.value}'" for e in enum)


# Condição das OS ativas, usada no índice que garante a RN02 no próprio banco.
_OS_ATIVA = text("status_chamado IN ('ABERTO', 'EM_ANDAMENTO')")


class Equipamento(Base):
    __tablename__ = "equipamentos"
    __table_args__ = (
        CheckConstraint(f"status_operacional IN ({_valores(StatusEquipamento)})", name="status_valido"),
        CheckConstraint("codigo_tag = upper(codigo_tag)", name="tag_maiuscula"),
        {"schema": "mnt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_tag: Mapped[str] = mapped_column(String(30), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    setor: Mapped[str] = mapped_column(String(50))
    posto_trabalho: Mapped[str | None] = mapped_column(String(50))
    status_operacional: Mapped[str] = mapped_column(
        String(20), default=StatusEquipamento.OPERACIONAL.value, server_default=StatusEquipamento.OPERACIONAL.value
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Peca(Base):
    __tablename__ = "pecas"
    __table_args__ = (
        CheckConstraint("codigo_peca = upper(codigo_peca)", name="codigo_maiusculo"),
        {"schema": "mnt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_peca: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    unidade_medida: Mapped[str] = mapped_column(String(10), default="UN", server_default="UN")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Chamado(Base):
    """Chamado de manutenção, que vira a Ordem de Serviço quando um técnico assume."""

    __tablename__ = "chamados"
    __table_args__ = (
        CheckConstraint(f"prioridade IN ({_valores(Prioridade)})", name="prioridade_valida"),
        CheckConstraint(f"tipo_manutencao IN ({_valores(TipoManutencao)})", name="tipo_valido"),
        CheckConstraint(f"status_chamado IN ({_valores(StatusChamado)})", name="status_valido"),
        CheckConstraint("downtime_minutos IS NULL OR downtime_minutos >= 0", name="downtime_nao_negativo"),
        Index("ix_chamados_status", "status_chamado"),
        Index("ix_chamados_equipamento_abertura", "equipamento_id", "data_hora_abertura"),
        Index("ix_chamados_tecnico", "tecnico_responsavel_id"),
        # RN02 garantida pelo banco: no máximo uma OS ativa por máquina, mesmo com cliques simultâneos.
        Index(
            "ux_chamados_uma_os_ativa",
            "equipamento_id",
            unique=True,
            postgresql_where=_OS_ATIVA,
            sqlite_where=_OS_ATIVA,
        ),
        # Reenvio de outro módulo (ex.: Qualidade) com o mesmo id_externo não duplica o chamado.
        Index(
            "ux_chamados_externo",
            "origem_sistema",
            "id_externo",
            unique=True,
            postgresql_where=text("id_externo IS NOT NULL"),
            sqlite_where=text("id_externo IS NOT NULL"),
        ),
        {"schema": "mnt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("mnt.equipamentos.id"))
    operador_abertura_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    tecnico_responsavel_id: Mapped[int | None] = mapped_column(ForeignKey("usr.usuarios.id"))
    prioridade: Mapped[str] = mapped_column(String(20))
    tipo_manutencao: Mapped[str] = mapped_column(
        String(20), default=TipoManutencao.CORRETIVA.value, server_default=TipoManutencao.CORRETIVA.value
    )
    status_chamado: Mapped[str] = mapped_column(
        String(20), default=StatusChamado.ABERTO.value, server_default=StatusChamado.ABERTO.value
    )
    descricao_falha: Mapped[str] = mapped_column(Text)
    diagnostico_tecnico: Mapped[str | None] = mapped_column(Text)
    causa_raiz: Mapped[str | None] = mapped_column(String(150))
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text)
    data_hora_abertura: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_hora_inicio_atendimento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_hora_fim_atendimento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    downtime_minutos: Mapped[int | None] = mapped_column(Integer)
    origem_sistema: Mapped[str | None] = mapped_column(String(50))
    id_externo: Mapped[str | None] = mapped_column(String(100))

    equipamento: Mapped[Equipamento] = relationship(lazy="joined")
    operador: Mapped[Usuario] = relationship(foreign_keys=[operador_abertura_id], lazy="joined")
    tecnico: Mapped[Usuario | None] = relationship(foreign_keys=[tecnico_responsavel_id], lazy="joined")
    pecas: Mapped[list["ChamadoPeca"]] = relationship(
        back_populates="chamado", cascade="all, delete-orphan", order_by="ChamadoPeca.id", lazy="selectin"
    )


class ChamadoPeca(Base):
    """Peça substituída numa OS. Uma linha por peça: adicionar de novo soma a quantidade."""

    __tablename__ = "chamado_pecas"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        UniqueConstraint("chamado_id", "peca_id", name="uq_chamado_pecas_chamado_peca"),
        {"schema": "mnt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chamado_id: Mapped[int] = mapped_column(ForeignKey("mnt.chamados.id", ondelete="CASCADE"))
    peca_id: Mapped[int] = mapped_column(ForeignKey("mnt.pecas.id"))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    chamado: Mapped[Chamado] = relationship(back_populates="pecas")
    peca: Mapped[Peca] = relationship(lazy="joined")


class HistoricoStatus(Base):
    """Trilha de auditoria das mudanças de status das máquinas (RN08). Só recebe inserções."""

    __tablename__ = "historico_status"
    __table_args__ = (
        CheckConstraint(f"status_anterior IN ({_valores(StatusEquipamento)})", name="anterior_valido"),
        CheckConstraint(f"status_novo IN ({_valores(StatusEquipamento)})", name="novo_valido"),
        Index("ix_historico_status_equipamento_data", "equipamento_id", "alterado_em"),
        {"schema": "mnt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("mnt.equipamentos.id"))
    chamado_id: Mapped[int | None] = mapped_column(ForeignKey("mnt.chamados.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    status_anterior: Mapped[str] = mapped_column(String(20))
    status_novo: Mapped[str] = mapped_column(String(20))
    alterado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    equipamento: Mapped[Equipamento] = relationship(lazy="joined")
    usuario: Mapped[Usuario] = relationship(lazy="joined")
