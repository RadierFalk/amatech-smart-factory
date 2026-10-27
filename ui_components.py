"""
Componentes visuais padronizados e Design System Corporativo AMATECH.
Implementa os tokens de cores (#1F3A5F, #2E75B6, #F4F6F9) e badges semânticos (docs/04_UI_UX_DESIGN_SYSTEM.md).
"""
from typing import Any
import streamlit as st

from config import COLORS, STATUS_CHAMADO_LABELS, STATUS_EQUIPAMENTO_LABELS


def aplicar_estilos_amatech() -> None:
    """Injeta o CSS industrial corporativo da AMATECH Electronics no Streamlit."""
    st.markdown(
        f"""
        <style>
        /* Fundo geral industrial limpo */
        .stApp {{
            background-color: {COLORS['background']};
            color: {COLORS['text_primary']};
        }}

        /* Barra Lateral Institucional (#1F3A5F) */
        section[data-testid="stSidebar"] {{
            background-color: {COLORS['primary']} !important;
            border-right: 3px solid {COLORS['secondary']};
        }}
        section[data-testid="stSidebar"] * {{
            color: #FFFFFF !important;
        }}
        section[data-testid="stSidebar"] .stRadio label {{
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 4px;
            transition: background 0.2s;
            font-weight: 500;
        }}
        section[data-testid="stSidebar"] .stRadio label:hover {{
            background-color: rgba(46, 117, 182, 0.35);
        }}
        section[data-testid="stSidebar"] button {{
            background-color: {COLORS['secondary']} !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] button:hover {{
            background-color: #235d93 !important;
            border-color: #FFFFFF !important;
        }}

        /* Cabeçalho Superior de Página */
        .amatech-header {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
            color: #FFFFFF;
            padding: 18px 24px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(31, 58, 95, 0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .amatech-header h1 {{
            color: #FFFFFF !important;
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .amatech-header p {{
            color: #E2E8F0 !important;
            font-size: 0.92rem !important;
            margin: 4px 0 0 0 !important;
        }}

        /* Cards de KPI no Topo */
        .kpi-card {{
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 16px 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            border-left: 5px solid {COLORS['secondary']};
            margin-bottom: 12px;
        }}
        .kpi-card .kpi-label {{
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748B;
            margin-bottom: 4px;
        }}
        .kpi-card .kpi-value {{
            font-size: 1.75rem;
            font-weight: 800;
            color: {COLORS['primary']};
            line-height: 1.2;
        }}
        .kpi-card .kpi-sub {{
            font-size: 0.78rem;
            color: #64748B;
            margin-top: 4px;
        }}

        /* Cards de Máquinas (Painel Sinótico) */
        .machine-card {{
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 12px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.07);
            border-top: 6px solid #CCCCCC;
            transition: transform 0.15s ease;
        }}
        .machine-card:hover {{
            transform: translateY(-2px);
        }}
        .machine-tag {{
            font-size: 1.25rem;
            font-weight: 800;
            color: {COLORS['primary']};
            letter-spacing: 0.5px;
        }}
        .machine-name {{
            font-size: 0.96rem;
            font-weight: 600;
            color: #334155;
            margin-top: 2px;
            margin-bottom: 8px;
            min-height: 2.4em;
        }}
        .machine-meta {{
            font-size: 0.82rem;
            color: #64748B;
            margin-bottom: 12px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            color: #FFFFFF;
            font-weight: 700;
            font-size: 0.82rem;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            text-align: center;
            width: 100%;
            box-sizing: border-box;
            margin-bottom: 10px;
        }}
        .priority-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            color: #FFFFFF;
            font-weight: 700;
            font-size: 0.75rem;
            text-transform: uppercase;
        }}

        /* Cronômetro Industrial da OS */
        .timer-box {{
            background: linear-gradient(135deg, #1F3A5F 0%, #0F233C 100%);
            color: #FFFFFF;
            border-radius: 12px;
            padding: 18px 24px;
            text-align: center;
            border: 2px solid #F2B705;
            box-shadow: 0 4px 14px rgba(0,0,0,0.12);
            margin-bottom: 16px;
        }}
        .timer-value {{
            font-family: 'Courier New', monospace;
            font-size: 2.3rem;
            font-weight: 800;
            color: #F2B705;
            letter-spacing: 2px;
        }}
        .timer-label {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #CBD5E1;
        }}

        /* Botões Primários no Corpo da Aplicação */
        div.stButton > button[kind="primary"] {{
            background-color: {COLORS['secondary']} !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: {COLORS['primary']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def renderizar_cabecalho(titulo: str, subtitulo: str, badge_extra: str = "") -> None:
    """Renderiza o cabeçalho institucional AMATECH no topo de cada tela."""
    extra_html = (
        f'<div style="background: rgba(255,255,255,0.18); padding: 6px 14px; '
        f'border-radius: 20px; font-size: 0.82rem; font-weight: 600;">{badge_extra}</div>'
        if badge_extra
        else ""
    )
    st.markdown(
        f"""
        <div class="amatech-header">
            <div>
                <h1>{titulo}</h1>
                <p>{subtitulo}</p>
            </div>
            {extra_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_kpi_card(
    label: str,
    valor: str,
    subtexto: str = "",
    cor_borda: str | None = None,
) -> None:
    """Renderiza um card estilizado de KPI industrial."""
    borda = cor_borda or COLORS["secondary"]
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: {borda};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color: {borda};">{valor}</div>
            <div class="kpi-sub">{subtexto}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_status_equipamento_html(status: str) -> str:
    """Retorna HTML de badge colorido para status operacional (OPERACIONAL, EM_MANUTENCAO, PARADA)."""
    cor = COLORS.get(status, "#6C757D")
    label = STATUS_EQUIPAMENTO_LABELS.get(status, status)
    icone = "🟢" if status == "OPERACIONAL" else ("🟡" if status == "EM_MANUTENCAO" else "🔴")
    return f'<div class="status-badge" style="background-color: {cor};">{icone} {label}</div>'


def badge_prioridade_html(prioridade: str) -> str:
    """Retorna HTML de badge colorido para prioridade do chamado."""
    cor = COLORS.get(prioridade, "#6C757D")
    return f'<span class="priority-badge" style="background-color: {cor};">{prioridade}</span>'


def formatar_duracao_hm(minutos: int | float | None) -> str:
    """Formata minutos em texto legível (ex: 1h 15min ou 45 min)."""
    if minutos is None:
        return "0 min"
    total_min = int(round(float(minutos)))
    if total_min < 60:
        return f"{total_min} min"
    horas = total_min // 60
    resto = total_min % 60
    if resto == 0:
        return f"{horas}h"
    return f"{horas}h {resto:02d}min"


def formatar_relogio_hms(segundos: int | None) -> str:
    """Formata segundos como HH:MM:SS para o cronômetro em tempo real."""
    seg = max(0, int(segundos or 0))
    horas = seg // 3600
    minutos = (seg % 3600) // 60
    s = seg % 60
    return f"{horas:02d}:{minutos:02d}:{s:02d}"


def navegar_para(codigo_pagina: str, **estado_extra: Any) -> None:
    """Altera a página ativa na sessão e dispara rerun imediato."""
    for chave, valor in estado_extra.items():
        st.session_state[chave] = valor
    st.session_state["pagina_atual"] = codigo_pagina
    st.rerun()
