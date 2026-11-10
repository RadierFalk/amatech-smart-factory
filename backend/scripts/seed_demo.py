"""Cria as 6 personas de demonstração se a tabela usr.usuarios estiver vazia.

Uso (a partir de backend/, depois de `alembic upgrade head`):
    python -m scripts.seed_demo

Não use em produção: a senha é pública (está no README).
"""
from sqlalchemy import func, select

from app.core.db import SessaoLocal
from app.core.rbac import Perfil
from app.core.seguranca import gerar_hash
from app.modulos.usuarios.modelos import Usuario

SENHA_DEMO = "amatech1234"

PERSONAS = [
    ("ADM-0001", "Ana Souza", Perfil.ADMINISTRADOR),
    ("GES-0001", "Orlando Vandres", Perfil.SUPERVISOR),
    ("QUA-0001", "Maria Santos", Perfil.INSPETOR),
    ("OPE-0001", "João Silva", Perfil.OPERADOR),
    ("TEC-2001", "João Lima Silva", Perfil.TECNICO),
    ("ALM-0001", "Carlos Oliveira", Perfil.ALMOXARIFE),
]


def main() -> None:
    with SessaoLocal() as sessao:
        if sessao.scalar(select(func.count()).select_from(Usuario)):
            print("usr.usuarios já tem registros; nada a fazer.")
            return
        hash_demo = gerar_hash(SENHA_DEMO)
        for matricula, nome, perfil in PERSONAS:
            sessao.add(Usuario(matricula=matricula, nome=nome, senha_hash=hash_demo, perfil=perfil.value))
        sessao.commit()
        print(f"{len(PERSONAS)} personas criadas (senha: {SENHA_DEMO}).")


if __name__ == "__main__":
    main()
