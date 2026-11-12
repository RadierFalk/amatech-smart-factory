"""Indicadores do painel, calculados na hora a partir dos módulos (portado de dashboard/servicos/calculadora.py).

Fórmulas (relatório da OA2, seção 2.4), as mesmas do sistema antigo:
  Atendimento da meta  = produção realizada ÷ meta × 100                       (%)
  Produtividade        = produção realizada ÷ (duração dos turnos − paradas)  (un/h)
  Índice de defeitos   = reprovados ÷ produção realizada × 100                 (%)
  Índice de retrabalho = notebooks em reprocesso ÷ produção realizada × 100    (%)
  Tempo de parada      = soma das durações das paradas                         (min)
  Perdas               = soma das quantidades perdidas, por tipo               (un)

De onde vem cada dado (antes eram cópias sincronizadas por HTTP):
  - Produção: passagens da RAS pelas etapas Aprovado (aprovada) e Reprovado (reprovada); realizada = soma das duas.
  - Retrabalho e defeitos por estação: ocorrências visíveis da QLD (retrabalho = situação Em reprocesso).
  - Paradas: chamados da MNT não cancelados, da abertura ao fim (ou até agora, se ativos); preventiva programada
    que ainda não parou a máquina não conta.
  - Metas e perdas: tabelas do próprio Dashboard.
Cada evento entra no dia e no turno da fábrica (Manaus) em que aconteceu; fora dos turnos cadastrados, fica de fora
(como no sistema antigo). O filtro de modelo não se aplica às paradas, que não têm modelo.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import ErroNegocio
from app.modulos.dashboard.constantes import (
    ETAPA_APROVADO,
    ETAPA_REPROVADO,
    Indicador,
    Semaforo,
    Sentido,
)
from app.modulos.dashboard.modelos import Limite, Meta, Perda, Turno
from app.modulos.manutencao.constantes import STATUS_ATIVOS, StatusChamado, StatusEquipamento
from app.modulos.manutencao.indicadores import SEM_LAUDO, downtime_efetivo, resumo
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.constantes import Classificacao, SituacaoProduto, StatusOcorrencia
from app.modulos.qualidade.modelos import Ocorrencia
from app.modulos.rastreabilidade.constantes import (
    ESTOQUE_CRITICO,
    ETAPA_FINAL,
    ORDEM_LATERAL,
    SOLICITACAO_ABERTA,
    StatusSolicitacao,
)
from app.modulos.rastreabilidade.modelos import Baixa, Componente, Etapa, Modelo, Passagem, Producao, Solicitacao

MAX_DIAS = 366


@dataclass
class Filtro:
    de: date
    ate: date
    turno_id: int | None = None
    modelo_id: int | None = None

    def validar(self) -> None:
        if self.ate < self.de:
            raise ErroNegocio("A data final não pode ser anterior à inicial.", status=422)
        if (self.ate - self.de).days >= MAX_DIAS:
            raise ErroNegocio(f"Escolha um período de até {MAX_DIAS} dias.", status=422)


def hoje_na_fabrica() -> date:
    return tempo.agora().astimezone(tempo.FUSO_FABRICA).date()


def _janela(f: Filtro) -> tuple[datetime, datetime]:
    """Instantes UTC do início do 1º dia ao início do dia seguinte ao último (dias da fábrica)."""
    def inicio(dia: date) -> datetime:
        return tempo.utc(datetime.combine(dia, time(), tempo.FUSO_FABRICA))

    return inicio(f.de), inicio(f.ate + timedelta(days=1))


class Turnos:
    """Classifica um instante no dia e no turno da fábrica."""

    def __init__(self, sessao: Session):
        self.lista = list(sessao.scalars(select(Turno).order_by(Turno.hora_inicio)))
        self.por_id = {t.id: t for t in self.lista}

    def classificar(self, instante: datetime) -> tuple[date, Turno | None]:
        local = tempo.utc(instante).astimezone(tempo.FUSO_FABRICA)
        hora = local.time().replace(tzinfo=None)
        turno = next((t for t in self.lista if t.hora_inicio <= hora < t.hora_fim), None)
        return local.date(), turno


def _pct(parte: float, total: float) -> float | None:
    return round(parte / total * 100, 1) if total else None


def semaforo(limites: dict[str, Limite], indicador: Indicador, valor: float | None) -> str | None:
    """Verde, amarelo ou vermelho; None sem valor (ex.: sem meta, RN03) ou sem limites."""
    limite = limites.get(indicador.value)
    if limite is None or valor is None:
        return None
    verde, amarelo = limite.limite_verde, limite.limite_amarelo
    if limite.sentido == Sentido.MAIOR_MELHOR:
        return (Semaforo.VERDE if valor >= verde else Semaforo.AMARELO if valor >= amarelo else Semaforo.VERMELHO).value
    return (Semaforo.VERDE if valor <= verde else Semaforo.AMARELO if valor <= amarelo else Semaforo.VERMELHO).value


# ---------------------------------------------------------------- fontes


def producao(sessao: Session, f: Filtro, turnos: Turnos) -> dict[tuple[date, int, int], dict[str, int]]:
    """(dia, turno, modelo) -> {aprovada, reprovada}, das passagens da RAS por Aprovado e Reprovado."""
    inicio, fim = _janela(f)
    linhas = sessao.execute(
        select(Passagem.registrada_em, Etapa.nome, Producao.modelo_id)
        .join(Etapa, Etapa.id == Passagem.etapa_id)
        .join(Producao, Producao.id == Passagem.producao_id)
        .where(Passagem.registrada_em >= inicio, Passagem.registrada_em < fim,
               Etapa.nome.in_([ETAPA_APROVADO, ETAPA_REPROVADO]))
    ).all()
    resultado: dict[tuple[date, int, int], dict[str, int]] = defaultdict(lambda: {"aprovada": 0, "reprovada": 0})
    for quando, etapa, modelo_id in linhas:
        dia, turno = turnos.classificar(quando)
        if turno is None or (f.turno_id and turno.id != f.turno_id) or (f.modelo_id and modelo_id != f.modelo_id):
            continue
        resultado[(dia, turno.id, modelo_id)]["aprovada" if etapa == ETAPA_APROVADO else "reprovada"] += 1
    return resultado


def metas(sessao: Session, f: Filtro) -> list[Meta]:
    consulta = select(Meta).where(Meta.data >= f.de, Meta.data <= f.ate)
    if f.turno_id:
        consulta = consulta.where(Meta.turno_id == f.turno_id)
    if f.modelo_id:
        consulta = consulta.where(Meta.modelo_id == f.modelo_id)
    return list(sessao.scalars(consulta))


def ocorrencias(sessao: Session, f: Filtro, turnos: Turnos) -> list[Ocorrencia]:
    """Ocorrências visíveis da QLD no período (no turno e no modelo do filtro)."""
    inicio, fim = _janela(f)
    nome_modelo = sessao.get(Modelo, f.modelo_id).nome if f.modelo_id else None
    lista = []
    for o in sessao.scalars(select(Ocorrencia).where(
        Ocorrencia.oculta.is_(False), Ocorrencia.ocorrida_em >= inicio, Ocorrencia.ocorrida_em < fim
    )):
        _, turno = turnos.classificar(o.ocorrida_em)
        if turno is None or (f.turno_id and turno.id != f.turno_id):
            continue
        if nome_modelo and o.produto.modelo.strip().lower() != nome_modelo.strip().lower():
            continue
        lista.append(o)
    return lista


@dataclass
class Parada:
    chamado: Chamado
    turno: Turno
    minutos: int


def chamados(sessao: Session, f: Filtro, turnos: Turnos) -> list[tuple[Chamado, Turno]]:
    """Chamados não cancelados abertos no período (e no turno do filtro)."""
    inicio, fim = _janela(f)
    lista = []
    for c in sessao.scalars(select(Chamado).where(
        Chamado.status_chamado != StatusChamado.CANCELADO.value,
        Chamado.data_hora_abertura >= inicio, Chamado.data_hora_abertura < fim,
    ).order_by(Chamado.data_hora_abertura)):
        _, turno = turnos.classificar(c.data_hora_abertura)
        if turno is None or (f.turno_id and turno.id != f.turno_id):
            continue
        lista.append((c, turno))
    return lista


def paradas(lista_chamados: list[tuple[Chamado, Turno]]) -> list[Parada]:
    """Os chamados que pararam a máquina (preventiva só programada não conta)."""
    agora = tempo.agora()
    lista = []
    for c, turno in lista_chamados:
        minutos = downtime_efetivo(c, agora)
        if minutos > 0:
            lista.append(Parada(c, turno, minutos))
    return lista


def paradas_em_andamento(sessao: Session) -> list[dict[str, Any]]:
    """Máquinas paradas agora (qualquer data): o aviso do painel não depende do filtro."""
    agora = tempo.agora()
    lista = []
    for c in sessao.scalars(select(Chamado).where(Chamado.status_chamado.in_(STATUS_ATIVOS))
                            .order_by(Chamado.data_hora_abertura)):
        if c.equipamento.status_operacional == StatusEquipamento.OPERACIONAL:
            continue  # preventiva programada que ainda não parou a máquina
        lista.append({
            "chamado_id": c.id, "maquina": c.equipamento.codigo_tag, "nome": c.equipamento.nome,
            "setor": c.equipamento.setor, "status_chamado": c.status_chamado, "motivo": c.descricao_falha,
            "desde": tempo.utc(c.data_hora_abertura), "minutos": downtime_efetivo(c, agora),
        })
    return lista


def perdas(sessao: Session, f: Filtro) -> list[Perda]:
    consulta = select(Perda).where(Perda.data >= f.de, Perda.data <= f.ate)
    if f.turno_id:
        consulta = consulta.where(Perda.turno_id == f.turno_id)
    if f.modelo_id:
        consulta = consulta.where(Perda.modelo_id == f.modelo_id)
    return list(sessao.scalars(consulta.order_by(Perda.data.desc(), Perda.id.desc())))


# ---------------------------------------------------------------- painel


def _contagem(valores) -> list[dict[str, Any]]:
    return [{"rotulo": r, "quantidade": n} for r, n in sorted(Counter(valores).items(), key=lambda x: (-x[1], x[0]))]


def painel(sessao: Session, f: Filtro) -> dict[str, Any]:
    f.validar()
    turnos = Turnos(sessao)
    prod = producao(sessao, f, turnos)
    lista_metas = metas(sessao, f)
    ocs = ocorrencias(sessao, f, turnos)
    lista_chamados = chamados(sessao, f, turnos)
    lista_paradas = paradas(lista_chamados)
    lista_perdas = perdas(sessao, f)
    limites = {l.indicador: l for l in sessao.scalars(select(Limite))}

    aprovada = sum(v["aprovada"] for v in prod.values())
    reprovada = sum(v["reprovada"] for v in prod.values())
    realizada = aprovada + reprovada
    meta = sum(m.quantidade for m in lista_metas)
    retrabalho = sum(1 for o in ocs if o.situacao_produto == SituacaoProduto.EM_REPROCESSO)
    minutos_parada = sum(p.minutos for p in lista_paradas)
    minutos_turno = sum(turnos.por_id[t].duracao_min for (_, t) in {(d, t) for d, t, _ in prod})
    minutos_produtivos = max(minutos_turno - minutos_parada, 0)
    atendimento = _pct(realizada, meta)
    defeitos = _pct(reprovada, realizada)
    indice_retrabalho = _pct(retrabalho, realizada)
    por_tipo = _contagem_somada((p.tipo.nome, p.quantidade) for p in lista_perdas)

    # Gráficos
    modelos = {m.id: m.nome for m in sessao.scalars(select(Modelo))}
    realizada_modelo: Counter = Counter()
    realizada_dia: Counter = Counter()
    for (dia, _, modelo_id), v in prod.items():
        realizada_modelo[modelo_id] += v["aprovada"] + v["reprovada"]
        realizada_dia[dia] += v["aprovada"] + v["reprovada"]
    meta_modelo: Counter = Counter()
    meta_dia: Counter = Counter()
    for m in lista_metas:
        meta_modelo[m.modelo_id] += m.quantidade
        meta_dia[m.data] += m.quantidade
    em_andamento = paradas_em_andamento(sessao)
    parada_turno: Counter = Counter()
    for p in lista_paradas:
        parada_turno[p.turno.nome] += p.minutos

    return {
        "periodo": {"de": f.de, "ate": f.ate},
        "producao": {"realizada": realizada, "aprovada": aprovada, "reprovada": reprovada, "meta": meta},
        "atendimento_meta": {"valor": atendimento, "semaforo": semaforo(limites, Indicador.ATENDIMENTO_META, atendimento)},
        "indice_defeitos": {"valor": defeitos, "semaforo": semaforo(limites, Indicador.INDICE_DEFEITOS, defeitos)},
        "indice_retrabalho": {"valor": indice_retrabalho, "retrabalho": retrabalho,
                              "semaforo": semaforo(limites, Indicador.INDICE_RETRABALHO, indice_retrabalho)},
        "produtividade": {
            "valor": round(realizada / (minutos_produtivos / 60), 1) if realizada and minutos_produtivos else None,
            "minutos_turno": minutos_turno, "minutos_produtivos": minutos_produtivos,
        },
        "tempo_parada": {"minutos": minutos_parada, "paradas": len(lista_paradas),
                         "em_andamento": sum(1 for p in lista_paradas if p.chamado.status_chamado in STATUS_ATIVOS)},
        "perdas": {"total": sum(p.quantidade for p in lista_perdas), "por_tipo": por_tipo},
        "graficos": {
            "producao_x_meta": [
                {"modelo": modelos[mid], "realizada": realizada_modelo[mid], "meta": meta_modelo[mid]}
                for mid in sorted(set(realizada_modelo) | set(meta_modelo), key=lambda i: modelos[i])
            ],
            "producao_por_dia": [
                {"data": (f.de + timedelta(days=i)).isoformat(), "realizada": realizada_dia[f.de + timedelta(days=i)],
                 "meta": meta_dia[f.de + timedelta(days=i)]}
                for i in range((f.ate - f.de).days + 1)
            ],
            "defeitos_por_estacao": _contagem(o.estacao.nome for o in ocs),
            "retrabalho_por_estacao": _contagem(o.estacao.nome for o in ocs
                                                if o.situacao_produto == SituacaoProduto.EM_REPROCESSO),
            "parada_por_turno": [{"rotulo": t.nome, "minutos": parada_turno[t.nome]} for t in turnos.lista
                                 if not f.turno_id or t.id == f.turno_id],
        },
        "paradas_em_andamento": em_andamento,
        "lead_time": lead_time(sessao, f, turnos, modelos),
        "em_producao": em_producao(sessao, f),
        "producao_por_turno": _linhas_producao(prod, lista_metas, turnos, modelos),
        "qualidade": _qualidade(ocs, f),
        "manutencao": _manutencao(sessao, f, turnos, lista_chamados, lista_paradas, em_andamento),
        "materiais": materiais(sessao, f),
    }


def _contagem_somada(pares) -> list[dict[str, Any]]:
    total: Counter = Counter()
    for rotulo, quantidade in pares:
        total[rotulo] += quantidade
    return [{"rotulo": r, "quantidade": n} for r, n in sorted(total.items(), key=lambda x: (-x[1], x[0]))]


def _linhas_producao(prod, lista_metas: list[Meta], turnos: Turnos, modelos: dict[int, str]) -> list[dict[str, Any]]:
    """Uma linha por dia, turno e modelo com produção ou meta, da mais recente para a mais antiga."""
    meta_por_chave: Counter = Counter()
    for m in lista_metas:
        meta_por_chave[(m.data, m.turno_id, m.modelo_id)] += m.quantidade
    linhas = []
    for chave in sorted(set(prod) | set(meta_por_chave), key=lambda c: (c[0], turnos.por_id[c[1]].hora_inicio, modelos[c[2]]),
                        reverse=True):
        dia, turno_id, modelo_id = chave
        v = prod.get(chave, {"aprovada": 0, "reprovada": 0})
        realizada = v["aprovada"] + v["reprovada"]
        meta = meta_por_chave.get(chave, 0)
        linhas.append({
            "data": dia, "turno_id": turno_id, "turno": turnos.por_id[turno_id].nome, "modelo": modelos[modelo_id],
            "realizada": realizada, "aprovada": v["aprovada"], "reprovada": v["reprovada"], "meta": meta,
            "atendimento_meta": _pct(realizada, meta),
        })
    return linhas


def historico_producao(sessao: Session, f: Filtro) -> list[dict[str, Any]]:
    """Uma linha por dia, turno e modelo, com o que foi produzido e a meta (T08 do sistema antigo)."""
    f.validar()
    turnos = Turnos(sessao)
    modelos = {m.id: m.nome for m in sessao.scalars(select(Modelo))}
    return _linhas_producao(producao(sessao, f, turnos), metas(sessao, f), turnos, modelos)


# ---------------------------------------------------------------- abas por setor


def _dia(instante: datetime) -> date:
    return tempo.utc(instante).astimezone(tempo.FUSO_FABRICA).date()


def _dias(f: Filtro) -> list[date]:
    return [f.de + timedelta(days=i) for i in range((f.ate - f.de).days + 1)]


def lead_time(sessao: Session, f: Filtro, turnos: Turnos, modelos: dict[int, str]) -> dict[str, Any]:
    """Do início da produção até a chegada na Expedição, para os notebooks expedidos no período."""
    inicio, fim = _janela(f)
    chegada: dict[int, tuple[datetime, datetime, int]] = {}
    for producao_id, quando, iniciada, modelo_id in sessao.execute(
        select(Passagem.producao_id, Passagem.registrada_em, Producao.iniciada_em, Producao.modelo_id)
        .join(Etapa, Etapa.id == Passagem.etapa_id)
        .join(Producao, Producao.id == Passagem.producao_id)
        .where(Etapa.nome == ETAPA_FINAL, Passagem.registrada_em >= inicio, Passagem.registrada_em < fim)
    ):
        if producao_id not in chegada or quando < chegada[producao_id][0]:
            chegada[producao_id] = (quando, iniciada, modelo_id)
    por_modelo: dict[int, list[int]] = defaultdict(list)
    for quando, iniciada, modelo_id in chegada.values():
        _, turno = turnos.classificar(quando)
        if (f.turno_id and (turno is None or turno.id != f.turno_id)) or (f.modelo_id and modelo_id != f.modelo_id):
            continue
        por_modelo[modelo_id].append(tempo.minutos_entre(iniciada, quando, minimo=0))
    todos = [m for lista in por_modelo.values() for m in lista]
    return {
        "minutos": round(sum(todos) / len(todos)) if todos else None,
        "expedidos": len(todos),
        "por_modelo": [{"modelo": modelos[mid], "minutos": round(sum(v) / len(v)), "expedidos": len(v)}
                       for mid, v in sorted(por_modelo.items(), key=lambda x: modelos[x[0]])],
    }


def em_producao(sessao: Session, f: Filtro) -> dict[str, Any]:
    """Notebooks ainda não expedidos, por etapa atual (agora: não depende do período)."""
    consulta = select(Producao.etapa_id, func.count()).group_by(Producao.etapa_id)
    if f.modelo_id:
        consulta = consulta.where(Producao.modelo_id == f.modelo_id)
    contagem = dict(sessao.execute(consulta).all())
    etapas = [e for e in sessao.scalars(select(Etapa).order_by(Etapa.ordem)) if e.nome != ETAPA_FINAL]
    por_etapa = [{"rotulo": e.nome, "quantidade": contagem.get(e.id, 0), "lateral": e.ordem >= ORDEM_LATERAL} for e in etapas]
    return {"total": sum(e["quantidade"] for e in por_etapa), "por_etapa": por_etapa}


def _qualidade(ocs: list[Ocorrencia], f: Filtro) -> dict[str, Any]:
    status = Counter(o.status for o in ocs)
    criticas = sorted((o for o in ocs if o.classificacao == Classificacao.CRITICO), key=lambda o: o.ocorrida_em, reverse=True)
    por_dia = Counter(_dia(o.ocorrida_em) for o in ocs)
    return {
        "ocorrencias": len(ocs),
        "abertas": status[StatusOcorrencia.ABERTA.value],
        "em_analise": status[StatusOcorrencia.EM_ANALISE.value],
        "resolvidas": status[StatusOcorrencia.RESOLVIDA.value],
        "criticas": len(criticas),
        "criticas_pendentes": sum(1 for o in criticas if o.status != StatusOcorrencia.RESOLVIDA),
        "por_tipo": _contagem(o.tipo_defeito.nome for o in ocs),
        "por_dia": [{"data": d.isoformat(), "quantidade": por_dia[d]} for d in _dias(f)],
        "criticas_recentes": [
            {"id": o.id, "ocorrida_em": tempo.utc(o.ocorrida_em), "defeito": o.tipo_defeito.nome,
             "numero_serie": o.produto.numero_serie, "modelo": o.produto.modelo, "estacao": o.estacao.nome, "status": o.status}
            for o in criticas[:5]
        ],
    }


def _manutencao(sessao: Session, f: Filtro, turnos: Turnos, lista_chamados: list[tuple[Chamado, Turno]],
                lista_paradas: list[Parada], em_andamento: list[dict[str, Any]]) -> dict[str, Any]:
    """MTTR, MTBF, MTTA e disponibilidade com as fórmulas da Manutenção, sobre o tempo de turno do período
    (máquinas ativas × dias × duração dos turnos)."""
    maquinas = list(sessao.scalars(select(Equipamento).where(Equipamento.ativo.is_(True))))
    minutos_turno = sum(t.duracao_min for t in turnos.lista if not f.turno_id or t.id == f.turno_id)
    lista = [c for c, _ in lista_chamados]
    r = resumo(lista, maquinas, tempo.agora(), len(maquinas) * len(_dias(f)) * minutos_turno)
    paradas_agora = {p["maquina"] for p in em_andamento}
    setor: dict[str, dict[str, int]] = defaultdict(lambda: {"minutos": 0, "paradas": 0})
    maquina: dict[int, dict[str, Any]] = {}
    por_dia: Counter = Counter()
    for p in lista_paradas:
        e = p.chamado.equipamento
        setor[e.setor]["minutos"] += p.minutos
        setor[e.setor]["paradas"] += 1
        m = maquina.setdefault(e.id, {"maquina": e.codigo_tag, "nome": e.nome, "setor": e.setor, "minutos": 0, "paradas": 0,
                                      "parada_agora": e.codigo_tag in paradas_agora})
        m["minutos"] += p.minutos
        m["paradas"] += 1
        por_dia[_dia(p.chamado.data_hora_abertura)] += p.minutos
    return {
        "disponibilidade": r["disponibilidade_pct"] if maquinas and minutos_turno else None,
        "mttr_minutos": r["mttr_minutos"] if r["chamados_concluidos"] else None,
        "mtta_minutos": r["mtta_minutos"] if any(c.data_hora_inicio_atendimento for c in lista) else None,
        "mtbf_minutos": r["mtbf_minutos"] if r["corretivas"] else None,
        "chamados": len(lista),
        "chamados_ativos": r["chamados_abertos"] + r["chamados_em_andamento"],
        "por_setor": sorted(({"setor": s, **v} for s, v in setor.items()), key=lambda x: (-x["minutos"], x["setor"])),
        "por_maquina": sorted(maquina.values(), key=lambda x: (-x["minutos"], x["maquina"]))[:10],
        "por_dia": [{"data": d.isoformat(), "minutos": por_dia[d]} for d in _dias(f)],
        "por_causa": _contagem((c.causa_raiz or "").strip() or SEM_LAUDO for c in lista),
    }


def materiais(sessao: Session, f: Filtro) -> dict[str, Any]:
    """Estoque e pedidos em aberto agora; baixas no período. O modelo filtra pedidos e baixas (o estoque é um só)."""
    inicio, fim = _janela(f)
    consulta = select(Solicitacao).where(Solicitacao.status.in_([s.value for s in SOLICITACAO_ABERTA]))
    if f.modelo_id:
        consulta = consulta.join(Producao, Producao.id == Solicitacao.producao_id).where(Producao.modelo_id == f.modelo_id)
    abertas = list(sessao.scalars(consulta))
    falta: Counter = Counter()
    producoes: dict[int, set[int]] = defaultdict(set)
    for s in abertas:
        falta[s.componente_id] += max(s.quantidade - s.quantidade_baixada, 0)
        producoes[s.componente_id].add(s.producao_id)

    componentes = {c.id: c for c in sessao.scalars(select(Componente).where(Componente.ativo.is_(True)))}
    criticos = [c for c in componentes.values() if c.estoque <= ESTOQUE_CRITICO or c.estoque < falta[c.id]]

    baixas = select(func.count(Baixa.id), func.coalesce(func.sum(Baixa.quantidade), 0)).where(
        Baixa.registrada_em >= inicio, Baixa.registrada_em < fim)
    if f.modelo_id:
        baixas = (baixas.join(Solicitacao, Solicitacao.id == Baixa.solicitacao_id)
                  .join(Producao, Producao.id == Solicitacao.producao_id).where(Producao.modelo_id == f.modelo_id))
    qtd_baixas, unidades = sessao.execute(baixas).one()

    def componente(cid: int, ids: set[int]) -> dict[str, Any]:
        c = componentes.get(cid)
        return {"sku": c.sku if c else "?", "nome": c.nome if c else "", "producoes": len(ids), "quantidade": falta[cid],
                "insuficiente": bool(c) and c.estoque < falta[cid]}

    return {
        "pendentes": sum(1 for s in abertas if s.status == StatusSolicitacao.PENDENTE),
        "parciais": sum(1 for s in abertas if s.status == StatusSolicitacao.PARCIAL),
        "producoes_com_pendencia": len({s.producao_id for s in abertas}),
        "baixas": qtd_baixas,
        "unidades_baixadas": int(unidades),
        "limite_critico": ESTOQUE_CRITICO,
        "estoque_critico": [
            {"sku": c.sku, "nome": c.nome, "estoque": c.estoque, "pedido": falta[c.id], "insuficiente": c.estoque < falta[c.id]}
            for c in sorted(criticos, key=lambda c: (c.estoque >= falta[c.id], c.estoque, c.sku))
        ],
        "pendencias_por_componente": sorted((componente(cid, ids) for cid, ids in producoes.items()),
                                            key=lambda x: (-x["producoes"], x["sku"])),
    }
