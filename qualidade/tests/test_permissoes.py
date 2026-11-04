"""
Testes das permissões por perfil (permissoes.py) e da autorização aplicada em ocorrencia.py.
Rodar:  python -m pytest tests -q
"""
import inspect

import pytest

import banco
import ocorrencia
import permissoes
from conftest import ler_tabela
from permissoes import PermissaoNegada

P = permissoes

ESPERADO = {
    "ADM-0001": set(P.TODAS_AS_PERMISSOES),
    "OPE-0001": {P.VER_DASHBOARD, P.VER_HISTORICO, P.ATUALIZAR_CADASTROS,
                 P.REGISTRAR_OCORRENCIA, P.EDITAR_OCORRENCIA, P.ABRIR_CHAMADO},
    "ALM-0001": {P.VER_DASHBOARD, P.VER_HISTORICO, P.ATUALIZAR_CADASTROS},
    "QUA-0001": {P.VER_DASHBOARD, P.VER_HISTORICO, P.ATUALIZAR_CADASTROS,
                 P.REGISTRAR_OCORRENCIA, P.EDITAR_OCORRENCIA, P.OCULTAR_OCORRENCIA, P.ABRIR_CHAMADO},
}


def dados(**mudancas):
    base = dict(
        data_ocorrencia="2026-10-28", hora_ocorrencia="10:00:00", classificacao_defeito="Maior",
        situacao_produto="Reprovado", observacao_ocorrencia="Tela sem imagem", acao_realizada="Troca da tela",
        status_ocorrencia="Aberta", id_produto=1, id_estacao=1, id_tipo_defeito=1, id_maquina=1,
    )
    base.update(mudancas)
    return base


# ============================================================
# MATRIZ
# ============================================================

def test_matriz_de_permissoes_por_perfil(entrar):
    for matricula, esperado in ESPERADO.items():
        usuario = entrar(matricula)
        obtido = {p for p in P.TODAS_AS_PERMISSOES if P.tem_permissao(usuario, p)}
        assert obtido == esperado, matricula


def test_somente_o_administrador_gerencia_usuarios(entrar):
    quem_pode = [m for m in ESPERADO if P.tem_permissao(entrar(m), P.GERENCIAR_USUARIOS)]
    assert quem_pode == ["ADM-0001"]


def test_menu_de_cada_perfil(entrar):
    assert P.paginas_permitidas(entrar("ADM-0001")) == ["Dashboard", "Registrar ocorrência", "Histórico", "Usuários"]
    assert P.paginas_permitidas(entrar("OPE-0001")) == ["Dashboard", "Registrar ocorrência", "Histórico"]
    assert P.paginas_permitidas(entrar("QUA-0001")) == ["Dashboard", "Registrar ocorrência", "Histórico"]
    assert P.paginas_permitidas(entrar("ALM-0001")) == ["Dashboard", "Histórico"]
    assert P.paginas_permitidas(None) == []


def test_sem_usuario_ou_com_perfil_desconhecido_nao_ha_permissao():
    assert not P.tem_permissao(None, P.VER_DASHBOARD)
    assert not P.tem_permissao({"perfil": "Gestor"}, P.VER_DASHBOARD)

    with pytest.raises(PermissaoNegada):
        P.exigir(None, P.VER_DASHBOARD)


# ============================================================
# REGISTRAR
# ============================================================

def test_registrar_usa_o_usuario_da_sessao(entrar, banco_migrado):
    assert "id_usuario" not in inspect.signature(ocorrencia.registrar_ocorrencia).parameters

    for matricula in ("ADM-0001", "OPE-0001", "QUA-0001"):
        usuario = entrar(matricula)
        sucesso, id_ocorrencia = ocorrencia.registrar_ocorrencia(usuario, **dados())

        assert sucesso is True
        assert banco.buscar_ocorrencia(id_ocorrencia)["id_usuario"] == usuario["id_usuario"]


def test_almoxarife_nao_registra(entrar, banco_migrado):
    antes = ler_tabela(banco_migrado, "SELECT COUNT(*) FROM ocorrencia")

    with pytest.raises(PermissaoNegada):
        ocorrencia.registrar_ocorrencia(entrar("ALM-0001"), **dados())

    assert ler_tabela(banco_migrado, "SELECT COUNT(*) FROM ocorrencia") == antes


def test_nao_da_para_registrar_em_nome_de_outro_usuario(entrar, banco_migrado):
    operador = entrar("OPE-0001")
    almoxarife = entrar("ALM-0001")

    # não existe parâmetro para escolher o responsável
    with pytest.raises(TypeError):
        ocorrencia.registrar_ocorrencia(operador, id_usuario=almoxarife["id_usuario"], **dados())

    # trocar o id no dicionário da sessão faz valer o perfil real da conta escolhida, não o do dicionário
    forjado = dict(operador, id_usuario=almoxarife["id_usuario"], perfil="Administrador")
    with pytest.raises(PermissaoNegada):
        ocorrencia.registrar_ocorrencia(forjado, **dados())

    # perfil forjado com o id correto também não vale
    with pytest.raises(PermissaoNegada):
        ocorrencia.registrar_ocorrencia(dict(almoxarife, perfil="Administrador"), **dados())

    # sem sessão, nada
    with pytest.raises(PermissaoNegada):
        ocorrencia.registrar_ocorrencia(None, **dados())


