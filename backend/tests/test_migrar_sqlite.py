"""Testes do script de migração SQLite -> PostgreSQL (scripts/migrar_sqlite.py).

Cada teste monta bancos SQLite pequenos (só as colunas que o script lê) e migra para o banco de testes.
"""
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.rbac import Perfil
from app.core.seguranca import verificar_senha
from app.modulos.manutencao.modelos import Chamado, ChamadoPeca, Equipamento, HistoricoStatus, Peca
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.usuarios.modelos import Usuario
from scripts import migrar_sqlite as m

ARGON_QLD = "$argon2id$v=19$m=19456,t=2,p=1$c2FsdGRlbW9zYWx0$hashdeexemploqualquer000000000000000000000"
PBKDF2_DSH = "pbkdf2_sha256$200000$2a749bbfdb6975587c0f333750989db5$aed48177dd4d2dbf76b9943f49c45f22"

DDL = {
    "portal": """CREATE TABLE usuarios (id INTEGER PRIMARY KEY, matricula TEXT, nome TEXT, senha_hash TEXT,
                 perfil TEXT, ativo BOOLEAN DEFAULT 1, criado_em TIMESTAMP)""",
    "mnt": """
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, matricula TEXT, senha_hash TEXT, perfil TEXT,
                               ativo BOOLEAN DEFAULT 1, criado_em TIMESTAMP);
        CREATE TABLE equipamentos (id INTEGER PRIMARY KEY, codigo_tag TEXT, nome TEXT, setor TEXT,
                                   posto_trabalho TEXT, status_operacional TEXT DEFAULT 'OPERACIONAL',
                                   ativo BOOLEAN DEFAULT 1);
        CREATE TABLE pecas (id INTEGER PRIMARY KEY, codigo_peca TEXT, nome TEXT, unidade_medida TEXT DEFAULT 'UN',
                            ativo BOOLEAN DEFAULT 1);
        CREATE TABLE chamados_manutencao (id INTEGER PRIMARY KEY, equipamento_id INTEGER, operador_abertura_id INTEGER,
            tecnico_responsavel_id INTEGER, prioridade TEXT, tipo_manutencao TEXT DEFAULT 'CORRETIVA',
            status_chamado TEXT, descricao_falha TEXT, diagnostico_tecnico TEXT, causa_raiz TEXT,
            data_hora_abertura TIMESTAMP, data_hora_inicio_atendimento TIMESTAMP, data_hora_fim_atendimento TIMESTAMP,
            downtime_minutos INTEGER, origem_sistema TEXT, id_externo TEXT);
        CREATE TABLE chamado_pecas_trocadas (id INTEGER PRIMARY KEY, chamado_id INTEGER, peca_id INTEGER,
                                             quantidade NUMERIC);
        CREATE TABLE historico_status (id INTEGER PRIMARY KEY, equipamento_id INTEGER, chamado_id INTEGER,
            usuario_id INTEGER, status_anterior TEXT, status_novo TEXT, alterado_em TIMESTAMP);
    """,
    "qld": """
        CREATE TABLE usuario (id_usuario INTEGER PRIMARY KEY, nome_usuario TEXT, perfil_usuario TEXT,
                              matricula TEXT, senha_hash TEXT, ativo INTEGER DEFAULT 0, data_criacao TEXT);
        CREATE TABLE produto (id_produto INTEGER PRIMARY KEY, numero_serie_produto TEXT, modelo_produto TEXT);
        CREATE TABLE estacao (id_estacao INTEGER PRIMARY KEY, nome_estacao TEXT, descricao_estacao TEXT);
        CREATE TABLE tipo_defeito (id_tipo_defeito INTEGER PRIMARY KEY, nome_tipo_defeito TEXT, descricao_tipo_defeito TEXT);
        CREATE TABLE maquina (id_maquina INTEGER PRIMARY KEY, nome_maquina TEXT, descricao_maquina TEXT);
        CREATE TABLE ocorrencia (id_ocorrencia INTEGER PRIMARY KEY, data_ocorrencia DATE, hora_ocorrencia TIME,
            classificacao_defeito TEXT, situacao_produto TEXT, observacao_ocorrencia TEXT, acao_realizada TEXT,
            status_ocorrencia TEXT, visibilidade_ocorrencia TEXT DEFAULT 'Visivel', id_produto INTEGER,
            id_estacao INTEGER, id_tipo_defeito INTEGER, id_maquina INTEGER, id_usuario INTEGER);
    """,
    "ras": """CREATE TABLE usuarios (id INTEGER PRIMARY KEY, matricula TEXT, nome TEXT, email TEXT, senha_hash TEXT,
              cargo TEXT, ativo INTEGER DEFAULT 1, criado_em TEXT)""",
    "dsh": """
        CREATE TABLE perfil (id_perfil INTEGER PRIMARY KEY, nome TEXT);
        CREATE TABLE usuario (id_usuario INTEGER PRIMARY KEY, nome TEXT, login TEXT, senha_hash TEXT,
                              id_perfil INTEGER, ativo INTEGER DEFAULT 1, criado_em TEXT);
    """,
}


