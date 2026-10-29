"""
API HTTP do Controle da Qualidade (FastAPI), usada pelos outros sistemas da fábrica.

Roda como um processo separado das telas:
    python -m uvicorn api:app --host 0.0.0.0 --port 5000
Documentação interativa: http://localhost:5000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException

import banco


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Chave que os outros sistemas enviam no cabeçalho X-API-Key (troque no servidor pela variável de ambiente)
CHAVE_API = os.environ.get("QUALIDADE_API_KEY", "amatech-qualidade-demo")


@asynccontextmanager
async def ciclo_de_vida(_app):
    banco.preparar_banco()
    yield


app = FastAPI(
    title="AMATECH Smart Factory - API do Controle da Qualidade",
    description="Ocorrências de defeito registradas na inspeção (Projeto 4).",
    version="2.0.0",
    lifespan=ciclo_de_vida
)


def exigir_chave(x_api_key: str | None = Header(None, alias="X-API-Key")):
    if x_api_key != CHAVE_API:
        raise HTTPException(status_code=401, detail="Chave de API inválida: informe o cabeçalho X-API-Key.")


# ============================================================
# ROTAS
# ============================================================

@app.get("/api/status")
def status():
    """Sem chave: serve para testar se o sistema está no ar."""
    return {
        "sistema": "Controle da Qualidade",
        "status": "online"
    }


@app.get("/api/ocorrencias", dependencies=[Depends(exigir_chave)])
def obter_ocorrencias(de: str | None = None, ate: str | None = None):
    """Ocorrências visíveis. Filtros opcionais por período: ?de=AAAA-MM-DD&ate=AAAA-MM-DD (inclusive)."""
    ocorrencias = banco.listar_ocorrencias()

    dados = []

    for ocorrencia in ocorrencias:
        if de and ocorrencia["data_ocorrencia"] < de[:10]:
            continue

        if ate and ocorrencia["data_ocorrencia"] > ate[:10]:
            continue

        dados.append({
            "id_ocorrencia": ocorrencia["id_ocorrencia"],
            "data_ocorrencia": ocorrencia["data_ocorrencia"],
            "hora_ocorrencia": ocorrencia["hora_ocorrencia"],
            "produto": ocorrencia["numero_serie_produto"],
            "modelo_produto": ocorrencia["modelo_produto"],
            "tipo_defeito": ocorrencia["nome_tipo_defeito"],
            "estacao": ocorrencia["nome_estacao"],
            "maquina": ocorrencia["nome_maquina"],
            "usuario": ocorrencia["nome_usuario"],
            "classificacao_defeito": ocorrencia["classificacao_defeito"],
            "situacao_produto": ocorrencia["situacao_produto"],
            "observacao_ocorrencia": ocorrencia["observacao_ocorrencia"],
            "acao_realizada": ocorrencia["acao_realizada"],
            "status_ocorrencia": ocorrencia["status_ocorrencia"]
        })

    return dados
