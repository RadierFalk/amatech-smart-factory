"""API de integração com outros sistemas.
 - /api/v1/...        usada pelos outros sistemas, autenticada por chave (cabeçalho X-API-Key)
 - /api/integracoes   usada pela tela de administração (somente Administrador) para criar/revogar chaves
"""
from fastapi import APIRouter, Depends, Header

from app import config
from app.db import get_conn
from app.schemas import ClienteAtivoIn, ClienteIntegracaoIn, NaoConformidadeExternaIn, StatusExternoIn
from app.seguranca import exigir_admin
from app.servicos import integracao as svc

router = APIRouter(prefix="/api/v1", tags=["Integração v1 (outros sistemas)"])
router_admin = APIRouter(prefix="/api/integracoes", tags=["Administração das integrações"])


def cliente_integracao(x_api_key: str | None = Header(None, alias="X-API-Key"), conn=Depends(get_conn)):
    return svc.autenticar_cliente(conn, x_api_key)


@router.get("/saude")
def saude():
    """Sem autenticação: serve para os outros sistemas testarem se este está no ar."""
    return {"status": "ok", "sistema": "AMATECH Rastreabilidade de Produtos", "versao_api": "v1", "versao": config.VERSAO}


@router.get("/status-producao")
def status_producao(conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.status_v1(conn)


@router.get("/produtos")
def produtos(conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.produtos_v1(conn)


@router.get("/componentes")
def componentes(conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.componentes_v1(conn)


@router.get("/producoes")
def producoes(atualizado_apos: str | None = None, status: str | None = None, limite: int = 200, offset: int = 0,
              conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.producoes_v1(conn, atualizado_apos, status, limite, offset)


@router.get("/producoes/{numero_serie}")
def producao(numero_serie: str, conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.producao_v1(conn, numero_serie)


@router.post("/producoes/{numero_serie}/status")
def atualizar_status(numero_serie: str, dados: StatusExternoIn, conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    r = svc.atualizar_status_externo(conn, cliente, numero_serie, dados.status, dados.maquina, dados.descricao_falha,
                                     dados.motivo_reprovacao, dados.id_externo)
    return {"alterado": r["alterado"], "status": r["producao"]["status_nome"]}


@router.get("/passagens")
def passagens(de: str | None = None, ate: str | None = None, status: str | None = None, limite: int = 5000,
              conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    """Histórico de etapas de todas as produções no período (de/ate em ISO 8601, UTC)."""
    return svc.passagens_v1(conn, de, ate, status, limite)


@router.post("/nao-conformidades", status_code=201)
def registrar_nao_conformidade(dados: NaoConformidadeExternaIn, conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.registrar_nc_externa(conn, cliente, dados.numero_serie, dados.descricao_falha,
                                    dados.motivo_reprovacao, dados.id_externo)


@router.get("/solicitacoes")
def solicitacoes(status: str | None = None, conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    return svc.solicitacoes_v1(conn, status)


@router.get("/eventos")
def eventos(apos_id: int = 0, limite: int = 100, tipo: str | None = None,
            conn=Depends(get_conn), cliente=Depends(cliente_integracao)):
    """Fila de eventos: guarde o `ultimo_id` recebido e peça só o que veio depois (apos_id)."""
    return svc.listar_eventos(conn, apos_id, limite, tipo)


# ---------------- administração das chaves (tela "Integrações")
@router_admin.get("")
def listar(conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.listar_clientes(conn)


@router_admin.post("", status_code=201)
def criar(dados: ClienteIntegracaoIn, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.criar_cliente(conn, dados.nome, usuario)


@router_admin.post("/{cliente_id}/nova-chave")
def nova_chave(cliente_id: int, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.nova_chave_cliente(conn, cliente_id)


@router_admin.put("/{cliente_id}")
def alterar(cliente_id: int, dados: ClienteAtivoIn, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    return svc.alterar_cliente(conn, cliente_id, dados.ativo)


@router_admin.delete("/{cliente_id}")
def excluir(cliente_id: int, conn=Depends(get_conn), usuario=Depends(exigir_admin)):
    svc.excluir_cliente(conn, cliente_id)
    return {"ok": True}
