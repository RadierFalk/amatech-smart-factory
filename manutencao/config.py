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

# Integração com o ecossistema (OA3): chave opcional para validação externa (se omitida na rede interna, liberada).
API_KEY_INTEGRACAO = os.environ.get("MANUTENCAO_API_KEY", "amatech-manutencao-demo")
EXIGIR_CHAVE = os.environ.get("MANUTENCAO_EXIGIR_CHAVE", "0") == "1"
# Origens (sites) autorizadas a chamar a API pelo navegador, separadas por vírgula. Vazio = nenhuma (padrão).
API_CORS_ORIGENS = [o.strip() for o in os.environ.get("MANUTENCAO_CORS", "").split(",") if o.strip()]
MATRICULA_INTEGRACAO = "SVC-INTEGRACAO"

# Paleta Oficial AMATECH (replicada do projeto de referência amatech-manutencao)
COLORS = {
    "navy": "#0D1B2A",
    "navy_dark": "#0D1B2A",
    "primary": "#0D1B2A",
    "secondary": "#1F5FD6",
    "azul": "#1F5FD6",
    "azul_claro": "#E6EEFC",
    "verde": "#1B7A43",
    "vermelho": "#B3261E",
    "amarelo": "#F2B21B",
    "roxo": "#6A4BC4",
    "cinza_900": "#142133",
    "cinza_700": "#4d5b6e",
    "cinza_500": "#4D5B6E",
    "cinza_300": "#D6DDE6",
    "cinza_200": "#D6DDE6",
    "cinza_100": "#F2F4F7",
    "background": "#F2F4F7",
    "text_primary": "#142133",
    "text_secondary": "#4d5b6e",
    "white": "#FFFFFF",
    # Cores Semânticas de Estado Operacional (RNF04)
    "OPERACIONAL": "#1B7A43",
    "EM_MANUTENCAO": "#F2B21B",
    "PARADA": "#B3261E",
    # Cores de Prioridade de Chamados
    "BAIXA": "#4D5B6E",
    "MEDIA": "#1F5FD6",
    "ALTA": "#F2B21B",
    "CRITICA": "#B3261E",
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
