"""Regras e SQL dos cadastros: usuários, status, componentes e produtos (com a lista de componentes)."""
import sqlite3

from app import config
from app.db import consultar, excluir, um
from app.erros import ErroNegocio
from app.servicos.integracao import registrar_evento
from app.seguranca import hash_senha


# ======================= USUÁRIOS (RF001) =======================
_COLUNAS_USUARIO = "id, matricula, nome, email, cargo, ativo, criado_em"


def listar_usuarios(conn, apenas_ativos=False):
    filtro = "WHERE ativo = 1" if apenas_ativos else ""
    return consultar(conn, f"SELECT {_COLUNAS_USUARIO} FROM usuarios {filtro} ORDER BY nome")


def obter_usuario(conn, usuario_id):
    u = um(conn, f"SELECT {_COLUNAS_USUARIO} FROM usuarios WHERE id = ?", (usuario_id,))
    if not u:
        raise ErroNegocio("Usuário não encontrado.", 404)
    return u


def _validar_usuario(d):
    if d["cargo"] not in config.CARGOS:
        raise ErroNegocio("Cargo inválido. Use: " + ", ".join(config.CARGOS) + ".")
    if d["ativo"] not in (0, 1):
        raise ErroNegocio("O campo ativo deve ser 0 ou 1.")
    if d.get("senha") and len(d["senha"]) < 6:
        raise ErroNegocio("A senha deve ter pelo menos 6 caracteres.")


def criar_usuario(conn, d, usuario):
    _validar_usuario(d)
    if not d.get("senha"):
        raise ErroNegocio("Informe uma senha para o novo usuário.")
    with conn:
        cur = conn.execute(
            "INSERT INTO usuarios (matricula, nome, email, senha_hash, cargo, ativo, criado_por) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d["matricula"].strip().upper(), d["nome"].strip(), d["email"].strip().lower(),
             hash_senha(d["senha"]), d["cargo"], d["ativo"], usuario["id"]))
    return obter_usuario(conn, cur.lastrowid)


def atualizar_usuario(conn, usuario_id, d, usuario):
    _validar_usuario(d)
    obter_usuario(conn, usuario_id)
    if usuario_id == usuario["id"] and (d["ativo"] == 0 or d["cargo"] not in config.CARGOS_ADMIN):
        raise ErroNegocio("Você não pode inativar nem rebaixar o seu próprio usuário.", 409)
    with conn:
        conn.execute(
            "UPDATE usuarios SET matricula=?, nome=?, email=?, cargo=?, ativo=? WHERE id=?",
            (d["matricula"].strip().upper(), d["nome"].strip(), d["email"].strip().lower(),
             d["cargo"], d["ativo"], usuario_id))
        if d.get("senha"):
            conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?", (hash_senha(d["senha"]), usuario_id))
    return obter_usuario(conn, usuario_id)


def excluir_usuario(conn, usuario_id, usuario):
    if usuario_id == usuario["id"]:
        raise ErroNegocio("Você não pode excluir o seu próprio usuário.", 409)
    excluir(conn, "usuarios", "id", usuario_id,
            "Este usuário já registrou dados no sistema e não pode ser excluído. Inative-o (campo Ativo).")


# ======================= STATUS DE PRODUÇÃO (RF003) =======================
def listar_status(conn):
    return consultar(conn, "SELECT id, nome_status, ordem, criado_em FROM status_producao ORDER BY ordem, id")


def obter_status(conn, status_id):
    s = um(conn, "SELECT id, nome_status, ordem, criado_em FROM status_producao WHERE id = ?", (status_id,))
    if not s:
        raise ErroNegocio("Status não encontrado.", 404)
    return s


def _ordem_padrao(conn):
    r = um(conn, "SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM status_producao WHERE ordem < ?",
           (config.ORDEM_LATERAL,))
    return r["prox"]


def criar_status(conn, d, usuario):
    ordem = d["ordem"] if d.get("ordem") is not None else _ordem_padrao(conn)
    with conn:
        cur = conn.execute("INSERT INTO status_producao (nome_status, ordem, criado_por) VALUES (?, ?, ?)",
                           (d["nome_status"].strip(), ordem, usuario["id"]))
    return obter_status(conn, cur.lastrowid)


