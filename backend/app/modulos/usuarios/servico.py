"""Regras de negócio de usuários e autenticação (portadas de portal/banco.py e portal/autenticacao.py)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.erros import ErroNegocio, NaoEncontrado
from app.core.rbac import PREFIXOS_MATRICULA, Perfil
from app.core.seguranca import gerar_hash, verificar_senha
from app.modulos.usuarios.esquemas import UsuarioAlterar, UsuarioCriar
from app.modulos.usuarios.modelos import Usuario


def buscar_por_matricula(sessao: Session, matricula: str) -> Usuario | None:
    mat = (matricula or "").strip().upper()
    return sessao.scalar(select(Usuario).where(Usuario.matricula == mat))


def autenticar(sessao: Session, matricula: str, senha: str) -> Usuario:
    usuario = buscar_por_matricula(sessao, matricula)
    # Mesma mensagem para matrícula inexistente e senha errada: não revela quais matrículas existem.
    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        raise ErroNegocio("Matrícula ou senha incorreta.", status=401)
    if not usuario.ativo:
        raise ErroNegocio(f"Acesso bloqueado: a conta '{usuario.matricula}' está inativa.", status=403)
    return usuario


def listar(sessao: Session) -> list[Usuario]:
    return list(sessao.scalars(select(Usuario).order_by(Usuario.matricula)))


def obter(sessao: Session, usuario_id: int) -> Usuario:
    usuario = sessao.get(Usuario, usuario_id)
    if usuario is None:
        raise NaoEncontrado("Usuário não encontrado.")
    return usuario


def proxima_matricula(sessao: Session, perfil: Perfil) -> str:
    """Próxima matrícula sequencial do prefixo do perfil (ex.: ADM-0002)."""
    prefixo = PREFIXOS_MATRICULA[perfil]
    existentes = sessao.scalars(select(Usuario.matricula).where(Usuario.matricula.like(f"{prefixo}-%")))
    numeros = []
    for mat in existentes:
        try:
            numeros.append(int(mat.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"{prefixo}-{(max(numeros, default=0) + 1):04d}"


def criar(sessao: Session, dados: UsuarioCriar) -> Usuario:
    mat = (dados.matricula or "").strip().upper() or proxima_matricula(sessao, dados.perfil)
    if sessao.scalar(select(func.count()).where(Usuario.matricula == mat)):
        raise ErroNegocio(f"A matrícula '{mat}' já está cadastrada.", status=409)
    usuario = Usuario(
        matricula=mat,
        nome=dados.nome.strip(),
        senha_hash=gerar_hash(dados.senha),
        perfil=dados.perfil.value,
        ativo=True,
    )
    sessao.add(usuario)
    sessao.flush()
    return usuario


def alterar(sessao: Session, usuario_id: int, dados: UsuarioAlterar, executor: Usuario) -> Usuario:
    usuario = obter(sessao, usuario_id)
    if usuario.id == executor.id and (dados.ativo is False or (dados.perfil and dados.perfil != usuario.perfil)):
        # Evita que o único administrador se tranque fora do sistema.
        raise ErroNegocio("Você não pode desativar nem trocar o perfil da própria conta.", status=409)
    if dados.nome is not None:
        usuario.nome = dados.nome.strip()
    if dados.perfil is not None:
        usuario.perfil = dados.perfil.value
    if dados.ativo is not None:
        usuario.ativo = dados.ativo
    sessao.flush()
    return usuario


def redefinir_senha(sessao: Session, usuario_id: int, nova_senha: str) -> None:
    usuario = obter(sessao, usuario_id)
    usuario.senha_hash = gerar_hash(nova_senha)
    sessao.flush()
