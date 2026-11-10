"""Testes de unidade do núcleo (não precisam de banco)."""
import jwt
import pytest

from app.core.rbac import CATALOGO, Modulo, Perfil, modulos_do_perfil, tem_acesso
from app.core.seguranca import criar_token, decodificar_token, gerar_hash, verificar_senha

# Mesma matriz do README / portal/permissoes.py
MATRIZ_ESPERADA = {
    Perfil.ADMINISTRADOR: {"RAS", "QLD", "MNT", "DSH", "USR"},
    Perfil.SUPERVISOR: {"RAS", "QLD", "MNT", "DSH"},
    Perfil.OPERADOR: {"RAS", "QLD", "MNT", "DSH"},
    Perfil.INSPETOR: {"RAS", "QLD", "DSH"},
    Perfil.TECNICO: {"MNT", "DSH"},
    Perfil.ALMOXARIFE: {"RAS", "QLD"},
}


@pytest.mark.parametrize("perfil", list(Perfil))
def test_matriz_de_acesso_igual_a_do_portal(perfil):
    assert {m.sigla for m in modulos_do_perfil(perfil)} == MATRIZ_ESPERADA[perfil]


def test_somente_administrador_acessa_usuarios():
    for perfil in Perfil:
        assert tem_acesso(perfil, Modulo.USUARIOS) == (perfil is Perfil.ADMINISTRADOR)


def test_catalogo_tem_os_cinco_modulos():
    assert set(CATALOGO) == set(Modulo)


def test_perfil_desconhecido_e_rejeitado():
    # O portal antigo transformava qualquer texto desconhecido em Operador; aqui é erro.
    with pytest.raises(ValueError):
        tem_acesso("Visitante", Modulo.DASHBOARD)


def test_hash_argon2_confere_e_rejeita_senha_errada():
    h = gerar_hash("amatech1234")
    assert h.startswith("$argon2")
    assert verificar_senha("amatech1234", h)
    assert not verificar_senha("outra", h)


@pytest.mark.parametrize("gravado", ["amatech1234", "sha256$abc", "", "e" * 64])
def test_nao_aceita_texto_puro_nem_hash_legado(gravado):
    # O portal antigo aceitava senha == hash gravado (texto puro). A migração converte para Argon2.
    assert not verificar_senha("amatech1234", gravado)


def test_token_ida_e_volta():
    token = criar_token("42", {"perfil": Perfil.TECNICO.value})
    corpo = decodificar_token(token)
    assert corpo["sub"] == "42"
    assert corpo["perfil"] == "Técnico de Manutenção"


def test_token_adulterado_e_rejeitado():
    token = criar_token("1")
    with pytest.raises(jwt.PyJWTError):
        decodificar_token(token[:-2] + ("AA" if not token.endswith("AA") else "BB"))
