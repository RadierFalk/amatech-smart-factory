"""Testes da API de autenticação e usuários (precisam de PostgreSQL; ver conftest.py)."""
from app.core.rbac import Perfil
from tests.conftest import SENHA


def test_saude(cliente):
    r = cliente.get("/api/saude")
    assert r.status_code == 200
    assert r.json()["api"] == "ok"


def test_login_ok_devolve_token_e_usuario(cliente, criar_usuario):
    criar_usuario("ADM-0001", Perfil.ADMINISTRADOR)
    r = cliente.post("/api/auth/login", json={"matricula": "adm-0001", "senha": SENHA})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario"]["matricula"] == "ADM-0001"
    assert "senha_hash" not in corpo["usuario"]


def test_login_senha_errada_e_matricula_inexistente_tem_mesma_mensagem(cliente, criar_usuario):
    criar_usuario("OPE-0001", Perfil.OPERADOR)
    errada = cliente.post("/api/auth/login", json={"matricula": "OPE-0001", "senha": "x"})
    inexistente = cliente.post("/api/auth/login", json={"matricula": "OPE-9999", "senha": "x"})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()


def test_conta_inativa_nao_entra(cliente, criar_usuario):
    criar_usuario("OPE-0002", Perfil.OPERADOR, ativo=False)
    r = cliente.post("/api/auth/login", json={"matricula": "OPE-0002", "senha": SENHA})
    assert r.status_code == 403


def test_me_e_modulos_por_persona(cliente, criar_usuario, token_de):
    criar_usuario("TEC-2001", Perfil.TECNICO)
    h = token_de("TEC-2001")
    assert cliente.get("/api/auth/me", headers=h).json()["perfil"] == "Técnico de Manutenção"
    siglas = {m["sigla"] for m in cliente.get("/api/auth/modulos", headers=h).json()}
    assert siglas == {"MNT", "DSH"}


def test_sem_token_e_token_invalido_dao_401(cliente):
    assert cliente.get("/api/auth/me").status_code == 401
    assert cliente.get("/api/auth/me", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_conta_desativada_perde_acesso_mesmo_com_token(cliente, sessao, criar_usuario, token_de):
    u = criar_usuario("QUA-0001", Perfil.INSPETOR)
    h = token_de("QUA-0001")
    u.ativo = False
    sessao.commit()
    assert cliente.get("/api/auth/me", headers=h).status_code == 401


def test_nao_administrador_nao_acessa_usuarios(cliente, criar_usuario, token_de):
    criar_usuario("GES-0001", Perfil.SUPERVISOR)
    assert cliente.get("/api/usuarios", headers=token_de("GES-0001")).status_code == 403


def test_crud_de_usuarios_pelo_administrador(cliente, criar_usuario, token_de):
    criar_usuario("ADM-0001", Perfil.ADMINISTRADOR)
    h = token_de("ADM-0001")

    novo = cliente.post(
        "/api/usuarios", headers=h, json={"nome": "Paula", "perfil": "Almoxarife", "senha": "senha-forte-1"}
    )
    assert novo.status_code == 201, novo.text
    assert novo.json()["matricula"] == "ALM-0001"  # gerada pelo prefixo do perfil
    uid = novo.json()["id"]

    duplicado = cliente.post(
        "/api/usuarios",
        headers=h,
        json={"nome": "X", "perfil": "Almoxarife", "senha": "senha-forte-1", "matricula": "alm-0001"},
    )
    assert duplicado.status_code == 409

    alterado = cliente.patch(f"/api/usuarios/{uid}", headers=h, json={"perfil": "Inspetor de Qualidade"})
    assert alterado.json()["perfil"] == "Inspetor de Qualidade"

    assert cliente.post(f"/api/usuarios/{uid}/senha", headers=h, json={"nova_senha": "nova-senha-9"}).status_code == 204
    login = cliente.post("/api/auth/login", json={"matricula": "ALM-0001", "senha": "nova-senha-9"})
    assert login.status_code == 200

    assert len(cliente.get("/api/usuarios", headers=h).json()) == 2


def test_senha_curta_e_perfil_invalido_dao_422(cliente, criar_usuario, token_de):
    criar_usuario("ADM-0001", Perfil.ADMINISTRADOR)
    h = token_de("ADM-0001")
    assert cliente.post("/api/usuarios", headers=h, json={"nome": "A", "perfil": "Almoxarife", "senha": "123"}).status_code == 422
    assert cliente.post("/api/usuarios", headers=h, json={"nome": "A", "perfil": "Chefe", "senha": "senha-forte-1"}).status_code == 422


def test_administrador_nao_se_desativa(cliente, criar_usuario, token_de):
    adm = criar_usuario("ADM-0001", Perfil.ADMINISTRADOR)
    r = cliente.patch(f"/api/usuarios/{adm.id}", headers=token_de("ADM-0001"), json={"ativo": False})
    assert r.status_code == 409
