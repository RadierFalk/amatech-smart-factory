from fastapi import APIRouter, Depends

from app.db import get_conn
from app.schemas import AvancarIn, NaoConformidadeIn, ProducaoEdicaoIn, ProducaoIn
from app.seguranca import usuario_atual
from app.servicos import producao as svc

router = APIRouter(prefix="/api/producoes", tags=["Produção"])


@router.get("")
def listar(q: str | None = None, status_id: int | None = None, produto_id: int | None = None,
           conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_producoes(conn, q, status_id, produto_id)


@router.get("/{producao_id}")
def obter(producao_id: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.obter_producao(conn, producao_id)


@router.post("", status_code=201)
def criar(dados: ProducaoIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.criar_producao(conn, dados.produto_id, dados.responsavel_etapa_id, usuario)


@router.put("/{producao_id}")
def atualizar(producao_id: int, dados: ProducaoEdicaoIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.atualizar_producao(conn, producao_id, dados.produto_id, dados.responsavel_etapa_id)


@router.delete("/{producao_id}")
def excluir(producao_id: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    svc.excluir_producao(conn, producao_id)
    return {"ok": True}


@router.post("/{producao_id}/avancar")
def avancar(producao_id: int, dados: AvancarIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.avancar_etapa(conn, producao_id, dados.status_id, dados.responsavel_etapa_id, usuario,
                             dados.descricao_falha, dados.motivo_reprovacao)


@router.post("/{producao_id}/nao-conformidades", status_code=201)
def registrar_nao_conformidade(producao_id: int, dados: NaoConformidadeIn, conn=Depends(get_conn),
                               usuario=Depends(usuario_atual)):
    return svc.registrar_nao_conformidade(conn, producao_id, dados.descricao_falha, dados.motivo_reprovacao, usuario)
