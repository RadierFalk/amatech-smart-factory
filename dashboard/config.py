"""Configurações do Dashboard Industrial (podem ser trocadas por variáveis de ambiente).

Usado por todas as camadas: caminhos, fuso horário e endereços dos sistemas dos outros setores.
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_BANCO = Path(os.environ.get("DASHBOARD_DB", BASE_DIR / "database" / "banco.db"))
SCRIPT_BANCO = BASE_DIR / "database" / "banco_dashboard_industrial.sql"
PASTA_MODELOS_CSV = BASE_DIR / "database" / "modelos_csv"

# Manaus = UTC-4 (sem horário de verão). Os outros sistemas que gravam em UTC são convertidos para este fuso.
FUSO_HORAS = int(os.environ.get("DASHBOARD_FUSO", "-4"))
FUSO = timezone(timedelta(hours=FUSO_HORAS))

# ---------------------------------------------------------------- sistemas dos outros setores (sincronização)
RASTREABILIDADE_URL = os.environ.get("RASTREABILIDADE_URL", "http://localhost:8000").rstrip("/")
RASTREABILIDADE_CHAVE = os.environ.get("RASTREABILIDADE_CHAVE", "amt_demo_dashboard")
QUALIDADE_URL = os.environ.get("QUALIDADE_URL", "http://localhost:5000").rstrip("/")
QUALIDADE_CHAVE = os.environ.get("QUALIDADE_CHAVE", "amatech-qualidade-demo")
MANUTENCAO_URL = os.environ.get("MANUTENCAO_URL", "http://localhost:5002").rstrip("/")
MANUTENCAO_CHAVE = os.environ.get("MANUTENCAO_CHAVE", "amatech-manutencao-demo")
TEMPO_LIMITE_HTTP = float(os.environ.get("DASHBOARD_TEMPO_LIMITE", "5"))

# ---------------------------------------------------------------- API do próprio Dashboard (api.py)
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY", "amatech-dashboard-demo")


def agora():
    """Data e hora atuais no fuso da fábrica, sem fuso no objeto (o banco guarda horário local)."""
    return datetime.now(FUSO).replace(tzinfo=None)
