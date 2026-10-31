"""
Testes do login (autenticacao.py), da gestão de contas e da sessão (sessao.py).
Rodar:  python -m pytest tests -q
"""
import sqlite3

import pytest

import autenticacao
import banco
import permissoes
import sessao
from conftest import SENHA_INICIAL, ler_tabela
from permissoes import PermissaoNegada

PERFIL_DE = {
    "ADM-0001": "Administrador",
    "OPE-0001": "Operador",
    "ALM-0001": "Almoxarife",
    "QUA-0001": "Inspetor de Qualidade",
}


# ============================================================
# AUTENTICAÇÃO
# ============================================================

def test_login_com_matricula_e_senha_corretas(entrar):
    usuario = entrar("ADM-0001")

    assert usuario["matricula"] == "ADM-0001"
    assert usuario["perfil"] == "Administrador"
    assert usuario["nome"] == "Ana Souza"
    assert "senha_hash" not in usuario and "senha" not in usuario


def test_as_quatro_contas_entram_com_a_mesma_senha_inicial(entrar):
    for matricula, perfil in PERFIL_DE.items():
        assert entrar(matricula)["perfil"] == perfil


def test_senha_incorreta(banco_migrado):
    for matricula in PERFIL_DE:
        assert autenticacao.autenticar(matricula, "senha-errada") is None
        assert autenticacao.autenticar(matricula, "") is None
        assert autenticacao.autenticar(matricula, None) is None


def test_matricula_inexistente(banco_migrado):
    assert autenticacao.autenticar("XXX-9999", SENHA_INICIAL) is None
    assert autenticacao.autenticar("", SENHA_INICIAL) is None
    assert autenticacao.autenticar(None, SENHA_INICIAL) is None
    assert autenticacao.autenticar("Ana Souza", SENHA_INICIAL) is None   # nome não é login


def test_matricula_aceita_minusculas_e_espacos(banco_migrado):
    assert autenticacao.autenticar("  adm-0001 ", SENHA_INICIAL)["matricula"] == "ADM-0001"


def test_matricula_nao_e_a_senha(banco_migrado):
    for matricula in PERFIL_DE:
        assert autenticacao.autenticar(matricula, matricula) is None


def test_conta_inativa_nao_entra(banco_migrado, entrar):
    operador = entrar("OPE-0001")
    banco.atualizar_ativo(operador["id_usuario"], False)

    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL) is None


def test_usuario_historico_sem_matricula_nao_entra(banco_migrado):
    visitante = next(c for c in banco.listar_contas() if c["nome_usuario"] == "Visitante Antigo")

    assert visitante["matricula"] is None and not visitante["ativo"]
    assert autenticacao.autenticar("Visitante Antigo", SENHA_INICIAL) is None
    assert autenticacao.autenticar(str(visitante["id_usuario"]), SENHA_INICIAL) is None
    assert autenticacao.obter_usuario_ativo(visitante["id_usuario"]) is None


def test_conta_ativa_sem_hash_nao_entra(banco_migrado):
    conexao = sqlite3.connect(banco_migrado)
    conexao.execute("UPDATE usuario SET senha_hash = NULL WHERE matricula = 'QUA-0001'")
    conexao.commit()
    conexao.close()

    assert autenticacao.autenticar("QUA-0001", SENHA_INICIAL) is None


def test_perfil_vem_do_banco(banco_migrado, entrar):
    operador = entrar("OPE-0001")
    assert operador["perfil"] == "Operador"

    banco.atualizar_perfil(operador["id_usuario"], "Almoxarife")

    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL)["perfil"] == "Almoxarife"


def test_hash_de_senha(banco_migrado):
    primeiro = autenticacao.gerar_hash("minha-senha-123")
    segundo = autenticacao.gerar_hash("minha-senha-123")

    assert primeiro.startswith("$argon2") and "minha-senha-123" not in primeiro
    assert primeiro != segundo   # cada hash tem o seu sal

    assert autenticacao.verificar_senha("minha-senha-123", primeiro) is True
    assert autenticacao.verificar_senha("outra-senha", primeiro) is False
    assert autenticacao.verificar_senha("minha-senha-123", None) is False
    assert autenticacao.verificar_senha("minha-senha-123", "isto-nao-e-um-hash") is False