class Bancos:
    """Cria os SQLite de origem num diretório temporário; os que não forem criados ficam ausentes."""

    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.caminhos = {origem: pasta / f"{origem}.db" for origem in m.CAMINHOS_PADRAO}

    def sql(self, origem: str, comandos: str, *linhas: tuple[str, tuple]) -> None:
        caminho = self.caminhos[origem]
        novo = not caminho.exists()
        with sqlite3.connect(caminho) as conn:
            if novo:
                conn.executescript(DDL[origem])
            if comandos:
                conn.executescript(comandos)
            for sql, params in linhas:
                conn.execute(sql, params)
        conn.close()

    def usuario_mnt(self, id_, matricula, nome="Fulano", perfil="OPERADOR", senha="123456", ativo=1,
                    criado="2026-10-28 00:08:40"):
        self.sql("mnt", "", ("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)",
                             (id_, nome, matricula, senha, perfil, ativo, criado)))

    def usuario_qld(self, id_, matricula, nome="Fulano", perfil="Operador", senha=ARGON_QLD, ativo=1,
                    criado="2026-10-31T01:12:56"):
        self.sql("qld", "", ("INSERT INTO usuario VALUES (?,?,?,?,?,?,?)",
                             (id_, nome, perfil, matricula, senha, ativo, criado)))


@pytest.fixture
def bancos(tmp_path) -> Bancos:
    return Bancos(tmp_path)


@pytest.fixture
def migrar(engine_testes, sessao):
    """Roda o script inteiro (transação própria) contra o banco de testes. `sessao` garante a limpeza no final."""
    fabrica = sessionmaker(bind=engine_testes, expire_on_commit=False)

    def _migrar(b: Bancos, simular: bool = False) -> m.Relatorio:
        return m.executar(fabrica, b.caminhos, simular)

    return _migrar


def _usuarios(sessao) -> dict[str, Usuario]:
    sessao.expire_all()
    return {u.matricula: u for u in sessao.scalars(select(Usuario))}


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


# --------------------------------------------------------------------------- regra 1: perfil
def test_persona_usa_perfil_do_portal_e_registra_conflito(bancos, migrar, sessao):
    bancos.usuario_mnt(30, "ADM-0001", "Ana Souza", "GESTOR", "amatech123")
    bancos.usuario_qld(6, "TEC-2001", "João Lima Silva", "Operador")
    bancos.sql("portal", "", ("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)",
                              (1, "ADM-0001", "Ana Souza", "x", "Administrador", 1, "2026-11-01 10:00:00")))

    rel = migrar(bancos)

    us = _usuarios(sessao)
    assert us["ADM-0001"].perfil == Perfil.ADMINISTRADOR
    assert us["TEC-2001"].perfil == Perfil.TECNICO  # persona sem portal: lista PERSONAS do seed_demo
    assert any("ADM-0001" in c and "'GESTOR'" in c for c in rel.conflitos)
    assert any("TEC-2001" in c and "'Operador'" in c for c in rel.conflitos)