def test_registrar_ainda_valida_os_dados(entrar):
    sucesso, erros = ocorrencia.registrar_ocorrencia(entrar("OPE-0001"), **dados(observacao_ocorrencia="  "))

    assert sucesso is False and erros


# ============================================================
# EDITAR E OCULTAR
# ============================================================

def test_operador_e_inspetor_editam_mas_o_almoxarife_nao(entrar, banco_migrado):
    operador = entrar("OPE-0001")
    inspetor = entrar("QUA-0001")
    sucesso, id_ocorrencia = ocorrencia.registrar_ocorrencia(operador, **dados())

    with pytest.raises(PermissaoNegada):
        ocorrencia.editar_ocorrencia(entrar("ALM-0001"), id_ocorrencia, **dados(status_ocorrencia="Resolvida"))

    sucesso, _ = ocorrencia.editar_ocorrencia(inspetor, id_ocorrencia, **dados(status_ocorrencia="Resolvida"))
    assert sucesso is True

    registro = banco.buscar_ocorrencia(id_ocorrencia)
    assert registro["status_ocorrencia"] == "Resolvida"
    assert registro["id_usuario"] == operador["id_usuario"]   # o responsável original continua o mesmo

    sucesso, _ = ocorrencia.editar_ocorrencia(operador, id_ocorrencia, **dados(status_ocorrencia="Em_analise"))
    assert sucesso is True


def test_editar_ocorrencia_antiga_preserva_o_responsavel_historico(entrar, banco_migrado):
    inspetor = entrar("QUA-0001")
    original = banco.buscar_ocorrencia(5)   # registrada pelo usuário antigo sem acesso (Visitante Antigo)

    sucesso, _ = ocorrencia.editar_ocorrencia(inspetor, 5, **dados(status_ocorrencia="Resolvida"))

    assert sucesso is True
    assert banco.buscar_ocorrencia(5)["id_usuario"] == original["id_usuario"]


def test_ocultar_so_administrador_e_inspetor_e_sem_apagar(entrar, banco_migrado):
    for matricula in ("OPE-0001", "ALM-0001"):
        with pytest.raises(PermissaoNegada):
            ocorrencia.ocultar_ocorrencia(entrar(matricula), 1)

    assert banco.buscar_ocorrencia(1)["visibilidade_ocorrencia"] == "Visivel"

    sucesso, _ = ocorrencia.ocultar_ocorrencia(entrar("QUA-0001"), 1)
    assert sucesso is True
    sucesso, _ = ocorrencia.ocultar_ocorrencia(entrar("ADM-0001"), 2)
    assert sucesso is True

    # continua no banco, só deixa de aparecer
    assert banco.buscar_ocorrencia(1)["visibilidade_ocorrencia"] == "Oculta"
    assert ler_tabela(banco_migrado, "SELECT COUNT(*) FROM ocorrencia") == [(6,)]


# ============================================================
# CHAMADO NA MANUTENÇÃO
# ============================================================

def test_abrir_chamado_exige_a_permissao_propria(entrar, banco_migrado, monkeypatch):
    chamadas = []
    monkeypatch.setattr(ocorrencia.integracao, "notificar_ocorrencia",
                        lambda id_ocorrencia, abrir_chamado: chamadas.append((id_ocorrencia, abrir_chamado)) or [])

    operador = entrar("OPE-0001")
    ocorrencia.notificar_setores(operador, 1, abrir_chamado=True)
    assert chamadas == [(1, True)]

    with pytest.raises(PermissaoNegada):
        ocorrencia.notificar_setores(entrar("ALM-0001"), 1, abrir_chamado=False)

    # ajuste futuro: tirar a permissão do perfil basta para bloquear, sem mexer nas telas
    monkeypatch.setitem(P.MATRIZ, P.OPERADOR, frozenset(P.MATRIZ[P.OPERADOR] - {P.ABRIR_CHAMADO}))

    with pytest.raises(PermissaoNegada):
        ocorrencia.notificar_setores(operador, 1, abrir_chamado=True)

    ocorrencia.notificar_setores(operador, 1, abrir_chamado=False)   # avisar a Rastreabilidade continua permitido
    assert chamadas[-1] == (1, False)


# ============================================================
# CONSULTAS CONTINUAM IGUAIS
# ============================================================

def test_consultas_e_responsaveis_antigos_aparecem(entrar, banco_migrado):
    todas = ocorrencia.listar_ocorrencias()

    assert len(todas) == 5   # 6 no banco, 1 oculta
    assert {o["nome_usuario"] for o in todas} == {"João Silva", "Maria Santos", "Carlos Oliveira", "Visitante Antigo"}
