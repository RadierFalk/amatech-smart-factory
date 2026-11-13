"""Alertas do sino (/api/alertas): qualquer pessoa logada; cada uma recebe os do seu perfil (servico.py)."""
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core import tempo
from app.core.deps import SessaoDep, UsuarioAtual
from app.modulos.alertas import servico
from app.modulos.alertas.modelos import Alerta

rotas = APIRouter(prefix="/api/alertas", tags=["Alertas"])


class AlertaSaida(BaseModel):
    id: int
    tipo: str
    modulo: str
    titulo: str
    detalhe: str
    link: str
    ativo: bool = Field(description="false = a situação já foi resolvida")
    lido: bool
    criado_em: datetime
    resolvido_em: datetime | None

    @classmethod
    def de(cls, a: Alerta, lido: bool) -> "AlertaSaida":
        return cls(id=a.id, tipo=a.tipo, modulo=a.modulo, titulo=a.titulo, detalhe=a.detalhe, link=a.link, ativo=a.ativo,
                   lido=lido, criado_em=tempo.utc(a.criado_em), resolvido_em=tempo.utc(a.resolvido_em))


class AlertasSaida(BaseModel):
    nao_lidos: int = Field(description="Alertas ativos que a pessoa ainda não leu (o número do sino)")
    alertas: list[AlertaSaida]


class LidosEntrada(BaseModel):
    ids: list[int] | None = Field(None, description="Vazio: marca todos os visíveis")


@rotas.get("", response_model=AlertasSaida)
def listar(sessao: SessaoDep, usuario: UsuarioAtual):
    """Confere as situações abertas agora e devolve os alertas do perfil de quem pediu."""
    servico.sincronizar(sessao)
    lista, nao_lidos = servico.visiveis(sessao, usuario)
    return AlertasSaida(nao_lidos=nao_lidos, alertas=[AlertaSaida.de(a, lido) for a, lido in lista])


@rotas.post("/lidos", status_code=status.HTTP_204_NO_CONTENT)
def marcar_lidos(dados: LidosEntrada, sessao: SessaoDep, usuario: UsuarioAtual):
    servico.marcar_lidos(sessao, usuario, dados.ids)
