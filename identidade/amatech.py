"""Identidade visual AMATECH para as telas em Streamlit (Qualidade, Manutenção e Dashboard).

Lê as cores de tokens.json (a mesma fonte do guia de estilo) e oferece as peças comuns: estilos, cabeçalho,
tela de login, cartão de indicador, etiqueta de estado e o tema dos gráficos em Matplotlib.
As cores do tema do Streamlit (botões, campos, barra lateral, Plotly) ficam no .streamlit/config.toml de cada
sistema, gerado por identidade/gerar_temas.py a partir dos mesmos tokens.
"""
import base64
import html
import json
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
SIMBOLO = PASTA / "amatech-simbolo.svg"

_tokens = json.loads((PASTA / "tokens.json").read_text(encoding="utf-8"))
_brutos = {t["name"]: t["value"] for t in _tokens["color"]["tokens"]}
# "{sinal}" é um apelido para outro token
CORES = {nome: (_brutos[v[1:-1]] if v.startswith("{") else v) for nome, v in _brutos.items()}
FONTES = _tokens["type"]["families"]

SETORES = {
    "ERP": "ERP Suite Industrial",
    "RAS": "Rastreabilidade de Produtos",
    "QLD": "Controle da Qualidade",
    "MNT": "Controle da Manutenção",
    "DSH": "Dashboard Industrial",
}

# Tom da etiqueta para cada estado usado nos setores (guia: componente Etiqueta)
TONS = {
    "aprovado": "ok", "funcionando": "ok", "operacional": "ok", "concluido": "ok", "concluído": "ok",
    "fechada": "ok", "resolvida": "ok", "verde": "ok", "dentro": "ok",
    "em_reprocesso": "atencao", "em reprocesso": "atencao", "em_manutencao": "atencao", "em manutenção": "atencao",
    "em_andamento": "atencao", "em andamento": "atencao", "alta": "atencao", "amarelo": "atencao",
    "atenção": "atencao", "em_analise": "atencao", "em análise": "atencao",
    "reprovado": "critico", "parada": "critico", "parado": "critico", "indisponivel": "critico",
    "indisponível": "critico", "critica": "critico", "crítica": "critico", "critico": "critico",
    "crítico": "critico", "vermelho": "critico",
    "aberto": "info", "aberta": "info", "media": "info", "média": "info", "em montagem": "info",
    "em fila": "neutro", "baixa": "neutro", "cancelado": "neutro",
}
ROTULO_SEMAFORO = {"ok": "Dentro", "atencao": "Atenção", "critico": "Crítico"}


def esc(valor) -> str:
    return html.escape("" if valor is None else str(valor))


def simbolo_data_uri() -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(SIMBOLO.read_bytes()).decode()


def turno_atual(agora: datetime | None = None) -> str:
    """Turnos da fábrica: 06h–14h e 14h–22h (horário de Manaus)."""
    hora = (agora or datetime.now()).hour
    if 6 <= hora < 14:
        return "1º turno · 06h–14h"
    if 14 <= hora < 22:
        return "2º turno · 14h–22h"
    return "Fora de turno"


def tom(estado) -> str:
    """Tom da etiqueta (ok, atencao, critico, info, neutro) para um estado de qualquer setor."""
    return TONS.get(str(estado or "").strip().lower(), "neutro")


# ---------------------------------------------------------------- estilos
def _variaveis() -> str:
    linhas = [f"--{nome}: {valor};" for nome, valor in CORES.items()]
    for familia in ("spacing", "radius", "shadow"):
        linhas += [f"--{t['name']}: {t['value']};" for t in _tokens[familia]["tokens"]]
    linhas += [f"--font-{chave}: {pilha};" for chave, pilha in FONTES.items()]
    return ":root {" + " ".join(linhas) + "}"


