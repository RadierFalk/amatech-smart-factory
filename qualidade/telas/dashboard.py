import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

import indicadores
import graficos


# ============================================================
# CONFIGURAÇÃO VISUAL
# ============================================================

FUNDO_GRAFICO = "#0E1117"
TEXTO_GRAFICO = "#FAFAFA"
GRADE_GRAFICO = "#30343B"


def configurar_grafico(ax):

    ax.set_facecolor(FUNDO_GRAFICO)

    ax.tick_params(
        colors=TEXTO_GRAFICO,
        labelcolor=TEXTO_GRAFICO
    )

    ax.xaxis.label.set_color(
        TEXTO_GRAFICO
    )

    ax.yaxis.label.set_color(
        TEXTO_GRAFICO
    )

    for borda in ax.spines.values():
        borda.set_color(
            GRADE_GRAFICO
        )

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.6,
        alpha=0.35,
        color=GRADE_GRAFICO
    )


# ============================================================
# DASHBOARD
# ============================================================

def mostrar_dashboard():

    st.title("Controle da Qualidade")

    st.caption(
        "Visão geral das ocorrências registradas na produção"
    )

    # ========================================================
    # INDICADORES
    # ========================================================

    dados = indicadores.obter_indicadores()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Total de ocorrências",
            dados["total_ocorrencias"]
        )

    with col2:

        st.metric(
            "Ocorrências abertas",
            dados["ocorrencias_abertas"]
        )

    with col3:

        st.metric(
            "Produtos reprovados",
            dados["produtos_reprovados"]
        )

    with col4:

        estacao = dados[
            "estacao_com_mais_ocorrencias"
        ]

        st.markdown(
            """
            <style>
            div[data-testid="stMetric"] {
                min-height: 110px;
            }

            div[data-testid="stMetricValue"] {
                white-space: normal !important;
                overflow-wrap: break-word !important;
                word-break: normal !important;
                font-size: 1.45rem !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.metric(
            "Estação com mais ocorrências",
            estacao if estacao else "-"
        )

    st.divider()

    # ========================================================
    # OCORRÊNCIAS POR TIPO DE DEFEITO
    # ========================================================

    st.subheader(
        "Ocorrências por tipo de defeito"
    )

    dados_tipo = (
        graficos.ocorrencias_por_tipo_defeito()
    )

    if dados_tipo:

        tipos = list(
            dados_tipo.keys()
        )

        quantidades = list(
            dados_tipo.values()
        )

        fig, ax = plt.subplots(
            figsize=(10, 5.2)
        )

        fig.patch.set_facecolor(
            FUNDO_GRAFICO
        )

        ax.set_facecolor(
            FUNDO_GRAFICO
        )

        posicoes = list(
            range(len(tipos))
        )

        barras = ax.bar(
            posicoes,
            quantidades
        )

        ax.set_xticks(
            posicoes
        )

        ax.set_xticklabels(
            tipos,
            rotation=25,
            ha="right"
        )

        ax.set_ylabel(
            "Quantidade de ocorrências"
        )

        configurar_grafico(
            ax
        )

        ax.yaxis.set_major_locator(
            MaxNLocator(integer=True)
        )

        maior_quantidade = max(
            quantidades
        )

        ax.set_ylim(
            0,
            maior_quantidade + 1.5
        )

        for barra, valor in zip(
            barras,
            quantidades
        ):

            ax.text(
                barra.get_x()
                + barra.get_width() / 2,
                barra.get_height() + 0.08,
                str(valor),
                ha="center",
                va="bottom",
                color=TEXTO_GRAFICO,
                fontsize=9
            )

        fig.subplots_adjust(
            left=0.08,
            right=0.96,
            bottom=0.25,
            top=0.91
        )

        st.pyplot(
            fig,
            use_container_width=True
        )

        plt.close(
            fig
        )

    else:

        st.info(
            "Não há ocorrências para exibir."
        )

    # ========================================================
    # DUAS COLUNAS
    # ========================================================

    col_esquerda, col_direita = (
        st.columns(2)
    )

    # ========================================================
    # OCORRÊNCIAS POR ESTAÇÃO
    # ========================================================

    with col_esquerda:

        st.subheader(
            "Ocorrências por estação"
        )

        dados_estacao = (
            graficos.ocorrencias_por_estacao()
        )

        if dados_estacao:

            estacoes = list(
                dados_estacao.keys()
            )

            quantidades_estacao = list(
                dados_estacao.values()
            )

            fig, ax = plt.subplots(
                figsize=(7, 4)
            )

            fig.patch.set_facecolor(
                FUNDO_GRAFICO
            )

            ax.set_facecolor(
                FUNDO_GRAFICO
            )

            estacoes_invertidas = (
                estacoes[::-1]
            )

            quantidades_invertidas = (
                quantidades_estacao[::-1]
            )

            barras = ax.barh(
                estacoes_invertidas,
                quantidades_invertidas
            )

            ax.set_xlabel(
                "Quantidade de ocorrências"
            )

            ax.set_ylabel(
                "Estação"
            )

            maior_valor = max(
                quantidades_invertidas
            )

            ax.set_xlim(
                0,
                maior_valor + 2
            )

            configurar_grafico(
                ax
            )

            ax.xaxis.set_major_locator(
                MaxNLocator(integer=True)
            )

            for barra, valor in zip(
                barras,
                quantidades_invertidas
            ):

                ax.text(
                    barra.get_width() + 0.05,
                    barra.get_y()
                    + barra.get_height() / 2,
                    str(valor),
                    va="center",
                    color=TEXTO_GRAFICO,
                    fontsize=9
                )

            fig.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(
                fig
            )

        else:

            st.info(
                "Não há ocorrências para exibir."
            )

    # ========================================================
    # TENDÊNCIA DE OCORRÊNCIAS
    # ========================================================

    with col_direita:

        st.subheader(
            "Tendência de ocorrências"
        )

        datas, quantidades = (
            graficos.ocorrencias_por_data()
        )

        if datas:

            fig, ax = plt.subplots(
                figsize=(7, 4)
            )

            fig.patch.set_facecolor(
                FUNDO_GRAFICO
            )

            ax.set_facecolor(
                FUNDO_GRAFICO
            )

            # ------------------------------------------------
            # DATAS
            # ------------------------------------------------

            datas_formatadas = [
                data[8:10]
                + "/"
                + data[5:7]
                for data in datas
            ]

            # ------------------------------------------------
            # LINHA
            # ------------------------------------------------

            ax.plot(
                datas_formatadas,
                quantidades,
                marker="o",
                linewidth=2
            )

            ax.set_xlabel(
                "Data"
            )

            ax.set_ylabel(
                "Ocorrências"
            )

            configurar_grafico(
                ax
            )

            ax.yaxis.set_major_locator(
                MaxNLocator(integer=True)
            )

            ax.set_ylim(
                bottom=0
            )

            # ------------------------------------------------
            # VALORES
            # ------------------------------------------------

            for data, valor in zip(
                datas_formatadas,
                quantidades
            ):

                ax.annotate(
                    str(valor),
                    (data, valor),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    color=TEXTO_GRAFICO
                )

            fig.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(
                fig
            )

        else:

            st.info(
                "Não há ocorrências para exibir."
            )