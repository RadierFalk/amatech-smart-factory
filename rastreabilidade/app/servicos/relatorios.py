"""Dashboard (indicadores e gráficos) e relatórios com exportação CSV (RNF006)."""
import csv
import io
from datetime import timedelta

from app import config
from app.db import agora_local, consultar, fuso_sql, um
from app.erros import ErroNegocio

STATUS_FINAL = "Expedição"


def dashboard(conn):
    fuso = fuso_sql()
    hoje = um(conn, "SELECT date('now', ?) AS d", (fuso,))["d"]
    kpis = {
        "produtos_dia": um(conn, "SELECT COUNT(*) AS n FROM producoes WHERE date(data_inicio, ?) = ?", (fuso, hoje))["n"],
        "em_producao": um(conn, """SELECT COUNT(*) AS n FROM producoes pr
                                   LEFT JOIN status_producao s ON s.id = pr.status_atual_id
                                   WHERE COALESCE(s.nome_status, '') != ?""", (STATUS_FINAL,))["n"],
        "aprovados": um(conn, """SELECT COUNT(*) AS n FROM producoes pr JOIN status_producao s ON s.id = pr.status_atual_id
                                 WHERE s.nome_status = 'Aprovado'""")["n"],
        "reprovados": um(conn, """SELECT COUNT(*) AS n FROM producoes pr JOIN status_producao s ON s.id = pr.status_atual_id
                                  WHERE s.nome_status = 'Reprovado'""")["n"],
        "solicitacoes_pendentes": um(conn, """SELECT COUNT(*) AS n FROM solicitacoes_materiais
                                              WHERE status_solicitacao IN ('PENDENTE', 'PARCIAL')""")["n"],
    }
    estoque_critico = consultar(conn, """SELECT idcmp, nome, codigo_sku, qtd_estoque FROM componentes
                                         WHERE COALESCE(qtd_estoque, 0) <= ? ORDER BY qtd_estoque, nome""",
                                (config.ESTOQUE_CRITICO,))
    kpis["estoque_critico"] = len(estoque_critico)

    por_status = consultar(conn, """
        SELECT s.nome_status AS status, s.ordem, COUNT(pr.id) AS quantidade
        FROM status_producao s LEFT JOIN producoes pr ON pr.status_atual_id = s.id
        GROUP BY s.id ORDER BY s.ordem, s.id""")

    por_dia = {r["dia"]: r["n"] for r in consultar(
        conn, "SELECT date(data_inicio, ?) AS dia, COUNT(*) AS n FROM producoes GROUP BY dia", (fuso,))}
    base = agora_local().date()
    ultimos_dias = []
    for i in range(6, -1, -1):
        dia = base - timedelta(days=i)
        ultimos_dias.append({"data": dia.isoformat(), "quantidade": por_dia.get(dia.isoformat(), 0)})

    return {"kpis": kpis, "por_status": por_status, "ultimos_dias": ultimos_dias,
            "estoque_critico": estoque_critico, "limite_estoque_critico": config.ESTOQUE_CRITICO}


# ------------------------------------------------------------------ relatórios
def _data_local(coluna):
    return f"strftime('%d/%m/%Y %H:%M', {coluna}, ?)"


def _filtro_data(coluna, data_ini, data_fim):
    filtros, params = [], []
    if data_ini:
        filtros.append(f"date({coluna}, ?) >= ?")
        params += [fuso_sql(), data_ini]
    if data_fim:
        filtros.append(f"date({coluna}, ?) <= ?")
        params += [fuso_sql(), data_fim]
    return filtros, params


def _rel_producao(conn, data_ini, data_fim):
    filtros, params = _filtro_data("pr.data_inicio", data_ini, data_fim)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    f = fuso_sql()
    linhas = consultar(conn, f"""
        SELECT pr.numero_serie_notebook AS numero_serie, pr.id_unica_producao AS id_unica,
               p.nome_modelo AS modelo, s.nome_status AS etapa, ur.nome AS responsavel,
               {_data_local('pr.data_inicio')} AS inicio,
               {_data_local("COALESCE((SELECT MAX(h.data_horario) FROM historico_passagem h WHERE h.producao_id = pr.id), pr.data_inicio)")} AS atualizado
        FROM producoes pr
        LEFT JOIN produtos p ON p.idprd = pr.produto_id
        LEFT JOIN status_producao s ON s.id = pr.status_atual_id
        LEFT JOIN usuarios ur ON ur.id = pr.responsavel_etapa_id
        {where} ORDER BY pr.id DESC""", [f, f] + params)
    colunas = [("numero_serie", "Nº de série"), ("id_unica", "ID da produção"), ("modelo", "Modelo"),
               ("etapa", "Etapa atual"), ("responsavel", "Responsável"), ("inicio", "Início"),
               ("atualizado", "Última atualização")]
    return "Produções e etapa atual", colunas, linhas


