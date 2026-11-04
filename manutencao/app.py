import os
"""
Ponto de Entrada Principal da Aplicação Streamlit (management-control).
AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção.
Replica fielmente o design, login split, sidebar agrupada e todas as rotas do projeto amatech-manutencao.
"""
import importlib
import streamlit as st

from ui_components import amatech, aplicar_estilos_amatech, esc, rotulo_amigavel

amatech.configurar_pagina("MNT", layout="wide", initial_sidebar_state="expanded")

from database import ensure_database_initialized  # noqa: E402
from services.auth_service import PERMISSOES_POR_PERFIL, autenticar_usuario  # noqa: E402
from services.chamado_service import listar_fila_chamados  # noqa: E402

# Estrutura de grupos e rotas idêntica a A.MENU do projeto amatech-manutencao
MENU_GRUPOS = [
    (
        "Operação",
        [
            ("painel_maquinas", "dashboard", "Painel de máquinas"),
            ("abrir_chamado", "add_circle", "Abrir chamado"),
            ("meus_chamados", "assignment_ind", "Meus chamados"),
        ],
    ),
    (
        "Manutenção",
        [
            ("fila_chamados", "list", "Fila de chamados"),
            ("preventiva", "event_repeat", "Preventiva"),
            ("ordem_servico", "build", "Ordem de serviço"),
        ],
    ),
    (
        "Gestão",
        [
            ("dashboard", "monitoring", "Indicadores"),
            ("historico", "history", "Histórico"),
            ("cadastros", "settings", "Cadastros"),
            ("auditoria", "fact_check", "Auditoria"),
        ],
    ),
]

