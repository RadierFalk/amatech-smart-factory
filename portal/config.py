"""
Configurações do Portal ERP AMATECH.
Define portas, URLs dos módulos integrados e caminhos de banco de dados.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = BASE_DIR.parent

# Banco de dados central de identidades do ERP
BANCO_DIR = BASE_DIR / "banco"
DB_PATH = Path(os.environ.get("ERP_DB", BANCO_DIR / "erp_usuarios.db"))

# URLs de acesso web aos módulos (para ambiente local e servidor)
PORTAL_URL = os.environ.get("ERP_PORTAL_URL", "http://localhost:8500")
RASTREABILIDADE_URL = os.environ.get("RASTREABILIDADE_URL", "http://localhost:8000")
QUALIDADE_URL = os.environ.get("QUALIDADE_URL", "http://localhost:8502")
MANUTENCAO_URL = os.environ.get("MANUTENCAO_URL", "http://localhost:8503")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8501")

# APIs para monitoramento em tempo real do ecossistema
APIS = {
    "Rastreabilidade": os.environ.get("RASTREABILIDADE_API_URL", "http://localhost:8000/api/v1/saude"),
    "Qualidade": os.environ.get("QUALIDADE_API_URL", "http://localhost:5000/api/status"),
    "Manutenção": os.environ.get("MANUTENCAO_API_URL", "http://localhost:5002/api/status"),
    "Dashboard": os.environ.get("DASHBOARD_API_URL", "http://localhost:5003/api/status"),
}

SENHA_INICIAL_PADRAO = "amatech1234"
