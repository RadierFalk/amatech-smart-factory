# Imagem única dos quatro sistemas. Cada serviço do docker-compose.yml escolhe a pasta (working_dir) e o comando.
FROM python:3.14-slim

# TZ no formato POSIX (UTC-4, Manaus): funciona sem instalar o pacote tzdata. Usado nos horários "agora" das telas.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ="<-04>4"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
