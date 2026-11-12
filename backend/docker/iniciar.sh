#!/bin/sh
# Ponto de entrada do contêiner da API: espera o banco, aplica as migrações e sobe o uvicorn.
#   AMATECH_SEED_DEMO=1  povoa os dados de demonstração (só tabelas vazias). Nunca use junto com a migração dos dados reais.
#   AMATECH_WORKERS      processos do uvicorn (padrão 2).
set -eu

echo "Esperando o PostgreSQL..."
python - <<'PY'
import sys, time
from sqlalchemy import create_engine, text
from app.core.config import obter_configuracao

engine = create_engine(obter_configuracao().database_url, pool_pre_ping=True)
for tentativa in range(60):
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        print("PostgreSQL no ar.")
        sys.exit(0)
    except Exception as erro:  # noqa: BLE001 - qualquer falha de conexão: tenta de novo
        if tentativa == 0:
            print(f"Ainda não: {type(erro).__name__}. Tentando por até 2 minutos.")
        time.sleep(2)
print("PostgreSQL não respondeu em 2 minutos.", file=sys.stderr)
sys.exit(1)
PY

echo "Aplicando as migrações..."
python -m alembic upgrade head

if [ "${AMATECH_SEED_DEMO:-0}" = "1" ]; then
  echo "Povoando os dados de demonstração (AMATECH_SEED_DEMO=1)..."
  python -m scripts.seed_demo
fi

# 0.0.0.0 dentro do contêiner: a porta não é publicada no servidor; só o serviço erp-web (nginx) fala com ela.
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --workers "${AMATECH_WORKERS:-2}" --proxy-headers --forwarded-allow-ips '*'
