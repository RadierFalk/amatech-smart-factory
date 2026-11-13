"""Testes de unidade do núcleo (não precisam de banco)."""
import jwt
import pytest

from app.core.rbac import CATALOGO, Modulo, Perfil, modulos_do_perfil, tem_acesso
from app.core.seguranca import criar_token, decodificar_token, gerar_hash, verificar_senha

# Mesma matriz do README / portal/permissoes.py
MATRIZ_ESPERADA = {
    Perfil.ADMINISTRADOR: {"RAS", "QLD", "MNT", "DSH", "USR", "AUD"},
    Perfil.SUPERVISOR: {"RAS", "QLD", "MNT", "DSH", "AUD"},
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


# ---------------------------------------------------------------- configuração de produção


@pytest.mark.parametrize(
    ("segredo", "chave", "trecho"),
    [
        ("dev-inseguro-troque-em-producao-0123456789", "chave-boa-123", "AMATECH_JWT_SEGREDO"),
        ("troque-este-segredo-com-mais-de-32-caracteres", "chave-boa-123", "AMATECH_JWT_SEGREDO"),
        ("curto-demais", "chave-boa-123", "32 caracteres"),
        ("x" * 40, "amatech-iot-demo", "AMATECH_CHAVE_MAQUINAS"),
        ("x" * 40, "troque-esta-chave", "AMATECH_CHAVE_MAQUINAS"),
    ],
)
def test_producao_recusa_segredos_de_exemplo(segredo, chave, trecho):
    from app.core.config import Configuracao

    cfg = Configuracao(ambiente="producao", jwt_segredo=segredo, chave_maquinas=chave)
    with pytest.raises(RuntimeError, match=trecho):
        cfg.validar_producao()


def test_producao_aceita_segredos_proprios_e_desenvolvimento_nao_valida():
    from app.core.config import Configuracao

    Configuracao(ambiente="producao", jwt_segredo="y" * 48, chave_maquinas="chave-da-fabrica-7").validar_producao()
    Configuracao(ambiente="desenvolvimento").validar_producao()  # padrões de desenvolvimento valem fora de produção
