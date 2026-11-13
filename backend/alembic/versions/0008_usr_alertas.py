"""usr: alertas do sino e quem já leu cada um

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-13

Um alerta por situação aberta (OS de prioridade alta, máquina parada sem técnico, estoque insuficiente, ocorrência
crítica), criado e resolvido por app/modulos/alertas/servico.py. O índice único parcial garante um alerta ATIVO por
chave mesmo com várias telas consultando ao mesmo tempo.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("modulo", sa.String(10), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("detalhe", sa.String(300), nullable=False),
        sa.Column("link", sa.String(200), nullable=False),
        sa.Column("perfis", sa.String(300), nullable=False),
        sa.Column("chave", sa.String(80), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolvido_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alertas")),
        sa.CheckConstraint(
            "tipo IN ('CHAMADO_ABERTO', 'PARADA_SEM_TECNICO', 'ESTOQUE_INSUFICIENTE', 'OCORRENCIA_CRITICA')",
            name=op.f("ck_alertas_tipo_valido"),
        ),
        schema="usr",
    )
    op.create_index("ux_alertas_chave_ativo", "alertas", ["chave"], unique=True, schema="usr",
                    postgresql_where=sa.text("ativo"))
    op.create_index("ix_alertas_criado_em", "alertas", ["criado_em"], schema="usr")
    op.create_table(
        "alertas_lidos",
        sa.Column("alerta_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("lido_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("alerta_id", "usuario_id", name=op.f("pk_alertas_lidos")),
        sa.ForeignKeyConstraint(["alerta_id"], ["usr.alertas.id"], name=op.f("fk_alertas_lidos_alerta_id_alertas"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usr.usuarios.id"], name=op.f("fk_alertas_lidos_usuario_id_usuarios"),
                                ondelete="CASCADE"),
        schema="usr",
    )


def downgrade() -> None:
    op.drop_table("alertas_lidos", schema="usr")
    op.drop_table("alertas", schema="usr")
