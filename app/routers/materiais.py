from fastapi import APIRouter, Depends

from app.db import get_conn
from app.schemas import BaixaEdicaoIn, BaixaIn, SolicitacaoEdicaoIn, SolicitacaoIn
from app.seguranca import exigir_baixa, usuario_atual
from app.servicos import materiais as svc

router = APIRouter(prefix="/api", tags=["Materiais"])


# ---- solicitações ----
@router.get("/solicitacoes")
def listar_solicitacoes(status: str | None = None, producao_id: int | None = None,
                        conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_solicitacoes(conn, status, producao_id)


@router.post("/solicitacoes", status_code=201)
def criar_solicitacao(dados: SolicitacaoIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.criar_solicitacao(conn, dados.producao_id, dados.componente_id, dados.quantidade_solicitada, usuario)


@router.post("/producoes/{producao_id}/solicitar-materiais", status_code=201)
def solicitar_materiais_da_producao(producao_id: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.gerar_solicitacoes_da_producao(conn, producao_id, usuario)


@router.put("/solicitacoes/{solicitacao_id}")
def atualizar_solicitacao(solicitacao_id: int, dados: SolicitacaoEdicaoIn, conn=Depends(get_conn),
                          usuario=Depends(usuario_atual)):
    return svc.atualizar_solicitacao(conn, solicitacao_id, dados.quantidade_solicitada, dados.cancelada)


@router.delete("/solicitacoes/{solicitacao_id}")
def excluir_solicitacao(solicitacao_id: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    svc.excluir_solicitacao(conn, solicitacao_id)
    return {"ok": True}


# ---- baixas (somente Almoxarife e Administrador) ----
@router.get("/baixas")
def listar_baixas(conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_baixas(conn)


@router.post("/baixas", status_code=201)
def criar_baixa(dados: BaixaIn, conn=Depends(get_conn), usuario=Depends(exigir_baixa)):
    return svc.criar_baixa(conn, dados.solicitacao_id, dados.quantidade_baixada, usuario)


@router.put("/baixas/{baixa_id}")
def atualizar_baixa(baixa_id: int, dados: BaixaEdicaoIn, conn=Depends(get_conn), usuario=Depends(exigir_baixa)):
    return svc.atualizar_baixa(conn, baixa_id, dados.quantidade_baixada)


@router.delete("/baixas/{baixa_id}")
def excluir_baixa(baixa_id: int, conn=Depends(get_conn), usuario=Depends(exigir_baixa)):
    svc.excluir_baixa(conn, baixa_id)
    return {"ok": True}
