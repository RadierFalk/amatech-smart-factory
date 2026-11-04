"""
Ponto de Entrada Unificado do ERP AMATECH.
Integra em uma única aplicação, única porta e única sessão autenticada os 5 módulos:
1. Rastreabilidade e Materiais (RAS)
2. Controle da Qualidade e Defeitos (QLD)
3. Gestão da Manutenção de Ativos (MNT)
4. Dashboard Industrial e Metas (DSH)
5. Gestão de Usuários e Acessos (USR)

Executar com:
    streamlit run app.py
"""
import os
import sys
from pathlib import Path

import streamlit as st

PASTA_PORTAL = Path(__file__).resolve().parent
RAIZ = PASTA_PORTAL.parent

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if str(PASTA_PORTAL) not in sys.path:
    sys.path.insert(0, str(PASTA_PORTAL))

# Habilita a comunicação in-process entre os módulos (sem necessidade de portas separadas)
os.environ["AMATECH_INTEGRACAO_LOCAL"] = "1"

from identidade import amatech
from autenticacao import autenticar
from banco import inicializar_banco
from integracao_local import sincronizar_usuario_nos_modulos
from modulos.dashboard import renderizar_modulo_dashboard
from modulos.manutencao import renderizar_modulo_manutencao
from modulos.qualidade import renderizar_modulo_qualidade
from modulos.rastreabilidade import renderizar_modulo_rastreabilidade
from permissoes import (
    MODULO_DASHBOARD,
    MODULO_MANUTENCAO,
    MODULO_QUALIDADE,
    MODULO_RASTREABILIDADE,
    MODULO_USUARIOS,
    modulos_permitidos,
    tem_acesso_modulo,
)
from telas.seletor import mostrar_seletor
from telas.usuarios import mostrar_gestao_usuarios

# Inicializa o banco central de identidades do ERP
inicializar_banco()

# Configuração e Design System Oficial AMATECH
amatech.configurar_pagina("ERP", layout="wide")
amatech.aplicar_estilos()

# ============================================================
# ESTADO DA SESSÃO UNIFICADA
# ============================================================

if "erp_usuario" not in st.session_state:
    st.session_state["erp_usuario"] = None

if "modulo_ativo" not in st.session_state:
    st.session_state["modulo_ativo"] = None

usuario = st.session_state["erp_usuario"]

# ============================================================
# TELA 1: LOGIN CORPORATIVO UNIFICADO (QUANDO NÃO AUTENTICADO)
# ============================================================

if usuario is None:
    amatech.tela_login("ERP")

    _, centro, _ = st.columns([1, 1.45, 1])
    with centro:
        with st.form("form_login_erp"):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 1.1rem;">
                    <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--tinta);">
                        Acesso Único Integrado — ERP AMATECH
                    </h3>
                    <p style="margin: 4px 0 0; font-size: 0.85rem; color: var(--tinta-2);">
                        Informe sua matrícula funcional e senha para acessar os módulos habilitados para sua persona
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            matricula = st.text_input("Matrícula Funcional", placeholder="Ex: ADM-0001, GES-0001, OPE-0001...")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            btn_entrar = st.form_submit_button("Entrar no ERP", type="primary", width="stretch")

            if btn_entrar:
                sucesso, mensagem, dados = autenticar(matricula, senha)
                if sucesso and dados:
                    st.session_state["erp_usuario"] = dados
                    st.session_state["modulo_ativo"] = None
                    sincronizar_usuario_nos_modulos(dados, st.session_state)
                    st.rerun()
                else:
                    st.error(mensagem)

        amatech.nota_login(
            "<b>Contas de Demonstração por Persona (Senha única: <code>amatech1234</code>):</b><br>"
            "• <code>ADM-0001</code> — Ana Souza (<b>Administrador</b>): RAS, QLD, MNT, DSH e USR (5 módulos)<br>"
            "• <code>GES-0001</code> — Orlando Vandres (<b>Supervisor / Gestor</b>): RAS, QLD, MNT e DSH (4 módulos)<br>"
            "• <code>OPE-0001</code> — João Silva (<b>Operador de Produção</b>): RAS, QLD, MNT e DSH (4 módulos)<br>"
            "• <code>QUA-0001</code> — Maria Santos (<b>Inspetor de Qualidade</b>): RAS, QLD e DSH (3 módulos)<br>"
            "• <code>TEC-2001</code> — João Lima Silva (<b>Técnico de Manutenção</b>): MNT e DSH (2 módulos)<br>"
            "• <code>ALM-0001</code> — Carlos Oliveira (<b>Almoxarife</b>): RAS e QLD (2 módulos)"
        )
    st.stop()


# Garante que as chaves de sessão dos módulos estejam sincronizadas
if "ras_usuario" not in st.session_state or "usuario_autenticado" not in st.session_state:
    sincronizar_usuario_nos_modulos(usuario, st.session_state)

modulo_ativo = st.session_state.get("modulo_ativo")

# Proteção RBAC: se o usuário não tiver permissão para o módulo ativo, volta ao Seletor
if modulo_ativo and not tem_acesso_modulo(usuario, modulo_ativo):
    st.session_state["modulo_ativo"] = None
    modulo_ativo = None


# ============================================================
# BARRA LATERAL GLOBAL DO ERP + SELETOR DE MÓDULOS
# ============================================================

with st.sidebar:
    amatech.usuario_no_menu(usuario["nome"], usuario["perfil"], usuario["matricula"])

    if st.button(
        "Seletor de Módulos (Hub)",
        icon=":material/apps:",
        key="erp_nav_seletor",
        type="primary" if modulo_ativo is None else "secondary",
        width="stretch",
    ):
        st.session_state["modulo_ativo"] = None
        st.rerun()

    st.markdown('<div class="sb-nav-grupo">Módulos Habilitados</div>', unsafe_allow_html=True)
    for mod in modulos_permitidos(usuario):
        eh_mod_ativo = modulo_ativo == mod.id
        if st.button(
            f"{mod.sigla} · {mod.nome}",
            icon=mod.icone,
            key=f"erp_sidebar_mod_{mod.id}",
            type="primary" if eh_mod_ativo else "secondary",
            width="stretch",
        ):
            st.session_state["modulo_ativo"] = mod.id
            st.rerun()

    st.markdown("---")
    if st.button("Encerrar Sessão", icon=":material/logout:", key="erp_btn_logout", width="stretch"):
        st.session_state.clear()
        st.rerun()


# ============================================================
# ROTEAMENTO MODULAR INTERNO (MESMA PORTA E MESMA SESSÃO)
# ============================================================

if modulo_ativo is None:
    mostrar_seletor(usuario)
elif modulo_ativo == MODULO_RASTREABILIDADE:
    renderizar_modulo_rastreabilidade(usuario)
elif modulo_ativo == MODULO_QUALIDADE:
    renderizar_modulo_qualidade(usuario)
elif modulo_ativo == MODULO_MANUTENCAO:
    renderizar_modulo_manutencao(usuario)
elif modulo_ativo == MODULO_DASHBOARD:
    renderizar_modulo_dashboard(usuario)
elif modulo_ativo == MODULO_USUARIOS:
    mostrar_gestao_usuarios(usuario)
else:
    mostrar_seletor(usuario)
