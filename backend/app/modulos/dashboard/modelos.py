"""Tabelas do Dashboard (schema dsh): só o que é dele.

Produção, defeitos, retrabalho e paradas NÃO são copiados para cá: os indicadores são calculados na hora a partir
de ras (passagens por Aprovado/Reprovado), qld (ocorrências) e mnt (chamados). O sistema antigo guardava cópias
sincronizadas; aqui ficam só metas, turnos, limites do semáforo e perdas, que nenhum outro módulo registra.
"""
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modulos.dashboard.constantes import Indicador, Sentido
from app.modulos.qualidade.modelos import Estacao
from app.modulos.rastreabilidade.modelos import Modelo
from app.modulos.usuarios.modelos import Usuario


class Turno(Base):
    __tablename__ = "turnos"
    __table_args__ = (
        CheckConstraint("hora_fim > hora_inicio", name="horario_valido"),
        {"schema": "dsh"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(30), unique=True)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fim: Mapped[time] = mapped_column(Time)

    @property
    def duracao_min(self) -> int:
        return (self.hora_fim.hour * 60 + self.hora_fim.minute) - (self.hora_inicio.hour * 60 + self.hora_inicio.minute)


class Limite(Base):
    """Limites do semáforo de cada indicador (RN08)."""

    __tablename__ = "limites"
    __table_args__ = (
        CheckConstraint(f"indicador IN ({', '.join(repr(i.value) for i in Indicador)})", name="indicador_valido"),
        CheckConstraint(f"sentido IN ({', '.join(repr(s.value) for s in Sentido)})", name="sentido_valido"),
        CheckConstraint("limite_verde >= 0 AND limite_amarelo >= 0", name="limites_nao_negativos"),
        {"schema": "dsh"},
    )

    indicador: Mapped[str] = mapped_column(String(30), primary_key=True)
    limite_verde: Mapped[float] = mapped_column(Float)
    limite_amarelo: Mapped[float] = mapped_column(Float)
    sentido: Mapped[str] = mapped_column(String(20))


class Meta(Base):
    """Meta de produção por dia, turno e modelo (RF02, RN09: uma só por combinação)."""

    __tablename__ = "metas"
    __table_args__ = (
        UniqueConstraint("data", "turno_id", "modelo_id", name="uq_metas_data_turno_modelo"),
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        {"schema": "dsh"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    turno_id: Mapped[int] = mapped_column(ForeignKey("dsh.turnos.id"))
    modelo_id: Mapped[int] = mapped_column(ForeignKey("ras.modelos.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    turno: Mapped[Turno] = relationship(lazy="joined")
    modelo: Mapped[Modelo] = relationship(lazy="joined")
    registrado_por: Mapped[Usuario] = relationship(lazy="joined")


class TipoPerda(Base):
    __tablename__ = "tipos_perda"
    __table_args__ = {"schema": "dsh"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Perda(Base):
    """Material perdido na linha (RF15, RN07)."""

    __tablename__ = "perdas"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint("origem IN ('manual', 'csv')", name="origem_valida"),
        Index("ix_perdas_data", "data"),
        {"schema": "dsh"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    turno_id: Mapped[int] = mapped_column(ForeignKey("dsh.turnos.id"))
    estacao_id: Mapped[int] = mapped_column(ForeignKey("qld.estacoes.id"))
    modelo_id: Mapped[int] = mapped_column(ForeignKey("ras.modelos.id"))
    tipo_perda_id: Mapped[int] = mapped_column(ForeignKey("dsh.tipos_perda.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    observacao: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(String(10), default="manual", server_default="manual")
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    turno: Mapped[Turno] = relationship(lazy="joined")
    estacao: Mapped[Estacao] = relationship(lazy="joined")
    modelo: Mapped[Modelo] = relationship(lazy="joined")
    tipo: Mapped[TipoPerda] = relationship(lazy="joined")
    registrado_por: Mapped[Usuario] = relationship(lazy="joined")
