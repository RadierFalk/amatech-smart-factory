"""Tabelas do módulo de Rastreabilidade (schema ras). Usuários vêm de usr.usuarios.

Nomes novos em relação ao SQLite antigo (rastreabilidade/database/migracoes/001_base.sql):
produtos -> modelos (são modelos de notebook; "produto" na Qualidade é o notebook), status_producao -> etapas,
produto_componentes -> modelo_componentes, historico_passagem -> passagens,
solicitacoes_materiais -> solicitacoes, baixas_materiais -> baixas.
"""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modulos.rastreabilidade.constantes import StatusSolicitacao
from app.modulos.usuarios.modelos import Usuario

_STATUS_SOLICITACAO = ", ".join(f"'{s.value}'" for s in StatusSolicitacao)


class Etapa(Base):
    __tablename__ = "etapas"
    __table_args__ = {"schema": "ras"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True)
    ordem: Mapped[int] = mapped_column(Integer)


class Componente(Base):
    __tablename__ = "componentes"
    __table_args__ = (
        CheckConstraint("sku = upper(sku)", name="sku_maiusculo"),
        CheckConstraint("estoque >= 0", name="estoque_nao_negativo"),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    estoque: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Modelo(Base):
    """Modelo de notebook (ex.: AMT N14) com a lista de componentes (BOM)."""

    __tablename__ = "modelos"
    __table_args__ = (
        CheckConstraint("codigo = upper(codigo)", name="codigo_maiusculo"),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    meta: Mapped[int | None] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    componentes: Mapped[list["ModeloComponente"]] = relationship(
        back_populates="modelo", cascade="all, delete-orphan", lazy="selectin"
    )


class ModeloComponente(Base):
    __tablename__ = "modelo_componentes"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        {"schema": "ras"},
    )

    modelo_id: Mapped[int] = mapped_column(ForeignKey("ras.modelos.id", ondelete="CASCADE"), primary_key=True)
    componente_id: Mapped[int] = mapped_column(ForeignKey("ras.componentes.id"), primary_key=True)
    quantidade: Mapped[int] = mapped_column(Integer)

    modelo: Mapped[Modelo] = relationship(back_populates="componentes")
    componente: Mapped[Componente] = relationship(lazy="joined")


class Producao(Base):
    """Um notebook em produção, identificado pelo número de série."""

    __tablename__ = "producoes"
    __table_args__ = (
        Index("ix_producoes_etapa", "etapa_id"),
        Index("ix_producoes_modelo", "modelo_id"),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_serie: Mapped[str] = mapped_column(String(30), unique=True)
    id_unica: Mapped[str] = mapped_column(String(50), unique=True)
    modelo_id: Mapped[int] = mapped_column(ForeignKey("ras.modelos.id"))
    etapa_id: Mapped[int] = mapped_column(ForeignKey("ras.etapas.id"))
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    modelo: Mapped[Modelo] = relationship(lazy="joined")
    etapa: Mapped[Etapa] = relationship(lazy="joined")
    responsavel: Mapped[Usuario] = relationship(foreign_keys=[responsavel_id], lazy="joined")
    criado_por: Mapped[Usuario] = relationship(foreign_keys=[criado_por_id], lazy="joined")


class Passagem(Base):
    """Histórico de etapas da produção (RF007): quem mudou, quando, para quem e por qual origem."""

    __tablename__ = "passagens"
    __table_args__ = (
        Index("ix_passagens_producao", "producao_id", "registrada_em"),
        Index("ix_passagens_registrada_em", "registrada_em"),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producao_id: Mapped[int] = mapped_column(ForeignKey("ras.producoes.id", ondelete="CASCADE"))
    etapa_id: Mapped[int] = mapped_column(ForeignKey("ras.etapas.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    responsavel_id: Mapped[int | None] = mapped_column(ForeignKey("usr.usuarios.id"))
    registrada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origem: Mapped[str] = mapped_column(String(50), default="MANUAL", server_default="MANUAL")

    etapa: Mapped[Etapa] = relationship(lazy="joined")
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id], lazy="joined")
    responsavel: Mapped[Usuario | None] = relationship(foreign_keys=[responsavel_id], lazy="joined")


class NaoConformidade(Base):
    __tablename__ = "nao_conformidades"
    __table_args__ = (
        Index("ix_nao_conformidades_producao", "producao_id"),
        # Reenvio de outro módulo (ex.: QLD-12 da Qualidade) não duplica a não conformidade.
        Index(
            "ux_nao_conformidades_externo",
            "origem_sistema",
            "id_externo",
            unique=True,
            postgresql_where=text("id_externo IS NOT NULL"),
            sqlite_where=text("id_externo IS NOT NULL"),
        ),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producao_id: Mapped[int] = mapped_column(ForeignKey("ras.producoes.id", ondelete="CASCADE"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    descricao_falha: Mapped[str] = mapped_column(Text)
    motivo_reprovacao: Mapped[str] = mapped_column(Text)
    registrada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origem_sistema: Mapped[str | None] = mapped_column(String(50))
    id_externo: Mapped[str | None] = mapped_column(String(100))

    usuario: Mapped[Usuario] = relationship(lazy="joined")
    producao: Mapped[Producao] = relationship(lazy="joined")


class Solicitacao(Base):
    """Pedido de material de uma produção ao almoxarifado (RF014)."""

    __tablename__ = "solicitacoes"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint(f"status IN ({_STATUS_SOLICITACAO})", name="status_valido"),
        Index("ix_solicitacoes_producao", "producao_id"),
        Index("ix_solicitacoes_status", "status"),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producao_id: Mapped[int] = mapped_column(ForeignKey("ras.producoes.id", ondelete="CASCADE"))
    componente_id: Mapped[int] = mapped_column(ForeignKey("ras.componentes.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default=StatusSolicitacao.PENDENTE.value, server_default=StatusSolicitacao.PENDENTE.value
    )
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    producao: Mapped[Producao] = relationship(lazy="joined")
    componente: Mapped[Componente] = relationship(lazy="joined")
    criado_por: Mapped[Usuario] = relationship(lazy="joined")
    baixas: Mapped[list["Baixa"]] = relationship(back_populates="solicitacao", lazy="selectin", order_by="Baixa.id")

    @property
    def quantidade_baixada(self) -> int:
        return sum(b.quantidade for b in self.baixas)


class Baixa(Base):
    """Saída de material do estoque para atender uma solicitação (RF015)."""

    __tablename__ = "baixas"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        Index("ix_baixas_solicitacao", "solicitacao_id"),
        {"schema": "ras"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitacao_id: Mapped[int] = mapped_column(ForeignKey("ras.solicitacoes.id", ondelete="CASCADE"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usr.usuarios.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    registrada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    solicitacao: Mapped[Solicitacao] = relationship(back_populates="baixas")
    usuario: Mapped[Usuario] = relationship(lazy="joined")
