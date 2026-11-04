"""
Serviço de Autenticação e Gestão de Sessão do ERP AMATECH.
Valida credenciais corporativas, verifica se o colaborador está ativo
e armazena a sessão com perfil e permissões.
"""
from pathlib import Path
from typing import Any

from banco import buscar_por_matricula, verificar_hash


def autenticar(matricula: str, senha: str, caminho_banco: Path | None = None) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Autentica o colaborador pela matrícula e senha.
    Bloqueia usuários desativados (ativo = 0).
    """
    mat = (matricula or "").strip().upper()
    if not mat:
        return False, "Informe a matrícula funcional.", None
    if not senha:
        return False, "Informe a senha de acesso.", None

    usuario = buscar_por_matricula(mat, caminho_banco)
    if not usuario:
        return False, "Matrícula não cadastrada no ERP.", None

    if not usuario.get("ativo"):
        return False, f"Acesso bloqueado: a conta '{mat}' ({usuario.get('nome')}) está inativa.", None

    if not verificar_hash(senha, usuario.get("senha_hash", "")):
        return False, "Senha incorreta. Verifique suas credenciais.", None

    # Remove o hash da sessão por segurança
    dados_sessao = {
        "id": usuario["id"],
        "matricula": usuario["matricula"],
        "nome": usuario["nome"],
        "perfil": usuario["perfil"],
        "ativo": usuario["ativo"],
        "criado_em": usuario["criado_em"],
    }
    return True, "Autenticação realizada com sucesso.", dados_sessao
