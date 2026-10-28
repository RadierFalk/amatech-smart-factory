"""
Design System e Componentes Visuais do Sistema de Controle da Manutenção AMATECH.
Replica fielmente o design, fontes, selos, topbar, cards, tabelas e botões do projeto amatech-manutencao.
"""
from datetime import datetime
from typing import Any
import html
import streamlit as st

from config import COLORS, STATUS_CHAMADO_LABELS, STATUS_EQUIPAMENTO_LABELS


def esc(valor: Any) -> str:
    """Escapa texto para inserção segura em blocos HTML."""
    if valor is None:
        return ""
    return html.escape(str(valor))


def rotulo_amigavel(valor: str | None) -> str:
    """Formata códigos de status/prioridade/tipo com a mesma capitalização do projeto de referência."""
    if not valor:
        return "—"
    mapa = {
        "OPERACIONAL": "Funcionando",
        "FUNCIONANDO": "Funcionando",
        "EM_MANUTENCAO": "Em manutenção",
        "PARADA": "Indisponível",
        "INDISPONIVEL": "Indisponível",
        "ABERTO": "Aberto",
        "EM_ANDAMENTO": "Em andamento",
        "CONCLUIDO": "Concluído",
        "CANCELADO": "Cancelado",
        "BAIXA": "Baixa",
        "MEDIA": "Média",
        "ALTA": "Alta",
        "CRITICA": "Crítica",
        "CORRETIVA": "Corretiva",
        "PREVENTIVA": "Preventiva",
        "OPERADOR": "Operador",
        "TECNICO": "Técnico",
        "GESTOR": "Gestor",
    }
    return mapa.get(str(valor).upper(), str(valor).replace("_", " ").capitalize())


