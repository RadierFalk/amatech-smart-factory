"""
Serviço de Autenticação, Sessão e Controle de Acesso Baseado em Perfil (RBAC).
Atende aos requisitos F01, F15, RN01 e RN07.
"""
import hashlib
from typing import Any

from config import PERFIS_USUARIO
from database import get_db
from models.entities import Usuario


# Mapa de permissões de telas por perfil (RN01)
PERMISSOES_POR_PERFIL: dict[str, list[str]] = {
    "OPERADOR": [
        "painel_maquinas",
        "abrir_chamado",
        "meus_chamados",
    ],
    "TECNICO": [
        "painel_maquinas",
        "fila_chamados",
        "preventiva",
        "ordem_servico",
        "dashboard",
        "historico",
    ],
    "GESTOR": [
        "painel_maquinas",
        "abrir_chamado",
        "meus_chamados",
        "fila_chamados",
        "preventiva",
        "ordem_servico",
        "dashboard",
        "historico",
        "cadastros",
        "auditoria",
    ],
}


def gerar_hash_senha(senha: str) -> str:
    """Gera hash SHA-256 para armazenamento seguro de senhas."""
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def verificar_senha(senha_informada: str, senha_armazenada: str) -> bool:
    """
    Valida a senha informada contra o valor armazenado no banco.
    Aceita texto plano ('123456' ou 'amatech123' para contas demo) ou hash SHA-256/MD5.
    """
    if not senha_informada or not senha_armazenada:
        return False
    if senha_informada == senha_armazenada:
        return True
    if senha_armazenada == "123456" and senha_informada == "amatech123":
        return True
    sha256_hex = gerar_hash_senha(senha_informada)
    if sha256_hex == senha_armazenada:
        return True
    md5_hex = hashlib.md5(senha_informada.encode("utf-8")).hexdigest()
    return md5_hex == senha_armazenada


def autenticar_usuario(matricula: str, senha: str, db_path: str | None = None) -> Usuario:
    """
    Autentica um colaborador pela matrícula e senha.
    Aplica RN01: bloqueia usuários inativos (ativo = 0).
    """
    matricula_limpa = (matricula or "").strip().upper()
    if not matricula_limpa or not senha:
        raise ValueError("Informe a matrícula e a senha para autenticar.")

    with get_db(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, nome, matricula, senha_hash, perfil, ativo, criado_em
            FROM usuarios
            WHERE UPPER(matricula) = ?
            """,
            (matricula_limpa,),
        ).fetchone()

        if not row:
            raise ValueError("Matrícula não encontrada no sistema.")

        if not bool(row["ativo"]):
            raise PermissionError(
                f"Acesso bloqueado (RN01): O usuário '{row['nome']}' ({row['matricula']}) está INATIVO."
            )

        if not verificar_senha(senha, row["senha_hash"]):
            raise ValueError("Senha incorreta. Verifique suas credenciais.")

        return Usuario(
            id=row["id"],
            nome=row["nome"],
            matricula=row["matricula"],
            perfil=row["perfil"],
            ativo=bool(row["ativo"]),
            criado_em=str(row["criado_em"]) if row["criado_em"] else None,
        )


def verificar_permissao(perfil: str, codigo_tela: str) -> bool:
    """Verifica se o perfil possui permissão para acessar determinada tela (RN01)."""
    telas_permitidas = PERMISSOES_POR_PERFIL.get((perfil or "").upper(), [])
    return codigo_tela in telas_permitidas


def listar_usuarios(apenas_ativos: bool = False, db_path: str | None = None) -> list[dict[str, Any]]:
    """Lista todos os usuários cadastrados (F15)."""
    query = """
        SELECT id, nome, matricula, perfil, ativo, criado_em
        FROM usuarios
    """
    params: tuple = ()
    if apenas_ativos:
        query += " WHERE ativo = 1"
    query += " ORDER BY perfil, nome ASC"

    with get_db(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def criar_usuario(
    nome: str,
    matricula: str,
    senha: str,
    perfil: str,
    db_path: str | None = None,
) -> int:
    """Cria um novo usuário validando unicidade de matrícula e perfil (F15)."""
    nome_limpo = (nome or "").strip()
    matricula_limpa = (matricula or "").strip().upper()
    perfil_limpo = (perfil or "").strip().upper()

    if not nome_limpo:
        raise ValueError("O nome do colaborador é obrigatório.")
    if not matricula_limpa:
        raise ValueError("A matrícula é obrigatória.")
    if not senha or len(senha.strip()) < 4:
        raise ValueError("A senha deve ter pelo menos 4 caracteres.")
    if perfil_limpo not in PERFIS_USUARIO:
        raise ValueError(f"Perfil inválido. Escolha entre: {', '.join(PERFIS_USUARIO)}.")

    with get_db(db_path) as conn:
        existente = conn.execute(
            "SELECT id FROM usuarios WHERE UPPER(matricula) = ?",
            (matricula_limpa,),
        ).fetchone()
        if existente:
            raise ValueError(f"Já existe um usuário cadastrado com a matrícula '{matricula_limpa}'.")

        cursor = conn.execute(
            """
            INSERT INTO usuarios (nome, matricula, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (nome_limpo, matricula_limpa, senha.strip(), perfil_limpo),
        )
        return int(cursor.lastrowid)


def alternar_status_usuario(usuario_id: int, ativo: bool, db_path: str | None = None) -> None:
    """Realiza ativação ou inativação lógica (Soft Delete - RN07) de um usuário."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "UPDATE usuarios SET ativo = ? WHERE id = ?",
            (1 if ativo else 0, usuario_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Usuário ID {usuario_id} não encontrado.")
