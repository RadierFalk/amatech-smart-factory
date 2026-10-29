"""CalculadoraIndicadores: os seis indicadores do painel, sempre para um período (RF06 a RF09, RF15, RN03, RN05).

Fórmulas (relatório da OA2, seção 2.4):
  Atendimento da meta  = produção realizada ÷ meta × 100                       (%)
  Produtividade        = produção realizada ÷ (duração dos turnos − paradas)  (unid/h)
  Índice de defeitos   = reprovados ÷ produção realizada × 100                 (%)
  Índice de retrabalho = quantidade em retrabalho ÷ produção realizada × 100   (%)
  Tempo de parada      = soma das durações das paradas                         (min)
  Perdas               = soma das quantidades perdidas, por tipo               (unid)

Os indicadores não ficam no banco: são calculados a cada consulta, então nunca ficam desatualizados.
"""
from dataclasses import dataclass, field

import config
from acesso_dados import Repositorio
from modelos import Estacao, Parada, Turno
from servicos.formatos import ler_data_hora, texto_data


@dataclass
class TempoParada:
    minutos: float = 0.0
    encerradas: int = 0
    em_andamento: int = 0


@dataclass
class ResultadoIndicadores:
    realizada: int = 0
    aprovada: int = 0
    reprovada: int = 0
    meta: int = 0
    atendimento_meta: float | None = None        # None = "sem meta" (RN03)
    produtividade: float | None = None
    minutos_turno: int = 0
    minutos_produtivos: float = 0.0
    indice_defeitos: float | None = None
    retrabalho: int = 0
    indice_retrabalho: float | None = None
    tempo_parada: TempoParada = field(default_factory=TempoParada)
    perdas: int = 0
    perdas_por_tipo: list = field(default_factory=list)

    @property
    def tem_dados(self):
        return self.realizada > 0 or self.meta > 0 or self.tempo_parada.minutos > 0 or self.perdas > 0


def _percentual(parte, total):
    return parte / total * 100 if total else None


