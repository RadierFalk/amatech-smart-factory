"""Produção e rastreabilidade: criar, consultar, avançar etapa, histórico e não conformidades."""
from app import config
from app.db import agora_local, consultar, excluir, um
from app.erros import ErroNegocio
from app.servicos.integracao import registrar_evento

_SQL_PRODUCAO = """
SELECT pr.id, pr.numero_serie_notebook AS numero_serie, pr.id_unica_producao, pr.produto_id,
       p.nome_modelo, p.codigo_modelo, pr.status_atual_id, s.nome_status AS status_nome,
       pr.responsavel_etapa_id, ur.nome AS responsavel_nome, pr.data_inicio,
       uc.nome AS criado_por_nome,
       COALESCE((SELECT MAX(h.data_horario) FROM historico_passagem h WHERE h.producao_id = pr.id),
                pr.data_inicio) AS atualizado_em
FROM producoes pr
LEFT JOIN produtos p        ON p.idprd = pr.produto_id
LEFT JOIN status_producao s ON s.id = pr.status_atual_id
LEFT JOIN usuarios ur       ON ur.id = pr.responsavel_etapa_id
LEFT JOIN usuarios uc       ON uc.id = pr.criado_por
"""


# ---------------------------------------------------------------- consultas
def listar_producoes(conn, q=None, status_id=None, produto_id=None, limite=500):
    """Lista produções. `q` procura no número de série, ID único e modelo (RF009)."""
    filtros, params = [], []
    if q and q.strip():
        like = "%" + q.strip() + "%"
        filtros.append("(pr.numero_serie_notebook LIKE ? OR pr.id_unica_producao LIKE ? "
                       "OR p.nome_modelo LIKE ? OR p.codigo_modelo LIKE ?)")
        params += [like, like, like, like]
    if status_id:
        filtros.append("pr.status_atual_id = ?")
        params.append(status_id)
    if produto_id:
        filtros.append("pr.produto_id = ?")
        params.append(produto_id)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    params.append(limite)
    return consultar(conn, f"{_SQL_PRODUCAO} {where} ORDER BY atualizado_em DESC, pr.id DESC LIMIT ?", params)


def _proxima_etapa_sugerida(conn, status_atual_id):
    principais = consultar(conn, "SELECT id FROM status_producao WHERE ordem < ? ORDER BY ordem, id",
                           (config.ORDEM_LATERAL,))
    ids = [s["id"] for s in principais]
    if not ids:
        return None
    if status_atual_id in ids:
        i = ids.index(status_atual_id)
        return ids[i + 1] if i + 1 < len(ids) else None
    return ids[1] if len(ids) > 1 else ids[0]   # veio de Parado/Reprovado: volta para a 2ª etapa (retrabalho)


def obter_producao(conn, producao_id):
    """Detalhe completo: histórico (RF007), não conformidades, materiais e outras produções do modelo (RF009)."""
    prod = um(conn, _SQL_PRODUCAO + " WHERE pr.id = ?", (producao_id,))
    if not prod:
        raise ErroNegocio("Produção não encontrada.", 404)
    prod["historico"] = consultar(conn, """
        SELECT h.id, h.data_horario, s.nome_status AS status_nome, uu.nome AS usuario_nome,
               ur.nome AS responsavel_nome, h.origem_atualizacao
        FROM historico_passagem h
        LEFT JOIN status_producao s ON s.id = h.status_id
        LEFT JOIN usuarios uu ON uu.id = h.usuario_id
        LEFT JOIN usuarios ur ON ur.id = h.responsavel_etapa_id
        WHERE h.producao_id = ? ORDER BY h.data_horario, h.id""", (producao_id,))
    prod["nao_conformidades"] = consultar(conn, """
        SELECT n.id, n.data_registro, n.descricao_falha, n.motivo_reprovacao, u.nome AS usuario_nome
        FROM nao_conformidades n LEFT JOIN usuarios u ON u.id = n.usuario_id
        WHERE n.producao_id = ? ORDER BY n.data_registro, n.id""", (producao_id,))
    prod["solicitacoes"] = consultar(conn, """
        SELECT s.id, c.nome AS componente_nome, c.codigo_sku, s.quantidade_solicitada, s.status_solicitacao,
               COALESCE((SELECT SUM(b.quantidade_baixada) FROM baixas_materiais b WHERE b.solicitacao_id = s.id), 0)
                 AS quantidade_baixada
        FROM solicitacoes_materiais s JOIN componentes c ON c.idcmp = s.componente_id
        WHERE s.producao_id = ? ORDER BY s.id""", (producao_id,))
    prod["materiais_pendentes"] = sum(1 for s in prod["solicitacoes"] if s["status_solicitacao"] in ("PENDENTE", "PARCIAL"))
    prod["mesmo_modelo"] = consultar(conn, """
        SELECT pr.id, pr.numero_serie_notebook AS numero_serie, s.nome_status AS status_nome, pr.data_inicio
        FROM producoes pr LEFT JOIN status_producao s ON s.id = pr.status_atual_id
        WHERE pr.produto_id = ? ORDER BY pr.id DESC""", (prod["produto_id"],))
    prod["proxima_etapa_sugerida_id"] = _proxima_etapa_sugerida(conn, prod["status_atual_id"])
    return prod


