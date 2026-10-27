"""
Ponto de Entrada Principal da Aplicação Streamlit (management-control).
AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção.
"""
import importlib
import streamlit as st

st.set_page_config(
    page_title="AMATECH | Controle da Manutenção",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

from api import iniciar_api_em_background
from config import API_PORT, COLORS
from database import ensure_database_initialized
from services.auth_service import PERMISSOES_POR_PERFIL, autenticar_usuario
from ui_components import aplicar_estilos_amatech, navegar_para

# Mapeamento das telas (código interno -> título no menu e módulo em pages/)
CATALOGO_TELAS = {
    "painel_maquinas": ("🏭 Painel de Máquinas", "pages.01_painel_maquinas"),
    "abrir_chamado": ("🚨 Abrir Chamado", "pages.02_abrir_chamado"),
    "fila_chamados": ("📋 Fila Técnica", "pages.03_fila_chamados"),
    "ordem_servico": ("🔧 Ordem de Serviço", "pages.04_ordem_servico"),
    "dashboard": ("📊 Dashboard de KPIs", "pages.05_dashboard"),
    "historico": ("📜 Histórico & Auditoria", "pages.06_historico"),
    "cadastros": ("⚙️ Cadastros", "pages.07_cadastros"),
}


def _realizar_login(matricula: str, senha: str) -> None:
    """Autentica o colaborador e redireciona para a tela inicial adequada ao perfil."""
    user = autenticar_usuario(matricula, senha)
    st.session_state["usuario_logado"] = {
        "id": user.id,
        "nome": user.nome,
        "matricula": user.matricula,
        "perfil": user.perfil,
    }
    if user.perfil == "TECNICO":
        st.session_state["pagina_atual"] = "fila_chamados"
    elif user.perfil == "GESTOR":
        st.session_state["pagina_atual"] = "painel_maquinas"
    else:
        st.session_state["pagina_atual"] = "painel_maquinas"


def _renderizar_tela_login() -> None:
    """Renderiza a Tela 1: Login e Autenticação com acesso rápido de demonstração (F01)."""
    st.markdown("<br>", unsafe_allow_html=True)
    col_vazia1, col_centro, col_vazia2 = st.columns([1, 1.4, 1])

    with col_centro:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
                        color: #FFFFFF; padding: 28px 30px; border-radius: 14px 14px 0 0; text-align: center;
                        box-shadow: 0 6px 20px rgba(31,58,95,0.2);">
                <div style="font-size: 2.2rem; margin-bottom: 4px;">🏭 AMATECH ELECTRONICS</div>
                <div style="font-size: 1.15rem; font-weight: 700; letter-spacing: 0.5px;">
                    SISTEMA DE CONTROLE DA MANUTENÇÃO (SMART FACTORY)
                </div>
                <div style="font-size: 0.85rem; color: #E2E8F0; margin-top: 6px;">
                    Polo Industrial de Manaus • Projeto Integrador: Ambiente Fabril I (FMM)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            st.markdown(
                """
                <div style="background:#FFFFFF; padding: 18px 24px 6px 24px; border-radius: 0 0 14px 14px;
                            box-shadow: 0 6px 20px rgba(0,0,0,0.06); margin-bottom: 14px;">
                    <h4 style="margin-top:0; color:#1F3A5F;">🔐 Autenticação de Colaborador (RBAC)</h4>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("form_login_amatech"):
                matricula_in = st.text_input(
                    "Matrícula Funcional",
                    placeholder="Ex: OP-10234, TEC-2001 ou GES-0001",
                )
                senha_in = st.text_input(
                    "Senha de Acesso",
                    type="password",
                    placeholder="Senha padrão de demonstração: 123456",
                )
                btn_entrar = st.form_submit_button(
                    "Entrar no Sistema",
                    type="primary",
                    use_container_width=True,
                )

                if btn_entrar:
                    try:
                        _realizar_login(matricula_in, senha_in)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"❌ Falha na autenticação: {exc}")

        st.markdown("##### ⚡ Acesso Rápido para Demonstração em Sala (Senha: `123456`)")
        d1, d2, d3 = st.columns(3)
        with d1:
            if st.button(
                "👷 Operador\n(OP-10234)",
                use_container_width=True,
                help="Carlos Mendonça — Perfil OPERADOR",
            ):
                _realizar_login("OP-10234", "123456")
                st.rerun()
        with d2:
            if st.button(
                "🔧 Técnico\n(TEC-2001)",
                use_container_width=True,
                help="João Lima Silva — Perfil TECNICO",
            ):
                _realizar_login("TEC-2001", "123456")
                st.rerun()
        with d3:
            if st.button(
                "📊 Gestor\n(GES-0001)",
                use_container_width=True,
                help="Orlando Vandres — Perfil GESTOR",
            ):
                _realizar_login("GES-0001", "123456")
                st.rerun()


def _renderizar_sidebar_e_navegacao(usuario: dict) -> str:
    """Renderiza a barra lateral institucional AMATECH com menu filtrado por RBAC (RN01)."""
    perfil = usuario["perfil"]
    telas_permitidas = PERMISSOES_POR_PERFIL.get(perfil, ["painel_maquinas"])

    if st.session_state.get("pagina_atual") not in telas_permitidas:
        st.session_state["pagina_atual"] = telas_permitidas[0]

    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align:center; padding: 10px 4px 16px 4px; border-bottom: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size:1.35rem; font-weight:800; letter-spacing:1px;">🏭 AMATECH</div>
                <div style="font-size:0.78rem; opacity:0.85;">CONTROLE DA MANUTENÇÃO</div>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 14px 0;">
                <div style="font-size:0.75rem; text-transform:uppercase; opacity:0.8;">Colaborador Logado</div>
                <div style="font-size:0.98rem; font-weight:700; margin-top:2px;">{usuario['nome']}</div>
                <div style="font-size:0.82rem; opacity:0.9;">Matrícula: <strong>{usuario['matricula']}</strong></div>
                <div style="margin-top:6px; display:inline-block; background:{COLORS['secondary']};
                            padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:700;">
                    PERFIL: {perfil}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Navegação do Módulo")
        pagina_ativa = st.session_state.get("pagina_atual", telas_permitidas[0])
        idx_atual = telas_permitidas.index(pagina_ativa) if pagina_ativa in telas_permitidas else 0

        escolha = st.radio(
            "Menu Principal",
            options=telas_permitidas,
            index=idx_atual,
            format_func=lambda cod: CATALOGO_TELAS[cod][0],
            label_visibility="collapsed",
        )

        if escolha != pagina_ativa:
            st.session_state["pagina_atual"] = escolha
            st.rerun()

        st.markdown("---")
        st.markdown("##### 🔄 Troca Rápida de Perfil (Demo)")
        c_op, c_tec, c_ges = st.columns(3)
        with c_op:
            if st.button("OP", help="Trocar para Operador (OP-10234)", use_container_width=True):
                _realizar_login("OP-10234", "123456")
                st.rerun()
        with c_tec:
            if st.button("TEC", help="Trocar para Técnico (TEC-2001)", use_container_width=True):
                _realizar_login("TEC-2001", "123456")
                st.rerun()
        with c_ges:
            if st.button("GES", help="Trocar para Gestor (GES-0001)", use_container_width=True):
                _realizar_login("GES-0001", "123456")
                st.rerun()

        if st.button("🚪 Encerrar Sessão (Logout)", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.markdown(
            f"""
            <div style="margin-top: 18px; padding: 10px; background: rgba(0,0,0,0.22);
                        border-radius: 8px; font-size: 0.75rem; text-align: center;">
                🟢 <strong>API REST JSON Ativa</strong><br>
                <code>http://localhost:{API_PORT}/api/status</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["pagina_atual"]


def main() -> None:
    """Inicializa banco, API REST em background, estilos e roteador de telas."""
    ensure_database_initialized()
    iniciar_api_em_background(API_PORT)
    aplicar_estilos_amatech()

    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        _renderizar_tela_login()
        return

    codigo_pagina = _renderizar_sidebar_e_navegacao(usuario)
    _, modulo_path = CATALOGO_TELAS[codigo_pagina]
    modulo = importlib.import_module(modulo_path)
    modulo.render()


if __name__ == "__main__":
    main()
