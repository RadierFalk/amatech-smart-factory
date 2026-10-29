"""
Serviço de Gestão de Equipamentos, Estados Operacionais e Catálogo de Peças.
Atende aos requisitos F02, F14, F16, F17, RN07 e RN08.
"""
from datetime import datetime, timezone
from typing import Any

from database import get_db


def _calcular_minutos_decorridos(data_hora_str: str | None) -> int | None:
    """Calcula minutos decorridos entre um timestamp ISO/SQLite (UTC) e o instante atual."""
    if not data_hora_str:
        return None
    try:
        limpo = str(data_hora_str).replace("T", " ").split(".")[0]
        dt_abertura = datetime.strptime(limpo, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        agora = datetime.now(timezone.utc)
        segundos = (agora - dt_abertura).total_seconds()
        return max(1, int(round(segundos / 60)))
    except Exception:
        return None


def listar_equipamentos(
    setor: str | None = None,
    apenas_ativos: bool = True,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Lista equipamentos com informações enriquecidas da OS ativa (quando houver)
    para exibição no Painel Sinótico de Máquinas (F02) e na API REST.
    """
    filtros = []
    params: list[Any] = []

    if apenas_ativos:
        filtros.append("e.ativo = 1")
    if setor and setor != "Todos":
        filtros.append("e.setor = ?")
        params.append(setor)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query = f"""
        SELECT
            e.id,
            e.codigo_tag,
            e.nome,
            e.setor,
            e.posto_trabalho,
            e.status_operacional,
            e.ativo,
            c.id AS os_ativa_id,
            c.status_chamado AS os_ativa_status,
            c.prioridade AS os_ativa_prioridade,
            c.data_hora_abertura AS os_ativa_abertura,
            c.data_hora_inicio_atendimento AS os_ativa_inicio,
            c.descricao_falha AS os_ativa_descricao,
            u.nome AS os_ativa_tecnico
        FROM equipamentos e
        LEFT JOIN chamados_manutencao c
            ON c.id = (
                SELECT c2.id
                FROM chamados_manutencao c2
                WHERE c2.equipamento_id = e.id
                  AND c2.status_chamado IN ('ABERTO', 'EM_ANDAMENTO')
                ORDER BY c2.data_hora_abertura DESC, c2.id DESC
                LIMIT 1
            )
        LEFT JOIN usuarios u
            ON u.id = c.tecnico_responsavel_id
        {where_clause}
        ORDER BY
            CASE e.status_operacional
                WHEN 'PARADA' THEN 1
                WHEN 'EM_MANUTENCAO' THEN 2
                ELSE 3
            END,
            e.codigo_tag ASC
    """

    with get_db(db_path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        resultado = []
        for r in rows:
            item = dict(r)
            item["ativo"] = bool(item["ativo"])
            item["tempo_decorrido_min"] = _calcular_minutos_decorridos(item.get("os_ativa_abertura"))
            resultado.append(item)
        return resultado


def obter_equipamento(equipamento_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    """Retorna os dados de um equipamento pelo seu ID."""
    with get_db(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, codigo_tag, nome, setor, posto_trabalho, status_operacional, ativo
            FROM equipamentos
            WHERE id = ?
            """,
            (equipamento_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["ativo"] = bool(d["ativo"])
        return d


def obter_equipamento_por_tag(codigo_tag: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Retorna os dados de um equipamento pela sua tag (ex: SMT-01)."""
    with get_db(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, codigo_tag, nome, setor, posto_trabalho, status_operacional, ativo
            FROM equipamentos
            WHERE UPPER(codigo_tag) = UPPER(?)
            """,
            ((codigo_tag or "").strip(),),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["ativo"] = bool(d["ativo"])
        return d


def listar_setores(db_path: str | None = None) -> list[str]:
    """Lista os setores distintos dos equipamentos ativos."""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT setor FROM equipamentos WHERE ativo = 1 ORDER BY setor ASC"
        ).fetchall()
        return [r["setor"] for r in rows if r["setor"]]


def criar_equipamento(
    codigo_tag: str,
    nome: str,
    setor: str,
    posto_trabalho: str,
    db_path: str | None = None,
) -> int:
    """Cadastra um novo equipamento fabril validando unicidade de TAG (F14)."""
    tag_limpa = (codigo_tag or "").strip().upper()
    nome_limpo = (nome or "").strip()
    setor_limpo = (setor or "").strip()
    posto_limpo = (posto_trabalho or "").strip()

    if not tag_limpa:
        raise ValueError("O Código/TAG do equipamento é obrigatório (ex: SMT-04).")
    if not nome_limpo:
        raise ValueError("O nome do equipamento é obrigatório.")
    if not setor_limpo:
        raise ValueError("O setor do equipamento é obrigatório.")

    with get_db(db_path) as conn:
        existente = conn.execute(
            "SELECT id FROM equipamentos WHERE UPPER(codigo_tag) = ?",
            (tag_limpa,),
        ).fetchone()
        if existente:
            raise ValueError(f"Já existe uma máquina cadastrada com a TAG '{tag_limpa}'.")

        cursor = conn.execute(
            """
            INSERT INTO equipamentos (codigo_tag, nome, setor, posto_trabalho, status_operacional, ativo)
            VALUES (?, ?, ?, ?, 'OPERACIONAL', 1)
            """,
            (tag_limpa, nome_limpo, setor_limpo, posto_limpo or "Posto 01"),
        )
        return int(cursor.lastrowid)


def atualizar_equipamento(
    equipamento_id: int,
    nome: str,
    setor: str,
    posto_trabalho: str,
    db_path: str | None = None,
) -> None:
    """Atualiza dados cadastrais de um equipamento (F14)."""
    if not (nome or "").strip():
        raise ValueError("O nome do equipamento não pode ficar vazio.")
    if not (setor or "").strip():
        raise ValueError("O setor do equipamento não pode ficar vazio.")

    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE equipamentos
            SET nome = ?, setor = ?, posto_trabalho = ?
            WHERE id = ?
            """,
            (nome.strip(), setor.strip(), (posto_trabalho or "").strip(), equipamento_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Equipamento ID {equipamento_id} não encontrado.")


def alternar_status_ativo_equipamento(
    equipamento_id: int,
    ativo: bool,
    db_path: str | None = None,
) -> None:
    """Ativa ou inativa logicamente um equipamento (Soft Delete - RN07)."""
    with get_db(db_path) as conn:
        if not ativo:
            os_ativa = conn.execute(
                """
                SELECT id FROM chamados_manutencao
                WHERE equipamento_id = ? AND status_chamado IN ('ABERTO', 'EM_ANDAMENTO')
                """,
                (equipamento_id,),
            ).fetchone()
            if os_ativa:
                raise ValueError(
                    f"Não é possível inativar o equipamento pois possui a OS #{os_ativa['id']} em aberto/andamento."
                )

        cursor = conn.execute(
            "UPDATE equipamentos SET ativo = ? WHERE id = ?",
            (1 if ativo else 0, equipamento_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Equipamento ID {equipamento_id} não encontrado.")


def listar_pecas(apenas_ativas: bool = True, db_path: str | None = None) -> list[dict[str, Any]]:
    """Lista o catálogo de peças e insumos sobressalentes (F16)."""
    query = "SELECT id, codigo_peca, nome, unidade_medida, ativo FROM pecas"
    if apenas_ativas:
        query += " WHERE ativo = 1"
    query += " ORDER BY codigo_peca ASC"

    with get_db(db_path) as conn:
        rows = conn.execute(query).fetchall()
        resultado = []
        for r in rows:
            item = dict(r)
            item["ativo"] = bool(item["ativo"])
            resultado.append(item)
        return resultado


def criar_peca(
    codigo_peca: str,
    nome: str,
    unidade_medida: str = "UN",
    db_path: str | None = None,
) -> int:
    """Cadastra uma nova peça no catálogo validando unicidade de código (F16)."""
    codigo_limpo = (codigo_peca or "").strip().upper()
    nome_limpo = (nome or "").strip()
    unidade_limpa = (unidade_medida or "UN").strip().upper()

    if not codigo_limpo:
        raise ValueError("O código da peça (Part Number) é obrigatório.")
    if not nome_limpo:
        raise ValueError("O nome/descrição da peça é obrigatório.")

    with get_db(db_path) as conn:
        existente = conn.execute(
            "SELECT id FROM pecas WHERE UPPER(codigo_peca) = ?",
            (codigo_limpo,),
        ).fetchone()
        if existente:
            raise ValueError(f"Já existe uma peça cadastrada com o código '{codigo_limpo}'.")

        cursor = conn.execute(
            """
            INSERT INTO pecas (codigo_peca, nome, unidade_medida, ativo)
            VALUES (?, ?, ?, 1)
            """,
            (codigo_limpo, nome_limpo, unidade_limpa),
        )
        return int(cursor.lastrowid)


def alternar_status_ativo_peca(
    peca_id: int,
    ativo: bool,
    db_path: str | None = None,
) -> None:
    """Ativa ou inativa logicamente uma peça do catálogo (Soft Delete - RN07)."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "UPDATE pecas SET ativo = ? WHERE id = ?",
            (1 if ativo else 0, peca_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Peça ID {peca_id} não encontrada.")
