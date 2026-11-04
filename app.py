"""
Ponto de Entrada Principal do ERP AMATECH (Aplicação Unificada).

Executa todos os módulos integrados (Rastreabilidade, Qualidade, Manutenção,
Dashboard Industrial e Gestão de Usuários) em uma única porta e sessão.

Executar com:
    streamlit run app.py
"""
from pathlib import Path
import runpy
import sys

RAIZ = Path(__file__).resolve().parent
PASTA_PORTAL = RAIZ / "portal"

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if str(PASTA_PORTAL) not in sys.path:
    sys.path.insert(0, str(PASTA_PORTAL))

runpy.run_path(str(PASTA_PORTAL / "app.py"), run_name="__main__")
