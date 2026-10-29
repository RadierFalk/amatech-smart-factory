"""Fluxo de materiais (Problema 5): solicitações padronizadas, baixas e controle de estoque."""
from app.db import consultar, excluir, um
from app.erros import ErroNegocio
from app.servicos.integracao import registrar_evento

_SQL_SOLICITACAO = """
SELECT s.id, s.producao_id, pr.numero_serie_notebook AS numero_serie, s.componente_id,
       c.nome AS componente_nome, c.codigo_sku, c.qtd_estoque, s.quantidade_solicitada,
       COALESCE((SELECT SUM(b.quantidade_baixada) FROM baixas_materiais b WHERE b.solicitacao_id = s.id), 0)
         AS quantidade_baixada,
       s.status_solicitacao, s.criado_em, u.nome AS solicitante_nome
FROM solicitacoes_materiais s
LEFT JOIN producoes pr ON pr.id = s.producao_id
JOIN componentes c ON c.idcmp = s.componente_id
LEFT JOIN usuarios u ON u.id = s.criado_por
"""

_SQL_BAIXA = """
SELECT b.id, b.solicitacao_id, b.quantidade_baixada, b.data_baixa, u.nome AS usuario_nome,
       pr.numero_serie_notebook AS numero_serie, c.nome AS componente_nome, c.codigo_sku
FROM baixas_materiais b
JOIN solicitacoes_materiais s ON s.id = b.solicitacao_id
LEFT JOIN producoes pr ON pr.id = s.producao_id
JOIN componentes c ON c.idcmp = s.componente_id
LEFT JOIN usuarios u ON u.id = b.usuario_id
"""


def _evento_solicitacao(conn, solicitacao_id):
    s = obter_solicitacao(conn, solicitacao_id)
    registrar_evento(conn, "solicitacao.criada", s["numero_serie"],
                     {"numero_serie": s["numero_serie"], "sku": s["codigo_sku"], "quantidade": s["quantidade_solicitada"]})


def _evento_estoque(conn, componente_id, motivo):
    c = um(conn, "SELECT codigo_sku, qtd_estoque FROM componentes WHERE idcmp = ?", (componente_id,))
    registrar_evento(conn, "estoque.alterado", c["codigo_sku"],
                     {"sku": c["codigo_sku"], "estoque": c["qtd_estoque"], "motivo": motivo})


# ============================ SOLICITAÇÕES (RF014) ============================
def listar_solicitacoes(conn, status=None, producao_id=None):
    filtros, params = [], []
    if status:
        filtros.append("s.status_solicitacao = ?")
        params.append(status)
    if producao_id:
        filtros.append("s.producao_id = ?")
        params.append(producao_id)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    return consultar(conn, f"{_SQL_SOLICITACAO} {where} ORDER BY s.id DESC", params)


def obter_solicitacao(conn, solicitacao_id):
    s = um(conn, _SQL_SOLICITACAO + " WHERE s.id = ?", (solicitacao_id,))
    if not s:
        raise ErroNegocio("Solicitação não encontrada.", 404)
    return s


def _recalcular_status(conn, solicitacao_id):
    """PENDENTE (nada baixado) -> PARCIAL -> ATENDIDA. Solicitação cancelada não muda."""
    s = um(conn, "SELECT quantidade_solicitada, status_solicitacao FROM solicitacoes_materiais WHERE id = ?",
           (solicitacao_id,))
    if s["status_solicitacao"] == "CANCELADA":
        return
    baixado = um(conn, "SELECT COALESCE(SUM(quantidade_baixada), 0) AS t FROM baixas_materiais WHERE solicitacao_id = ?",
                 (solicitacao_id,))["t"]
    novo = "PENDENTE" if baixado == 0 else ("ATENDIDA" if baixado >= s["quantidade_solicitada"] else "PARCIAL")
    conn.execute("UPDATE solicitacoes_materiais SET status_solicitacao = ? WHERE id = ?", (novo, solicitacao_id))


