"""
Persistência e Gerenciamento do Banco de Identidades do ERP AMATECH.
Banco SQLite: portal/banco/erp_usuarios.db
"""
import hashlib
import hmac
import sqlite3
from pathlib import Path
from typing import Any

from config import DB_PATH, SENHA_INICIAL_PADRAO
from permissoes import (
    ADMINISTRADOR,
    ALMOXARIFE,
    INSPETOR,
    OPERADOR,
    PREFIXOS_MATRICULA,
    TECNICO,
)

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
except ImportError:
    _hasher = None


# ============================================================
# CRIPTOGRAFIA DE SENHAS
# ============================================================

def gerar_hash(senha: str) -> str:
    """Gera hash seguro da senha. Prefere Argon2; fallback para SHA-256."""
    if _hasher:
        return _hasher.hash(senha)
    # Fallback caso argon2 não esteja presente
    sal = "amatech_salt_2026"
    return "sha256$" + hashlib.sha256(f"{sal}:{senha}".encode("utf-8")).hexdigest()


def verificar_hash(senha: str, hash_gravado: str) -> bool:
    """Verifica a senha contra o hash gravado."""
    if not senha or not hash_gravado:
        return False
    # Senhas planas de demo em bancos legados
    if senha == hash_gravado or (hash_gravado in ("123456", "amatech123", "amatech1234") and senha == hash_gravado):
        return True
    if hash_gravado.startswith("$argon2"):
        if _hasher:
            try:
                return _hasher.verify(hash_gravado, senha)
            except Exception:
                return False
        return False
    if hash_gravado.startswith("sha256$"):
        sal = "amatech_salt_2026"
        esperado = "sha256$" + hashlib.sha256(f"{sal}:{senha}".encode("utf-8")).hexdigest()
        return hmac.compare_digest(hash_gravado, esperado)
    # Suporte a SHA-256 puro legado
    if len(hash_gravado) == 64:
        return hashlib.sha256(senha.encode("utf-8")).hexdigest() == hash_gravado
    return False


# ============================================================
# CONEXÃO E INICIALIZAÇÃO
# ============================================================

