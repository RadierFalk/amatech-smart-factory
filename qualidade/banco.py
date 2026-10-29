import os
import shutil
import sqlite3
from pathlib import Path


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Banco que vem com o projeto (dados iniciais)
BANCO_INICIAL = Path(__file__).parent / "banco" / "controle_qualidade.db"

# Banco em uso. No servidor (Docker), QUALIDADE_DB aponta para um volume, para os dados sobreviverem às atualizações.
CAMINHO_BANCO = Path(os.environ.get("QUALIDADE_DB", BANCO_INICIAL))


def preparar_banco():
    """Se o banco em uso ainda não existe (ex.: primeiro início no servidor), começa com uma cópia do banco inicial."""
    if not CAMINHO_BANCO.exists():
        CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(BANCO_INICIAL, CAMINHO_BANCO)


# ============================================================
# CONEXÃO
# ============================================================

def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


# ============================================================
# CONSULTAS DE CADASTROS
# ============================================================

def listar_produtos():
    conexao = conectar()

    dados = conexao.execute("""
        SELECT
            id_produto,
            numero_serie_produto,
            modelo_produto
        FROM produto
        ORDER BY numero_serie_produto
    """).fetchall()

    conexao.close()
    return dados


def listar_estacoes():
    conexao = conectar()

    dados = conexao.execute("""
        SELECT
            id_estacao,
            nome_estacao,
            descricao_estacao
        FROM estacao
        ORDER BY nome_estacao
    """).fetchall()

    conexao.close()
    return dados


def listar_tipos_defeito():
    conexao = conectar()

    dados = conexao.execute("""
        SELECT
            id_tipo_defeito,
            nome_tipo_defeito,
            descricao_tipo_defeito
        FROM tipo_defeito
        ORDER BY nome_tipo_defeito
    """).fetchall()

    conexao.close()
    return dados


def listar_maquinas():
    conexao = conectar()

    dados = conexao.execute("""
        SELECT
            id_maquina,
            nome_maquina,
            descricao_maquina
        FROM maquina
        ORDER BY nome_maquina
    """).fetchall()

    conexao.close()
    return dados


def listar_usuarios():
    conexao = conectar()

    dados = conexao.execute("""
        SELECT
            id_usuario,
            nome_usuario,
            perfil_usuario
        FROM usuario
        ORDER BY nome_usuario
    """).fetchall()

    conexao.close()
    return dados


# ============================================================
# OCORRÊNCIA
# ============================================================

def registrar_ocorrencia(
    data_ocorrencia,
    hora_ocorrencia,
    classificacao_defeito,
    situacao_produto,
    observacao_ocorrencia,
    acao_realizada,
    status_ocorrencia,
    id_produto,
    id_estacao,
    id_tipo_defeito,
    id_maquina,
    id_usuario
):
    conexao = conectar()

    cursor = conexao.execute("""
        INSERT INTO ocorrencia (
            data_ocorrencia,
            hora_ocorrencia,
            classificacao_defeito,
            situacao_produto,
            observacao_ocorrencia,
            acao_realizada,
            status_ocorrencia,
            visibilidade_ocorrencia,
            id_produto,
            id_estacao,
            id_tipo_defeito,
            id_maquina,
            id_usuario
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Visivel', ?, ?, ?, ?, ?)
    """, (
        data_ocorrencia,
        hora_ocorrencia,
        classificacao_defeito,
        situacao_produto,
        observacao_ocorrencia,
        acao_realizada,
        status_ocorrencia,
        id_produto,
        id_estacao,
        id_tipo_defeito,
        id_maquina,
        id_usuario
    ))

    conexao.commit()
    id_ocorrencia = cursor.lastrowid

    conexao.close()

    return id_ocorrencia


# ============================================================
# HISTÓRICO
# ============================================================

def listar_ocorrencias():
    conexao = conectar()

    dados = conexao.execute("""
        SELECT
            o.id_ocorrencia,
            o.data_ocorrencia,
            o.hora_ocorrencia,
            p.numero_serie_produto,
            p.modelo_produto,
            e.nome_estacao,
            t.nome_tipo_defeito,
            m.nome_maquina,
            u.nome_usuario,
            o.classificacao_defeito,
            o.situacao_produto,
            o.observacao_ocorrencia,
            o.acao_realizada,
            o.status_ocorrencia,
            o.visibilidade_ocorrencia
        FROM ocorrencia o

        INNER JOIN produto p
            ON o.id_produto = p.id_produto

        INNER JOIN estacao e
            ON o.id_estacao = e.id_estacao

        INNER JOIN tipo_defeito t
            ON o.id_tipo_defeito = t.id_tipo_defeito

        INNER JOIN maquina m
            ON o.id_maquina = m.id_maquina

        INNER JOIN usuario u
            ON o.id_usuario = u.id_usuario

        WHERE o.visibilidade_ocorrencia = 'Visivel'

        ORDER BY
            o.data_ocorrencia DESC,
            o.hora_ocorrencia DESC
    """).fetchall()

    conexao.close()
    return dados


