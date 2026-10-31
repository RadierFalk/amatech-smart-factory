"""
Autenticação e gestão de contas do Controle da Qualidade.

- Login só por matrícula + senha. O perfil vem do banco (tabela usuario), nunca da tela.
- Senhas guardadas somente como hash Argon2; a senha em texto puro não é gravada nem registrada.
- Vale só para a TELA. A API (api.py) e a integração com os outros setores usam as chaves
  X-API-Key e não passam por este módulo.
"""
import os

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

import banco
import permissoes
from permissoes import PermissaoNegada


# ============================================================
# CONFIGURAÇÃO
# ============================================================

TAMANHO_MINIMO_SENHA = 8
TAMANHO_MAXIMO_NOME = 80

_hasher = None
_hash_falso = None


def senha_inicial():
    """Senha das contas na criação inicial (migracao.py). Pode ser trocada por QUALIDADE_SENHA_INICIAL."""
    return os.environ.get("QUALIDADE_SENHA_INICIAL", "amatech1234")


# ============================================================
# HASH DE SENHA
# ============================================================

def _obter_hasher():
    global _hasher

    if _hasher is None:
        _hasher = PasswordHasher()

    return _hasher


def gerar_hash(senha):
    return _obter_hasher().hash(senha)


def verificar_senha(senha, senha_hash):
    """True só se a senha corresponde ao hash. Hash ausente ou inválido nunca autentica."""
    if not senha_hash or senha is None:
        return False

    try:
        return bool(_obter_hasher().verify(senha_hash, senha))
    except (VerificationError, InvalidHashError):
        return False


def _gastar_tempo_de_verificacao(senha):
    """Matrícula inexistente ou conta inativa levam o mesmo tempo de uma senha errada."""
    global _hash_falso

    if _hash_falso is None:
        _hash_falso = gerar_hash("senha-falsa-para-igualar-o-tempo")

    verificar_senha(senha, _hash_falso)


# ============================================================
# USUÁRIO DA SESSÃO
# ============================================================

def normalizar_matricula(matricula):
    return (matricula or "").strip().upper()


def _dados_do_usuario(linha):
    """Só o que a interface precisa. Nunca inclui o hash."""
    return {
        "id_usuario": linha["id_usuario"],
        "matricula": linha["matricula"],
        "nome": linha["nome_usuario"],
        "perfil": linha["perfil_usuario"],
    }


def _pode_entrar(linha):
    return (
        linha is not None
        and linha["matricula"] is not None
        and bool(linha["ativo"])
        and linha["perfil_usuario"] in permissoes.PERFIS
    )


def obter_usuario_ativo(id_usuario):
    """Usuário atual lido do banco (perfil e situação sempre atualizados), ou None se não puder mais entrar."""
    if id_usuario is None:
        return None

    linha = banco.buscar_usuario_por_id(id_usuario)

    if not _pode_entrar(linha):
        return None

    return _dados_do_usuario(linha)


def autenticar(matricula, senha):
    """
    Confere, nesta ordem: a matrícula existe, a conta está ativa, a senha bate com o hash.
    Devolve o usuário (id, matrícula, nome, perfil) ou None. Não diz qual verificação falhou.
    """
    linha = banco.buscar_usuario_por_matricula(normalizar_matricula(matricula))

    if not _pode_entrar(linha) or not linha["senha_hash"]:
        _gastar_tempo_de_verificacao(senha)
        return None

    if not verificar_senha(senha, linha["senha_hash"]):
        return None

    return _dados_do_usuario(linha)


def validar_ator(usuario):
    """
    Confirma no banco quem está pedindo uma operação, ignorando o perfil que veio no dicionário.
    Assim, ninguém consegue agir com um perfil ou uma identidade que não tem.
    """
    if not usuario or "id_usuario" not in usuario:
        raise PermissaoNegada("Sessão inválida: entre novamente no sistema.")

    atual = obter_usuario_ativo(usuario["id_usuario"])

    if atual is None:
        raise PermissaoNegada("Esta conta não está ativa.")

    return atual


