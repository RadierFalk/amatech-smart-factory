"""
Servidor de API REST JSON em FastAPI para Integração no Ecossistema Mini-ERP AMATECH.
Expõe dados para Controle de Qualidade (Anderson), Rastreabilidade (Waddington)
e Central de Visualização (Letícia/Radier).
Porta padrão: 5002
"""
from contextlib import asynccontextmanager
import socket
import threading
from typing import Any, AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_HOST, API_PORT
from database import ensure_database_initialized
from services.chamado_service import listar_historico_chamados
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_iso(ts: str | None) -> str | None:
    if not ts:
        return None
    return str(ts).replace(" ", "T")


@app.get("/api/status")
def obter_status() -> dict[str, Any]:
    """Endpoint 1: Healthcheck e Status do Sistema."""
    return {
        "sistema": "Controle da Manutencao",
        "status": "online",
        "versao": "1.0.0",
        "responsavel": "Equipe Orlando",
    }


@app.get("/api/equipamentos")
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


@app.get("/api/manutencao/chamados")
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
            }
        )
    return resultado


@app.get("/api/manutencao/indicadores")
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


def _porta_em_uso(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", porta)) == 0


_api_thread_lock = threading.Lock()
_api_started = False


def iniciar_api_em_background(porta: int = API_PORT) -> bool:
    """
    Inicia o servidor FastAPI/Uvicorn em uma thread daemon paralela ao Streamlit,
    permitindo que `streamlit run app.py` também suba a API REST na porta 5002.
    """
    global _api_started
    with _api_thread_lock:
        if _api_started or _porta_em_uso(porta):
            _api_started = True
            return False

        def _run() -> None:
            try:
                config = uvicorn.Config(
                    app,
                    host=API_HOST,
                    port=porta,
                    log_level="warning",
                )
                server = uvicorn.Server(config)
                server.run()
            except Exception:
                pass

        thread = threading.Thread(target=_run, daemon=True, name="amatech-manutencao-api")
        thread.start()
        _api_started = True
        return True


if __name__ == "__main__":
    ensure_database_initialized()
    uvicorn.run(app, host=API_HOST, port=API_PORT)
