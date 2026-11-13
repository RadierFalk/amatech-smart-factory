"""qld: produto ligado à produção da Rastreabilidade

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-13

Cada notebook da Qualidade (qld.produtos) passa a apontar para a sua produção em ras.producoes (1 para 1).
Os produtos que já existem são ligados pelo número de série, e o modelo passa a ser o da Rastreabilidade
(a dona do notebook). Produtos sem produção correspondente ficam como histórico, sem ligação.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("produtos", sa.Column("producao_id", sa.Integer(), nullable=True), schema="qld")
    op.create_unique_constraint(op.f("uq_produtos_producao_id"), "produtos", ["producao_id"], schema="qld")
    op.create_foreign_key(
        op.f("fk_produtos_producao_id_producoes"), "produtos", "producoes", ["producao_id"], ["id"],
        source_schema="qld", referent_schema="ras", ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE qld.produtos AS q
           SET producao_id = p.id, modelo = m.nome
          FROM ras.producoes AS p
          JOIN ras.modelos AS m ON m.id = p.modelo_id
         WHERE upper(p.numero_serie) = q.numero_serie
        """
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_produtos_producao_id_producoes"), "produtos", schema="qld", type_="foreignkey")
    op.drop_constraint(op.f("uq_produtos_producao_id"), "produtos", schema="qld", type_="unique")
    op.drop_column("produtos", "producao_id", schema="qld")
