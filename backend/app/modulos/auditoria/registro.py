"""Grava a trilha de auditoria sozinha, a cada flush do SQLAlchemy, na mesma transação da operação.

- Quem fez: o usuário que `definir_usuario` guardou na sessão (o login da requisição, ou a conta de serviço das
  máquinas). Sem usuário, fica como "sistema".
- O quê: só as classes de AUDITADOS. Logs que já são trilhas (passagens da RAS, histórico de estado das máquinas)
  e a própria auditoria ficam de fora.
- Campos: os de coluna, com antes e depois. Senhas nunca entram, nem o hash.
- Se a operação for desfeita (rollback), o registro de auditoria também é.
- Cargas em lote (migração dos bancos antigos, dados de demonstração) chamam `desligar` antes.
"""
import enum
from datetime import date, datetime, time
from decimal import Decimal
from itertools import chain
from typing import Any

from sqlalchemy import event, insert, inspect, update
from sqlalchemy.orm import Session

from app.core import tempo
from app.modulos.auditoria.modelos import RegistroAuditoria

CHAVE_USUARIO = "auditoria_usuario"
CHAVE_DESLIGADA = "auditoria_desligada"
CHAVE_CRIADOS = "auditoria_criados"

# Nunca gravados, em nenhuma tabela.
CAMPOS_OCULTOS = frozenset({"senha_hash"})

_config: dict[type, tuple[str, str, str | None, frozenset[str]]] | None = None


def _auditados() -> dict[type, tuple[str, str, str | None, frozenset[str]]]:
    """classe -> (módulo, nome legível, campo que identifica o registro ou None para "#id", campos ignorados).
    Montado na primeira vez (os modelos dos módulos importam o core, e não o contrário)."""
    global _config
    if _config is None:
        from app.modulos.dashboard.modelos import Limite, Meta, Perda, TipoPerda, Turno
        from app.modulos.manutencao.modelos import Chamado, ChamadoPeca, Equipamento, Peca
        from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
        from app.modulos.rastreabilidade.modelos import (
            Baixa, Componente, Etapa, Modelo, ModeloComponente, NaoConformidade, Producao, Solicitacao,
        )
        from app.modulos.usuarios.modelos import Usuario

        nada: frozenset[str] = frozenset()
        _config = {
            Usuario: ("USR", "Usuário", "matricula", nada),
            Componente: ("RAS", "Componente", "sku", nada),
            Modelo: ("RAS", "Modelo", "nome", nada),
            ModeloComponente: ("RAS", "Componente do modelo", None, nada),
            Etapa: ("RAS", "Etapa", "nome", nada),
            # A etapa de cada produção já tem trilha própria (ras.passagens).
            Producao: ("RAS", "Produção", "numero_serie", frozenset({"etapa_id", "atualizada_em", "responsavel_id"})),
            NaoConformidade: ("RAS", "Não conformidade", None, nada),
            Solicitacao: ("RAS", "Pedido de material", None, nada),
            Baixa: ("RAS", "Baixa de material", None, nada),
            Ocorrencia: ("QLD", "Ocorrência", None, nada),
            Produto: ("QLD", "Notebook", "numero_serie", nada),
            Estacao: ("QLD", "Estação", "nome", nada),
            TipoDefeito: ("QLD", "Tipo de defeito", "nome", nada),
            Equipamento: ("MNT", "Máquina", "codigo_tag", nada),
            Peca: ("MNT", "Peça", "codigo_peca", nada),
            Chamado: ("MNT", "OS", None, nada),
            ChamadoPeca: ("MNT", "Peça da OS", None, nada),
            Meta: ("DSH", "Meta", None, nada),
            Perda: ("DSH", "Perda", None, nada),
            Turno: ("DSH", "Turno", "nome", nada),
            TipoPerda: ("DSH", "Tipo de perda", "nome", nada),
            Limite: ("DSH", "Limite do semáforo", "indicador", nada),
        }
    return _config


def definir_usuario(sessao: Session, usuario) -> None:
    """Quem responde pelas alterações desta sessão (chamado na autenticação de cada requisição)."""
    sessao.info[CHAVE_USUARIO] = (usuario.id, usuario.matricula, usuario.nome)


def desligar(sessao: Session) -> None:
    """Sem auditoria nesta sessão (cargas em lote: migração e dados de demonstração)."""
    sessao.info[CHAVE_DESLIGADA] = True