def atualizar_status(conn, status_id, d):
    obter_status(conn, status_id)
    ordem = d["ordem"] if d.get("ordem") is not None else _ordem_padrao(conn)
    with conn:
        conn.execute("UPDATE status_producao SET nome_status=?, ordem=? WHERE id=?",
                     (d["nome_status"].strip(), ordem, status_id))
    return obter_status(conn, status_id)


def excluir_status(conn, status_id):
    excluir(conn, "status_producao", "id", status_id,
            "Este status já foi usado em produções ou no histórico e não pode ser excluído.")


# ======================= COMPONENTES (RF013) =======================
_SQL_COMPONENTES = """
SELECT c.idcmp, c.nome, c.codigo_sku, c.qtd_estoque, c.criado_em, u.nome AS criado_por_nome,
       CASE WHEN COALESCE(c.qtd_estoque, 0) <= %d THEN 1 ELSE 0 END AS estoque_critico,
       COALESCE((SELECT SUM(s.quantidade_solicitada -
                            COALESCE((SELECT SUM(b.quantidade_baixada) FROM baixas_materiais b
                                      WHERE b.solicitacao_id = s.id), 0))
                 FROM solicitacoes_materiais s
                 WHERE s.componente_id = c.idcmp AND s.status_solicitacao IN ('PENDENTE', 'PARCIAL')), 0)
         AS qtd_pendente
FROM componentes c
LEFT JOIN usuarios u ON u.id = c.criado_por
""" % int(config.ESTOQUE_CRITICO)


def listar_componentes(conn):
    return consultar(conn, _SQL_COMPONENTES + " ORDER BY c.nome")


def obter_componente(conn, idcmp):
    c = um(conn, _SQL_COMPONENTES + " WHERE c.idcmp = ?", (idcmp,))
    if not c:
        raise ErroNegocio("Componente não encontrado.", 404)
    return c


def criar_componente(conn, d, usuario):
    with conn:
        cur = conn.execute("INSERT INTO componentes (nome, codigo_sku, qtd_estoque, criado_por) VALUES (?, ?, ?, ?)",
                           (d["nome"].strip(), d["codigo_sku"].strip().upper(), d["qtd_estoque"], usuario["id"]))
        registrar_evento(conn, "componente.atualizado", d["codigo_sku"].strip().upper(),
                         {"sku": d["codigo_sku"].strip().upper(), "nome": d["nome"].strip(), "estoque": d["qtd_estoque"]})
    return obter_componente(conn, cur.lastrowid)


def atualizar_componente(conn, idcmp, d):
    obter_componente(conn, idcmp)
    with conn:
        conn.execute("UPDATE componentes SET nome=?, codigo_sku=?, qtd_estoque=? WHERE idcmp=?",
                     (d["nome"].strip(), d["codigo_sku"].strip().upper(), d["qtd_estoque"], idcmp))
        registrar_evento(conn, "componente.atualizado", d["codigo_sku"].strip().upper(),
                         {"sku": d["codigo_sku"].strip().upper(), "nome": d["nome"].strip(), "estoque": d["qtd_estoque"]})
    return obter_componente(conn, idcmp)


def excluir_componente(conn, idcmp):
    excluir(conn, "componentes", "idcmp", idcmp,
            "Este componente está vinculado a produtos ou a solicitações de material e não pode ser excluído.")


# ======================= PRODUTOS + COMPONENTES (RF009 / RF016) =======================
def listar_produtos(conn):
    return consultar(conn, """
        SELECT p.idprd, p.nome_modelo, p.codigo_modelo, p.quantidade, p.criado_em, u.nome AS criado_por_nome,
               (SELECT COUNT(*) FROM produto_componentes pc WHERE pc.produto_id = p.idprd) AS qtd_componentes,
               (SELECT COUNT(*) FROM producoes pr WHERE pr.produto_id = p.idprd) AS qtd_producoes
        FROM produtos p LEFT JOIN usuarios u ON u.id = p.criado_por
        ORDER BY p.nome_modelo""")


