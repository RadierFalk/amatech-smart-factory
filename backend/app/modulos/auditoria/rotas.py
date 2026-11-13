"""Consulta da trilha de auditoria (/api/auditoria): Administrador e Supervisor (módulo AUD no rbac.py).

Só leitura: a trilha não é editada nem apagada pela API.
"""
from datetime import date, datetime, time, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.core import tempo
from app.core.deps import SessaoDep, exigir_modulo
from app.core.rbac import Modulo
from app.modulos.auditoria.modelos import RegistroAuditoria

rotas = APIRouter(prefix="/api/auditoria", tags=["Auditoria (AUD)"], dependencies=[Depends(exigir_modulo(Modulo.AUDITORIA))])


class RegistroSaida(BaseModel):
    id: int
    registrada_em: datetime
    usuario_matricula: str | None
    usuario_nome: str | None
    modulo: str
    entidade: str
    entidade_id: str
    descricao: str
    acao: Literal["CRIOU", "ALTEROU", "EXCLUIU"]
    alteracoes: dict[str, list[Any]]

    @classmethod
    def de(cls, r: RegistroAuditoria) -> "RegistroSaida":
        return cls(id=r.id, registrada_em=tempo.utc(r.registrada_em), usuario_matricula=r.usuario_matricula,
                   usuario_nome=r.usuario_nome, modulo=r.modulo, entidade=r.entidade, entidade_id=r.entidade_id,
                   descricao=r.descricao, acao=r.acao, alteracoes=r.alteracoes)


def _inicio(dia: date) -> datetime:
    """00:00 do dia da fábrica (Manaus), em UTC."""
    return tempo.utc(datetime.combine(dia, time(), tempo.FUSO_FABRICA))


@rotas.get("", response_model=list[RegistroSaida])
def listar(
    sessao: SessaoDep,
    modulo: Literal["RAS", "QLD", "MNT", "DSH", "USR"] | None = None,
    acao: Literal["CRIOU", "ALTEROU", "EXCLUIU"] | None = None,
    busca: str | None = Query(None, description="Registro (ex.: AMT-000025, OS #9) ou pessoa (nome ou matrícula)"),
    entidade: str | None = None,
    entidade_id: str | None = None,
    de: date | None = None,
    ate: date | None = None,
    limite: int = Query(200, ge=1, le=1000),
):
    """Mais recentes primeiro. Datas pelo dia da fábrica (Manaus)."""
    consulta = select(RegistroAuditoria)
    if modulo:
        consulta = consulta.where(RegistroAuditoria.modulo == modulo)
    if acao:
        consulta = consulta.where(RegistroAuditoria.acao == acao)
    if entidade:
        consulta = consulta.where(RegistroAuditoria.entidade == entidade)
    if entidade_id:
        consulta = consulta.where(RegistroAuditoria.entidade_id == entidade_id)
    if de:
        consulta = consulta.where(RegistroAuditoria.registrada_em >= _inicio(de))
    if ate:
        consulta = consulta.where(RegistroAuditoria.registrada_em < _inicio(ate + timedelta(days=1)))
    termo = (busca or "").strip()
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.where(or_(
            RegistroAuditoria.descricao.ilike(padrao),
            RegistroAuditoria.usuario_nome.ilike(padrao),
            RegistroAuditoria.usuario_matricula.ilike(padrao),
        ))
    consulta = consulta.order_by(RegistroAuditoria.registrada_em.desc(), RegistroAuditoria.id.desc()).limit(limite)
    return [RegistroSaida.de(r) for r in sessao.scalars(consulta)]
