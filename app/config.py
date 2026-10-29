"""Configurações do sistema (podem ser trocadas por variáveis de ambiente)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("AMATECH_DB", BASE_DIR / "database" / "amatech.db"))
MIGRACOES_DIR = BASE_DIR / "database" / "migracoes"
STATIC_DIR = BASE_DIR / "static"

# O SQLite grava CURRENT_TIMESTAMP em UTC. Manaus = UTC-4 (sem horário de verão).
FUSO_HORAS = int(os.environ.get("AMATECH_FUSO", "-4"))

# Chave que as máquinas/IoT enviam no cabeçalho X-API-Key (RF017).
API_KEY_MAQUINAS = os.environ.get("AMATECH_API_KEY", "amatech-iot-demo")
MATRICULA_IOT = "MAT-IOT"          # usuário de serviço usado nas atualizações automáticas

# Chaves de demonstração dos outros sistemas do ecossistema (OA3), criadas ao iniciar se o nome ainda não existir.
# Mesmo espírito da chave amatech-iot-demo: só para a demonstração. AMATECH_CHAVES_DEMO=0 desliga.
CHAVES_DEMO = {} if os.environ.get("AMATECH_CHAVES_DEMO", "1") == "0" else {
    "qualidade": os.environ.get("AMATECH_CHAVE_QUALIDADE", "amt_demo_qualidade"),
    "dashboard": os.environ.get("AMATECH_CHAVE_DASHBOARD", "amt_demo_dashboard"),
    "manutencao": os.environ.get("AMATECH_CHAVE_MANUTENCAO", "amt_demo_manutencao"),
}

SESSAO_HORAS = 12                  # validade do login
PREFIXO_SERIE = "AMT"              # número de série: AMT-000245
ESTOQUE_CRITICO = 50               # abaixo (ou igual) disso o componente aparece como crítico
ORDEM_LATERAL = 90                 # status com ordem >= 90 (Parado, Reprovado) ficam fora do fluxo principal

CARGOS = ["Administrador", "Operador", "Almoxarife", "Inspetor de Qualidade", "Integração"]
CARGOS_ADMIN = ("Administrador",)
CARGOS_BAIXA = ("Administrador", "Almoxarife")

VERSAO = "1.0.0"
# Origens (sites) autorizadas a chamar a API pelo navegador, separadas por vírgula.
# Ex.: AMATECH_CORS="http://localhost:3000,http://192.168.0.20:8501". Vazio = só o próprio sistema.
CORS_ORIGENS = [o.strip() for o in os.environ.get("AMATECH_CORS", "").split(",") if o.strip()]
