"""
Suíte de Testes Unitários e de Integração do ERP Unificado AMATECH.
Valida:
- Autenticação única e gestão de credenciais (Argon2/SHA-256)
- Matriz RBAC das 6 Personas × 5 Módulos Integrados
- Isolamento de contexto (`ambiente_modulo`) sem colisão de nomes entre os 4 setores
- Sincronização automática de sessão e usuários nos bancos dos 4 módulos
- Comunicação in-process entre Rastreabilidade, Qualidade, Manutenção e Dashboard
- Navegação integrada em porta única via Streamlit AppTest
"""
import os
from pathlib import Path
import sys
import tempfile

import pytest

PASTA_PORTAL = Path(__file__).resolve().parent.parent
RAIZ = PASTA_PORTAL.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if str(PASTA_PORTAL) not in sys.path:
    sys.path.insert(0, str(PASTA_PORTAL))

from autenticacao import autenticar
from banco import (
    alterar_perfil,
    alternar_ativo,
    criar_usuario,
    inicializar_banco,
    listar_usuarios,
    proxima_matricula,
    redefinir_senha,
)
from integracao_local import (
    ClienteHttpLocal,
    ambiente_modulo,
    despachar_requisicao_local,
    sincronizar_usuario_nos_modulos,
)
from permissoes import (
    ADMINISTRADOR,
    ALMOXARIFE,
    INSPETOR,
    MODULO_DASHBOARD,
    MODULO_MANUTENCAO,
    MODULO_QUALIDADE,
    MODULO_RASTREABILIDADE,
    MODULO_USUARIOS,
    OPERADOR,
    SUPERVISOR,
    TECNICO,
    modulos_permitidos,
    tem_acesso_modulo,
)


