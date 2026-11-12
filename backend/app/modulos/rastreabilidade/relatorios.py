"""Painel e relatórios da Rastreabilidade (portado de rastreabilidade/app/servicos/relatorios.py).

Os relatórios devolvem colunas + linhas (a tela mostra a tabela e exporta o CSV). Datas vão em UTC (ISO);
a tela formata no horário da fábrica. Filtros por dia usam o dia da fábrica (Manaus).
"""
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import NaoEncontrado
from app.modulos.rastreabilidade.cadastros import listar_componentes, listar_etapas, pendente_por_componente
from app.modulos.rastreabilidade.constantes import ESTOQUE_CRITICO, ETAPA_APROVADO, ETAPA_FINAL, ETAPA_REPROVADO, SOLICITACAO_ABERTA
from app.modulos.rastreabilidade.modelos import NaoConformidade, Producao, Solicitacao


def _dia_fabrica(valor: datetime) -> date:
    return tempo.utc(valor).astimezone(tempo.FUSO_FABRICA).date()


def _inicio(dia: date) -> datetime:
    return tempo.utc(datetime.combine(dia, time(), tempo.FUSO_FABRICA))


def _periodo(consulta, coluna, de: date | None, ate: date | None):
    if de:
        consulta = consulta.where(coluna >= _inicio(de))
    if ate:
        consulta = consulta.where(coluna < _inicio(ate + timedelta(days=1)))
    return consulta


def painel(sessao: Session) -> dict[str, Any]:
    producoes = list(sessao.scalars(select(Producao)))
    hoje = tempo.agora().astimezone(tempo.FUSO_FABRICA).date()
    por_etapa = Counter(p.etapa_id for p in producoes)
    por_dia = Counter(_dia_fabrica(p.iniciada_em) for p in producoes)
    componentes = listar_componentes(sessao)
    criticos = [c for c in componentes if c.estoque <= ESTOQUE_CRITICO]

    def na_etapa(nome: str) -> int:
        return sum(1 for p in producoes if p.etapa.nome == nome)

    return {
        "kpis": {
            "iniciadas_hoje": por_dia.get(hoje, 0),
            "em_producao": sum(1 for p in producoes if p.etapa.nome != ETAPA_FINAL),
            "aprovados": na_etapa(ETAPA_APROVADO),
            "reprovados": na_etapa(ETAPA_REPROVADO),
            "solicitacoes_pendentes": len(list(sessao.scalars(
                select(Solicitacao.id).where(Solicitacao.status.in_(SOLICITACAO_ABERTA))))),
            "estoque_critico": len(criticos),
        },
        "por_etapa": [{"etapa": e.nome, "ordem": e.ordem, "quantidade": por_etapa.get(e.id, 0)} for e in listar_etapas(sessao)],
        "ultimos_dias": [
            {"data": (hoje - timedelta(days=i)).isoformat(), "quantidade": por_dia.get(hoje - timedelta(days=i), 0)}
            for i in range(6, -1, -1)
        ],
        "estoque_critico": [{"id": c.id, "sku": c.sku, "nome": c.nome, "estoque": c.estoque} for c in
                            sorted(criticos, key=lambda c: (c.estoque, c.nome))],
        "limite_estoque_critico": ESTOQUE_CRITICO,
    }


# ---------------------------------------------------------------- relatórios


def _rel_producao(sessao: Session, de, ate):
    consulta = _periodo(select(Producao), Producao.iniciada_em, de, ate).order_by(Producao.id.desc())
    linhas = [{
        "numero_serie": p.numero_serie, "id_unica": p.id_unica, "modelo": p.modelo.nome, "etapa": p.etapa.nome,
        "responsavel": p.responsavel.nome, "inicio": tempo.utc(p.iniciada_em), "atualizado": tempo.utc(p.atualizada_em),
    } for p in sessao.scalars(consulta)]
    colunas = [("numero_serie", "Nº de série", "texto"), ("id_unica", "ID da produção", "texto"),
               ("modelo", "Modelo", "texto"), ("etapa", "Etapa atual", "texto"), ("responsavel", "Responsável", "texto"),
               ("inicio", "Início", "data"), ("atualizado", "Última atualização", "data")]
    return "Produções e etapa atual", colunas, linhas


