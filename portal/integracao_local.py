"""
Núcleo de Integração In-Process e Isolamento de Contexto do ERP AMATECH.

Permite que os 4 subsistemas setoriais (Rastreabilidade, Qualidade, Manutenção e Dashboard)
e o módulo de Gestão de Usuários coexistam no mesmo processo Python / Streamlit,
compartilhando uma única sessão autenticada e comunicando-se em memória sem
necessidade de múltiplos servidores ou portas separadas.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.parse import urlparse

from permissoes import (
    ADMINISTRADOR,
    ALMOXARIFE,
    INSPETOR,
    OPERADOR,
    SUPERVISOR,
    TECNICO,
)

RAIZ = Path(__file__).resolve().parent.parent
PASTA_PORTAL = Path(__file__).resolve().parent

PASTAS_SETORES: dict[str, Path] = {
    "rastreabilidade": RAIZ / "rastreabilidade",
    "qualidade": RAIZ / "qualidade",
    "manutencao": RAIZ / "manutencao",
    "dashboard": RAIZ / "dashboard",
}

# Módulos de topo que existem com o mesmo nome em diferentes pastas setoriais
NOMES_MODULOS_SETORIAIS = frozenset({
    "config",
    "database",
    "ui_components",
    "models",
    "services",
    "pages",
    "banco",
    "ocorrencia",
    "indicadores",
    "graficos",
    "integracao",
    "autenticacao",
    "permissoes",
    "sessao",
    "migracao",
    "telas",
    "acesso_dados",
    "modelos",
    "servicos",
    "app",
    "api",
})

_CACHE_MODULOS: dict[str, dict[str, Any]] = {
    setor: {} for setor in PASTAS_SETORES
}


def _eh_modulo_setorial(nome_modulo: str) -> bool:
    topo = nome_modulo.split(".")[0]
    return topo in NOMES_MODULOS_SETORIAIS


@contextmanager
def ambiente_modulo(setor: str):
    """
    Isola temporariamente sys.path, diretório de trabalho (cwd) e sys.modules
    para o setor informado ('rastreabilidade', 'qualidade', 'manutencao', 'dashboard').
    Suporta chamadas aninhadas (ex.: Qualidade acionando Rastreabilidade ou Manutenção).
    """
    pasta_setor = PASTAS_SETORES[setor]
    cwd_anterior = Path.cwd()
    sys_path_anterior = list(sys.path)

    # Salva os módulos setoriais atualmente ativos em sys.modules
    modulos_anteriores: dict[str, Any] = {}
    for nome in list(sys.modules.keys()):
        if _eh_modulo_setorial(nome):
            modulos_anteriores[nome] = sys.modules.pop(nome)

    # Restaura o cache de módulos já carregados para o setor alvo
    for nome, mod in _CACHE_MODULOS.get(setor, {}).items():
        sys.modules[nome] = mod

    # Ajusta sys.path com a pasta do setor na frente e a raiz do projeto em seguida
    caminhos_excluir = {str(p) for p in PASTAS_SETORES.values()} | {str(PASTA_PORTAL)}
    novo_sys_path = [str(pasta_setor), str(RAIZ)]
    for caminho in sys_path_anterior:
        if caminho not in caminhos_excluir and caminho not in novo_sys_path:
            novo_sys_path.append(caminho)

    sys.path[:] = novo_sys_path
    os.chdir(pasta_setor)

    try:
        yield pasta_setor
    finally:
        # Atualiza o cache do setor com todos os módulos carregados durante a execução
        cache_atualizado: dict[str, Any] = {}
        for nome in list(sys.modules.keys()):
            if _eh_modulo_setorial(nome):
                cache_atualizado[nome] = sys.modules.pop(nome)
        _CACHE_MODULOS[setor] = cache_atualizado

        # Restaura os módulos anteriores, sys.path e diretório de trabalho
        for nome, mod in modulos_anteriores.items():
            sys.modules[nome] = mod
        sys.path[:] = sys_path_anterior
        os.chdir(cwd_anterior)


# ============================================================
# DESPACHO DE INTEGRAÇÃO IN-PROCESS (SEM SERVIDORES EXTERNOS)
# ============================================================

def _identificar_setor_por_url(url: str) -> tuple[str | None, str]:
    parsed = urlparse(url)
    caminho = parsed.path or "/"
    if parsed.query:
        caminho = f"{caminho}?{parsed.query}"
    host_porta = parsed.netloc.lower()

    if ":8000" in host_porta or caminho.startswith("/api/v1/"):
        return "rastreabilidade", caminho
    if ":5002" in host_porta or caminho.startswith("/api/ocorrencias"):
        return "qualidade", caminho
    if ":5000" in host_porta or caminho.startswith("/api/manutencao") or caminho.startswith("/api/equipamentos"):
        return "manutencao", caminho
    if ":5003" in host_porta or caminho.startswith("/api/indicadores"):
        return "dashboard", caminho
    return None, caminho


class RespostaLocal:
    """Objeto de resposta compatível com requests.Response para chamadas in-process."""

    def __init__(self, status_code: int, dados: Any, text: str = ""):
        self.status_code = status_code
        self._dados = dados
        self.text = text

    def json(self) -> Any:
        return self._dados


def requisicao_fastapi_local(
    metodo: str,
    url: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> RespostaLocal:
    """Executa uma requisição diretamente contra o FastAPI do setor em memória."""
    from fastapi.testclient import TestClient

    setor, caminho = _identificar_setor_por_url(url)
    if not setor:
        return RespostaLocal(404, {"detail": f"Rota local não reconhecida: {url}"})

    with ambiente_modulo(setor):
        if setor == "rastreabilidade":
            from contextlib import closing
            from app import db, seed
            from app.main import app as fastapi_app
            db.inicializar()
            with closing(db.conectar()) as conn:
                if db.um(conn, "SELECT COUNT(*) AS n FROM status_producao")["n"] == 0:
                    seed.popular(conn)
        elif setor == "qualidade":
            import banco
            import migracao
            banco.preparar_banco()
            migracao.migrar()
            from api import app as fastapi_app
        elif setor == "manutencao":
            from database import ensure_database_initialized
            ensure_database_initialized()
            from api import app as fastapi_app
        elif setor == "dashboard":
            from api import app as fastapi_app
        else:
            return RespostaLocal(404, {"detail": "Setor desconhecido"})

        client = TestClient(fastapi_app)
        cabecalhos = dict(headers or {})
        resp = client.request(
            method=metodo.upper(),
            url=caminho,
            params=params,
            json=json_body,
            headers=cabecalhos,
        )
        try:
            corpo_json = resp.json()
        except Exception:
            corpo_json = {}
        return RespostaLocal(resp.status_code, corpo_json, resp.text)


def despachar_requisicao_local(
    metodo: str,
    url: str,
    corpo: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[bool, Any]:
    """
    Retorna (True, dados_json) ou (False, mensagem_erro) no formato esperado
    por `qualidade/integracao.py`.
    """
    try:
        resposta = requisicao_fastapi_local(metodo, url, json_body=corpo, headers=headers)
    except Exception as exc:
        return False, f"erro na integração interna ({exc})"

    if resposta.status_code >= 400:
        dados = resposta.json() if isinstance(resposta.json(), dict) else {}
        detalhe = dados.get("detail") or resposta.text or f"HTTP {resposta.status_code}"
        return False, f"resposta recusada ({detalhe})"
    return True, resposta.json()


class ClienteHttpLocal:
    """Cliente compatível com `requests` para o `ConectorEcossistema` do Dashboard."""

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> RespostaLocal:
        return requisicao_fastapi_local("GET", url, params=params, headers=headers)


# ============================================================
# SINCRONIZAÇÃO AUTOMÁTICA DO USUÁRIO LOGADO NOS 4 SUBSISTEMAS
# ============================================================

MAPA_CARGO_RASTREABILIDADE = {
    ADMINISTRADOR: "Administrador",
    SUPERVISOR: "Administrador",
    INSPETOR: "Inspetor de Qualidade",
    OPERADOR: "Operador",
    ALMOXARIFE: "Almoxarife",
    TECNICO: "Operador",
}

MAPA_PERFIL_QUALIDADE = {
    ADMINISTRADOR: "Administrador",
    SUPERVISOR: "Administrador",
    INSPETOR: "Inspetor de Qualidade",
    OPERADOR: "Operador",
    ALMOXARIFE: "Almoxarife",
    TECNICO: "Operador",
}

MAPA_PERFIL_MANUTENCAO = {
    ADMINISTRADOR: "GESTOR",
    SUPERVISOR: "GESTOR",
    TECNICO: "TECNICO",
    OPERADOR: "OPERADOR",
    INSPETOR: "OPERADOR",
    ALMOXARIFE: "OPERADOR",
}

MAPA_PERFIL_DASHBOARD = {
    ADMINISTRADOR: "Administrador",
    SUPERVISOR: "Supervisor de produção",
    OPERADOR: "Operador de estação",
    INSPETOR: "Inspetor de qualidade",
    TECNICO: "Manutenção",
    ALMOXARIFE: "Operador de estação",
}


def sincronizar_usuario_nos_modulos(usuario_erp: dict[str, Any], session_state: Any) -> None:
    """
    Garante que o colaborador autenticado no ERP exista nos bancos de dados dos
    4 módulos operacionais com o perfil correspondente à sua persona e preenche
    as chaves de sessão esperadas por cada módulo.
    """
    if not usuario_erp:
        return

    matricula = usuario_erp["matricula"].strip().upper()
    nome = usuario_erp["nome"].strip()
    perfil_erp = usuario_erp["perfil"]

    # 1. Rastreabilidade (rastreabilidade/database/amatech.db)
    cargo_ras = MAPA_CARGO_RASTREABILIDADE.get(perfil_erp, "Operador")
    with ambiente_modulo("rastreabilidade"):
        from contextlib import closing
        from app import db, seed
        db.inicializar()
        with closing(db.conectar()) as conn:
            if db.um(conn, "SELECT COUNT(*) AS n FROM status_producao")["n"] == 0:
                seed.popular(conn)
            with conn:
                row = conn.execute(
                    "SELECT id, matricula, nome, email, cargo, ativo FROM usuarios WHERE UPPER(matricula) = ?",
                    (matricula,),
                ).fetchone()
                if row is None:
                    email_padrao = f"{matricula.lower()}@amatech.com.br"
                    cur = conn.execute(
                        """
                        INSERT INTO usuarios (matricula, nome, email, senha_hash, cargo, ativo)
                        VALUES (?, ?, ?, '123456', ?, 1)
                        """,
                        (matricula, nome, email_padrao, cargo_ras),
                    )
                    id_ras = cur.lastrowid
                else:
                    id_ras = row["id"]
                    conn.execute(
                        "UPDATE usuarios SET nome = ?, cargo = ?, ativo = 1 WHERE id = ?",
                        (nome, cargo_ras, id_ras),
                    )
            session_state["ras_usuario"] = {
                "id": id_ras,
                "matricula": matricula,
                "nome": nome,
                "cargo": cargo_ras,
                "ativo": 1,
            }

    # 2. Qualidade (qualidade/banco/controle_qualidade.db)
    perfil_qld = MAPA_PERFIL_QUALIDADE.get(perfil_erp, "Operador")
    with ambiente_modulo("qualidade"):
        from contextlib import closing
        import banco
        import migracao
        banco.preparar_banco()
        migracao.migrar()
        with closing(banco.conectar()) as conn:
            row = conn.execute(
                "SELECT id_usuario FROM usuario WHERE UPPER(matricula) = ?",
                (matricula,),
            ).fetchone()
            if row is None:
                cur = conn.execute(
                    """
                    INSERT INTO usuario (matricula, nome_usuario, senha_usuario, perfil_usuario, ativo)
                    VALUES (?, ?, 'amatech1234', ?, 1)
                    """,
                    (matricula, nome, perfil_qld),
                )
                id_qld = cur.lastrowid
                conn.commit()
            else:
                id_qld = row["id_usuario"]
                conn.execute(
                    "UPDATE usuario SET nome_usuario = ?, perfil_usuario = ?, ativo = 1 WHERE id_usuario = ?",
                    (nome, perfil_qld, id_qld),
                )
                conn.commit()
        session_state["usuario_autenticado"] = {
            "id": id_qld,
            "matricula": matricula,
            "nome": nome,
            "perfil": perfil_qld,
        }
        session_state["ultimo_acesso"] = time.time()

    # 3. Manutenção (manutencao/manutencao.db)
    perfil_mnt = MAPA_PERFIL_MANUTENCAO.get(perfil_erp, "OPERADOR")
    with ambiente_modulo("manutencao"):
        from database import ensure_database_initialized, get_connection
        ensure_database_initialized()
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id FROM usuarios WHERE UPPER(matricula) = ?",
                (matricula,),
            ).fetchone()
            if row is None:
                cur = conn.execute(
                    """
                    INSERT INTO usuarios (nome, matricula, senha_hash, perfil, ativo)
                    VALUES (?, ?, 'amatech1234', ?, 1)
                    """,
                    (nome, matricula, perfil_mnt),
                )
                id_mnt = cur.lastrowid
                conn.commit()
            else:
                id_mnt = row["id"]
                conn.execute(
                    "UPDATE usuarios SET nome = ?, perfil = ?, ativo = 1 WHERE id = ?",
                    (nome, perfil_mnt, id_mnt),
                )
                conn.commit()
        finally:
            conn.close()
        session_state["usuario_logado"] = {
            "id": id_mnt,
            "nome": nome,
            "matricula": matricula,
            "perfil": perfil_mnt,
            "ativo": True,
        }

    # 4. Dashboard Industrial (dashboard/database/banco.db)
    perfil_dsh_nome = MAPA_PERFIL_DASHBOARD.get(perfil_erp, "Operador de estação")
    with ambiente_modulo("dashboard"):
        from acesso_dados import Repositorio
        from modelos import Perfil, Usuario
        from servicos.autenticacao import ServicoAutenticacao

        repo = Repositorio()
        perfil_row = repo.consultar_um(
            "SELECT id_perfil, nome, descricao FROM perfil WHERE nome = ?",
            (perfil_dsh_nome,),
        )
        if not perfil_row:
            perfil_row = repo.consultar_um("SELECT id_perfil, nome, descricao FROM perfil ORDER BY id_perfil LIMIT 1")

        login_dsh = matricula.lower()
        usr_row = repo.consultar_um(
            "SELECT id_usuario FROM usuario WHERE LOWER(login) = ?",
            (login_dsh,),
        )
        if usr_row is None:
            id_dsh = repo.executar(
                "INSERT INTO usuario (nome, login, senha_hash, id_perfil, ativo) VALUES (?, ?, ?, ?, 1)",
                (nome, login_dsh, ServicoAutenticacao.gerar_hash("amatech1234"), perfil_row["id_perfil"]),
            )
        else:
            id_dsh = usr_row["id_usuario"]
            repo.executar(
                "UPDATE usuario SET nome = ?, id_perfil = ?, ativo = 1 WHERE id_usuario = ?",
                (nome, perfil_row["id_perfil"], id_dsh),
            )

        session_state["usuario"] = Usuario(
            nome=nome,
            login=login_dsh,
            ativo=True,
            id=id_dsh,
            perfil=Perfil(
                nome=perfil_row["nome"],
                descricao=perfil_row["descricao"],
                id=perfil_row["id_perfil"],
            ),
        )