@pytest.fixture()
def banco_temp():
    """Cria um banco SQLite temporário isolado para cada teste."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_erp.db"
        inicializar_banco(db_file)
        yield db_file


# ============================================================
# 1. TESTES DE SEMENTE E AUTENTICAÇÃO CORPORATIVA
# ============================================================

def test_seed_cria_as_6_personas_canonicas(banco_temp):
    usuarios = listar_usuarios(banco_temp)
    assert len(usuarios) == 6
    matriculas = {u["matricula"] for u in usuarios}
    assert matriculas == {
        "ADM-0001",
        "GES-0001",
        "QUA-0001",
        "OPE-0001",
        "TEC-2001",
        "ALM-0001",
    }


def test_autenticacao_valida_credenciais_corretas(banco_temp):
    ok, msg, dados = autenticar("ADM-0001", "amatech1234", banco_temp)
    assert ok is True
    assert dados is not None
    assert dados["matricula"] == "ADM-0001"
    assert dados["perfil"] == ADMINISTRADOR
    assert "senha_hash" not in dados


def test_autenticacao_rejeita_senha_incorreta_ou_inativa(banco_temp):
    ok, msg, dados = autenticar("ADM-0001", "senha_errada", banco_temp)
    assert ok is False
    assert dados is None

    usuarios = listar_usuarios(banco_temp)
    ope = next(u for u in usuarios if u["matricula"] == "OPE-0001")
    alternar_ativo(ope["id"], banco_temp)

    ok2, msg2, dados2 = autenticar("OPE-0001", "amatech1234", banco_temp)
    assert ok2 is False
    assert dados2 is None
    assert "inativa" in msg2.lower()


# ============================================================
# 2. TESTES DA MATRIZ DE PERMISSÕES RBAC (6 PERSONAS × 5 MÓDULOS)
# ============================================================

def test_administrador_acessa_todos_os_5_modulos():
    usuario = {"perfil": ADMINISTRADOR}
    mods = [m.id for m in modulos_permitidos(usuario)]
    assert len(mods) == 5
    assert set(mods) == {
        MODULO_RASTREABILIDADE,
        MODULO_QUALIDADE,
        MODULO_MANUTENCAO,
        MODULO_DASHBOARD,
        MODULO_USUARIOS,
    }


def test_supervisor_acessa_4_modulos_operacionais_sem_gestao_usuarios():
    usuario = {"perfil": SUPERVISOR}
    mods = {m.id for m in modulos_permitidos(usuario)}
    assert mods == {
        MODULO_RASTREABILIDADE,
        MODULO_QUALIDADE,
        MODULO_MANUTENCAO,
        MODULO_DASHBOARD,
    }
    assert tem_acesso_modulo(usuario, MODULO_USUARIOS) is False


def test_operador_acessa_rastreabilidade_qualidade_manutencao_e_dashboard():
    usuario = {"perfil": OPERADOR}
    mods = {m.id for m in modulos_permitidos(usuario)}
    assert mods == {
        MODULO_RASTREABILIDADE,
        MODULO_QUALIDADE,
        MODULO_MANUTENCAO,
        MODULO_DASHBOARD,
    }
    assert tem_acesso_modulo(usuario, MODULO_USUARIOS) is False


def test_inspetor_acessa_rastreabilidade_qualidade_e_dashboard():
    usuario = {"perfil": INSPETOR}
    mods = {m.id for m in modulos_permitidos(usuario)}
    assert mods == {
        MODULO_RASTREABILIDADE,
        MODULO_QUALIDADE,
        MODULO_DASHBOARD,
    }
    assert tem_acesso_modulo(usuario, MODULO_MANUTENCAO) is False
    assert tem_acesso_modulo(usuario, MODULO_USUARIOS) is False


def test_tecnico_acessa_manutencao_e_dashboard():
    usuario = {"perfil": TECNICO}
    mods = {m.id for m in modulos_permitidos(usuario)}
    assert mods == {
        MODULO_MANUTENCAO,
        MODULO_DASHBOARD,
    }
    assert tem_acesso_modulo(usuario, MODULO_RASTREABILIDADE) is False
    assert tem_acesso_modulo(usuario, MODULO_QUALIDADE) is False
    assert tem_acesso_modulo(usuario, MODULO_USUARIOS) is False


def test_almoxarife_acessa_rastreabilidade_e_qualidade():
    usuario = {"perfil": ALMOXARIFE}
    mods = {m.id for m in modulos_permitidos(usuario)}
    assert mods == {
        MODULO_RASTREABILIDADE,
        MODULO_QUALIDADE,
    }
    assert tem_acesso_modulo(usuario, MODULO_MANUTENCAO) is False
    assert tem_acesso_modulo(usuario, MODULO_DASHBOARD) is False
    assert tem_acesso_modulo(usuario, MODULO_USUARIOS) is False


# ============================================================
# 3. TESTES DO MÓDULO DE GESTÃO DE USUÁRIOS (CRUD)
# ============================================================

def test_criar_alterar_e_redefinir_senha_usuario(banco_temp):
    prox = proxima_matricula(TECNICO, banco_temp)
    assert prox == "TEC-2002"

    ok, msg, novo = criar_usuario("Roberto Alencar", TECNICO, "senhaForte99", None, banco_temp)
    assert ok is True
    assert novo["matricula"] == "TEC-2002"

    alterar_perfil(novo["id"], SUPERVISOR, banco_temp)
    redefinir_senha(novo["id"], "novaSenha2026", banco_temp)

    ok_login, _, sessao = autenticar("TEC-2002", "novaSenha2026", banco_temp)
    assert ok_login is True
    assert sessao["perfil"] == SUPERVISOR


# ============================================================
# 4. TESTES DE ISOLAMENTO DE CONTEXTO E INTEGRAÇÃO IN-PROCESS
# ============================================================

def test_isolamento_ambiente_modulo_sem_colisao_entre_setores():
    with ambiente_modulo("manutencao"):
        import config as cfg_mnt
        assert hasattr(cfg_mnt, "ESTACOES_FLUXO")

    with ambiente_modulo("dashboard"):
        import config as cfg_dsh
        assert hasattr(cfg_dsh, "FUSO_HORAS")

    with ambiente_modulo("rastreabilidade"):
        from contextlib import closing
        from app import db, seed
        db.inicializar()
        with closing(db.conectar()) as conn:
            if db.um(conn, "SELECT COUNT(*) AS n FROM status_producao")["n"] == 0:
                seed.popular(conn)
            total_prod = conn.execute("SELECT COUNT(*) as c FROM produtos").fetchone()["c"]
            assert total_prod >= 1


def test_sincronizar_usuario_nos_4_modulos():
    estado = {}
    usuario_erp = {
        "id": 1,
        "matricula": "ADM-0001",
        "nome": "Ana Souza",
        "perfil": ADMINISTRADOR,
    }
    sincronizar_usuario_nos_modulos(usuario_erp, estado)

    assert estado["ras_usuario"]["cargo"] == "Administrador"
    assert estado["usuario_autenticado"]["perfil"] == "Administrador"
    assert estado["usuario_logado"]["perfil"] == "GESTOR"
    assert estado["usuario"].perfil.nome == "Administrador"


def test_comunicacao_in_process_entre_setores():
    os.environ["AMATECH_INTEGRACAO_LOCAL"] = "1"
    ok_ras, produtos_ras = despachar_requisicao_local("GET", "http://localhost:8000/api/v1/produtos")
    assert ok_ras is True
    assert isinstance(produtos_ras, list) and len(produtos_ras) >= 1

    ok_mnt, maquinas_mnt = despachar_requisicao_local("GET", "http://localhost:5000/api/equipamentos")
    assert ok_mnt is True
    assert isinstance(maquinas_mnt, list) and len(maquinas_mnt) >= 1

    cliente = ClienteHttpLocal()
    resp_qld = cliente.get("http://localhost:5002/api/ocorrencias")
    assert resp_qld.status_code == 200
    assert isinstance(resp_qld.json(), list)


def test_navegacao_integrada_nos_5_modulos_mesma_sessao():
    """Testa o fluxo real do ERP unificado em uma única sessão (Login -> Seletor -> 5 Módulos)."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=20)
    at.run()
    assert not at.exception

    # Faz login único como Administrador
    at.text_input[0].set_value("ADM-0001")
    at.text_input[1].set_value("amatech1234")
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["erp_usuario"]["matricula"] == "ADM-0001"
    assert at.session_state["modulo_ativo"] is None

    # Navega internamente pelos 5 módulos na mesma sessão (sem trocar de porta nem pedir nova senha)
    for id_modulo in (
        MODULO_RASTREABILIDADE,
        MODULO_QUALIDADE,
        MODULO_MANUTENCAO,
        MODULO_DASHBOARD,
        MODULO_USUARIOS,
    ):
        at.session_state["modulo_ativo"] = id_modulo
        at.run()
        assert not at.exception, f"Erro ao renderizar módulo {id_modulo}: {at.exception}"

    # Verifica também as subpáginas da Rastreabilidade
    at.session_state["modulo_ativo"] = MODULO_RASTREABILIDADE
    for sub_ras in ("terminal", "producao", "solicitacoes", "baixas", "cadastros", "relatorios"):
        at.session_state["ras_subpagina"] = sub_ras
        at.run()
        assert not at.exception, f"Erro na subpágina RAS '{sub_ras}': {at.exception}"

    # Verifica também as subpáginas do Dashboard Industrial
    at.session_state["modulo_ativo"] = MODULO_DASHBOARD
    for sub_dsh in (
        "pages/1_Painel.py",
        "pages/2_Producao_e_metas.py",
        "pages/3_Qualidade.py",
        "pages/4_Paradas.py",
        "pages/5_Perdas.py",
        "pages/6_Importacao.py",
        "pages/7_Historico.py",
        "pages/8_Cadastros.py",
    ):
        at.session_state["dsh_subpagina"] = sub_dsh
        at.run()
        assert not at.exception, f"Erro na subpágina DSH '{sub_dsh}': {at.exception}"




