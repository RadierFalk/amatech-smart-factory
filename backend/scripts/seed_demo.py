"""Dados de demonstração para um banco novo: as 6 personas, as máquinas e o catálogo de peças.

Uso (a partir de backend/, depois de `alembic upgrade head`):
    python -m scripts.seed_demo

Cada tabela só é povoada se estiver vazia, então rodar de novo não duplica nada.
Para trazer os dados reais dos bancos SQLite antigos, use o script de migração (HANDOFF_POSTGRES.md).
Não use em produção: a senha é pública (está no README).
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import SessaoLocal
from app.core.rbac import Perfil
from app.core.seguranca import gerar_hash
from app.modulos.manutencao.modelos import Equipamento, Peca
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

# Mesmas TAGs de manutencao/docs/02_DATABASE_SCHEMA.sql (a Qualidade e a Rastreabilidade usam essas TAGs).
MAQUINAS = [
    ("SMT-01", "Insersora Automática High-Speed", "SMT", "Posto 01"),
    ("SMT-02", "Forno de Refusão 10 Zonas", "SMT", "Posto 02"),
    ("SMT-03", "Máquina de Serigrafia (Screen Printer)", "SMT", "Posto 01"),
    ("TEST-01", "Testador ICT (In-Circuit Test)", "Testes Funcionais", "Posto 01"),
    ("TEST-02", "Testador Funcional FCT 01", "Testes Funcionais", "Posto 02"),
    ("TEST-03", "Rack de Burn-in e Stress Térmico", "Testes Funcionais", "Posto 03"),
    ("MONT-01", "Esteira Automatizada de Montagem", "Montagem Final", "Posto 01"),
    ("EMB-01", "Encartuchadora Automática", "Embalagem", "Posto 01"),
    ("INS-01", "Bancada de Inserção Manual", "Inserção Manual", "Posto 01"),
    ("QC-01", "Bancada de Inspeção da Qualidade", "Inspeção da Qualidade", "Posto 01"),
]

PECAS = [
    ("PN-COR-100", "Correia Dentada de Alimentador SMT"),
    ("PN-SEN-030", "Sensor Óptico de Posicionamento 24V"),
    ("PN-RES-500", "Resistência Tubular Forno de Refusão"),
    ("PN-VAL-012", "Válvula Solenoide Pneumática 5/2"),
    ("PN-CAB-045", "Cabo de Sonda ICT de Precisão"),
    ("PN-ROL-608", "Rolamento Blindado Esteira de Montagem"),
    ("PN-VEN-120", "Ventoinha Cooler Industrial 120mm"),
]


def _vazia(sessao: Session, modelo) -> bool:
    return not sessao.scalar(select(func.count()).select_from(modelo))


def popular(sessao: Session) -> list[str]:
    """Povoa as tabelas vazias e devolve o que foi feito (uma linha por tabela)."""
    feito = []
    if _vazia(sessao, Usuario):
        hash_demo = gerar_hash(SENHA_DEMO)
        for matricula, nome, perfil in PERSONAS:
            sessao.add(Usuario(matricula=matricula, nome=nome, senha_hash=hash_demo, perfil=perfil.value))
        feito.append(f"usr.usuarios: {len(PERSONAS)} personas (senha: {SENHA_DEMO})")
    if _vazia(sessao, Equipamento):
        for tag, nome, setor, posto in MAQUINAS:
            sessao.add(Equipamento(codigo_tag=tag, nome=nome, setor=setor, posto_trabalho=posto))
        feito.append(f"mnt.equipamentos: {len(MAQUINAS)} máquinas")
    if _vazia(sessao, Peca):
        for codigo, nome in PECAS:
            sessao.add(Peca(codigo_peca=codigo, nome=nome, unidade_medida="UN"))
        feito.append(f"mnt.pecas: {len(PECAS)} peças")
    sessao.flush()
    return feito


def main() -> None:
    with SessaoLocal() as sessao:
        feito = popular(sessao)
        sessao.commit()
    print("\n".join(feito) if feito else "Todas as tabelas já têm dados; nada a fazer.")


if __name__ == "__main__":
    main()
