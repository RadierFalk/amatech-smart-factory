"""
Módulo 3: Gestão da Manutenção de Ativos (MNT).
Renderiza diretamente no ERP unificado todas as telas e serviços de `manutencao/`,
preservando a identidade visual AMATECH e o controle de acesso por persona.
"""
import importlib
from typing import Any

import streamlit as st

from integracao_local import ambiente_modulo

# Catálogo de rotas internas da Manutenção
CATALOGO_ROTAS: dict[str, tuple[str, str, str, list[str]]] = {
    "painel_maquinas": (
        "Painel de máquinas",
        "pages.01_painel_maquinas",
        ":material/precision_manufacturing:",
        ["OPERADOR", "TECNICO", "GESTOR"],
    ),
    "abrir_chamado": (
        "Abrir chamado",
        "pages.02_abrir_chamado",
        ":material/add_alert:",
        ["OPERADOR", "GESTOR"],
    ),
    "meus_chamados": (
        "Meus chamados",
        "pages.03_meus_chamados",
        ":material/assignment_ind:",
        ["OPERADOR", "GESTOR"],
    ),
    "fila_chamados": (
        "Fila de chamados",
        "pages.04_fila_chamados",
        ":material/format_list_bulleted:",
        ["TECNICO", "GESTOR"],
    ),
    "preventiva": (
        "Manutenção preventiva",
        "pages.05_preventiva",
        ":material/event_repeat:",
        ["TECNICO", "GESTOR"],
    ),
    "ordem_servico": (
        "Ordem de serviço",
        "pages.05_ordem_servico",
        ":material/build_circle:",
        ["TECNICO", "GESTOR"],
    ),
    "indicadores": (
        "Indicadores",
        "pages.06_indicadores",
        ":material/monitoring:",
        ["TECNICO", "GESTOR"],
    ),
    "historico": (
        "Histórico e relatórios",
        "pages.06_historico",
        ":material/history:",
        ["TECNICO", "GESTOR"],
    ),
    "cadastros": (
        "Cadastros",
        "pages.07_cadastros",
        ":material/settings:",
        ["GESTOR"],
    ),
}

MENU_GRUPOS: list[tuple[str, list[str]]] = [
    ("Operação", ["painel_maquinas", "abrir_chamado", "meus_chamados"]),
    ("Manutenção", ["fila_chamados", "preventiva", "ordem_servico"]),
    ("Gestão", ["indicadores", "historico", "cadastros"]),
]


def renderizar_modulo_manutencao(usuario_erp: dict[str, Any]) -> None:
    """Renderiza o módulo de Gestão da Manutenção integrado ao ERP."""
    usuario_mnt = st.session_state.get("usuario_logado") or {
        "id": 1,
        "nome": usuario_erp["nome"],
        "matricula": usuario_erp["matricula"],
        "perfil": "OPERADOR",
        "ativo": True,
    }
    perfil_mnt = usuario_mnt.get("perfil", "OPERADOR")

    rotas_permitidas = [
        cod for cod, info in CATALOGO_ROTAS.items() if perfil_mnt in info[3]
    ]
    if not rotas_permitidas:
        rotas_permitidas = ["painel_maquinas"]

    if (
        "pagina_atual" not in st.session_state
        or st.session_state["pagina_atual"] not in rotas_permitidas
    ):
        st.session_state["pagina_atual"] = rotas_permitidas[0]

    pagina_ativa = st.session_state["pagina_atual"]

    with st.sidebar:
        for nome_grupo, codigos in MENU_GRUPOS:
            visiveis = [c for c in codigos if c in rotas_permitidas]
            if not visiveis:
                continue
            st.markdown(f'<div class="sb-nav-grupo">MNT · {nome_grupo}</div>', unsafe_allow_html=True)
            for cod in visiveis:
                rotulo, _, icone, _ = CATALOGO_ROTAS[cod]
                ativo = cod == pagina_ativa
                if st.button(
                    rotulo,
                    icon=icone,
                    key=f"mnt_nav_{cod}",
                    type="primary" if ativo else "secondary",
                    width="stretch",
                ):
                    st.session_state["pagina_atual"] = cod
                    st.rerun()

    with ambiente_modulo("manutencao"):
        from database import ensure_database_initialized
        from ui_components import aplicar_estilos_amatech

        ensure_database_initialized()
        aplicar_estilos_amatech()

        _, modulo_path, _, _ = CATALOGO_ROTAS[st.session_state["pagina_atual"]]
        modulo = importlib.import_module(modulo_path)
        modulo.render()
