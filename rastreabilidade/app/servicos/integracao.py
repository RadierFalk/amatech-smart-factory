"""Integração com outros sistemas (outras equipes, máquinas): clientes com chave de API, fila de eventos e
contrato estável da API /api/v1 (campos em português, datas ISO 8601 em UTC, chave de negócio = número de série)."""
import hashlib
import json
import secrets

from app import config
from app.db import consultar, um
from app.erros import ErroNegocio


# ------------------------------------------------------------------ utilidades
def iso(ts):
    """'2026-10-18 12:30:00' (UTC, como o SQLite guarda) -> '2026-10-18T12:30:00Z'."""
    return ts.replace(" ", "T") + "Z" if ts else None


def para_sqlite(ts):
    """Aceita '2026-10-18T12:30:00Z' ou '2026-10-18 12:30:00' e devolve o formato do SQLite."""
    if not ts:
        return None
    limpo = ts.strip().replace("T", " ").rstrip("Zz")[:19]
    if len(limpo) == 10:
        limpo += " 00:00:00"
    return limpo


def _hash(chave):
    return hashlib.sha256(chave.encode()).hexdigest()


# ------------------------------------------------------------------ fila de eventos (outbox)
def registrar_evento(conn, tipo, referencia, dados):
    """Grava um evento na mesma transação da operação que o gerou (chame dentro de `with conn:`)."""
    conn.execute("INSERT INTO integracao_eventos (tipo, referencia, payload) VALUES (?, ?, ?)",
                 (tipo, referencia, json.dumps(dados, ensure_ascii=False)))


def listar_eventos(conn, apos_id=0, limite=100, tipo=None):
    limite = max(1, min(limite, 1000))
    filtros, params = ["id > ?"], [apos_id or 0]
    if tipo:
        filtros.append("tipo = ?")
        params.append(tipo)
    linhas = consultar(conn, "SELECT id, tipo, referencia, payload, criado_em FROM integracao_eventos "
                             f"WHERE {' AND '.join(filtros)} ORDER BY id LIMIT ?", params + [limite])
    eventos = [{"id": l["id"], "tipo": l["tipo"], "referencia": l["referencia"],
                "dados": json.loads(l["payload"]), "ocorreu_em": iso(l["criado_em"])} for l in linhas]
    return {"eventos": eventos, "ultimo_id": eventos[-1]["id"] if eventos else (apos_id or 0)}


# ------------------------------------------------------------------ clientes (sistemas autorizados)
def _nova_chave():
    return "amt_" + secrets.token_urlsafe(24)


def listar_clientes(conn):
    return consultar(conn, "SELECT id, nome, ativo, criado_em, ultimo_uso_em FROM integracao_clientes ORDER BY nome")


def criar_cliente(conn, nome, usuario):
    nome = (nome or "").strip().lower()
    if not nome or not all(c.isalnum() or c in "-_" for c in nome):
        raise ErroNegocio("Informe um nome curto, só com letras, números, '-' ou '_' (ex.: qualidade).")
    chave = _nova_chave()
    with conn:
        cur = conn.execute("INSERT INTO integracao_clientes (nome, chave_hash, criado_por) VALUES (?, ?, ?)",
                           (nome, _hash(chave), usuario["id"]))
    return {"id": cur.lastrowid, "nome": nome, "ativo": 1, "chave": chave}   # a chave só aparece agora


def nova_chave_cliente(conn, cliente_id):
    c = um(conn, "SELECT id, nome FROM integracao_clientes WHERE id = ?", (cliente_id,))
    if not c:
        raise ErroNegocio("Sistema não encontrado.", 404)
    chave = _nova_chave()
    with conn:
        conn.execute("UPDATE integracao_clientes SET chave_hash = ? WHERE id = ?", (_hash(chave), cliente_id))
    return {"id": c["id"], "nome": c["nome"], "chave": chave}


def alterar_cliente(conn, cliente_id, ativo):
    if not um(conn, "SELECT 1 AS ok FROM integracao_clientes WHERE id = ?", (cliente_id,)):
        raise ErroNegocio("Sistema não encontrado.", 404)
    with conn:
        conn.execute("UPDATE integracao_clientes SET ativo = ? WHERE id = ?", (1 if ativo else 0, cliente_id))
    return {"ok": True}


def excluir_cliente(conn, cliente_id):
    with conn:
        cur = conn.execute("DELETE FROM integracao_clientes WHERE id = ?", (cliente_id,))
    if cur.rowcount == 0:
        raise ErroNegocio("Sistema não encontrado.", 404)