def test_permissoes_modulo_manutencao_por_perfil():
    """Valida que no módulo de manutenção:
    - Técnico: acesso SOMENTE a Manutenção Técnica (fila_chamados, preventiva, ordem_servico)
    - Supervisor: APENAS à seção de Gestão (indicadores, historico, cadastros, auditoria)
    - Operador: TODA a seção de Operação (painel_maquinas, abrir_chamado, meus_chamados)
    - Administrador: todas as seções
    """
    from portal.modulos.manutencao import CATALOGO_ROTAS
    from portal.permissoes import ADMINISTRADOR, OPERADOR, SUPERVISOR, TECNICO

    def obter_rotas_usuario(perfil_nome: str) -> set[str]:
        rotas = set()
        for cod, info in CATALOGO_ROTAS.items():
            if cod == "dashboard":
                continue
            permitidos = info[4]
            if perfil_nome in permitidos:
                rotas.add(cod)
        return rotas

    rotas_tec = obter_rotas_usuario(TECNICO)
    assert rotas_tec == {"fila_chamados", "preventiva", "ordem_servico"}

    rotas_sup = obter_rotas_usuario(SUPERVISOR)
    assert rotas_sup == {"indicadores", "historico", "cadastros", "auditoria"}

    rotas_op = obter_rotas_usuario(OPERADOR)
    assert rotas_op == {"painel_maquinas", "abrir_chamado", "meus_chamados"}

    rotas_adm = obter_rotas_usuario(ADMINISTRADOR)
    assert rotas_adm == {
        "painel_maquinas",
        "abrir_chamado",
        "meus_chamados",
        "fila_chamados",
        "preventiva",
        "ordem_servico",
        "indicadores",
        "historico",
        "cadastros",
        "auditoria",
    }