CSS = """@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap");
""" + _variaveis() + """
/* Moldura do Streamlit: sem a barra branca do topo e com a margem do guia */
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.25rem; }
[data-testid="stMetricValue"] { font-family: var(--font-display); font-variant-numeric: tabular-nums; }
code, .am-codigo { font-family: var(--font-mono); font-weight: 500; }

h1, h2, h3 { font-family: var(--font-display) !important; font-weight: 600 !important; color: var(--tinta) !important; }

/* Cabeçalho */
.am-cab { background: var(--noite); color: var(--on-noite); display: flex; align-items: center; flex-wrap: wrap;
          gap: var(--space-4); padding: var(--space-2) var(--space-6); min-height: 56px;
          border-radius: var(--radius-md); margin-bottom: var(--space-4); }
.am-cab-marca { display: flex; align-items: center; gap: var(--space-2); }
.am-cab-marca img { width: 32px; height: 32px; display: block; }
.am-cab-marca b { font-family: var(--font-display); font-weight: 700; font-size: 18px; letter-spacing: .08em; color: var(--on-noite); }
.am-cab-sep { width: 1px; align-self: stretch; background: var(--noite-2); }
.am-cab-sistema { display: flex; flex-direction: column; gap: 2px; }
.am-cab-sistema span:last-child { font-size: 15px; font-weight: 600; color: var(--on-noite); }
.am-setor { display: inline-flex; align-items: center; gap: var(--space-1); font-family: var(--font-mono); font-weight: 500;
            font-size: 11px; line-height: 16px; letter-spacing: .06em; color: var(--led); }
.am-setor::before { content: ""; width: 6px; height: 6px; border-radius: var(--radius-pill); background: var(--led); }
.am-cab-info { margin-left: auto; display: flex; align-items: center; gap: var(--space-6); }
.am-cab-item small { display: block; font-size: 11px; line-height: 16px; color: var(--on-noite-suave); }
.am-cab-item b { font-weight: 600; color: var(--on-noite); }

/* Título da tela */
.am-titulo { margin: 0 0 var(--space-4); }
.am-breadcrumb { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--sinal); font-weight: 600; margin-bottom: 3px; }
.am-titulo h1 { font-family: var(--font-display); font-weight: 600; font-size: 24px; line-height: 30px; color: var(--tinta); margin: 0; padding: 0; }
.am-titulo p { margin: 3px 0 0; color: var(--tinta-2); font-size: 14px; }

/* Cartão de indicador */
.am-kpi { background: var(--superficie); border: 1px solid var(--linha); border-radius: var(--radius-md); box-shadow: var(--sombra-cartao);
          padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-1); min-height: 140px;
          box-sizing: border-box; margin-bottom: var(--space-2); transition: transform 0.15s ease, box-shadow 0.15s ease; }
.am-kpi:hover { box-shadow: 0 4px 12px rgba(13, 27, 42, 0.08); }
.am-kpi-topo { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: var(--space-1) var(--space-2); }
.am-kpi-rotulo { font-size: 11px; line-height: 16px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--tinta-2); }
.am-kpi-valor { font-family: var(--font-display); font-weight: 600; font-size: 30px; line-height: 34px; font-variant-numeric: tabular-nums; color: var(--tinta); }
.am-kpi-valor small { font-family: var(--font-sans); font-size: 14px; font-weight: 400; color: var(--tinta-2); }
.am-kpi-detalhe { font-size: 12px; line-height: 16px; color: var(--tinta-2); }

/* Etiqueta de estado */
.am-etq { display: inline-flex; align-items: center; gap: 6px; height: 22px; padding: 0 10px; border-radius: var(--radius-pill);
          font-size: 12px; font-weight: 600; white-space: nowrap; line-height: 22px; }
.am-etq::before { content: ""; width: 7px; height: 7px; border-radius: var(--radius-pill); background: currentColor; }
.am-etq.ok { background: var(--ok-suave); color: var(--ok); }
.am-etq.atencao { background: var(--atencao-suave); color: var(--atencao); }
.am-etq.atencao::before { background: var(--atencao-sinal); }
.am-etq.critico { background: var(--critico-suave); color: var(--critico); }
.am-etq.info { background: var(--sinal-suave); color: var(--sinal-forte); }
.am-etq.neutro { background: var(--neutro-suave); color: var(--tinta-2); }

/* Badges de Setor em Fundo Claro (Contraste Aprovado WCAG AA) */
.am-badge-setor {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
}
.am-badge-setor.ras { background: #e0f4f7; color: #0e7c90; }
.am-badge-setor.qld { background: #eeeafa; color: #6a4bc4; }
.am-badge-setor.mnt { background: #f7e8f1; color: #a0407f; }
.am-badge-setor.dsh { background: #e6eefc; color: #1f5fd6; }
.am-badge-setor.usr { background: #e2f3e8; color: #1b7a43; }
.am-badge-setor.erp { background: var(--noite-2); color: var(--on-noite); }

/* Sidebar Global AMATECH */
section[data-testid="stSidebar"] {
  background-color: var(--noite) !important;
  border-right: 1px solid var(--noite-2) !important;
}
.sb-nav-grupo {
  font-size: 11px;
  line-height: 16px;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--on-noite-suave) !important;
  margin: 8px 4px 2px;
  padding: 6px 0 2px;
  font-weight: 600;
}
section[data-testid="stSidebar"] div.stButton > button {
  width: 100%;
  justify-content: flex-start !important;
  text-align: left !important;
  padding: 8px 12px !important;
  border-radius: var(--radius-sm) !important;
  font-size: 13.5px !important;
  font-weight: 400 !important;
  border: none !important;
  background: transparent !important;
  color: var(--on-noite) !important;
  margin-bottom: 2px !important;
  box-shadow: none !important;
  min-height: 36px !important;
  position: relative;
  transition: background 0.15s ease, color 0.15s ease;
}
section[data-testid="stSidebar"] div.stButton > button > div,
section[data-testid="stSidebar"] div.stButton > button p {
  justify-content: flex-start !important;
  text-align: left !important;
  width: 100%;
}
section[data-testid="stSidebar"] div.stButton > button:hover {
  background: var(--noite-2) !important;
  color: var(--on-noite) !important;
}
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid*="primary"],
section[data-testid="stSidebar"] div.stButton > button[kind="primary"],
section[data-testid="stSidebar"] div.stButton > button[data-testid*="primary"] {
  background: var(--azul) !important;
  background-color: var(--azul) !important;
  color: #ffffff !important;
  border: 1px solid var(--azul) !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
}
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] *,
section[data-testid="stSidebar"] button[kind="primary"] * {
  color: #ffffff !important;
  font-weight: 600 !important;
}

/* Menu lateral legada / st.navigation */
[data-testid="stSidebarNav"] a[aria-current="page"]::after { content: ""; position: absolute; right: 12px; width: 8px; height: 8px;
          border-radius: var(--radius-pill); background: var(--led); }
[data-testid="stSidebarNav"] a { position: relative; }
[data-testid="stSidebarNavSeparator"] { border-color: var(--noite-2); }
.am-menu-usuario { padding: var(--space-2) 0; }
.am-menu-usuario b { display: block; font-weight: 600; color: var(--on-noite); }
.am-menu-usuario small { color: var(--on-noite-suave); font-size: 12px; }
"""

