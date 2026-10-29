"""
Configurações globais, caminhos de arquivos e constantes do Design System AMATECH.
Projeto 5: Sistema de Controle da Manutenção (management-control)
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("MANUTENCAO_DB", os.path.join(BASE_DIR, "manutencao.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "docs", "02_DATABASE_SCHEMA.sql")

API_HOST = "0.0.0.0"
API_PORT = int(os.environ.get("MANUTENCAO_API_PORT", "5002"))

# Integração com o ecossistema (OA3): chave que os outros sistemas enviam no cabeçalho X-API-Key para abrir
# chamados pela API, e o usuário de serviço que fica como "operador de abertura" desses chamados.
API_KEY_INTEGRACAO = os.environ.get("MANUTENCAO_API_KEY", "amatech-manutencao-demo")
MATRICULA_INTEGRACAO = "SVC-INTEGRACAO"

# Paleta Oficial AMATECH (replicada do projeto de referência amatech-manutencao)
COLORS = {
    "navy": "#1F3A5F",
    "navy_dark": "#16293F",
    "primary": "#1F3A5F",
    "secondary": "#2E75B6",
    "azul": "#2E75B6",
    "azul_claro": "#E8F1FA",
    "verde": "#2E9E4F",
    "vermelho": "#D32F2F",
    "amarelo": "#F2B705",
    "roxo": "#6B3F8A",
    "cinza_900": "#1C2530",
    "cinza_700": "#495665",
    "cinza_500": "#7B8794",
    "cinza_300": "#CCD5DE",
    "cinza_200": "#E4EAF0",
    "cinza_100": "#F4F7FA",
    "background": "#F4F7FA",
    "text_primary": "#1C2530",
    "text_secondary": "#495665",
    "white": "#FFFFFF",
    # Cores Semânticas de Estado Operacional (RNF04)
    "OPERACIONAL": "#2E9E4F",
    "EM_MANUTENCAO": "#F2B705",
    "PARADA": "#D32F2F",
    # Cores de Prioridade de Chamados
    "BAIXA": "#7B8794",
    "MEDIA": "#2E75B6",
    "ALTA": "#F2B705",
    "CRITICA": "#D32F2F",
}

STATUS_EQUIPAMENTO_LABELS = {
    "OPERACIONAL": "Funcionando",
    "EM_MANUTENCAO": "Em manutenção",
    "PARADA": "Indisponível",
}

STATUS_CHAMADO_LABELS = {
    "ABERTO": "Aberto",
    "EM_ANDAMENTO": "Em andamento",
    "CONCLUIDO": "Concluído",
    "CANCELADO": "Cancelado",
}

PRIORIDADES = ["BAIXA", "MEDIA", "ALTA", "CRITICA"]
TIPOS_MANUTENCAO = ["CORRETIVA", "PREVENTIVA"]
PERFIS_USUARIO = ["OPERADOR", "TECNICO", "GESTOR"]

# Mapeamento das Estações do Processo Produtivo (ordem_fluxo, código, nome, descrição)
ESTACOES_FLUXO = {
    "Recebimento de Materiais": (1, "REC", "Conferência e recebimento de componentes, telas, baterias e embalagens."),
    "Almoxarifado": (2, "ALM", "Armazenamento, controle e separação de materiais para a produção."),
    "SMT": (3, "SMT", "Montagem automatizada de componentes eletrônicos na placa."),
    "Linha SMT": (3, "SMT", "Montagem automatizada de componentes eletrônicos na placa."),
    "Inserção Manual": (4, "INS", "Componentes que exigem colocação ou ajuste manual."),
    "Montagem Final": (5, "MON", "Integração dos módulos do notebook (placa, tela, teclado, bateria)."),
    "Instalação de Software": (6, "SW", "Gravação do sistema operacional, drivers e programas."),
    "Testes Funcionais": (7, "TST", "Testes de inicialização, tela, teclado, portas, Wi-Fi, câmera e bateria."),
    "Inspeção da Qualidade": (8, "INSQ", "Verificação funcional, visual e documental do produto."),
    "Embalagem": (9, "EMB", "Inclusão do produto, acessórios, manuais e etiquetas."),
    "Expedição": (10, "EXP", "Organização e envio dos produtos acabados."),
}

SETORES_PADRAO = [
    "SMT",
    "Inserção Manual",
    "Montagem Final",
    "Instalação de Software",
    "Testes Funcionais",
    "Inspeção da Qualidade",
    "Embalagem",
    "Almoxarifado",
    "Expedição",
]

CAUSAS_RAIZ_PADRAO = [
    "Desgaste natural do componente",
    "Desgaste mecânico / Fadiga de componente",
    "Falta de lubrificação",
    "Componente eletrônico queimado",
    "Falha elétrica em resistor de potência",
    "Falha de sensor / calibração",
    "Sobreaquecimento",
    "Erro de operação",
    "Falta de manutenção preventiva",
    "Falha de energia elétrica",
    "Desalinhamento mecânico",
    "Software / firmware desatualizado",
    "Programa de manutenção preventiva",
]

# Tempo programado padrão por máquina para cálculo de disponibilidade (1 turno = 600 min)
TEMPO_PROGRAMADO_POR_MAQUINA_MIN = 600
