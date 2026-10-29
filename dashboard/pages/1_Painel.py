"""T02 Painel de indicadores (RF06 a RF12, RF17). Supervisor e Gestor/Diretoria."""
import plotly.graph_objects as go
import streamlit as st

from pages.comum import cartao, exigir, filtros, hora, minutos, numero, percentual
from servicos.alertas import AvaliadorAlertas
from servicos.calculadora import CalculadoraIndicadores

exigir("painel")
st.title("Painel de indicadores")

calculadora = CalculadoraIndicadores()
alertas = AvaliadorAlertas()
filtro = filtros("painel")

# Aviso de paradas em andamento: não depende do filtro, a máquina está parada agora
andamento = calculadora.paradas_em_andamento()
if andamento:
    itens = " | ".join(f"{p['estacao']}{' · ' + p['maquina'] if p['maquina'] else ''} · {p['motivo'].lower()} · "
                       f"desde {hora(p['inicio'])}" for p in andamento)
    st.warning(f"{len(andamento)} parada(s) em andamento: {itens}")

if filtro is None:
    st.stop()

r = calculadora.calcular(filtro)
if not r.tem_dados:
    st.info("Não há registros para o período e os filtros escolhidos.")

c = st.columns(6)
with c[0]:
    cartao("Atendimento da meta", percentual(r.atendimento_meta),
           f"{numero(r.realizada)} de {numero(r.meta)}" if r.meta else "sem meta cadastrada (RN03)",
           alertas.classificar("atendimento_meta", r.atendimento_meta))
with c[1]:
    cartao("Índice de defeitos", percentual(r.indice_defeitos), f"{numero(r.reprovada)} reprovados",
           alertas.classificar("indice_defeitos", r.indice_defeitos))
with c[2]:
    cartao("Índice de retrabalho", percentual(r.indice_retrabalho), f"{numero(r.retrabalho)} unidades",
           alertas.classificar("indice_retrabalho", r.indice_retrabalho))
with c[3]:
    cartao("Produtividade", f"{numero(r.produtividade, 1)} un/h" if r.produtividade else "—",
           f"{numero(r.minutos_produtivos)} min produtivos")
with c[4]:
    detalhe = f"{r.tempo_parada.encerradas} encerrada(s)"
    if r.tempo_parada.em_andamento:
        detalhe += f", {r.tempo_parada.em_andamento} em andamento"
    cartao("Tempo de parada", minutos(r.tempo_parada.minutos), detalhe)
with c[5]:
    cartao("Perdas", f"{numero(r.perdas)} un.", ", ".join(p["tipo"] for p in r.perdas_por_tipo[:2]) or "nenhuma")


def grafico(titulo, rotulos, valores, sufixo="", cores=None):
    """Barras horizontais, no estilo dos wireframes."""
    if not valores or not any(valores):
        st.markdown(f"**{titulo}**")
        st.caption("Sem dados no período.")
        return
    figura = go.Figure(go.Bar(x=valores, y=rotulos, orientation="h", marker_color=cores or "#757575",
                              text=[numero(v) + sufixo for v in valores], textposition="outside", cliponaxis=False))
    figura.update_layout(title=titulo, height=90 + 45 * len(rotulos), margin=dict(l=10, r=60, t=40, b=10),
                         xaxis=dict(visible=False), yaxis=dict(autorange="reversed"), showlegend=False)
    st.plotly_chart(figura, config={"displayModeBar": False})


esquerda, direita = st.columns(2)
with esquerda:
    grafico("Produção realizada × meta", ["Meta", "Realizada"], [r.meta, r.realizada], cores=["#bdbdbd", "#616161"])
    paradas = calculadora.parada_por_turno(filtro)
    grafico("Tempo de parada por turno", [l["turno"] for l in paradas], [l["minutos"] for l in paradas], " min")
with direita:
    defeitos = calculadora.defeitos_por_estacao(filtro)
    grafico("Defeitos por estação", [l["estacao"] for l in defeitos], [l["quantidade"] for l in defeitos])
    retrabalho = calculadora.retrabalho_por_estacao(filtro)
    grafico("Retrabalho por estação de retorno", [l["estacao"] for l in retrabalho],
            [l["quantidade"] for l in retrabalho])

st.caption("Cores: só os três indicadores com limites cadastrados recebem o semáforo; os demais ficam em cinza.")