# ============================================================
# GESTÃO DE CONTAS
# ============================================================

def test_administrador_cria_usuario_com_matricula_do_perfil(entrar):
    admin = entrar("ADM-0001")

    novo = autenticacao.criar_usuario(admin, "  Paulo Lima ", "Operador", "senha-do-paulo")
    assert novo == {"matricula": "OPE-0002", "nome": "Paulo Lima", "perfil": "Operador"}

    outro_admin = autenticacao.criar_usuario(admin, "Rita Costa", "Administrador", "senha-da-rita")
    assert outro_admin["matricula"] == "ADM-0002"

    assert autenticacao.autenticar("OPE-0002", "senha-do-paulo")["perfil"] == "Operador"
    assert autenticacao.autenticar("ADM-0002", "senha-da-rita")["perfil"] == "Administrador"
    assert autenticacao.autenticar("OPE-0002", SENHA_INICIAL) is None

    assert autenticacao.previsao_matricula("Operador") == "OPE-0003"


def test_so_o_administrador_gerencia_usuarios(entrar):
    admin = entrar("ADM-0001")
    alvo = entrar("ALM-0001")

    for matricula in ("OPE-0001", "ALM-0001", "QUA-0001"):
        comum = entrar(matricula)

        with pytest.raises(PermissaoNegada):
            autenticacao.criar_usuario(comum, "Intruso", "Administrador", "senha-qualquer")
        with pytest.raises(PermissaoNegada):
            autenticacao.alterar_perfil(comum, alvo["id_usuario"], "Administrador")
        with pytest.raises(PermissaoNegada):
            autenticacao.definir_ativo(comum, alvo["id_usuario"], False)
        with pytest.raises(PermissaoNegada):
            autenticacao.redefinir_senha(comum, alvo["id_usuario"], "senha-nova-123")

    # nada mudou
    assert autenticacao.autenticar("ALM-0001", SENHA_INICIAL)["perfil"] == "Almoxarife"
    assert len([c for c in banco.listar_contas() if c["matricula"]]) == 4
    assert admin["perfil"] == "Administrador"


def test_criar_usuario_valida_os_dados(entrar):
    admin = entrar("ADM-0001")

    with pytest.raises(ValueError):
        autenticacao.criar_usuario(admin, "Fulano", "Operador", "curta")           # senha curta
    with pytest.raises(ValueError):
        autenticacao.criar_usuario(admin, "Fulano", "Gerente Geral", "senha-valida-1")   # perfil inexistente
    with pytest.raises(ValueError):
        autenticacao.criar_usuario(admin, "", "Operador", "senha-valida-1")        # sem nome
    with pytest.raises(ValueError):
        autenticacao.criar_usuario(admin, "ana souza", "Operador", "senha-valida-1")   # nome já usado

    assert len(banco.listar_contas()) == 5   # nenhuma conta foi criada


def test_nao_altera_o_proprio_perfil_nem_se_desativa(entrar):
    admin = entrar("ADM-0001")

    with pytest.raises(PermissaoNegada):
        autenticacao.alterar_perfil(admin, admin["id_usuario"], "Operador")
    with pytest.raises(PermissaoNegada):
        autenticacao.definir_ativo(admin, admin["id_usuario"], False)

    assert autenticacao.autenticar("ADM-0001", SENHA_INICIAL)["perfil"] == "Administrador"


def test_administrador_muda_o_perfil_e_desativa_outras_contas(entrar):
    admin = entrar("ADM-0001")
    operador = entrar("OPE-0001")

    autenticacao.alterar_perfil(admin, operador["id_usuario"], "Inspetor de Qualidade")
    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL)["perfil"] == "Inspetor de Qualidade"   # matrícula não muda

    autenticacao.definir_ativo(admin, operador["id_usuario"], False)
    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL) is None

    autenticacao.definir_ativo(admin, operador["id_usuario"], True)
    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL) is not None