def _json(valor: Any) -> Any:
    if isinstance(valor, datetime):
        return tempo.utc(valor).isoformat() if valor.tzinfo else valor.isoformat()
    if isinstance(valor, (date, time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, enum.Enum):
        return valor.value
    if isinstance(valor, (bytes, bytearray)):
        return None
    return valor


def _alteracoes(estado, acao: str, ignorados: frozenset[str]) -> dict[str, list[Any]]:
    """{campo: [antes, depois]} só com o que mudou. Usa os valores já em memória: não consulta o banco no meio
    do flush (um valor padrão do banco ainda não carregado fica de fora na criação)."""
    mudancas: dict[str, list[Any]] = {}
    for atributo in estado.mapper.column_attrs:
        campo = atributo.key
        if campo in CAMPOS_OCULTOS or campo in ignorados:
            continue
        if acao == "ALTEROU":
            historico = estado.attrs[campo].history
            if not historico.has_changes():
                continue
            antes = historico.deleted[0] if historico.deleted else None
            depois = historico.added[0] if historico.added else None
            if antes == depois:
                continue
        elif campo not in estado.dict:
            continue
        elif acao == "CRIOU":
            antes, depois = None, estado.dict[campo]
        else:
            antes, depois = estado.dict[campo], None
        mudancas[campo] = [_json(antes), _json(depois)]
    return mudancas


@event.listens_for(Session, "after_flush")
def _registrar(sessao: Session, _contexto) -> None:
    if sessao.info.get(CHAVE_DESLIGADA):
        return
    auditados = _auditados()
    usuario_id, matricula, nome = sessao.info.get(CHAVE_USUARIO, (None, None, None))
    agora = tempo.agora()
    # Criados nesta transação: (entidade, chave) -> (id da linha "CRIOU", alterações). Uma alteração logo depois
    # (ex.: a produção ganha o número de série definitivo) entra nessa mesma linha, com os valores finais.
    criados: dict[tuple[str, str], tuple[int, dict]] = sessao.info.setdefault(CHAVE_CRIADOS, {})
    conexao = sessao.connection()
    linhas = []
    eventos = chain(((o, "CRIOU") for o in sessao.new), ((o, "ALTEROU") for o in sessao.dirty),
                    ((o, "EXCLUIU") for o in sessao.deleted))
    for objeto, acao in eventos:
        config = auditados.get(type(objeto))
        if config is None:
            continue
        modulo, rotulo, campo_nome, ignorados = config
        estado = inspect(objeto)
        alteracoes = _alteracoes(estado, acao, ignorados)
        if not alteracoes:
            continue  # só relações mudaram, ou só campos ignorados
        # A chave vem do objeto: num registro novo, a identidade da sessão só é montada depois deste evento.
        chave = "/".join(str(v) for v in estado.mapper.primary_key_from_instance(objeto) if v is not None)
        identificador = estado.dict.get(campo_nome) if campo_nome else None
        descricao = str(f"{rotulo} {identificador}" if identificador else f"{rotulo} #{chave}")[:200]
        entidade = f"{estado.mapper.local_table.schema}.{estado.mapper.local_table.name}"
        if acao == "ALTEROU" and (entidade, chave) in criados:
            linha_id, valores = criados[(entidade, chave)]
            juntos = {**valores, **{campo: [None, depois] for campo, (_antes, depois) in alteracoes.items()}}
            atualizada = conexao.execute(update(RegistroAuditoria).where(RegistroAuditoria.id == linha_id)
                                         .values(alteracoes=juntos, descricao=descricao))
            if atualizada.rowcount:  # 0: a criação foi desfeita num savepoint; registra a alteração à parte
                criados[(entidade, chave)] = (linha_id, juntos)
                continue
        linhas.append({
            "registrada_em": agora, "usuario_id": usuario_id, "usuario_matricula": matricula, "usuario_nome": nome,
            "modulo": modulo, "entidade": entidade, "entidade_id": chave or "?", "descricao": descricao,
            "acao": acao, "alteracoes": alteracoes,
        })
    if linhas:
        ids = conexao.execute(insert(RegistroAuditoria).returning(RegistroAuditoria.id, sort_by_parameter_order=True),
                              linhas).scalars().all()
        for linha, linha_id in zip(linhas, ids, strict=True):
            if linha["acao"] == "CRIOU":
                criados[(linha["entidade"], linha["entidade_id"])] = (linha_id, linha["alteracoes"])


@event.listens_for(Session, "after_transaction_end")
def _fim_da_transacao(sessao: Session, transacao) -> None:
    if transacao.parent is None:  # só a transação de fora (um savepoint terminando não encerra a operação)
        sessao.info.pop(CHAVE_CRIADOS, None)