# ============================================================
# PESQUISA
# ============================================================

def pesquisar_ocorrencias(termo):
    conexao = conectar()

    termo = f"%{termo}%"

    dados = conexao.execute("""
        SELECT
            o.id_ocorrencia,
            o.data_ocorrencia,
            o.hora_ocorrencia,
            p.numero_serie_produto,
            p.modelo_produto,
            e.nome_estacao,
            t.nome_tipo_defeito,
            m.nome_maquina,
            u.nome_usuario,
            o.classificacao_defeito,
            o.situacao_produto,
            o.observacao_ocorrencia,
            o.acao_realizada,
            o.status_ocorrencia,
            o.visibilidade_ocorrencia
        FROM ocorrencia o

        INNER JOIN produto p
            ON o.id_produto = p.id_produto

        INNER JOIN estacao e
            ON o.id_estacao = e.id_estacao

        INNER JOIN tipo_defeito t
            ON o.id_tipo_defeito = t.id_tipo_defeito

        INNER JOIN maquina m
            ON o.id_maquina = m.id_maquina

        INNER JOIN usuario u
            ON o.id_usuario = u.id_usuario

        WHERE o.visibilidade_ocorrencia = 'Visivel'

        AND (
            p.numero_serie_produto LIKE ?
            OR p.modelo_produto LIKE ?
            OR e.nome_estacao LIKE ?
            OR t.nome_tipo_defeito LIKE ?
            OR m.nome_maquina LIKE ?
            OR u.nome_usuario LIKE ?
            OR o.classificacao_defeito LIKE ?
            OR o.status_ocorrencia LIKE ?
        )

        ORDER BY
            o.data_ocorrencia DESC,
            o.hora_ocorrencia DESC
    """, (
        termo,
        termo,
        termo,
        termo,
        termo,
        termo,
        termo,
        termo
    )).fetchall()

    conexao.close()
    return dados


# ============================================================
# FILTROS
# ============================================================

def filtrar_ocorrencias(
    tipo_defeito=None,
    estacao=None,
    classificacao=None,
    status=None
):
    conexao = conectar()

    consulta = """
        SELECT
            o.id_ocorrencia,
            o.data_ocorrencia,
            o.hora_ocorrencia,
            p.numero_serie_produto,
            p.modelo_produto,
            e.nome_estacao,
            t.nome_tipo_defeito,
            m.nome_maquina,
            u.nome_usuario,
            o.classificacao_defeito,
            o.situacao_produto,
            o.observacao_ocorrencia,
            o.acao_realizada,
            o.status_ocorrencia,
            o.visibilidade_ocorrencia
        FROM ocorrencia o

        INNER JOIN produto p
            ON o.id_produto = p.id_produto

        INNER JOIN estacao e
            ON o.id_estacao = e.id_estacao

        INNER JOIN tipo_defeito t
            ON o.id_tipo_defeito = t.id_tipo_defeito

        INNER JOIN maquina m
            ON o.id_maquina = m.id_maquina

        INNER JOIN usuario u
            ON o.id_usuario = u.id_usuario

        WHERE o.visibilidade_ocorrencia = 'Visivel'
    """

    parametros = []

    if tipo_defeito:
        consulta += " AND t.nome_tipo_defeito = ?"
        parametros.append(tipo_defeito)

    if estacao:
        consulta += " AND e.nome_estacao = ?"
        parametros.append(estacao)

    if classificacao:
        consulta += " AND o.classificacao_defeito = ?"
        parametros.append(classificacao)

    if status:
        consulta += " AND o.status_ocorrencia = ?"
        parametros.append(status)

    consulta += """
        ORDER BY
            o.data_ocorrencia DESC,
            o.hora_ocorrencia DESC
    """

    dados = conexao.execute(
        consulta,
        parametros
    ).fetchall()

    conexao.close()
    return dados


# ============================================================
# BUSCAR UMA OCORRÊNCIA
# ============================================================