def garantir_chaves_demo(conn):
    """Cria os clientes de demonstração do ecossistema (config.CHAVES_DEMO) que ainda não existem.
    Um cliente já cadastrado nunca é alterado: se o administrador trocou a chave, a nova continua valendo."""
    with conn:
        for nome, chave in config.CHAVES_DEMO.items():
            conn.execute("INSERT OR IGNORE INTO integracao_clientes (nome, chave_hash) VALUES (?, ?)",
                         (nome, _hash(chave)))


def autenticar_cliente(conn, chave):
    if not chave:
        raise ErroNegocio("Informe a chave no cabeçalho X-API-Key.", 401)
    c = um(conn, "SELECT id, nome, ativo FROM integracao_clientes WHERE chave_hash = ?", (_hash(chave),))
    if not c or not c["ativo"]:
        raise ErroNegocio("Chave de API inválida ou inativa.", 401)
    with conn:
        conn.execute("UPDATE integracao_clientes SET ultimo_uso_em = CURRENT_TIMESTAMP WHERE id = ?", (c["id"],))
    return c


# ------------------------------------------------------------------ contrato v1 (leitura)
def status_v1(conn):
    return [{"id": s["id"], "nome": s["nome_status"], "ordem": s["ordem"]} for s in
            consultar(conn, "SELECT id, nome_status, ordem FROM status_producao ORDER BY ordem, id")]


def componentes_v1(conn):
    from app.servicos import cadastros
    return [{"sku": c["codigo_sku"], "nome": c["nome"], "estoque": c["qtd_estoque"] or 0,
             "pendente_de_baixa": c["qtd_pendente"]} for c in cadastros.listar_componentes(conn)]


def produtos_v1(conn):
    r = []
    for p in consultar(conn, "SELECT idprd, nome_modelo, codigo_modelo, quantidade FROM produtos ORDER BY nome_modelo"):
        comps = consultar(conn, """SELECT c.codigo_sku AS sku, c.nome, pc.quantidade_necessaria AS quantidade
                                   FROM produto_componentes pc JOIN componentes c ON c.idcmp = pc.componente_id
                                   WHERE pc.produto_id = ? ORDER BY c.nome""", (p["idprd"],))
        r.append({"codigo": p["codigo_modelo"], "nome": p["nome_modelo"], "quantidade": p["quantidade"],
                  "componentes": comps})
    return r


def _producao_v1(l):
    return {"numero_serie": l["numero_serie"], "id_unica": l["id_unica_producao"],
            "modelo": {"codigo": l["codigo_modelo"], "nome": l["nome_modelo"]},
            "status": l["status_nome"], "responsavel": l["responsavel_nome"],
            "iniciada_em": iso(l["data_inicio"]), "atualizada_em": iso(l["atualizado_em"])}


def producoes_v1(conn, atualizado_apos=None, status=None, limite=200, offset=0):
    from app.servicos import producao as svc
    limite = max(1, min(limite, 1000))
    filtros, params = [], []
    if atualizado_apos:
        filtros.append("atualizado_em > ?")
        params.append(para_sqlite(atualizado_apos))
    if status:
        filtros.append("lower(status_nome) = lower(?)")
        params.append(status)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    linhas = consultar(conn, f"SELECT * FROM ({svc._SQL_PRODUCAO}) {where} ORDER BY atualizado_em, id LIMIT ? OFFSET ?",
                       params + [limite, max(0, offset)])
    return [_producao_v1(l) for l in linhas]


def producao_v1(conn, numero_serie):
    from app.servicos import producao as svc
    l = um(conn, f"SELECT * FROM ({svc._SQL_PRODUCAO}) WHERE numero_serie = ?", (numero_serie.strip(),))
    if not l:
        raise ErroNegocio("Número de série não encontrado.", 404)
    d = svc.obter_producao(conn, l["id"])
    r = _producao_v1(l)
    r["historico"] = [{"status": h["status_nome"], "em": iso(h["data_horario"]), "atualizado_por": h["usuario_nome"],
                       "responsavel": h["responsavel_nome"], "origem": h["origem_atualizacao"]} for h in d["historico"]]
    r["nao_conformidades"] = consultar(conn, """
        SELECT n.descricao_falha AS falha, n.motivo_reprovacao AS motivo, n.data_registro AS em,
               n.origem_sistema AS origem, n.id_externo
        FROM nao_conformidades n WHERE n.producao_id = ? ORDER BY n.id""", (l["id"],))
    for n in r["nao_conformidades"]:
        n["em"] = iso(n["em"])
    r["materiais"] = [{"sku": s["codigo_sku"], "componente": s["componente_nome"], "solicitada": s["quantidade_solicitada"],
                       "baixada": s["quantidade_baixada"], "status": s["status_solicitacao"]} for s in d["solicitacoes"]]
    return r