def test_quem_so_existe_nos_modulos_tem_perfil_mapeado(bancos, migrar, sessao):
    bancos.usuario_mnt(1, "OP-10234", perfil="OPERADOR")
    bancos.usuario_mnt(4, "TEC-2002", perfil="TECNICO")
    bancos.usuario_mnt(6, "GES-0002", perfil="GESTOR")
    bancos.usuario_qld(9, "QUA-0099", perfil="Inspetor de Qualidade")
    bancos.sql("ras", "", ("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?)",
                           (5, "MAT-0100", "Ana Beatriz", "a@b", "!", "Almoxarife", 1, "2026-10-01 00:00:00")))

    migrar(bancos)

    us = _usuarios(sessao)
    assert us["OP-10234"].perfil == Perfil.OPERADOR
    assert us["TEC-2002"].perfil == Perfil.TECNICO
    assert us["GES-0002"].perfil == Perfil.SUPERVISOR
    assert us["QUA-0099"].perfil == Perfil.INSPETOR
    assert us["MAT-0100"].perfil == Perfil.ALMOXARIFE


def test_perfil_conflitante_entre_modulos_segue_a_ordem_mnt_qld(bancos, migrar, sessao):
    bancos.usuario_mnt(1, "X-1", perfil="TECNICO")
    bancos.usuario_qld(1, "X-1", perfil="Operador")
    rel = migrar(bancos)
    assert _usuarios(sessao)["X-1"].perfil == Perfil.TECNICO
    assert any("X-1" in c and "QLD" in c for c in rel.conflitos)


@pytest.mark.parametrize(("texto", "esperado"), [
    ("Operador de estação", Perfil.OPERADOR),
    ("Inspetor de qualidade", Perfil.INSPETOR),
    ("Manutenção", Perfil.TECNICO),
    ("Supervisor de produção", Perfil.SUPERVISOR),
    ("Gestor/Diretoria", Perfil.SUPERVISOR),
    ("Administrador", Perfil.ADMINISTRADOR),
    ("Técnico de Manutenção", Perfil.TECNICO),
    ("Integração", Perfil.OPERADOR),
    ("Cozinheiro", None),
])
def test_perfil_por_texto(texto, esperado):
    assert m.perfil_por_texto(texto) == esperado


# --------------------------------------------------------------------------- regra 2: nome
def test_nome_do_portal_para_persona_e_primeiro_modulo_para_os_demais(bancos, migrar, sessao):
    bancos.sql("portal", "", ("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)",
                              (1, "OPE-0001", "João Silva", "x", "Operador de Produção", 1, "2026-11-01 00:00:00")))
    bancos.usuario_mnt(29, "OPE-0001", nome="Joao S.")
    bancos.usuario_mnt(1, "OP-1", nome="")
    bancos.usuario_qld(1, "OP-1", nome="Nome da Qualidade")

    rel = migrar(bancos)

    us = _usuarios(sessao)
    assert us["OPE-0001"].nome == "João Silva"
    assert us["OP-1"].nome == "Nome da Qualidade"  # MNT vazio: vale o próximo da ordem
    assert any("OPE-0001" in c and "Joao S." in c for c in rel.conflitos)


