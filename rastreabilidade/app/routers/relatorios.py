from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.db import get_conn
from app.seguranca import usuario_atual
from app.servicos import relatorios as svc

router = APIRouter(prefix="/api", tags=["Dashboard e relatórios"])


@router.get("/dashboard")
def dashboard(conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.dashboard(conn)


@router.get("/relatorios/{tipo}")
def relatorio(tipo: str, data_ini: str | None = None, data_fim: str | None = None,
              conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    return svc.gerar_relatorio(conn, tipo, data_ini, data_fim)


@router.get("/relatorios/{tipo}/csv")
def relatorio_csv(tipo: str, data_ini: str | None = None, data_fim: str | None = None,
                  conn=Depends(get_conn), usuario=Depends(usuario_atual)):
    rel = svc.gerar_relatorio(conn, tipo, data_ini, data_fim)
    return Response(content=svc.relatorio_csv(rel), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="relatorio_{tipo}.csv"'})