def conectar(caminho: Path | None = None) -> sqlite3.Connection:
    target = caminho or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_banco(caminho: Path | None = None) -> None:
    """Cria a tabela de usuários do ERP e popula com os usuários canônicos se vazia."""
    with conectar(caminho) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula VARCHAR(20) NOT NULL UNIQUE,
                nome VARCHAR(100) NOT NULL,
                senha_hash VARCHAR(255) NOT NULL,
                perfil VARCHAR(50) NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT 1,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_usuarios_matricula ON usuarios(matricula);")

        cursor = conn.execute("SELECT COUNT(*) as total FROM usuarios")
        total = cursor.fetchone()["total"]

        if total == 0:
            # Seed com as 5 personas canônicas
            hash_padrao = gerar_hash(SENHA_INICIAL_PADRAO)
            usuarios_seed = [
                ("ADM-0001", "Ana Souza", ADMINISTRADOR),
                ("QUA-0001", "Maria Santos", INSPETOR),
                ("OPE-0001", "João Silva", OPERADOR),
                ("TEC-2001", "João Lima Silva", TECNICO),
                ("ALM-0001", "Carlos Oliveira", ALMOXARIFE),
            ]
            for mat, nome, perfil in usuarios_seed:
                conn.execute(
                    """
                    INSERT INTO usuarios (matricula, nome, senha_hash, perfil, ativo)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (mat, nome, hash_padrao, perfil),
                )
            conn.commit()


# ============================================================
# OPERAÇÕES DE CONSULTA E GESTÃO (CRUD)
# ============================================================

def listar_usuarios(caminho: Path | None = None) -> list[dict[str, Any]]:
    with conectar(caminho) as conn:
        cursor = conn.execute("""
            SELECT id, matricula, nome, perfil, ativo, criado_em
            FROM usuarios
            ORDER BY matricula ASC
        """)
        return [dict(r) for r in cursor.fetchall()]


def buscar_por_matricula(matricula: str, caminho: Path | None = None) -> dict[str, Any] | None:
    mat = (matricula or "").strip().upper()
    with conectar(caminho) as conn:
        cursor = conn.execute("""
            SELECT id, matricula, nome, senha_hash, perfil, ativo, criado_em
            FROM usuarios
            WHERE UPPER(matricula) = ?
        """, (mat,))
        row = cursor.fetchone()
        return dict(row) if row else None


def buscar_por_id(id_usuario: int, caminho: Path | None = None) -> dict[str, Any] | None:
    with conectar(caminho) as conn:
        cursor = conn.execute("""
            SELECT id, matricula, nome, senha_hash, perfil, ativo, criado_em
            FROM usuarios
            WHERE id = ?
        """, (id_usuario,))
        row = cursor.fetchone()
        return dict(row) if row else None


def proxima_matricula(perfil: str, caminho: Path | None = None) -> str:
    """Gera a próxima matrícula sequencial baseada no prefixo do perfil (ex.: ADM-0002)."""
    prefixo = PREFIXOS_MATRICULA.get(perfil, "USR")
    with conectar(caminho) as conn:
        cursor = conn.execute("""
            SELECT matricula FROM usuarios
            WHERE matricula LIKE ?
            ORDER BY matricula DESC
        """, (f"{prefixo}-%",))
        rows = cursor.fetchall()
        numeros = []
        for r in rows:
            try:
                num = int(r["matricula"].split("-")[1])
                numeros.append(num)
            except (IndexError, ValueError):
                continue
        proximo = (max(numeros) + 1) if numeros else 1
        return f"{prefixo}-{proximo:04d}"


def criar_usuario(
    nome: str,
    perfil: str,
    senha: str,
    matricula: str | None = None,
    caminho: Path | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    nome_limpo = (nome or "").strip()
    if not nome_limpo:
        return False, "Informe o nome completo do colaborador.", None
    if not senha or len(senha) < 4:
        return False, "A senha deve ter no mínimo 4 caracteres.", None

    mat = (matricula or "").strip().upper() or proxima_matricula(perfil, caminho)

    with conectar(caminho) as conn:
        # Verificar se já existe a matrícula
        cursor = conn.execute("SELECT id FROM usuarios WHERE UPPER(matricula) = ?", (mat,))
        if cursor.fetchone():
            return False, f"A matrícula '{mat}' já está cadastrada.", None

        conn.execute("""
            INSERT INTO usuarios (matricula, nome, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, 1)
        """, (mat, nome_limpo, gerar_hash(senha), perfil))
        conn.commit()

    novo = buscar_por_matricula(mat, caminho)
    return True, f"Usuário {mat} ({nome_limpo}) criado com sucesso!", novo


def alterar_perfil(id_usuario: int, novo_perfil: str, caminho: Path | None = None) -> tuple[bool, str]:
    with conectar(caminho) as conn:
        conn.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (novo_perfil, id_usuario))
        conn.commit()
    return True, "Perfil atualizado com sucesso."


def alternar_ativo(id_usuario: int, caminho: Path | None = None) -> tuple[bool, str]:
    with conectar(caminho) as conn:
        cursor = conn.execute("SELECT ativo, matricula FROM usuarios WHERE id = ?", (id_usuario,))
        row = cursor.fetchone()
        if not row:
            return False, "Usuário não encontrado."
        novo_status = 0 if row["ativo"] else 1
        conn.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (novo_status, id_usuario))
        conn.commit()
        status_txt = "ativada" if novo_status else "desativada"
        return True, f"Conta {row['matricula']} foi {status_txt}."


def redefinir_senha(id_usuario: int, nova_senha: str, caminho: Path | None = None) -> tuple[bool, str]:
    if not nova_senha or len(nova_senha) < 4:
        return False, "A nova senha deve ter no mínimo 4 caracteres."
    with conectar(caminho) as conn:
        conn.execute(
            "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
            (gerar_hash(nova_senha), id_usuario),
        )
        conn.commit()
    return True, "Senha redefinida com sucesso."
