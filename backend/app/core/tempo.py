"""Data e hora: o banco grava sempre em UTC; a fábrica fica em Manaus (UTC-4, sem horário de verão)."""
from datetime import UTC, datetime, timedelta, timezone

# Offset fixo em vez de zoneinfo("America/Manaus"): dispensa o pacote tzdata no Windows e Manaus não tem horário de verão.
FUSO_FABRICA = timezone(timedelta(hours=-4), "Manaus")


def agora() -> datetime:
    """Instante atual em UTC. Os testes substituem esta função para controlar o relógio."""
    return datetime.now(UTC)


def utc(valor: datetime | None) -> datetime | None:
    """Garante datetime com fuso UTC (alguns drivers devolvem sem fuso)."""
    if valor is None:
        return None
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def minutos_entre(inicio: datetime | None, fim: datetime | None, minimo: int = 1) -> int:
    """Minutos arredondados entre dois instantes; `minimo` quando o intervalo existe, 0 quando não existe."""
    a, b = utc(inicio), utc(fim)
    if a is None or b is None or b < a:
        return 0
    return max(minimo, round((b - a).total_seconds() / 60))
