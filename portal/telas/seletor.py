"""
Tela Pós-Login: Seletor de Módulos do ERP AMATECH.
Exibe estritamente os módulos que a persona do usuário logado tem poder para acessar
e navega internamente no mesmo sistema (mesma porta e mesma sessão autenticada).
"""
import sys
from pathlib import Path
from typing import Any

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from identidade import amatech
from permissoes import (
    CATALOGO_MODULOS,
    DESCRICAO_PERSONAS,
    modulos_permitidos,
    obter_papel_no_modulo,
)


def mostrar_seletor(usuario: dict[str, Any]) -> None:
    """Renderiza a tela de Seleção de Módulos pós-login com filtro estrito por Persona."""
    amatech.cabecalho(
        "ERP",
        [
            ("Turno", amatech.turno_atual()),
            ("Colaborador", f"{amatech.esc(usuario['nome'])} · <span class='am-codigo'>{amatech.esc(usuario['matricula'])}</span>"),
            ("Persona", amatech.esc(usuario["perfil"])),
        ],
    )

    modulos = modulos_permitidos(usuario)
    total_catalogo = len(CATALOGO_MODULOS)
    desc_persona = DESCRICAO_PERSONAS.get(usuario["perfil"], "")

    amatech.titulo(
        "Selecione o Módulo Operacional",
        f"Bem-vindo(a), {usuario['nome']}. Sua persona ({usuario['perfil']}) possui acesso habilitado a {len(modulos)} de {total_catalogo} módulos do ERP AMATECH.",
    )

    if desc_persona:
        st.caption(f"**Escopo Corporativo da Persona:** {desc_persona}")

    if not modulos:
        st.warning(
            "Seu perfil de usuário não possui permissão para acessar nenhum módulo ativo no momento. Contate o Administrador."
        )
        return

    # Grade de cartões dos módulos autorizados (2 colunas)
    col1, col2 = st.columns(2, gap="medium")
    cols = [col1, col2]

    for idx, modulo in enumerate(modulos):
        coluna = cols[idx % 2]
        papel = obter_papel_no_modulo(usuario, modulo.id)

        with coluna:
            with st.container(border=True):
                topo_l, topo_r = st.columns([3.5, 1])
                with topo_l:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div>
                                <h3 style="margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--tinta);">
                                    {amatech.esc(modulo.nome)}
                                </h3>
                                <small style="color: var(--tinta-2); font-weight: 500;">{amatech.esc(modulo.categoria)}</small>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with topo_r:
                    st.markdown(
                        f"""
                        <div style="text-align: right;">
                            <span class="am-setor" style="font-size: 11px;">{amatech.esc(modulo.sigla)}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<p style='color: var(--tinta); font-size: 0.9rem; min-height: 44px; margin: 0.7rem 0;'>{amatech.esc(modulo.descricao)}</p>",
                    unsafe_allow_html=True,
                )

                st.info(f"**Poder de Acesso no Módulo:** {papel}", icon=":material/verified_user:")

                if st.button(
                    f"Entrar em {modulo.nome} ({modulo.sigla})",
                    icon=modulo.icone,
                    key=f"btn_entrar_modulo_{modulo.id}",
                    type="primary",
                    width="stretch",
                ):
                    st.session_state["modulo_ativo"] = modulo.id
                    st.rerun()
