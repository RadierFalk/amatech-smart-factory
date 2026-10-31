"""
Servidor de API REST JSON em FastAPI para Integração no Ecossistema Mini-ERP AMATECH.
Expõe dados para Controle de Qualidade (Anderson), Rastreabilidade (Waddington)
e Central de Visualização (Letícia/Radier).
Porta padrão: 5002

Roda como um processo separado das telas (numa empresa, a API não pode depender de alguém abrir a tela):
    python -m uvicorn api:app --host 0.0.0.0 --port 5002      (ou: python api.py)
"""
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import API_CORS_ORIGENS, API_HOST, API_KEY_INTEGRACAO, API_PORT, EXIGIR_CHAVE
from database import ensure_database_initialized
from services.chamado_service import abrir_chamado_externo, listar_historico_chamados
from services.equipamento_service import listar_equipamentos
from services.relatorio_service import obter_indicadores_consolidados


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_database_initialized()
    yield


app = FastAPI(
    title="AMATECH Smart Factory - API de Controle da Manutenção",
    description="Contrato REST JSON do Módulo de Manutenção (Projeto 5 - Equipe Orlando)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS só para as origens configuradas (MANUTENCAO_CORS): telas de outros sistemas que chamem a API pelo navegador.
if API_CORS_ORIGENS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=API_CORS_ORIGENS,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def exigir_chave(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """Autenticação por perímetro de rede (Abordagem 1):
    - Chamadas internas sem cabeçalho são permitidas.
    - Se uma chave for enviada, valida se confere com a configurada."""
    if not x_api_key:
        if EXIGIR_CHAVE:
            raise HTTPException(status_code=401, detail="Chave de API inválida: informe o cabeçalho X-API-Key.")
        return
    if API_KEY_INTEGRACAO and x_api_key != API_KEY_INTEGRACAO:
        raise HTTPException(status_code=401, detail="Chave de API inválida: informe o cabeçalho X-API-Key.")


def _format_iso(ts: str | None) -> str | None:
    """O banco grava em UTC (RN06); o "Z" deixa isso explícito para os outros sistemas."""
    if not ts:
        return None
    return str(ts).replace(" ", "T") + "Z"


class ChamadoExternoIn(BaseModel):
    """Chamado aberto por outro sistema do ecossistema (ex.: Controle da Qualidade)."""
    equipamento_tag: str = Field(min_length=1)
    descricao_falha: str = Field(min_length=5)
    prioridade: str = "MEDIA"
    tipo_manutencao: str = "CORRETIVA"
    origem_sistema: str = Field(min_length=1)
    id_externo: str | None = None


@app.get("/api/status")
def obter_status() -> dict[str, Any]:
    """Endpoint 1: Healthcheck e Status do Sistema (sem chave)."""
    return {
        "sistema": "Controle da Manutencao",
        "status": "online",
        "versao": "1.0.0",
        "responsavel": "Equipe Orlando",
    }


@app.get("/api/equipamentos", dependencies=[Depends(exigir_chave)])
def obter_equipamentos() -> list[dict[str, Any]]:
    """Endpoint 2: Lista de máquinas com status operacional em tempo real."""
    equipamentos = listar_equipamentos(apenas_ativos=True)
    resultado = []
    # Ordena por ID para consistência com o contrato da documentação
    for eq in sorted(equipamentos, key=lambda x: x["id"]):
        resultado.append(
            {
                "id": eq["id"],
                "codigo_tag": eq["codigo_tag"],
                "nome": eq["nome"],
                "setor": eq["setor"],
                "posto_trabalho": eq["posto_trabalho"],
                "status_operacional": eq["status_operacional"],
            }
        )
    return resultado


@app.get("/api/manutencao/chamados", dependencies=[Depends(exigir_chave)])
def obter_chamados() -> list[dict[str, Any]]:
    """Endpoint 3: Histórico e chamados ativos com timestamps, downtime e peças substituídas."""
    chamados = listar_historico_chamados()
    resultado = []
    for c in chamados:
        resultado.append(
            {
                "id_chamado": c["id"],
                "equipamento_tag": c["equipamento_tag"],
                "equipamento_nome": c["equipamento_nome"],
                "setor": c["setor"],
                "operador": c["operador_nome"],
                "tecnico": c["tecnico_nome"],
                "prioridade": c["prioridade"],
                "tipo_manutencao": c["tipo_manutencao"],
                "status_chamado": c["status_chamado"],
                "descricao_falha": c["descricao_falha"],
                "diagnostico_tecnico": c["diagnostico_tecnico"],
                "causa_raiz": c["causa_raiz"],
                "data_hora_abertura": _format_iso(c["data_hora_abertura"]),
                "data_hora_inicio": _format_iso(c["data_hora_inicio_atendimento"]),
                "data_hora_fim": _format_iso(c["data_hora_fim_atendimento"]),
                "downtime_minutos": c["downtime_minutos"],
                "pecas_trocadas": c["pecas_trocadas"],
                "origem_sistema": c["origem_sistema"],
                "id_externo": c["id_externo"],
            }
        )
    return resultado


@app.post("/api/manutencao/chamados", status_code=201, dependencies=[Depends(exigir_chave)])
def criar_chamado_externo(dados: ChamadoExternoIn, response: Response) -> dict[str, Any]:
    """
    Endpoint 5: outro sistema abre um chamado (cabeçalho X-API-Key = MANUTENCAO_API_KEY).
    Reenvio com o mesmo origem_sistema + id_externo devolve o chamado existente ("criado": false).
    Máquina já parada ou em manutenção (RN02) responde 409.
    """
    try:
        chamado_id, criado = abrir_chamado_externo(
            dados.equipamento_tag,
            dados.descricao_falha,
            prioridade=dados.prioridade,
            tipo_manutencao=dados.tipo_manutencao,
            origem_sistema=dados.origem_sistema.strip().lower(),
            id_externo=dados.id_externo,
        )
    except LookupError as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except ValueError as erro:
        codigo = 409 if "RN02" in str(erro) else 422
        raise HTTPException(status_code=codigo, detail=str(erro)) from erro
    if not criado:
        response.status_code = 200
    return {"id_chamado": chamado_id, "criado": criado}


@app.get("/api/manutencao/indicadores", dependencies=[Depends(exigir_chave)])
def obter_indicadores() -> dict[str, Any]:
    """Endpoint 4: Métricas consolidadas (Downtime total, MTTR, MTTA, contadores e disponibilidade)."""
    ind = obter_indicadores_consolidados()
    return {
        "sistema": "Controle da Manutencao",
        "downtime_total_minutos": ind["downtime_total_minutos"],
        "mttr_minutos": ind["mttr_minutos"],
        "mtta_resposta_minutos": ind["mtta_resposta_minutos"],
        "total_chamados": ind["total_chamados"],
        "chamados_abertos": ind["chamados_abertos"],
        "chamados_em_andamento": ind["chamados_em_andamento"],
        "chamados_concluidos": ind["chamados_concluidos"],
        "maquinas_operacionais": ind["maquinas_operacionais"],
        "maquinas_em_manutencao": ind["maquinas_em_manutencao"],
        "maquinas_paradas": ind["maquinas_paradas"],
        "disponibilidade_geral_pct": ind["disponibilidade_geral_pct"],
    }


if __name__ == "__main__":
    ensure_database_initialized()
    uvicorn.run(app, host=API_HOST, port=API_PORT)
