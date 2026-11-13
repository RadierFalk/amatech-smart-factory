"""usr: trilha de auditoria de todos os módulos

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-13

Uma linha por registro criado, alterado ou excluído (app/modulos/auditoria/registro.py), com os campos antes e
depois em JSONB. Fica no schema usr, junto das contas, e é consultada pelo módulo AUD (Administrador e Supervisor).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("registrada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("usuario_matricula", sa.String(20), nullable=True),
        sa.Column("usuario_nome", sa.String(100), nullable=True),
        sa.Column("modulo", sa.String(10), nullable=False),
        sa.Column("entidade", sa.String(60), nullable=False),
        sa.Column("entidade_id", sa.String(60), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("acao", sa.String(10), nullable=False),
        sa.Column("alteracoes", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usr.usuarios.id"], name=op.f("fk_auditoria_usuario_id_usuarios"),
                                ondelete="SET NULL"),
        sa.CheckConstraint("acao IN ('CRIOU', 'ALTEROU', 'EXCLUIU')", name=op.f("ck_auditoria_acao_valida")),
        schema="usr",
    )
    op.create_index("ix_auditoria_registrada_em", "auditoria", ["registrada_em"], schema="usr")
    op.create_index("ix_auditoria_entidade", "auditoria", ["entidade", "entidade_id"], schema="usr")
    op.create_index("ix_auditoria_usuario_id", "auditoria", ["usuario_id"], schema="usr")


def downgrade() -> None:
    op.drop_table("auditoria", schema="usr")
