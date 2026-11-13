"""Trilha de auditoria (usr.auditoria): uma linha por registro criado, alterado ou excluído, com os campos antes e
depois. Quem fez fica também por matrícula e nome, para continuar legível se a conta for desativada."""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ACOES = ("CRIOU", "ALTEROU", "EXCLUIU")


class RegistroAuditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        CheckConstraint(f"acao IN ({', '.join(repr(a) for a in ACOES)})", name="acao_valida"),
        Index("ix_auditoria_registrada_em", "registrada_em"),
        Index("ix_auditoria_entidade", "entidade", "entidade_id"),
        Index("ix_auditoria_usuario_id", "usuario_id"),
        {"schema": "usr"},
    )

    # BIGINT: a trilha cresce sem parar. No SQLite dos testes, INTEGER para o id ser gerado sozinho.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    registrada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usr.usuarios.id", ondelete="SET NULL"))
    usuario_matricula: Mapped[str | None] = mapped_column(String(20))
    usuario_nome: Mapped[str | None] = mapped_column(String(100))
    modulo: Mapped[str] = mapped_column(String(10))       # RAS, QLD, MNT, DSH, USR
    entidade: Mapped[str] = mapped_column(String(60))     # tabela, ex.: qld.ocorrencias
    entidade_id: Mapped[str] = mapped_column(String(60))  # chave do registro (composta: "3/7")
    descricao: Mapped[str] = mapped_column(String(200))   # ex.: "Ocorrência #17", "Produção AMT-000025"
    acao: Mapped[str] = mapped_column(String(10))
    # {campo: [antes, depois]}; na criação o "antes" é null, na exclusão o "depois" é null.
    alteracoes: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
