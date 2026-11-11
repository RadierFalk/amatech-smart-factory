"""API única do ERP AMATECH (substitui as 4 APIs por setor e o portal Streamlit).

Executar (a partir de backend/):
    uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import obter_configuracao
from app.core.db import engine
from app.core.erros import ErroNegocio
from app.modulos.manutencao.rotas import rotas as rotas_manutencao
from app.modulos.usuarios.rotas import rotas_auth, rotas_usuarios

cfg = obter_configuracao()
cfg.validar_producao()

app = FastAPI(title="ERP AMATECH", version="2.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErroNegocio)
def tratar_erro_negocio(_: Request, exc: ErroNegocio) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})


@app.get("/api/saude", tags=["Sistema"])
def saude():
    """Verifica a API e a conexão com o PostgreSQL."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        banco = "ok"
    except Exception as exc:  # noqa: BLE001 - a rota de saúde precisa responder mesmo com o banco fora
        banco = f"indisponível ({type(exc).__name__})"
    return {"api": "ok", "banco": banco}


app.include_router(rotas_auth)
app.include_router(rotas_usuarios)
app.include_router(rotas_manutencao)