def aplicar_estilos_amatech() -> None:
    """Injeta a folha de estilos completa replicada de amatech-manutencao/web/css/styles.css."""
    st.markdown(
        """
        <style>
        :root {
          --navy: #1f3a5f;
          --navy-dark: #16293f;
          --azul: #2e75b6;
          --azul-claro: #e8f1fa;
          --verde: #2e9e4f;
          --vermelho: #d32f2f;
          --amarelo: #f2b705;
          --roxo: #6b3f8a;
          --cinza-900: #1c2530;
          --cinza-700: #495665;
          --cinza-500: #7b8794;
          --cinza-300: #ccd5de;
          --cinza-200: #e4eaf0;
          --cinza-100: #f4f7fa;
          --branco: #ffffff;
          --sombra: 0 1px 2px rgba(16, 32, 51, 0.06), 0 4px 14px rgba(16, 32, 51, 0.06);
          --sombra-alta: 0 12px 32px rgba(16, 32, 51, 0.16);
          --raio: 10px;
          --raio-sm: 6px;
        }

        /* Tipografia e Fundo Global */
        html, body, .stApp {
          font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
          background-color: var(--cinza-100) !important;
          color: var(--cinza-900) !important;
          font-size: 14px !important;
          -webkit-font-smoothing: antialiased;
        }

        /* Remove espaçamento excessivo padrão do Streamlit */
        .block-container {
          padding-top: 0.8rem !important;
          padding-bottom: 2.5rem !important;
          padding-left: 1.6rem !important;
          padding-right: 1.6rem !important;
          max-width: 1520px !important;
        }
        header[data-testid="stHeader"] {
          background: transparent !important;
          height: 1.5rem !important;
        }

        /* ---------------- Sidebar (#16293f --navy-dark) ---------------- */
        section[data-testid="stSidebar"] {
          background-color: var(--navy-dark) !important;
          border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
          width: 252px !important;
        }
        section[data-testid="stSidebar"] > div {
          padding-top: 0.5rem !important;
        }
        section[data-testid="stSidebar"] * {
          font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        }

        .sb-marca {
          padding: 12px 10px 16px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          margin-bottom: 10px;
        }
        .sb-logo-linha {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .sb-logo-simbolo {
          width: 34px;
          height: 34px;
          border-radius: 8px;
          background: linear-gradient(135deg, var(--azul), #4a9de0);
          display: grid;
          place-items: center;
          color: #ffffff !important;
          font-weight: 800;
          font-size: 15px;
          letter-spacing: -0.5px;
          flex-shrink: 0;
        }
        .sb-logo-txt strong {
          display: block;
          color: #ffffff !important;
          font-size: 14px;
          letter-spacing: 0.2px;
          line-height: 1.2;
        }
        .sb-logo-txt span {
          font-size: 10.5px;
          color: #8fa5bd !important;
          text-transform: uppercase;
          letter-spacing: 0.8px;
        }
        .sb-nav-grupo {
          font-size: 10.5px;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #6f88a3 !important;
          margin: 14px 6px 6px;
          font-weight: 700;
        }
        .sb-rodape {
          padding: 12px 8px 8px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          font-size: 11.5px;
          color: #7b91a9 !important;
          margin-top: 12px;
        }
        .sb-rodape strong {
          color: #c9d6e4 !important;
          display: block;
          font-size: 12.5px;
          margin-bottom: 2px;
        }

        /* Botões de navegação na Sidebar */
        section[data-testid="stSidebar"] div.stButton > button {
          width: 100%;
          justify-content: flex-start !important;
          text-align: left !important;
          padding: 8px 12px !important;
          border-radius: 6px !important;
          font-size: 13.5px !important;
          font-weight: 500 !important;
          border: none !important;
          border-left: 3px solid transparent !important;
          background: transparent !important;
          color: #c9d6e4 !important;
          margin-bottom: 1px !important;
          box-shadow: none !important;
          min-height: 36px !important;
        }
        section[data-testid="stSidebar"] div.stButton > button:hover {
          background: rgba(255, 255, 255, 0.06) !important;
          color: #ffffff !important;
        }
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
          background: rgba(46, 117, 182, 0.28) !important;
          color: #ffffff !important;
          border-left: 3px solid var(--azul) !important;
          font-weight: 600 !important;
        }

        /* ---------------- Topbar (.topbar) ---------------- */
        .topbar {
          min-height: 62px;
          background: var(--branco);
          border: 1px solid var(--cinza-200);
          border-radius: var(--raio);
          box-shadow: var(--sombra);
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 10px 22px;
          margin-bottom: 18px;
        }
        .topbar h1 {
          font-size: 17px !important;
          margin: 0 !important;
          padding: 0 !important;
          color: var(--navy) !important;
          font-weight: 650 !important;
          letter-spacing: -0.2px !important;
          line-height: 1.25 !important;
        }
        .topbar .sub {
          font-size: 12px;
          color: var(--cinza-500);
          margin-top: 2px;
        }
        .topbar-direita {
          margin-left: auto;
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .relogio {
          font-variant-numeric: tabular-nums;
          color: var(--cinza-700);
          font-size: 13px;
        }
        .usuario-chip {
          display: flex;
          align-items: center;
          gap: 9px;
          padding-left: 14px;
          border-left: 1px solid var(--cinza-200);
        }
        .avatar {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          background: var(--azul-claro);
          color: var(--navy);
          display: grid;
          place-items: center;
          font-weight: 700;
          font-size: 12.5px;
        }
        .usuario-chip .nome {
          font-size: 13px;
          font-weight: 600;
          line-height: 1.2;
          color: var(--cinza-900);
        }
        .usuario-chip .perfil {
          font-size: 11px;
          color: var(--cinza-500);
        }

        /* ---------------- KPIs (.kpi) ---------------- */
        .kpi {
          background: var(--branco);
          border: 1px solid var(--cinza-200);
          border-radius: var(--raio);
          padding: 15px 16px;
          box-shadow: var(--sombra);
          position: relative;
          overflow: hidden;
          margin-bottom: 10px;
          min-height: 98px;
        }
        .kpi::before {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 3px;
          background: var(--azul);
        }
        .kpi.verde::before { background: var(--verde); }
        .kpi.vermelho::before { background: var(--vermelho); }
        .kpi.amarelo::before { background: var(--amarelo); }
        .kpi.azul::before { background: var(--azul); }
        .kpi .rotulo {
          font-size: 11.5px;
          text-transform: uppercase;
          letter-spacing: 0.6px;
          color: var(--cinza-500);
          font-weight: 600;
        }
        .kpi .valor {
          font-size: 26px;
          font-weight: 700;
          color: var(--navy);
          margin: 6px 0 2px;
          letter-spacing: -0.6px;
          font-variant-numeric: tabular-nums;
          line-height: 1.15;
        }
        .kpi .valor small {
          font-size: 13px;
          font-weight: 600;
          color: var(--cinza-500);
          margin-left: 3px;
        }
        .kpi .detalhe {
          font-size: 12px;
          color: var(--cinza-500);
        }

        /* ---------------- Cards (.card) ---------------- */
        .card {
          background: var(--branco);
          border: 1px solid var(--cinza-200);
          border-radius: var(--raio);
          box-shadow: var(--sombra);
          margin-bottom: 16px;
          overflow: hidden;
        }
        .card-cabecalho {
          padding: 13px 18px;
          border-bottom: 1px solid var(--cinza-200);
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
          background: var(--branco);
        }
        .card-cabecalho h2 {
          font-size: 14.5px !important;
          margin: 0 !important;
          padding: 0 !important;
          color: var(--navy) !important;
          font-weight: 650 !important;
        }
        .card-cabecalho .acao {
          margin-left: auto;
          display: flex;
          gap: 8px;
          align-items: center;
          font-size: 12px;
          color: var(--cinza-500);
        }
        .card-corpo {
          padding: 18px;
        }

        /* ---------------- Selos / Badges (.selo) ---------------- */
        .selo {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 2px 8px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.4px;
          white-space: nowrap;
        }
        .selo::before {
          content: "";
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
        }
        .selo-funcionando, .selo-operacional, .selo-concluido {
          background: #eaf7ee;
          color: #1c6b33;
        }
        .selo-em_manutencao, .selo-em_andamento, .selo-alta {
          background: #fff8e1;
          color: #8a6a00;
        }
        .selo-indisponivel, .selo-parada, .selo-aberto, .selo-critica {
          background: #fdecec;
          color: #a01f1f;
        }
        .selo-media {
          background: var(--azul-claro);
          color: #1d4b73;
        }
        .selo-baixa, .selo-cancelado {
          background: #eef1f4;
          color: #495665;
        }
        .selo-preventiva {
          background: #eef4ff;
          color: #2b4c7e;
        }
        .selo-corretiva {
          background: #f6eefb;
          color: #6b3f8a;
        }

        .tag {
          font-family: ui-monospace, "Cascadia Mono", monospace;
          font-size: 11.5px;
          font-weight: 700;
          color: var(--azul);
          background: var(--azul-claro);
          padding: 1px 6px;
          border-radius: 4px;
        }

        /* ---------------- Avisos (.aviso-info) ---------------- */
        .aviso-info {
          display: flex;
          gap: 10px;
          align-items: flex-start;
          background: var(--azul-claro);
          border: 1px solid #c9dff2;
          border-radius: var(--raio-sm);
          padding: 10px 12px;
          font-size: 12.5px;
          color: #1d4b73;
          line-height: 1.5;
          margin-bottom: 14px;
        }
        .aviso-alerta { background: #fff8e1; border-color: #ffe08a; color: #7a5c00; }
        .aviso-erro { background: #fdecec; border-color: #f5bcbc; color: #96201f; }
        .aviso-ok { background: #eaf7ee; border-color: #b7e0c4; color: #1c6b33; }

        /* ---------------- Painel de Máquinas e Grupos de Estação ---------------- */
        .legenda {
          display: flex;
          gap: 16px;
          align-items: center;
          font-size: 12px;
          color: var(--cinza-700);
        }
        .legenda span {
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .legenda i {
          width: 9px;
          height: 9px;
          border-radius: 50%;
          display: inline-block;
        }
        .dot-funcionando { background: var(--verde); }
        .dot-em_manutencao { background: var(--amarelo); }
        .dot-indisponivel { background: var(--vermelho); }

        .grupo-estacao-cabecalho {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 14px 0 10px;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--cinza-200);
        }
        .grupo-estacao-cabecalho h3 {
          margin: 0 !important;
          padding: 0 !important;
          font-size: 14px !important;
          color: var(--navy) !important;
          font-weight: 700 !important;
        }
        .grupo-estacao-cabecalho .etapa {
          background: var(--navy);
          color: #fff;
          font-size: 10.5px;
          font-weight: 700;
          padding: 2px 7px;
          border-radius: 4px;
          letter-spacing: 0.4px;
        }
        .grupo-estacao-cabecalho .contagem {
          font-size: 12px;
          color: var(--cinza-500);
        }
        .grupo-estacao-cabecalho .alerta-estacao {
          margin-left: auto;
          font-size: 11.5px;
          font-weight: 700;
          color: var(--vermelho);
          background: #fdecec;
          padding: 3px 9px;
          border-radius: 20px;
        }

        .maquina-card {
          background: var(--branco);
          border: 1px solid var(--cinza-200);
          border-left: 4px solid var(--verde);
          border-radius: var(--raio);
          padding: 13px 14px;
          box-shadow: var(--sombra);
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 6px;
          min-height: 126px;
        }
        .maquina-card[data-estado="EM_MANUTENCAO"] { border-left-color: var(--amarelo); }
        .maquina-card[data-estado="PARADA"],
        .maquina-card[data-estado="INDISPONIVEL"] { border-left-color: var(--vermelho); }
        .maquina-card.inativa { opacity: 0.62; border-left-style: dashed; }
        .maquina-card .nome {
          font-weight: 650;
          font-size: 13.5px;
          line-height: 1.3;
          color: var(--cinza-900);
        }
        .maquina-card .meta {
          font-size: 11.5px;
          color: var(--cinza-500);
        }
        .maquina-card .os-link {
          font-size: 11.5px;
          color: var(--cinza-700);
          margin-top: auto;
        }

        /* ---------------- Tabelas (.tabela) ---------------- */
        .tabela-wrap { overflow-x: auto; }
        table.tabela {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
          background: var(--branco);
        }
        table.tabela th {
          text-align: left;
          padding: 10px 12px;
          background: var(--cinza-100);
          font-size: 11.5px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--cinza-700);
          border-bottom: 1px solid var(--cinza-200);
          white-space: nowrap;
          font-weight: 700;
        }
        table.tabela td {
          padding: 10px 12px;
          border-bottom: 1px solid var(--cinza-200);
          vertical-align: middle;
          color: var(--cinza-900);
        }
        table.tabela tbody tr:hover { background: #fafcfe; }
        table.tabela tbody tr:last-child td { border-bottom: 0; }
        table.tabela td.num, table.tabela th.num {
          text-align: right;
          font-variant-numeric: tabular-nums;
        }
        table.tabela .mono {
          font-family: ui-monospace, "Cascadia Mono", monospace;
          font-size: 12px;
        }
        table.tabela tbody tr.prioridade-critica td:first-child { box-shadow: inset 3px 0 0 var(--vermelho); }
        table.tabela tbody tr.prioridade-alta td:first-child { box-shadow: inset 3px 0 0 var(--amarelo); }
        table.tabela tbody tr.prioridade-media td:first-child { box-shadow: inset 3px 0 0 var(--azul); }
        table.tabela tbody tr.prioridade-baixa td:first-child { box-shadow: inset 3px 0 0 var(--cinza-300); }

        .vazio {
          padding: 32px 20px;
          text-align: center;
          color: var(--cinza-500);
          font-size: 13px;
        }
        .vazio strong {
          display: block;
          color: var(--cinza-700);
          font-size: 14px;
          margin-bottom: 4px;
        }

        /* ---------------- Contadores (.contador) ---------------- */
        .contadores { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
        .contador {
          background: var(--branco);
          border: 1px solid var(--cinza-200);
          border-radius: var(--raio-sm);
          padding: 8px 16px;
          min-width: 110px;
          box-shadow: var(--sombra);
        }
        .contador .n {
          font-size: 20px;
          font-weight: 700;
          color: var(--navy);
          line-height: 1.1;
        }
        .contador .r {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--cinza-500);
          font-weight: 600;
        }
        .contador.destaque { background: #fdecec; border-color: #f5bcbc; }
        .contador.destaque .n { color: var(--vermelho); }

        /* ---------------- Ordem de Serviço (.os-cronometro, .dados-lista) ---------------- */
        .os-cronometro {
          background: var(--navy);
          color: #fff;
          border-radius: var(--raio);
          padding: 20px 22px;
          display: flex;
          align-items: center;
          gap: 22px;
          box-shadow: var(--sombra);
          height: 100%;
          min-height: 150px;
        }
        .os-cronometro .relogio-os {
          font-family: ui-monospace, "Cascadia Mono", monospace;
          font-size: 34px;
          font-weight: 700;
          letter-spacing: 1px;
          font-variant-numeric: tabular-nums;
          color: #ffffff;
        }
        .os-cronometro .rotulo {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #9db4cd;
          margin-bottom: 2px;
        }
        .os-cronometro .sub {
          font-size: 12px;
          color: #b9cadb;
          margin-top: 4px;
        }
        .os-cronometro .divisor {
          width: 1px;
          align-self: stretch;
          background: rgba(255, 255, 255, 0.16);
        }
        .os-cronometro .mini {
          font-size: 11.5px;
          color: #9db4cd;
          text-transform: uppercase;
          letter-spacing: 0.6px;
        }
        .os-cronometro .mini strong {
          display: block;
          font-size: 17px;
          color: #fff;
          letter-spacing: 0;
          text-transform: none;
          margin-top: 2px;
        }

        .dados-lista { display: grid; gap: 9px; font-size: 13px; }
        .dados-lista .linha {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding-bottom: 8px;
          border-bottom: 1px dashed var(--cinza-200);
        }
        .dados-lista .linha:last-child { border-bottom: 0; padding-bottom: 0; }
        .dados-lista .r { color: var(--cinza-500); font-size: 12.5px; }
        .dados-lista .v { font-weight: 600; text-align: right; color: var(--cinza-900); }

        .peca-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 9px 11px;
          border: 1px solid var(--cinza-200);
          border-radius: var(--raio-sm);
          background: var(--cinza-100);
          margin-bottom: 6px;
        }
        .peca-item .cod {
          font-family: ui-monospace, monospace;
          font-size: 11.5px;
          color: var(--azul);
          font-weight: 700;
        }
        .peca-item .nome { font-size: 12.5px; color: var(--cinza-900); }
        .peca-item .qtd { margin-left: auto; font-weight: 700; font-size: 12.5px; color: var(--navy); }

        /* ---------------- Tela de Login Split (.login-marca) ---------------- */
        .login-marca-panel {
          position: relative;
          overflow: hidden;
          padding: 46px 48px;
          color: #ffffff;
          border-radius: 12px;
          min-height: 540px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          background:
            radial-gradient(circle at 85% 15%, rgba(46, 117, 182, 0.55), transparent 55%),
            radial-gradient(circle at 10% 90%, rgba(46, 158, 79, 0.28), transparent 50%),
            #1f3a5f;
          box-shadow: var(--sombra-alta);
        }
        .login-marca-panel::after {
          content: "";
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
          background-size: 44px 44px;
          pointer-events: none;
        }
        .login-marca-panel > * { position: relative; z-index: 1; }
        .login-marca-panel h1 {
          font-size: 31px !important;
          line-height: 1.15 !important;
          margin: 18px 0 10px !important;
          letter-spacing: -0.4px !important;
          color: #ffffff !important;
          font-weight: 700 !important;
        }
        .login-marca-panel p {
          color: #c8d6e5 !important;
          max-width: 440px;
          line-height: 1.6;
          font-size: 14.5px;
        }
        .login-lista {
          margin: 24px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 14px;
        }
        .login-lista li {
          display: flex;
          gap: 12px;
          align-items: flex-start;
          color: #dbe6f1;
          font-size: 13.8px;
          line-height: 1.45;
        }
        .login-lista .ico-check {
          flex: 0 0 22px;
          width: 22px;
          height: 22px;
          border-radius: 50%;
          background: rgba(46, 158, 79, 0.9);
          display: grid;
          place-items: center;
          font-size: 12px;
          color: #fff;
          font-weight: 700;
          margin-top: 2px;
        }
        .contas-demo-box {
          margin-top: 16px;
          border: 1px dashed var(--cinza-300);
          border-radius: var(--raio-sm);
          padding: 12px 14px;
          background: var(--cinza-100);
        }
        .contas-demo-box strong {
          display: block;
          font-size: 11.5px;
          text-transform: uppercase;
          letter-spacing: 0.6px;
          color: var(--cinza-700);
          margin-bottom: 6px;
        }

        /* ---------------- Botões e Inputs Padrão no Conteúdo Principal ---------------- */
        div[data-testid="stMainBlockContainer"] div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
          background-color: var(--azul) !important;
          color: #ffffff !important;
          border: 1px solid transparent !important;
          border-radius: var(--raio-sm) !important;
          font-size: 13px !important;
          font-weight: 600 !important;
          padding: 7px 14px !important;
          transition: filter 0.15s !important;
        }
        div[data-testid="stMainBlockContainer"] div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
          filter: brightness(1.07) !important;
        }
        div[data-testid="stMainBlockContainer"] div.stButton > button[kind="secondary"],
        div[data-testid="stFormSubmitButton"] > button[kind="secondary"] {
          background-color: var(--branco) !important;
          color: var(--navy) !important;
          border: 1px solid var(--cinza-300) !important;
          border-radius: var(--raio-sm) !important;
          font-size: 13px !important;
          font-weight: 600 !important;
        }
        div[data-testid="stMainBlockContainer"] div.stButton > button[kind="secondary"]:hover {
          background-color: var(--cinza-100) !important;
          border-color: var(--azul) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def renderizar_topbar(titulo: str, subtitulo: str = "") -> None:
    """Renderiza a barra superior (.topbar) idêntica à do projeto amatech-manutencao."""
    usuario = st.session_state.get("usuario_logado") or {
        "nome": "Visitante",
        "perfil": "OPERADOR",
        "matricula": "",
    }
    partes_nome = [p for p in str(usuario.get("nome", "U")).split(" ") if p]
    iniciais = "".join(p[0] for p in partes_nome[:2]).upper() or "AM"
    perfil_fmt = rotulo_amigavel(usuario.get("perfil"))

    dias_semana = ["seg.", "ter.", "qua.", "qui.", "sex.", "sáb.", "dom."]
    agora = datetime.now()
    relogio_str = f"{dias_semana[agora.weekday()]}, {agora.strftime('%d/%m, %H:%M')}"

    st.markdown(
        f"""
        <header class="topbar">
          <div>
            <h1>{esc(titulo)}</h1>
            <div class="sub">{esc(subtitulo)}</div>
          </div>
          <div class="topbar-direita">
            <span class="relogio">{esc(relogio_str)}</span>
            <div class="usuario-chip">
              <div class="avatar">{esc(iniciais)}</div>
              <div>
                <div class="nome">{esc(usuario.get('nome'))}</div>
                <div class="perfil">{esc(perfil_fmt)}</div>
              </div>
            </div>
          </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def renderizar_cabecalho(titulo: str, subtitulo: str = "", badge_extra: str = "") -> None:
    """Alias compatível que renderiza a topbar padronizada do sistema."""
    sub = f"{subtitulo} · {badge_extra}" if badge_extra and subtitulo else (subtitulo or badge_extra)
    renderizar_topbar(titulo, sub)


def kpi_html(
    rotulo: str,
    valor: str,
    unidade: str = "",
    detalhe: str = "",
    variante: str = "azul",
) -> str:
    """Gera o bloco HTML de um card .kpi (variantes: verde, amarelo, vermelho, azul)."""
    small_html = f"<small>{esc(unidade)}</small>" if unidade else ""
    return f"""
    <div class="kpi {esc(variante)}">
      <div class="rotulo">{esc(rotulo)}</div>
      <div class="valor">{esc(valor)}{small_html}</div>
      <div class="detalhe">{esc(detalhe)}</div>
    </div>
    """


def renderizar_kpi_card(
    label: str,
    valor: str,
    subtexto: str = "",
    cor_borda: str | None = None,
    unidade: str = "",
) -> None:
    """Renderiza um card .kpi estilizado com barra lateral de 3px."""
    mapa_var = {
        COLORS["verde"]: "verde",
        COLORS["OPERACIONAL"]: "verde",
        COLORS["amarelo"]: "amarelo",
        COLORS["EM_MANUTENCAO"]: "amarelo",
        COLORS["vermelho"]: "vermelho",
        COLORS["PARADA"]: "vermelho",
    }
    variante = mapa_var.get(cor_borda or "", "azul")
    st.markdown(kpi_html(label, valor, unidade=unidade, detalhe=subtexto, variante=variante), unsafe_allow_html=True)


def selo_html(valor: str | None) -> str:
    """Retorna um badge .selo com ponto colorido conforme o estado/status/prioridade/tipo."""
    if not valor:
        return '<span class="selo selo-baixa">—</span>'
    chave = str(valor).upper()
    mapa_classe = {
        "OPERACIONAL": "selo-funcionando",
        "FUNCIONANDO": "selo-funcionando",
        "EM_MANUTENCAO": "selo-em_manutencao",
        "PARADA": "selo-indisponivel",
        "INDISPONIVEL": "selo-indisponivel",
        "ABERTO": "selo-aberto",
        "EM_ANDAMENTO": "selo-em_andamento",
        "CONCLUIDO": "selo-concluido",
        "CANCELADO": "selo-cancelado",
        "BAIXA": "selo-baixa",
        "MEDIA": "selo-media",
        "ALTA": "selo-alta",
        "CRITICA": "selo-critica",
        "PREVENTIVA": "selo-preventiva",
        "CORRETIVA": "selo-corretiva",
        "GESTOR": "selo-media",
        "TECNICO": "selo-alta",
        "OPERADOR": "selo-baixa",
    }
    classe = mapa_classe.get(chave, "selo-baixa")
    return f'<span class="selo {classe}">{esc(rotulo_amigavel(chave))}</span>'


def badge_status_equipamento_html(status: str) -> str:
    """Compatibilidade para exibição de selo de status operacional."""
    return selo_html(status)


def badge_prioridade_html(prioridade: str) -> str:
    """Compatibilidade para exibição de selo de prioridade."""
    return selo_html(prioridade)


def formatar_data_br(iso_str: str | None, com_hora: bool = True) -> str:
    """Formata string ISO/SQLite em DD/MM/AAAA HH:MM."""
    if not iso_str:
        return "—"
    try:
        limpo = str(iso_str).replace("T", " ").split(".")[0]
        dt = datetime.strptime(limpo, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M") if com_hora else dt.strftime("%d/%m/%Y")
    except Exception:
        return str(iso_str)


def formatar_duracao_hm(minutos: int | float | None) -> str:
    """Formata minutos no padrão 'X h Y min' ou 'X min' do projeto de referência."""
    if minutos is None:
        return "0 min"
    m = max(0, int(round(float(minutos))))
    if m < 60:
        return f"{m} min"
    h = m // 60
    resto = m % 60
    return f"{h} h {resto} min" if resto else f"{h} h"


def formatar_duracao_curta(minutos: int | float | None) -> str:
    """Formata minutos no padrão curto '1h25' ou '35m'."""
    if minutos is None:
        return "0m"
    m = max(0, int(round(float(minutos))))
    if m < 60:
        return f"{m}m"
    h = m // 60
    resto = m % 60
    return f"{h}h{resto:02d}" if resto else f"{h}h"


def formatar_relogio_hms(segundos: int | None) -> str:
    """Formata segundos como HH:MM:SS para o cronômetro da OS."""
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