class CalculadoraIndicadores:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()

    # ------------------------------------------------------------ filtros SQL
    @staticmethod
    def _onde(filtro, prefixo="", coluna_data="data", com_produto=True):
        """Condições do filtro: período (sempre, RN05), turno e produto quando escolhidos."""
        coluna = coluna_data if "(" in coluna_data else prefixo + coluna_data   # expressão (ex.: date(p.inicio)) já vem completa
        condicoes = [f"{coluna} BETWEEN ? AND ?"]
        params = [texto_data(filtro.data_inicial), texto_data(filtro.data_final)]
        if filtro.id_turno:
            condicoes.append(f"{prefixo}id_turno = ?")
            params.append(filtro.id_turno)
        if com_produto and filtro.id_produto:
            condicoes.append(f"{prefixo}id_produto = ?")
            params.append(filtro.id_produto)
        return " AND ".join(condicoes), params

    # ------------------------------------------------------------ indicadores
    def producao(self, filtro):
        onde, params = self._onde(filtro)
        linha = self.repo.consultar_um(
            f"""SELECT COALESCE(SUM(qtd_realizada), 0) AS realizada, COALESCE(SUM(qtd_aprovada), 0) AS aprovada,
                       COALESCE(SUM(qtd_reprovada), 0) AS reprovada
                FROM registro_producao WHERE {onde}""", params)
        return linha["realizada"], linha["aprovada"], linha["reprovada"]

    def meta(self, filtro):
        onde, params = self._onde(filtro)
        return self.repo.consultar_um(
            f"SELECT COALESCE(SUM(qtd_meta), 0) AS meta FROM meta_producao WHERE {onde}", params)["meta"]

    def atendimento_meta(self, filtro):
        """RN03: sem meta cadastrada, devolve None ("sem meta"), sem dividir por zero."""
        meta = self.meta(filtro)
        return _percentual(self.producao(filtro)[0], meta) if meta else None

    def minutos_turno(self, filtro):
        """Duração dos turnos que tiveram produção registrada no período."""
        onde, params = self._onde(filtro)
        return self.repo.consultar_um(
            f"""SELECT COALESCE(SUM(t.duracao_min), 0) AS minutos
                FROM (SELECT DISTINCT data, id_turno FROM registro_producao WHERE {onde}) r
                JOIN turno t ON t.id_turno = r.id_turno""", params)["minutos"]

    def produtividade(self, filtro):
        realizada = self.producao(filtro)[0]
        minutos_produtivos = self.minutos_turno(filtro) - self.tempo_parada(filtro).minutos
        if not realizada or minutos_produtivos <= 0:
            return None
        return realizada / (minutos_produtivos / 60)

    def indice_defeitos(self, filtro):
        realizada, _, reprovada = self.producao(filtro)
        return _percentual(reprovada, realizada)

    def quantidade_retrabalho(self, filtro):
        onde, params = self._onde(filtro, prefixo="r.")
        return self.repo.consultar_um(
            f"""SELECT COALESCE(SUM(rt.quantidade), 0) AS total FROM retrabalho rt
                JOIN defeito d ON d.id_defeito = rt.id_defeito
                JOIN registro_producao r ON r.id_producao = d.id_producao WHERE {onde}""", params)["total"]

    def indice_retrabalho(self, filtro):
        return _percentual(self.quantidade_retrabalho(filtro), self.producao(filtro)[0])

    def paradas(self, filtro):
        """Paradas do período como objetos Parada (a parada não tem produto, então o filtro de produto não se aplica)."""
        onde, params = self._onde(filtro, prefixo="p.", coluna_data="date(p.inicio)", com_produto=False)
        linhas = self.repo.consultar(
            f"""SELECT p.*, e.nome AS estacao, t.nome AS turno, t.hora_inicio, t.hora_fim, t.duracao_min,
                       mp.descricao AS motivo
                FROM parada p JOIN estacao e ON e.id_estacao = p.id_estacao
                JOIN turno t ON t.id_turno = p.id_turno JOIN motivo_parada mp ON mp.id_motivo = p.id_motivo
                WHERE {onde} ORDER BY p.inicio""", params)
        return [Parada(estacao=Estacao(nome=l["estacao"]), motivo=l["motivo"], id=l["id_parada"],
                       turno=Turno(nome=l["turno"], hora_inicio=l["hora_inicio"], hora_fim=l["hora_fim"],
                                   duracao_min=l["duracao_min"], id=l["id_turno"]),
                       inicio=ler_data_hora(l["inicio"]), fim=ler_data_hora(l["fim"]) if l["fim"] else None,
                       observacao=l["observacao"]) for l in linhas]

    def tempo_parada(self, filtro):
        """Paradas em andamento contam até agora, para o painel mostrar a perda já durante o turno."""
        agora = config.agora()
        resultado = TempoParada()
        for parada in self.paradas(filtro):
            resultado.minutos += parada.calcular_duracao(ate=agora)
            if parada.fim:
                resultado.encerradas += 1
            else:
                resultado.em_andamento += 1
        return resultado

    def perdas(self, filtro):
        onde, params = self._onde(filtro, prefixo="p.")
        return self.repo.consultar(
            f"""SELECT tp.descricao AS tipo, SUM(p.quantidade) AS quantidade FROM perda p
                JOIN tipo_perda tp ON tp.id_tipo_perda = p.id_tipo_perda WHERE {onde}
                GROUP BY tp.descricao ORDER BY quantidade DESC""", params)

    def calcular(self, filtro):
        """Todos os indicadores de uma vez, para o painel (UC12)."""
        filtro.validar()
        r = ResultadoIndicadores()
        r.realizada, r.aprovada, r.reprovada = self.producao(filtro)
        r.meta = self.meta(filtro)
        r.atendimento_meta = _percentual(r.realizada, r.meta) if r.meta else None
        r.tempo_parada = self.tempo_parada(filtro)
        r.minutos_turno = self.minutos_turno(filtro)
        r.minutos_produtivos = max(r.minutos_turno - r.tempo_parada.minutos, 0)
        r.produtividade = r.realizada / (r.minutos_produtivos / 60) if r.realizada and r.minutos_produtivos else None
        r.indice_defeitos = _percentual(r.reprovada, r.realizada)
        r.retrabalho = self.quantidade_retrabalho(filtro)
        r.indice_retrabalho = _percentual(r.retrabalho, r.realizada)
        r.perdas_por_tipo = self.perdas(filtro)
        r.perdas = sum(p["quantidade"] for p in r.perdas_por_tipo)
        return r

    # ------------------------------------------------------------ dados dos gráficos (RF11)
    def producao_x_meta(self, filtro):
        onde_r, params_r = self._onde(filtro, prefixo="r.")
        onde_m, params_m = self._onde(filtro, prefixo="m.")
        return self.repo.consultar(
            f"""SELECT pr.modelo AS produto,
                       COALESCE((SELECT SUM(m.qtd_meta) FROM meta_producao m WHERE m.id_produto = pr.id_produto AND {onde_m}), 0) AS meta,
                       COALESCE((SELECT SUM(r.qtd_realizada) FROM registro_producao r WHERE r.id_produto = pr.id_produto AND {onde_r}), 0) AS realizada
                FROM produto pr ORDER BY pr.modelo""", params_m + params_r)

    def defeitos_por_estacao(self, filtro):
        onde, params = self._onde(filtro, prefixo="r.")
        return self.repo.consultar(
            f"""SELECT e.nome AS estacao, SUM(d.quantidade) AS quantidade FROM defeito d
                JOIN registro_producao r ON r.id_producao = d.id_producao
                JOIN estacao e ON e.id_estacao = d.id_estacao WHERE {onde}
                GROUP BY e.nome ORDER BY quantidade DESC""", params)

    def parada_por_turno(self, filtro):
        agora = config.agora()
        minutos = {}
        for parada in self.paradas(filtro):
            minutos[parada.turno.nome] = minutos.get(parada.turno.nome, 0) + parada.calcular_duracao(ate=agora)
        return [{"turno": turno, "minutos": round(valor, 1)} for turno, valor in sorted(minutos.items())]

    def retrabalho_por_estacao(self, filtro):
        onde, params = self._onde(filtro, prefixo="r.")
        return self.repo.consultar(
            f"""SELECT e.nome AS estacao, SUM(rt.quantidade) AS quantidade FROM retrabalho rt
                JOIN defeito d ON d.id_defeito = rt.id_defeito
                JOIN registro_producao r ON r.id_producao = d.id_producao
                JOIN estacao e ON e.id_estacao = rt.id_estacao_retorno WHERE {onde}
                GROUP BY e.nome ORDER BY quantidade DESC""", params)

    def paradas_em_andamento(self):
        """Todas as paradas sem fim, de qualquer data: o aviso do painel não depende do filtro."""
        return self.repo.consultar(
            """SELECT p.id_parada, e.nome AS estacao, m.codigo AS maquina, mp.descricao AS motivo, p.inicio,
                      p.origem_sistema
               FROM parada p JOIN estacao e ON e.id_estacao = p.id_estacao
               JOIN motivo_parada mp ON mp.id_motivo = p.id_motivo
               LEFT JOIN maquina m ON m.id_maquina = p.id_maquina
               WHERE p.fim IS NULL ORDER BY p.inicio""")