def componentes_do_produto(conn, idprd):
    return consultar(conn, """
        SELECT c.idcmp AS componente_id, c.nome, c.codigo_sku, c.qtd_estoque, pc.quantidade_necessaria
        FROM produto_componentes pc JOIN componentes c ON c.idcmp = pc.componente_id
        WHERE pc.produto_id = ? ORDER BY c.nome""", (idprd,))


def obter_produto(conn, idprd):
    p = um(conn, "SELECT idprd, nome_modelo, codigo_modelo, quantidade, criado_em FROM produtos WHERE idprd = ?",
           (idprd,))
    if not p:
        raise ErroNegocio("Produto não encontrado.", 404)
    p["componentes"] = componentes_do_produto(conn, idprd)
    return p


def _sincronizar_componentes(conn, idprd, componentes, usuario):
    """Faz a lista de componentes do produto ficar igual à lista enviada (insere, altera e remove)."""
    novos = {}
    for c in componentes:
        if c["componente_id"] in novos:
            raise ErroNegocio("O mesmo componente foi vinculado mais de uma vez ao produto.")
        if not um(conn, "SELECT 1 AS ok FROM componentes WHERE idcmp = ?", (c["componente_id"],)):
            raise ErroNegocio("Componente %s não existe." % c["componente_id"], 404)
        novos[c["componente_id"]] = c["quantidade_necessaria"]
    atuais = {r["componente_id"]: r["quantidade_necessaria"] for r in
              consultar(conn, "SELECT componente_id, quantidade_necessaria FROM produto_componentes WHERE produto_id = ?",
                        (idprd,))}
    for cid in atuais.keys() - novos.keys():
        conn.execute("DELETE FROM produto_componentes WHERE produto_id = ? AND componente_id = ?", (idprd, cid))
    for cid, qtd in novos.items():
        if cid not in atuais:
            conn.execute("INSERT INTO produto_componentes (produto_id, componente_id, quantidade_necessaria, criado_por) "
                         "VALUES (?, ?, ?, ?)", (idprd, cid, qtd, usuario["id"]))
        elif atuais[cid] != qtd:
            conn.execute("UPDATE produto_componentes SET quantidade_necessaria = ? "
                         "WHERE produto_id = ? AND componente_id = ?", (qtd, idprd, cid))


def criar_produto(conn, d, usuario):
    with conn:   # produto + componentes na mesma transação: ou grava tudo ou nada
        cur = conn.execute("INSERT INTO produtos (nome_modelo, codigo_modelo, quantidade, criado_por) VALUES (?, ?, ?, ?)",
                           (d["nome_modelo"].strip(), d["codigo_modelo"].strip().upper(), d["quantidade"], usuario["id"]))
        _sincronizar_componentes(conn, cur.lastrowid, d["componentes"], usuario)
    return obter_produto(conn, cur.lastrowid)


def atualizar_produto(conn, idprd, d, usuario):
    obter_produto(conn, idprd)
    with conn:
        conn.execute("UPDATE produtos SET nome_modelo=?, codigo_modelo=?, quantidade=? WHERE idprd=?",
                     (d["nome_modelo"].strip(), d["codigo_modelo"].strip().upper(), d["quantidade"], idprd))
        _sincronizar_componentes(conn, idprd, d["componentes"], usuario)
    return obter_produto(conn, idprd)


def excluir_produto(conn, idprd):
    obter_produto(conn, idprd)
    if um(conn, "SELECT 1 AS ok FROM producoes WHERE produto_id = ?", (idprd,)):
        raise ErroNegocio("Existem produções deste modelo; não é possível excluí-lo.", 409)
    try:
        with conn:
            conn.execute("DELETE FROM produto_componentes WHERE produto_id = ?", (idprd,))
            conn.execute("DELETE FROM produtos WHERE idprd = ?", (idprd,))
    except sqlite3.IntegrityError:
        raise ErroNegocio("Este produto está vinculado a outros registros e não pode ser excluído.", 409)