CSS_LOGIN = """
.stApp, [data-testid="stAppViewContainer"] { background: var(--noite); }
.am-login-marca { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); margin: var(--space-6) 0 var(--space-4); }
.am-login-marca img { width: 52px; height: 52px; }
.am-login-marca b { font-family: var(--font-display); font-weight: 700; font-size: 24px; letter-spacing: .08em; color: var(--on-noite); }
.am-login-marca span.am-setor { font-size: 12px; }
.am-login-marca span.nome { color: var(--on-noite); font-size: 16px; font-weight: 600; }
[data-testid="stForm"] { background: var(--superficie); border: 1px solid var(--linha); border-radius: var(--radius-md); padding: var(--space-6); box-shadow: 0 10px 25px rgba(0,0,0,0.25); }
.am-login-persona-box { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius-md); padding: var(--space-4); margin-top: var(--space-4); }
.am-login-nota { color: var(--on-noite-suave); font-size: 12px; text-align: center; margin-top: var(--space-4); line-height: 1.5; }

/* Ocultação completa da sidebar e de seus controles na tela de login */
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
div[data-testid="stSidebarCollapseButton"],
button[data-testid="baseButton-headerNoPadding"],
.stSidebar {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    visibility: hidden !important;
}

[data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
    padding-left: 0 !important;
}

[data-testid="stAppViewBlockContainer"],
.block-container {
    max-width: 100% !important;
    padding-top: 2vh !important;
    padding-bottom: 4vh !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin: 0 auto !important;
}
"""


def _st():
    import streamlit as st   # importado aqui para os testes e o gerador não dependerem do Streamlit
    return st


def aplicar_estilos() -> None:
    """Injeta as variáveis dos tokens e os estilos comuns. Chamar uma vez por execução, antes de desenhar a tela."""
    _st().html(f"<style>{CSS}</style>")


def configurar_pagina(setor: str, **extras) -> None:
    """st.set_page_config com o título padrão ("Controle da Qualidade · AMATECH") e o símbolo na aba."""
    _st().set_page_config(page_title=f"{SETORES[setor]} · AMATECH", page_icon=str(SIMBOLO), **extras)


def cabecalho(setor: str, itens: list[tuple[str, str]] | None = None) -> None:
    """Barra do topo: marca, código e nome do sistema e, à direita, pares (rótulo, valor) como turno e usuário."""
    direita = "".join(f'<div class="am-cab-item"><small>{esc(r)}</small><b>{v}</b></div>' for r, v in (itens or []))
    _st().html(
        f"""<header class="am-cab">
              <div class="am-cab-marca"><img src="{simbolo_data_uri()}" alt=""><b>AMATECH</b></div>
              <div class="am-cab-sep"></div>
              <div class="am-cab-sistema"><span class="am-setor">{esc(setor)}</span><span>{esc(SETORES[setor])}</span></div>
              <div class="am-cab-info">{direita}</div>
            </header>""")


