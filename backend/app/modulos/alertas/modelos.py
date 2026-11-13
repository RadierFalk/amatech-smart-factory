"""Alertas do sistema (usr.alertas) e quem já leu cada um (usr.alertas_lidos).

Um alerta representa uma situação aberta (OS de prioridade alta, máquina parada sem técnico, estoque que não cobre
os pedidos, ocorrência crítica). Enquanto a situação existe, o alerta fica ativo; quando ela acaba, fica resolvido.
A `chave` identifica a situação (ex.: "estoque:12"): só pode haver um alerta ATIVO por chave.
"""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TIPOS = ("CHAMADO_ABERTO", "PARADA_SEM_TECNICO", "ESTOQUE_INSUFICIENTE", "OCORRENCIA_CRITICA")


class Alerta(Base):
    __tablename__ = "alertas"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({', '.join(repr(t) for t in TIPOS)})", name="tipo_valido"),
        Index("ux_alertas_chave_ativo", "chave", unique=True, postgresql_where=text("ativo"), sqlite_where=text("ativo")),
        Index("ix_alertas_criado_em", "criado_em"),
        {"schema": "usr"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    modulo: Mapped[str] = mapped_column(String(10))
    titulo: Mapped[str] = mapped_column(String(200))
    detalhe: Mapped[str] = mapped_column(String(300))
    link: Mapped[str] = mapped_column(String(200))  # rota das telas, ex.: /manutencao/ordens/9
    perfis: Mapped[str] = mapped_column(String(300))  # perfis que recebem, separados por "|"
    chave: Mapped[str] = mapped_column(String(80))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertaLido(Base):
    __tablename__ = "alertas_lidos"
    __table_args__ = {"schema": "usr"}

    alerta_id: Mapped[int] = mapped_column(ForeignKey("usr.alertas.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id", ondelete="CASCADE"), primary_key=True)
    lido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
