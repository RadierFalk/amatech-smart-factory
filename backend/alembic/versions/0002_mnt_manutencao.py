"""mnt: máquinas, peças, chamados/OS, peças trocadas e auditoria de status

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10

Escrita à mão (sem Postgres na máquina de origem). Confira com `alembic check` depois de subir o banco.
Diferenças em relação ao SQLite antigo (manutencao/docs/02_DATABASE_SCHEMA.sql):
- usuários vêm de usr.usuarios (a tabela mnt.usuarios deixou de existir);
- chamados_manutencao -> chamados; chamado_pecas_trocadas -> chamado_pecas (uma linha por peça);
- novo motivo_cancelamento (antes o motivo era gravado por cima do diagnóstico);
- índice único parcial ux_chamados_uma_os_ativa garante a RN02 no banco.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_EQUIP = "'OPERACIONAL', 'EM_MANUTENCAO', 'PARADA'"


def upgrade() -> None:
    op.create_table(
        "equipamentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo_tag", sa.String(30), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("setor", sa.String(50), nullable=False),
        sa.Column("posto_trabalho", sa.String(50), nullable=True),
        sa.Column("status_operacional", sa.String(20), nullable=False, server_default="OPERACIONAL"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_equipamentos")),
        sa.UniqueConstraint("codigo_tag", name=op.f("uq_equipamentos_codigo_tag")),
        sa.CheckConstraint(f"status_operacional IN ({STATUS_EQUIP})", name=op.f("ck_equipamentos_status_valido")),
        sa.CheckConstraint("codigo_tag = upper(codigo_tag)", name=op.f("ck_equipamentos_tag_maiuscula")),
        schema="mnt",
    )

    op.create_table(
        "pecas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo_peca", sa.String(50), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("unidade_medida", sa.String(10), nullable=False, server_default="UN"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pecas")),
        sa.UniqueConstraint("codigo_peca", name=op.f("uq_pecas_codigo_peca")),
        sa.CheckConstraint("codigo_peca = upper(codigo_peca)", name=op.f("ck_pecas_codigo_maiusculo")),
        schema="mnt",
    )

    op.create_table(
        "chamados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipamento_id", sa.Integer(), nullable=False),
        sa.Column("operador_abertura_id", sa.Integer(), nullable=False),
        sa.Column("tecnico_responsavel_id", sa.Integer(), nullable=True),
        sa.Column("prioridade", sa.String(20), nullable=False),
        sa.Column("tipo_manutencao", sa.String(20), nullable=False, server_default="CORRETIVA"),
        sa.Column("status_chamado", sa.String(20), nullable=False, server_default="ABERTO"),
        sa.Column("descricao_falha", sa.Text(), nullable=False),
        sa.Column("diagnostico_tecnico", sa.Text(), nullable=True),
        sa.Column("causa_raiz", sa.String(150), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column("data_hora_abertura", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_hora_inicio_atendimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_hora_fim_atendimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downtime_minutos", sa.Integer(), nullable=True),
        sa.Column("origem_sistema", sa.String(50), nullable=True),
        sa.Column("id_externo", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chamados")),
        sa.ForeignKeyConstraint(
            ["equipamento_id"], ["mnt.equipamentos.id"], name=op.f("fk_chamados_equipamento_id_equipamentos")
        ),
        sa.ForeignKeyConstraint(
            ["operador_abertura_id"], ["usr.usuarios.id"], name=op.f("fk_chamados_operador_abertura_id_usuarios")
        ),
        sa.ForeignKeyConstraint(
            ["tecnico_responsavel_id"], ["usr.usuarios.id"], name=op.f("fk_chamados_tecnico_responsavel_id_usuarios")
        ),
        sa.CheckConstraint("prioridade IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA')", name=op.f("ck_chamados_prioridade_valida")),
        sa.CheckConstraint("tipo_manutencao IN ('CORRETIVA', 'PREVENTIVA')", name=op.f("ck_chamados_tipo_valido")),
        sa.CheckConstraint(
            "status_chamado IN ('ABERTO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO')", name=op.f("ck_chamados_status_valido")
        ),
        sa.CheckConstraint(
            "downtime_minutos IS NULL OR downtime_minutos >= 0", name=op.f("ck_chamados_downtime_nao_negativo")
        ),
        schema="mnt",
    )
    op.create_index("ix_chamados_status", "chamados", ["status_chamado"], schema="mnt")
    op.create_index("ix_chamados_equipamento_abertura", "chamados", ["equipamento_id", "data_hora_abertura"], schema="mnt")
    op.create_index("ix_chamados_tecnico", "chamados", ["tecnico_responsavel_id"], schema="mnt")
    op.create_index(
        "ux_chamados_uma_os_ativa",
        "chamados",
        ["equipamento_id"],
        unique=True,
        schema="mnt",
        postgresql_where=sa.text("status_chamado IN ('ABERTO', 'EM_ANDAMENTO')"),
    )
    op.create_index(
        "ux_chamados_externo",
        "chamados",
        ["origem_sistema", "id_externo"],
        unique=True,
        schema="mnt",
        postgresql_where=sa.text("id_externo IS NOT NULL"),
    )

    op.create_table(
        "chamado_pecas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chamado_id", sa.Integer(), nullable=False),
        sa.Column("peca_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Numeric(10, 2), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chamado_pecas")),
        sa.ForeignKeyConstraint(
            ["chamado_id"], ["mnt.chamados.id"], name=op.f("fk_chamado_pecas_chamado_id_chamados"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["peca_id"], ["mnt.pecas.id"], name=op.f("fk_chamado_pecas_peca_id_pecas")),
        sa.UniqueConstraint("chamado_id", "peca_id", name=op.f("uq_chamado_pecas_chamado_peca")),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_chamado_pecas_quantidade_positiva")),
        schema="mnt",
    )

    op.create_table(
        "historico_status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipamento_id", sa.Integer(), nullable=False),
        sa.Column("chamado_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("status_anterior", sa.String(20), nullable=False),
        sa.Column("status_novo", sa.String(20), nullable=False),
        sa.Column("alterado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historico_status")),
        sa.ForeignKeyConstraint(
            ["equipamento_id"], ["mnt.equipamentos.id"], name=op.f("fk_historico_status_equipamento_id_equipamentos")
        ),
        sa.ForeignKeyConstraint(["chamado_id"], ["mnt.chamados.id"], name=op.f("fk_historico_status_chamado_id_chamados")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usr.usuarios.id"], name=op.f("fk_historico_status_usuario_id_usuarios")),
        sa.CheckConstraint(f"status_anterior IN ({STATUS_EQUIP})", name=op.f("ck_historico_status_anterior_valido")),
        sa.CheckConstraint(f"status_novo IN ({STATUS_EQUIP})", name=op.f("ck_historico_status_novo_valido")),
        schema="mnt",
    )
    op.create_index(
        "ix_historico_status_equipamento_data", "historico_status", ["equipamento_id", "alterado_em"], schema="mnt"
    )


def downgrade() -> None:
    op.drop_table("historico_status", schema="mnt")
    op.drop_table("chamado_pecas", schema="mnt")
    op.drop_table("chamados", schema="mnt")
    op.drop_table("pecas", schema="mnt")
    op.drop_table("equipamentos", schema="mnt")
