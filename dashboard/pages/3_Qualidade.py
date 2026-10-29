"""T04 Qualidade (RF03, RF04). Operador e Inspetor registram defeitos; o Inspetor também registra o retrabalho."""
import streamlit as st

from pages.comum import data_br, data_e_hora, data_hora_br, exigir, hora, mostrar_erro, opcoes, pode, tabela
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.historico import ServicoHistorico
from servicos.registro import ServicoRegistro

usuario = exigir("defeitos", "retrabalho")
st.title("Qualidade")

cadastros = ServicoCadastros()
registro = ServicoRegistro()
historico = ServicoHistorico()
estacoes = cadastros.listar_estacoes()
ids_estacao, rotulo_estacao = opcoes(estacoes, "id_estacao", "nome")

abas = []
if pode("defeitos"):
    abas.append("Registrar defeito")
if pode("retrabalho"):
    abas.append("Registrar retrabalho")
for aba, nome in zip(st.tabs(abas), abas):
    with aba:
        if nome == "Registrar defeito":
            producoes = historico.registros_producao_recentes(limite=50)
            if not producoes:
                st.info("Registre a produção antes: todo defeito pertence a um registro de produção.")
                continue
            ids, rotulo = opcoes(producoes, "id_producao",
                                 lambda l: f"{data_br(l['data'])} · {l['turno']} · {l['produto']}")
            id_producao = st.selectbox("Registro de produção de origem", ids, format_func=rotulo)
            c = st.columns(3)
            ids_tipo, rotulo_tipo = opcoes(cadastros.listar_tipos_defeito(), "id_tipo_defeito", "descricao")
            id_tipo = c[0].selectbox("Tipo de defeito", ids_tipo, format_func=rotulo_tipo)
            id_estacao = c[1].selectbox("Estação", ids_estacao, format_func=rotulo_estacao, key="defeito_estacao")
            # A lista de máquinas mostra só as da estação escolhida
            ids_maquina, rotulo_maquina = opcoes(cadastros.listar_maquinas(id_estacao), "id_maquina",
                                                 lambda m: f"{m['codigo']} · {m['nome']}", vazio="—")
            id_maquina = c[2].selectbox("Máquina (opcional)", ids_maquina, format_func=rotulo_maquina)
            c = st.columns([1, 2])
            quantidade = c[0].number_input("Quantidade", min_value=1, step=1)
            observacao = c[1].text_input("Observação (opcional)")
            momento = data_e_hora("Data da detecção", "defeito")
            if st.button("Registrar defeito", type="primary"):
                try:
                    registro.registrar_defeito(id_producao, id_tipo, id_estacao, quantidade, momento, usuario.id,
                                               id_maquina=id_maquina, observacao=observacao)
                    st.success("Defeito registrado.")
                except ErroValidacao as erro:
                    mostrar_erro(erro)
        else:
            defeitos = historico.defeitos_recentes(limite=50)
            if not defeitos:
                st.info("Não há defeitos registrados para associar ao retrabalho.")
                continue
            ids, rotulo = opcoes(defeitos, "id_defeito",
                                 lambda d: f"{data_hora_br(d['data_hora'])} · {d['tipo_defeito']} · {d['estacao']} · "
                                           f"{d['quantidade']} un. ({d['retrabalho']} já em retrabalho)")
            id_defeito = st.selectbox("Defeito de origem", ids, format_func=rotulo)
            c = st.columns([1, 2, 1])
            indice = next((i for i, e in enumerate(estacoes) if e["nome"] == "Montagem final"), 0)
            id_retorno = c[0].selectbox("Estação de retorno", ids_estacao, index=indice, format_func=rotulo_estacao)
            motivo = c[1].text_input("Motivo do retrabalho")
            quantidade = c[2].number_input("Quantidade em retrabalho", min_value=1, step=1)
            momento = data_e_hora("Data do retrabalho", "retrabalho")
            if st.button("Registrar retrabalho", type="primary"):
                try:
                    registro.registrar_retrabalho(id_defeito, id_retorno, motivo, quantidade, momento, usuario.id)
                    st.success("Retrabalho registrado.")
                except ErroValidacao as erro:
                    mostrar_erro(erro)

st.subheader("Últimos defeitos registrados")
linhas = historico.defeitos_recentes(limite=20)
for l in linhas:
    l["dia"], l["hora"] = data_br(l["data_hora"]), hora(l["data_hora"])
tabela(linhas, {"dia": "Data", "hora": "Hora", "tipo_defeito": "Tipo de defeito", "estacao": "Estação",
                "quantidade": "Qtd.", "retrabalho": "Em retrabalho"})
st.caption("O retrabalho exige o defeito de origem, a estação de retorno, o motivo e a quantidade (RN02).")
