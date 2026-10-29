"""Peças usadas por todas as telas: usuário logado, permissões, formatação brasileira, cartões do semáforo e filtros.

Regra da camada 1: as telas não calculam indicadores nem acessam o banco; chamam as classes de servicos/.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from servicos.autenticacao import ServicoAutenticacao
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.filtro import Filtro
from servicos.formatos import ler_data, ler_data_hora
from servicos.historico import ServicoHistorico

CORES = {   # semáforo: (borda, fundo, texto)
    "verde": ("#2e7d32", "#e8f5e9", "#1b5e20"),
    "amarelo": ("#f9a825", "#fff8e1", "#6d5200"),
    "vermelho": ("#c62828", "#ffebee", "#8e0000"),
    None: ("#bdbdbd", "#fafafa", "#616161"),
}


# ---------------------------------------------------------------- sessão e permissões
def usuario_logado():
    return st.session_state.get("usuario")


def exigir(*funcoes):
    """Interrompe a tela se o usuário não tiver nenhuma das permissões (RF19)."""
    usuario = usuario_logado()
    if not any(ServicoAutenticacao.tem_permissao(usuario, f) for f in funcoes):
        st.error("Você não tem permissão para acessar esta tela.")
        st.stop()
    return usuario


def pode(funcao):
    return ServicoAutenticacao.tem_permissao(usuario_logado(), funcao)


def mostrar_erro(erro):
    """Mostra os problemas de um ErroValidacao, um por linha."""
    problemas = erro.problemas if isinstance(erro, ErroValidacao) else [(None, str(erro))]
    st.error("\n".join(f"- {mensagem}" for _, mensagem in problemas))


# ---------------------------------------------------------------- formatação brasileira
def numero(valor, casas=0):
    """1420 -> '1.420'; 94.666 -> '94,7' (com casas=1)."""
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def percentual(valor):
    return "—" if valor is None else numero(valor, 1) + "%"


def data_br(valor):
    """Aceita só a data ('2026-08-15') ou data e hora ('2026-08-15 09:30')."""
    data = (ler_data(valor) or ler_data_hora(valor)) if valor else None
    return data.strftime("%d/%m/%Y") if data else ""


def data_hora_br(valor):
    momento = ler_data_hora(valor) if valor else None
    return momento.strftime("%d/%m/%Y %H:%M") if momento else ""


def hora(valor):
    momento = ler_data_hora(valor) if valor else None
    return momento.strftime("%H:%M") if momento else ""


def minutos(valor):
    return f"{numero(valor, 0)} min"


# ---------------------------------------------------------------- componentes
def cartao(titulo, valor, detalhe="", cor=None):
    """Cartão de indicador. Só os indicadores com limites recebem cor; os outros ficam em cinza."""
    borda, fundo, texto = CORES.get(cor, CORES[None])
    largura = "6px" if cor else "1px"
    st.markdown(
        f"""<div style="border:1px solid {borda};border-left:{largura} solid {borda};background:{fundo};
                        border-radius:8px;padding:12px 14px;height:118px;margin-bottom:8px">
              <div style="font-size:0.85rem;color:#424242">{titulo}</div>
              <div style="font-size:1.7rem;font-weight:700;color:#212121;line-height:1.5">{valor}</div>
              <div style="font-size:0.8rem;color:{texto}">{detalhe}</div>
            </div>""",
        unsafe_allow_html=True)


def tabela(linhas, colunas, vazio="Nenhum registro."):
    """Mostra uma lista de dicionários com os nomes de coluna em português. `colunas` = {chave: rótulo}."""
    if not linhas:
        st.caption(vazio)
        return None
    quadro = pd.DataFrame(linhas)[list(colunas)].rename(columns=colunas)
    st.dataframe(quadro, hide_index=True, width="stretch")
    return quadro


def csv_para_download(quadro):
    """CSV que abre certo no Excel em português: ';' e UTF-8 com BOM."""
    return quadro.to_csv(sep=";", index=False, decimal=",").encode("utf-8-sig")


def opcoes(linhas, chave, rotulo, vazio=None):
    """Lista de ids e função de rótulo para um st.selectbox. `vazio` acrescenta uma opção None no início."""
    nomes = {l[chave]: (rotulo(l) if callable(rotulo) else l[rotulo]) for l in linhas}
    ids = ([None] if vazio is not None else []) + list(nomes)
    return ids, (lambda i: vazio if i is None else nomes[i])


# ---------------------------------------------------------------- filtros (RF12, RN05)
def data_padrao():
    """Data do último registro de produção (assim o painel não abre vazio); sem registros, hoje."""
    recentes = ServicoHistorico().registros_producao_recentes(limite=1)
    return ler_data(recentes[0]["data"]) if recentes else config.agora().date()


def filtros(chave, com_produto=True):
    """Data inicial, data final, turno e produto. Devolve um Filtro válido ou None (com a mensagem na tela)."""
    cadastros = ServicoCadastros()
    padrao = st.session_state.setdefault("data_padrao", data_padrao())
    colunas = st.columns(4 if com_produto else 3)
    inicio = colunas[0].date_input("Data inicial", padrao, format="DD/MM/YYYY", key=f"{chave}_ini")
    fim = colunas[1].date_input("Data final", padrao, format="DD/MM/YYYY", key=f"{chave}_fim")
    ids, rotulo = opcoes(cadastros.listar_turnos(), "id_turno", "nome", vazio="Todos")
    id_turno = colunas[2].selectbox("Turno", ids, format_func=rotulo, key=f"{chave}_turno")
    id_produto = None
    if com_produto:
        ids, rotulo = opcoes(cadastros.listar_produtos(apenas_ativos=False), "id_produto", "modelo", vazio="Todos")
        id_produto = colunas[3].selectbox("Produto", ids, format_func=rotulo, key=f"{chave}_produto")
    filtro = Filtro(inicio, fim, id_turno, id_produto)
    try:
        return filtro.validar()
    except ErroValidacao as erro:
        mostrar_erro(erro)
        return None


def data_e_hora(rotulo, chave, valor=None, coluna=None):
    """Data e hora em dois campos, devolvidas como um datetime."""
    alvo = coluna or st
    valor = valor or config.agora()
    c1, c2 = alvo.columns(2)
    dia = c1.date_input(rotulo, valor.date(), format="DD/MM/YYYY", key=f"{chave}_data")
    momento = c2.time_input("Hora", valor.time(), step=60, key=f"{chave}_hora")
    return datetime.combine(dia, momento)
