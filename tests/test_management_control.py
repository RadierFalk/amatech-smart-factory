"""
Suíte de Testes Automatizados do Sistema de Controle da Manutenção (AMATECH).
Valida Máquina de Estados, Regras de Negócio (RN01 a RN09), Cálculo de KPIs e Endpoints da API REST.
"""
import importlib
import os
import tempfile
import pytest

from api import obter_chamados, obter_equipamentos, obter_indicadores, obter_status
from database import ensure_database_initialized
from services.auth_service import (
    alternar_status_usuario,
    autenticar_usuario,
    criar_usuario,
    verificar_permissao,
)
from services.chamado_service import (
    abrir_chamado,
    adicionar_peca_chamado,
    assumir_chamado,
    concluir_chamado,
    listar_fila_chamados,
    listar_historico_auditoria,
    obter_chamado_detalhado,
)
from services.equipamento_service import (
    alternar_status_ativo_equipamento,
    alternar_status_ativo_peca,
    criar_equipamento,
    criar_peca,
    obter_equipamento,
)
from services.relatorio_service import obter_indicadores_consolidados


@pytest.fixture
def temp_db():
    """Cria um banco SQLite temporário populado com o seed oficial de docs/02_DATABASE_SCHEMA.sql."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    ensure_database_initialized(db_path=path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_rn01_autenticacao_e_rbac(temp_db):
    """Testa login dos 3 perfis padrão, bloqueio de inativos e permissões RBAC (RN01)."""
    op = autenticar_usuario("OP-10234", "123456", db_path=temp_db)
    assert op.perfil == "OPERADOR"
    assert verificar_permissao(op.perfil, "painel_maquinas") is True
    assert verificar_permissao(op.perfil, "cadastros") is False

    tec = autenticar_usuario("TEC-2001", "123456", db_path=temp_db)
    assert tec.perfil == "TECNICO"
    assert verificar_permissao(tec.perfil, "fila_chamados") is True
    assert verificar_permissao(tec.perfil, "ordem_servico") is True

    ges = autenticar_usuario("GES-0001", "123456", db_path=temp_db)
    assert ges.perfil == "GESTOR"
    assert verificar_permissao(ges.perfil, "dashboard") is True
    assert verificar_permissao(ges.perfil, "cadastros") is True

    # Inativação bloqueia login (RN01 + RN07)
    alternar_status_usuario(op.id, False, db_path=temp_db)
    with pytest.raises(PermissionError, match="RN01"):
        autenticar_usuario("OP-10234", "123456", db_path=temp_db)


def test_fluxo_completo_maquina_estados_e_auditoria_rn02_a_rn09(temp_db):
    """
    Testa o ciclo completo obrigatório:
    Abertura (PARADA / ABERTO) -> Assumir (EM_MANUTENCAO / EM_ANDAMENTO)
    -> Peças (RN09) -> Conclusão (OPERACIONAL / CONCLUIDO / Downtime RN05)
    -> Auditoria (RN08).
    """
    # Equipamento 1 (SMT-01) inicia OPERACIONAL no seed
    eq_antes = obter_equipamento(1, db_path=temp_db)
    assert eq_antes["status_operacional"] == "OPERACIONAL"

    # 1. Operador (ID 1) abre chamado para SMT-01 (ID 1)
    chamado_id = abrir_chamado(
        equipamento_id=1,
        operador_abertura_id=1,
        prioridade="CRITICA",
        descricao_falha="Falha no bico de vácuo do cabeçote 2.",
        tipo_manutencao="CORRETIVA",
        db_path=temp_db,
    )
    assert chamado_id > 0

    eq_parada = obter_equipamento(1, db_path=temp_db)
    assert eq_parada["status_operacional"] == "PARADA"

    # RN02: Tentativa de abrir outro chamado para a mesma máquina PARADA deve ser bloqueada
    with pytest.raises(ValueError, match="RN02"):
        abrir_chamado(
            equipamento_id=1,
            operador_abertura_id=2,
            prioridade="ALTA",
            descricao_falha="Chamado duplicado na mesma máquina",
            db_path=temp_db,
        )

    # Verifica que está no topo da fila técnica por prioridade CRITICA
    fila = listar_fila_chamados(db_path=temp_db)
    assert fila[0]["id"] == chamado_id

    # 2. Técnico (ID 3 - João Lima Silva) assume a OS
    assumir_chamado(chamado_id=chamado_id, tecnico_id=3, db_path=temp_db)
    eq_manut = obter_equipamento(1, db_path=temp_db)
    assert eq_manut["status_operacional"] == "EM_MANUTENCAO"

    # RN09: Quantidade de peças deve ser > 0
    with pytest.raises(ValueError, match="RN09"):
        adicionar_peca_chamado(chamado_id=chamado_id, peca_id=1, quantidade=0, db_path=temp_db)

    adicionar_peca_chamado(chamado_id=chamado_id, peca_id=2, quantidade=2, db_path=temp_db)

    # RN04: Conclusão sem diagnóstico ou causa raiz deve falhar
    with pytest.raises(ValueError, match="RN04"):
        concluir_chamado(
            chamado_id=chamado_id,
            usuario_id=3,
            diagnostico_tecnico="",
            causa_raiz="Falha elétrica",
            db_path=temp_db,
        )

    # RN03: Outro técnico (ID 4) não pode concluir a OS assumida pelo técnico ID 3
    with pytest.raises(PermissionError, match="RN03"):
        concluir_chamado(
            chamado_id=chamado_id,
            usuario_id=4,
            diagnostico_tecnico="Troca efetuada",
            causa_raiz="Desgaste mecânico",
            db_path=temp_db,
        )

    # 3. Técnico responsável (ID 3) conclui a OS
    res = concluir_chamado(
        chamado_id=chamado_id,
        usuario_id=3,
        diagnostico_tecnico="Substituídos 2 sensores ópticos e recalibrado eixo Z.",
        causa_raiz="Falha elétrica / Curto-circuito / Sensor",
        tipo_manutencao="CORRETIVA",
        db_path=temp_db,
    )
    assert res["status_chamado"] == "CONCLUIDO"
    assert res["status_equipamento"] == "OPERACIONAL"
    assert isinstance(res["downtime_minutos"], int)
    assert res["downtime_minutos"] >= 0

    eq_final = obter_equipamento(1, db_path=temp_db)
    assert eq_final["status_operacional"] == "OPERACIONAL"

    detalhe = obter_chamado_detalhado(chamado_id, db_path=temp_db)
    assert len(detalhe["pecas_trocadas"]) == 1
    assert detalhe["pecas_trocadas"][0]["quantidade"] == 2.0

    # RN08: Verifica registros na trilha de auditoria historico_status
    auditoria = listar_historico_auditoria(equipamento_id=1, db_path=temp_db)
    transicoes_os = [a for a in auditoria if a["chamado_id"] == chamado_id]
    assert len(transicoes_os) == 3
    status_novos = {t["status_novo"] for t in transicoes_os}
    assert status_novos == {"PARADA", "EM_MANUTENCAO", "OPERACIONAL"}


def test_cadastros_e_soft_delete_rn07(temp_db):
    """Testa criação e inativação lógica de Equipamentos, Peças e Usuários (F14, F15, F16, RN07)."""
    eq_id = criar_equipamento("SMT-99", "Insersora Teste", "SMT", "Posto 09", db_path=temp_db)
    alternar_status_ativo_equipamento(eq_id, False, db_path=temp_db)
    eq = obter_equipamento(eq_id, db_path=temp_db)
    assert eq["ativo"] is False

    peca_id = criar_peca("PN-TST-999", "Sensor Laser", "UN", db_path=temp_db)
    alternar_status_ativo_peca(peca_id, False, db_path=temp_db)

    user_id = criar_usuario("Teste Operador", "OP-99999", "123456", "OPERADOR", db_path=temp_db)
    alternar_status_usuario(user_id, False, db_path=temp_db)


def test_indicadores_e_api_endpoints():
    """Valida o banco principal e os 4 endpoints da API REST JSON."""
    ensure_database_initialized(force_reset=True)

    st_resp = obter_status()
    assert st_resp["sistema"] == "Controle da Manutencao"
    assert st_resp["status"] == "online"

    eq_resp = obter_equipamentos()
    assert len(eq_resp) >= 8
    assert any(e["codigo_tag"] == "SMT-01" for e in eq_resp)

    ch_resp = obter_chamados()
    assert len(ch_resp) >= 3
    assert "pecas_trocadas" in ch_resp[0]

    ind_resp = obter_indicadores()
    assert ind_resp["sistema"] == "Controle da Manutencao"
    assert ind_resp["downtime_total_minutos"] == 60
    assert ind_resp["mttr_minutos"] == 45.0
    assert ind_resp["mtta_resposta_minutos"] == 15.0
    assert ind_resp["disponibilidade_geral_pct"] == 98.75


def test_importacao_modulos_paginas():
    """Garante que todos os módulos de páginas Streamlit e o app.py importam sem erros."""
    modulos = [
        "config",
        "database",
        "ui_components",
        "api",
        "pages.01_painel_maquinas",
        "pages.02_abrir_chamado",
        "pages.03_fila_chamados",
        "pages.04_ordem_servico",
        "pages.05_dashboard",
        "pages.06_historico",
        "pages.07_cadastros",
    ]
    for nome_mod in modulos:
        mod = importlib.import_module(nome_mod)
        assert mod is not None


def test_renderizacao_telas_streamlit_sem_erros():
    """Executa o app.py via AppTest do Streamlit validando todas as telas sem exceções."""
    from streamlit.testing.v1 import AppTest

    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    at = AppTest.from_file(app_path, default_timeout=15)
    at.run()
    assert not at.exception

    # Simula login como GESTOR (acesso a todas as 7 telas)
    at.session_state["usuario_logado"] = {
        "id": 5,
        "nome": "Orlando Vandres",
        "matricula": "GES-0001",
        "perfil": "GESTOR",
    }

    for tela in [
        "painel_maquinas",
        "abrir_chamado",
        "meus_chamados",
        "fila_chamados",
        "preventiva",
        "ordem_servico",
        "dashboard",
        "historico",
        "cadastros",
        "auditoria",
    ]:
        at.session_state["pagina_atual"] = tela
        at.run()
        assert not at.exception, f"Exceção na tela {tela}: {at.exception}"


def test_tela_login_e_botoes_rapidos():
    """Valida a renderização da tela de login oficial, botão ENTRAR e os 3 botões de login rápido."""
    from streamlit.testing.v1 import AppTest

    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    
    # 1. Login direto com credenciais pré-preenchidas e botão ENTRAR
    at = AppTest.from_file(app_path, default_timeout=15)
    at.run()
    assert not at.exception
    assert len(at.text_input) == 2
    assert at.text_input[0].value == "OP-10234"
    assert at.text_input[1].value == "123456"
    assert at.button[0].label == "ENTRAR"
    
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["usuario_logado"]["matricula"] == "OP-10234"

    # 2. Login rápido de Gestor
    at_ges = AppTest.from_file(app_path, default_timeout=15)
    at_ges.run()
    at_ges.button(key="btn_demo_ges").click().run()
    assert not at_ges.exception
    assert at_ges.session_state["usuario_logado"]["perfil"] == "GESTOR"

    # 3. Login rápido de Técnico
    at_tec = AppTest.from_file(app_path, default_timeout=15)
    at_tec.run()
    at_tec.button(key="btn_demo_tec").click().run()
    assert not at_tec.exception
    assert at_tec.session_state["usuario_logado"]["perfil"] == "TECNICO"

