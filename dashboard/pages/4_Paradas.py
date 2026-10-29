"""T05 Paradas (RF05, RN04). Manutenção e Supervisor iniciam e encerram paradas; a duração é calculada."""
import streamlit as st

import config
from pages.comum import data_e_hora, exigir, hora, minutos, mostrar_erro, opcoes, tabela
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.formatos import ler_data_hora
from servicos.historico import ServicoHistorico
from servicos.registro import ServicoRegistro

usuario = exigir("paradas")
st.title("Paradas")

cadastros = ServicoCadastros()
registro = ServicoRegistro()
historico = ServicoHistorico()

st.subheader("Iniciar parada")
c = st.columns(3)
ids_estacao, rotulo_estacao = opcoes(cadastros.listar_estacoes(), "id_estacao", "nome")
id_estacao = c[0].selectbox("Estação", ids_estacao, format_func=rotulo_estacao)
ids_maquina, rotulo_maquina = opcoes(cadastros.listar_maquinas(id_estacao), "id_maquina",
                                     lambda m: f"{m['codigo']} · {m['nome']}", vazio="—")
id_maquina = c[1].selectbox("Máquina (opcional)", ids_maquina, format_func=rotulo_maquina)
ids_motivo, rotulo_motivo = opcoes(cadastros.listar_motivos_parada(), "id_motivo",
                                   lambda m: f"{m['descricao']} ({m['tipo']})")
id_motivo = c[2].selectbox("Motivo", ids_motivo, format_func=rotulo_motivo)

c = st.columns(2)
inicio = data_e_hora("Início", "inicio", coluna=c[0])
encerrada = st.checkbox("Parada já encerrada (informar o fim)")
fim = data_e_hora("Fim", "fim", coluna=c[1]) if encerrada else None
ids_turno, rotulo_turno = opcoes(cadastros.listar_turnos(), "id_turno", "nome")
turno = cadastros.turno_por_horario(inicio)
id_turno = st.selectbox("Turno", ids_turno, format_func=rotulo_turno,
                        index=ids_turno.index(turno["id_turno"]) if turno else 0,
                        help="Preenchido pelo horário de início; pode ser alterado.")
observacao = st.text_input("Observação (opcional)")
if st.button("Iniciar parada" if not encerrada else "Registrar parada", type="primary"):
    try:
        registro.registrar_parada(id_estacao, id_turno, id_motivo, inicio, usuario.id, fim=fim, id_maquina=id_maquina,
                                  observacao=observacao)
        st.success("Parada registrada.")
    except ErroValidacao as erro:
        mostrar_erro(erro)

st.subheader("Paradas em andamento")
andamento = historico.paradas_recentes(limite=50, em_andamento=True)
if not andamento:
    st.caption("Nenhuma parada em andamento.")
else:
    larguras = [2, 1.2, 2, 1.6, 1.3, 1]
    cabecalho = st.columns(larguras)
    for coluna, titulo in zip(cabecalho, ["Estação", "Máquina", "Motivo", "Início", "Tempo decorrido", "Ação"]):
        coluna.markdown(f"**{titulo}**")
    for p in andamento:
        linha = st.columns(larguras)
        linha[0].write(p["estacao"])
        linha[1].write(p["maquina"] or "—")
        linha[2].write(p["motivo"])
        linha[3].write(ler_data_hora(p["inicio"]).strftime("%d/%m %H:%M"))
        linha[4].write(minutos(p["duracao_min"]))
        if linha[5].button("Encerrar", key=f"encerrar_{p['id_parada']}"):
            try:
                registro.encerrar_parada(p["id_parada"], config.agora())
                st.rerun()
            except ErroValidacao as erro:
                mostrar_erro(erro)

st.subheader("Paradas encerradas hoje")
hoje = config.agora().date()
encerradas = [p for p in historico.paradas_recentes(limite=100, em_andamento=False)
              if ler_data_hora(p["fim"]).date() == hoje]
for p in encerradas:
    p["hora_inicio"], p["hora_fim"], p["duracao"] = hora(p["inicio"]), hora(p["fim"]), minutos(p["duracao_min"])
tabela(encerradas, {"estacao": "Estação", "maquina": "Máquina", "motivo": "Motivo", "hora_inicio": "Início",
                    "hora_fim": "Fim", "duracao": "Duração", "origem": "Origem"},
       vazio="Nenhuma parada encerrada hoje.")
st.caption("A duração é calculada pelo sistema a partir do início e do fim. "
           "O botão \"Encerrar\" grava o horário atual como fim da parada.")
