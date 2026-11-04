"""
Migração do banco para o login (tabela usuario), incremental e repetível.

O que faz, só quando ainda há algo a fazer:
  1. Cria um backup do banco em banco/backups/ (ao lado do arquivo do banco em uso).
  2. Acrescenta à tabela usuario as colunas matricula (única), senha_hash, ativo, data_criacao e data_alteracao_senha.
  3. Transforma os usuários antigos nas contas do sistema novo, mantendo o mesmo id_usuario, então as
     ocorrências continuam ligadas à mesma pessoa:
         Ana Souza        (Gestor)                -> ADM-0001  Administrador
         João Silva       (Operador)              -> OPE-0001  Operador
         Carlos Oliveira  (Supervisor de produção)-> ALM-0001  Almoxarife
         Maria Santos     (Responsável qualidade) -> QUA-0001  Inspetor de Qualidade
     Se algum desses nomes não existir, a conta é criada nova (com o nome do perfil).
  4. Define a senha inicial das contas (QUALIDADE_SENHA_INICIAL; padrão amatech1234), sempre como hash.

Garantias: tudo acontece numa única transação (ou conclui inteiro ou nada muda); rodar de novo não duplica
contas nem sobrescreve senhas; usuários antigos que não são uma das contas acima ficam inativos e sem matrícula
(preservados para o histórico, mas sem acesso); nenhuma ocorrência é alterada.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import autenticacao
import banco
import permissoes


# ============================================================
# CONTAS INICIAIS
# ============================================================

# (matrícula, perfil, nome do usuário antigo que passa a ser esta conta)
CONTAS_INICIAIS = [
    ("ADM-0001", permissoes.ADMINISTRADOR, "Ana Souza"),
    ("OPE-0001", permissoes.OPERADOR, "João Silva"),
    ("ALM-0001", permissoes.ALMOXARIFE, "Carlos Oliveira"),
    ("QUA-0001", permissoes.INSPETOR, "Maria Santos"),
]

# Colunas acrescentadas à tabela usuario. `ativo` nasce 0: quem não foi habilitado explicitamente não entra.
COLUNAS_NOVAS = [
    ("matricula", "TEXT"),
    ("senha_hash", "TEXT"),
    ("ativo", "INTEGER NOT NULL DEFAULT 0"),
    ("data_criacao", "TEXT"),
    ("data_alteracao_senha", "TEXT"),
]


# ============================================================
# VERIFICAÇÕES
# ============================================================

def _colunas(conexao):
    return {linha[1] for linha in conexao.execute("PRAGMA table_info(usuario)")}


def _precisa_migrar(conexao):
    colunas = _colunas(conexao)

    if any(nome not in colunas for nome, _ in COLUNAS_NOVAS):
        return True

    for matricula, _, _ in CONTAS_INICIAIS:
        existe = conexao.execute(
            "SELECT 1 FROM usuario WHERE matricula = ?", (matricula,)
        ).fetchone()

        if not existe:
            return True

    return False


def _violacoes_de_chave_estrangeira(conexao):
    return len(conexao.execute("PRAGMA foreign_key_check").fetchall())


# ============================================================
# BACKUP
# ============================================================

def _fazer_backup(caminho):
    """Cópia consistente do banco (API de backup do SQLite) em backups/, ao lado do banco."""
    pasta = caminho.parent / "backups"
    pasta.mkdir(parents=True, exist_ok=True)

    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = pasta / f"{caminho.stem}_{carimbo}.db"
    contador = 1

    while destino.exists():
        destino = pasta / f"{caminho.stem}_{carimbo}_{contador}.db"
        contador += 1

    origem = sqlite3.connect(caminho)
    copia = sqlite3.connect(destino)

    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()

    return destino


# ============================================================
# MIGRAÇÃO
# ============================================================

def _resultado_vazio():
    return {"migrado": False, "backup": None, "convertidas": [], "criadas": []}


def migrar(caminho=None, senha=None):
    """
    Aplica a migração se for necessária. Devolve um resumo:
    {"migrado": bool, "backup": caminho do backup ou None, "convertidas": [...], "criadas": [...]}.
    """
    caminho = Path(caminho or banco.CAMINHO_BANCO)

    if not caminho.exists():
        raise FileNotFoundError(f"Banco não encontrado: {caminho}")

    conexao = sqlite3.connect(caminho, timeout=30)
    conexao.isolation_level = None   # transação controlada à mão

    try:
        # Caminho rápido: quase sempre já está tudo pronto
        if not _precisa_migrar(conexao):
            return _resultado_vazio()

        conexao.execute("BEGIN IMMEDIATE")

        try:
            # Outro processo (tela e API sobem juntas) pode ter migrado enquanto esperávamos o bloqueio
            if not _precisa_migrar(conexao):
                conexao.execute("ROLLBACK")
                return _resultado_vazio()

            violacoes_antes = _violacoes_de_chave_estrangeira(conexao)
            backup = _fazer_backup(caminho)

            colunas = _colunas(conexao)
            for nome, definicao in COLUNAS_NOVAS:
                if nome not in colunas:
                    conexao.execute(f"ALTER TABLE usuario ADD COLUMN {nome} {definicao}")

            conexao.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuario_matricula ON usuario(matricula)"
            )

            convertidas, criadas = _preparar_contas(conexao, senha or autenticacao.senha_inicial())

            if _violacoes_de_chave_estrangeira(conexao) > violacoes_antes:
                raise RuntimeError("A migração quebraria uma chave estrangeira; nada foi alterado.")

            conexao.execute("COMMIT")

        except Exception:
            if conexao.in_transaction:
                conexao.execute("ROLLBACK")
            raise

        return {
            "migrado": True,
            "backup": str(backup),
            "convertidas": convertidas,
            "criadas": criadas,
        }

    finally:
        conexao.close()


def _preparar_contas(conexao, senha):
    """Converte os usuários antigos nas contas iniciais e cria as que ainda faltarem."""
    agora = datetime.now().isoformat(timespec="seconds")
    convertidas = []
    criadas = []

    for matricula, perfil, nome_antigo in CONTAS_INICIAIS:
        if conexao.execute("SELECT 1 FROM usuario WHERE matricula = ?", (matricula,)).fetchone():
            continue   # conta já existe: a senha dela não é tocada

        antigo = conexao.execute("""
            SELECT id_usuario
            FROM usuario
            WHERE nome_usuario = ? AND matricula IS NULL
            ORDER BY id_usuario
            LIMIT 1
        """, (nome_antigo,)).fetchone()

        senha_hash = autenticacao.gerar_hash(senha)

        if antigo:
            conexao.execute("""
                UPDATE usuario
                SET matricula = ?,
                    perfil_usuario = ?,
                    senha_hash = ?,
                    ativo = 1,
                    data_criacao = ?,
                    data_alteracao_senha = ?
                WHERE id_usuario = ? AND matricula IS NULL
            """, (matricula, perfil, senha_hash, agora, agora, antigo[0]))
            convertidas.append((matricula, nome_antigo, perfil))

        else:
            conexao.execute("""
                INSERT INTO usuario (
                    matricula, nome_usuario, perfil_usuario, senha_hash, ativo, data_criacao, data_alteracao_senha
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (matricula, perfil, perfil, senha_hash, agora, agora))
            criadas.append((matricula, perfil, perfil))

    return convertidas, criadas


if __name__ == "__main__":
    banco.preparar_banco()
    print(migrar())