def buscar_ocorrencia(id_ocorrencia):
    conexao = conectar()

    dado = conexao.execute("""
        SELECT
            *
        FROM ocorrencia
        WHERE id_ocorrencia = ?
    """, (id_ocorrencia,)).fetchone()

    conexao.close()

    return dado


# ============================================================
# EDITAR OCORRÊNCIA
# ============================================================

def editar_ocorrencia(
    id_ocorrencia,
    data_ocorrencia,
    hora_ocorrencia,
    classificacao_defeito,
    situacao_produto,
    observacao_ocorrencia,
    acao_realizada,
    status_ocorrencia,
    id_produto,
    id_estacao,
    id_tipo_defeito,
    id_maquina,
    id_usuario
):
    conexao = conectar()

    conexao.execute("""
        UPDATE ocorrencia
        SET
            data_ocorrencia = ?,
            hora_ocorrencia = ?,
            classificacao_defeito = ?,
            situacao_produto = ?,
            observacao_ocorrencia = ?,
            acao_realizada = ?,
            status_ocorrencia = ?,
            id_produto = ?,
            id_estacao = ?,
            id_tipo_defeito = ?,
            id_maquina = ?,
            id_usuario = ?
        WHERE id_ocorrencia = ?
    """, (
        data_ocorrencia,
        hora_ocorrencia,
        classificacao_defeito,
        situacao_produto,
        observacao_ocorrencia,
        acao_realizada,
        status_ocorrencia,
        id_produto,
        id_estacao,
        id_tipo_defeito,
        id_maquina,
        id_usuario,
        id_ocorrencia
    ))

    conexao.commit()
    conexao.close()


# ============================================================
# OCULTAR OCORRÊNCIA
# ============================================================

def ocultar_ocorrencia(id_ocorrencia):
    conexao = conectar()

    conexao.execute("""
        UPDATE ocorrencia
        SET visibilidade_ocorrencia = 'Oculta'
        WHERE id_ocorrencia = ?
    """, (id_ocorrencia,))

    conexao.commit()
    conexao.close()

# ============================================================
# INTEGRAÇÃO COM OS OUTROS SETORES
# ============================================================

def buscar_ocorrencia_detalhada(id_ocorrencia):
    """Ocorrência com os nomes do produto, defeito, estação e máquina (usada ao avisar os outros sistemas)."""
    conexao = conectar()

    dado = conexao.execute("""
        SELECT
            o.id_ocorrencia,
            o.data_ocorrencia,
            o.hora_ocorrencia,
            o.classificacao_defeito,
            o.situacao_produto,
            o.observacao_ocorrencia,
            o.acao_realizada,
            p.numero_serie_produto,
            p.modelo_produto,
            t.nome_tipo_defeito,
            e.nome_estacao,
            m.nome_maquina
        FROM ocorrencia o
        INNER JOIN produto p ON o.id_produto = p.id_produto
        INNER JOIN tipo_defeito t ON o.id_tipo_defeito = t.id_tipo_defeito
        INNER JOIN estacao e ON o.id_estacao = e.id_estacao
        INNER JOIN maquina m ON o.id_maquina = m.id_maquina
        WHERE o.id_ocorrencia = ?
    """, (id_ocorrencia,)).fetchone()

    conexao.close()

    return dado


def inserir_produto_se_novo(numero_serie, modelo):
    """Grava um notebook vindo da Rastreabilidade. Devolve True se ele ainda não existia.
    Só grava quando é novo: assim, abrir o sistema não altera o banco versionado no Git."""
    conexao = conectar()

    existe = conexao.execute("""
        SELECT 1 FROM produto WHERE numero_serie_produto = ?
    """, (numero_serie,)).fetchone()

    if not existe:
        conexao.execute("""
            INSERT INTO produto (
                numero_serie_produto,
                modelo_produto
            )
            VALUES (?, ?)
        """, (numero_serie, modelo))

        conexao.commit()

    conexao.close()

    return not existe


def inserir_maquina_se_nova(tag, descricao):
    """Grava uma máquina vinda da Manutenção (a TAG é o nome). Devolve True se ela ainda não existia."""
    conexao = conectar()

    existe = conexao.execute("""
        SELECT 1 FROM maquina WHERE nome_maquina = ?
    """, (tag,)).fetchone()

    if not existe:
        conexao.execute("""
            INSERT INTO maquina (
                nome_maquina,
                descricao_maquina
            )
            VALUES (?, ?)
        """, (tag, descricao))

        conexao.commit()

    conexao.close()

    return not existe
