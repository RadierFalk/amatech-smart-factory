"""Leitura e gravação de datas nos formatos do banco: 'AAAA-MM-DD' e 'AAAA-MM-DD HH:MM'."""
from datetime import date, datetime

FORMATO_DATA = "%Y-%m-%d"
FORMATO_DATA_HORA = "%Y-%m-%d %H:%M"

_ENTRADAS_DATA = ("%Y-%m-%d", "%d/%m/%Y")
_ENTRADAS_DATA_HORA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                       "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


def ler_data(valor):
    """Aceita date, datetime, 'AAAA-MM-DD' ou 'DD/MM/AAAA'. Devolve date ou None se não for uma data válida."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    for formato in _ENTRADAS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def ler_data_hora(valor):
    """Aceita datetime ou textos como '2026-08-15 09:30', '15/08/2026 09:30' e '2026-08-15T09:30:00'."""
    if isinstance(valor, datetime):
        return valor.replace(second=0, microsecond=0, tzinfo=None)
    texto = str(valor or "").strip()
    for formato in _ENTRADAS_DATA_HORA:
        try:
            return datetime.strptime(texto, formato).replace(second=0)
        except ValueError:
            continue
    return None


def texto_data(valor):
    return valor.strftime(FORMATO_DATA)


def texto_data_hora(valor):
    return valor.strftime(FORMATO_DATA_HORA)