def criar_solicitacao(conn, producao_id, componente_id, quantidade, usuario):
    if not um(conn, "SELECT 1 AS ok FROM producoes WHERE id = ?", (producao_id,)):
        raise ErroNegocio("Produção não encontrada.", 404)
    if not um(conn, "SELECT 1 AS ok FROM componentes WHERE idcmp = ?", (componente_id,)):
        raise ErroNegocio("Componente não encontrado.", 404)
    with conn:
        cur = conn.execute("INSERT INTO solicitacoes_materiais (producao_id, componente_id, quantidade_solicitada, "
                           "status_solicitacao, criado_por) VALUES (?, ?, ?, 'PENDENTE', ?)",
                           (producao_id, componente_id, quantidade, usuario["id"]))
        _evento_solicitacao(conn, cur.lastrowid)
    return obter_solicitacao(conn, cur.lastrowid)


def gerar_solicitacoes_da_producao(conn, producao_id, usuario):
    """Padroniza o pedido: cria uma solicitação para cada componente da lista do produto (RF016).
    Componentes que já têm solicitação ativa nesta produção são ignorados (evita pedido em duplicidade)."""
    prod = um(conn, "SELECT id, produto_id FROM producoes WHERE id = ?", (producao_id,))
    if not prod:
        raise ErroNegocio("Produção não encontrada.", 404)
    lista = consultar(conn, "SELECT componente_id, quantidade_necessaria FROM produto_componentes WHERE produto_id = ?",
                      (prod["produto_id"],))
    if not lista:
        raise ErroNegocio("O produto desta produção não tem componentes vinculados. "
                          "Vincule-os em Cadastros > Produtos.", 409)
    criadas = ignoradas = 0
    with conn:
        for item in lista:
            ja = um(conn, "SELECT 1 AS ok FROM solicitacoes_materiais WHERE producao_id = ? AND componente_id = ? "
                          "AND status_solicitacao != 'CANCELADA'", (producao_id, item["componente_id"]))
            if ja:
                ignoradas += 1
                continue
            cur = conn.execute("INSERT INTO solicitacoes_materiais (producao_id, componente_id, quantidade_solicitada, "
                               "status_solicitacao, criado_por) VALUES (?, ?, ?, 'PENDENTE', ?)",
                               (producao_id, item["componente_id"], item["quantidade_necessaria"], usuario["id"]))
            _evento_solicitacao(conn, cur.lastrowid)
            criadas += 1
    return {"criadas": criadas, "ignoradas": ignoradas}


def atualizar_solicitacao(conn, solicitacao_id, quantidade, cancelada):
    atual = obter_solicitacao(conn, solicitacao_id)
    if quantidade < atual["quantidade_baixada"]:
        raise ErroNegocio("A quantidade não pode ser menor que a já baixada (%d)." % atual["quantidade_baixada"], 409)
    with conn:
        conn.execute("UPDATE solicitacoes_materiais SET quantidade_solicitada = ?, status_solicitacao = ? WHERE id = ?",
                     (quantidade, "CANCELADA" if cancelada else "PENDENTE", solicitacao_id))
        _recalcular_status(conn, solicitacao_id)
    return obter_solicitacao(conn, solicitacao_id)


def excluir_solicitacao(conn, solicitacao_id):
    obter_solicitacao(conn, solicitacao_id)
    if um(conn, "SELECT 1 AS ok FROM baixas_materiais WHERE solicitacao_id = ?", (solicitacao_id,)):
        raise ErroNegocio("Esta solicitação já tem baixas. Exclua as baixas primeiro (o estoque será devolvido) "
                          "ou cancele a solicitação.", 409)
    excluir(conn, "solicitacoes_materiais", "id", solicitacao_id, "Solicitação vinculada a outros registros.")


# ============================ BAIXAS (RF015) ============================
def listar_baixas(conn):
    return consultar(conn, _SQL_BAIXA + " ORDER BY b.id DESC")


def obter_baixa(conn, baixa_id):
    b = um(conn, _SQL_BAIXA + " WHERE b.id = ?", (baixa_id,))
    if not b:
        raise ErroNegocio("Baixa não encontrada.", 404)
    return b


