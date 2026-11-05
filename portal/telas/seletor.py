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
        breadcrumb="ERP AMATECH · HUB DE MÓDULOS",
    )

    if desc_persona:
        st.html(
            f"""
            <div style="background: var(--superficie); border: 1px solid var(--linha); border-left: 3px solid var(--sinal); border-radius: var(--radius-sm); padding: 8px 14px; margin-bottom: 16px; font-size: 13px; color: var(--tinta-2);">
                <strong style="color: var(--tinta);">Escopo da Persona ({amatech.esc(usuario['perfil'])}):</strong> {amatech.esc(desc_persona)}
            </div>
            """
        )

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
                topo_l, topo_r = st.columns([3.5, 1.2])
                with topo_l:
                    st.html(
                        f"""
                        <div>
                            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--tinta);">
                                {amatech.esc(modulo.nome)}
                            </h3>
                            <small style="color: var(--tinta-2); font-weight: 500;">{amatech.esc(modulo.categoria)}</small>
                        </div>
                        """
                    )
                with topo_r:
                    st.html(
                        f"""
                        <div style="text-align: right;">
                            {amatech.badge_setor(modulo.sigla)}
                        </div>
                        """
                    )

                st.html(
                    f"<p style='color: var(--tinta); font-size: 0.88rem; line-height: 1.45; min-height: 42px; margin: 0.6rem 0;'>{amatech.esc(modulo.descricao)}</p>"
                )

                st.html(
                    f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: var(--superficie-2); border-radius: var(--radius-sm); margin-bottom: 12px; border: 1px solid var(--linha);">
                        <span style="font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--tinta-2); font-weight: 600;">Poder de Acesso</span>
                        <span style="font-size: 12px; font-weight: 600; color: var(--tinta);">{amatech.esc(papel)}</span>
                    </div>
                    """
                )

                if st.button(
                    f"Entrar em {modulo.nome} ({modulo.sigla})",
                    icon=modulo.icone,
                    key=f"btn_entrar_modulo_{modulo.id}",
                    type="primary",
                    width="stretch",
                ):
                    st.session_state["modulo_ativo"] = modulo.id
                    st.rerun()
