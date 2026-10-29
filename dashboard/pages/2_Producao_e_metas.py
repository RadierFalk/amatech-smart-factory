"""T03 Produção e metas (RF01, RF02). Operador registra a produção; Supervisor também cadastra as metas."""
import streamlit as st

import config
from pages.comum import data_br, exigir, mostrar_erro, numero, opcoes, pode, tabela
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.historico import ServicoHistorico
from servicos.registro import ServicoRegistro

usuario = exigir("producao", "metas")
st.title("Produção e metas")

cadastros = ServicoCadastros()
registro = ServicoRegistro()
historico = ServicoHistorico()
turnos = cadastros.listar_turnos()
produtos = cadastros.listar_produtos()
ids_turno, rotulo_turno = opcoes(turnos, "id_turno", "nome")
ids_produto, rotulo_produto = opcoes(produtos, "id_produto", "modelo")
agora = config.agora()
turno_atual = cadastros.turno_por_horario(agora)
indice_turno = ids_turno.index(turno_atual["id_turno"]) if turno_atual else 0


def campos_comuns(chave):
    """Data e turno vêm preenchidos pelo relógio e podem ser alterados."""
    c = st.columns(3)
    data = c[0].date_input("Data", agora.date(), format="DD/MM/YYYY", key=f"{chave}_data")
    id_turno = c[1].selectbox("Turno", ids_turno, index=indice_turno, format_func=rotulo_turno, key=f"{chave}_turno")
    id_produto = c[2].selectbox("Produto", ids_produto, format_func=rotulo_produto, key=f"{chave}_produto")
    return data, id_turno, id_produto


abas = []
if pode("producao"):
    abas.append("Registrar produção")
if pode("metas"):
    abas.append("Metas")
for aba, nome in zip(st.tabs(abas), abas):
    with aba:
        if nome == "Registrar produção":
            data, id_turno, id_produto = campos_comuns("producao")
            c = st.columns(3)
            realizada = c[0].number_input("Quantidade realizada", min_value=0, step=1)
            aprovada = c[1].number_input("Quantidade aprovada", min_value=0, step=1)
            reprovada = c[2].number_input("Quantidade reprovada", min_value=0, step=1)
            if aprovada + reprovada == realizada:
                st.markdown(f":green[✓ Aprovados + reprovados = {numero(realizada)} (confere com a quantidade realizada)]")
            else:
                st.markdown(f":red[✗ Aprovados + reprovados = {numero(aprovada + reprovada)}, "
                            f"mas a quantidade realizada é {numero(realizada)}]")
            if st.button("Registrar produção", type="primary"):
                try:
                    registro.registrar_producao(data, id_turno, id_produto, realizada, aprovada, reprovada, usuario.id)
                    st.success("Produção registrada com sucesso.")
                except ErroValidacao as erro:
                    mostrar_erro(erro)

            st.subheader("Últimos lançamentos")
            linhas = historico.registros_producao_recentes(limite=20)
            for l in linhas:
                l["data"] = data_br(l["data"])
            tabela(linhas, {"data": "Data", "turno": "Turno", "produto": "Produto", "qtd_realizada": "Realizada",
                            "qtd_aprovada": "Aprovada", "qtd_reprovada": "Reprovada",
                            "registrado_por": "Registrado por", "origem": "Origem"})
        else:
            data, id_turno, id_produto = campos_comuns("meta")
            qtd_meta = st.number_input("Meta (unidades)", min_value=0, step=10)
            if st.button("Cadastrar meta", type="primary"):
                try:
                    registro.registrar_meta(data, id_turno, id_produto, qtd_meta, usuario.id)
                    st.success("Meta cadastrada.")
                except ErroValidacao as erro:
                    mostrar_erro(erro)

            st.subheader("Metas cadastradas")
            linhas = historico.metas_recentes()
            for l in linhas:
                l["data"] = data_br(l["data"])
            tabela(linhas, {"data": "Data", "turno": "Turno", "produto": "Produto", "qtd_meta": "Meta",
                            "registrado_por": "Registrado por"})

st.caption("Data e turno vêm preenchidos pelo relógio e podem ser alterados. "
           "Só pode haver uma meta por dia, turno e produto (RN09).")
