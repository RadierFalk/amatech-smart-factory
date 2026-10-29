"""T09 Cadastros (UC03) e limites do semáforo (RF17, RN08, UC16).

O Administrador edita todas as listas. O Supervisor vê só a aba "Limites do semáforo".
Itens não são apagados pela tela: os registros antigos continuam apontando para eles.
"""
import pandas as pd
import streamlit as st

from pages.comum import exigir, mostrar_erro, pode
from servicos.alertas import NOMES_INDICADORES, AvaliadorAlertas
from servicos.cadastros import CADASTROS, CATEGORIAS_DEFEITO, TIPOS_MOTIVO, ServicoCadastros
from servicos.erros import ErroValidacao

exigir("cadastros", "limites")
cadastros = ServicoCadastros()
alertas = AvaliadorAlertas()

ROTULOS = {"nome": "Nome", "hora_inicio": "Início (HH:MM)", "hora_fim": "Fim (HH:MM)", "duracao_min": "Duração (min)",
           "modelo": "Modelo", "descricao": "Descrição", "ativo": "Ativo", "setor": "Setor",
           "ordem_fluxo": "Ordem no fluxo", "codigo": "Código", "estacao": "Estação", "categoria": "Categoria",
           "tipo": "Tipo"}


def aba_cadastro(cadastro):
    c = CADASTROS[cadastro]
    linhas = cadastros.listar(cadastro)
    colunas = [c["chave"]] + c["colunas"]
    quadro = pd.DataFrame(linhas, columns=colunas)
    config = {c["chave"]: st.column_config.NumberColumn("Id", disabled=True)}
    config.update({col: ROTULOS.get(col, col) for col in c["colunas"]})
    if cadastro == "maquina":   # mostra o nome da estação no lugar do id
        estacoes = {e["id_estacao"]: e["nome"] for e in cadastros.listar_estacoes()}
        quadro["estacao"] = quadro.pop("id_estacao").map(estacoes)
        config["estacao"] = st.column_config.SelectboxColumn("Estação", options=list(estacoes.values()), required=True)
    elif cadastro == "produto":
        quadro["ativo"] = quadro["ativo"].astype(bool)
        config["ativo"] = st.column_config.CheckboxColumn("Ativo", default=True)
    elif cadastro == "motivo_parada":
        config["tipo"] = st.column_config.SelectboxColumn("Tipo", options=list(TIPOS_MOTIVO), required=True)
    elif cadastro == "tipo_defeito":
        config["categoria"] = st.column_config.SelectboxColumn("Categoria", options=list(CATEGORIAS_DEFEITO))

    st.caption("Tabela editável: clique numa célula para alterar o valor; use a última linha para acrescentar um item.")
    editado = st.data_editor(quadro, column_config=config, num_rows="add", hide_index=True, width="stretch",
                             key=f"editor_{cadastro}")
    if st.button("Salvar alterações", type="primary", key=f"salvar_{cadastro}"):
        registros = editado.to_dict("records")
        if cadastro == "maquina":
            ids = {nome: id_ for id_, nome in estacoes.items()}
            for r in registros:
                r["id_estacao"] = ids.get(r.pop("estacao"))
        try:
            quantidade = cadastros.salvar(cadastro, registros)
            st.success(f"{c['titulo']}: {quantidade} item(ns) salvos.")
        except ErroValidacao as erro:
            mostrar_erro(erro)


def aba_limites():
    limites = alertas.limites()
    quadro = pd.DataFrame([{"indicador": l["indicador"], "nome": NOMES_INDICADORES.get(l["indicador"], l["indicador"]),
                            "limite_verde": l["limite_verde"], "limite_amarelo": l["limite_amarelo"],
                            "sentido": "maior é melhor" if l["sentido"] == "maior_melhor" else "menor é melhor"}
                           for l in limites.values()])
    st.caption("Tabela editável: clique numa célula de Verde ou Amarelo para alterar o limite (%).")
    editado = st.data_editor(
        quadro, hide_index=True, width="stretch", disabled=["nome", "sentido"], column_order=[
            "nome", "limite_verde", "limite_amarelo", "sentido"],
        column_config={"nome": "Indicador", "sentido": "Sentido",
                       "limite_verde": st.column_config.NumberColumn("Verde (%)", min_value=0, step=0.5),
                       "limite_amarelo": st.column_config.NumberColumn("Amarelo (%)", min_value=0, step=0.5)},
        key="editor_limites")
    st.caption("Maior é melhor: verde a partir do limite verde, amarelo a partir do amarelo. Menor é melhor: verde "
               "até o limite verde, amarelo até o amarelo. Fora da faixa amarela, o indicador fica vermelho.")
    if st.button("Salvar alterações", type="primary", key="salvar_limites"):
        try:
            for l in editado.to_dict("records"):
                alertas.salvar_limites(l["indicador"], l["limite_verde"], l["limite_amarelo"])
            st.success("Alterações salvas. O painel já usa os novos limites.")
        except ErroValidacao as erro:
            mostrar_erro(erro)


if pode("cadastros"):
    st.title("Cadastros")
    nomes = [CADASTROS[c]["titulo"] for c in CADASTROS] + ["Limites do semáforo"]
    for aba, chave in zip(st.tabs(nomes), list(CADASTROS) + ["limites"]):
        with aba:
            if chave == "limites":
                aba_limites()
            else:
                aba_cadastro(chave)
else:
    st.title("Limites do semáforo")
    aba_limites()
