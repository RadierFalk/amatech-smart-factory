"""
Módulo 4: Dashboard Industrial e Metas (DSH).
Renderiza diretamente no ERP unificado as telas analíticas e operacionais de `dashboard/`,
compartilhando a sessão autenticada e a sincronização in-process com Rastreabilidade,
Qualidade e Manutenção.
"""
import runpy
from typing import Any

import streamlit as st

from identidade import amatech
from integracao_local import ambiente_modulo

# Catálogo das telas do Dashboard Industrial (excluindo Usuários, centralizado no Módulo 5)
TELAS_DASHBOARD: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("pages/1_Painel.py", "Painel de Indicadores", ":material/analytics:", ("painel",)),
    ("pages/2_Producao_e_metas.py", "Produção e Metas", ":material/conveyor_belt:", ("producao", "metas")),
    ("pages/3_Qualidade.py", "Qualidade e Retrabalho", ":material/verified:", ("defeitos", "retrabalho")),
    ("pages/4_Paradas.py", "Paradas de Linha", ":material/timer_off:", ("paradas",)),
    ("pages/5_Perdas.py", "Perdas de Materiais", ":material/delete_sweep:", ("perdas",)),
    ("pages/6_Importacao.py", "Importação e Sincronização", ":material/cloud_sync:", ("importacao",)),
    ("pages/7_Historico.py", "Histórico e Exportação", ":material/history:", ("historico",)),
    ("pages/8_Cadastros.py", "Cadastros e Semáforo", ":material/tune:", ("cadastros", "limites")),
]


def renderizar_modulo_dashboard(usuario_erp: dict[str, Any]) -> None:
    """Renderiza o módulo de Dashboard Industrial integrado ao ERP."""
    with ambiente_modulo("dashboard") as pasta_dsh:
        from servicos.autenticacao import ServicoAutenticacao

        usuario_dsh = st.session_state.get("usuario")

        telas_permitidas: list[tuple[str, str, str]] = []
        for arquivo, titulo, icone, funcoes in TELAS_DASHBOARD:
            if any(ServicoAutenticacao.tem_permissao(usuario_dsh, f) for f in funcoes):
                rotulo = titulo
                if arquivo.endswith("8_Cadastros.py") and not ServicoAutenticacao.tem_permissao(
                    usuario_dsh, "cadastros"
                ):
                    rotulo = "Limites do Semáforo"
                telas_permitidas.append((arquivo, rotulo, icone))

        if not telas_permitidas:
            st.warning("Seu perfil não possui telas habilitadas no Dashboard Industrial.")
            return

        arquivos_validos = {t[0] for t in telas_permitidas}
        if (
            "dsh_subpagina" not in st.session_state
            or st.session_state["dsh_subpagina"] not in arquivos_validos
        ):
            st.session_state["dsh_subpagina"] = telas_permitidas[0][0]

        with st.sidebar:
            st.markdown('<div class="sb-nav-grupo">Módulo Dashboard (DSH)</div>', unsafe_allow_html=True)
            for arquivo, rotulo, icone in telas_permitidas:
                ativo = st.session_state["dsh_subpagina"] == arquivo
                if st.button(
                    rotulo,
                    icon=icone,
                    key=f"dsh_nav_{arquivo}",
                    type="primary" if ativo else "secondary",
                    width="stretch",
                ):
                    st.session_state["dsh_subpagina"] = arquivo
                    st.rerun()

        nome_perfil = usuario_dsh.perfil.nome if usuario_dsh else usuario_erp["perfil"]
        nome_usr = usuario_dsh.nome if usuario_dsh else usuario_erp["nome"]
        amatech.cabecalho(
            "DSH",
            [
                ("Turno", amatech.turno_atual()),
                (
                    nome_perfil,
                    f"{amatech.esc(nome_usr)} · <span class='am-codigo'>{amatech.esc(usuario_erp['matricula'])}</span>",
                ),
            ],
        )

        caminho_script = pasta_dsh / st.session_state["dsh_subpagina"]
        runpy.run_path(str(caminho_script), run_name="__main__")
