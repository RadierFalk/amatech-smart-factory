"""
Testes automatizados do Portal ERP AMATECH.
Valida:
1. Segregação rigorosa de personas e visibilidade de módulos (RBAC).
2. Autenticação corporativa com hash e bloqueio de usuários inativos.
3. Operações do Módulo 4 (Gestão de Usuários e Acessos).
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent.parent
PORTAL_DIR = RAIZ / "portal"
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(PORTAL_DIR))

import autenticacao
import banco
import permissoes
from permissoes import (
    ADMINISTRADOR,
    ALMOXARIFE,
    INSPETOR,
    MODULO_MANUTENCAO,
    MODULO_QUALIDADE,
    MODULO_RASTREABILIDADE,
    MODULO_USUARIOS,
    OPERADOR,
    TECNICO,
    modulos_permitidos,
    tem_acesso_modulo,
)


@pytest.fixture
def banco_teste(tmp_path):
    caminho = tmp_path / "erp_teste.db"
    banco.inicializar_banco(caminho)
    return caminho


# ============================================================
# 1. MATRIZ DE PERSONAS E VISIBILIDADE DE MÓDULOS (RBAC)
# ============================================================

def test_administrador_acessa_todos_os_quatro_modulos():
    admin = {"perfil": ADMINISTRADOR}
    ids = {m.id for m in modulos_permitidos(admin)}
    assert ids == {MODULO_RASTREABILIDADE, MODULO_QUALIDADE, MODULO_MANUTENCAO, MODULO_USUARIOS}
    assert tem_acesso_modulo(admin, MODULO_USUARIOS) is True


def test_inspetor_acessa_apenas_rastreabilidade_e_qualidade():
    inspetor = {"perfil": INSPETOR}
    ids = {m.id for m in modulos_permitidos(inspetor)}
    assert ids == {MODULO_RASTREABILIDADE, MODULO_QUALIDADE}
    assert tem_acesso_modulo(inspetor, MODULO_MANUTENCAO) is False
    assert tem_acesso_modulo(inspetor, MODULO_USUARIOS) is False


def test_operador_acessa_rastreabilidade_qualidade_e_manutencao():
    operador = {"perfil": OPERADOR}
    ids = {m.id for m in modulos_permitidos(operador)}
    assert ids == {MODULO_RASTREABILIDADE, MODULO_QUALIDADE, MODULO_MANUTENCAO}
    assert tem_acesso_modulo(operador, MODULO_USUARIOS) is False


def test_tecnico_acessa_estritamente_manutencao():
    tecnico = {"perfil": TECNICO}
    ids = {m.id for m in modulos_permitidos(tecnico)}
    assert ids == {MODULO_MANUTENCAO}
    assert tem_acesso_modulo(tecnico, MODULO_RASTREABILIDADE) is False
    assert tem_acesso_modulo(tecnico, MODULO_QUALIDADE) is False
    assert tem_acesso_modulo(tecnico, MODULO_USUARIOS) is False


def test_almoxarife_acessa_rastreabilidade_e_qualidade():
    almoxarife = {"perfil": ALMOXARIFE}
    ids = {m.id for m in modulos_permitidos(almoxarife)}
    assert ids == {MODULO_RASTREABILIDADE, MODULO_QUALIDADE}
    assert tem_acesso_modulo(almoxarife, MODULO_MANUTENCAO) is False
    assert tem_acesso_modulo(almoxarife, MODULO_USUARIOS) is False


def test_usuario_sem_perfil_nao_acessa_nada():
    assert modulos_permitidos(None) == []
    assert modulos_permitidos({}) == []
    assert tem_acesso_modulo({}, MODULO_RASTREABILIDADE) is False


# ============================================================
# 2. AUTENTICAÇÃO E SESSÃO
# ============================================================

def test_autenticar_usuarios_iniciais_com_sucesso(banco_teste):
    for mat in ("ADM-0001", "QUA-0001", "OPE-0001", "TEC-2001", "ALM-0001"):
        sucesso, msg, usuario = autenticacao.autenticar(mat, "amatech1234", caminho_banco=banco_teste)
        assert sucesso is True
        assert usuario is not None
        assert usuario["matricula"] == mat
        assert "senha_hash" not in usuario


def test_rejeitar_senha_incorreta(banco_teste):
    sucesso, msg, usuario = autenticacao.autenticar("ADM-0001", "senha-errada", caminho_banco=banco_teste)
    assert sucesso is False
    assert usuario is None
    assert "Senha incorreta" in msg


def test_bloquear_usuario_desativado(banco_teste):
    user = banco.buscar_por_matricula("OPE-0001", banco_teste)
    banco.alternar_ativo(user["id"], banco_teste)

    sucesso, msg, usuario = autenticacao.autenticar("OPE-0001", "amatech1234", caminho_banco=banco_teste)
    assert sucesso is False
    assert usuario is None
    assert "bloqueado" in msg.lower() or "inativa" in msg.lower()


# ============================================================
# 3. MÓDULO 4: GESTÃO DE USUÁRIOS
# ============================================================

def test_criar_novo_usuario_com_matricula_automatica(banco_teste):
    sucesso, msg, novo = banco.criar_usuario("Mariana Ferreira", INSPETOR, "senha123", caminho=banco_teste)
    assert sucesso is True
    assert novo is not None
    assert novo["matricula"] == "QUA-0002"
    assert novo["nome"] == "Mariana Ferreira"
    assert novo["perfil"] == INSPETOR

    # Consegue autenticar o novo usuário
    ok, _, dados = autenticacao.autenticar("QUA-0002", "senha123", caminho_banco=banco_teste)
    assert ok is True
    assert dados["nome"] == "Mariana Ferreira"


def test_alterar_perfil_modifica_acessos_imediatamente(banco_teste):
    user = banco.buscar_por_matricula("TEC-2001", banco_teste)
    # Inicialmente técnico só vê manutenção
    assert {m.id for m in modulos_permitidos(user)} == {MODULO_MANUTENCAO}

    # Promover a Administrador
    banco.alterar_perfil(user["id"], ADMINISTRADOR, banco_teste)
    atualizado = banco.buscar_por_id(user["id"], banco_teste)
    assert atualizado["perfil"] == ADMINISTRADOR
    assert {m.id for m in modulos_permitidos(atualizado)} == {
        MODULO_RASTREABILIDADE, MODULO_QUALIDADE, MODULO_MANUTENCAO, MODULO_USUARIOS
    }


def test_redefinir_senha_usuario(banco_teste):
    user = banco.buscar_por_matricula("ALM-0001", banco_teste)
    sucesso, msg = banco.redefinir_senha(user["id"], "nova_senha_99", banco_teste)
    assert sucesso is True

    # Antiga falha, nova funciona
    assert autenticacao.autenticar("ALM-0001", "amatech1234", caminho_banco=banco_teste)[0] is False
    assert autenticacao.autenticar("ALM-0001", "nova_senha_99", caminho_banco=banco_teste)[0] is True
