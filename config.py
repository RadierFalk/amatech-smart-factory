"""
Configurações globais, caminhos de arquivos e constantes do Design System AMATECH.
Projeto 5: Sistema de Controle da Manutenção (management-control)
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "manutencao.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "docs", "02_DATABASE_SCHEMA.sql")

API_HOST = "0.0.0.0"
API_PORT = int(os.environ.get("MANUTENCAO_API_PORT", "5002"))

# Design Tokens Oficiais AMATECH (docs/04_UI_UX_DESIGN_SYSTEM.md)
COLORS = {
    "primary": "#1F3A5F",          # Azul Institucional Primário
    "secondary": "#2E75B6",        # Azul Secundário de Destaque
    "background": "#F4F6F9",       # Cinza de Fundo Industrial
    "text_primary": "#2C3E50",     # Texto Principal
    "text_secondary": "#333333",   # Texto Secundário
    "white": "#FFFFFF",
    # Cores Semânticas de Estado Operacional (RNF04)
    "OPERACIONAL": "#2E9E4F",      # Verde escuro / Positivo
    "EM_MANUTENCAO": "#F2B705",    # Amarelo âmbar / Atenção
    "PARADA": "#D32F2F",           # Vermelho industrial / Alerta crítico
    # Cores de Prioridade de Chamados
    "BAIXA": "#6C757D",            # Cinza neutro
    "MEDIA": "#0288D1",            # Azul informativo
    "ALTA": "#F57C00",             # Laranja
    "CRITICA": "#C62828",          # Vermelho pulsante
}

STATUS_EQUIPAMENTO_LABELS = {
    "OPERACIONAL": "OPERACIONAL",
    "EM_MANUTENCAO": "EM MANUTENÇÃO",
    "PARADA": "MÁQUINA PARADA",
}

STATUS_CHAMADO_LABELS = {
    "ABERTO": "Aberto (Fila)",
    "EM_ANDAMENTO": "Em Atendimento",
    "CONCLUIDO": "Concluído",
    "CANCELADO": "Cancelado",
}

PRIORIDADES = ["BAIXA", "MEDIA", "ALTA", "CRITICA"]
TIPOS_MANUTENCAO = ["CORRETIVA", "PREVENTIVA"]
PERFIS_USUARIO = ["OPERADOR", "TECNICO", "GESTOR"]

SETORES_PADRAO = [
    "SMT",
    "Testes Funcionais",
    "Montagem Final",
    "Embalagem",
]

CAUSAS_RAIZ_PADRAO = [
    "Desgaste mecânico / Fadiga de componente",
    "Falha elétrica em resistor de potência",
    "Falha elétrica / Curto-circuito / Sensor",
    "Descalibração / Erro de parâmetro de processo",
    "Falha pneumática / Perda de pressão ou vácuo",
    "Falta de lubrificação / Sujeira acumulada",
    "Fadiga térmica / Superaquecimento",
    "Erro operacional / Setup incorreto",
    "Manutenção preventiva programada",
    "Outra causa (especificada no diagnóstico)",
]

# Tempo programado padrão por máquina para cálculo de disponibilidade (1 turno = 600 min)
TEMPO_PROGRAMADO_POR_MAQUINA_MIN = 600
