"""
Ponto de Entrada Principal da Aplicação Streamlit (management-control).
AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção.
Replica fielmente o design, login split, sidebar agrupada e todas as rotas do projeto amatech-manutencao.
"""
import importlib
import streamlit as st

st.set_page_config(
    page_title="AMATECH · Controle da Manutenção",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

from api import iniciar_api_em_background
from config import API_PORT
from database import ensure_database_initialized
from services.auth_service import PERMISSOES_POR_PERFIL, autenticar_usuario
from services.chamado_service import listar_fila_chamados
from ui_components import aplicar_estilos_amatech, esc, rotulo_amigavel

# Estrutura de grupos e rotas idêntica a A.MENU do projeto amatech-manutencao
MENU_GRUPOS = [
    (
        "Operação",
        [
            ("painel_maquinas", "▦", "Painel de máquinas"),
            ("abrir_chamado", "＋", "Abrir chamado"),
            ("meus_chamados", "☑", "Meus chamados"),
        ],
    ),
    (
        "Manutenção",
        [
            ("fila_chamados", "≡", "Fila de chamados"),
            ("preventiva", "⟳", "Preventiva"),
            ("ordem_servico", "🗎", "Ordem de serviço"),
        ],
    ),
    (
        "Gestão",
        [
            ("dashboard", "◫", "Dashboard"),
            ("historico", "⌸", "Histórico"),
            ("cadastros", "⚙", "Cadastros"),
            ("auditoria", "⧉", "Auditoria"),
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
    """Renderiza a Tela de Login idêntica ao design oficial AMATECH: fundo #1F3A5F e card centralizado."""
    st.markdown(
        """
        <style>
        /* Fundo global e remoção da sidebar/header na tela de login */
        .stApp {
          background-color: #1f3a5f !important;
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
          padding-top: 6vh !important;
          padding-bottom: 4vh !important;
        }

        /* Card Central Branco */
        div[data-testid="stForm"] {
          background: #ffffff !important;
          border-radius: 14px !important;
          padding: 38px 40px 28px 40px !important;
          box-shadow: 0 14px 40px rgba(0, 0, 0, 0.3) !important;
          border: 1px solid rgba(255, 255, 255, 0.15) !important;
          max-width: 440px !important;
          margin: 0 auto !important;
        }

        /* Tipografia do Card */
        .login-title {
          color: #1f3a5f;
          font-size: 26px;
          font-weight: 800;
          text-align: center;
          margin: 0 0 6px 0;
          letter-spacing: 0.5px;
          font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .login-sub {
          color: #5a6e85;
          font-size: 13.5px;
          text-align: center;
          margin: 0 0 22px 0;
          font-weight: 400;
          font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* Inputs e Rótulos */
        div[data-testid="stForm"] label {
          color: #334155 !important;
          font-size: 13px !important;
          font-weight: 500 !important;
          margin-bottom: 3px !important;
        }
        div[data-testid="stForm"] input {
          height: 42px !important;
          border: 1px solid #cbd5e1 !important;
          border-radius: 6px !important;
          font-size: 14px !important;
          color: #1e293b !important;
          background-color: #ffffff !important;
        }
        div[data-testid="stForm"] input:focus {
          border-color: #2e75b6 !important;
          box-shadow: 0 0 0 2px rgba(46, 117, 182, 0.2) !important;
        }

        /* Botão ENTRAR */
        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {
          background-color: #2e75b6 !important;
          color: #ffffff !important;
          font-weight: 700 !important;
          font-size: 14px !important;
          letter-spacing: 0.6px !important;
          text-transform: uppercase !important;
          border-radius: 6px !important;
          height: 42px !important;
          margin-top: 8px !important;
          border: none !important;
          box-shadow: 0 2px 4px rgba(46, 117, 182, 0.3) !important;
          transition: all 0.2s ease !important;
        }
        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button:hover {
          background-color: #246299 !important;
          box-shadow: 0 4px 10px rgba(46, 117, 182, 0.45) !important;
        }

        /* Rodapé interno do Card */
        .login-card-footer {
          text-align: center;
          color: #64748b;
          font-size: 11.5px;
          margin-top: 18px;
          font-weight: 400;
          font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* Botões de Demonstração / Acesso Rápido */
        .login-demo-header {
          text-align: center;
          color: #8fa5bd;
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

    col_esq, col_card, col_dir = st.columns([1, 1.15, 1])

    with col_card:
        with st.form("form_login_amatech"):
            st.markdown('<div class="login-title">AMATECH</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="login-sub">Sistema de Controle da Manutenção</div>',
                unsafe_allow_html=True,
            )

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
                "ENTRAR",
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
    """Renderiza a sidebar escura (--navy-dark #16293f) com grupos de menu e badge da fila."""
    perfil = usuario["perfil"]
    telas_permitidas = PERMISSOES_POR_PERFIL.get(perfil, ["painel_maquinas"])

    if st.session_state.get("pagina_atual") not in telas_permitidas:
        st.session_state["pagina_atual"] = telas_permitidas[0]

    pagina_ativa = st.session_state.get("pagina_atual", telas_permitidas[0])
    qtd_fila = len(listar_fila_chamados())

    with st.sidebar:
        st.markdown(
            """
            <div class="sb-marca">
              <div class="sb-logo-linha">
                <div class="sb-logo-simbolo">A</div>
                <div class="sb-logo-txt">
                  <strong>AMATECH</strong>
                  <span>Controle da Manutenção</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for nome_grupo, itens in MENU_GRUPOS:
            itens_visiveis = [it for it in itens if it[0] in telas_permitidas]
            if not itens_visiveis:
                continue
            st.markdown(f'<div class="sb-nav-grupo">{esc(nome_grupo)}</div>', unsafe_allow_html=True)
            for cod_rota, icone, texto in itens_visiveis:
                label = f"{icone}  {texto}"
                if cod_rota == "fila_chamados" and qtd_fila > 0:
                    label = f"{icone}  {texto}   ({qtd_fila})"
                tipo_btn = "primary" if pagina_ativa == cod_rota else "secondary"
                if st.button(
                    label,
                    key=f"nav_btn_{cod_rota}",
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

        if st.button("Sair do sistema", key="btn_logout_sb", use_container_width=True):
            st.session_state.clear()
            st.rerun()

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
    modulo_path, func_name = CATALOGO_ROTAS.get(
        codigo_pagina, ("pages.01_painel_maquinas", "render")
    )
    modulo = importlib.import_module(modulo_path)
    getattr(modulo, func_name)()


if __name__ == "__main__":
    main()
