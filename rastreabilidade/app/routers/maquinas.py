from fastapi import APIRouter, Depends, Header, HTTPException

from app import config
from app.db import get_conn
from app.schemas import MaquinaStatusIn
from app.servicos import producao as svc

router = APIRouter(prefix="/api/maquinas", tags=["Integração com máquinas (RF017)"])


@router.post("/status")
def atualizar_status(dados: MaquinaStatusIn, x_api_key: str | None = Header(None), conn=Depends(get_conn)):
    """Rota simples para máquinas/IoT (chave única do equipamento, config.API_KEY_MAQUINAS). O histórico registra a
    origem MAQUINA/IOT. Outros sistemas (equipes) devem usar a API /api/v1, que tem uma chave por sistema."""
    if x_api_key != config.API_KEY_MAQUINAS:
        raise HTTPException(status_code=401, detail="Chave de API inválida.")
    return svc.atualizar_por_maquina(conn, dados.numero_serie, dados.status, dados.maquina)