# ============================================================
# GESTÃO DE CONTAS (somente Administrador)
# ============================================================

def _validar_senha(senha):
    if not senha or len(senha) < TAMANHO_MINIMO_SENHA:
        raise ValueError(f"A senha deve ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")


def _validar_perfil(perfil):
    if perfil not in permissoes.PERFIS:
        raise ValueError("Perfil inválido.")


def _ator_administrador(ator):
    atual = validar_ator(ator)
    permissoes.exigir(atual, permissoes.GERENCIAR_USUARIOS)
    return atual


def _conta_alvo(id_usuario):
    alvo = banco.buscar_usuario_por_id(id_usuario)

    if alvo is None or alvo["matricula"] is None:
        raise ValueError("Este usuário não tem acesso ao sistema.")

    return alvo


def previsao_matricula(perfil):
    """Matrícula que a próxima conta deste perfil vai receber (só para mostrar na tela)."""
    _validar_perfil(perfil)

    prefixo = permissoes.PREFIXO_MATRICULA[perfil]
    maior = 0

    for conta in banco.listar_contas():
        matricula = conta["matricula"] or ""

        if matricula.startswith(prefixo + "-") and matricula[len(prefixo) + 1:].isdigit():
            maior = max(maior, int(matricula[len(prefixo) + 1:]))

    return f"{prefixo}-{maior + 1:04d}"


def criar_usuario(ator, nome, perfil, senha):
    """Cria uma conta ativa e devolve {matricula, nome, perfil}. A matrícula é gerada pelo perfil."""
    _ator_administrador(ator)

    nome = (nome or "").strip()

    if len(nome) < 2:
        raise ValueError("Informe o nome do usuário.")

    if len(nome) > TAMANHO_MAXIMO_NOME:
        raise ValueError(f"O nome deve ter no máximo {TAMANHO_MAXIMO_NOME} caracteres.")

    _validar_perfil(perfil)
    _validar_senha(senha)

    if banco.nome_em_uso(nome):
        raise ValueError("Já existe um usuário com este nome.")

    matricula = banco.criar_conta(
        nome,
        perfil,
        permissoes.PREFIXO_MATRICULA[perfil],
        gerar_hash(senha)
    )

    return {"matricula": matricula, "nome": nome, "perfil": perfil}


def alterar_perfil(ator, id_usuario, novo_perfil):
    atual = _ator_administrador(ator)
    alvo = _conta_alvo(id_usuario)

    if alvo["id_usuario"] == atual["id_usuario"]:
        raise PermissaoNegada("Você não pode alterar o seu próprio perfil.")

    _validar_perfil(novo_perfil)

    if (
        alvo["perfil_usuario"] == permissoes.ADMINISTRADOR
        and novo_perfil != permissoes.ADMINISTRADOR
        and alvo["ativo"]
        and banco.contar_administradores_ativos() <= 1
    ):
        raise ValueError("O sistema precisa de pelo menos um Administrador ativo.")

    banco.atualizar_perfil(alvo["id_usuario"], novo_perfil)


def definir_ativo(ator, id_usuario, ativo):
    atual = _ator_administrador(ator)
    alvo = _conta_alvo(id_usuario)

    if alvo["id_usuario"] == atual["id_usuario"]:
        raise PermissaoNegada("Você não pode desativar a sua própria conta.")

    if (
        not ativo
        and alvo["perfil_usuario"] == permissoes.ADMINISTRADOR
        and alvo["ativo"]
        and banco.contar_administradores_ativos() <= 1
    ):
        raise ValueError("O sistema precisa de pelo menos um Administrador ativo.")

    banco.atualizar_ativo(alvo["id_usuario"], ativo)


def redefinir_senha(ator, id_usuario, nova_senha):
    _ator_administrador(ator)
    alvo = _conta_alvo(id_usuario)

    _validar_senha(nova_senha)

    banco.atualizar_senha_hash(alvo["id_usuario"], gerar_hash(nova_senha))
