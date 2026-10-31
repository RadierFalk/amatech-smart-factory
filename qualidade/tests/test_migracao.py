"""
Testes da migração do banco (migracao.py) e da independência da API em relação ao login.
Rodar:  python -m pytest tests -q
"""
import sqlite3
from pathlib import Path

import pytest

import autenticacao
import banco
import migracao
from conftest import SENHA_INICIAL, ler_tabela, criar_banco_legado

RAIZ = Path(__file__).resolve().parent.parent

LEGADO_PARA_NOVO = {
    "Ana Souza": ("ADM-0001", "Administrador"),
    "João Silva": ("OPE-0001", "Operador"),
    "Carlos Oliveira": ("ALM-0001", "Almoxarife"),
    "Maria Santos": ("QUA-0001", "Inspetor de Qualidade"),
}


def test_usuarios_antigos_viram_as_contas_novas_com_o_mesmo_id(banco_legado):
    antes = {n: i for i, n in ler_tabela(banco_legado, "SELECT id_usuario, nome_usuario FROM usuario")}

    resultado = migracao.migrar()
    assert resultado["migrado"] is True
    assert len(resultado["convertidas"]) == 4 and resultado["criadas"] == []

    depois = {
        nome: (matricula, perfil, ativo, id_usuario)
        for id_usuario, nome, matricula, perfil, ativo in ler_tabela(
            banco_legado,
            "SELECT id_usuario, nome_usuario, matricula, perfil_usuario, ativo FROM usuario"
        )
    }

    for nome, (matricula, perfil) in LEGADO_PARA_NOVO.items():
        assert depois[nome][:3] == (matricula, perfil, 1)
        assert depois[nome][3] == antes[nome]   # mesmo id_usuario: o histórico continua ligado à mesma pessoa

    # O usuário antigo que não é uma das quatro contas fica preservado, mas sem acesso
    assert depois["Visitante Antigo"][0] is None and depois["Visitante Antigo"][2] == 0


def test_ocorrencias_e_chaves_estrangeiras_preservadas(banco_legado):
    consulta = "SELECT * FROM ocorrencia ORDER BY id_ocorrencia"
    antes = ler_tabela(banco_legado, consulta)

    migracao.migrar()

    assert ler_tabela(banco_legado, consulta) == antes
    assert ler_tabela(banco_legado, "PRAGMA foreign_key_check") == []

    # cada ocorrência continua apontando para a mesma pessoa
    nomes = ler_tabela(banco_legado, """
        SELECT o.id_ocorrencia, u.nome_usuario FROM ocorrencia o
        JOIN usuario u ON u.id_usuario = o.id_usuario ORDER BY o.id_ocorrencia
    """)
    assert [n for _, n in nomes] == [
        "João Silva", "Maria Santos", "Carlos Oliveira", "Ana Souza", "Visitante Antigo", "João Silva"
    ]


def test_backup_e_feito_antes_da_migracao_e_so_uma_vez(banco_legado):
    resultado = migracao.migrar()
    backup = Path(resultado["backup"])

    assert backup.exists() and backup.parent == banco_legado.parent / "backups"

    colunas = {c[1] for c in ler_tabela(backup, "PRAGMA table_info(usuario)")}
    assert "matricula" not in colunas   # o backup é o banco como era antes
    assert ler_tabela(backup, "SELECT COUNT(*) FROM ocorrencia") == [(6,)]

    migracao.migrar()
    assert len(list((banco_legado.parent / "backups").glob("*.db"))) == 1


def test_migracao_e_idempotente(banco_legado):
    migracao.migrar()
    contas = ler_tabela(banco_legado, "SELECT id_usuario, matricula, senha_hash FROM usuario ORDER BY id_usuario")

    segunda = migracao.migrar()

    assert segunda["migrado"] is False and segunda["backup"] is None
    assert ler_tabela(banco_legado, "SELECT id_usuario, matricula, senha_hash FROM usuario ORDER BY id_usuario") == contas
    assert ler_tabela(banco_legado, "SELECT COUNT(*) FROM usuario") == [(5,)]
    assert ler_tabela(banco_legado, "SELECT COUNT(*) FROM usuario WHERE matricula IS NOT NULL") == [(4,)]


