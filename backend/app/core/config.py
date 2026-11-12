"""Configuração da API única do ERP AMATECH, lida de variáveis de ambiente (ou backend/.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

SEGREDO_DESENVOLVIMENTO = "dev-inseguro-troque-em-producao-0123456789"
CHAVE_MAQUINAS_DESENVOLVIMENTO = "amatech-iot-demo"  # a mesma do sistema antigo (rastreabilidade/app/config.py)


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AMATECH_", extra="ignore")

    # postgresql+psycopg://usuario:senha@host:porta/banco
    database_url: str = "postgresql+psycopg://amatech:amatech@localhost:5432/amatech"

    jwt_segredo: str = SEGREDO_DESENVOLVIMENTO
    jwt_algoritmo: str = "HS256"
    jwt_expiracao_minutos: int = 480  # um turno de 8 horas

    # Origens liberadas no CORS (o Angular em desenvolvimento roda na 4200)
    cors_origens: list[str] = ["http://localhost:4200"]

    ambiente: str = "desenvolvimento"  # desenvolvimento | producao

    # Máquinas/IoT informam a etapa dos notebooks em /api/ras/maquinas/status com esta chave (X-API-Key).
    chave_maquinas: str = CHAVE_MAQUINAS_DESENVOLVIMENTO
    # Conta de serviço (inativa, sem login) que assina as mudanças feitas pelas máquinas.
    matricula_servico: str = "SVC-INTEGRACAO"

    def validar_producao(self) -> None:
        if self.ambiente == "producao" and self.jwt_segredo == SEGREDO_DESENVOLVIMENTO:
            raise RuntimeError("Defina AMATECH_JWT_SEGREDO antes de subir em produção.")
        if self.ambiente == "producao" and self.chave_maquinas == CHAVE_MAQUINAS_DESENVOLVIMENTO:
            raise RuntimeError("Defina AMATECH_CHAVE_MAQUINAS antes de subir em produção.")


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