def titulo(texto: str, subtitulo: str = "", breadcrumb: str = "") -> None:
    """Título da tela (estilo titulo-tela) com uma linha de explicação e breadcrumb opcional."""
    crumbs = f'<div class="am-breadcrumb">{esc(breadcrumb)}</div>' if breadcrumb else ""
    sub = f"<p>{esc(subtitulo)}</p>" if subtitulo else ""
    _st().html(f'<div class="am-titulo">{crumbs}<h1>{esc(texto)}</h1>{sub}</div>')


def badge_setor(sigla: str) -> str:
    """Badge de setor com alto contraste e fundo suave para superfícies claras (WCAG AA)."""
    s = str(sigla or "").strip().lower()
    return f'<span class="am-badge-setor {esc(s)}">{esc(sigla)}</span>'



def tela_login(setor: str) -> None:
    """Fundo noite e marca centralizada acima do formulário de login, que cada sistema desenha em seguida."""
    _st().html(
        f"""<style>{CSS_LOGIN}</style>
            <div class="am-login-marca"><img src="{simbolo_data_uri()}" alt=""><b>AMATECH</b>
              <span class="am-setor">{esc(setor)}</span><span class="nome">{esc(SETORES[setor])}</span></div>""")


def nota_login(texto: str) -> None:
    conteudo = texto if ("<" in texto and ">" in texto) else esc(texto)
    _st().html(f'<div class="am-login-nota">{conteudo}</div>')


def usuario_no_menu(nome: str, perfil: str, matricula: str = "") -> None:
    """Nome, perfil e matrícula no fim do menu lateral."""
    codigo = f' · <span class="am-codigo">{esc(matricula)}</span>' if matricula else ""
    _st().sidebar.html(f'<div class="am-menu-usuario"><b>{esc(nome)}</b><small>{esc(perfil)}{codigo}</small></div>')


def etiqueta(texto: str, tom_etiqueta: str | None = None) -> str:
    """HTML de uma etiqueta de estado. Sem tom, ele é deduzido do texto (Aprovado → ok, Parada → critico...)."""
    return f'<span class="am-etq {tom_etiqueta or tom(texto)}">{esc(texto)}</span>'


def cartao_html(rotulo: str, valor: str, detalhe: str = "", estado: str | None = None, unidade: str = "") -> str:
    """Cartão de indicador. `estado` (ok, atencao, critico) põe a etiqueta do semáforo; sem limite, sem etiqueta."""
    selo = etiqueta(ROTULO_SEMAFORO[estado], estado) if estado in ROTULO_SEMAFORO else ""
    medida = f" <small>{esc(unidade)}</small>" if unidade else ""
    return (f'<div class="am-kpi"><div class="am-kpi-topo"><span class="am-kpi-rotulo">{esc(rotulo)}</span>{selo}</div>'
            f'<div class="am-kpi-valor">{esc(valor)}{medida}</div><div class="am-kpi-detalhe">{esc(detalhe)}</div></div>')


def cartao(rotulo: str, valor: str, detalhe: str = "", estado: str | None = None, unidade: str = "") -> None:
    _st().html(cartao_html(rotulo, valor, detalhe, estado, unidade))


# ---------------------------------------------------------------- gráficos
SERIES = [CORES["grafico-1"], CORES["grafico-2"], CORES["grafico-3"], CORES["grafico-4"]]


def estilo_matplotlib() -> None:
    """Tema dos gráficos em Matplotlib: fundo claro, grade em `linha`, textos em `tinta-2` e as cores de série."""
    import matplotlib as mpl
    from cycler import cycler
    mpl.rcParams.update({
        "figure.facecolor": CORES["superficie"], "axes.facecolor": CORES["superficie"],
        "axes.edgecolor": CORES["linha"], "axes.labelcolor": CORES["tinta-2"], "axes.titlecolor": CORES["tinta"],
        "axes.prop_cycle": cycler(color=SERIES), "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": CORES["linha"], "grid.linewidth": 0.8,
        "xtick.color": CORES["tinta-2"], "ytick.color": CORES["tinta-2"], "text.color": CORES["tinta"],
        "font.family": "sans-serif", "font.sans-serif": ["IBM Plex Sans", "Segoe UI", "DejaVu Sans"],
        "font.size": 10,
    })
