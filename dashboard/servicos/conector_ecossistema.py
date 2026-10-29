"""ConectorEcossistema: busca os dados dos outros setores pelas APIs deles e os grava pelo ImportadorCSV (OA3).

Cada setor vira uma "planilha" com as mesmas colunas da importação manual, então valem as mesmas regras:
RN06 (tudo ou nada, por setor), validações do ServicoRegistro e registro na tabela importacao.
Cada linha leva origem_sistema e id_externo; sincronizar de novo atualiza em vez de duplicar.

Ordem: cadastros dos donos (modelos e máquinas) -> produção -> defeitos -> paradas
(os defeitos precisam da produção do mesmo dia, turno e modelo).
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

import config
from acesso_dados import Repositorio
from servicos.cadastros import ServicoCadastros
from servicos.cadastros_comuns import ESTACAO_RETORNO_REPROCESSO
from servicos.formatos import texto_data, texto_data_hora
from servicos.importador_csv import ImportadorCSV

NOMES_SETORES = {"rastreabilidade": "Rastreabilidade", "qualidade": "Qualidade", "manutencao": "Manutenção"}


@dataclass
class ResultadoSetor:
    setor: str                      # rastreabilidade, qualidade ou manutencao
    status: str                     # concluida, rejeitada, sem_dados ou fora_do_ar
    mensagem: str = ""
    lidas: int = 0
    importadas: int = 0
    erros: list = field(default_factory=list)       # (linha, coluna, problema), como na importação
    ignorados: list = field(default_factory=list)   # textos: eventos fora dos turnos, chamados cancelados...

    @property
    def nome(self):
        return NOMES_SETORES[self.setor]


class SistemaForaDoAr(Exception):
    pass


def utc_para_local(texto):
    """'2026-10-28T13:05:00Z' (ou sem o Z) em UTC -> datetime local da fábrica, sem fuso."""
    momento = datetime.fromisoformat(texto.strip().rstrip("Zz").replace(" ", "T")[:19])
    return momento + timedelta(hours=config.FUSO_HORAS)


def local_para_utc(momento):
    return (momento - timedelta(hours=config.FUSO_HORAS)).strftime("%Y-%m-%dT%H:%M:%SZ")


class ConectorEcossistema:
    def __init__(self, repo=None, http=None):
        self.repo = repo or Repositorio()
        self.http = http or requests
        self.importador = ImportadorCSV(self.repo)
        self.cadastros = ServicoCadastros(self.repo)

    # ------------------------------------------------------------ HTTP
    def _get(self, url, params=None, chave=None):
        try:
            resposta = self.http.get(url, params=params, headers={"X-API-Key": chave} if chave else None,
                                     timeout=config.TEMPO_LIMITE_HTTP)
        except requests.RequestException as erro:
            raise SistemaForaDoAr(f"sem resposta de {url}") from erro
        if resposta.status_code >= 400:
            raise SistemaForaDoAr(f"{url} respondeu com erro {resposta.status_code}")
        return resposta.json()

    # ------------------------------------------------------------ sincronização (T07)
    def sincronizar(self, data_inicial, data_final, usuario_id):
        """Sincroniza os três setores no período (datas locais, inclusive). Devolve um ResultadoSetor por setor."""
        avisos_cadastro = self.sincronizar_cadastros()
        periodo = f"{data_inicial:%d/%m} a {data_final:%d/%m/%Y}"
        resultados = []
        for setor, buscar, tipo in (("rastreabilidade", self.linhas_producao, "producao"),
                                    ("qualidade", self.linhas_defeitos, "defeito"),
                                    ("manutencao", self.linhas_paradas, "parada")):
            try:
                linhas, ignorados = buscar(data_inicial, data_final)
            except SistemaForaDoAr as erro:
                resultados.append(ResultadoSetor(setor, "fora_do_ar", f"Sistema fora do ar ({erro})."))
                continue
            resultados.append(self._importar(setor, tipo, linhas, ignorados, usuario_id,
                                             f"Sincronização: {NOMES_SETORES[setor]} ({periodo})"))
        if avisos_cadastro:
            resultados[0].ignorados = avisos_cadastro + resultados[0].ignorados
        return resultados

    def _importar(self, setor, tipo, linhas, ignorados, usuario_id, nome):
        if not linhas:
            return ResultadoSetor(setor, "sem_dados", "Nenhum registro no período.", ignorados=ignorados)
        r = self.importador.importar_linhas(linhas, tipo, usuario_id, nome)
        if r.aceita:
            mensagem = f"{r.importadas} registro(s) sincronizado(s)."
        else:
            mensagem = f"Recusado: {r.rejeitadas} registro(s) com erro. Nada deste setor foi gravado (RN06)."
        return ResultadoSetor(setor, r.status, mensagem, r.lidas, r.importadas, r.erros, ignorados)

    # ------------------------------------------------------------ cadastros dos donos
    def sincronizar_cadastros(self):
        """Modelos da Rastreabilidade e máquinas da Manutenção. Devolve avisos (ex.: máquina de setor desconhecido).
        Um sistema fora do ar aqui não é erro: o setor dele aparece como fora do ar logo depois."""
        avisos = []
        try:
            for modelo in self._get(f"{config.RASTREABILIDADE_URL}/api/v1/produtos",
                                    chave=config.RASTREABILIDADE_CHAVE):
                self.cadastros.garantir_produto(modelo["nome"], modelo.get("codigo"))
        except SistemaForaDoAr:
            pass
        try:
            for maquina in self._get(f"{config.MANUTENCAO_URL}/api/equipamentos"):
                id_estacao = self.cadastros.buscar_id("estacao", maquina["setor"])
                if id_estacao is None:
                    avisos.append(f"Máquina {maquina['codigo_tag']}: setor \"{maquina['setor']}\" sem estação "
                                  "correspondente no Dashboard (não cadastrada).")
                    continue
                self.cadastros.garantir_maquina(maquina["codigo_tag"], maquina["nome"], id_estacao)
        except SistemaForaDoAr:
            pass
        return avisos

    def _turno(self, momento, descricao, ignorados):
        turno = self.cadastros.turno_por_horario(momento)
        if turno is None:
            ignorados.append(f"{descricao}: {momento:%d/%m/%Y %H:%M} fora dos turnos cadastrados.")
        return turno

    # ------------------------------------------------------------ Rastreabilidade -> produção
    def linhas_producao(self, data_inicial, data_final):
        """Cada Aprovado ou Reprovado é uma unidade produzida no turno: realizada = aprovados + reprovados."""
        inicio = datetime.combine(data_inicial, datetime.min.time())
        fim = datetime.combine(data_final + timedelta(days=1), datetime.min.time()) - timedelta(seconds=1)
        passagens = self._get(f"{config.RASTREABILIDADE_URL}/api/v1/passagens",
                              {"de": local_para_utc(inicio), "ate": local_para_utc(fim)}, config.RASTREABILIDADE_CHAVE)
        contagem, ignorados = {}, []
        for p in passagens:
            if p["status"] not in ("Aprovado", "Reprovado"):
                continue
            momento = utc_para_local(p["em"])
            if not data_inicial <= momento.date() <= data_final:
                continue
            turno = self._turno(momento, f"{p['numero_serie']} ({p['status']})", ignorados)
            if turno is None:
                continue
            chave = (texto_data(momento), turno["nome"], p["modelo"]["nome"])
            aprovados, reprovados = contagem.get(chave, (0, 0))
            contagem[chave] = (aprovados + 1, reprovados) if p["status"] == "Aprovado" else (aprovados, reprovados + 1)
        linhas = [{"data": data, "turno": turno, "produto": modelo, "qtd_realizada": a + r, "qtd_aprovada": a,
                   "qtd_reprovada": r, "origem_sistema": "rastreabilidade", "id_externo": f"{data}|{turno}|{modelo}"}
                  for (data, turno, modelo), (a, r) in sorted(contagem.items())]
        return linhas, ignorados

    # ------------------------------------------------------------ Qualidade -> defeitos e retrabalho
    def linhas_defeitos(self, data_inicial, data_final):
        """Uma ocorrência = um defeito de quantidade 1. Em_reprocesso também gera retrabalho na Montagem final."""
        ocorrencias = self._get(f"{config.QUALIDADE_URL}/api/ocorrencias",
                                {"de": texto_data(data_inicial), "ate": texto_data(data_final)})
        linhas, ignorados = [], []
        for o in ocorrencias:
            momento = datetime.fromisoformat(f"{o['data_ocorrencia']}T{o['hora_ocorrencia']}"[:19])
            if not data_inicial <= momento.date() <= data_final:
                continue
            id_externo = f"QLD-{o['id_ocorrencia']}"
            turno = self._turno(momento, f"Ocorrência {id_externo}", ignorados)
            if turno is None:
                continue
            linha = {"data": texto_data(momento), "turno": turno["nome"], "produto": o["modelo_produto"],
                     "tipo_defeito": o["tipo_defeito"], "estacao": o["estacao"], "maquina_codigo": o["maquina"],
                     "quantidade": 1, "data_hora": texto_data_hora(momento),
                     "observacao": f"{o['produto']}: {o['observacao_ocorrencia'] or ''}".strip(),
                     "origem_sistema": "qualidade", "id_externo": id_externo}
            if o["situacao_produto"] == "Em_reprocesso":
                linha.update(estacao_retorno=ESTACAO_RETORNO_REPROCESSO,
                             motivo_retrabalho=o["acao_realizada"] or "Reprocesso", qtd_retrabalho=1)
            linhas.append(linha)
        return linhas, ignorados

    # ------------------------------------------------------------ Manutenção -> paradas
    def linhas_paradas(self, data_inicial, data_final):
        """Chamado = parada da máquina, da abertura ao fim do atendimento. Cancelados não contam."""
        chamados = self._get(f"{config.MANUTENCAO_URL}/api/manutencao/chamados")
        linhas, ignorados = [], []
        for c in chamados:
            id_externo = f"MNT-{c['id_chamado']}"
            if c["status_chamado"] == "CANCELADO":
                ignorados.append(f"Chamado {id_externo} ({c['equipamento_tag']}): cancelado.")
                continue
            inicio = utc_para_local(c["data_hora_abertura"])
            if not data_inicial <= inicio.date() <= data_final:
                continue
            turno = self._turno(inicio, f"Chamado {id_externo}", ignorados)
            if turno is None:
                continue
            fim = utc_para_local(c["data_hora_fim"]) if c.get("data_hora_fim") else None
            if fim and fim.replace(second=0) <= inicio.replace(second=0):
                fim = inicio.replace(second=0) + timedelta(minutes=1)   # o banco guarda minutos: evita fim = início
            linhas.append({"estacao": c["setor"], "maquina_codigo": c["equipamento_tag"], "turno": turno["nome"],
                           "motivo": c["tipo_manutencao"], "inicio": texto_data_hora(inicio),
                           "fim": texto_data_hora(fim) if fim else None, "observacao": c["descricao_falha"],
                           "origem_sistema": "manutencao", "id_externo": id_externo})
        return linhas, ignorados
