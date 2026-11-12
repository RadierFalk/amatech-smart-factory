"""dsh: turnos, limites do semáforo, metas, tipos de perda e perdas

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12

Escrita à mão (sem Postgres na máquina de origem); o CI confere com `alembic check`.
Diferenças em relação ao SQLite antigo (dashboard/database/banco_dashboard_industrial.sql):
- registro_producao, defeito, retrabalho, parada, importacao, produto, estacao, maquina, tipo_defeito e
  motivo_parada não vieram: os indicadores são calculados na hora a partir de ras, qld e mnt;
- usuario e perfil não vieram (usr.usuarios);
- meta_producao -> metas (modelo de ras.modelos); parametro_alerta -> limites (chave = indicador);
- perda -> perdas (estação de qld.estacoes, modelo de ras.modelos) e tipo_perda -> tipos_perda (com `ativo`);
- turno guarda hora de início e fim (TIME); a duração é calculada.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "turnos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(30), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fim", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_turnos")),
        sa.UniqueConstraint("nome", name=op.f("uq_turnos_nome")),
        sa.CheckConstraint("hora_fim > hora_inicio", name=op.f("ck_turnos_horario_valido")),
        schema="dsh",
    )
    op.create_table(
        "limites",
        sa.Column("indicador", sa.String(30), nullable=False),
        sa.Column("limite_verde", sa.Float(), nullable=False),
        sa.Column("limite_amarelo", sa.Float(), nullable=False),
        sa.Column("sentido", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("indicador", name=op.f("pk_limites")),
        sa.CheckConstraint("indicador IN ('atendimento_meta', 'indice_defeitos', 'indice_retrabalho')",
                           name=op.f("ck_limites_indicador_valido")),
        sa.CheckConstraint("sentido IN ('maior_melhor', 'menor_melhor')", name=op.f("ck_limites_sentido_valido")),
        sa.CheckConstraint("limite_verde >= 0 AND limite_amarelo >= 0", name=op.f("ck_limites_limites_nao_negativos")),
        schema="dsh",
    )
    op.create_table(
        "metas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("turno_id", sa.Integer(), nullable=False),
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("registrado_por_id", sa.Integer(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metas")),
        sa.UniqueConstraint("data", "turno_id", "modelo_id", name=op.f("uq_metas_data_turno_modelo")),
        sa.ForeignKeyConstraint(["turno_id"], ["dsh.turnos.id"], name=op.f("fk_metas_turno_id_turnos")),
        sa.ForeignKeyConstraint(["modelo_id"], ["ras.modelos.id"], name=op.f("fk_metas_modelo_id_modelos")),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usr.usuarios.id"], name=op.f("fk_metas_registrado_por_id_usuarios")),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_metas_quantidade_positiva")),
        schema="dsh",
    )
    op.create_table(
        "tipos_perda",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tipos_perda")),
        sa.UniqueConstraint("nome", name=op.f("uq_tipos_perda_nome")),
        schema="dsh",
    )
    op.create_table(
        "perdas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("turno_id", sa.Integer(), nullable=False),
        sa.Column("estacao_id", sa.Integer(), nullable=False),
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("tipo_perda_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("registrado_por_id", sa.Integer(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_perdas")),
        sa.ForeignKeyConstraint(["turno_id"], ["dsh.turnos.id"], name=op.f("fk_perdas_turno_id_turnos")),
        sa.ForeignKeyConstraint(["estacao_id"], ["qld.estacoes.id"], name=op.f("fk_perdas_estacao_id_estacoes")),
        sa.ForeignKeyConstraint(["modelo_id"], ["ras.modelos.id"], name=op.f("fk_perdas_modelo_id_modelos")),
        sa.ForeignKeyConstraint(["tipo_perda_id"], ["dsh.tipos_perda.id"], name=op.f("fk_perdas_tipo_perda_id_tipos_perda")),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usr.usuarios.id"], name=op.f("fk_perdas_registrado_por_id_usuarios")),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_perdas_quantidade_positiva")),
        sa.CheckConstraint("origem IN ('manual', 'csv')", name=op.f("ck_perdas_origem_valida")),
        schema="dsh",
    )
    op.create_index("ix_perdas_data", "perdas", ["data"], schema="dsh")


def downgrade() -> None:
    for tabela in ("perdas", "tipos_perda", "metas", "limites", "turnos"):
        op.drop_table(tabela, schema="dsh")
