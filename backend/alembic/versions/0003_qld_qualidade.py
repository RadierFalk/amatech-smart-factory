"""qld: produtos, estações, tipos de defeito e ocorrências

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12

Escrita à mão (sem Postgres na máquina de origem); o CI confere com `alembic check`.
Diferenças em relação ao SQLite antigo (qualidade/criar_banco.py):
- usuários vêm de usr.usuarios e máquinas de mnt.equipamentos (as tabelas usuario e maquina deixaram de existir);
- data e hora (texto, hora de Manaus) viraram ocorrida_em (timestamptz, UTC);
- classificação, situação e status em códigos maiúsculos (CRITICO, EM_REPROCESSO, EM_ANALISE...);
- visibilidade 'Visivel'/'Oculta' virou o booleano oculta;
- produtos, estações e tipos de defeito ganharam `ativo` (são inativados, nunca apagados).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ativo() -> sa.Column:
    return sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true"))


def upgrade() -> None:
    op.create_table(
        "produtos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_serie", sa.String(30), nullable=False),
        sa.Column("modelo", sa.String(50), nullable=False),
        _ativo(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_produtos")),
        sa.UniqueConstraint("numero_serie", name=op.f("uq_produtos_numero_serie")),
        sa.CheckConstraint("numero_serie = upper(numero_serie)", name=op.f("ck_produtos_serie_maiuscula")),
        schema="qld",
    )
    for tabela in ("estacoes", "tipos_defeito"):
        op.create_table(
            tabela,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(60), nullable=False),
            sa.Column("descricao", sa.String(200), nullable=True),
            _ativo(),
            sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{tabela}")),
            sa.UniqueConstraint("nome", name=op.f(f"uq_{tabela}_nome")),
            schema="qld",
        )

    op.create_table(
        "ocorrencias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ocorrida_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("classificacao", sa.String(20), nullable=False),
        sa.Column("situacao_produto", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ABERTA"),
        sa.Column("observacao", sa.Text(), nullable=False),
        sa.Column("acao_realizada", sa.Text(), nullable=False),
        sa.Column("oculta", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("estacao_id", sa.Integer(), nullable=False),
        sa.Column("tipo_defeito_id", sa.Integer(), nullable=False),
        sa.Column("equipamento_id", sa.Integer(), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocorrencias")),
        sa.ForeignKeyConstraint(["produto_id"], ["qld.produtos.id"], name=op.f("fk_ocorrencias_produto_id_produtos")),
        sa.ForeignKeyConstraint(["estacao_id"], ["qld.estacoes.id"], name=op.f("fk_ocorrencias_estacao_id_estacoes")),
        sa.ForeignKeyConstraint(
            ["tipo_defeito_id"], ["qld.tipos_defeito.id"], name=op.f("fk_ocorrencias_tipo_defeito_id_tipos_defeito")
        ),
        sa.ForeignKeyConstraint(
            ["equipamento_id"], ["mnt.equipamentos.id"], name=op.f("fk_ocorrencias_equipamento_id_equipamentos")
        ),
        sa.ForeignKeyConstraint(["responsavel_id"], ["usr.usuarios.id"], name=op.f("fk_ocorrencias_responsavel_id_usuarios")),
        sa.CheckConstraint("classificacao IN ('CRITICO', 'MAIOR', 'MENOR')", name=op.f("ck_ocorrencias_classificacao_valida")),
        sa.CheckConstraint(
            "situacao_produto IN ('APROVADO', 'REPROVADO', 'EM_REPROCESSO')", name=op.f("ck_ocorrencias_situacao_valida")
        ),
        sa.CheckConstraint("status IN ('ABERTA', 'EM_ANALISE', 'RESOLVIDA')", name=op.f("ck_ocorrencias_status_valido")),
        schema="qld",
    )
    op.create_index("ix_ocorrencias_ocorrida_em", "ocorrencias", ["ocorrida_em"], schema="qld")
    op.create_index("ix_ocorrencias_status", "ocorrencias", ["status"], schema="qld")


def downgrade() -> None:
    op.drop_table("ocorrencias", schema="qld")
    op.drop_table("tipos_defeito", schema="qld")
    op.drop_table("estacoes", schema="qld")
    op.drop_table("produtos", schema="qld")
