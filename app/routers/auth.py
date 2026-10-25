from fastapi import APIRouter, Depends, HTTPException

from app.db import get_conn, um
from app.schemas import LoginIn
from app.seguranca import criar_sessao, encerrar_sessao, usuario_atual, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])

TURNOS = ["Turno 1", "Turno 2"]   # a fábrica opera em dois turnos


@router.post("/login")
def login(dados: LoginIn, conn=Depends(get_conn)):
    u = um(conn, "SELECT id, matricula, nome, cargo, ativo, senha_hash FROM usuarios WHERE matricula = ?",
           (dados.matricula.strip().upper(),))
    if not u or not u["ativo"] or not verificar_senha(dados.senha, u["senha_hash"]):
        raise HTTPException(status_code=401, detail="Matrícula ou senha inválida.")
    token = criar_sessao(u["id"], dados.turno)
    return {"token": token, "turno": dados.turno,
            "usuario": {"id": u["id"], "matricula": u["matricula"], "nome": u["nome"], "cargo": u["cargo"]}}


@router.get("/me")
def me(usuario=Depends(usuario_atual)):
    return {"usuario": {k: usuario[k] for k in ("id", "matricula", "nome", "cargo")}, "turno": usuario["turno"]}


@router.get("/turnos")
def turnos():
    return TURNOS


@router.post("/logout")
def logout(usuario=Depends(usuario_atual)):
    encerrar_sessao(usuario["token"])
    return {"ok": True}