# --------------------------------------------------------------------------- regra 3: senha
def test_senhas(bancos, migrar, sessao):
    bancos.usuario_mnt(30, "ADM-0001", perfil="GESTOR", senha="amatech123")
    bancos.usuario_mnt(1, "OP-10234", senha="123456")
    bancos.usuario_mnt(7, "SVC-INTEGRACAO", senha="!", ativo=0)
    bancos.usuario_qld(1, "QUA-0099", perfil="Inspetor de Qualidade", senha=ARGON_QLD)
    bancos.sql("dsh", "INSERT INTO perfil VALUES (4, 'Supervisor de produção');",
               ("INSERT INTO usuario VALUES (?,?,?,?,?,?,?)",
                (2, "Maria Souza", "supervisor", PBKDF2_DSH, 4, 1, "2026-10-01 08:00:00")))

    rel = migrar(bancos)

    us = _usuarios(sessao)
    assert verificar_senha(m.SENHA_DEMO, us["ADM-0001"].senha_hash)  # persona: senha do README
    assert not verificar_senha("amatech123", us["ADM-0001"].senha_hash)
    assert us["OP-10234"].senha_hash.startswith("$argon2")
    assert verificar_senha("123456", us["OP-10234"].senha_hash)
    assert us["QUA-0099"].senha_hash == ARGON_QLD  # hash Argon2 mantido como está
    assert us["SVC-INTEGRACAO"].senha_hash == "!"
    assert us["SUPERVISOR"].senha_hash == PBKDF2_DSH  # formato não suportado: sem login até redefinir
    assert rel.senhas_convertidas == ["OP-10234"]
    assert set(rel.senhas_sem_login) == {"SVC-INTEGRACAO", "SUPERVISOR"}
    assert "123456" not in rel.texto(False) and "amatech123" not in rel.texto(False)


# --------------------------------------------------------------------------- regras 4 e 5: ativo e criado_em
def test_inativo_em_qualquer_origem_e_menor_data(bancos, migrar, sessao):
    bancos.usuario_mnt(1, "X-1", ativo=1, criado="2026-10-28 00:08:40")
    bancos.usuario_qld(1, "X-1", ativo=0, criado="2026-10-20T12:00:00")
    bancos.sql("dsh", "INSERT INTO perfil VALUES (1, 'Operador de estação');",
               ("INSERT INTO usuario VALUES (?,?,?,?,?,?,?)", (1, "Fulano", "x-1", "!", 1, 1, "2026-10-20 07:00:00")))

    rel = migrar(bancos)

    u = _usuarios(sessao)["X-1"]
    assert u.ativo is False
    # DSH grava hora local de Manaus: 07:00 (UTC-4) = 11:00 UTC, antes das 12:00 UTC da QLD.
    assert _utc(u.criado_em) == datetime(2026, 10, 20, 11, 0, tzinfo=UTC)
    assert any("X-1" in c and "inativo" in c for c in rel.conflitos)


def test_matricula_normalizada_unifica_usuarios(bancos, migrar, sessao):
    bancos.usuario_mnt(1, " op-10234 ")
    bancos.usuario_qld(1, "OP-10234")
    bancos.usuario_qld(2, None, nome="Sem matrícula")
    rel = migrar(bancos)
    assert list(_usuarios(sessao)) == ["OP-10234"]
    assert any("sem matrícula" in i for i in rel.ignorados)


