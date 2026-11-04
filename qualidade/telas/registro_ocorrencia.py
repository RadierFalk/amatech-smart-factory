import streamlit as st
from datetime import date, datetime, time

import banco
import ocorrencia
import permissoes


def mostrar_registro_ocorrencia(usuario):

    if not permissoes.tem_permissao(usuario, permissoes.REGISTRAR_OCORRENCIA):
        st.error("Seu perfil não tem permissão para registrar ocorrências.")
        return

    st.title("Registro de Ocorrência")

    st.caption(
        "Registre uma ocorrência de falha identificada durante a produção."
    )

    st.caption(
        f"Responsável pelo registro: **{usuario['nome']}** ({usuario['matricula']})"
    )

    # ========================================================
    # CARREGAMENTO DAS OPÇÕES
    # ========================================================

    produtos = banco.listar_produtos()
    estacoes = banco.listar_estacoes()
    tipos_defeito = banco.listar_tipos_defeito()
    maquinas = banco.listar_maquinas()

    # ========================================================
    # FORMULÁRIO
    # ========================================================

    with st.form("form_registro_ocorrencia"):

        st.subheader("Dados da ocorrência")

        col1, col2 = st.columns(2)

        # ----------------------------------------------------
        # PRODUTO
        # ----------------------------------------------------

        with col1:

            produto_opcoes = {
                produto["numero_serie_produto"]: produto["id_produto"]
                for produto in produtos
            }

            produto_selecionado = st.selectbox(
                "Produto",
                options=list(produto_opcoes.keys()),
                index=None,
                placeholder="Selecione o produto"
            )

            data_ocorrencia = st.date_input(
                "Data da ocorrência",
                value=date.today()
            )

            classificacao_defeito = st.selectbox(
                "Classificação do defeito",
                options=ocorrencia.CLASSIFICACOES_DEFEITO
            )

            situacao_produto = st.selectbox(
                "Situação do produto",
                options=ocorrencia.SITUACOES_PRODUTO
            )

            status_ocorrencia = st.selectbox(
                "Status da ocorrência",
                options=ocorrencia.STATUS_OCORRENCIA
            )

        # ----------------------------------------------------
        # ESTAÇÃO / DEFEITO / MÁQUINA
        # ----------------------------------------------------

        with col2:

            estacao_opcoes = {
                estacao["nome_estacao"]: estacao["id_estacao"]
                for estacao in estacoes
            }

            estacao_selecionada = st.selectbox(
                "Estação",
                options=list(estacao_opcoes.keys()),
                index=None,
                placeholder="Selecione a estação"
            )

            tipo_defeito_opcoes = {
                tipo["nome_tipo_defeito"]: tipo["id_tipo_defeito"]
                for tipo in tipos_defeito
            }

            tipo_defeito_selecionado = st.selectbox(
                "Tipo de defeito",
                options=list(tipo_defeito_opcoes.keys()),
                index=None,
                placeholder="Selecione o tipo de defeito"
            )

            maquina_opcoes = {
                maquina["nome_maquina"]: maquina["id_maquina"]
                for maquina in maquinas
            }

            maquina_selecionada = st.selectbox(
                "Máquina",
                options=list(maquina_opcoes.keys()),
                index=None,
                placeholder="Selecione a máquina"
            )

            hora_ocorrencia = st.time_input(
                "Hora da ocorrência",
                value=time(
                    datetime.now().hour,
                    datetime.now().minute
                )
            )

        # ====================================================
        # OBSERVAÇÃO E AÇÃO
        # ====================================================

        st.subheader("Detalhes da ocorrência")

        observacao_ocorrencia = st.text_area(
            "Observação da ocorrência",
            placeholder="Descreva o defeito identificado."
        )

        acao_realizada = st.text_area(
            "Ação realizada",
            placeholder="Descreva a ação realizada após a identificação do defeito."
        )

        pode_abrir_chamado = permissoes.tem_permissao(usuario, permissoes.ABRIR_CHAMADO)

        abrir_chamado = pode_abrir_chamado and st.checkbox(
            "Abrir chamado na manutenção (defeito causado pela máquina)",
            help="Envia um chamado para o sistema de Manutenção, com a máquina selecionada acima."
        )

        # ====================================================
        # BOTÃO
        # ====================================================

        registrar = st.form_submit_button(
            "Registrar ocorrência",
            type="primary"
        )

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    if registrar:

        id_produto = (
            produto_opcoes.get(produto_selecionado)
            if produto_selecionado
            else None
        )

        id_estacao = (
            estacao_opcoes.get(estacao_selecionada)
            if estacao_selecionada
            else None
        )

        id_tipo_defeito = (
            tipo_defeito_opcoes.get(tipo_defeito_selecionado)
            if tipo_defeito_selecionado
            else None
        )

        id_maquina = (
            maquina_opcoes.get(maquina_selecionada)
            if maquina_selecionada
            else None
        )

        sucesso, resultado = ocorrencia.registrar_ocorrencia(
            usuario=usuario,
            data_ocorrencia=data_ocorrencia,
            hora_ocorrencia=hora_ocorrencia,
            classificacao_defeito=classificacao_defeito,
            situacao_produto=situacao_produto,
            observacao_ocorrencia=observacao_ocorrencia,
            acao_realizada=acao_realizada,
            status_ocorrencia=status_ocorrencia,
            id_produto=id_produto,
            id_estacao=id_estacao,
            id_tipo_defeito=id_tipo_defeito,
            id_maquina=id_maquina
        )

        if sucesso:

            st.success(
                f"Ocorrência registrada com sucesso. "
                f"ID da ocorrência: {resultado}"
            )

            # Avisa a Rastreabilidade (etapa do notebook) e, se pedido, a Manutenção (chamado)
            for tipo, mensagem in ocorrencia.notificar_setores(usuario, resultado, abrir_chamado):
                if tipo == "sucesso":
                    st.info(mensagem)
                else:
                    st.warning(mensagem)

        else:

            for erro in resultado:
                st.error(erro)