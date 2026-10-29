"""ServicoAutenticacao: login, hash de senha, permissões por perfil e gestão de usuários (RF18, RF19, RNF07)."""
import hashlib
import hmac
import os
import sqlite3

from acesso_dados import Repositorio
from modelos import Perfil, Usuario
from servicos.erros import ErroValidacao

ITERACOES = 200_000

# Permissões fixas no código (decisão da OA2: não há tabela de permissões). Chave = nome do perfil.
OPERADOR = "Operador de estação"
INSPETOR = "Inspetor de qualidade"
MANUTENCAO = "Manutenção"
SUPERVISOR = "Supervisor de produção"
GESTOR = "Gestor/Diretoria"
ADMINISTRADOR = "Administrador"

PERMISSOES = {
    "painel": {SUPERVISOR, GESTOR},
    "producao": {OPERADOR, SUPERVISOR},
    "metas": {SUPERVISOR},
    "defeitos": {OPERADOR, INSPETOR, SUPERVISOR},
    "retrabalho": {INSPETOR, SUPERVISOR},
    "paradas": {MANUTENCAO, SUPERVISOR},
    "perdas": {SUPERVISOR},
    "importacao": {SUPERVISOR},
    "historico": {SUPERVISOR, GESTOR},
    "limites": {SUPERVISOR, ADMINISTRADOR},
    "cadastros": {ADMINISTRADOR},
    "usuarios": {ADMINISTRADOR},
}


class ServicoAutenticacao:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()

    # ------------------------------------------------------------ senhas (RNF07)
    @staticmethod
    def gerar_hash(senha):
        """PBKDF2-SHA256 com sal aleatório: a mesma senha gera hashes diferentes, e a senha nunca é guardada."""
        sal = os.urandom(16)
        resumo = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
        return f"pbkdf2_sha256${ITERACOES}${sal.hex()}${resumo.hex()}"

    @staticmethod
    def conferir_senha(senha, senha_hash):
        try:
            _, iteracoes, sal, resumo = senha_hash.split("$")
        except (AttributeError, ValueError):
            return False
        calculado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), int(iteracoes))
        return hmac.compare_digest(calculado.hex(), resumo)

    # ------------------------------------------------------------ login e permissões
    def autenticar(self, login, senha):
        """Devolve o Usuario se login e senha conferem e o usuário está ativo; senão, None."""
        linha = self.repo.consultar_um(
            """SELECT u.*, p.nome AS perfil_nome, p.descricao AS perfil_descricao
               FROM usuario u JOIN perfil p ON p.id_perfil = u.id_perfil WHERE u.login = ?""",
            ((login or "").strip().lower(),))
        if not linha or not linha["ativo"] or not self.conferir_senha(senha or "", linha["senha_hash"]):
            return None
        return self._usuario(linha)

    @staticmethod
    def tem_permissao(usuario, funcao):
        return usuario is not None and usuario.perfil.nome in PERMISSOES.get(funcao, set())

    @staticmethod
    def _usuario(linha):
        return Usuario(nome=linha["nome"], login=linha["login"], ativo=bool(linha["ativo"]), id=linha["id_usuario"],
                       perfil=Perfil(nome=linha["perfil_nome"], descricao=linha["perfil_descricao"],
                                     id=linha["id_perfil"]))

    # ------------------------------------------------------------ gestão de usuários (T10)
    def listar_perfis(self):
        return self.repo.consultar("SELECT * FROM perfil ORDER BY id_perfil")

    def listar_usuarios(self):
        return self.repo.consultar(
            """SELECT u.id_usuario, u.nome, u.login, p.nome AS perfil, u.ativo, u.criado_em
               FROM usuario u JOIN perfil p ON p.id_perfil = u.id_perfil ORDER BY u.nome""")

    def criar_usuario(self, nome, login, id_perfil, senha):
        problemas = []
        nome, login = (nome or "").strip(), (login or "").strip().lower()
        if not nome:
            problemas.append(("nome", "Informe o nome."))
        if not login or " " in login:
            problemas.append(("login", "Informe um login sem espaços."))
        if not id_perfil:
            problemas.append(("perfil", "Escolha o perfil."))
        problemas += self._validar_senha(senha)
        if problemas:
            raise ErroValidacao(problemas)
        try:
            return self.repo.executar("INSERT INTO usuario (nome, login, senha_hash, id_perfil) VALUES (?, ?, ?, ?)",
                                      (nome, login, self.gerar_hash(senha), id_perfil))
        except sqlite3.IntegrityError as erro:
            raise ErroValidacao([("login", f"Já existe um usuário com o login '{login}'.")]) from erro

    def redefinir_senha(self, id_usuario, nova_senha):
        problemas = self._validar_senha(nova_senha)
        if problemas:
            raise ErroValidacao(problemas)
        self.repo.executar("UPDATE usuario SET senha_hash = ? WHERE id_usuario = ?",
                           (self.gerar_hash(nova_senha), id_usuario))

    def alterar_ativo(self, id_usuario, ativo):
        """Usuários são desativados, nunca apagados: assim não se perde quem lançou cada dado."""
        self.repo.executar("UPDATE usuario SET ativo = ? WHERE id_usuario = ?", (1 if ativo else 0, id_usuario))

    @staticmethod
    def _validar_senha(senha):
        if not senha or len(senha) < 6:
            return [("senha", "A senha deve ter pelo menos 6 caracteres.")]
        return []
