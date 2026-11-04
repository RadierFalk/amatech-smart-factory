"""
Módulo 1: Rastreabilidade de Produtos e Gestão de Materiais (RAS).
Interface nativa Streamlit integrada ao ERP AMATECH, reutilizando integralmente
a camada de serviços e regras de negócio de `rastreabilidade/app/servicos/`.
"""
from contextlib import closing
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from identidade import amatech
from integracao_local import ambiente_modulo

# Permissão de telas internas da Rastreabilidade por cargo setorial
TELAS_POR_CARGO: dict[str, list[tuple[str, str, str]]] = {
    "Administrador": [
        ("terminal", "Terminal do Operador", ":material/qr_code_scanner:"),
        ("producao", "Produção e Rastreabilidade", ":material/precision_manufacturing:"),
        ("solicitacoes", "Solicitações de Material", ":material/shopping_cart_checkout:"),
        ("baixas", "Baixas de Material", ":material/inventory:"),
        ("cadastros", "Cadastros e BOM", ":material/category:"),
        ("relatorios", "Relatórios e CSV", ":material/description:"),
    ],
    "Operador": [
        ("terminal", "Terminal do Operador", ":material/qr_code_scanner:"),
        ("producao", "Produção e Rastreabilidade", ":material/precision_manufacturing:"),
        ("solicitacoes", "Solicitações de Material", ":material/shopping_cart_checkout:"),
    ],
    "Inspetor de Qualidade": [
        ("terminal", "Terminal do Operador", ":material/qr_code_scanner:"),
        ("producao", "Produção e Rastreabilidade", ":material/precision_manufacturing:"),
        ("relatorios", "Relatórios e CSV", ":material/description:"),
    ],
    "Almoxarife": [
        ("terminal", "Terminal do Operador", ":material/qr_code_scanner:"),
        ("solicitacoes", "Solicitações de Material", ":material/shopping_cart_checkout:"),
        ("baixas", "Baixas de Material", ":material/inventory:"),
        ("cadastros", "Componentes e Estoque", ":material/category:"),
        ("relatorios", "Relatórios e CSV", ":material/description:"),
    ],
}


def _executar_servico(fn, *args, **kwargs):
    """Executa função de serviço da Rastreabilidade capturando ErroNegocio e validações."""
    try:
        return True, fn(*args, **kwargs)
    except Exception as exc:
        msg = getattr(exc, "mensagem", None) or getattr(exc, "detail", None) or str(exc)
        return False, str(msg)


