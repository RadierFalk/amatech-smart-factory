import streamlit as st

import banco
import ocorrencia


def mostrar_historico_ocorrencias():
    st.title("Histórico de Ocorrências")
    st.caption(
        "Consulte, pesquise, filtre, edite ou oculte ocorrências registradas."
    )

    # ========================================================
    # EDIÇÃO
    # ========================================================

    if "ocorrencia_em_edicao" in st.session_state:
        id_edicao = st.session_state["ocorrencia_em_edicao"]

        registro = ocorrencia.buscar_ocorrencia(id_edicao)

        if registro is None:
            st.error("Ocorrência não encontrada.")
            del st.session_state["ocorrencia_em_edicao"]
            st.rerun()

        st.subheader(f"Editar ocorrência #{id_edicao}")

        produtos = banco.listar_produtos()
        estacoes = banco.listar_estacoes()
        tipos_defeito = banco.listar_tipos_defeito()
        maquinas = banco.listar_maquinas()
        usuarios = banco.listar_usuarios()

        produto_opcoes = {
            produto["numero_serie_produto"]: produto["id_produto"]
            for produto in produtos
        }

        estacao_opcoes = {
            estacao["nome_estacao"]: estacao["id_estacao"]
            for estacao in estacoes
        }

        tipo_defeito_opcoes = {
            tipo["nome_tipo_defeito"]: tipo["id_tipo_defeito"]
            for tipo in tipos_defeito
        }

        maquina_opcoes = {
            maquina["nome_maquina"]: maquina["id_maquina"]
            for maquina in maquinas
        }

        usuario_opcoes = {
            usuario["nome_usuario"]: usuario["id_usuario"]
            for usuario in usuarios
        }

        produto_atual = next(
            (
                nome
                for nome, id_produto in produto_opcoes.items()
                if id_produto == registro["id_produto"]
            ),
            None
        )

        estacao_atual = next(
            (
                nome
                for nome, id_estacao in estacao_opcoes.items()
                if id_estacao == registro["id_estacao"]
            ),
            None
        )

        tipo_atual = next(
            (
                nome
                for nome, id_tipo in tipo_defeito_opcoes.items()
                if id_tipo == registro["id_tipo_defeito"]
            ),
            None
        )

        maquina_atual = next(
            (
                nome
                for nome, id_maquina in maquina_opcoes.items()
                if id_maquina == registro["id_maquina"]
            ),
            None
        )

        usuario_atual = next(
            (
                nome
                for nome, id_usuario in usuario_opcoes.items()
                if id_usuario == registro["id_usuario"]
            ),
            None
        )

        with st.form("form_editar_ocorrencia"):
            col1, col2 = st.columns(2)

            with col1:
                produto_selecionado = st.selectbox(
                    "Produto",
                    options=list(produto_opcoes.keys()),
                    index=(
                        list(produto_opcoes.keys()).index(produto_atual)
                        if produto_atual in produto_opcoes
                        else 0
                    )
                )

                estacao_selecionada = st.selectbox(
                    "Estação",
                    options=list(estacao_opcoes.keys()),
                    index=(
                        list(estacao_opcoes.keys()).index(estacao_atual)
                        if estacao_atual in estacao_opcoes
                        else 0
                    )
                )

                tipo_defeito_selecionado = st.selectbox(
                    "Tipo de defeito",
                    options=list(tipo_defeito_opcoes.keys()),
                    index=(
                        list(tipo_defeito_opcoes.keys()).index(tipo_atual)
                        if tipo_atual in tipo_defeito_opcoes
                        else 0
                    )
                )

                maquina_selecionada = st.selectbox(
                    "Máquina",
                    options=list(maquina_opcoes.keys()),
                    index=(
                        list(maquina_opcoes.keys()).index(maquina_atual)
                        if maquina_atual in maquina_opcoes
                        else 0
                    )
                )

            with col2:
                usuario_selecionado = st.selectbox(
                    "Usuário responsável",
                    options=list(usuario_opcoes.keys()),
                    index=(
                        list(usuario_opcoes.keys()).index(usuario_atual)
                        if usuario_atual in usuario_opcoes
                        else 0
                    )
                )

                classificacao = st.selectbox(
                    "Classificação do defeito",
                    options=ocorrencia.CLASSIFICACOES_DEFEITO,
                    index=(
                        ocorrencia.CLASSIFICACOES_DEFEITO.index(
                            registro["classificacao_defeito"]
                        )
                        if registro["classificacao_defeito"]
                        in ocorrencia.CLASSIFICACOES_DEFEITO
                        else 0
                    )
                )

                situacao = st.selectbox(
                    "Situação do produto",
                    options=ocorrencia.SITUACOES_PRODUTO,
                    index=(
                        ocorrencia.SITUACOES_PRODUTO.index(
                            registro["situacao_produto"]
                        )
                        if registro["situacao_produto"]
                        in ocorrencia.SITUACOES_PRODUTO
                        else 0
                    )
                )

                status = st.selectbox(
                    "Status da ocorrência",
                    options=ocorrencia.STATUS_OCORRENCIA,
                    index=(
                        ocorrencia.STATUS_OCORRENCIA.index(
                            registro["status_ocorrencia"]
                        )
                        if registro["status_ocorrencia"]
                        in ocorrencia.STATUS_OCORRENCIA
                        else 0
                    )
                )

            observacao = st.text_area(
                "Observação da ocorrência",
                value=registro["observacao_ocorrencia"]
            )

            acao = st.text_area(
                "Ação realizada",
                value=registro["acao_realizada"]
            )

            col1, col2 = st.columns(2)

            with col1:
                salvar = st.form_submit_button(
                    "Salvar alterações",
                    type="primary"
                )

            with col2:
                cancelar = st.form_submit_button(
                    "Cancelar"
                )

        if cancelar:
            del st.session_state["ocorrencia_em_edicao"]
            st.rerun()

        if salvar:
            sucesso, resultado = ocorrencia.editar_ocorrencia(
                id_ocorrencia=id_edicao,
                data_ocorrencia=registro["data_ocorrencia"],
                hora_ocorrencia=registro["hora_ocorrencia"],
                classificacao_defeito=classificacao,
                situacao_produto=situacao,
                observacao_ocorrencia=observacao,
                acao_realizada=acao,
                status_ocorrencia=status,
                id_produto=produto_opcoes[produto_selecionado],
                id_estacao=estacao_opcoes[estacao_selecionada],
                id_tipo_defeito=tipo_defeito_opcoes[
                    tipo_defeito_selecionado
                ],
                id_maquina=maquina_opcoes[maquina_selecionada],
                id_usuario=usuario_opcoes[usuario_selecionado]
            )

            if sucesso:
                del st.session_state["ocorrencia_em_edicao"]

                st.success(
                    "Ocorrência atualizada com sucesso."
                )

                st.rerun()

            else:
                for erro in resultado:
                    st.error(erro)

        return

    # ========================================================
    # PESQUISA
    # ========================================================

    termo_pesquisa = st.text_input(
        "Pesquisar ocorrências",
        placeholder="Digite o ID, produto, tipo de defeito ou estação"
    )

    # ========================================================
    # FILTROS
    # ========================================================

    tipos_defeito = banco.listar_tipos_defeito()
    estacoes = banco.listar_estacoes()

    tipos_opcoes = {
        "Todos": None
    }

    for tipo in tipos_defeito:
        tipos_opcoes[tipo["nome_tipo_defeito"]] = tipo["id_tipo_defeito"]

    estacoes_opcoes = {
        "Todas": None
    }

    for estacao in estacoes:
        estacoes_opcoes[estacao["nome_estacao"]] = estacao["id_estacao"]

    col1, col2 = st.columns(2)

    with col1:
        tipo_selecionado = st.selectbox(
            "Filtrar por tipo de defeito",
            options=list(tipos_opcoes.keys())
        )

    with col2:
        estacao_selecionada = st.selectbox(
            "Filtrar por estação",
            options=list(estacoes_opcoes.keys())
        )

    # ========================================================
    # CONSULTA
    # ========================================================

    termo = termo_pesquisa.strip()

    if termo.isdigit():
        id_pesquisado = int(termo)

        ocorrencias = [
            item
            for item in ocorrencia.listar_ocorrencias()
            if item["id_ocorrencia"] == id_pesquisado
        ]

    elif termo:
        ocorrencias = ocorrencia.pesquisar_ocorrencias(termo)

    else:
        ocorrencias = ocorrencia.listar_ocorrencias()

    # ========================================================
    # FILTRO POR TIPO
    # ========================================================

    if tipo_selecionado != "Todos":
        ocorrencias = [
        item
        for item in ocorrencias
        if item["nome_tipo_defeito"] == tipo_selecionado
    ]

    # ========================================================
    # FILTRO POR ESTAÇÃO
    # ========================================================

    if estacao_selecionada != "Todas":
        ocorrencias = [
        item
        for item in ocorrencias
        if item["nome_estacao"] == estacao_selecionada
    ]

    # ========================================================
    # RESULTADO
    # ========================================================

    st.subheader("Ocorrências registradas")

    if not ocorrencias:
        st.info("Nenhuma ocorrência encontrada.")
        return

    st.write(f"Total encontrado: **{len(ocorrencias)}**")

    # ========================================================
    # LISTAGEM
    # ========================================================

    for item in ocorrencias:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(
                [0.7, 1.2, 1.6, 1.3]
            )

            with col1:
                st.write("**ID**")
                st.write(item["id_ocorrencia"])

            with col2:
                st.write("**Data**")
                st.write(item["data_ocorrencia"])

            with col3:
                st.write("**Produto**")
                st.write(item["numero_serie_produto"])

            with col4:
                st.write("**Status**")
                st.write(item["status_ocorrencia"])

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.write("**Tipo de defeito**")
                st.write(item["nome_tipo_defeito"])

            with col2:
                st.write("**Estação**")
                st.write(item["nome_estacao"])

            with col3:
                st.write("**Classificação**")
                st.write(item["classificacao_defeito"])

            with col4:
                st.write("**Ações**")

                editar = st.button(
                    "Editar",
                    key=f"editar_{item['id_ocorrencia']}"
                )

                ocultar = st.button(
                    "Ocultar",
                    key=f"ocultar_{item['id_ocorrencia']}"
                )

            # =================================================
            # EDITAR
            # =================================================

            if editar:
                st.session_state[
                    "ocorrencia_em_edicao"
                ] = item["id_ocorrencia"]

                st.rerun()

            # =================================================
            # OCULTAR
            # =================================================

            if ocultar:
                sucesso, mensagem = ocorrencia.ocultar_ocorrencia(
                    item["id_ocorrencia"]
                )

                if sucesso:
                    st.success(
                        "Ocorrência ocultada com sucesso."
                    )
                    st.rerun()
                else:
                    st.error(mensagem)