"""
Módulo 3: Gestão da Manutenção de Ativos (MNT).
Renderiza diretamente no ERP unificado todas as telas e serviços de `manutencao/`,
preservando a identidade visual AMATECH e o controle de acesso por persona.
"""
import importlib
from typing import Any

import streamlit as st

from integracao_local import MAPA_PERFIL_MANUTENCAO, ambiente_modulo
try:
    from portal.permissoes import (
        ADMINISTRADOR,
        SUPERVISOR,
        TECNICO,
        OPERADOR,
        resolver_perfil_canonico,
    )
except ImportError:
    from permissoes import (
        ADMINISTRADOR,
        SUPERVISOR,
        TECNICO,
        OPERADOR,
        resolver_perfil_canonico,
    )

# Catálogo completo e corrigido de rotas internas da Manutenção
CATALOGO_ROTAS: dict[str, tuple[str, str, str, str, list[str]]] = {
    "painel_maquinas": (
        "Painel de máquinas",
        "pages.01_painel_maquinas",
        "render",
        ":material/precision_manufacturing:",
        ["OPERADOR", "TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO, OPERADOR],
    ),
    "abrir_chamado": (
        "Abrir chamado",
        "pages.02_abrir_chamado",
        "render",
        ":material/add_alert:",
        ["OPERADOR", "GESTOR", ADMINISTRADOR, SUPERVISOR, OPERADOR],
    ),
    "meus_chamados": (
        "Meus chamados",
        "pages.02_abrir_chamado",
        "render_meus_chamados",
        ":material/assignment_ind:",
        ["OPERADOR", "GESTOR", ADMINISTRADOR, SUPERVISOR, OPERADOR],
    ),
    "fila_chamados": (
        "Fila de chamados",
        "pages.03_fila_chamados",
        "render",
        ":material/format_list_bulleted:",
        ["TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO],
    ),
    "preventiva": (
        "Manutenção preventiva",
        "pages.03_fila_chamados",
        "render_preventiva",
        ":material/event_repeat:",
        ["TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO],
    ),
    "ordem_servico": (
        "Ordem de serviço",
        "pages.04_ordem_servico",
        "render",
        ":material/build_circle:",
        ["TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO],
    ),
    "indicadores": (
        "Indicadores",
        "pages.05_dashboard",
        "render",
        ":material/monitoring:",
        ["TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO],
    ),
    "dashboard": (
        "Indicadores",
        "pages.05_dashboard",
        "render",
        ":material/monitoring:",
        ["TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO],
    ),
    "historico": (
        "Histórico e relatórios",
        "pages.06_historico",
        "render",
        ":material/history:",
        ["TECNICO", "GESTOR", ADMINISTRADOR, SUPERVISOR, TECNICO],
    ),
    "cadastros": (
        "Cadastros",
        "pages.07_cadastros",
        "render",
        ":material/settings:",
        ["GESTOR", ADMINISTRADOR, SUPERVISOR],
    ),
    "auditoria": (
        "Auditoria de status",
        "pages.06_historico",
        "render_auditoria",
        ":material/fact_check:",
        ["GESTOR", ADMINISTRADOR, SUPERVISOR],
    ),
}

MENU_GRUPOS: list[tuple[str, list[str]]] = [
    ("Operação", ["painel_maquinas", "abrir_chamado", "meus_chamados"]),
    ("Manutenção Técnica", ["fila_chamados", "preventiva", "ordem_servico"]),
    ("Gestão", ["indicadores", "historico", "cadastros", "auditoria"]),
]


def renderizar_modulo_manutencao(usuario_erp: dict[str, Any]) -> None:
    """Renderiza o módulo de Gestão da Manutenção integrado ao ERP."""
    perfil_erp = usuario_erp.get("perfil", "OPERADOR")
    perfil_canonico = resolver_perfil_canonico(perfil_erp)
    perfil_mnt = MAPA_PERFIL_MANUTENCAO.get(perfil_canonico, "OPERADOR")

    # Garante que o usuario_logado esteja sempre completo e sincronizado na sessão
    usuario_mnt = {
        "id": usuario_erp.get("id", 1),
        "nome": usuario_erp.get("nome", "Usuário"),
        "matricula": usuario_erp.get("matricula", "MAT-0001"),
        "perfil": perfil_mnt,
        "ativo": True,
    }
    st.session_state["usuario_logado"] = usuario_mnt

    # Mapeia rotas permitidas para o perfil do usuário
    rotas_permitidas = [
        cod for cod, info in CATALOGO_ROTAS.items()
        if (perfil_mnt in info[4] or perfil_canonico in info[4]) and cod not in ("dashboard",)
    ]
    if not rotas_permitidas:
        rotas_permitidas = ["painel_maquinas"]

    # Validação e normalização da rota ativa
    pagina_solicitada = st.session_state.get("pagina_atual")
    if pagina_solicitada == "dashboard":
        pagina_solicitada = "indicadores"
    elif pagina_solicitada == "historico_relatorios":
        pagina_solicitada = "historico"

    if not pagina_solicitada or pagina_solicitada not in rotas_permitidas:
        pagina_solicitada = rotas_permitidas[0]

    st.session_state["pagina_atual"] = pagina_solicitada
    pagina_ativa = pagina_solicitada

    # Menu lateral seguindo rigorosamente o design unificado dos outros módulos
    with st.sidebar:
        st.markdown('<div class="sb-nav-grupo">Módulo Manutenção (MNT)</div>', unsafe_allow_html=True)
        for nome_grupo, codigos in MENU_GRUPOS:
            visiveis = [c for c in codigos if c in rotas_permitidas]
            if not visiveis:
                continue
            st.markdown(f'<div class="sb-nav-grupo" style="padding-top:6px; opacity:0.85;">{nome_grupo}</div>', unsafe_allow_html=True)
            for cod in visiveis:
                rotulo, _, _, icone, _ = CATALOGO_ROTAS[cod]
                ativo = (cod == pagina_ativa)
                if st.button(
                    rotulo,
                    icon=icone,
                    key=f"mnt_nav_{cod}",
                    type="primary" if ativo else "secondary",
                    width="stretch",
                ):
                    st.session_state["pagina_atual"] = cod
                    st.rerun()

    # Execução isolada no ambiente de manutenção
    with ambiente_modulo("manutencao"):
        from database import ensure_database_initialized
        from ui_components import aplicar_estilos_amatech

        ensure_database_initialized()
        aplicar_estilos_amatech()

        _, modulo_path, fn_name, _, _ = CATALOGO_ROTAS[pagina_ativa]
        try:
            modulo = importlib.import_module(modulo_path)
            importlib.reload(modulo)
            fn_render = getattr(modulo, fn_name, getattr(modulo, "render", None))
            if fn_render:
                fn_render()
            else:
                st.error(f"Função '{fn_name}' não encontrada no módulo {modulo_path}.")
        except Exception as exc:
            st.error(f"Erro ao carregar tela da Manutenção ({modulo_path}): {exc}")
            import traceback
            st.code(traceback.format_exc())
