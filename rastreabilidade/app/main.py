"""Ponto de entrada: python -m uvicorn app.main:app --reload"""
import mimetypes
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config, db
from app.erros import ErroNegocio
from app.routers import auth, cadastros, integracao, maquinas, materiais, producao, relatorios

# No Windows o tipo de arquivo vem do registro do sistema e às vezes ".js" é "text/plain"; o navegador então
# recusa os módulos JavaScript e a tela fica em branco. Fixamos os tipos corretos.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")


@asynccontextmanager
async def lifespan(app):
    db.inicializar()   # cria o banco com dados de demonstração na primeira execução
    yield


app = FastAPI(
    title="AMATECH Electronics – Rastreabilidade de Produtos",
    description="API do MVP: produtos, componentes, produção com histórico, fluxo de materiais e relatórios.",
    version="1.0.0",
    lifespan=lifespan,
)

for modulo in (auth, cadastros, producao, materiais, relatorios, maquinas, integracao):
    app.include_router(modulo.router)
app.include_router(integracao.router_admin)

# Só habilita CORS se houver origens configuradas (variável AMATECH_CORS): outros sistemas com tela própria.
if config.CORS_ORIGENS:
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGENS, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ErroNegocio)
async def tratar_erro_negocio(request, exc):
    return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})


@app.exception_handler(RequestValidationError)
async def tratar_validacao(request, exc):
    partes = []
    for e in exc.errors():
        campo = ".".join(str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path"))
        partes.append(f"{campo}: {e.get('msg', 'valor inválido')}" if campo else e.get("msg", "valor inválido"))
    return JSONResponse(status_code=422, content={"detail": "Dados inválidos — " + "; ".join(partes)})


@app.exception_handler(sqlite3.IntegrityError)
async def tratar_integridade(request, exc):
    texto = str(exc)
    if texto.startswith("UNIQUE constraint failed:"):
        campo = texto.split(":", 1)[1].strip().split(".")[-1]
        mensagem = f"Já existe um registro com o mesmo valor de '{campo}'."
    elif "FOREIGN KEY" in texto:
        mensagem = "Operação não permitida: o registro está vinculado a outros dados."
    else:
        mensagem = "Os dados informados violam uma regra do banco: " + texto
    return JSONResponse(status_code=409, content={"detail": mensagem})


# Frontend (HTML/CSS/JS) servido pela própria API; as rotas /api têm prioridade por serem registradas antes.
app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="frontend")