def _rel_estoque(conn, data_ini, data_fim):
    linhas = consultar(conn, """
        SELECT c.codigo_sku AS sku, c.nome AS componente, COALESCE(c.qtd_estoque, 0) AS estoque,
               COALESCE((SELECT SUM(s.quantidade_solicitada -
                                    COALESCE((SELECT SUM(b.quantidade_baixada) FROM baixas_materiais b
                                              WHERE b.solicitacao_id = s.id), 0))
                         FROM solicitacoes_materiais s
                         WHERE s.componente_id = c.idcmp AND s.status_solicitacao IN ('PENDENTE', 'PARCIAL')), 0)
                 AS pendente
        FROM componentes c ORDER BY c.nome""")
    for r in linhas:
        r["saldo"] = r["estoque"] - r["pendente"]
        r["situacao"] = ("INSUFICIENTE" if r["saldo"] < 0 else
                         "CRÍTICO" if r["estoque"] <= config.ESTOQUE_CRITICO else "OK")
    colunas = [("sku", "SKU"), ("componente", "Componente"), ("estoque", "Estoque"),
               ("pendente", "Solicitado e não baixado"), ("saldo", "Saldo após pendências"), ("situacao", "Situação")]
    return "Estoque de componentes e pendências de material", colunas, linhas


def _rel_materiais(conn, data_ini, data_fim):
    filtros, params = _filtro_data("s.criado_em", data_ini, data_fim)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    linhas = consultar(conn, f"""
        SELECT s.id AS solicitacao, {_data_local('s.criado_em')} AS data, pr.numero_serie_notebook AS numero_serie,
               c.nome AS componente, s.quantidade_solicitada AS solicitada,
               COALESCE((SELECT SUM(b.quantidade_baixada) FROM baixas_materiais b WHERE b.solicitacao_id = s.id), 0) AS baixada,
               s.status_solicitacao AS status, u.nome AS solicitante
        FROM solicitacoes_materiais s
        LEFT JOIN producoes pr ON pr.id = s.producao_id
        JOIN componentes c ON c.idcmp = s.componente_id
        LEFT JOIN usuarios u ON u.id = s.criado_por
        {where} ORDER BY s.id DESC""", [fuso_sql()] + params)
    for r in linhas:
        r["saldo"] = r["solicitada"] - r["baixada"]
    colunas = [("solicitacao", "Nº"), ("data", "Data"), ("numero_serie", "Nº de série"), ("componente", "Componente"),
               ("solicitada", "Solicitada"), ("baixada", "Baixada"), ("saldo", "Saldo"),
               ("status", "Status"), ("solicitante", "Solicitante")]
    return "Solicitações e baixas de material", colunas, linhas


def _rel_nao_conformidades(conn, data_ini, data_fim):
    filtros, params = _filtro_data("n.data_registro", data_ini, data_fim)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    linhas = consultar(conn, f"""
        SELECT {_data_local('n.data_registro')} AS data, pr.numero_serie_notebook AS numero_serie,
               p.nome_modelo AS modelo, n.descricao_falha AS falha, n.motivo_reprovacao AS motivo, u.nome AS usuario
        FROM nao_conformidades n
        LEFT JOIN producoes pr ON pr.id = n.producao_id
        LEFT JOIN produtos p ON p.idprd = pr.produto_id
        LEFT JOIN usuarios u ON u.id = n.usuario_id
        {where} ORDER BY n.id DESC""", [fuso_sql()] + params)
    colunas = [("data", "Data"), ("numero_serie", "Nº de série"), ("modelo", "Modelo"),
               ("falha", "Falha"), ("motivo", "Motivo da reprovação"), ("usuario", "Registrado por")]
    return "Não conformidades registradas", colunas, linhas


RELATORIOS = {
    "producao": _rel_producao,
    "estoque": _rel_estoque,
    "materiais": _rel_materiais,
    "nao_conformidades": _rel_nao_conformidades,
}


def gerar_relatorio(conn, tipo, data_ini=None, data_fim=None):
    if tipo not in RELATORIOS:
        raise ErroNegocio("Relatório inexistente. Use: " + ", ".join(RELATORIOS) + ".", 404)
    titulo, colunas, linhas = RELATORIOS[tipo](conn, data_ini or None, data_fim or None)
    return {"tipo": tipo, "titulo": titulo, "data_ini": data_ini, "data_fim": data_fim,
            "colunas": [{"chave": c, "titulo": t} for c, t in colunas], "linhas": linhas}


def relatorio_csv(relatorio) -> bytes:
    """CSV com ';' e BOM UTF-8: abre direto no Excel em português."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow([c["titulo"] for c in relatorio["colunas"]])
    for linha in relatorio["linhas"]:
        escritor.writerow([linha.get(c["chave"], "") for c in relatorio["colunas"]])
    return ("﻿" + saida.getvalue()).encode("utf-8")
