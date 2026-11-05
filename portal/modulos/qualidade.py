"""
Módulo 2: Controle da Qualidade e Defeitos (QLD).
Renderiza diretamente no ERP unificado as telas e regras de negócio de `qualidade/`,
compartilhando a sessão autenticada e a integração in-process com Rastreabilidade e Manutenção.
"""
from typing import Any

import streamlit as st

from identidade import amatech
from integracao_local import ambiente_modulo


def renderizar_modulo_qualidade(usuario_erp: dict[str, Any]) -> None:
    """Renderiza o módulo de Controle da Qualidade integrado ao ERP."""
    usuario_qld = st.session_state.get("usuario_autenticado") or {
        "id": 1,
        "matricula": usuario_erp["matricula"],
        "nome": usuario_erp["nome"],
        "perfil": "Operador",
    }

    with ambiente_modulo("qualidade"):
        import banco
        import integracao
        import migracao
        import permissoes
        from telas.dashboard import mostrar_dashboard
        from telas.historico_ocorrencias import mostrar_historico_ocorrencias
        from telas.registro_ocorrencia import mostrar_registro_ocorrencia

        banco.preparar_banco()
        migracao.migrar()

        # Filtra páginas permitidas para a persona (excluindo 'Usuários', que é centralizado no Módulo 5 do ERP)
        paginas = [p for p in permissoes.paginas_permitidas(usuario_qld) if p != "Usuários"]
        if not paginas:
            paginas = ["Dashboard"]

        if "qld_subpagina" not in st.session_state or st.session_state["qld_subpagina"] not in paginas:
            st.session_state["qld_subpagina"] = paginas[0]

        icones_qld = {
            "Dashboard": ":material/analytics:",
            "Registrar ocorrência": ":material/add_alert:",
            "Histórico": ":material/history:",
            "Histórico de ocorrências": ":material/history:",
        }

        with st.sidebar:
            st.markdown('<div class="sb-nav-grupo">Módulo Qualidade (QLD)</div>', unsafe_allow_html=True)
            for pag in paginas:
                ativo = st.session_state["qld_subpagina"] == pag
                if st.button(
                    pag,
                    icon=icones_qld.get(pag, ":material/circle:"),
                    key=f"qld_nav_{pag}",
                    type="primary" if ativo else "secondary",
                    width="stretch",
                ):
                    st.session_state["qld_subpagina"] = pag
                    st.rerun()

            if permissoes.tem_permissao(usuario_qld, permissoes.ATUALIZAR_CADASTROS):
                st.markdown('<div class="sb-nav-grupo">Integração entre Setores</div>', unsafe_allow_html=True)
                if st.button(
                    "Sincronizar Cadastros (RAS/MNT)",
                    icon=":material/sync:",
                    key="qld_btn_sinc_setores",
                    width="stretch",
                ):
                    with st.spinner("Sincronizando cadastros com RAS e MNT..."):
                        for tipo, mensagem in integracao.sincronizar_cadastros():
                            if tipo == "sucesso":
                                st.toast(f"✅ {mensagem}")
                            else:
                                st.toast(f"⚠️ {mensagem}")

        amatech.cabecalho(
            "QLD",
            [
                ("Turno", amatech.turno_atual()),
                (
                    usuario_qld["perfil"],
                    f"{amatech.esc(usuario_qld['nome'])} · <span class='am-codigo'>{amatech.esc(usuario_qld['matricula'])}</span>",
                ),
            ],
        )

        sub = st.session_state["qld_subpagina"]
        if sub == "Dashboard":
            mostrar_dashboard()
        elif sub == "Registrar ocorrência":
            mostrar_registro_ocorrencia(usuario_qld)
        elif sub in ("Histórico", "Histórico de ocorrências"):
            mostrar_historico_ocorrencias(usuario_qld)
