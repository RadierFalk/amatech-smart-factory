"""As 13 classes de dados do sistema (diagrama de classes da OA2, seção 5.2).

Cada classe segue uma tabela do MER. No lugar das chaves estrangeiras, guarda o objeto relacionado
(ex.: RegistroProducao.turno é um Turno). Só a classe Parada tem um método: calcular_duracao().
"""
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Perfil:
    nome: str
    descricao: str | None = None
    id: int | None = None


@dataclass
class Usuario:
    nome: str
    login: str
    perfil: Perfil
    ativo: bool = True
    id: int | None = None
    _senha_hash: str | None = field(default=None, repr=False)   # privado: nunca exibido


@dataclass
class Turno:
    nome: str
    hora_inicio: str
    hora_fim: str
    duracao_min: int
    id: int | None = None


@dataclass
class Produto:
    modelo: str
    descricao: str | None = None
    ativo: bool = True
    id: int | None = None


@dataclass
class Estacao:
    nome: str
    setor: str | None = None
    ordem_fluxo: int | None = None
    id: int | None = None


@dataclass
class Maquina:
    codigo: str
    nome: str
    estacao: Estacao | None = None
    id: int | None = None


@dataclass
class MetaProducao:
    data: date
    turno: Turno
    produto: Produto
    qtd_meta: int
    id: int | None = None


@dataclass
class RegistroProducao:
    data: date
    turno: Turno
    produto: Produto
    qtd_realizada: int
    qtd_aprovada: int
    qtd_reprovada: int
    id: int | None = None


@dataclass
class Defeito:
    tipo: str
    estacao: Estacao
    quantidade: int
    data_hora: datetime
    maquina: Maquina | None = None
    observacao: str | None = None
    id: int | None = None


@dataclass
class Retrabalho:
    estacao_retorno: Estacao
    motivo: str
    quantidade: int
    data_hora: datetime
    id: int | None = None


@dataclass
class Parada:
    estacao: Estacao
    turno: Turno
    motivo: str
    inicio: datetime
    fim: datetime | None = None          # vazio = parada em andamento
    maquina: Maquina | None = None
    observacao: str | None = None
    id: int | None = None

    def calcular_duracao(self, ate=None):
        """Duração em minutos. Parada em andamento: conta até `ate` (normalmente o horário atual)."""
        fim = self.fim or ate
        if fim is None:
            return 0.0
        return max((fim - self.inicio).total_seconds() / 60, 0.0)


@dataclass
class Perda:
    data: date
    tipo: str
    quantidade: int
    estacao: Estacao | None = None
    produto: Produto | None = None
    id: int | None = None


@dataclass
class Importacao:
    nome_arquivo: str
    tipo_dado: str
    linhas_lidas: int = 0
    linhas_importadas: int = 0
    linhas_rejeitadas: int = 0
    situacao: str = "concluida"           # concluida ou rejeitada
    id: int | None = None
