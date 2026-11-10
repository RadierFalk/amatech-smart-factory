"""Tabela central de usuários (schema usr). Todos os módulos referenciam usr.usuarios.id."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.rbac import Perfil

_PERFIS_SQL = ", ".join(f"'{p.value}'" for p in Perfil)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(f"perfil IN ({_PERFIS_SQL})", name="perfil_valido"),
        CheckConstraint("matricula = upper(matricula)", name="matricula_maiuscula"),
        {"schema": "usr"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)  # UNIQUE já cria índice no Postgres
    nome: Mapped[str] = mapped_column(String(100))
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(50))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
