"""Migração dos bancos SQLite antigos para o PostgreSQL da API única.

Uso (a partir de backend/, depois de `alembic upgrade head`):
    python -m scripts.migrar_sqlite --simular     # faz tudo, mostra o relatório e desfaz
    python -m scripts.migrar_sqlite               # grava

Os caminhos dos bancos têm padrão (arquivos do repositório) e podem ser trocados por argumento
(--mnt, --qld, --ras, --dsh, --portal). Arquivo inexistente é avisado e pulado.

Regras (HANDOFF_POSTGRES.md, seções 4.2 e 4.3):
- Os SQLite são abertos só para leitura.
- Tudo roda numa transação: qualquer erro desfaz tudo; --simular desfaz no final.
- Pode rodar várias vezes: usuários são unificados pela matrícula e gravados com upsert;
  as tabelas de mnt mantêm os IDs de origem e também usam upsert.
- Senhas nunca vão para o relatório nem são gravadas em texto puro.

Uma função por schema (migrar_usr, migrar_mnt, migrar_qld). Os schemas ras e dsh entram aqui quando
os modelos deles existirem; migrar_usr já lê os usuários desses bancos e devolve o mapa de IDs.

Contas da mesma pessoa com matrículas diferentes (ex.: MAT-00421 na Rastreabilidade e OP-10234 na
Manutenção) só são unidas com --equivalencias; o relatório lista os nomes repetidos para ajudar a decidir.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.core.rbac import Perfil
from app.core.seguranca import gerar_hash, verificar_senha
from app.core.tempo import FUSO_FABRICA
from app.modulos.manutencao.constantes import STATUS_ATIVOS, StatusChamado
from app.modulos.manutencao.modelos import Chamado, ChamadoPeca, Equipamento, HistoricoStatus, Peca
from app.modulos.qualidade.constantes import LEGADO_CLASSIFICACAO, LEGADO_SITUACAO, LEGADO_STATUS
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.usuarios.modelos import Usuario
from scripts.seed_demo import PERSONAS, SENHA_DEMO

RAIZ_REPO = Path(__file__).resolve().parents[2]

CAMINHOS_PADRAO = {
    "portal": RAIZ_REPO / "portal" / "banco" / "erp_usuarios.db",
    "mnt": RAIZ_REPO / "manutencao" / "manutencao.db",
    "qld": RAIZ_REPO / "qualidade" / "banco" / "controle_qualidade.db",
    "ras": RAIZ_REPO / "rastreabilidade" / "database" / "amatech.db",
    "dsh": RAIZ_REPO / "dashboard" / "database" / "banco.db",
}

# Ordem de preferência para nome e perfil de quem não é persona (seção 4.3, regra 2).
ORDEM_MODULOS = ("mnt", "qld", "ras", "dsh")

# Fuso em que cada origem grava as datas. O Dashboard usa datetime('now', 'localtime'); os demais, UTC.
FUSO_ORIGEM = {"portal": UTC, "mnt": UTC, "qld": UTC, "ras": UTC, "dsh": FUSO_FABRICA}

PERSONAS_POR_MATRICULA = {m: (nome, perfil) for m, nome, perfil in PERSONAS}

TABELAS_COM_SEQUENCIA = ("usr.usuarios", "mnt.equipamentos", "mnt.pecas", "mnt.chamados",
                         "mnt.chamado_pecas", "mnt.historico_status",
                         "qld.produtos", "qld.estacoes", "qld.tipos_defeito", "qld.ocorrencias")


class ErroMigracao(Exception):
    """Problema que impede a migração; a transação é desfeita."""


# --------------------------------------------------------------------------- relatório
@dataclass
class Relatorio:
    lidas: dict[str, int] = field(default_factory=dict)          # "mnt.usuarios" -> linhas
    origens_ausentes: list[str] = field(default_factory=list)
    usuarios_criados: list[str] = field(default_factory=list)
    usuarios_atualizados: list[str] = field(default_factory=list)
    usuarios_sem_mudanca: list[str] = field(default_factory=list)
    conflitos: list[str] = field(default_factory=list)
    senhas_convertidas: list[str] = field(default_factory=list)  # só matrículas
    senhas_sem_login: list[str] = field(default_factory=list)    # só matrículas
    ignorados: list[str] = field(default_factory=list)
    gravadas: dict[str, int] = field(default_factory=dict)       # "mnt.chamados" -> linhas
    pecas_somadas: int = 0
    pendencias: list[str] = field(default_factory=list)          # decisões para o dono do projeto
    equivalencias_aplicadas: list[str] = field(default_factory=list)
    possiveis_duplicados: list[str] = field(default_factory=list)  # mesmo nome, matrículas diferentes

    def texto(self, simulacao: bool) -> str:
        linhas = ["=" * 70, "MIGRAÇÃO SQLite -> PostgreSQL" + ("  (SIMULAÇÃO: nada foi gravado)" if simulacao else ""),
                  "=" * 70, "", "Linhas lidas por origem:"]
        linhas += [f"  {k:<34} {v:>6}" for k, v in sorted(self.lidas.items())] or ["  (nenhuma)"]
        if self.origens_ausentes:
            linhas += ["", "Origens não encontradas (puladas):"] + [f"  - {o}" for o in self.origens_ausentes]
        linhas += ["", "Usuários (usr.usuarios):",
                   f"  criados: {len(self.usuarios_criados)}  {', '.join(self.usuarios_criados)}",
                   f"  atualizados: {len(self.usuarios_atualizados)}  {', '.join(self.usuarios_atualizados)}",
                   f"  sem mudança: {len(self.usuarios_sem_mudanca)}"]
        secoes = [
            ("Conflitos resolvidos", self.conflitos),
            ("Senhas em texto puro convertidas para Argon2 (matrículas)", self.senhas_convertidas),
            ("Contas sem login possível: hash inválido ou de formato não suportado (matrículas)", self.senhas_sem_login),
            ("Equivalências de matrícula aplicadas (--equivalencias)", self.equivalencias_aplicadas),
            ("Possíveis duplicados: mesmo nome com matrículas diferentes (nada foi unido; "
             "use --equivalencias se forem a mesma pessoa)", self.possiveis_duplicados),
            ("Registros ignorados", self.ignorados),
        ]
        for titulo, itens in secoes:
            if itens:
                linhas += ["", f"{titulo}:"] + [f"  - {i}" for i in itens]
        linhas += ["", "Linhas gravadas no destino:"]
        linhas += [f"  {k:<34} {v:>6}" for k, v in sorted(self.gravadas.items())] or ["  (nenhuma)"]
        if self.pecas_somadas:
            linhas.append(f"  (mnt.chamado_pecas: {self.pecas_somadas} linha(s) repetida(s) somada(s) à mesma peça)")
        if self.pendencias:
            linhas += ["", "PENDÊNCIAS (decisão do dono do projeto):"] + [f"  ! {p}" for p in self.pendencias]
        return "\n".join(linhas)


# --------------------------------------------------------------------------- utilitários
def abrir_somente_leitura(caminho: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def normalizar_matricula(valor: str | None) -> str:
    return "".join((valor or "").split()).upper()


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def perfil_por_texto(texto: str | None) -> Perfil | None:
    """Traduz o perfil/cargo de qualquer sistema antigo para uma das 6 personas (None se não reconhecer)."""
    t = _sem_acento((texto or "").strip())
    if not t:
        return None
    for perfil in Perfil:
        if t == _sem_acento(perfil.value):
            return perfil
    regras = [  # a ordem importa: "Supervisor de produção" não pode cair em "operador"
        ("admin", Perfil.ADMINISTRADOR),
        ("supervisor", Perfil.SUPERVISOR), ("gestor", Perfil.SUPERVISOR), ("diretoria", Perfil.SUPERVISOR),
        ("inspetor", Perfil.INSPETOR), ("qualidade", Perfil.INSPETOR),
        ("tecnico", Perfil.TECNICO), ("manutencao", Perfil.TECNICO),
        ("almox", Perfil.ALMOXARIFE),
        ("operador", Perfil.OPERADOR), ("integracao", Perfil.OPERADOR),
    ]
    return next((p for chave, p in regras if chave in t), None)


def para_datahora(valor, fuso=UTC) -> datetime | None:
    """Texto do SQLite ('2026-10-25 20:08:40', ISO com 'T', com ou sem fração) -> datetime em UTC."""
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        dt = valor
    else:
        try:
            dt = datetime.fromisoformat(str(valor).strip())
        except ValueError as e:
            raise ErroMigracao(f"Data em formato desconhecido: {valor!r}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=fuso)
    return dt.astimezone(UTC)


def _mesmo_instante(a: datetime | None, b: datetime | None) -> bool:
    if a is None or b is None:
        return a is b
    a = a.replace(tzinfo=UTC) if a.tzinfo is None else a
    b = b.replace(tzinfo=UTC) if b.tzinfo is None else b
    return a == b


def _texto_puro(senha: str | None) -> bool:
    """Senha gravada sem hash. Hashes conhecidos usam '$' (argon2, pbkdf2, sha256$); '!' bloqueia o login."""
    if not senha or senha.startswith("!") or "$" in senha:
        return False
    eh_hex_sha256 = len(senha) == 64 and all(c in "0123456789abcdef" for c in senha.lower())
    return not eh_hex_sha256


def _upsert(sessao: Session, tabela, valores: dict, chave: list[str], atualizar: list[str]):
    """INSERT ... ON CONFLICT (chave) DO UPDATE, no PostgreSQL (e no SQLite dos testes locais)."""
    dialeto = postgresql if sessao.get_bind().dialect.name == "postgresql" else sqlite
    stmt = dialeto.insert(tabela).values(**valores)
    stmt = stmt.on_conflict_do_update(index_elements=chave, set_={c: stmt.excluded[c] for c in atualizar})
    sessao.execute(stmt)


# --------------------------------------------------------------------------- leitura dos usuários
@dataclass
class UsuarioOrigem:
    origem: str
    id_antigo: int
    matricula: str
    nome: str
    perfil_texto: str
    senha: str
    ativo: bool
    criado_em: datetime | None


_CONSULTAS_USUARIOS: dict[str, str] = {
    "portal": "SELECT id, matricula, nome, perfil, senha_hash, ativo, criado_em FROM usuarios",
    "mnt": "SELECT id, matricula, nome, perfil, senha_hash, ativo, criado_em FROM usuarios",
    "qld": ("SELECT id_usuario, matricula, nome_usuario, perfil_usuario, senha_hash, ativo, data_criacao "
            "FROM usuario"),
    "ras": "SELECT id, matricula, nome, cargo, senha_hash, ativo, criado_em FROM usuarios",
    # O Dashboard não tem matrícula: o login (ex.: "supervisor") faz esse papel.
    "dsh": ("SELECT u.id_usuario, u.login, u.nome, p.nome, u.senha_hash, u.ativo, u.criado_em "
            "FROM usuario u LEFT JOIN perfil p ON p.id_perfil = u.id_perfil"),
}


def ler_equivalencias(caminho: Path) -> dict[str, str]:
    """CSV com cabeçalho `matricula_antiga,matricula_nova` (separador , ou ;): une contas da mesma pessoa."""
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        primeira = arquivo.readline()
        arquivo.seek(0)
        leitor = csv.DictReader(arquivo, delimiter=";" if ";" in primeira else ",")
        faltando = {"matricula_antiga", "matricula_nova"} - set(leitor.fieldnames or [])
        if faltando:
            raise ErroMigracao(f"{caminho}: faltam as colunas {', '.join(sorted(faltando))}")
        pares = {}
        for linha in leitor:
            antiga = normalizar_matricula(linha["matricula_antiga"])
            nova = normalizar_matricula(linha["matricula_nova"])
            if antiga and nova and antiga != nova:
                pares[antiga] = nova
    return pares


def ler_usuarios(origem: str, conn: sqlite3.Connection, rel: Relatorio,
                 equivalencias: dict[str, str] | None = None) -> list[UsuarioOrigem]:
    linhas = conn.execute(_CONSULTAS_USUARIOS[origem]).fetchall()
    rel.lidas[f"{origem}.usuarios"] = len(linhas)
    lidos = []
    for id_antigo, matricula, nome, perfil, senha, ativo, criado in linhas:
        mat = normalizar_matricula(matricula)
        if equivalencias and mat in equivalencias:
            rel.equivalencias_aplicadas.append(f"{origem.upper()} {mat} -> {equivalencias[mat]}")
            mat = equivalencias[mat]
        if not mat:
            rel.ignorados.append(f"{origem} usuário id {id_antigo} ({nome}): sem matrícula")
            continue
        if len(mat) > 20:
            rel.ignorados.append(f"{origem} usuário id {id_antigo}: matrícula {mat!r} passa de 20 caracteres")
            continue
        lidos.append(UsuarioOrigem(origem, id_antigo, mat, (nome or "").strip(), (perfil or "").strip(),
                                   senha or "", bool(ativo), para_datahora(criado, FUSO_ORIGEM[origem])))
    return lidos


# --------------------------------------------------------------------------- usr
def _escolher_senha(mat: str, registros: list[UsuarioOrigem], hash_atual: str | None, rel: Relatorio) -> str:
    """Regra 3. Se o hash já gravado no destino aceita a senha esperada, ele é mantido (idempotência)."""
    def converter(senha_texto: str) -> str:
        if hash_atual and verificar_senha(senha_texto, hash_atual):
            return hash_atual
        return gerar_hash(senha_texto)

    if mat in PERSONAS_POR_MATRICULA:
        return converter(SENHA_DEMO)
    por_ordem = sorted(registros, key=lambda r: ORDEM_MODULOS.index(r.origem) if r.origem in ORDEM_MODULOS else -1)
    argon = next((r.senha for r in por_ordem if r.senha.startswith("$argon2")), None)
    if argon:
        return argon
    texto = next((r.senha for r in por_ordem if _texto_puro(r.senha)), None)
    if texto is not None:
        rel.senhas_convertidas.append(mat)
        return converter(texto)
    rel.senhas_sem_login.append(mat)
    return next((r.senha for r in por_ordem if r.senha), "!")


def _consolidar(mat: str, registros: list[UsuarioOrigem], rel: Relatorio) -> tuple[str, str, bool, datetime | None]:
    """Nome, perfil, ativo e criado_em de uma matrícula (regras 1, 2, 4 e 5)."""
    por_origem = {r.origem: r for r in registros}
    modulos = [por_origem[o] for o in ORDEM_MODULOS if o in por_origem]

    if mat in PERSONAS_POR_MATRICULA:
        nome_persona, perfil_persona = PERSONAS_POR_MATRICULA[mat]
        portal = por_origem.get("portal")
        nome = portal.nome if portal and portal.nome else nome_persona
        perfil = (perfil_por_texto(portal.perfil_texto) if portal else None) or perfil_persona
        fonte = "portal" if portal else "persona"
    else:
        nome = next((r.nome for r in modulos if r.nome), mat)
        perfil = next((p for p in (perfil_por_texto(r.perfil_texto) for r in modulos) if p), None)
        fonte = "módulos"
        if perfil is None:
            perfil = Perfil.OPERADOR
            rel.conflitos.append(f"{mat}: perfil não reconhecido em nenhuma origem; usado {perfil.value}")

    for r in registros:
        p = perfil_por_texto(r.perfil_texto)
        if r.perfil_texto and p != perfil:
            rel.conflitos.append(f"{mat}: perfil {r.perfil_texto!r} em {r.origem.upper()}; mantido "
                                 f"{perfil.value!r} ({fonte})")
        if r.nome and r.nome != nome:
            rel.conflitos.append(f"{mat}: nome {r.nome!r} em {r.origem.upper()}; mantido {nome!r} ({fonte})")

    ativo = all(r.ativo for r in registros)
    if not ativo and any(r.ativo for r in registros):
        inativos = ", ".join(r.origem.upper() for r in registros if not r.ativo)
        rel.conflitos.append(f"{mat}: inativo em {inativos}; gravado como inativo")
    datas = [r.criado_em for r in registros if r.criado_em]
    return nome, perfil.value, ativo, min(datas) if datas else None


def _avisar_duplicados(por_matricula: dict[str, list[UsuarioOrigem]], rel: Relatorio) -> None:
    """Mesmo nome (sem acento, sem diferenciar maiúsculas) em matrículas diferentes: talvez a mesma pessoa."""
    por_nome: dict[str, set[str]] = defaultdict(set)
    rotulo: dict[str, str] = {}
    for mat, registros in por_matricula.items():
        for r in registros:
            chave = " ".join(_sem_acento(r.nome).split())
            if chave:
                por_nome[chave].add(mat)
                rotulo.setdefault(chave, r.nome)
    for chave, mats in sorted(por_nome.items()):
        if len(mats) > 1:
            rel.possiveis_duplicados.append(f"{rotulo[chave]}: {', '.join(sorted(mats))}")


def migrar_usr(sessao: Session, conexoes: dict[str, sqlite3.Connection], rel: Relatorio,
               equivalencias: dict[str, str] | None = None) -> dict[tuple[str, int], int]:
    """Unifica os usuários de todas as origens em usr.usuarios. Devolve (origem, id_antigo) -> usr.usuarios.id."""
    por_matricula: dict[str, list[UsuarioOrigem]] = defaultdict(list)
    for origem in ("portal", *ORDEM_MODULOS):
        if origem in conexoes:
            for u in ler_usuarios(origem, conexoes[origem], rel, equivalencias):
                por_matricula[u.matricula].append(u)
    _avisar_duplicados(por_matricula, rel)

    tabela = Usuario.__table__
    mapa: dict[tuple[str, int], int] = {}
    for mat in sorted(por_matricula):
        registros = por_matricula[mat]
        nome, perfil, ativo, criado_em = _consolidar(mat, registros, rel)
        atual = sessao.execute(select(tabela).where(tabela.c.matricula == mat)).mappings().first()
        senha = _escolher_senha(mat, registros, atual["senha_hash"] if atual else None, rel)
        valores = {"matricula": mat, "nome": nome[:100], "senha_hash": senha, "perfil": perfil, "ativo": ativo}
        if criado_em:
            valores["criado_em"] = criado_em
        elif atual:
            valores["criado_em"] = atual["criado_em"]  # mantém a data que já existe

        if atual is None:
            rel.usuarios_criados.append(mat)
        elif all(_mesmo_instante(atual[k], v) if k == "criado_em" else atual[k] == v for k, v in valores.items()):
            rel.usuarios_sem_mudanca.append(mat)
        else:
            rel.usuarios_atualizados.append(mat)
        _upsert(sessao, tabela, valores, ["matricula"], [c for c in valores if c != "matricula"])

        novo_id = sessao.scalar(select(tabela.c.id).where(tabela.c.matricula == mat))
        for r in registros:
            mapa[(r.origem, r.id_antigo)] = novo_id
    rel.gravadas["usr.usuarios"] = len(por_matricula)
    return mapa


# --------------------------------------------------------------------------- mnt
def _usuario(mapa: dict[tuple[str, int], int], id_antigo: int | None, onde: str, origem: str = "mnt") -> int | None:
    if id_antigo is None:
        return None
    try:
        return mapa[(origem, id_antigo)]
    except KeyError:
        raise ErroMigracao(f"{onde}: usuário id {id_antigo} não existe (ou não tem matrícula) "
                           f"nos usuários de {origem.upper()}") from None


def _conferir_ids_livres(sessao: Session, modelo, coluna: str, pares: list[tuple[int, str]]) -> None:
    """O destino pode ter dados do seed_demo com outros IDs: aí o upsert por ID colidiria com a chave única.

    `pares` = (id na origem, valor da chave única já normalizado)."""
    tabela = modelo.__table__
    existentes = dict(sessao.execute(select(tabela.c[coluna], tabela.c.id)).all())
    divergentes = [f"{chave} (origem id {id_}, destino id {existentes[chave]})"
                   for id_, chave in pares if chave in existentes and existentes[chave] != id_]
    if divergentes:
        raise ErroMigracao(f"{tabela.fullname} já tem registros com outros IDs: {'; '.join(divergentes)}. "
                           "Migre para um banco vazio (sem o seed_demo).")


def migrar_mnt(sessao: Session, conn: sqlite3.Connection, mapa: dict[tuple[str, int], int], rel: Relatorio) -> None:
    def ler(tabela: str) -> list[sqlite3.Row]:
        linhas = conn.execute(f"SELECT * FROM {tabela} ORDER BY id").fetchall()  # noqa: S608 (nome fixo)
        rel.lidas[f"mnt.{tabela}"] = len(linhas)
        return linhas

    equipamentos, pecas = ler("equipamentos"), ler("pecas")
    chamados, trocas, historico = ler("chamados_manutencao"), ler("chamado_pecas_trocadas"), ler("historico_status")
    _conferir_ids_livres(sessao, Equipamento, "codigo_tag", [(e["id"], e["codigo_tag"].strip().upper()) for e in equipamentos])
    _conferir_ids_livres(sessao, Peca, "codigo_peca", [(p["id"], p["codigo_peca"].strip().upper()) for p in pecas])

    colunas_eqp = ["codigo_tag", "nome", "setor", "posto_trabalho", "status_operacional", "ativo"]
    for e in equipamentos:
        valores = {"id": e["id"], "codigo_tag": e["codigo_tag"].strip().upper(), "nome": e["nome"],
                   "setor": e["setor"], "posto_trabalho": e["posto_trabalho"],
                   "status_operacional": e["status_operacional"], "ativo": bool(e["ativo"])}
        _upsert(sessao, Equipamento.__table__, valores, ["id"], colunas_eqp)
    rel.gravadas["mnt.equipamentos"] = len(equipamentos)

    for p in pecas:
        valores = {"id": p["id"], "codigo_peca": p["codigo_peca"].strip().upper(), "nome": p["nome"],
                   "unidade_medida": p["unidade_medida"], "ativo": bool(p["ativo"])}
        _upsert(sessao, Peca.__table__, valores, ["id"], ["codigo_peca", "nome", "unidade_medida", "ativo"])
    rel.gravadas["mnt.pecas"] = len(pecas)

    # RN02: no máximo uma OS ativa por máquina. Se a origem tiver mais, fica a mais antiga e as outras
    # são deixadas de fora (com tudo o que depende delas) até o dono do projeto decidir.
    ativas: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for c in chamados:
        if c["status_chamado"] in STATUS_ATIVOS:
            ativas[c["equipamento_id"]].append(c)
    fora: set[int] = set()
    for equipamento_id, lista in ativas.items():
        if len(lista) > 1:
            mantida, *extras = sorted(lista, key=lambda c: (c["data_hora_abertura"], c["id"]))
            fora.update(c["id"] for c in extras)
            rel.pendencias.append(
                f"Máquina id {equipamento_id} tem {len(lista)} OS ativas (RN02). Migrada a OS #{mantida['id']}; "
                f"NÃO migradas: {', '.join('#' + str(c['id']) for c in extras)}. Qual manter?")

    colunas_chamado = [col.name for col in Chamado.__table__.columns if col.name != "id"]
    gravados = 0
    for c in chamados:
        if c["id"] in fora:
            continue
        onde = f"chamado #{c['id']}"
        cancelado = c["status_chamado"] == StatusChamado.CANCELADO
        origem_sistema = (c["origem_sistema"] or "").strip().lower() or None
        valores = {
            "id": c["id"],
            "equipamento_id": c["equipamento_id"],
            "operador_abertura_id": _usuario(mapa, c["operador_abertura_id"], onde),
            "tecnico_responsavel_id": _usuario(mapa, c["tecnico_responsavel_id"], onde),
            "prioridade": c["prioridade"],
            "tipo_manutencao": c["tipo_manutencao"],
            "status_chamado": c["status_chamado"],
            "descricao_falha": c["descricao_falha"],
            # O sistema antigo gravava o motivo do cancelamento no diagnóstico.
            "diagnostico_tecnico": None if cancelado else c["diagnostico_tecnico"],
            "motivo_cancelamento": c["diagnostico_tecnico"] if cancelado else None,
            "causa_raiz": c["causa_raiz"],
            "data_hora_abertura": para_datahora(c["data_hora_abertura"]),
            "data_hora_inicio_atendimento": para_datahora(c["data_hora_inicio_atendimento"]),
            "data_hora_fim_atendimento": para_datahora(c["data_hora_fim_atendimento"]),
            "downtime_minutos": c["downtime_minutos"],
            "origem_sistema": origem_sistema,
            "id_externo": c["id_externo"],
        }
        _upsert(sessao, Chamado.__table__, valores, ["id"], colunas_chamado)
        gravados += 1
    rel.gravadas["mnt.chamados"] = gravados

    # Agora há UNIQUE (chamado_id, peca_id): linhas repetidas da mesma peça na mesma OS são somadas.
    somadas: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for t in trocas:
        if t["chamado_id"] in fora:
            continue
        somadas[(t["chamado_id"], t["peca_id"])] += Decimal(str(t["quantidade"]))
    rel.pecas_somadas = sum(1 for t in trocas if t["chamado_id"] not in fora) - len(somadas)
    for (chamado_id, peca_id), quantidade in somadas.items():
        valores = {"chamado_id": chamado_id, "peca_id": peca_id, "quantidade": quantidade}
        _upsert(sessao, ChamadoPeca.__table__, valores, ["chamado_id", "peca_id"], ["quantidade"])
    rel.gravadas["mnt.chamado_pecas"] = len(somadas)

    # Linhas com status_anterior = status_novo também entram: são histórico.
    colunas_hist = ["equipamento_id", "chamado_id", "usuario_id", "status_anterior", "status_novo", "alterado_em"]
    gravados = 0
    for h in historico:
        if h["chamado_id"] in fora:
            rel.ignorados.append(f"mnt.historico_status id {h['id']}: pertence à OS #{h['chamado_id']}, não migrada")
            continue
        valores = {"id": h["id"], "equipamento_id": h["equipamento_id"], "chamado_id": h["chamado_id"],
                   "usuario_id": _usuario(mapa, h["usuario_id"], f"historico_status id {h['id']}"),
                   "status_anterior": h["status_anterior"], "status_novo": h["status_novo"],
                   "alterado_em": para_datahora(h["alterado_em"])}
        _upsert(sessao, HistoricoStatus.__table__, valores, ["id"], colunas_hist)
        gravados += 1
    rel.gravadas["mnt.historico_status"] = gravados


# --------------------------------------------------------------------------- qld
def _legado(tabela: dict, valor, onde: str) -> str:
    try:
        return tabela[(valor or "").strip()].value
    except KeyError:
        raise ErroMigracao(f"{onde}: valor {valor!r} desconhecido (esperado um de {', '.join(tabela)})") from None


def migrar_qld(sessao: Session, conn: sqlite3.Connection, mapa: dict[tuple[str, int], int], rel: Relatorio) -> None:
    """Produtos, estações, tipos de defeito e ocorrências, com os IDs de origem.

    A tabela maquina da Qualidade guardava a TAG; a ocorrência passa a apontar para mnt.equipamentos.
    Por isso migrar_mnt (ou o cadastro das máquinas) tem que vir antes."""
    def ler(tabela: str) -> list[sqlite3.Row]:
        linhas = conn.execute(f"SELECT * FROM {tabela}").fetchall()  # noqa: S608 (nome fixo)
        rel.lidas[f"qld.{tabela}"] = len(linhas)
        return linhas

    produtos, estacoes, tipos = ler("produto"), ler("estacao"), ler("tipo_defeito")
    maquinas, ocorrencias = ler("maquina"), ler("ocorrencia")

    serie = {p["id_produto"]: p["numero_serie_produto"].strip().upper() for p in produtos}
    _conferir_ids_livres(sessao, Produto, "numero_serie", list(serie.items()))
    _conferir_ids_livres(sessao, Estacao, "nome", [(e["id_estacao"], e["nome_estacao"].strip()) for e in estacoes])
    _conferir_ids_livres(sessao, TipoDefeito, "nome", [(t["id_tipo_defeito"], t["nome_tipo_defeito"].strip()) for t in tipos])

    for p in produtos:
        valores = {"id": p["id_produto"], "numero_serie": serie[p["id_produto"]], "modelo": p["modelo_produto"].strip()}
        _upsert(sessao, Produto.__table__, valores, ["id"], ["numero_serie", "modelo"])
    rel.gravadas["qld.produtos"] = len(produtos)

    for linhas, modelo, prefixo, chave in ((estacoes, Estacao, "estacao", "qld.estacoes"),
                                           (tipos, TipoDefeito, "tipo_defeito", "qld.tipos_defeito")):
        for r in linhas:
            valores = {"id": r[f"id_{prefixo}"], "nome": r[f"nome_{prefixo}"].strip(),
                       "descricao": (r[f"descricao_{prefixo}"] or "").strip() or None}
            _upsert(sessao, modelo.__table__, valores, ["id"], ["nome", "descricao"])
        rel.gravadas[chave] = len(linhas)

    # Máquina da Qualidade (TAG) -> mnt.equipamentos.id
    tags = dict(sessao.execute(select(Equipamento.codigo_tag, Equipamento.id)).all())
    maquina_para_equipamento: dict[int, int] = {}
    sem_cadastro = []
    for mq in maquinas:
        tag = mq["nome_maquina"].strip().upper()
        if tag in tags:
            maquina_para_equipamento[mq["id_maquina"]] = tags[tag]
        else:
            sem_cadastro.append(tag)
    usadas_sem_cadastro = {o["id_maquina"] for o in ocorrencias} - set(maquina_para_equipamento)
    if usadas_sem_cadastro:
        raise ErroMigracao(
            f"Máquinas da Qualidade sem cadastro na Manutenção: {', '.join(sorted(sem_cadastro))}. "
            "Cadastre essas TAGs em mnt.equipamentos (ou migre o banco da Manutenção junto) e rode de novo.")
    if sem_cadastro:
        rel.ignorados.append(f"qld.maquina sem ocorrências e sem cadastro na Manutenção: {', '.join(sem_cadastro)}")

    colunas = [c.name for c in Ocorrencia.__table__.columns if c.name != "id"]
    for o in ocorrencias:
        onde = f"ocorrência #{o['id_ocorrencia']}"
        # Data e hora da tela: hora da fábrica (Manaus).
        ocorrida_em = para_datahora(f"{o['data_ocorrencia']} {o['hora_ocorrencia']}", FUSO_FABRICA)
        valores = {
            "id": o["id_ocorrencia"],
            "ocorrida_em": ocorrida_em,
            "classificacao": _legado(LEGADO_CLASSIFICACAO, o["classificacao_defeito"], onde),
            "situacao_produto": _legado(LEGADO_SITUACAO, o["situacao_produto"], onde),
            "status": _legado(LEGADO_STATUS, o["status_ocorrencia"], onde),
            "observacao": (o["observacao_ocorrencia"] or "").strip(),
            "acao_realizada": (o["acao_realizada"] or "").strip(),
            "oculta": (o["visibilidade_ocorrencia"] or "").strip().lower() == "oculta",
            "produto_id": o["id_produto"],
            "estacao_id": o["id_estacao"],
            "tipo_defeito_id": o["id_tipo_defeito"],
            "equipamento_id": maquina_para_equipamento[o["id_maquina"]],
            "responsavel_id": _usuario(mapa, o["id_usuario"], onde, origem="qld"),
        }
        _upsert(sessao, Ocorrencia.__table__, valores, ["id"], colunas)
    rel.gravadas["qld.ocorrencias"] = len(ocorrencias)


# --------------------------------------------------------------------------- execução
def ajustar_sequencias(sessao: Session) -> None:
    """Depois de inserir com IDs explícitos, o próximo ID gerado tem que vir depois do maior existente."""
    if sessao.get_bind().dialect.name != "postgresql":
        return
    for tabela in TABELAS_COM_SEQUENCIA:
        sessao.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
            f"COALESCE((SELECT max(id) FROM {tabela}), 1), (SELECT max(id) FROM {tabela}) IS NOT NULL)"
        ))


def migrar(sessao: Session, caminhos: dict[str, Path], rel: Relatorio,
           equivalencias: dict[str, str] | None = None) -> None:
    """Executa a migração inteira na sessão recebida, sem commit."""
    conexoes: dict[str, sqlite3.Connection] = {}
    try:
        for origem, caminho in caminhos.items():
            if caminho and Path(caminho).is_file():
                conexoes[origem] = abrir_somente_leitura(Path(caminho))
            else:
                rel.origens_ausentes.append(f"{origem}: {caminho}")
        mapa = migrar_usr(sessao, conexoes, rel, equivalencias or {})
        if "mnt" in conexoes:
            migrar_mnt(sessao, conexoes["mnt"], mapa, rel)
        if "qld" in conexoes:
            sessao.flush()  # as máquinas da Manutenção precisam estar visíveis para mapear as TAGs
            migrar_qld(sessao, conexoes["qld"], mapa, rel)
        sessao.flush()
        ajustar_sequencias(sessao)
    finally:
        for conn in conexoes.values():
            conn.close()


def executar(fabrica_sessao: Callable[[], Session], caminhos: dict[str, Path], simular: bool,
             equivalencias: dict[str, str] | None = None) -> Relatorio:
    """Uma transação só: commit no final, ou rollback em --simular e em qualquer erro."""
    rel = Relatorio()
    with fabrica_sessao() as sessao:
        try:
            migrar(sessao, caminhos, rel, equivalencias)
        except Exception:
            sessao.rollback()
            raise
        if simular:
            sessao.rollback()
        else:
            sessao.commit()
    return rel


def contar(sessao: Session, modelo) -> int:
    return sessao.scalar(select(func.count()).select_from(modelo)) or 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migra os bancos SQLite antigos para o PostgreSQL da API única.")
    for origem, padrao in CAMINHOS_PADRAO.items():
        parser.add_argument(f"--{origem}", type=Path, default=padrao, help=f"banco SQLite ({origem}); padrão: {padrao}")
    parser.add_argument("--simular", action="store_true", help="faz tudo e desfaz no final (só o relatório)")
    parser.add_argument("--equivalencias", type=Path,
                        help="CSV matricula_antiga,matricula_nova: une contas da mesma pessoa em sistemas diferentes")
    args = parser.parse_args(argv)

    from app.core.db import SessaoLocal  # só conecta quando roda de verdade

    caminhos = {origem: getattr(args, origem) for origem in CAMINHOS_PADRAO}
    try:
        equivalencias = ler_equivalencias(args.equivalencias) if args.equivalencias else None
        rel = executar(SessaoLocal, caminhos, args.simular, equivalencias)
    except ErroMigracao as e:
        print(f"ERRO: {e}\nNada foi gravado.", file=sys.stderr)
        return 1
    print(rel.texto(args.simular))
    return 0


if __name__ == "__main__":
    sys.exit(main())
