from fastapi import APIRouter, Depends

from app.db import get_conn
from app.schemas import ComponenteIn, ProdutoIn, StatusIn, UsuarioIn
from app.seguranca import exigir_admin, usuario_atual
from app.servicos import cadastros as svc

router = APIRouter(prefix="/api", tags=["Cadastros"])


# ---- usuários (só administrador altera) ----
@router.get("/usuarios")
def listar_usuarios(apenas_ativos: int = 0, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_usuarios(conn, bool(apenas_ativos))


@router.post("/usuarios", status_code=201)
def criar_usuario(dados: UsuarioIn, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.criar_usuario(conn, dados.model_dump(), usuario)


@router.put("/usuarios/{usuario_id}")
def atualizar_usuario(usuario_id: int, dados: UsuarioIn, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.atualizar_usuario(conn, usuario_id, dados.model_dump(), usuario)


@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(usuario_id: int, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    svc.excluir_usuario(conn, usuario_id, usuario)
    return {"ok": True}


@router.get("/cargos")
def listar_cargos(usuario=Depends(usuario_atual)):
    from app import config
    return config.CARGOS


# ---- status de produção ----
@router.get("/status")
def listar_status(conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_status(conn)


@router.post("/status", status_code=201)
def criar_status(dados: StatusIn, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.criar_status(conn, dados.model_dump(), usuario)


@router.put("/status/{status_id}")
def atualizar_status(status_id: int, dados: StatusIn, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.atualizar_status(conn, status_id, dados.model_dump())


@router.delete("/status/{status_id}")
def excluir_status(status_id: int, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    svc.excluir_status(conn, status_id)
    return {"ok": True}


# ---- componentes ----
@router.get("/componentes")
def listar_componentes(conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_componentes(conn)


@router.post("/componentes", status_code=201)
def criar_componente(dados: ComponenteIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.criar_componente(conn, dados.model_dump(), usuario)


@router.put("/componentes/{idcmp}")
def atualizar_componente(idcmp: int, dados: ComponenteIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.atualizar_componente(conn, idcmp, dados.model_dump())


@router.delete("/componentes/{idcmp}")
def excluir_componente(idcmp: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    svc.excluir_componente(conn, idcmp)
    return {"ok": True}


# ---- produtos (com a lista de componentes) ----
@router.get("/produtos")
def listar_produtos(conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.listar_produtos(conn)


@router.get("/produtos/{idprd}")
def obter_produto(idprd: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.obter_produto(conn, idprd)


@router.post("/produtos", status_code=201)
def criar_produto(dados: ProdutoIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.criar_produto(conn, dados.model_dump(), usuario)


@router.put("/produtos/{idprd}")
def atualizar_produto(idprd: int, dados: ProdutoIn, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.atualizar_produto(conn, idprd, dados.model_dump(), usuario)


@router.delete("/produtos/{idprd}")
def excluir_produto(idprd: int, conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    svc.excluir_produto(conn, idprd)
    return {"ok": True}