def passagens_v1(conn, de=None, ate=None, status=None, limite=5000):
    """Histórico de etapas de todas as produções num período (ex.: o Dashboard conta Aprovados e Reprovados por
    turno). Diferente da fila /eventos, inclui o histórico de demonstração gravado pelo povoamento inicial."""
    limite = max(1, min(limite, 20000))
    filtros, params = [], []
    if de:
        filtros.append("h.data_horario >= ?")
        params.append(para_sqlite(de))
    if ate:
        filtros.append("h.data_horario <= ?")
        params.append(para_sqlite(ate))
    if status:
        filtros.append("lower(s.nome_status) = lower(?)")
        params.append(status)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    linhas = consultar(conn, f"""
        SELECT pr.numero_serie_notebook AS numero_serie, p.codigo_modelo, p.nome_modelo, s.nome_status,
               h.data_horario, h.origem_atualizacao
        FROM historico_passagem h JOIN producoes pr ON pr.id = h.producao_id
        LEFT JOIN produtos p ON p.idprd = pr.produto_id LEFT JOIN status_producao s ON s.id = h.status_id
        {where} ORDER BY h.data_horario, h.id LIMIT ?""", params + [limite])
    return [{"numero_serie": l["numero_serie"], "modelo": {"codigo": l["codigo_modelo"], "nome": l["nome_modelo"]},
             "status": l["nome_status"], "em": iso(l["data_horario"]), "origem": l["origem_atualizacao"]}
            for l in linhas]


def solicitacoes_v1(conn, status=None):
    from app.servicos import materiais
    return [{"id": s["id"], "numero_serie": s["numero_serie"], "sku": s["codigo_sku"], "componente": s["componente_nome"],
             "solicitada": s["quantidade_solicitada"], "baixada": s["quantidade_baixada"],
             "status": s["status_solicitacao"], "criada_em": iso(s["criado_em"])}
            for s in materiais.listar_solicitacoes(conn, status=status)]


# ------------------------------------------------------------------ contrato v1 (escrita por sistemas externos)
def _usuario_servico(conn):
    u = um(conn, "SELECT id, nome FROM usuarios WHERE matricula = ?", (config.MATRICULA_IOT,))
    if not u:
        raise ErroNegocio("Usuário de serviço da integração não está cadastrado.", 500)
    return u


def atualizar_status_externo(conn, cliente, numero_serie, status, maquina=None, descricao_falha=None,
                             motivo_reprovacao=None, id_externo=None):
    from app.servicos import producao as svc
    return svc.atualizar_por_maquina(conn, numero_serie, status, maquina, origem="API:" + cliente["nome"],
                                     descricao_falha=descricao_falha, motivo_reprovacao=motivo_reprovacao,
                                     origem_sistema=cliente["nome"], id_externo=id_externo)


def registrar_nc_externa(conn, cliente, numero_serie, falha, motivo, id_externo=None):
    prod = um(conn, "SELECT id FROM producoes WHERE numero_serie_notebook = ?", (numero_serie.strip(),))
    if not prod:
        raise ErroNegocio("Número de série não encontrado.", 404)
    if id_externo:
        ja = um(conn, "SELECT id FROM nao_conformidades WHERE origem_sistema = ? AND id_externo = ?",
                (cliente["nome"], id_externo))
        if ja:
            return {"criada": False, "id": ja["id"]}      # reenvio do mesmo registro: não duplica
    usuario = _usuario_servico(conn)
    with conn:
        cur = conn.execute("INSERT INTO nao_conformidades (producao_id, usuario_id, descricao_falha, motivo_reprovacao, "
                           "origem_sistema, id_externo) VALUES (?, ?, ?, ?, ?, ?)",
                           (prod["id"], usuario["id"], falha.strip(), motivo.strip(), cliente["nome"], id_externo))
        registrar_evento(conn, "nao_conformidade.registrada", numero_serie.strip(),
                         {"numero_serie": numero_serie.strip(), "falha": falha.strip(), "motivo": motivo.strip(),
                          "origem": cliente["nome"]})
    return {"criada": True, "id": cur.lastrowid}
