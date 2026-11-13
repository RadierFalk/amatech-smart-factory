"""Personas e acesso aos módulos (RBAC), portado de portal/permissoes.py.

Diferença em relação ao portal: o perfil é gravado sempre com um dos 6 valores
canônicos (constraint no banco), então não há mais adivinhação por trecho de texto.
A regra é aplicada no servidor, em cada rota, e não só escondendo telas.
"""
from dataclasses import dataclass
from enum import StrEnum


class Perfil(StrEnum):
    ADMINISTRADOR = "Administrador"
    SUPERVISOR = "Supervisor / Gestor"
    INSPETOR = "Inspetor de Qualidade"
    OPERADOR = "Operador de Produção"
    TECNICO = "Técnico de Manutenção"
    ALMOXARIFE = "Almoxarife"


PREFIXOS_MATRICULA: dict[Perfil, str] = {
    Perfil.ADMINISTRADOR: "ADM",
    Perfil.SUPERVISOR: "GES",
    Perfil.INSPETOR: "QUA",
    Perfil.OPERADOR: "OPE",
    Perfil.TECNICO: "TEC",
    Perfil.ALMOXARIFE: "ALM",
}


class Modulo(StrEnum):
    RASTREABILIDADE = "rastreabilidade"
    QUALIDADE = "qualidade"
    MANUTENCAO = "manutencao"
    DASHBOARD = "dashboard"
    USUARIOS = "usuarios"
    AUDITORIA = "auditoria"


@dataclass(frozen=True)
class ModuloERP:
    id: Modulo
    sigla: str
    nome: str
    descricao: str
    perfis: frozenset[Perfil]


P = Perfil
CATALOGO: dict[Modulo, ModuloERP] = {
    Modulo.RASTREABILIDADE: ModuloERP(
        Modulo.RASTREABILIDADE, "RAS", "Rastreabilidade e Materiais",
        "Notebooks por número de série, etapas nas estações, solicitações e baixas de material (BOM).",
        frozenset({P.ADMINISTRADOR, P.SUPERVISOR, P.OPERADOR, P.INSPETOR, P.ALMOXARIFE}),
    ),
    Modulo.QUALIDADE: ModuloERP(
        Modulo.QUALIDADE, "QLD", "Controle da Qualidade e Defeitos",
        "Ocorrências de defeito, classificação de gravidade, reprovação/reprocesso e acionamento da manutenção.",
        frozenset({P.ADMINISTRADOR, P.SUPERVISOR, P.INSPETOR, P.OPERADOR, P.ALMOXARIFE}),
    ),
    Modulo.MANUTENCAO: ModuloERP(
        Modulo.MANUTENCAO, "MNT", "Gestão da Manutenção de Ativos",
        "Máquinas por estação (TAGs), chamados, Ordens de Serviço, preventivas e MTTR/MTBF.",
        frozenset({P.ADMINISTRADOR, P.SUPERVISOR, P.TECNICO, P.OPERADOR}),
    ),
    Modulo.DASHBOARD: ModuloERP(
        Modulo.DASHBOARD, "DSH", "Dashboard Industrial e Metas",
        "Indicadores consolidados (meta, defeitos, retrabalho, paradas, perdas) e semáforo de alertas.",
        frozenset({P.ADMINISTRADOR, P.SUPERVISOR, P.OPERADOR, P.INSPETOR, P.TECNICO}),
    ),
    Modulo.USUARIOS: ModuloERP(
        Modulo.USUARIOS, "USR", "Gestão de Usuários e Acessos",
        "Cadastro de colaboradores, personas, ativação/bloqueio e senhas.",
        frozenset({P.ADMINISTRADOR}),
    ),
    Modulo.AUDITORIA: ModuloERP(
        Modulo.AUDITORIA, "AUD", "Auditoria",
        "Quem criou, alterou ou excluiu cada registro, em todos os módulos, com os valores antes e depois.",
        frozenset({P.ADMINISTRADOR, P.SUPERVISOR}),
    ),
}


def tem_acesso(perfil: Perfil | str, modulo: Modulo | str) -> bool:
    item = CATALOGO.get(Modulo(modulo))
    return item is not None and Perfil(perfil) in item.perfis


def modulos_do_perfil(perfil: Perfil | str) -> list[ModuloERP]:
    p = Perfil(perfil)
    return [m for m in CATALOGO.values() if p in m.perfis]