def _render_terminal(conn, usuario_ras: dict[str, Any], servicos: dict[str, Any]) -> None:
    amatech.titulo(
        "Terminal de Rastreabilidade e Chão de Fábrica",
        "Visão em tempo real do fluxo de montagem seriada, etapas da linha e alertas de estoque (BOM)",
    )

    dados = servicos["relatorios"].dashboard(conn)
    kpis = dados["kpis"]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        amatech.cartao("Iniciados Hoje", str(kpis["produtos_dia"]), "Unidades abertas na data")
    with c2:
        amatech.cartao("Em Produção", str(kpis["em_producao"]), "Unidades antes da expedição", "atencao")
    with c3:
        amatech.cartao("Aprovados", str(kpis["aprovados"]), "Unidades aprovadas nos testes", "ok")
    with c4:
        amatech.cartao(
            "Reprovados",
            str(kpis["reprovados"]),
            "Retidas por não conformidade",
            "critico" if kpis["reprovados"] > 0 else "ok",
        )
    with c5:
        amatech.cartao(
            "Solicitações Pendentes",
            str(kpis["solicitacoes_pendentes"]),
            "Aguardando baixa do almoxarifado",
            "atencao" if kpis["solicitacoes_pendentes"] > 0 else "ok",
        )
    with c6:
        amatech.cartao(
            "Estoque Crítico",
            str(kpis["estoque_critico"]),
            f"Componentes <= {dados['limite_estoque_critico']} un.",
            "critico" if kpis["estoque_critico"] > 0 else "ok",
        )

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    # Busca rápida por número de série
    with st.container(border=True):
        st.markdown("**🔎 Consulta Rápida de Unidade por Número de Série**")
        b_col1, b_col2 = st.columns([4, 1])
        with b_col1:
            termo_serie = st.text_input(
                "Número de Série ou ID da Produção",
                placeholder="Ex.: AMT-000001...",
                label_visibility="collapsed",
                key="ras_busca_rapida_serie",
            )
        with b_col2:
            if st.button("Localizar Série", type="primary", width="stretch", key="ras_btn_localizar"):
                if termo_serie.strip():
                    encontrados = servicos["producao"].listar_producoes(conn, q=termo_serie.strip())
                    if encontrados:
                        st.session_state["ras_producao_detalhe_id"] = encontrados[0]["id"]
                        st.session_state["ras_subpagina"] = "producao"
                        st.rerun()
                    else:
                        st.warning(f"Nenhuma produção localizada para '{termo_serie}'.")

    # Gráficos
    g_esq, g_dir = st.columns(2)
    with g_esq:
        por_status = dados.get("por_status", [])
        if por_status:
            fig = go.Figure(
                go.Bar(
                    x=[x["quantidade"] for x in por_status],
                    y=[x["status"] for x in por_status],
                    orientation="h",
                    marker_color=amatech.CORES["grafico-1"],
                    text=[str(x["quantidade"]) for x in por_status],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig.update_layout(
                title="Unidades por Etapa do Processo",
                height=300,
                margin=dict(l=10, r=45, t=40, b=10),
                xaxis=dict(visible=False),
                yaxis=dict(autorange="reversed"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with g_dir:
        ultimos_7 = dados.get("ultimos_dias", [])
        if ultimos_7:
            fig2 = go.Figure(
                go.Bar(
                    x=[x["data"][8:10] + "/" + x["data"][5:7] for x in ultimos_7],
                    y=[x["quantidade"] for x in ultimos_7],
                    marker_color=amatech.CORES["grafico-1"],
                    text=[str(x["quantidade"]) for x in ultimos_7],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig2.update_layout(
                title="Produções Iniciadas (Últimos 7 Dias)",
                height=300,
                margin=dict(l=10, r=20, t=40, b=10),
                yaxis=dict(visible=False),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    t_esq, t_dir = st.columns([1.4, 1])
    with t_esq:
        st.subheader("Últimas Produções Movimentadas")
        recentes = servicos["producao"].listar_producoes(conn, limite=10)
        if recentes:
            df_rec = pd.DataFrame(recentes)[
                ["numero_serie", "nome_modelo", "status_nome", "responsavel_nome", "atualizado_em"]
            ].rename(
                columns={
                    "numero_serie": "Nº de Série",
                    "nome_modelo": "Modelo",
                    "status_nome": "Etapa Atual",
                    "responsavel_nome": "Responsável",
                    "atualizado_em": "Atualizado em",
                }
            )
            st.dataframe(df_rec, hide_index=True, use_container_width=True)
        else:
            st.caption("Nenhuma produção registrada.")

    with t_dir:
        st.subheader("Alertas de Estoque Crítico (BOM)")
        criticos = dados.get("estoque_critico", [])
        if criticos:
            df_crit = pd.DataFrame(criticos)[
                ["codigo_sku", "nome", "qtd_estoque"]
            ].rename(
                columns={
                    "codigo_sku": "SKU",
                    "nome": "Componente",
                    "qtd_estoque": "Saldo",
                }
            )
            st.dataframe(df_crit, hide_index=True, use_container_width=True)
        else:
            st.success("Todos os componentes estão com saldo acima do nível crítico.")


def _render_producao(conn, usuario_ras: dict[str, Any], servicos: dict[str, Any]) -> None:
    amatech.titulo(
        "Produção e Rastreabilidade por Número de Série",
        "Inicie ordens seriadas, consulte o histórico de passagem pelas estações, avance etapas e registre não conformidades",
    )

    lista_status = servicos["cadastros"].listar_status(conn)
    lista_produtos = servicos["cadastros"].listar_produtos(conn)
    lista_usuarios = servicos["cadastros"].listar_usuarios(conn, apenas_ativos=True)

    # Seção para iniciar nova produção
    with st.expander("➕ Iniciar Nova Produção Seriada", expanded=False):
        if not lista_produtos:
            st.warning("Cadastre ao menos um produto antes de iniciar uma produção.")
        else:
            with st.form("ras_form_nova_producao"):
                c1, c2 = st.columns(2)
                opcoes_prd = {p["idprd"]: f"{p['nome_modelo']} ({p['codigo_modelo']})" for p in lista_produtos}
                opcoes_usr = {u["id"]: f"{u['nome']} ({u['matricula']})" for u in lista_usuarios}
                idx_usr = list(opcoes_usr.keys()).index(usuario_ras["id"]) if usuario_ras["id"] in opcoes_usr else 0

                prd_sel = c1.selectbox(
                    "Modelo do Produto",
                    options=list(opcoes_prd.keys()),
                    format_func=lambda k: opcoes_prd[k],
                )
                usr_sel = c2.selectbox(
                    "Responsável pela Etapa Inicial",
                    options=list(opcoes_usr.keys()),
                    index=idx_usr,
                    format_func=lambda k: opcoes_usr[k],
                )
                st.caption("O Número de Série (`AMT-...`) e o ID único da produção são gerados automaticamente.")
                if st.form_submit_button("Iniciar Produção", type="primary"):
                    ok, res = _executar_servico(
                        servicos["producao"].criar_producao,
                        conn,
                        prd_sel,
                        usr_sel,
                        usuario_ras,
                    )
                    if ok:
                        st.success(f"Produção **{res['numero_serie']}** iniciada na etapa **{res['status_nome']}**!")
                        st.session_state["ras_producao_detalhe_id"] = res["id"]
                        st.rerun()
                    else:
                        st.error(res)

    # Filtros de consulta
    f1, f2, f3 = st.columns([2, 1.3, 1.3])
    busca_q = f1.text_input(
        "Buscar por Nº de Série, ID da Produção ou Modelo",
        placeholder="Digite para filtrar...",
        key="ras_filtro_prod_q",
    )
    opcoes_st_filtro = {0: "Todas as etapas"} | {s["id"]: s["nome_status"] for s in lista_status}
    st_filtro = f2.selectbox(
        "Filtrar por Etapa",
        options=list(opcoes_st_filtro.keys()),
        format_func=lambda k: opcoes_st_filtro[k],
        key="ras_filtro_prod_status",
    )

    producoes = servicos["producao"].listar_producoes(
        conn,
        q=busca_q.strip() or None,
        status_id=st_filtro if st_filtro != 0 else None,
    )

    if not producoes:
        st.info("Nenhuma produção encontrada para os filtros selecionados.")
        return

    opcoes_detalhe = {
        p["id"]: f"{p['numero_serie']} · {p['nome_modelo']} ({p['status_nome']})"
        for p in producoes
    }
    id_pre = st.session_state.get("ras_producao_detalhe_id")
    if id_pre not in opcoes_detalhe:
        id_pre = producoes[0]["id"]

    id_selecionado = f3.selectbox(
        "Inspecionar / Operar Série",
        options=list(opcoes_detalhe.keys()),
        index=list(opcoes_detalhe.keys()).index(id_pre),
        format_func=lambda k: opcoes_detalhe[k],
        key="ras_select_prod_ativa",
    )
    st.session_state["ras_producao_detalhe_id"] = id_selecionado

    # Tabela geral
    df_prod = pd.DataFrame(producoes)[
        [
            "numero_serie",
            "id_unica_producao",
            "nome_modelo",
            "status_nome",
            "responsavel_nome",
            "data_inicio",
            "atualizado_em",
        ]
    ].rename(
        columns={
            "numero_serie": "Nº de Série",
            "id_unica_producao": "ID Produção",
            "nome_modelo": "Modelo",
            "status_nome": "Etapa Atual",
            "responsavel_nome": "Responsável",
            "data_inicio": "Início",
            "atualizado_em": "Última Atualização",
        }
    )
    st.dataframe(df_prod, hide_index=True, use_container_width=True)

    # Painel de Detalhes e Operação da Produção selecionada
    detalhe = servicos["producao"].obter_producao(conn, id_selecionado)
    st.divider()
    st.subheader(f"Dossiê da Unidade: {detalhe['numero_serie']} — {detalhe['nome_modelo']}")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        amatech.cartao("Número de Série", detalhe["numero_serie"], f"ID: {detalhe['id_unica_producao']}")
    with k2:
        tom_status = (
            "ok"
            if detalhe["status_nome"] == "Aprovado"
            else ("critico" if detalhe["status_nome"] == "Reprovado" else "atencao")
        )
        amatech.cartao("Etapa Atual", detalhe["status_nome"], f"Resp.: {detalhe.get('responsavel_nome') or '—'}", tom_status)
    with k3:
        amatech.cartao("Passagens Registradas", str(len(detalhe["historico"])), f"Início: {detalhe['data_inicio']}")
    with k4:
        amatech.cartao(
            "Pendências de Material",
            str(detalhe["materiais_pendentes"]),
            f"{len(detalhe['solicitacoes'])} solicitação(ões) BOM",
            "atencao" if detalhe["materiais_pendentes"] > 0 else "ok",
        )

    aba_avancar, aba_hist, aba_mat, aba_nc = st.tabs([
        ":material/fast_forward: Avançar Etapa",
        f":material/history: Histórico de Passagem ({len(detalhe['historico'])})",
        f":material/inventory_2: Materiais da Produção ({len(detalhe['solicitacoes'])})",
        f":material/report_problem: Não Conformidades ({len(detalhe['nao_conformidades'])})",
    ])

    with aba_avancar:
        opcoes_novo_status = {
            s["id"]: s["nome_status"]
            for s in lista_status
            if s["id"] != detalhe["status_atual_id"]
        }
        sugerido = detalhe.get("proxima_etapa_sugerida_id")
        idx_sug = (
            list(opcoes_novo_status.keys()).index(sugerido)
            if sugerido in opcoes_novo_status
            else 0
        )
        opcoes_usr = {u["id"]: f"{u['nome']} ({u['matricula']})" for u in lista_usuarios}
        idx_usr = list(opcoes_usr.keys()).index(usuario_ras["id"]) if usuario_ras["id"] in opcoes_usr else 0

        col_a1, col_a2 = st.columns(2)
        novo_st_id = col_a1.selectbox(
            "Nova Etapa de Produção",
            options=list(opcoes_novo_status.keys()),
            index=idx_sug,
            format_func=lambda k: opcoes_novo_status[k],
            key=f"ras_novo_st_{detalhe['id']}",
        )
        novo_resp_id = col_a2.selectbox(
            "Responsável pela Nova Etapa",
            options=list(opcoes_usr.keys()),
            index=idx_usr,
            format_func=lambda k: opcoes_usr[k],
            key=f"ras_novo_resp_{detalhe['id']}",
        )

        nome_st_escolhido = opcoes_novo_status[novo_st_id].strip().lower()
        eh_reprovacao = nome_st_escolhido == "reprovado"
        desc_falha = ""
        motivo_rep = ""
        if eh_reprovacao:
            st.warning("A mudança para **Reprovado** exige o preenchimento da falha encontrada e do motivo da reprovação.")
            desc_falha = st.text_input("Falha Encontrada *", key=f"ras_falha_{detalhe['id']}")
            motivo_rep = st.text_input("Motivo da Reprovação *", key=f"ras_motivo_{detalhe['id']}")

        if st.button("Confirmar Avanço de Etapa", type="primary", key=f"ras_btn_avancar_{detalhe['id']}"):
            ok, res = _executar_servico(
                servicos["producao"].avancar_etapa,
                conn,
                detalhe["id"],
                novo_st_id,
                novo_resp_id,
                usuario_ras,
                descricao_falha=desc_falha or None,
                motivo_reprovacao=motivo_rep or None,
            )
            if ok:
                st.success(f"Etapa de **{detalhe['numero_serie']}** atualizada para **{res['status_nome']}**!")
                st.rerun()
            else:
                st.error(res)

    with aba_hist:
        if detalhe["historico"]:
            df_h = pd.DataFrame(detalhe["historico"])[
                ["data_horario", "status_nome", "usuario_nome", "responsavel_nome", "origem_atualizacao"]
            ].rename(
                columns={
                    "data_horario": "Data / Hora",
                    "status_nome": "Etapa",
                    "usuario_nome": "Registrado por",
                    "responsavel_nome": "Responsável da Etapa",
                    "origem_atualizacao": "Origem",
                }
            )
            st.dataframe(df_h, hide_index=True, use_container_width=True)
        else:
            st.caption("Sem histórico de passagens.")

    with aba_mat:
        if st.button(
            "Gerar Solicitações Padrão da Lista Técnica (BOM)",
            type="secondary",
            key=f"ras_btn_bom_{detalhe['id']}",
        ):
            ok, res = _executar_servico(
                servicos["materiais"].gerar_solicitacoes_da_producao,
                conn,
                detalhe["id"],
                usuario_ras,
            )
            if ok:
                st.success(
                    f"{res['criadas']} solicitação(ões) gerada(s); {res['ignoradas']} já existia(m) para esta unidade."
                )
                st.rerun()
            else:
                st.error(res)

        if detalhe["solicitacoes"]:
            df_s = pd.DataFrame(detalhe["solicitacoes"])[
                [
                    "codigo_sku",
                    "componente_nome",
                    "quantidade_solicitada",
                    "quantidade_baixada",
                    "status_solicitacao",
                ]
            ].rename(
                columns={
                    "codigo_sku": "SKU",
                    "componente_nome": "Componente",
                    "quantidade_solicitada": "Qtd. Solicitada",
                    "quantidade_baixada": "Qtd. Baixada",
                    "status_solicitacao": "Status",
                }
            )
            st.dataframe(df_s, hide_index=True, use_container_width=True)
        else:
            st.caption("Nenhuma solicitação de material vinculada a esta produção.")

    with aba_nc:
        with st.form(f"ras_form_nc_{detalhe['id']}"):
            st.markdown("**Registrar Não Conformidade na Unidade**")
            nc_falha = st.text_input("Descrição da Falha Encontrada *")
            nc_motivo = st.text_input("Motivo da Reprovação / Retenção *")
            if st.form_submit_button("Registrar Não Conformidade", type="primary"):
                ok, res = _executar_servico(
                    servicos["producao"].registrar_nao_conformidade,
                    conn,
                    detalhe["id"],
                    nc_falha,
                    nc_motivo,
                    usuario_ras,
                )
                if ok:
                    st.success("Não conformidade registrada com sucesso.")
                    st.rerun()
                else:
                    st.error(res)

        if detalhe["nao_conformidades"]:
            df_nc = pd.DataFrame(detalhe["nao_conformidades"])[
                ["data_registro", "descricao_falha", "motivo_reprovacao", "usuario_nome"]
            ].rename(
                columns={
                    "data_registro": "Data / Hora",
                    "descricao_falha": "Falha Encontrada",
                    "motivo_reprovacao": "Motivo",
                    "usuario_nome": "Registrado por",
                }
            )
            st.dataframe(df_nc, hide_index=True, use_container_width=True)
        else:
            st.caption("Nenhuma não conformidade registrada para esta unidade.")


def _render_solicitacoes(conn, usuario_ras: dict[str, Any], servicos: dict[str, Any]) -> None:
    amatech.titulo(
        "Solicitações de Material para a Linha",
        "Requisição de componentes (BOM) por ordem de produção e acompanhamento de atendimento pelo almoxarifado",
    )

    producoes = servicos["producao"].listar_producoes(conn)
    componentes = servicos["cadastros"].listar_componentes(conn)

    with st.expander("➕ Nova Solicitação de Material", expanded=False):
        if not producoes or not componentes:
            st.warning("É necessário ter produções e componentes cadastrados.")
        else:
            with st.form("ras_form_nova_solicitacao"):
                c1, c2, c3 = st.columns([2, 2, 1])
                op_prod = {p["id"]: f"{p['numero_serie']} ({p['nome_modelo']})" for p in producoes}
                op_comp = {
                    c["idcmp"]: f"{c['codigo_sku']} — {c['nome']} ( Saldo: {c['qtd_estoque']} )"
                    for c in componentes
                }
                prod_id = c1.selectbox("Produção (Nº de Série)", list(op_prod.keys()), format_func=lambda k: op_prod[k])
                comp_id = c2.selectbox("Componente", list(op_comp.keys()), format_func=lambda k: op_comp[k])
                qtd = c3.number_input("Quantidade", min_value=1, value=1, step=1)
                if st.form_submit_button("Criar Solicitação", type="primary"):
                    ok, res = _executar_servico(
                        servicos["materiais"].criar_solicitacao,
                        conn,
                        prod_id,
                        comp_id,
                        int(qtd),
                        usuario_ras,
                    )
                    if ok:
                        st.success(f"Solicitação #{res['id']} registrada com sucesso!")
                        st.rerun()
                    else:
                        st.error(res)

    status_opcoes = ["Todos", "PENDENTE", "PARCIAL", "ATENDIDA", "CANCELADA"]
    st_sol = st.selectbox("Filtrar por Status da Solicitação", status_opcoes, key="ras_sol_status")

    solicitacoes = servicos["materiais"].listar_solicitacoes(
        conn,
        status=None if st_sol == "Todos" else st_sol,
    )

    if solicitacoes:
        df_sol = pd.DataFrame(solicitacoes)[
            [
                "id",
                "numero_serie",
                "codigo_sku",
                "componente_nome",
                "quantidade_solicitada",
                "quantidade_baixada",
                "qtd_estoque",
                "status_solicitacao",
                "criado_em",
            ]
        ].rename(
            columns={
                "id": "ID",
                "numero_serie": "Nº de Série",
                "codigo_sku": "SKU",
                "componente_nome": "Componente",
                "quantidade_solicitada": "Solicitada",
                "quantidade_baixada": "Baixada",
                "qtd_estoque": "Estoque Atual",
                "status_solicitacao": "Status",
                "criado_em": "Criada em",
            }
        )
        st.dataframe(df_sol, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma solicitação encontrada.")


def _render_baixas(conn, usuario_ras: dict[str, Any], servicos: dict[str, Any]) -> None:
    amatech.titulo(
        "Baixas de Material e Controle de Saída do Almoxarifado",
        "Atendimento de solicitações abertas com dedução automática no saldo de estoque de componentes",
    )

    solicitacoes_abertas = [
        s
        for s in servicos["materiais"].listar_solicitacoes(conn)
        if s["status_solicitacao"] in ("PENDENTE", "PARCIAL")
    ]

    with st.container(border=True):
        st.markdown("#### Registrar Baixa de Material")
        if not solicitacoes_abertas:
            st.info("Não há solicitações pendentes ou parciais aguardando baixa no momento.")
        else:
            with st.form("ras_form_baixa"):
                op_sol = {
                    s["id"]: (
                        f"#{s['id']} · {s['numero_serie']} · {s['codigo_sku']} ({s['componente_nome']}) — "
                        f"Restante: {s['quantidade_solicitada'] - s['quantidade_baixada']} un. "
                        f"| Estoque: {s['qtd_estoque']} un."
                    )
                    for s in solicitacoes_abertas
                }
                c1, c2 = st.columns([3, 1])
                sol_id = c1.selectbox(
                    "Solicitação Pendente",
                    options=list(op_sol.keys()),
                    format_func=lambda k: op_sol[k],
                )
                qtd_baixa = c2.number_input("Quantidade a Baixar", min_value=1, value=1, step=1)
                if st.form_submit_button("Confirmar Baixa no Estoque", type="primary"):
                    ok, res = _executar_servico(
                        servicos["materiais"].criar_baixa,
                        conn,
                        sol_id,
                        int(qtd_baixa),
                        usuario_ras,
                    )
                    if ok:
                        st.success(f"Baixa #{res['id']} efetuada! Estoque do componente atualizado.")
                        st.rerun()
                    else:
                        st.error(res)

    st.subheader("Histórico de Baixas Realizadas")
    baixas = servicos["materiais"].listar_baixas(conn)
    if baixas:
        df_b = pd.DataFrame(baixas)[
            [
                "id",
                "data_baixa",
                "numero_serie",
                "codigo_sku",
                "componente_nome",
                "quantidade_baixada",
                "usuario_nome",
            ]
        ].rename(
            columns={
                "id": "ID Baixa",
                "data_baixa": "Data / Hora",
                "numero_serie": "Nº de Série",
                "codigo_sku": "SKU",
                "componente_nome": "Componente",
                "quantidade_baixada": "Qtd. Baixada",
                "usuario_nome": "Almoxarife / Resp.",
            }
        )
        st.dataframe(df_b, hide_index=True, use_container_width=True)
    else:
        st.caption("Nenhuma baixa registrada.")


def _render_cadastros(conn, usuario_ras: dict[str, Any], servicos: dict[str, Any]) -> None:
    eh_admin = usuario_ras["cargo"] == "Administrador"
    amatech.titulo(
        "Cadastros de Engenharia e Estoque de Componentes",
        "Gestão de componentes, saldos de inventário, modelos de produtos, estrutura BOM e etapas da linha",
    )

    abas_nomes = ["Componentes e Estoque", "Produtos e Lista Técnica (BOM)"]
    if eh_admin:
        abas_nomes.append("Etapas de Produção (Status)")

    abas = st.tabs(abas_nomes)

    # Aba 1: Componentes
    with abas[0]:
        with st.expander("➕ Cadastrar Novo Componente no Almoxarifado", expanded=False):
            with st.form("ras_form_novo_comp"):
                c1, c2, c3 = st.columns([1.2, 2.2, 1])
                sku = c1.text_input("Código SKU *", placeholder="Ex.: MEM-DDR4-16G")
                nome_c = c2.text_input("Nome do Componente *", placeholder="Ex.: Memória RAM 16GB DDR4")
                qtd_c = c3.number_input("Saldo Inicial", min_value=0, value=25, step=1)
                if st.form_submit_button("Salvar Componente", type="primary"):
                    ok, res = _executar_servico(
                        servicos["cadastros"].criar_componente,
                        conn,
                        {
                            "codigo_sku": sku,
                            "nome": nome_c,
                            "qtd_estoque": int(qtd_c),
                        },
                        usuario_ras,
                    )
                    if ok:
                        st.success(f"Componente **{res['codigo_sku']}** cadastrado!")
                        st.rerun()
                    else:
                        st.error(res)

        componentes = servicos["cadastros"].listar_componentes(conn)
        if componentes:
            df_c = pd.DataFrame(componentes)[
                ["idcmp", "codigo_sku", "nome", "qtd_estoque", "qtd_pendente"]
            ].rename(
                columns={
                    "idcmp": "ID",
                    "codigo_sku": "SKU",
                    "nome": "Componente",
                    "qtd_estoque": "Saldo em Estoque",
                    "qtd_pendente": "Qtd. Pendente Solicitações",
                }
            )
            st.dataframe(df_c, hide_index=True, use_container_width=True)

    # Aba 2: Produtos & BOM
    with abas[1]:
        produtos = servicos["cadastros"].listar_produtos(conn)
        if produtos:
            df_p = pd.DataFrame(produtos)[
                ["idprd", "codigo_modelo", "nome_modelo", "quantidade", "qtd_componentes", "qtd_producoes"]
            ].rename(
                columns={
                    "idprd": "ID",
                    "codigo_modelo": "Código",
                    "nome_modelo": "Modelo",
                    "quantidade": "Meta Lote",
                    "qtd_componentes": "Itens na BOM",
                    "qtd_producoes": "Produções",
                }
            )
            st.dataframe(df_p, hide_index=True, use_container_width=True)

            op_p = {p["idprd"]: f"{p['nome_modelo']} ({p['codigo_modelo']})" for p in produtos}
            prd_bom_id = st.selectbox(
                "Consultar Lista Técnica (BOM) do Produto:",
                options=list(op_p.keys()),
                format_func=lambda k: op_p[k],
                key="ras_sel_prd_bom",
            )
            itens_bom = servicos["cadastros"].componentes_do_produto(conn, prd_bom_id)
            if itens_bom:
                df_bom = pd.DataFrame(itens_bom)[
                    ["codigo_sku", "nome", "quantidade_necessaria", "qtd_estoque"]
                ].rename(
                    columns={
                        "codigo_sku": "SKU",
                        "nome": "Componente",
                        "quantidade_necessaria": "Qtd. por Unidade",
                        "qtd_estoque": "Estoque Atual",
                    }
                )
                st.dataframe(df_bom, hide_index=True, use_container_width=True)
            else:
                st.caption("Nenhum componente vinculado a este modelo.")

    # Aba 3: Status / Etapas
    if eh_admin and len(abas) > 2:
        with abas[2]:
            status_list = servicos["cadastros"].listar_status(conn)
            if status_list:
                df_st = pd.DataFrame(status_list)[
                    ["ordem", "nome_status", "criado_em"]
                ].rename(
                    columns={
                        "ordem": "Ordem no Fluxo",
                        "nome_status": "Etapa",
                        "criado_em": "Criado em",
                    }
                )
                st.dataframe(df_st, hide_index=True, use_container_width=True)


def _render_relatorios(conn, usuario_ras: dict[str, Any], servicos: dict[str, Any]) -> None:
    amatech.titulo(
        "Relatórios Operacionais e Exportação CSV",
        "Emissão de relatórios auditáveis de produção, materiais, estoque e não conformidades",
    )

    tipos = {
        "producao": "Produções e Etapa Atual",
        "materiais": "Solicitações e Baixas de Material",
        "estoque": "Estoque de Componentes e Pendências",
        "nao_conformidades": "Não Conformidades Registradas",
    }

    c1, c2, c3 = st.columns([2, 1, 1])
    tipo_sel = c1.selectbox("Tipo de Relatório", list(tipos.keys()), format_func=lambda k: tipos[k])
    data_ini = c2.text_input("Data Inicial (AAAA-MM-DD)", placeholder="Opcional")
    data_fim = c3.text_input("Data Final (AAAA-MM-DD)", placeholder="Opcional")

    rel = servicos["relatorios"].gerar_relatorio(
        conn,
        tipo_sel,
        data_ini=data_ini.strip() or None,
        data_fim=data_fim.strip() or None,
    )
    csv_bytes = servicos["relatorios"].relatorio_csv(rel)

    st.download_button(
        f"📥 Exportar CSV — {rel['titulo']}",
        data=csv_bytes,
        file_name=f"relatorio_{tipo_sel}.csv",
        mime="text/csv",
        type="primary",
    )

    if rel["linhas"]:
        col_map = {c["chave"]: c["titulo"] for c in rel["colunas"]}
        df_rel = pd.DataFrame(rel["linhas"])[list(col_map.keys())].rename(columns=col_map)
        st.dataframe(df_rel, hide_index=True, use_container_width=True)
        st.caption(f"Total: **{len(rel['linhas'])}** registro(s).")
    else:
        st.info("Nenhum registro encontrado para os parâmetros informados.")


def renderizar_modulo_rastreabilidade(usuario_erp: dict[str, Any]) -> None:
    """Renderiza o módulo de Rastreabilidade e Materiais integrado ao ERP."""
    usuario_ras = st.session_state.get("ras_usuario") or {
        "id": 1,
        "matricula": usuario_erp["matricula"],
        "nome": usuario_erp["nome"],
        "cargo": "Operador",
    }
    cargo = usuario_ras.get("cargo", "Operador")
    telas_disponiveis = TELAS_POR_CARGO.get(cargo, TELAS_POR_CARGO["Operador"])

    if "ras_subpagina" not in st.session_state or st.session_state["ras_subpagina"] not in {
        t[0] for t in telas_disponiveis
    }:
        st.session_state["ras_subpagina"] = telas_disponiveis[0][0]

    with st.sidebar:
        st.markdown('<div class="sb-nav-grupo">Módulo Rastreabilidade (RAS)</div>', unsafe_allow_html=True)
        for cod, rotulo, icone in telas_disponiveis:
            ativo = st.session_state["ras_subpagina"] == cod
            if st.button(
                rotulo,
                icon=icone,
                key=f"ras_nav_{cod}",
                type="primary" if ativo else "secondary",
                width="stretch",
            ):
                st.session_state["ras_subpagina"] = cod
                st.rerun()

    amatech.cabecalho(
        "RAS",
        [
            ("Turno", amatech.turno_atual()),
            (cargo, f"{amatech.esc(usuario_ras['nome'])} · <span class='am-codigo'>{amatech.esc(usuario_ras['matricula'])}</span>"),
        ],
    )

    with ambiente_modulo("rastreabilidade"):
        from app import db, seed
        from app.servicos import cadastros, materiais, producao, relatorios

        db.inicializar()
        servicos = {
            "cadastros": cadastros,
            "materiais": materiais,
            "producao": producao,
            "relatorios": relatorios,
        }
        sub = st.session_state["ras_subpagina"]
        with closing(db.conectar()) as conn:
            if db.um(conn, "SELECT COUNT(*) AS n FROM status_producao")["n"] == 0:
                seed.popular(conn)
            if sub == "terminal":
                _render_terminal(conn, usuario_ras, servicos)
            elif sub == "producao":
                _render_producao(conn, usuario_ras, servicos)
            elif sub == "solicitacoes":
                _render_solicitacoes(conn, usuario_ras, servicos)
            elif sub == "baixas":
                _render_baixas(conn, usuario_ras, servicos)
            elif sub == "cadastros":
                _render_cadastros(conn, usuario_ras, servicos)
            elif sub == "relatorios":
                _render_relatorios(conn, usuario_ras, servicos)