# --------------------------------------------------------------------------- mnt
def _mnt_basico(b: Bancos) -> None:
    b.usuario_mnt(1, "OP-10234")
    b.usuario_mnt(3, "TEC-2001", perfil="TECNICO")
    b.sql("mnt", """
        INSERT INTO equipamentos VALUES (1, 'smt-01', 'Insersora', 'SMT', 'Posto 01', 'OPERACIONAL', 1);
        INSERT INTO equipamentos VALUES (2, 'SMT-02', 'Forno', 'SMT', NULL, 'OPERACIONAL', 0);
        INSERT INTO equipamentos VALUES (8, 'EMB-01', 'Encartuchadora', 'Embalagem', NULL, 'PARADA', 1);
        INSERT INTO pecas VALUES (1, 'pn-cor-100', 'Correia', 'UN', 1);
        INSERT INTO pecas VALUES (3, 'PN-RES-500', 'Resistência', 'UN', 1);
        INSERT INTO chamados_manutencao VALUES (1, 1, 1, 3, 'ALTA', 'CORRETIVA', 'CONCLUIDO', 'Travou', 'Correia',
            'Desgaste', '2026-10-25 20:08:40', '2026-10-25 20:23:40', '2026-10-25 21:08:40', 60, NULL, NULL);
        INSERT INTO chamados_manutencao VALUES (2, 2, 1, 3, 'CRITICA', 'CORRETIVA', 'CANCELADO', 'Oscila',
            'Cancelado na tela da OS', NULL, '2026-10-27 23:08:40', NULL, '2026-11-05 02:57:06', 0, 'QUALIDADE', 'Q-7');
        INSERT INTO chamados_manutencao VALUES (5, 8, 1, NULL, 'MEDIA', 'CORRETIVA', 'ABERTO', 'Parou', NULL, NULL,
            '2026-11-06 10:00:00', NULL, NULL, NULL, NULL, NULL);
        INSERT INTO chamado_pecas_trocadas VALUES (1, 1, 1, 1);
        INSERT INTO chamado_pecas_trocadas VALUES (2, 1, 1, 2.5);
        INSERT INTO chamado_pecas_trocadas VALUES (3, 1, 3, 1);
        INSERT INTO historico_status VALUES (1, 1, 1, 1, 'OPERACIONAL', 'PARADA', '2026-10-25 20:08:40');
        INSERT INTO historico_status VALUES (10, 8, 5, 3, 'OPERACIONAL', 'OPERACIONAL', '2026-11-05 03:49:55');
    """)


def test_migra_mnt_preservando_ids_e_aplicando_as_regras(bancos, migrar, sessao):
    _mnt_basico(bancos)
    rel = migrar(bancos)
    sessao.expire_all()
    us = _usuarios(sessao)

    eqp = {e.id: e for e in sessao.scalars(select(Equipamento))}
    assert set(eqp) == {1, 2, 8}
    assert eqp[1].codigo_tag == "SMT-01" and eqp[2].ativo is False
    assert {p.id: p.codigo_peca for p in sessao.scalars(select(Peca))} == {1: "PN-COR-100", 3: "PN-RES-500"}

    chamados = {c.id: c for c in sessao.scalars(select(Chamado))}
    assert set(chamados) == {1, 2, 5}
    assert chamados[1].operador_abertura_id == us["OP-10234"].id
    assert chamados[1].tecnico_responsavel_id == us["TEC-2001"].id
    assert _utc(chamados[1].data_hora_abertura) == datetime(2026, 10, 25, 20, 8, 40, tzinfo=UTC)
    cancelado = chamados[2]
    assert cancelado.motivo_cancelamento == "Cancelado na tela da OS"
    assert cancelado.diagnostico_tecnico is None
    assert cancelado.origem_sistema == "qualidade"
    assert chamados[1].diagnostico_tecnico == "Correia" and chamados[1].motivo_cancelamento is None

    pecas = {(p.chamado_id, p.peca_id): p.quantidade for p in sessao.scalars(select(ChamadoPeca))}
    assert pecas == {(1, 1): Decimal("3.5"), (1, 3): Decimal("1")}
    assert rel.pecas_somadas == 1

    hist = {h.id: h for h in sessao.scalars(select(HistoricoStatus))}
    assert set(hist) == {1, 10}  # a linha OPERACIONAL -> OPERACIONAL também é histórico
    assert hist[10].usuario_id == us["TEC-2001"].id

    assert rel.gravadas["mnt.chamados"] == rel.lidas["mnt.chamados_manutencao"] == 3
    assert rel.gravadas["mnt.historico_status"] == rel.lidas["mnt.historico_status"] == 2


