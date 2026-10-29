"""Acesso ao SQLite (SQL puro, sem ORM)."""
import sqlite3
from datetime import datetime, timedelta, timezone

from app import config
from app.erros import ErroNegocio


def conectar() -> sqlite3.Connection:
    # check_same_thread=False: o FastAPI pode executar a dependência e a rota em threads diferentes;
    # cada requisição usa a sua própria conexão, então não há compartilhamento simultâneo.
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # tem que ser ligado em toda conexão
    return conn


def get_conn():
    """Dependência do FastAPI: uma conexão por requisição."""
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()


def consultar(conn, sql, params=()):
    return [dict(linha) for linha in conn.execute(sql, params).fetchall()]


def um(conn, sql, params=()):
    linha = conn.execute(sql, params).fetchone()
    return dict(linha) if linha else None


def excluir(conn, tabela, coluna_pk, valor, mensagem_vinculo):
    """DELETE com mensagem amigável quando a chave estrangeira impede a exclusão.
    `tabela` e `coluna_pk` vêm sempre do código (nunca do usuário)."""
    try:
        with conn:
            cur = conn.execute(f"DELETE FROM {tabela} WHERE {coluna_pk} = ?", (valor,))
    except sqlite3.IntegrityError:
        raise ErroNegocio(mensagem_vinculo, 409)
    if cur.rowcount == 0:
        raise ErroNegocio("Registro não encontrado.", 404)


def fuso_sql() -> str:
    """Modificador de fuso para as funções de data do SQLite, ex.: '-4 hours'."""
    return f"{config.FUSO_HORAS:+d} hours"


def agora_local() -> datetime:
    return datetime.now(timezone(timedelta(hours=config.FUSO_HORAS)))


def inicializar():
    """Aplica as migrações pendentes. Se o arquivo do banco ainda não existia, também carrega os dados de
    demonstração. Um banco que já existe (ex.: compartilhado com outras equipes) nunca é apagado nem repovoado."""
    from app import migracoes, seed  # import tardio para evitar import circular
    from app.servicos import integracao
    novo = not config.DB_PATH.exists()
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = conectar()
    try:
        migracoes.aplicar(conn)
        if novo:
            seed.popular(conn)
        integracao.garantir_chaves_demo(conn)
    finally:
        conn.close()
