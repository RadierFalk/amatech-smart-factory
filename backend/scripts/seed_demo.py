"""Dados de demonstração para um banco novo: personas, máquinas, peças e os cadastros da Qualidade.

Uso (a partir de backend/, depois de `alembic upgrade head`):
    python -m scripts.seed_demo

Cada tabela só é povoada se estiver vazia, então rodar de novo não duplica nada.
Para trazer os dados reais dos bancos SQLite antigos, use o script de migração (HANDOFF_POSTGRES.md).
Não use em produção: a senha é pública (está no README).
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import obter_configuracao
from app.core.db import SessaoLocal
from app.core.rbac import Perfil
from app.core.seguranca import gerar_hash
from app.modulos.manutencao.modelos import Equipamento, Peca
from app.modulos.qualidade.modelos import Estacao, Produto, TipoDefeito
from app.modulos.usuarios.modelos import Usuario
from scripts import demo_rastreabilidade

SENHA_DEMO = "amatech1234"
SERVICO = obter_configuracao().matricula_servico

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

# Mesmos cadastros de qualidade/criar_banco.py (séries e modelos iguais aos da Rastreabilidade).
ESTACOES = [
    ("SMT", "Montagem de componentes eletrônicos"),
    ("Inserção Manual", "Inserção manual de componentes"),
    ("Montagem Final", "Montagem final do notebook"),
    ("Instalação de Software", "Instalação e configuração do software"),
    ("Teste Funcional", "Testes funcionais do produto"),
    ("Inspeção de Qualidade", "Inspeção e controle da qualidade"),
    ("Embalagem", "Embalagem do produto final"),
]

TIPOS_DEFEITO = ["Tela", "Teclado", "Touchpad", "USB", "Áudio", "Wi-Fi", "Câmera", "Bateria",
                 "Armazenamento", "Desempenho", "Montagem", "Software"]

MODELOS_NOTEBOOK = ["AMT N14", "AMT N15", "AMT N16", "AMT N17", "AMT N18"]
PRODUTOS = [(f"AMT-{n:06d}", MODELOS_NOTEBOOK[(n - 1) % len(MODELOS_NOTEBOOK)]) for n in range(1, 31)]


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
    if not sessao.scalar(select(Usuario.id).where(Usuario.matricula == SERVICO)):
        # Conta de serviço das máquinas (/api/ras/maquinas/status): inativa e sem senha válida, não faz login.
        sessao.add(Usuario(matricula=SERVICO, nome="Integração (máquinas e outros sistemas)", senha_hash="!",
                           perfil=Perfil.OPERADOR.value, ativo=False))
        feito.append(f"usr.usuarios: conta de serviço {SERVICO}")
    if _vazia(sessao, Equipamento):
        for tag, nome, setor, posto in MAQUINAS:
            sessao.add(Equipamento(codigo_tag=tag, nome=nome, setor=setor, posto_trabalho=posto))
        feito.append(f"mnt.equipamentos: {len(MAQUINAS)} máquinas")
    if _vazia(sessao, Peca):
        for codigo, nome in PECAS:
            sessao.add(Peca(codigo_peca=codigo, nome=nome, unidade_medida="UN"))
        feito.append(f"mnt.pecas: {len(PECAS)} peças")
    if _vazia(sessao, Estacao):
        sessao.add_all(Estacao(nome=nome, descricao=descricao) for nome, descricao in ESTACOES)
        feito.append(f"qld.estacoes: {len(ESTACOES)} estações")
    if _vazia(sessao, TipoDefeito):
        sessao.add_all(TipoDefeito(nome=nome) for nome in TIPOS_DEFEITO)
        feito.append(f"qld.tipos_defeito: {len(TIPOS_DEFEITO)} tipos de defeito")
    if _vazia(sessao, Produto):
        sessao.add_all(Produto(numero_serie=serie, modelo=modelo) for serie, modelo in PRODUTOS)
        feito.append(f"qld.produtos: {len(PRODUTOS)} notebooks")
    sessao.flush()
    pessoas = {p.matricula: p for p in sessao.scalars(select(Usuario))}
    if all(m in pessoas for m in ("OPE-0001", "QUA-0001", "ALM-0001")):
        feito += demo_rastreabilidade.popular(sessao, {
            "operador": pessoas["OPE-0001"], "operador2": pessoas.get("OP-10234", pessoas["OPE-0001"]),
            "inspetor": pessoas["QUA-0001"], "almoxarife": pessoas["ALM-0001"],
        })
    sessao.flush()
    return feito


def main() -> None:
    with SessaoLocal() as sessao:
        feito = popular(sessao)
        sessao.commit()
    print("\n".join(feito) if feito else "Todas as tabelas já têm dados; nada a fazer.")


if __name__ == "__main__":
    main()