# ---------------------------------------------------------------- escrita
def _exigir_usuario(conn, usuario_id):
    if not um(conn, "SELECT 1 AS ok FROM usuarios WHERE id = ?", (usuario_id,)):
        raise ErroNegocio("Responsável não encontrado.", 404)


def criar_producao(conn, produto_id, responsavel_id, usuario):
    """RF002 + RF004 + RF005: cria a produção, gera o nº de série e o ID único e grava o 1º registro do histórico."""
    if not um(conn, "SELECT 1 AS ok FROM produtos WHERE idprd = ?", (produto_id,)):
        raise ErroNegocio("Produto não encontrado.", 404)
    inicial = um(conn, "SELECT id FROM status_producao ORDER BY ordem, id LIMIT 1")
    if not inicial:
        raise ErroNegocio("Cadastre os status de produção antes de iniciar uma produção.", 409)
    responsavel_id = responsavel_id or usuario["id"]
    _exigir_usuario(conn, responsavel_id)
    with conn:
        conn.execute("BEGIN IMMEDIATE")   # trava gravações concorrentes para o nº de série nunca repetir
        seq = um(conn, "SELECT seq FROM sqlite_sequence WHERE name = 'producoes'")
        n = (seq["seq"] if seq else 0) + 1
        serie = f"{config.PREFIXO_SERIE}-{n:06d}"
        id_unica = f"PRD-{serie}-{agora_local():%Y%m%d}"
        conn.execute(
            "INSERT INTO producoes (id, numero_serie_notebook, id_unica_producao, produto_id, status_atual_id, "
            "responsavel_etapa_id, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (n, serie, id_unica, produto_id, inicial["id"], responsavel_id, usuario["id"]))
        conn.execute(
            "INSERT INTO historico_passagem (producao_id, status_id, usuario_id, responsavel_etapa_id, origem_atualizacao) "
            "VALUES (?, ?, ?, ?, 'MANUAL')", (n, inicial["id"], usuario["id"], responsavel_id))
        registrar_evento(conn, "producao.criada", serie, {"numero_serie": serie, "id_unica": id_unica, "produto_id": produto_id})
    return obter_producao(conn, n)


def atualizar_producao(conn, producao_id, produto_id, responsavel_id):
    obter_producao(conn, producao_id)
    if not um(conn, "SELECT 1 AS ok FROM produtos WHERE idprd = ?", (produto_id,)):
        raise ErroNegocio("Produto não encontrado.", 404)
    if responsavel_id:
        _exigir_usuario(conn, responsavel_id)
    with conn:
        conn.execute("UPDATE producoes SET produto_id = ?, responsavel_etapa_id = COALESCE(?, responsavel_etapa_id) "
                     "WHERE id = ?", (produto_id, responsavel_id, producao_id))
    return obter_producao(conn, producao_id)


def excluir_producao(conn, producao_id):
    obter_producao(conn, producao_id)
    if um(conn, """SELECT 1 AS ok FROM baixas_materiais b JOIN solicitacoes_materiais s ON s.id = b.solicitacao_id
                   WHERE s.producao_id = ?""", (producao_id,)):
        raise ErroNegocio("Há baixas de material registradas nesta produção. Exclua as baixas antes "
                          "(o estoque será devolvido).", 409)
    with conn:
        conn.execute("DELETE FROM nao_conformidades WHERE producao_id = ?", (producao_id,))
        conn.execute("DELETE FROM solicitacoes_materiais WHERE producao_id = ?", (producao_id,))
        conn.execute("DELETE FROM historico_passagem WHERE producao_id = ?", (producao_id,))
    excluir(conn, "producoes", "id", producao_id, "Esta produção está vinculada a outros registros.")


def avancar_etapa(conn, producao_id, status_id, responsavel_id, usuario,
                  descricao_falha=None, motivo_reprovacao=None, origem="MANUAL", origem_sistema=None, id_externo=None):
    """RF006 + RF008 + RF012: muda a etapa e guarda dia/horário, quem atualizou e o novo responsável."""
    prod = um(conn, """SELECT pr.id, pr.numero_serie_notebook AS numero_serie, pr.status_atual_id, pr.responsavel_etapa_id,
                              s.nome_status AS status_nome
                       FROM producoes pr LEFT JOIN status_producao s ON s.id = pr.status_atual_id WHERE pr.id = ?""",
              (producao_id,))
    if not prod:
        raise ErroNegocio("Produção não encontrada.", 404)
    status = um(conn, "SELECT id, nome_status FROM status_producao WHERE id = ?", (status_id,))
    if not status:
        raise ErroNegocio("Status inválido.", 404)
    if prod["status_atual_id"] == status_id:
        raise ErroNegocio("A produção já está nesta etapa.", 409)
    responsavel_id = responsavel_id or prod["responsavel_etapa_id"] or usuario["id"]
    _exigir_usuario(conn, responsavel_id)
    reprovado = status["nome_status"].strip().lower() == "reprovado"
    falha, motivo = (descricao_falha or "").strip(), (motivo_reprovacao or "").strip()
    if reprovado and not (falha and motivo):
        raise ErroNegocio("Para reprovar, informe a falha encontrada e o motivo da reprovação.")
    with conn:
        conn.execute("UPDATE producoes SET status_atual_id = ?, responsavel_etapa_id = ? WHERE id = ?",
                     (status_id, responsavel_id, producao_id))
        conn.execute(
            "INSERT INTO historico_passagem (producao_id, status_id, usuario_id, responsavel_etapa_id, origem_atualizacao) "
            "VALUES (?, ?, ?, ?, ?)", (producao_id, status_id, usuario["id"], responsavel_id, origem))
        if reprovado:   # origem_sistema/id_externo: NC vinda de outro sistema pela API (ex.: QLD-12 da Qualidade)
            conn.execute("INSERT INTO nao_conformidades (producao_id, usuario_id, descricao_falha, motivo_reprovacao, "
                         "origem_sistema, id_externo) VALUES (?, ?, ?, ?, COALESCE(?, 'AMATECH'), ?)",
                         (producao_id, usuario["id"], falha, motivo, origem_sistema, id_externo))
            registrar_evento(conn, "nao_conformidade.registrada", prod["numero_serie"],
                             {"numero_serie": prod["numero_serie"], "falha": falha, "motivo": motivo, "origem": origem})
        registrar_evento(conn, "producao.etapa_alterada", prod["numero_serie"],
                         {"numero_serie": prod["numero_serie"], "status_anterior": prod["status_nome"],
                          "status_novo": status["nome_status"], "origem": origem})
    return obter_producao(conn, producao_id)


def registrar_nao_conformidade(conn, producao_id, descricao_falha, motivo_reprovacao, usuario):
    """RF011: registra uma falha (ex.: encontrada na etapa de teste) sem mudar a etapa."""
    serie = obter_producao(conn, producao_id)["numero_serie"]
    with conn:
        conn.execute("INSERT INTO nao_conformidades (producao_id, usuario_id, descricao_falha, motivo_reprovacao) "
                     "VALUES (?, ?, ?, ?)", (producao_id, usuario["id"], descricao_falha.strip(), motivo_reprovacao.strip()))
        registrar_evento(conn, "nao_conformidade.registrada", serie,
                         {"numero_serie": serie, "falha": descricao_falha.strip(), "motivo": motivo_reprovacao.strip(),
                          "origem": "AMATECH"})
    return obter_producao(conn, producao_id)


def atualizar_por_maquina(conn, numero_serie, nome_status, maquina=None, origem="MAQUINA/IOT", descricao_falha=None,
                          motivo_reprovacao=None, origem_sistema=None, id_externo=None):
    """RF017: uma máquina (ou outro sistema, via /api/v1) informa o status e a produção é atualizada.
    A origem fica gravada no histórico: MAQUINA/IOT ou API:<nome do sistema>.

    Outro sistema pode mandar a falha e o motivo reais da reprovação e o id do registro dele (id_externo).
    Uma reprovação com o mesmo id_externo já registrada não é aplicada de novo (reenvio)."""
    prod = um(conn, "SELECT id, status_atual_id FROM producoes WHERE numero_serie_notebook = ?", (numero_serie.strip(),))
    if not prod:
        raise ErroNegocio("Número de série não encontrado.", 404)
    status = um(conn, "SELECT id FROM status_producao WHERE lower(nome_status) = lower(?)", (nome_status.strip(),))
    if not status:
        raise ErroNegocio("Status '%s' não cadastrado." % nome_status, 404)
    iot = um(conn, "SELECT id, nome FROM usuarios WHERE matricula = ?", (config.MATRICULA_IOT,))
    if not iot:
        raise ErroNegocio("Usuário de serviço da integração não está cadastrado.", 500)
    ja_registrada = id_externo and um(conn, "SELECT 1 AS ok FROM nao_conformidades WHERE origem_sistema = ? "
                                            "AND id_externo = ?", (origem_sistema, id_externo))
    if prod["status_atual_id"] == status["id"] or (ja_registrada and nome_status.strip().lower() == "reprovado"):
        return {"alterado": False, "producao": obter_producao(conn, prod["id"])}
    origem_txt = "Reprovado automaticamente pela máquina" + (f" {maquina}" if maquina else "")
    producao = avancar_etapa(conn, prod["id"], status["id"], None, iot,
                             descricao_falha=(descricao_falha or "").strip() or origem_txt,
                             motivo_reprovacao=(motivo_reprovacao or "").strip() or "Detecção por equipamento",
                             origem=origem, origem_sistema=origem_sistema, id_externo=id_externo)
    return {"alterado": True, "producao": producao}