def test_duas_os_ativas_na_mesma_maquina_vira_pendencia_sem_falhar(bancos, migrar, sessao):
    _mnt_basico(bancos)
    bancos.sql("mnt", """
        INSERT INTO chamados_manutencao VALUES (6, 8, 1, 3, 'ALTA', 'CORRETIVA', 'EM_ANDAMENTO', 'De novo', NULL, NULL,
            '2026-11-07 10:00:00', '2026-11-07 10:05:00', NULL, NULL, NULL, NULL);
        INSERT INTO historico_status VALUES (11, 8, 6, 3, 'PARADA', 'EM_MANUTENCAO', '2026-11-07 10:05:00');
    """)

    rel = migrar(bancos)

    sessao.expire_all()
    assert {c.id for c in sessao.scalars(select(Chamado))} == {1, 2, 5}  # fica a mais antiga
    assert len(rel.pendencias) == 1 and "#5" in rel.pendencias[0] and "#6" in rel.pendencias[0]
    assert 11 not in {h.id for h in sessao.scalars(select(HistoricoStatus))}


def test_usuario_inexistente_desfaz_tudo(bancos, migrar, sessao):
    _mnt_basico(bancos)
    bancos.sql("mnt", "UPDATE chamados_manutencao SET operador_abertura_id = 99 WHERE id = 5")
    with pytest.raises(m.ErroMigracao, match="usuário id 99"):
        migrar(bancos)
    assert _usuarios(sessao) == {}
    assert sessao.scalars(select(Equipamento)).first() is None


def test_destino_com_ids_diferentes_e_recusado(bancos, migrar, sessao):
    _mnt_basico(bancos)
    sessao.add(Equipamento(id=50, codigo_tag="SMT-01", nome="Seed", setor="SMT"))
    sessao.commit()
    with pytest.raises(m.ErroMigracao, match="banco vazio"):
        migrar(bancos)


# --------------------------------------------------------------------------- execução
def test_rodar_duas_vezes_nao_muda_nada(bancos, migrar, sessao):
    _mnt_basico(bancos)
    bancos.usuario_mnt(30, "ADM-0001", perfil="GESTOR", senha="amatech123")
    bancos.usuario_qld(1, "QUA-0099", perfil="Inspetor de Qualidade")

    migrar(bancos)
    antes = {mat: (u.id, u.nome, u.perfil, u.senha_hash, u.ativo, _utc(u.criado_em))
             for mat, u in _usuarios(sessao).items()}
    chamados_antes = sessao.scalars(select(Chamado.id)).all()

    rel = migrar(bancos)

    depois = {mat: (u.id, u.nome, u.perfil, u.senha_hash, u.ativo, _utc(u.criado_em))
              for mat, u in _usuarios(sessao).items()}
    assert depois == antes
    assert rel.usuarios_criados == [] and rel.usuarios_atualizados == []
    assert sorted(rel.usuarios_sem_mudanca) == sorted(antes)
    assert sessao.scalars(select(Chamado.id)).all() == chamados_antes
    assert len(sessao.scalars(select(ChamadoPeca)).all()) == 2


def test_simular_nao_grava(bancos, migrar, sessao):
    _mnt_basico(bancos)
    rel = migrar(bancos, simular=True)
    assert rel.usuarios_criados == ["OP-10234", "TEC-2001"]
    assert "SIMULAÇÃO" in rel.texto(True)
    assert _usuarios(sessao) == {}
    assert sessao.scalars(select(Chamado)).first() is None


def test_origem_ausente_e_avisada(bancos, migrar, sessao):
    bancos.usuario_mnt(1, "OP-1")
    rel = migrar(bancos)
    assert {o.split(":")[0] for o in rel.origens_ausentes} == {"portal", "qld", "ras", "dsh"}
    assert "OP-1" in _usuarios(sessao)


