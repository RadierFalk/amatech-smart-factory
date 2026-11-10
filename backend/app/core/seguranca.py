"""Hash de senhas (Argon2) e tokens de acesso (JWT)."""
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import obter_configuracao

# Mesmos parâmetros do portal antigo, para os hashes migrados continuarem válidos.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, hash_gravado: str) -> bool:
    """Só aceita hashes Argon2. Senhas em texto puro dos bancos antigos são convertidas na migração."""
    if not senha or not hash_gravado or not hash_gravado.startswith("$argon2"):
        return False
    try:
        return _hasher.verify(hash_gravado, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def criar_token(sub: str, dados: dict[str, Any] | None = None) -> str:
    cfg = obter_configuracao()
    agora = datetime.now(UTC)
    corpo = {
        "sub": sub,
        "iat": agora,
        "exp": agora + timedelta(minutes=cfg.jwt_expiracao_minutos),
        **(dados or {}),
    }
    return jwt.encode(corpo, cfg.jwt_segredo, algorithm=cfg.jwt_algoritmo)


def decodificar_token(token: str) -> dict[str, Any]:
    """Levanta jwt.PyJWTError se o token for inválido ou expirado."""
    cfg = obter_configuracao()
    return jwt.decode(token, cfg.jwt_segredo, algorithms=[cfg.jwt_algoritmo])