def test_nao_ha_como_gerenciar_usuario_sem_acesso(entrar):
    admin = entrar("ADM-0001")
    visitante = next(c for c in banco.listar_contas() if c["nome_usuario"] == "Visitante Antigo")

    with pytest.raises(ValueError):
        autenticacao.alterar_perfil(admin, visitante["id_usuario"], "Administrador")
    with pytest.raises(ValueError):
        autenticacao.definir_ativo(admin, visitante["id_usuario"], True)
    with pytest.raises(ValueError):
        autenticacao.redefinir_senha(admin, visitante["id_usuario"], "senha-nova-123")


def test_redefinir_senha(entrar):
    admin = entrar("ADM-0001")
    alvo = entrar("QUA-0001")

    with pytest.raises(ValueError):
        autenticacao.redefinir_senha(admin, alvo["id_usuario"], "curta")

    autenticacao.redefinir_senha(admin, alvo["id_usuario"], "senha-nova-123")

    assert autenticacao.autenticar("QUA-0001", "senha-nova-123") is not None
    assert autenticacao.autenticar("QUA-0001", SENHA_INICIAL) is None
    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL) is not None   # as outras contas não mudaram


def test_perfil_forjado_no_dicionario_e_ignorado(entrar):
    operador = entrar("OPE-0001")
    forjado = dict(operador, perfil="Administrador")

    with pytest.raises(PermissaoNegada):
        autenticacao.criar_usuario(forjado, "Intruso", "Administrador", "senha-qualquer")

    with pytest.raises(PermissaoNegada):
        autenticacao.criar_usuario(None, "Intruso", "Administrador", "senha-qualquer")


# ============================================================
# SESSÃO
# ============================================================

def test_sessao_guarda_so_o_id_e_o_horario(entrar):
    usuario = entrar("OPE-0001")
    estado = {}

    sessao.iniciar(usuario, estado, agora=1000)

    assert set(estado[sessao.CHAVE]) == {"id_usuario", "ultimo_acesso"}
    assert SENHA_INICIAL not in str(estado) and "argon2" not in str(estado)
    assert sessao.usuario_atual(estado, agora=1010)["matricula"] == "OPE-0001"


def test_sem_sessao_nao_ha_usuario(banco_migrado):
    assert sessao.usuario_atual({}, agora=1) is None


def test_logout_limpa_a_sessao(entrar):
    usuario = entrar("OPE-0001")
    estado = {"qualquer_coisa": 1}
    sessao.iniciar(usuario, estado, agora=1000)

    sessao.encerrar(estado)

    assert estado == {}
    assert sessao.usuario_atual(estado, agora=1001) is None


def test_sessao_expira_por_inatividade_e_renova_com_o_uso(entrar):
    usuario = entrar("OPE-0001")
    limite = sessao.MINUTOS_DE_INATIVIDADE * 60
    estado = {}
    sessao.iniciar(usuario, estado, agora=0)

    # o uso renova o prazo
    assert sessao.usuario_atual(estado, agora=limite - 1) is not None
    assert sessao.usuario_atual(estado, agora=2 * limite - 2) is not None

    # parado por mais que o limite: expira, e a sessão antiga não volta a valer
    assert sessao.usuario_atual(estado, agora=2 * limite - 2 + limite + 1) is None
    assert sessao.CHAVE not in estado and sessao.CHAVE_AVISO in estado
    assert sessao.usuario_atual(estado, agora=2 * limite - 2 + limite + 2) is None


def test_conta_desativada_perde_a_sessao_na_hora(entrar):
    admin = entrar("ADM-0001")
    operador = entrar("OPE-0001")
    estado = {}
    sessao.iniciar(operador, estado, agora=0)
    assert sessao.usuario_atual(estado, agora=1) is not None

    autenticacao.definir_ativo(admin, operador["id_usuario"], False)

    assert sessao.usuario_atual(estado, agora=2) is None
    assert estado.get(sessao.CHAVE) is None


def test_mudanca_de_perfil_vale_na_sessao_aberta(entrar):
    admin = entrar("ADM-0001")
    operador = entrar("OPE-0001")
    estado = {}
    sessao.iniciar(operador, estado, agora=0)

    autenticacao.alterar_perfil(admin, operador["id_usuario"], "Almoxarife")

    assert sessao.usuario_atual(estado, agora=1)["perfil"] == "Almoxarife"