def test_matriculas_sao_unicas(banco_migrado):
    conexao = sqlite3.connect(banco_migrado)

    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "INSERT INTO usuario (nome_usuario, perfil_usuario, matricula, ativo) VALUES ('Copia', 'Operador', 'ADM-0001', 1)"
        )

    conexao.close()


def test_senhas_ficam_somente_como_hash(banco_migrado):
    for (senha_hash,) in ler_tabela(banco_migrado, "SELECT senha_hash FROM usuario WHERE matricula IS NOT NULL"):
        assert senha_hash.startswith("$argon2")
        assert SENHA_INICIAL not in senha_hash

    conexao = sqlite3.connect(banco_migrado)
    despejo = "\n".join(conexao.iterdump())
    conexao.close()
    assert SENHA_INICIAL not in despejo   # a senha em texto puro não aparece em lugar nenhum do banco


def test_senha_alterada_nao_e_sobrescrita_pela_migracao(banco_migrado, entrar):
    admin = entrar("ADM-0001")
    operador = entrar("OPE-0001")
    autenticacao.redefinir_senha(admin, operador["id_usuario"], "senha-nova-123")

    # força a migração a rodar de novo: uma das contas perde a matrícula e precisa ser refeita
    conexao = sqlite3.connect(banco_migrado)
    conexao.execute("UPDATE usuario SET matricula = NULL WHERE matricula = 'ALM-0001'")
    conexao.commit()
    conexao.close()

    resultado = migracao.migrar()
    assert resultado["migrado"] is True

    assert autenticacao.autenticar("OPE-0001", "senha-nova-123") is not None
    assert autenticacao.autenticar("OPE-0001", SENHA_INICIAL) is None
    assert autenticacao.autenticar("ALM-0001", SENHA_INICIAL) is not None   # a conta refeita volta com a senha inicial


def test_banco_sem_usuarios_antigos_recebe_as_quatro_contas(tmp_path, monkeypatch):
    caminho = tmp_path / "vazio.db"
    criar_banco_legado(caminho, com_usuarios=False)
    monkeypatch.setattr(banco, "CAMINHO_BANCO", caminho)

    resultado = migracao.migrar()

    assert len(resultado["criadas"]) == 4 and resultado["convertidas"] == []
    contas = ler_tabela(caminho, "SELECT matricula, nome_usuario, perfil_usuario FROM usuario ORDER BY matricula")
    assert contas == [
        ("ADM-0001", "Administrador", "Administrador"),
        ("ALM-0001", "Almoxarife", "Almoxarife"),
        ("OPE-0001", "Operador", "Operador"),
        ("QUA-0001", "Inspetor de Qualidade", "Inspetor de Qualidade"),
    ]


def test_falha_na_migracao_nao_deixa_o_banco_pela_metade(banco_legado, monkeypatch):
    def quebrar(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(migracao.autenticacao, "gerar_hash", quebrar)

    with pytest.raises(RuntimeError):
        migracao.migrar()

    colunas = {c[1] for c in ler_tabela(banco_legado, "PRAGMA table_info(usuario)")}
    assert colunas == {"id_usuario", "nome_usuario", "perfil_usuario"}   # nada mudou
    assert ler_tabela(banco_legado, "SELECT COUNT(*) FROM ocorrencia") == [(6,)]


# ============================================================
# A API E A INTEGRAÇÃO NÃO DEPENDEM DO LOGIN
# ============================================================

def test_api_e_integracao_nao_usam_o_login():
    for arquivo in ("api.py", "integracao.py"):
        codigo = (RAIZ / arquivo).read_text(encoding="utf-8")
        for modulo in ("autenticacao", "sessao", "permissoes", "migracao"):
            assert modulo not in codigo, f"{arquivo} não deve depender de {modulo}"


def test_api_continua_funcionando_so_com_a_chave(banco_migrado):
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient

    import api

    with TestClient(api.app) as cliente:
        assert cliente.get("/api/status").json()["status"] == "online"
        assert cliente.get("/api/ocorrencias").status_code == 401

        resposta = cliente.get("/api/ocorrencias", headers={"X-API-Key": api.CHAVE_API})
        assert resposta.status_code == 200
        assert len(resposta.json()) == 5   # as 5 visíveis (1 está oculta); nenhuma sessão de usuário envolvida
        assert "senha_hash" not in resposta.text and "matricula" not in resposta.text