def _validar_saldos(conn, solicitacao, nova_qtd_baixa, qtd_baixa_antiga=0):
    """Confere se a baixa cabe no saldo da solicitação e no estoque do componente."""
    baixado_sem_esta = solicitacao["quantidade_baixada"] - qtd_baixa_antiga
    saldo_solicitacao = solicitacao["quantidade_solicitada"] - baixado_sem_esta
    if nova_qtd_baixa > saldo_solicitacao:
        raise ErroNegocio("Quantidade maior que o saldo da solicitação (%d)." % saldo_solicitacao, 409)
    estoque = um(conn, "SELECT qtd_estoque FROM componentes WHERE idcmp = ?", (solicitacao["componente_id"],))["qtd_estoque"] or 0
    disponivel = estoque + qtd_baixa_antiga
    if nova_qtd_baixa > disponivel:
        raise ErroNegocio("Estoque insuficiente: disponível %d, solicitado %d." % (disponivel, nova_qtd_baixa), 409)


def criar_baixa(conn, solicitacao_id, quantidade, usuario):
    with conn:
        conn.execute("BEGIN IMMEDIATE")   # evita duas baixas simultâneas sobre o mesmo estoque
        sol = obter_solicitacao(conn, solicitacao_id)
        if sol["status_solicitacao"] == "CANCELADA":
            raise ErroNegocio("Não é possível dar baixa em solicitação cancelada.", 409)
        _validar_saldos(conn, sol, quantidade)
        cur = conn.execute("INSERT INTO baixas_materiais (solicitacao_id, usuario_id, quantidade_baixada) VALUES (?, ?, ?)",
                           (solicitacao_id, usuario["id"], quantidade))
        conn.execute("UPDATE componentes SET qtd_estoque = COALESCE(qtd_estoque, 0) - ? WHERE idcmp = ?",
                     (quantidade, sol["componente_id"]))
        _recalcular_status(conn, solicitacao_id)
        registrar_evento(conn, "baixa.registrada", sol["numero_serie"],
                         {"numero_serie": sol["numero_serie"], "sku": sol["codigo_sku"], "quantidade": quantidade})
        _evento_estoque(conn, sol["componente_id"], "baixa")
    return obter_baixa(conn, cur.lastrowid)


def atualizar_baixa(conn, baixa_id, quantidade):
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        baixa = um(conn, "SELECT id, solicitacao_id, quantidade_baixada FROM baixas_materiais WHERE id = ?", (baixa_id,))
        if not baixa:
            raise ErroNegocio("Baixa não encontrada.", 404)
        sol = obter_solicitacao(conn, baixa["solicitacao_id"])
        _validar_saldos(conn, sol, quantidade, baixa["quantidade_baixada"])
        conn.execute("UPDATE baixas_materiais SET quantidade_baixada = ? WHERE id = ?", (quantidade, baixa_id))
        conn.execute("UPDATE componentes SET qtd_estoque = COALESCE(qtd_estoque, 0) + ? WHERE idcmp = ?",
                     (baixa["quantidade_baixada"] - quantidade, sol["componente_id"]))
        _recalcular_status(conn, sol["id"])
        _evento_estoque(conn, sol["componente_id"], "baixa alterada")
    return obter_baixa(conn, baixa_id)


def excluir_baixa(conn, baixa_id):
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        baixa = um(conn, "SELECT id, solicitacao_id, quantidade_baixada FROM baixas_materiais WHERE id = ?", (baixa_id,))
        if not baixa:
            raise ErroNegocio("Baixa não encontrada.", 404)
        sol = obter_solicitacao(conn, baixa["solicitacao_id"])
        conn.execute("DELETE FROM baixas_materiais WHERE id = ?", (baixa_id,))
        conn.execute("UPDATE componentes SET qtd_estoque = COALESCE(qtd_estoque, 0) + ? WHERE idcmp = ?",
                     (baixa["quantidade_baixada"], sol["componente_id"]))
        _recalcular_status(conn, sol["id"])
        _evento_estoque(conn, sol["componente_id"], "baixa excluída")