CATALOGO_ROTAS = {
    "painel_maquinas": ("pages.01_painel_maquinas", "render"),
    "abrir_chamado": ("pages.02_abrir_chamado", "render"),
    "meus_chamados": ("pages.02_abrir_chamado", "render_meus_chamados"),
    "fila_chamados": ("pages.03_fila_chamados", "render"),
    "preventiva": ("pages.03_fila_chamados", "render_preventiva"),
    "ordem_servico": ("pages.04_ordem_servico", "render"),
    "dashboard": ("pages.05_dashboard", "render"),
    "historico": ("pages.06_historico", "render"),
    "cadastros": ("pages.07_cadastros", "render"),
    "auditoria": ("pages.06_historico", "render_auditoria"),
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
    st.session_state["pagina_atual"] = "painel_maquinas"


def _renderizar_tela_login() -> None:
    """Renderiza a Tela de Login idêntica ao design oficial AMATECH: fundo #0D1B2A e card centralizado."""
    st.markdown(
        """
        <style>
        /* Fundo global e remoção da sidebar/header na tela de login */
        .stApp {
          background-color: #0d1b2a !important;
        }
        section[data-testid="stSidebar"] {
          display: none !important;
        }
        header[data-testid="stHeader"] {
          display: none !important;
        }
        footer {
          display: none !important;
        }
        .block-container {
          max-width: 100% !important;
          padding-top: 2vh !important;
          padding-bottom: 4vh !important;
        }

        /* Card Central Branco */
        div[data-testid="stForm"] {
          background: #ffffff !important;
          border-radius: var(--radius-md) !important;
          padding: 28px 32px 20px 32px !important;
          box-shadow: 0 14px 40px rgba(0, 0, 0, 0.3) !important;
          border: 1px solid rgba(255, 255, 255, 0.15) !important;
          max-width: 440px !important;
          margin: 0 auto !important;
        }

        /* Tipografia do Card */
        .login-title {
          color: #0d1b2a;
          font-size: 26px;
          font-weight: 800;
          text-align: center;
          margin: 0 0 6px 0;
          letter-spacing: 0.5px;
          font-family: var(--font-sans);
        }
        .login-sub {
          color: #4d5b6e;
          font-size: 13.5px;
          text-align: center;
          margin: 0 0 22px 0;
          font-weight: 400;
          font-family: var(--font-sans);
        }

        /* Inputs e Rótulos */
        div[data-testid="stForm"] label {
          color: #4d5b6e !important;
          font-size: 13px !important;
          font-weight: 500 !important;
          margin-bottom: 3px !important;
        }
        div[data-testid="stForm"] input {
          height: 42px !important;
          border: 1px solid #d6dde6 !important;
          border-radius: 6px !important;
          font-size: 14px !important;
          color: #142133 !important;
          background-color: #ffffff !important;
        }
        div[data-testid="stForm"] input:focus {
          border-color: #1f5fd6 !important;
          box-shadow: 0 0 0 2px rgba(31, 95, 214, 0.2) !important;
        }

        /* Botão ENTRAR */
        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {
          background-color: #1f5fd6 !important;
          color: #ffffff !important;
          font-weight: 700 !important;
          font-size: 14px !important;
          border-radius: 6px !important;
          height: 42px !important;
          margin-top: 8px !important;
          border: none !important;
          box-shadow: 0 2px 4px rgba(31, 95, 214, 0.3) !important;
          transition: all 0.2s ease !important;
        }
        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button:hover {
          background-color: #1747a6 !important;
          box-shadow: 0 4px 10px rgba(31, 95, 214, 0.45) !important;
        }

        /* Rodapé interno do Card */
        .login-card-footer {
          text-align: center;
          color: #4d5b6e;
          font-size: 11.5px;
          margin-top: 18px;
          font-weight: 400;
          font-family: var(--font-sans);
        }

        /* Botões de Demonstração / Acesso Rápido */
        .login-demo-header {
          text-align: center;
          color: #a9b8ca;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          font-weight: 600;
          margin: 18px 0 8px 0;
        }
        div[data-testid="stMainBlockContainer"] div.stButton > button {
          background-color: rgba(255, 255, 255, 0.1) !important;
          color: #ffffff !important;
          border: 1px solid rgba(255, 255, 255, 0.22) !important;
          border-radius: 6px !important;
          font-size: 12.5px !important;
          font-weight: 500 !important;
          padding: 8px 12px !important;
          margin-bottom: 3px !important;
          transition: all 0.2s ease !important;
        }
        div[data-testid="stMainBlockContainer"] div.stButton > button:hover {
          background-color: rgba(255, 255, 255, 0.2) !important;
          border-color: #ffffff !important;
          color: #ffffff !important;
          transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    amatech.tela_login("MNT")
    col_esq, col_card, col_dir = st.columns([1, 1.15, 1])

    with col_card:
        with st.form("form_login_amatech"):

            matricula_in = st.text_input(
                "Matrícula",
                value="OP-10234",
                placeholder="Ex.: OP-10234",
            )
            senha_in = st.text_input(
                "Senha",
                value="123456",
                type="password",
                placeholder="••••••••",
            )
            btn_entrar = st.form_submit_button(
                "Entrar",
                type="primary",
                use_container_width=True,
            )

            st.markdown(
                '<div class="login-card-footer">Acesso conforme perfil: Operador · Técnico · Gestor</div>',
                unsafe_allow_html=True,
            )

            if btn_entrar:
                try:
                    _realizar_login(matricula_in, senha_in)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.markdown(
            '<div class="login-demo-header">⚡ Contas de demonstração · Acesso em 1 clique</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "Carlos Mendonça / Maria Souza  —  OP-10234 · Operador",
            key="btn_demo_op",
            use_container_width=True,
        ):
            _realizar_login("OP-10234", "123456")
            st.rerun()

        if st.button(
            "João Lima Silva  —  TEC-2001 · Técnico",
            key="btn_demo_tec",
            use_container_width=True,
        ):
            _realizar_login("TEC-2001", "123456")
            st.rerun()

        if st.button(
            "Orlando Vandres / Carlos Mota  —  GES-0001 · Gestor",
            key="btn_demo_ges",
            use_container_width=True,
        ):
            _realizar_login("GES-0001", "123456")
            st.rerun()


def _renderizar_sidebar_e_navegacao(usuario: dict) -> str:
    """Renderiza a sidebar escura (--navy-dark #0d1b2a) com grupos de menu e badge da fila."""
    perfil = usuario["perfil"]
    telas_permitidas = PERMISSOES_POR_PERFIL.get(perfil, ["painel_maquinas"])

    if st.session_state.get("pagina_atual") not in telas_permitidas:
        st.session_state["pagina_atual"] = telas_permitidas[0]

    pagina_ativa = st.session_state.get("pagina_atual", telas_permitidas[0])
    qtd_fila = len(listar_fila_chamados())

    with st.sidebar:
        for nome_grupo, itens in MENU_GRUPOS:
            itens_visiveis = [it for it in itens if it[0] in telas_permitidas]
            if not itens_visiveis:
                continue
            st.markdown(f'<div class="sb-nav-grupo">{esc(nome_grupo)}</div>', unsafe_allow_html=True)
            for cod_rota, icone, texto in itens_visiveis:
                label = texto
                if cod_rota == "fila_chamados" and qtd_fila > 0:
                    label = f"{texto} ({qtd_fila})"
                tipo_btn = "primary" if pagina_ativa == cod_rota else "secondary"
                if st.button(
                    label,
                    key=f"nav_btn_{cod_rota}",
                    icon=f":material/{icone}:",
                    type=tipo_btn,
                    use_container_width=True,
                ):
                    st.session_state["pagina_atual"] = cod_rota
                    st.rerun()

        st.markdown(
            f"""
            <div class="sb-rodape">
              <strong>{esc(usuario['nome'])}</strong>
              {esc(rotulo_amigavel(perfil))} · {esc(usuario['matricula'])}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.sidebar.link_button(
            "Hub do ERP",
            url=os.environ.get("ERP_PORTAL_URL", "http://localhost:8500"),
            icon=":material/apps:",
            use_container_width=True,
        )
        if st.button("Sair do sistema", key="btn_logout_sb", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    return st.session_state["pagina_atual"]


def main() -> None:
    """Inicializa banco, estilos e roteador de telas. A API roda à parte (python -m uvicorn api:app --port 5002)."""
    ensure_database_initialized()
    aplicar_estilos_amatech()

    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        _renderizar_tela_login()
        return

    codigo_pagina = _renderizar_sidebar_e_navegacao(usuario)
    modulo_path, func_name = CATALOGO_ROTAS.get(
        codigo_pagina, ("pages.01_painel_maquinas", "render")
    )
    modulo = importlib.import_module(modulo_path)
    getattr(modulo, func_name)()


if __name__ == "__main__":
    main()
