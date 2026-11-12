# Imagem da API única do ERP AMATECH (FastAPI + SQLAlchemy + Alembic).
# Ao subir: espera o PostgreSQL, aplica as migrações (alembic upgrade head) e inicia o uvicorn na porta 8000.
# Configuração por variáveis AMATECH_* (app/core/config.py); nada de .env dentro da imagem.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x docker/iniciar.sh \
    && useradd --system --uid 10001 --no-create-home amatech \
    && chown -R amatech /app
USER amatech

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import json, sys, urllib.request; d = json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/saude', timeout=4)); sys.exit(0 if d.get('banco') == 'ok' else 1)"]

ENTRYPOINT ["./docker/iniciar.sh"]