def test_bancos_do_repositorio(migrar, sessao):
    """Aceite da seção 4.2/4.3 com os arquivos versionados (MNT e QLD)."""
    caminhos = {o: m.CAMINHOS_PADRAO[o] for o in ("mnt", "qld")}
    if not all(c.is_file() for c in caminhos.values()):
        pytest.skip("Bancos de MNT/QLD do repositório não encontrados")
    b = Bancos(Path("."))
    b.caminhos = caminhos

    rel = migrar(b)

    us = _usuarios(sessao)
    assert len(us) == 11
    assert us["ADM-0001"].perfil == Perfil.ADMINISTRADOR and us["GES-0001"].perfil == Perfil.SUPERVISOR
    assert us["TEC-2001"].nome == "João Lima Silva"  # acentos preservados
    assert us["SVC-INTEGRACAO"].ativo is False
    for chave in ("equipamentos", "pecas", "historico_status"):
        assert rel.gravadas[f"mnt.{chave}"] == rel.lidas[f"mnt.{chave}"]
    assert rel.gravadas["mnt.chamados"] == rel.lidas["mnt.chamados_manutencao"]
    assert rel.gravadas["mnt.chamado_pecas"] + rel.pecas_somadas == rel.lidas["mnt.chamado_pecas_trocadas"]
    assert rel.pendencias == []

    for origem, destino in (("produto", "produtos"), ("estacao", "estacoes"), ("tipo_defeito", "tipos_defeito"),
                            ("ocorrencia", "ocorrencias")):
        assert rel.gravadas[f"qld.{destino}"] == rel.lidas[f"qld.{origem}"]
    sessao.expire_all()
    ocorrencias = sessao.scalars(select(Ocorrencia)).all()
    assert len(ocorrencias) == 39 and sum(o.oculta for o in ocorrencias) == 1

    rel2 = migrar(b)
    assert rel2.usuarios_criados == [] and rel2.usuarios_atualizados == []


# --------------------------------------------------------------------------- qld
def _qld_basico(b: Bancos) -> None:
    _mnt_basico(b)  # máquinas SMT-01, SMT-02, EMB-01 na Manutenção
    b.usuario_qld(2, "QUA-0001", "Maria Santos", "Inspetor de Qualidade")
    b.sql("qld", """
        INSERT INTO produto VALUES (1, 'amt-000001', 'AMT N14');
        INSERT INTO produto VALUES (17, 'AMT-000017', 'AMT N16');
        INSERT INTO estacao VALUES (5, 'Teste Funcional', 'Testes funcionais do produto');
        INSERT INTO tipo_defeito VALUES (1, 'Tela', NULL);
        INSERT INTO maquina VALUES (4, 'smt-01', 'Insersora');
        INSERT INTO maquina VALUES (9, 'EMB-01', NULL);
        INSERT INTO ocorrencia VALUES (1, '2026-09-28', '08:15', 'Maior', 'Reprovado', 'Tela com falha.',
            'Retido.', 'Em_analise', 'Visivel', 1, 5, 1, 4, 2);
        INSERT INTO ocorrencia VALUES (7, '2026-09-28', '22:40:10', 'Critico', 'Em_reprocesso', 'Tela apagada.',
            'Reprocesso.', 'Resolvida', 'Oculta', 17, 5, 1, 9, 2);
    """)


