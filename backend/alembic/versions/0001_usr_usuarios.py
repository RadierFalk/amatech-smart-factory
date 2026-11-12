"""usr: schemas dos módulos e tabela central de usuários

Revision ID: 0001
Revises:
Create Date: 2026-11-10

Escrita à mão (sem Postgres disponível na máquina de origem). Depois de subir o banco,
confira com `alembic check`: o resultado deve ser "No new upgrade operations detected".
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIS = (
    "Administrador",
    "Supervisor / Gestor",
    "Inspetor de Qualidade",
    "Operador de Produção",
    "Técnico de Manutenção",
    "Almoxarife",
)


def upgrade() -> None:
    for schema in ("usr", "ras", "qld", "mnt", "dsh"):
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    perfis_sql = ", ".join(f"'{p}'" for p in PERFIS)
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("matricula", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(50), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuarios")),
        sa.UniqueConstraint("matricula", name=op.f("uq_usuarios_matricula")),
        sa.CheckConstraint(f"perfil IN ({perfis_sql})", name=op.f("ck_usuarios_perfil_valido")),
        sa.CheckConstraint("matricula = upper(matricula)", name=op.f("ck_usuarios_matricula_maiuscula")),
        schema="usr",
    )


def downgrade() -> None:
    op.drop_table("usuarios", schema="usr")
    # Os schemas ficam: podem conter tabelas de migrações posteriores.