def _rel_estoque(sessao: Session, de, ate):
    pendente = pendente_por_componente(sessao)
    linhas = []
    for c in listar_componentes(sessao, incluir_inativos=True):
        pend = pendente.get(c.id, 0)
        saldo = c.estoque - pend
        situacao = "INSUFICIENTE" if saldo < 0 else "CRÍTICO" if c.estoque <= ESTOQUE_CRITICO else "OK"
        linhas.append({"sku": c.sku, "componente": c.nome, "estoque": c.estoque, "pendente": pend,
                       "saldo": saldo, "situacao": situacao})
    colunas = [("sku", "SKU", "texto"), ("componente", "Componente", "texto"), ("estoque", "Estoque", "numero"),
               ("pendente", "Solicitado e não baixado", "numero"), ("saldo", "Saldo após pendências", "numero"),
               ("situacao", "Situação", "texto")]
    return "Estoque de componentes e pendências de material", colunas, linhas


def _rel_materiais(sessao: Session, de, ate):
    consulta = _periodo(select(Solicitacao), Solicitacao.criada_em, de, ate).order_by(Solicitacao.id.desc())
    linhas = [{
        "solicitacao": s.id, "data": tempo.utc(s.criada_em), "numero_serie": s.producao.numero_serie,
        "componente": s.componente.nome, "solicitada": s.quantidade, "baixada": s.quantidade_baixada,
        "saldo": s.quantidade - s.quantidade_baixada, "status": s.status, "solicitante": s.criado_por.nome,
    } for s in sessao.scalars(consulta)]
    colunas = [("solicitacao", "Nº", "numero"), ("data", "Data", "data"), ("numero_serie", "Nº de série", "texto"),
               ("componente", "Componente", "texto"), ("solicitada", "Solicitada", "numero"),
               ("baixada", "Baixada", "numero"), ("saldo", "Saldo", "numero"), ("status", "Status", "texto"),
               ("solicitante", "Solicitante", "texto")]
    return "Solicitações e baixas de material", colunas, linhas


def _rel_nao_conformidades(sessao: Session, de, ate):
    consulta = _periodo(select(NaoConformidade), NaoConformidade.registrada_em, de, ate).order_by(NaoConformidade.id.desc())
    linhas = [{
        "data": tempo.utc(n.registrada_em), "numero_serie": n.producao.numero_serie, "modelo": n.producao.modelo.nome,
        "falha": n.descricao_falha, "motivo": n.motivo_reprovacao, "usuario": n.usuario.nome,
        "origem": n.origem_sistema or "Rastreabilidade",
    } for n in sessao.scalars(consulta)]
    colunas = [("data", "Data", "data"), ("numero_serie", "Nº de série", "texto"), ("modelo", "Modelo", "texto"),
               ("falha", "Falha", "texto"), ("motivo", "Motivo da reprovação", "texto"),
               ("usuario", "Registrado por", "texto"), ("origem", "Origem", "texto")]
    return "Não conformidades registradas", colunas, linhas


RELATORIOS = {
    "producao": _rel_producao,
    "estoque": _rel_estoque,
    "materiais": _rel_materiais,
    "nao_conformidades": _rel_nao_conformidades,
}


def gerar(sessao: Session, tipo: str, de: date | None = None, ate: date | None = None) -> dict[str, Any]:
    if tipo not in RELATORIOS:
        raise NaoEncontrado("Relatório inexistente. Use: " + ", ".join(RELATORIOS) + ".")
    titulo, colunas, linhas = RELATORIOS[tipo](sessao, de, ate)
    return {
        "tipo": tipo, "titulo": titulo, "de": de, "ate": ate,
        "colunas": [{"chave": c, "titulo": t, "formato": f} for c, t, f in colunas],
        "linhas": linhas,
    }