def test_migra_qld_preservando_ids_e_convertendo_valores(bancos, migrar, sessao):
    _qld_basico(bancos)
    rel = migrar(bancos)
    sessao.expire_all()

    assert {p.id: p.numero_serie for p in sessao.scalars(select(Produto))} == {1: "AMT-000001", 17: "AMT-000017"}
    assert sessao.get(Estacao, 5).nome == "Teste Funcional"
    assert sessao.get(TipoDefeito, 1).descricao is None

    oc = {o.id: o for o in sessao.scalars(select(Ocorrencia))}
    assert set(oc) == {1, 7}
    um, sete = oc[1], oc[7]
    assert (um.classificacao, um.situacao_produto, um.status, um.oculta) == ("MAIOR", "REPROVADO", "EM_ANALISE", False)
    assert (sete.classificacao, sete.situacao_produto, sete.status, sete.oculta) == ("CRITICO", "EM_REPROCESSO", "RESOLVIDA", True)
    # Hora digitada na tela = hora de Manaus: 08:15 -> 12:15 UTC; 22:40 -> 02:40 UTC do dia seguinte.
    assert _utc(um.ocorrida_em) == datetime(2026, 9, 28, 12, 15, tzinfo=UTC)
    assert _utc(sete.ocorrida_em) == datetime(2026, 9, 29, 2, 40, 10, tzinfo=UTC)
    # A máquina 4 da Qualidade (TAG smt-01) é o equipamento 1 da Manutenção; a 9 (EMB-01) é o 8.
    assert (um.equipamento_id, sete.equipamento_id) == (1, 8)
    assert um.responsavel_id == _usuarios(sessao)["QUA-0001"].id
    assert rel.gravadas["qld.ocorrencias"] == 2


def test_maquina_da_qualidade_sem_cadastro_na_manutencao_desfaz_tudo(bancos, migrar, sessao):
    _qld_basico(bancos)
    bancos.sql("qld", "UPDATE maquina SET nome_maquina = 'XYZ-99' WHERE id_maquina = 9")
    with pytest.raises(m.ErroMigracao, match="XYZ-99"):
        migrar(bancos)
    assert _usuarios(sessao) == {}


def test_valor_antigo_desconhecido_desfaz_tudo(bancos, migrar, sessao):
    _qld_basico(bancos)
    bancos.sql("qld", "UPDATE ocorrencia SET status_ocorrencia = 'Arquivada' WHERE id_ocorrencia = 1")
    with pytest.raises(m.ErroMigracao, match="Arquivada"):
        migrar(bancos)


# --------------------------------------------------------------------------- equivalências e duplicados
def test_mesmo_nome_com_matriculas_diferentes_so_avisa(bancos, migrar, sessao):
    bancos.usuario_mnt(1, "OP-10234", nome="Carlos Mendonça")
    bancos.sql("ras", "", ("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?)",
                           (2, "MAT-00421", "Carlos Mendonca", "c@a", "!", "Operador", 1, "2026-10-01 00:00:00")))
    rel = migrar(bancos)
    assert set(_usuarios(sessao)) == {"OP-10234", "MAT-00421"}
    assert rel.possiveis_duplicados == ["Carlos Mendonça: MAT-00421, OP-10234"]


def test_equivalencias_unem_contas_da_mesma_pessoa(bancos, engine_testes, sessao, tmp_path):
    bancos.usuario_mnt(1, "OP-10234", nome="Carlos Mendonça", senha="123456")
    bancos.sql("ras", "", ("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?)",
                           (2, "MAT-00421", "Carlos Mendonça", "c@a", "!", "Operador", 1, "2026-10-01 00:00:00")))
    csv_ = tmp_path / "equivalencias.csv"
    csv_.write_text("matricula_antiga;matricula_nova\nmat-00421 ;OP-10234\n", encoding="utf-8")

    equivalencias = m.ler_equivalencias(csv_)
    rel = m.executar(sessionmaker(bind=engine_testes), bancos.caminhos, False, equivalencias)

    us = _usuarios(sessao)
    assert set(us) == {"OP-10234"}
    assert _utc(us["OP-10234"].criado_em) == datetime(2026, 10, 1, tzinfo=UTC)  # a data mais antiga das duas contas
    assert rel.equivalencias_aplicadas == ["RAS MAT-00421 -> OP-10234"]
    assert rel.possiveis_duplicados == []


def test_equivalencias_sem_as_colunas_certas(tmp_path):
    csv_ = tmp_path / "e.csv"
    csv_.write_text("de,para\nA,B\n", encoding="utf-8")
    with pytest.raises(m.ErroMigracao, match="matricula_antiga"):
        m.ler_equivalencias(csv_)
