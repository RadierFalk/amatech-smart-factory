"""T08 Histórico (RF13). Supervisor e Gestor/Diretoria consultam os registros do período e baixam em CSV."""
import streamlit as st

from pages.comum import csv_para_download, data_br, data_hora_br, exigir, filtros, tabela
from servicos.historico import ServicoHistorico

exigir("historico")
st.title("Histórico")

historico = ServicoHistorico()
filtro = filtros("historico")
if filtro is None:
    st.stop()

# Aba: (consulta, colunas mostradas, colunas de data e de data e hora a formatar)
ABAS = {
    "Produção": (historico.producao, {
        "data": "Data", "turno": "Turno", "produto": "Produto", "qtd_meta": "Meta", "qtd_realizada": "Realizada",
        "qtd_aprovada": "Aprovada", "qtd_reprovada": "Reprovada", "pct_meta": "% da meta",
        "registrado_por": "Registrado por", "origem": "Origem"}, ["data"], []),
    "Defeitos": (historico.defeitos, {
        "data_hora": "Data e hora", "turno": "Turno", "produto": "Produto", "tipo_defeito": "Tipo de defeito",
        "estacao": "Estação", "maquina": "Máquina", "quantidade": "Qtd.", "retrabalho": "Em retrabalho",
        "observacao": "Observação", "registrado_por": "Registrado por", "origem": "Origem"}, [], ["data_hora"]),
    "Paradas": (historico.paradas, {
        "inicio": "Início", "fim": "Fim", "duracao_min": "Duração (min)", "situacao": "Situação", "turno": "Turno",
        "estacao": "Estação", "maquina": "Máquina", "motivo": "Motivo", "observacao": "Observação",
        "registrado_por": "Registrado por", "origem": "Origem"}, [], ["inicio", "fim"]),
    "Perdas": (historico.perdas, {
        "data": "Data", "turno": "Turno", "estacao": "Estação", "produto": "Produto", "tipo_perda": "Tipo de perda",
        "quantidade": "Qtd.", "observacao": "Observação", "registrado_por": "Registrado por",
        "origem": "Origem"}, ["data"], []),
}

for aba, (nome, (consulta, colunas, datas, datas_horas)) in zip(st.tabs(list(ABAS)), ABAS.items()):
    with aba:
        linhas = consulta(filtro)
        for l in linhas:
            for c in datas:
                l[c] = data_br(l[c])
            for c in datas_horas:
                l[c] = data_hora_br(l[c])
        quadro = tabela(linhas, colunas, vazio="Nenhum registro no período.")
        if quadro is not None:
            st.download_button("Baixar CSV", csv_para_download(quadro), mime="text/csv", key=f"baixar_{nome}",
                               file_name=f"{nome.lower()}_{filtro.data_inicial:%Y-%m-%d}_{filtro.data_final:%Y-%m-%d}.csv")
            st.caption(f"{len(linhas)} registro(s).")
