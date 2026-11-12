"""Tabelas do módulo de Qualidade (schema qld).

Usuários vêm de usr.usuarios e máquinas de mnt.equipamentos (a Manutenção é a dona das TAGs).
Produtos (notebooks) ficam aqui até o módulo de Rastreabilidade, dono deles, existir na API única.
"""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modulos.manutencao.modelos import Equipamento
from app.modulos.qualidade.constantes import Classificacao, SituacaoProduto, StatusOcorrencia
from app.modulos.usuarios.modelos import Usuario


def _valores(enum) -> str:
    return ", ".join(f"'{e.value}'" for e in enum)


class Produto(Base):
    __tablename__ = "produtos"
    __table_args__ = (
        CheckConstraint("numero_serie = upper(numero_serie)", name="serie_maiuscula"),
        {"schema": "qld"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_serie: Mapped[str] = mapped_column(String(30), unique=True)
    modelo: Mapped[str] = mapped_column(String(50))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Estacao(Base):
    __tablename__ = "estacoes"
    __table_args__ = {"schema": "qld"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    descricao: Mapped[str | None] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class TipoDefeito(Base):
    __tablename__ = "tipos_defeito"
    __table_args__ = {"schema": "qld"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    descricao: Mapped[str | None] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Ocorrencia(Base):
    """Defeito apontado num notebook. Nunca é apagada: no máximo ocultada (some das listas e dos indicadores)."""

    __tablename__ = "ocorrencias"
    __table_args__ = (
        CheckConstraint(f"classificacao IN ({_valores(Classificacao)})", name="classificacao_valida"),
        CheckConstraint(f"situacao_produto IN ({_valores(SituacaoProduto)})", name="situacao_valida"),
        CheckConstraint(f"status IN ({_valores(StatusOcorrencia)})", name="status_valido"),
        Index("ix_ocorrencias_ocorrida_em", "ocorrida_em"),
        Index("ix_ocorrencias_status", "status"),
        {"schema": "qld"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ocorrida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    classificacao: Mapped[str] = mapped_column(String(20))
    situacao_produto: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default=StatusOcorrencia.ABERTA.value, server_default=StatusOcorrencia.ABERTA.value
    )
    observacao: Mapped[str] = mapped_column(Text)
    acao_realizada: Mapped[str] = mapped_column(Text)
    oculta: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("qld.produtos.id"))
    estacao_id: Mapped[int] = mapped_column(ForeignKey("qld.estacoes.id"))
    tipo_defeito_id: Mapped[int] = mapped_column(ForeignKey("qld.tipos_defeito.id"))
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("mnt.equipamentos.id"))
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))

    produto: Mapped[Produto] = relationship(lazy="joined")
    estacao: Mapped[Estacao] = relationship(lazy="joined")
    tipo_defeito: Mapped[TipoDefeito] = relationship(lazy="joined")
    equipamento: Mapped[Equipamento] = relationship(lazy="joined")
    responsavel: Mapped[Usuario] = relationship(lazy="joined")
