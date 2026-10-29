"""Senhas, login (sessões em memória) e verificação de permissões."""
import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Depends, Header, HTTPException

from app import config
from app.db import get_conn, um

ITERACOES = 200_000
_sessoes: dict[str, dict] = {}   # token -> {"usuario_id", "turno", "expira"}


# ---------- senhas ----------
def hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
    return "pbkdf2$%d$%s$%s" % (ITERACOES, base64.b64encode(sal).decode(), base64.b64encode(h).decode())


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        _, iteracoes, sal, esperado = armazenado.split("$")
        h = hashlib.pbkdf2_hmac("sha256", senha.encode(), base64.b64decode(sal), int(iteracoes))
        return hmac.compare_digest(h, base64.b64decode(esperado))
    except (ValueError, TypeError):
        return False   # hash inválido (ex.: usuário de serviço sem senha)


# ---------- sessões ----------
def criar_sessao(usuario_id: int, turno: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessoes[token] = {"usuario_id": usuario_id, "turno": turno,
                       "expira": time.time() + config.SESSAO_HORAS * 3600}
    return token


def encerrar_sessao(token: str) -> None:
    _sessoes.pop(token, None)


def _token_do_cabecalho(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    return authorization[7:].strip()


def usuario_atual(authorization: str | None = Header(None), conn=Depends(get_conn)) -> dict:
    token = _token_do_cabecalho(authorization)
    sessao = _sessoes.get(token)
    if not sessao or sessao["expira"] < time.time():
        _sessoes.pop(token, None)
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
    usuario = um(conn, "SELECT id, matricula, nome, cargo, ativo FROM usuarios WHERE id = ?",
                 (sessao["usuario_id"],))
    if not usuario or not usuario["ativo"]:
        raise HTTPException(status_code=401, detail="Usuário inativo.")
    usuario["turno"] = sessao["turno"]
    usuario["token"] = token
    return usuario


def exigir_cargos(*cargos):
    """Cria uma dependência que só deixa passar os cargos informados."""
    def verificador(usuario=Depends(usuario_atual)):
        if usuario["cargo"] not in cargos:
            raise HTTPException(status_code=403,
                                detail="Seu cargo não tem permissão para esta operação (%s)." % ", ".join(cargos))
        return usuario
    return verificador


exigir_admin = exigir_cargos(*config.CARGOS_ADMIN)
exigir_baixa = exigir_cargos(*config.CARGOS_BAIXA)
