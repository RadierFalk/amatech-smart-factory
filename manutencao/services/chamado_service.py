"""
Serviço de Ciclo de Vida da Ordem de Serviço (Chamados de Manutenção).
Atende aos requisitos F03–F11, F17 e Regras de Negócio RN02, RN03, RN04, RN05, RN06, RN08 e RN09.
"""
from datetime import datetime, timezone
from typing import Any

from config import MATRICULA_INTEGRACAO, PRIORIDADES, TIPOS_MANUTENCAO
from database import get_db


def _agora_utc_str() -> str:
    """Gera carimbo de data/hora no servidor em UTC compatível com SQLite CURRENT_TIMESTAMP (RN06)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Converte string de data/hora do banco em objeto datetime UTC."""
    if not ts_str:
        return None
    try:
        limpo = str(ts_str).replace("T", " ").split(".")[0]
        return datetime.strptime(limpo, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def calcular_downtime_minutos(abertura_str: str, fim_str: str) -> int:
    """
    Calcula o downtime total em minutos entre a abertura do chamado e o fim do atendimento (RN05).
    Fórmula: round((fim - abertura).total_seconds() / 60), garantindo mínimo de 1 minuto para OS concluída.
    """
    dt_abertura = _parse_timestamp(abertura_str)
    dt_fim = _parse_timestamp(fim_str)
    if not dt_abertura or not dt_fim:
        return 0
    segundos = (dt_fim - dt_abertura).total_seconds()
    if segundos < 0:
        return 0
    return max(1, int(round(segundos / 60.0)))


def calcular_segundos_decorridos(inicio_str: str | None) -> int:
    """Retorna o total de segundos decorridos desde um timestamp até agora (para cronômetro em tempo real)."""
    dt_inicio = _parse_timestamp(inicio_str)
    if not dt_inicio:
        return 0
    agora = datetime.now(timezone.utc)
    return max(0, int((agora - dt_inicio).total_seconds()))


def abrir_chamado(
    equipamento_id: int,
    operador_abertura_id: int,
    prioridade: str,
    descricao_falha: str,
    tipo_manutencao: str = "CORRETIVA",
    parar_maquina: bool = True,
    db_path: str | None = None,
    origem_sistema: str | None = None,
    id_externo: str | None = None,
) -> int:
    """
    Abre um novo chamado de manutenção (F03):
    - Valida bloqueio de redundância (RN02): proíbe abertura para máquina já PARADA ou EM_MANUTENCAO.
    - Muda status do equipamento para PARADA (Vermelho).
    - Grava chamado com status ABERTO e data_hora_abertura = now() (RN06).
    - Registra transição na trilha de auditoria historico_status (RN08).
    """
    prioridade_limpa = (prioridade or "MEDIA").strip().upper()
    tipo_limpo = (tipo_manutencao or "CORRETIVA").strip().upper()
    descricao_limpa = (descricao_falha or "").strip()

    if prioridade_limpa not in PRIORIDADES:
        raise ValueError(f"Prioridade inválida. Valores aceitos: {', '.join(PRIORIDADES)}.")
    if tipo_limpo not in TIPOS_MANUTENCAO:
        raise ValueError(f"Tipo de manutenção inválido. Valores aceitos: {', '.join(TIPOS_MANUTENCAO)}.")
    if not descricao_limpa or len(descricao_limpa) < 5:
        raise ValueError("Descreva detalhadamente o sintoma ou falha observada (mínimo de 5 caracteres).")

    with get_db(db_path) as conn:
        equip = conn.execute(
            """
            SELECT id, codigo_tag, nome, status_operacional, ativo
            FROM equipamentos
            WHERE id = ?
            """,
            (equipamento_id,),
        ).fetchone()

        if not equip:
            raise ValueError("Equipamento selecionado não existe.")
        if not bool(equip["ativo"]):
            raise ValueError(f"O equipamento {equip['codigo_tag']} está inativo.")

        os_ativa = conn.execute(
            """
            SELECT id, status_chamado, prioridade, data_hora_abertura
            FROM chamados_manutencao
            WHERE equipamento_id = ? AND status_chamado IN ('ABERTO', 'EM_ANDAMENTO')
            ORDER BY id DESC LIMIT 1
            """,
            (equipamento_id,),
        ).fetchone()

        # RN02: Bloqueio de redundância
        if equip["status_operacional"] in ("PARADA", "EM_MANUTENCAO") or os_ativa is not None:
            num_os = f"OS #{os_ativa['id']}" if os_ativa else "OS ativa"
            raise ValueError(
                f"Bloqueio de Redundância (RN02): A máquina {equip['codigo_tag']} ({equip['nome']}) "
                f"já se encontra com status '{equip['status_operacional']}' vinculada à {num_os}."
            )

        agora = _agora_utc_str()
        status_anterior = equip["status_operacional"]

        # 1. Insere o chamado com status ABERTO
        cursor = conn.execute(
            """
            INSERT INTO chamados_manutencao (
                equipamento_id,
                operador_abertura_id,
                prioridade,
                tipo_manutencao,
                status_chamado,
                descricao_falha,
                data_hora_abertura,
                origem_sistema,
                id_externo
            ) VALUES (?, ?, ?, ?, 'ABERTO', ?, ?, ?, ?)
            """,
            (
                equipamento_id,
                operador_abertura_id,
                prioridade_limpa,
                tipo_limpo,
                descricao_limpa,
                agora,
                origem_sistema,
                id_externo,
            ),
        )
        chamado_id = int(cursor.lastrowid)

        # 2. Atualiza equipamento para PARADA (Vermelho) se parar_maquina=True
        novo_status_maq = "PARADA" if parar_maquina else status_anterior
        if parar_maquina:
            conn.execute(
                "UPDATE equipamentos SET status_operacional = 'PARADA' WHERE id = ?",
                (equipamento_id,),
            )

        # 3. Grava trilha de auditoria (RN08)
        conn.execute(
            """
            INSERT INTO historico_status (
                equipamento_id, chamado_id, usuario_id, status_anterior, status_novo, alterado_em
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (equipamento_id, chamado_id, operador_abertura_id, status_anterior, novo_status_maq, agora),
        )

        return chamado_id


def abrir_chamado_externo(
    equipamento_tag: str,
    descricao_falha: str,
    prioridade: str = "MEDIA",
    tipo_manutencao: str = "CORRETIVA",
    origem_sistema: str | None = None,
    id_externo: str | None = None,
    db_path: str | None = None,
) -> tuple[int, bool]:
    """
    Abre um chamado pedido por outro sistema do ecossistema (ex.: a Qualidade encontrou um defeito causado
    pela máquina). Devolve (id do chamado, criado). Um reenvio com o mesmo (origem_sistema, id_externo)
    devolve o chamado já aberto, sem duplicar. As regras são as mesmas do formulário (RN02 incluída).
    """
    tag = (equipamento_tag or "").strip().upper()
    with get_db(db_path) as conn:
        if id_externo:
            existente = conn.execute(
                "SELECT id FROM chamados_manutencao WHERE origem_sistema = ? AND id_externo = ?",
                (origem_sistema, id_externo),
            ).fetchone()
            if existente:
                return int(existente["id"]), False
        equip = conn.execute("SELECT id FROM equipamentos WHERE UPPER(codigo_tag) = ?", (tag,)).fetchone()
        if not equip:
            raise LookupError(f"Máquina com a TAG '{tag}' não encontrada.")
        servico = conn.execute(
            "SELECT id FROM usuarios WHERE matricula = ?", (MATRICULA_INTEGRACAO,)
        ).fetchone()
        if not servico:
            raise RuntimeError("Usuário de serviço da integração não está cadastrado.")
    chamado_id = abrir_chamado(
        int(equip["id"]),
        int(servico["id"]),
        prioridade,
        descricao_falha,
        tipo_manutencao=tipo_manutencao,
        db_path=db_path,
        origem_sistema=origem_sistema,
        id_externo=id_externo,
    )
    return chamado_id, True


def assumir_chamado(
    chamado_id: int,
    tecnico_id: int,
    db_path: str | None = None,
) -> None:
    """
    Técnico assume a OS na fila (F06):
    - Valida responsabilidade única (RN03).
    - Atualiza chamado para EM_ANDAMENTO e grava data_hora_inicio_atendimento = now().
    - Atualiza máquina para EM_MANUTENCAO (Amarelo).
    - Grava trilha de auditoria em historico_status (RN08).
    """
    with get_db(db_path) as conn:
        chamado = conn.execute(
            """
            SELECT id, equipamento_id, status_chamado, tecnico_responsavel_id
            FROM chamados_manutencao
            WHERE id = ?
            """,
            (chamado_id,),
        ).fetchone()

        if not chamado:
            raise ValueError(f"Ordem de Serviço #{chamado_id} não encontrada.")
        if chamado["status_chamado"] != "ABERTO":
            raise ValueError(
                f"A OS #{chamado_id} não pode ser assumida pois está com status '{chamado['status_chamado']}'."
            )

        usuario = conn.execute(
            "SELECT id, nome, perfil, ativo FROM usuarios WHERE id = ?",
            (tecnico_id,),
        ).fetchone()
        if not usuario or not bool(usuario["ativo"]):
            raise ValueError("Usuário técnico inválido ou inativo.")
        if usuario["perfil"] not in ("TECNICO", "GESTOR"):
            raise PermissionError("Apenas usuários com perfil TECNICO ou GESTOR podem assumir uma OS.")

        equip = conn.execute(
            "SELECT id, status_operacional FROM equipamentos WHERE id = ?",
            (chamado["equipamento_id"],),
        ).fetchone()
        status_anterior = equip["status_operacional"] if equip else "PARADA"

        agora = _agora_utc_str()

        # 1. Atualiza o chamado para EM_ANDAMENTO
        conn.execute(
            """
            UPDATE chamados_manutencao
            SET tecnico_responsavel_id = ?,
                status_chamado = 'EM_ANDAMENTO',
                data_hora_inicio_atendimento = ?
            WHERE id = ?
            """,
            (tecnico_id, agora, chamado_id),
        )

        # 2. Atualiza o equipamento para EM_MANUTENCAO (Amarelo)
        conn.execute(
            "UPDATE equipamentos SET status_operacional = 'EM_MANUTENCAO' WHERE id = ?",
            (chamado["equipamento_id"],),
        )

        # 3. Grava trilha de auditoria (RN08)
        conn.execute(
            """
            INSERT INTO historico_status (
                equipamento_id, chamado_id, usuario_id, status_anterior, status_novo, alterado_em
            ) VALUES (?, ?, ?, ?, 'EM_MANUTENCAO', ?)
            """,
            (chamado["equipamento_id"], chamado_id, tecnico_id, status_anterior, agora),
        )


def salvar_progresso_laudo(
    chamado_id: int,
    diagnostico_tecnico: str,
    causa_raiz: str,
    tipo_manutencao: str = "CORRETIVA",
    db_path: str | None = None,
) -> None:
    """Salva o rascunho/progresso do diagnóstico e causa raiz durante o atendimento (F07)."""
    tipo_limpo = (tipo_manutencao or "CORRETIVA").strip().upper()
    if tipo_limpo not in TIPOS_MANUTENCAO:
        tipo_limpo = "CORRETIVA"

    with get_db(db_path) as conn:
        conn.execute(
            """
            UPDATE chamados_manutencao
            SET diagnostico_tecnico = ?,
                causa_raiz = ?,
                tipo_manutencao = ?
            WHERE id = ? AND status_chamado = 'EM_ANDAMENTO'
            """,
            ((diagnostico_tecnico or "").strip(), (causa_raiz or "").strip(), tipo_limpo, chamado_id),
        )


def adicionar_peca_chamado(
    chamado_id: int,
    peca_id: int,
    quantidade: float,
    db_path: str | None = None,
) -> int:
    """
    Registra peça substituída na OS (F08).
    Valida RN09: quantidade estritamente maior que zero (quantidade > 0).
    """
    if quantidade is None or float(quantidade) <= 0:
        raise ValueError("Regra RN09: A quantidade de peças trocadas deve ser estritamente maior que zero.")

    qtd = round(float(quantidade), 2)

    with get_db(db_path) as conn:
        chamado = conn.execute(
            "SELECT id, status_chamado FROM chamados_manutencao WHERE id = ?",
            (chamado_id,),
        ).fetchone()
        if not chamado:
            raise ValueError(f"OS #{chamado_id} não encontrada.")
        if chamado["status_chamado"] not in ("EM_ANDAMENTO", "ABERTO"):
            raise ValueError("Só é permitido adicionar peças em uma OS em atendimento.")

        peca = conn.execute(
            "SELECT id, nome, ativo FROM pecas WHERE id = ?",
            (peca_id,),
        ).fetchone()
        if not peca or not bool(peca["ativo"]):
            raise ValueError("Peça inválida ou inativa no catálogo.")

        existente = conn.execute(
            """
            SELECT id, quantidade
            FROM chamado_pecas_trocadas
            WHERE chamado_id = ? AND peca_id = ?
            """,
            (chamado_id, peca_id),
        ).fetchone()

        if existente:
            nova_qtd = round(float(existente["quantidade"]) + qtd, 2)
            conn.execute(
                "UPDATE chamado_pecas_trocadas SET quantidade = ? WHERE id = ?",
                (nova_qtd, existente["id"]),
            )
            return int(existente["id"])

        cursor = conn.execute(
            """
            INSERT INTO chamado_pecas_trocadas (chamado_id, peca_id, quantidade)
            VALUES (?, ?, ?)
            """,
            (chamado_id, peca_id, qtd),
        )
        return int(cursor.lastrowid)


def remover_peca_chamado(registro_id: int, db_path: str | None = None) -> None:
    """Remove um item da lista de peças substituídas de uma OS em andamento (F08)."""
    with get_db(db_path) as conn:
        conn.execute("DELETE FROM chamado_pecas_trocadas WHERE id = ?", (registro_id,))


def listar_pecas_chamado(chamado_id: int, db_path: str | None = None) -> list[dict[str, Any]]:
    """Lista todas as peças vinculadas a uma Ordem de Serviço."""
    with get_db(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                cpt.id,
                cpt.chamado_id,
                cpt.peca_id,
                p.codigo_peca,
                p.nome,
                cpt.quantidade,
                p.unidade_medida AS unidade
            FROM chamado_pecas_trocadas cpt
            JOIN pecas p ON p.id = cpt.peca_id
            WHERE cpt.chamado_id = ?
            ORDER BY cpt.id ASC
            """,
            (chamado_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def concluir_chamado(
    chamado_id: int,
    usuario_id: int,
    diagnostico_tecnico: str,
    causa_raiz: str,
    tipo_manutencao: str = "CORRETIVA",
    pecas_adicionais: list[dict[str, Any]] | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Conclui uma Ordem de Serviço (F09):
    - Valida RN03 (Responsabilidade única: técnico responsável ou Gestor).
    - Valida RN04 (Obrigatoriedade de diagnóstico técnico, causa raiz e tipo de manutenção).
    - Grava data_hora_fim_atendimento = now() (RN06).
    - Calcula automaticamente downtime_minutos = round((fim - abertura).total_seconds() / 60) (RN05).
    - Retorna máquina para OPERACIONAL (Verde).
    - Grava trilha de auditoria em historico_status (RN08).
    """
    diag_limpo = (diagnostico_tecnico or "").strip()
    causa_limpa = (causa_raiz or "").strip()
    tipo_limpo = (tipo_manutencao or "").strip().upper()

    # RN04: Obrigatoriedade de laudo técnico
    if not diag_limpo:
        raise ValueError("Regra RN04: O campo 'Diagnóstico Técnico' é obrigatório para concluir a OS.")
    if not causa_limpa:
        raise ValueError("Regra RN04: O campo 'Causa Raiz' é obrigatório para concluir a OS.")
    if tipo_limpo not in TIPOS_MANUTENCAO:
        raise ValueError("Regra RN04: O campo 'Tipo de Manutenção' (CORRETIVA/PREVENTIVA) é obrigatório.")

    with get_db(db_path) as conn:
        chamado = conn.execute(
            """
            SELECT
                id, equipamento_id, tecnico_responsavel_id, status_chamado,
                data_hora_abertura, data_hora_inicio_atendimento
            FROM chamados_manutencao
            WHERE id = ?
            """,
            (chamado_id,),
        ).fetchone()

        if not chamado:
            raise ValueError(f"Ordem de Serviço #{chamado_id} não encontrada.")
        if chamado["status_chamado"] != "EM_ANDAMENTO":
            raise ValueError(
                f"Apenas chamados 'EM_ANDAMENTO' podem ser concluídos (status atual: {chamado['status_chamado']})."
            )

        usuario = conn.execute(
            "SELECT id, nome, perfil FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if not usuario:
            raise ValueError("Usuário executor não encontrado.")

        # RN03: Responsabilidade única (apenas técnico responsável ou Gestor)
        if (
            usuario["perfil"] != "GESTOR"
            and chamado["tecnico_responsavel_id"] is not None
            and int(chamado["tecnico_responsavel_id"]) != int(usuario_id)
        ):
            raise PermissionError(
                "Regra RN03: Apenas o técnico responsável pela OS ou um Gestor pode concluir este chamado."
            )

        # Caso existam peças enviadas junto no payload de conclusão
        if pecas_adicionais:
            for item in pecas_adicionais:
                p_id = int(item["peca_id"])
                qtd = float(item["quantidade"])
                if qtd <= 0:
                    raise ValueError("Regra RN09: A quantidade de peças deve ser maior que zero.")
                conn.execute(
                    """
                    INSERT INTO chamado_pecas_trocadas (chamado_id, peca_id, quantidade)
                    VALUES (?, ?, ?)
                    """,
                    (chamado_id, p_id, round(qtd, 2)),
                )

        agora = _agora_utc_str()
        downtime_min = calcular_downtime_minutos(str(chamado["data_hora_abertura"]), agora)

        equip = conn.execute(
            "SELECT id, status_operacional FROM equipamentos WHERE id = ?",
            (chamado["equipamento_id"],),
        ).fetchone()
        status_anterior = equip["status_operacional"] if equip else "EM_MANUTENCAO"

        # 1. Atualiza o chamado para CONCLUIDO com o downtime calculado
        conn.execute(
            """
            UPDATE chamados_manutencao
            SET status_chamado = 'CONCLUIDO',
                diagnostico_tecnico = ?,
                causa_raiz = ?,
                tipo_manutencao = ?,
                data_hora_fim_atendimento = ?,
                downtime_minutos = ?
            WHERE id = ?
            """,
            (diag_limpo, causa_limpa, tipo_limpo, agora, downtime_min, chamado_id),
        )

        # 2. Libera o equipamento para OPERACIONAL (Verde)
        conn.execute(
            "UPDATE equipamentos SET status_operacional = 'OPERACIONAL' WHERE id = ?",
            (chamado["equipamento_id"],),
        )

        # 3. Grava na trilha de auditoria (RN08)
        conn.execute(
            """
            INSERT INTO historico_status (
                equipamento_id, chamado_id, usuario_id, status_anterior, status_novo, alterado_em
            ) VALUES (?, ?, ?, ?, 'OPERACIONAL', ?)
            """,
            (chamado["equipamento_id"], chamado_id, usuario_id, status_anterior, agora),
        )

        return {
            "chamado_id": chamado_id,
            "equipamento_id": chamado["equipamento_id"],
            "status_chamado": "CONCLUIDO",
            "status_equipamento": "OPERACIONAL",
            "data_hora_fim_atendimento": agora,
            "downtime_minutos": downtime_min,
        }


def cancelar_chamado(
    chamado_id: int,
    usuario_id: int,
    motivo_cancelamento: str = "Alarme falso / Cancelado pela supervisão",
    db_path: str | None = None,
) -> None:
    """
    Cancela um chamado aberto ou em andamento, retornando a máquina para OPERACIONAL
    e registrando na trilha de auditoria (RN08).
    """
    with get_db(db_path) as conn:
        chamado = conn.execute(
            "SELECT id, equipamento_id, status_chamado FROM chamados_manutencao WHERE id = ?",
            (chamado_id,),
        ).fetchone()
        if not chamado:
            raise ValueError(f"OS #{chamado_id} não encontrada.")
        if chamado["status_chamado"] in ("CONCLUIDO", "CANCELADO"):
            raise ValueError(f"A OS #{chamado_id} já está encerrada ({chamado['status_chamado']}).")

        equip = conn.execute(
            "SELECT id, status_operacional FROM equipamentos WHERE id = ?",
            (chamado["equipamento_id"],),
        ).fetchone()
        status_anterior = equip["status_operacional"] if equip else "PARADA"
        agora = _agora_utc_str()

        conn.execute(
            """
            UPDATE chamados_manutencao
            SET status_chamado = 'CANCELADO',
                diagnostico_tecnico = ?,
                data_hora_fim_atendimento = ?,
                downtime_minutos = 0
            WHERE id = ?
            """,
            (motivo_cancelamento.strip(), agora, chamado_id),
        )

        conn.execute(
            "UPDATE equipamentos SET status_operacional = 'OPERACIONAL' WHERE id = ?",
            (chamado["equipamento_id"],),
        )

        conn.execute(
            """
            INSERT INTO historico_status (
                equipamento_id, chamado_id, usuario_id, status_anterior, status_novo, alterado_em
            ) VALUES (?, ?, ?, ?, 'OPERACIONAL', ?)
            """,
            (chamado["equipamento_id"], chamado_id, usuario_id, status_anterior, agora),
        )


def listar_fila_chamados(setor: str | None = None, db_path: str | None = None) -> list[dict[str, Any]]:
    """
    Lista os chamados com status ABERTO ordenados por prioridade (Crítica no topo)
    e maior tempo de espera (F05).
    """
    filtro_setor = ""
    params: list[Any] = []
    if setor and setor != "Todos":
        filtro_setor = "AND e.setor = ?"
        params.append(setor)

    query = f"""
        SELECT
            c.id,
            c.equipamento_id,
            e.codigo_tag AS equipamento_tag,
            e.nome AS equipamento_nome,
            e.setor,
            e.posto_trabalho,
            c.prioridade,
            c.tipo_manutencao,
            c.status_chamado,
            c.descricao_falha,
            c.data_hora_abertura,
            u_op.nome AS operador_nome,
            u_op.matricula AS operador_matricula
        FROM chamados_manutencao c
        JOIN equipamentos e ON e.id = c.equipamento_id
        JOIN usuarios u_op ON u_op.id = c.operador_abertura_id
        WHERE c.status_chamado = 'ABERTO'
        {filtro_setor}
        ORDER BY
            CASE c.prioridade
                WHEN 'CRITICA' THEN 1
                WHEN 'ALTA' THEN 2
                WHEN 'MEDIA' THEN 3
                WHEN 'BAIXA' THEN 4
                ELSE 5
            END ASC,
            c.data_hora_abertura ASC
    """

    with get_db(db_path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        resultado = []
        for r in rows:
            item = dict(r)
            seg = calcular_segundos_decorridos(item.get("data_hora_abertura"))
            item["tempo_espera_segundos"] = seg
            item["tempo_espera_min"] = max(1, int(round(seg / 60.0)))
            resultado.append(item)
        return resultado


def listar_chamados_em_andamento(
    tecnico_id: int | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Lista todas as Ordens de Serviço com status EM_ANDAMENTO (F07)."""
    filtro_tec = ""
    params: list[Any] = []
    if tecnico_id is not None:
        filtro_tec = "AND c.tecnico_responsavel_id = ?"
        params.append(tecnico_id)

    query = f"""
        SELECT
            c.id,
            c.equipamento_id,
            e.codigo_tag AS equipamento_tag,
            e.nome AS equipamento_nome,
            e.setor,
            e.posto_trabalho,
            c.operador_abertura_id,
            u_op.nome AS operador_nome,
            c.tecnico_responsavel_id,
            u_tec.nome AS tecnico_nome,
            c.prioridade,
            c.tipo_manutencao,
            c.status_chamado,
            c.descricao_falha,
            c.diagnostico_tecnico,
            c.causa_raiz,
            c.data_hora_abertura,
            c.data_hora_inicio_atendimento
        FROM chamados_manutencao c
        JOIN equipamentos e ON e.id = c.equipamento_id
        JOIN usuarios u_op ON u_op.id = c.operador_abertura_id
        LEFT JOIN usuarios u_tec ON u_tec.id = c.tecnico_responsavel_id
        WHERE c.status_chamado = 'EM_ANDAMENTO'
        {filtro_tec}
        ORDER BY
            CASE c.prioridade
                WHEN 'CRITICA' THEN 1
                WHEN 'ALTA' THEN 2
                WHEN 'MEDIA' THEN 3
                ELSE 4
            END ASC,
            c.data_hora_inicio_atendimento ASC
    """

    with get_db(db_path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        resultado = []
        for r in rows:
            item = dict(r)
            seg_atend = calcular_segundos_decorridos(item.get("data_hora_inicio_atendimento"))
            seg_total = calcular_segundos_decorridos(item.get("data_hora_abertura"))
            item["tempo_atendimento_segundos"] = seg_atend
            item["tempo_atendimento_min"] = max(1, int(round(seg_atend / 60.0)))
            item["tempo_total_segundos"] = seg_total
            item["tempo_total_min"] = max(1, int(round(seg_total / 60.0)))
            item["pecas_trocadas"] = listar_pecas_chamado(item["id"], db_path=db_path)
            resultado.append(item)
        return resultado


def obter_chamado_detalhado(chamado_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    """Retorna todos os dados de uma OS específica incluindo peças substituídas."""
    with get_db(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                c.*,
                e.codigo_tag AS equipamento_tag,
                e.nome AS equipamento_nome,
                e.setor,
                e.posto_trabalho,
                u_op.nome AS operador_nome,
                u_tec.nome AS tecnico_nome
            FROM chamados_manutencao c
            JOIN equipamentos e ON e.id = c.equipamento_id
            JOIN usuarios u_op ON u_op.id = c.operador_abertura_id
            LEFT JOIN usuarios u_tec ON u_tec.id = c.tecnico_responsavel_id
            WHERE c.id = ?
            """,
            (chamado_id,),
        ).fetchone()

        if not row:
            return None

        item = dict(row)
        item["pecas_trocadas"] = listar_pecas_chamado(chamado_id, db_path=db_path)
        return item


def listar_historico_chamados(
    equipamento_id: int | None = None,
    tecnico_id: int | None = None,
    operador_id: int | None = None,
    setor: str | None = None,
    status_chamado: str | None = None,
    tipo_manutencao: str | None = None,
    prioridade: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    busca_texto: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Consulta detalhada de chamados com múltiplos filtros para a tela de Histórico (F11)
    e para o endpoint GET /api/manutencao/chamados.
    """
    filtros = []
    params: list[Any] = []

    if equipamento_id:
        filtros.append("c.equipamento_id = ?")
        params.append(equipamento_id)
    if tecnico_id:
        filtros.append("c.tecnico_responsavel_id = ?")
        params.append(tecnico_id)
    if operador_id:
        filtros.append("c.operador_abertura_id = ?")
        params.append(operador_id)
    if setor and setor != "Todos":
        filtros.append("e.setor = ?")
        params.append(setor)
    if status_chamado and status_chamado != "Todos":
        filtros.append("c.status_chamado = ?")
        params.append(status_chamado)
    if tipo_manutencao and tipo_manutencao != "Todos":
        filtros.append("c.tipo_manutencao = ?")
        params.append(tipo_manutencao)
    if prioridade and prioridade != "Todos":
        filtros.append("c.prioridade = ?")
        params.append(prioridade)
    if data_inicio:
        filtros.append("date(c.data_hora_abertura) >= date(?)")
        params.append(data_inicio)
    if data_fim:
        filtros.append("date(c.data_hora_abertura) <= date(?)")
        params.append(data_fim)
    if busca_texto and busca_texto.strip():
        termo = f"%{busca_texto.strip()}%"
        filtros.append(
            "(e.codigo_tag LIKE ? OR e.nome LIKE ? OR c.descricao_falha LIKE ? "
            "OR IFNULL(c.diagnostico_tecnico, '') LIKE ? OR IFNULL(c.causa_raiz, '') LIKE ?)"
        )
        params.extend([termo, termo, termo, termo, termo])

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query = f"""
        SELECT
            c.id,
            c.equipamento_id,
            e.codigo_tag AS equipamento_tag,
            e.nome AS equipamento_nome,
            e.setor,
            e.posto_trabalho,
            c.operador_abertura_id,
            u_op.nome AS operador_nome,
            c.tecnico_responsavel_id,
            u_tec.nome AS tecnico_nome,
            c.prioridade,
            c.tipo_manutencao,
            c.status_chamado,
            c.descricao_falha,
            c.diagnostico_tecnico,
            c.causa_raiz,
            c.data_hora_abertura,
            c.data_hora_inicio_atendimento,
            c.data_hora_fim_atendimento,
            c.downtime_minutos,
            c.origem_sistema,
            c.id_externo
        FROM chamados_manutencao c
        JOIN equipamentos e ON e.id = c.equipamento_id
        JOIN usuarios u_op ON u_op.id = c.operador_abertura_id
        LEFT JOIN usuarios u_tec ON u_tec.id = c.tecnico_responsavel_id
        {where_clause}
        ORDER BY c.data_hora_abertura DESC, c.id DESC
    """

    with get_db(db_path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

        # Busca todas as peças trocadas de uma vez para evitar N+1 queries
        pecas_rows = conn.execute(
            """
            SELECT
                cpt.chamado_id,
                p.codigo_peca,
                p.nome,
                cpt.quantidade,
                p.unidade_medida AS unidade
            FROM chamado_pecas_trocadas cpt
            JOIN pecas p ON p.id = cpt.peca_id
            ORDER BY cpt.id ASC
            """
        ).fetchall()

        pecas_por_chamado: dict[int, list[dict[str, Any]]] = {}
        for pr in pecas_rows:
            cid = int(pr["chamado_id"])
            pecas_por_chamado.setdefault(cid, []).append(
                {
                    "codigo_peca": pr["codigo_peca"],
                    "nome": pr["nome"],
                    "quantidade": float(pr["quantidade"]),
                    "unidade": pr["unidade"],
                }
            )

        resultado = []
        for r in rows:
            item = dict(r)
            if item["status_chamado"] == "CONCLUIDO" and not item.get("downtime_minutos"):
                item["downtime_minutos"] = max(
                    1,
                    calcular_downtime_minutos(
                        str(item.get("data_hora_abertura") or ""),
                        str(item.get("data_hora_fim_atendimento") or ""),
                    ),
                )
            elif item["status_chamado"] in ("ABERTO", "EM_ANDAMENTO") and item.get("downtime_minutos") is None:
                seg_parado = calcular_segundos_decorridos(item.get("data_hora_abertura"))
                item["tempo_parado_min"] = max(1, int(round(seg_parado / 60.0)))
            else:
                item["tempo_parado_min"] = int(item.get("downtime_minutos") or 0)

            pecas_os = pecas_por_chamado.get(int(item["id"]), [])
            item["pecas_trocadas"] = pecas_os
            item["resumo_pecas"] = (
                ", ".join(
                    f"{p['codigo_peca']} ({p['quantidade']:g} {p['unidade']})" for p in pecas_os
                )
                if pecas_os
                else "Nenhuma"
            )
            resultado.append(item)
        return resultado


def listar_historico_auditoria(
    equipamento_id: int | None = None,
    limite: int = 100,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Lista a trilha de auditoria imutável da tabela historico_status (F17 / RN08)."""
    filtro = "WHERE h.equipamento_id = ?" if equipamento_id else ""
    params: tuple = (equipamento_id, limite) if equipamento_id else (limite,)

    query = f"""
        SELECT
            h.id,
            h.equipamento_id,
            e.codigo_tag AS equipamento_tag,
            e.nome AS equipamento_nome,
            h.chamado_id,
            h.usuario_id,
            u.nome AS usuario_nome,
            u.perfil AS usuario_perfil,
            h.status_anterior,
            h.status_novo,
            h.alterado_em
        FROM historico_status h
        JOIN equipamentos e ON e.id = h.equipamento_id
        JOIN usuarios u ON u.id = h.usuario_id
        {filtro}
        ORDER BY h.alterado_em DESC, h.id DESC
        LIMIT ?
    """

    with get_db(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
