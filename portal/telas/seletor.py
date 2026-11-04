"""
Tela do Seletor de Módulos (ERP Launcher / Hub Modular).
Exibe pós-login estritamente os módulos autorizados para a persona do colaborador.
"""
import sys
from pathlib import Path
from typing import Any

import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from identidade import amatech
from config import APIS
from permissoes import (
    MODULO_USUARIOS,
    modulos_permitidos,
    obter_papel_no_modulo,
)


def checar_status_servicos() -> dict[str, bool]:
    """Testa a conectividade com as APIs do ecossistema."""
    status = {}
    for nome, url in APIS.items():
        try:
            r = requests.get(url, timeout=1.0)
            status[nome] = r.status_code == 200
        except Exception:
            status[nome] = False
    return status


def mostrar_seletor(usuario: dict[str, Any]) -> None:
    """Renderiza o Hub Modular do ERP com os cartões restritos por perfil."""
    modulos = modulos_permitidos(usuario)

    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h2 style="font-family: var(--font-display); font-size: 1.6rem; font-weight: 700; color: var(--tinta); margin: 0 0 0.25rem 0;">
                Módulos Industriais Disponíveis
            </h2>
            <p style="color: var(--tinta-2); font-size: 0.95rem; margin: 0;">
                Conforme seu perfil corporativo (<b>{usuario['perfil']}</b>), selecione o módulo operacional para atuar:
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not modulos:
        st.warning("Seu perfil de usuário não possui permissão para acessar nenhum módulo ativo no momento. Contate o Administrador.")
        return

    # Grid de cartões de módulos (2 colunas)
    col1, col2 = st.columns(2, gap="medium")
    cols = [col1, col2]

    for idx, modulo in enumerate(modulos):
        coluna = cols[idx % 2]
        papel = obter_papel_no_modulo(usuario, modulo.id)

        with coluna:
            with st.container(border=True):
                topo_l, topo_r = st.columns([3, 1])
                with topo_l:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.4rem;">{modulo.icone}</span>
                            <div>
                                <h3 style="margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--tinta);">
                                    {modulo.nome}
                                </h3>
                                <small style="color: var(--tinta-2); font-weight: 500;">{modulo.categoria}</small>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with topo_r:
                    st.markdown(
                        f"""
                        <div style="text-align: right;">
                            <span class="am-setor" style="font-size: 11px;">{modulo.sigla}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown(f"<p style='color: var(--tinta); font-size: 0.9rem; min-height: 48px; margin: 0.8rem 0;'>{modulo.descricao}</p>", unsafe_allow_html=True)

                st.info(f"**Seu Poder de Acesso:** {papel}", icon=":material/badge:")

                # Ação de navegação
                if modulo.id == MODULO_USUARIOS:
                    if st.button("Gerenciar Usuários e Acessos", icon=":material/arrow_forward:", key=f"btn_{modulo.id}", type="primary", width="stretch"):
                        st.session_state["modulo_ativo"] = MODULO_USUARIOS
                        st.rerun()
                else:
                    st.link_button(
                        f"Abrir Módulo ({modulo.sigla})",
                        url=modulo.url,
                        icon=":material/open_in_new:",
                        type="primary",
                        width="stretch",
                    )

    st.markdown("---")

    # Monitor de Conectividade dos Serviços do ERP
    with st.expander("Monitor de Conectividade do Ecossistema AMATECH", expanded=False):
        status_servicos = checar_status_servicos()
        c1, c2, c3, c4 = st.columns(4)
        for c, (servico, online) in zip([c1, c2, c3, c4], status_servicos.items()):
            with c:
                cor = "green" if online else "red"
                texto = "ONLINE" if online else "OFFLINE"
                st.markdown(
                    f"""
                    <div style="background: var(--superficie); border: 1px solid var(--linha); border-radius: 6px; padding: 10px; text-align: center;">
                        <small style="color: var(--tinta-2); display: block; font-weight: 600;">{servico}</small>
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {cor}; margin-right: 6px;"></span>
                        <b style="color: {cor}; font-size: 12px;">{texto}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
