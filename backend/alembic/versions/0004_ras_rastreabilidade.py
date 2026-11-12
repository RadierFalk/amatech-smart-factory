"""ras: etapas, componentes, modelos (BOM), produções, passagens, não conformidades e materiais

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12

Escrita à mão (sem Postgres na máquina de origem); o CI confere com `alembic check`.
Diferenças em relação ao SQLite antigo (rastreabilidade/database/migracoes/*.sql):
- usuários vêm de usr.usuarios (a tabela usuarios da RAS deixou de existir);
- produtos -> modelos, status_producao -> etapas, produto_componentes -> modelo_componentes,
  historico_passagem -> passagens, solicitacoes_materiais -> solicitacoes, baixas_materiais -> baixas;
- producoes.atualizada_em guarda a última passagem (antes era uma subconsulta);
- componentes e modelos ganharam `ativo` (são inativados, nunca apagados);
- integracao_clientes e integracao_eventos não vieram: na API única os módulos se chamam por dentro.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _usuario_fk(coluna: str, tabela: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([coluna], ["usr.usuarios.id"], name=op.f(f"fk_{tabela}_{coluna}_usuarios"))


def upgrade() -> None:
    op.create_table(
        "etapas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(50), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_etapas")),
        sa.UniqueConstraint("nome", name=op.f("uq_etapas_nome")),
        schema="ras",
    )
    op.create_table(
        "componentes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("estoque", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_componentes")),
        sa.UniqueConstraint("sku", name=op.f("uq_componentes_sku")),
        sa.CheckConstraint("sku = upper(sku)", name=op.f("ck_componentes_sku_maiusculo")),
        sa.CheckConstraint("estoque >= 0", name=op.f("ck_componentes_estoque_nao_negativo")),
        schema="ras",
    )
    op.create_table(
        "modelos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("meta", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modelos")),
        sa.UniqueConstraint("codigo", name=op.f("uq_modelos_codigo")),
        sa.CheckConstraint("codigo = upper(codigo)", name=op.f("ck_modelos_codigo_maiusculo")),
        schema="ras",
    )
    op.create_table(
        "modelo_componentes",
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("componente_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("modelo_id", "componente_id", name=op.f("pk_modelo_componentes")),
        sa.ForeignKeyConstraint(["modelo_id"], ["ras.modelos.id"], name=op.f("fk_modelo_componentes_modelo_id_modelos"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["componente_id"], ["ras.componentes.id"],
                                name=op.f("fk_modelo_componentes_componente_id_componentes")),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_modelo_componentes_quantidade_positiva")),
        schema="ras",
    )
    op.create_table(
        "producoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_serie", sa.String(30), nullable=False),
        sa.Column("id_unica", sa.String(50), nullable=False),
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("etapa_id", sa.Integer(), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_producoes")),
        sa.UniqueConstraint("numero_serie", name=op.f("uq_producoes_numero_serie")),
        sa.UniqueConstraint("id_unica", name=op.f("uq_producoes_id_unica")),
        sa.ForeignKeyConstraint(["modelo_id"], ["ras.modelos.id"], name=op.f("fk_producoes_modelo_id_modelos")),
        sa.ForeignKeyConstraint(["etapa_id"], ["ras.etapas.id"], name=op.f("fk_producoes_etapa_id_etapas")),
        _usuario_fk("responsavel_id", "producoes"),
        _usuario_fk("criado_por_id", "producoes"),
        schema="ras",
    )
    op.create_index("ix_producoes_etapa", "producoes", ["etapa_id"], schema="ras")
    op.create_index("ix_producoes_modelo", "producoes", ["modelo_id"], schema="ras")

    op.create_table(
        "passagens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("etapa_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), nullable=True),
        sa.Column("registrada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origem", sa.String(50), nullable=False, server_default="MANUAL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passagens")),
        sa.ForeignKeyConstraint(["producao_id"], ["ras.producoes.id"], name=op.f("fk_passagens_producao_id_producoes"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["etapa_id"], ["ras.etapas.id"], name=op.f("fk_passagens_etapa_id_etapas")),
        _usuario_fk("usuario_id", "passagens"),
        _usuario_fk("responsavel_id", "passagens"),
        schema="ras",
    )
    op.create_index("ix_passagens_producao", "passagens", ["producao_id", "registrada_em"], schema="ras")
    op.create_index("ix_passagens_registrada_em", "passagens", ["registrada_em"], schema="ras")

    op.create_table(
        "nao_conformidades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("descricao_falha", sa.Text(), nullable=False),
        sa.Column("motivo_reprovacao", sa.Text(), nullable=False),
        sa.Column("registrada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origem_sistema", sa.String(50), nullable=True),
        sa.Column("id_externo", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nao_conformidades")),
        sa.ForeignKeyConstraint(["producao_id"], ["ras.producoes.id"],
                                name=op.f("fk_nao_conformidades_producao_id_producoes"), ondelete="CASCADE"),
        _usuario_fk("usuario_id", "nao_conformidades"),
        schema="ras",
    )
    op.create_index("ix_nao_conformidades_producao", "nao_conformidades", ["producao_id"], schema="ras")
    op.create_index("ux_nao_conformidades_externo", "nao_conformidades", ["origem_sistema", "id_externo"], unique=True,
                    schema="ras", postgresql_where=sa.text("id_externo IS NOT NULL"))

    op.create_table(
        "solicitacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("componente_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solicitacoes")),
        sa.ForeignKeyConstraint(["producao_id"], ["ras.producoes.id"], name=op.f("fk_solicitacoes_producao_id_producoes"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["componente_id"], ["ras.componentes.id"],
                                name=op.f("fk_solicitacoes_componente_id_componentes")),
        _usuario_fk("criado_por_id", "solicitacoes"),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_solicitacoes_quantidade_positiva")),
        sa.CheckConstraint("status IN ('PENDENTE', 'PARCIAL', 'ATENDIDA', 'CANCELADA')",
                           name=op.f("ck_solicitacoes_status_valido")),
        schema="ras",
    )
    op.create_index("ix_solicitacoes_producao", "solicitacoes", ["producao_id"], schema="ras")
    op.create_index("ix_solicitacoes_status", "solicitacoes", ["status"], schema="ras")

    op.create_table(
        "baixas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("solicitacao_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("registrada_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_baixas")),
        sa.ForeignKeyConstraint(["solicitacao_id"], ["ras.solicitacoes.id"],
                                name=op.f("fk_baixas_solicitacao_id_solicitacoes"), ondelete="CASCADE"),
        _usuario_fk("usuario_id", "baixas"),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_baixas_quantidade_positiva")),
        schema="ras",
    )
    op.create_index("ix_baixas_solicitacao", "baixas", ["solicitacao_id"], schema="ras")


def downgrade() -> None:
    for tabela in ("baixas", "solicitacoes", "nao_conformidades", "passagens", "producoes", "modelo_componentes",
                   "modelos", "componentes", "etapas"):
        op.drop_table(tabela, schema="ras")
