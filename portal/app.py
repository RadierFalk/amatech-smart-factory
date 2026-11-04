"""
Ponto de Entrada do Portal ERP AMATECH.
Hub Central Modular de Navegação e Gestão de Acessos Industriais.

Executar com:
    streamlit run portal/app.py --server.port 8500
"""
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from identidade import amatech
from autenticacao import autenticar
from banco import inicializar_banco
from permissoes import (
    ADMINISTRADOR,
    MODULO_USUARIOS,
)
from telas.seletor import mostrar_seletor
from telas.usuarios import mostrar_gestao_usuarios

# Inicializa banco de identidades do ERP
inicializar_banco()

# Configuração e Design System Oficial AMATECH
amatech.configurar_pagina("ERP", layout="wide")
amatech.aplicar_estilos()

# ============================================================
# ESTADO DA SESSÃO
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

    _, centro, _ = st.columns([1, 1.4, 1])
    with centro:
        with st.form("form_login_erp"):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 1.25rem;">
                    <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--tinta);">
                        Acesso Corporativo ao ERP
                    </h3>
                    <p style="margin: 4px 0 0; font-size: 0.85rem; color: var(--tinta-2);">
                        Informe sua matrícula funcional e senha para desbloquear seus módulos
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            matricula = st.text_input("Matrícula Funcional", placeholder="Ex: ADM-0001, OPE-0001...")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            btn_entrar = st.form_submit_button("Entrar no ERP", type="primary", width="stretch")

            if btn_entrar:
                sucesso, mensagem, dados = autenticar(matricula, senha)
                if sucesso and dados:
                    st.session_state["erp_usuario"] = dados
                    st.session_state["modulo_ativo"] = None
                    st.rerun()
                else:
                    st.error(mensagem)

        st.markdown(
            """
            <div style="margin-top: 1.5rem; background: var(--superficie); border: 1px solid var(--linha); border-radius: 8px; padding: 14px;">
                <b style="display: block; font-size: 12px; color: var(--tinta); margin-bottom: 6px;">
                    🔑 Contas de Demonstração (Senha padrão: <code>amatech1234</code>):
                </b>
                <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: var(--tinta-2); line-height: 1.6;">
                    <li><code>ADM-0001</code> (Ana Souza · <b>Administrador</b>): Acesso aos 4 módulos.</li>
                    <li><code>QUA-0001</code> (Maria Santos · <b>Inspetor de Qualidade</b>): Acesso a Rastreabilidade e Qualidade.</li>
                    <li><code>OPE-0001</code> (João Silva · <b>Operador</b>): Acesso a Rastreabilidade, Qualidade e Manutenção.</li>
                    <li><code>TEC-2001</code> (João Lima Silva · <b>Técnico</b>): Acesso restrito à Manutenção.</li>
                    <li><code>ALM-0001</code> (Carlos Oliveira · <b>Almoxarife</b>): Acesso a Rastreabilidade e Qualidade.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()


# ============================================================
# TELA 2: ÁREA AUTENTICADA (SELETOR DE MÓDULOS E GESTÃO)
# ============================================================

# Barra Lateral
with st.sidebar:
    st.markdown(
        f"""
        <div style="padding: 12px 0; border-bottom: 1px solid var(--noite-2); margin-bottom: 12px;">
            <b style="display: block; color: var(--on-noite); font-size: 14px;">{usuario['nome']}</b>
            <span class="am-codigo" style="font-size: 11px; color: var(--led);">{usuario['matricula']}</span>
            <small style="display: block; color: var(--on-noite-suave); font-size: 12px; margin-top: 2px;">
                Persona: <b>{usuario['perfil']}</b>
            </small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Seletor de Módulos (Hub)", icon=":material/dashboard:", width="stretch"):
        st.session_state["modulo_ativo"] = None
        st.rerun()

    if usuario["perfil"] == ADMINISTRADOR:
        if st.button("Gestão de Usuários (Módulo 4)", icon=":material/manage_accounts:", width="stretch"):
            st.session_state["modulo_ativo"] = MODULO_USUARIOS
            st.rerun()

    st.markdown("---")

    if st.button("Encerrar Sessão", icon=":material/logout:", width="stretch"):
        st.session_state["erp_usuario"] = None
        st.session_state["modulo_ativo"] = None
        st.rerun()


# Cabeçalho Superior AMATECH
amatech.cabecalho("ERP", [
    ("Turno", amatech.turno_atual()),
    ("Colaborador", usuario["nome"]),
    ("Persona", usuario["perfil"]),
])

# Roteamento interno
if st.session_state.get("modulo_ativo") == MODULO_USUARIOS and usuario["perfil"] == ADMINISTRADOR:
    mostrar_gestao_usuarios(usuario)
else:
    mostrar_seletor(usuario)
