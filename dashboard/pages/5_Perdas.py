"""T06 Perdas (RF15, RN07). Supervisor registra componentes e materiais perdidos."""
import streamlit as st

import config
from pages.comum import data_br, exigir, mostrar_erro, opcoes, tabela
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.historico import ServicoHistorico
from servicos.registro import ServicoRegistro

usuario = exigir("perdas")
st.title("Perdas")

cadastros = ServicoCadastros()
registro = ServicoRegistro()
agora = config.agora()

c = st.columns(3)
data = c[0].date_input("Data", agora.date(), format="DD/MM/YYYY")
ids_turno, rotulo_turno = opcoes(cadastros.listar_turnos(), "id_turno", "nome")
turno = cadastros.turno_por_horario(agora)
id_turno = c[1].selectbox("Turno", ids_turno, format_func=rotulo_turno,
                          index=ids_turno.index(turno["id_turno"]) if turno else 0)
ids_estacao, rotulo_estacao = opcoes(cadastros.listar_estacoes(), "id_estacao", "nome")
id_estacao = c[2].selectbox("Estação", ids_estacao, format_func=rotulo_estacao)

c = st.columns(3)
ids_produto, rotulo_produto = opcoes(cadastros.listar_produtos(), "id_produto", "modelo")
id_produto = c[0].selectbox("Produto", ids_produto, format_func=rotulo_produto)
ids_tipo, rotulo_tipo = opcoes(cadastros.listar_tipos_perda(), "id_tipo_perda", "descricao")
id_tipo = c[1].selectbox("Tipo de perda", ids_tipo, format_func=rotulo_tipo)
quantidade = c[2].number_input("Quantidade", min_value=1, step=1)
observacao = st.text_input("Observação (opcional)")

if st.button("Registrar perda", type="primary"):
    try:
        registro.registrar_perda(data, id_turno, id_estacao, id_produto, id_tipo, quantidade, usuario.id,
                                 observacao=observacao)
        st.success("Perda registrada.")
    except ErroValidacao as erro:
        mostrar_erro(erro)

st.subheader("Últimas perdas registradas")
linhas = ServicoHistorico().perdas_recentes()
for l in linhas:
    l["data"] = data_br(l["data"])
tabela(linhas, {"data": "Data", "turno": "Turno", "estacao": "Estação", "produto": "Produto",
                "tipo_perda": "Tipo de perda", "quantidade": "Qtd.", "observacao": "Observação",
                "registrado_por": "Registrado por", "origem": "Origem"})
