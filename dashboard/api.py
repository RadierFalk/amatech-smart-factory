"""API do Dashboard Industrial (FastAPI): os indicadores do painel para outros sistemas da rede da fábrica.

Faz parte da camada 1 (apresentação), como as telas: não calcula nada, só chama as classes de servicos/.
Todas as rotas de dados exigem o cabeçalho X-API-Key (variável DASHBOARD_API_KEY).

Executar:  python -m uvicorn api:app --host 0.0.0.0 --port 5003      Documentação: http://localhost:5003/docs
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException

import config
from acesso_dados import Repositorio
from servicos.alertas import AvaliadorAlertas
from servicos.cadastros import ServicoCadastros
from servicos.calculadora import CalculadoraIndicadores
from servicos.erros import ErroValidacao
from servicos.filtro import Filtro
from servicos.formatos import ler_data, texto_data

@asynccontextmanager
async def ciclo_de_vida(_app):
    Repositorio()   # cria o banco na primeira execução, antes de a tela subir (evita as duas criarem juntas)
    yield


app = FastAPI(title="AMATECH Smart Factory - API do Dashboard Industrial",
              description="Indicadores consolidados da linha de produção (Projeto 3). Datas em AAAA-MM-DD ou "
                          "DD/MM/AAAA; sem datas, o dia de hoje.",
              version="1.0.0", lifespan=ciclo_de_vida)


def exigir_chave(x_api_key: str | None = Header(None, alias="X-API-Key")):
    if x_api_key != config.DASHBOARD_API_KEY:
        raise HTTPException(status_code=401, detail="Chave de API inválida: informe o cabeçalho X-API-Key.")


def filtro(de: str | None = None, ate: str | None = None, turno: str | None = None, produto: str | None = None):
    """Monta o Filtro do período (RN05). Turno e produto pelo nome (aceita os sinônimos dos outros setores)."""
    hoje = config.agora().date()
    data_inicial, data_final = (ler_data(de) if de else hoje), (ler_data(ate) if ate else hoje)
    if data_inicial is None or data_final is None:
        raise HTTPException(status_code=422, detail="Data inválida: use AAAA-MM-DD ou DD/MM/AAAA.")
    cadastros = ServicoCadastros()
    ids = {}
    for cadastro, valor in (("turno", turno), ("produto", produto)):
        if valor:
            ids[cadastro] = cadastros.buscar_id(cadastro, valor)
            if ids[cadastro] is None:
                raise HTTPException(status_code=422, detail=f"{cadastro.capitalize()} \"{valor}\" não cadastrado.")
    try:
        return Filtro(data_inicial, data_final, ids.get("turno"), ids.get("produto")).validar()
    except ErroValidacao as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


def _arredondar(valor):
    return round(valor, 1) if valor is not None else None


@app.get("/api/status")
def status():
    """Sem chave: serve para testar se o sistema está no ar."""
    return {"sistema": "Dashboard Industrial", "status": "online"}


@app.get("/api/indicadores", dependencies=[Depends(exigir_chave)])
def indicadores(f: Filtro = Depends(filtro)):
    """Os seis indicadores do painel (T02) no período, com a cor do semáforo dos que têm limites (RN08)."""
    r = CalculadoraIndicadores().calcular(f)
    alertas = AvaliadorAlertas()

    def com_semaforo(indicador, valor):
        return {"valor": _arredondar(valor), "unidade": "%", "semaforo": alertas.classificar(indicador, valor)}

    return {
        "periodo": {"de": texto_data(f.data_inicial), "ate": texto_data(f.data_final)},
        "producao": {"realizada": r.realizada, "aprovada": r.aprovada, "reprovada": r.reprovada, "meta": r.meta},
        "atendimento_meta": com_semaforo("atendimento_meta", r.atendimento_meta),
        "indice_defeitos": com_semaforo("indice_defeitos", r.indice_defeitos),
        "indice_retrabalho": com_semaforo("indice_retrabalho", r.indice_retrabalho) | {"quantidade": r.retrabalho},
        "produtividade": {"valor": _arredondar(r.produtividade), "unidade": "un/h",
                          "minutos_produtivos": _arredondar(r.minutos_produtivos)},
        "tempo_parada": {"minutos": _arredondar(r.tempo_parada.minutos), "encerradas": r.tempo_parada.encerradas,
                         "em_andamento": r.tempo_parada.em_andamento},
        "perdas": {"total": r.perdas, "por_tipo": r.perdas_por_tipo},
    }


@app.get("/api/graficos", dependencies=[Depends(exigir_chave)])
def graficos(f: Filtro = Depends(filtro)):
    """Dados dos quatro gráficos do painel (RF11)."""
    calculadora = CalculadoraIndicadores()
    return {
        "periodo": {"de": texto_data(f.data_inicial), "ate": texto_data(f.data_final)},
        "producao_x_meta": calculadora.producao_x_meta(f),
        "defeitos_por_estacao": calculadora.defeitos_por_estacao(f),
        "parada_por_turno": calculadora.parada_por_turno(f),
        "retrabalho_por_estacao": calculadora.retrabalho_por_estacao(f),
    }


@app.get("/api/paradas-em-andamento", dependencies=[Depends(exigir_chave)])
def paradas_em_andamento():
    """Máquinas paradas agora, de qualquer data (o mesmo aviso do topo do painel)."""
    return CalculadoraIndicadores().paradas_em_andamento()
