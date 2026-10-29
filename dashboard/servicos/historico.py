"""ServicoHistorico: consultas das tabelas de histórico (T08, RF13) e das listas de últimos lançamentos das telas
de registro. Só lê dados; os cálculos dos indicadores ficam na CalculadoraIndicadores."""
import config
from acesso_dados import Repositorio
from servicos.calculadora import CalculadoraIndicadores
from servicos.formatos import ler_data_hora

NOMES_ORIGEM = {"rastreabilidade": "Rastreabilidade", "qualidade": "Qualidade", "manutencao": "Manutenção"}


def origem(linha):
    """De onde veio o dado: formulário, planilha ou sistema de outro setor (decisão 5.2.6)."""
    if linha.get("origem_sistema"):
        return "Sistema: " + NOMES_ORIGEM.get(linha["origem_sistema"], linha["origem_sistema"])
    if linha.get("id_importacao"):
        return f"Planilha #{linha['id_importacao']}"
    return "Formulário"


class ServicoHistorico:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()

    def _onde(self, filtro, prefixo, coluna_data="data", com_produto=True):
        return CalculadoraIndicadores._onde(filtro, prefixo, coluna_data, com_produto)

    def producao(self, filtro):
        onde, params = self._onde(filtro, "r.")
        linhas = self.repo.consultar(
            f"""SELECT r.id_producao, r.data, t.nome AS turno, p.modelo AS produto, r.qtd_realizada, r.qtd_aprovada,
                       r.qtd_reprovada, m.qtd_meta, u.nome AS registrado_por, r.registrado_em, r.id_importacao,
                       r.origem_sistema
                FROM registro_producao r JOIN turno t ON t.id_turno = r.id_turno
                JOIN produto p ON p.id_produto = r.id_produto JOIN usuario u ON u.id_usuario = r.registrado_por
                LEFT JOIN meta_producao m ON m.data = r.data AND m.id_turno = r.id_turno AND m.id_produto = r.id_produto
                WHERE {onde} ORDER BY r.data DESC, t.nome, p.modelo""", params)
        for l in linhas:
            l["pct_meta"] = round(l["qtd_realizada"] / l["qtd_meta"] * 100, 1) if l["qtd_meta"] else None
            l["origem"] = origem(l)
        return linhas

    def defeitos(self, filtro):
        onde, params = self._onde(filtro, "r.")
        linhas = self.repo.consultar(
            f"""SELECT d.id_defeito, d.data_hora, t.nome AS turno, p.modelo AS produto, td.descricao AS tipo_defeito,
                       e.nome AS estacao, mq.codigo AS maquina, d.quantidade,
                       COALESCE((SELECT SUM(rt.quantidade) FROM retrabalho rt WHERE rt.id_defeito = d.id_defeito), 0)
                           AS retrabalho,
                       d.observacao, u.nome AS registrado_por, d.id_importacao, d.origem_sistema, d.id_externo
                FROM defeito d JOIN registro_producao r ON r.id_producao = d.id_producao
                JOIN turno t ON t.id_turno = r.id_turno JOIN produto p ON p.id_produto = r.id_produto
                JOIN tipo_defeito td ON td.id_tipo_defeito = d.id_tipo_defeito
                JOIN estacao e ON e.id_estacao = d.id_estacao LEFT JOIN maquina mq ON mq.id_maquina = d.id_maquina
                JOIN usuario u ON u.id_usuario = d.registrado_por
                WHERE {onde} ORDER BY d.data_hora DESC""", params)
        for l in linhas:
            l["origem"] = origem(l)
        return linhas

    def paradas(self, filtro):
        onde, params = self._onde(filtro, "pa.", "date(pa.inicio)", com_produto=False)
        linhas = self.repo.consultar(
            f"""SELECT pa.id_parada, pa.inicio, pa.fim, t.nome AS turno, e.nome AS estacao, mq.codigo AS maquina,
                       mp.descricao AS motivo, mp.tipo AS tipo_motivo, pa.observacao, u.nome AS registrado_por,
                       pa.id_importacao, pa.origem_sistema, pa.id_externo
                FROM parada pa JOIN turno t ON t.id_turno = pa.id_turno JOIN estacao e ON e.id_estacao = pa.id_estacao
                JOIN motivo_parada mp ON mp.id_motivo = pa.id_motivo LEFT JOIN maquina mq ON mq.id_maquina = pa.id_maquina
                JOIN usuario u ON u.id_usuario = pa.registrado_por
                WHERE {onde} ORDER BY pa.inicio DESC""", params)
        return [self._com_duracao(l) for l in linhas]

    def perdas(self, filtro):
        onde, params = self._onde(filtro, "pe.")
        linhas = self.repo.consultar(
            f"""SELECT pe.id_perda, pe.data, t.nome AS turno, e.nome AS estacao, p.modelo AS produto,
                       tp.descricao AS tipo_perda, pe.quantidade, pe.observacao, u.nome AS registrado_por,
                       pe.id_importacao
                FROM perda pe JOIN turno t ON t.id_turno = pe.id_turno JOIN estacao e ON e.id_estacao = pe.id_estacao
                JOIN produto p ON p.id_produto = pe.id_produto JOIN tipo_perda tp ON tp.id_tipo_perda = pe.id_tipo_perda
                JOIN usuario u ON u.id_usuario = pe.registrado_por
                WHERE {onde} ORDER BY pe.data DESC, pe.id_perda DESC""", params)
        for l in linhas:
            l["origem"] = origem(l)
        return linhas

    def importacoes(self, limite=30):
        return self.repo.consultar(
            """SELECT i.id_importacao, i.data_hora, i.nome_arquivo, i.tipo_dado, u.nome AS usuario, i.linhas_lidas,
                      i.linhas_importadas, i.linhas_rejeitadas, i.status
               FROM importacao i JOIN usuario u ON u.id_usuario = i.id_usuario
               ORDER BY i.id_importacao DESC LIMIT ?""", (limite,))

    # ------------------------------------------------------------ listas das telas de registro
    def registros_producao_recentes(self, limite=50):
        """Opções de 'registro de produção de origem' na tela de Qualidade e últimos lançamentos da tela T03."""
        linhas = self.repo.consultar(
            """SELECT r.id_producao, r.data, t.nome AS turno, p.modelo AS produto, r.qtd_realizada, r.qtd_aprovada,
                      r.qtd_reprovada, u.nome AS registrado_por, r.registrado_em, r.id_importacao, r.origem_sistema
               FROM registro_producao r JOIN turno t ON t.id_turno = r.id_turno
               JOIN produto p ON p.id_produto = r.id_produto JOIN usuario u ON u.id_usuario = r.registrado_por
               ORDER BY r.data DESC, r.id_producao DESC LIMIT ?""", (limite,))
        for l in linhas:
            l["origem"] = origem(l)
        return linhas

    def metas_recentes(self, limite=30):
        return self.repo.consultar(
            """SELECT m.data, t.nome AS turno, p.modelo AS produto, m.qtd_meta, u.nome AS registrado_por
               FROM meta_producao m JOIN turno t ON t.id_turno = m.id_turno JOIN produto p ON p.id_produto = m.id_produto
               JOIN usuario u ON u.id_usuario = m.registrado_por ORDER BY m.data DESC, m.id_meta DESC LIMIT ?""",
            (limite,))

    def defeitos_recentes(self, limite=50):
        """Opções de 'defeito de origem' do retrabalho."""
        return self.repo.consultar(
            """SELECT d.id_defeito, d.data_hora, td.descricao AS tipo_defeito, e.nome AS estacao, d.quantidade,
                      COALESCE((SELECT SUM(rt.quantidade) FROM retrabalho rt WHERE rt.id_defeito = d.id_defeito), 0)
                          AS retrabalho
               FROM defeito d JOIN tipo_defeito td ON td.id_tipo_defeito = d.id_tipo_defeito
               JOIN estacao e ON e.id_estacao = d.id_estacao ORDER BY d.data_hora DESC LIMIT ?""", (limite,))

    def paradas_recentes(self, limite=30, em_andamento=None):
        filtro = "" if em_andamento is None else ("WHERE pa.fim IS NULL" if em_andamento else "WHERE pa.fim IS NOT NULL")
        linhas = self.repo.consultar(
            f"""SELECT pa.id_parada, pa.inicio, pa.fim, t.nome AS turno, e.nome AS estacao, mq.codigo AS maquina,
                       mp.descricao AS motivo, pa.observacao, u.nome AS registrado_por, pa.id_importacao,
                       pa.origem_sistema
                FROM parada pa JOIN turno t ON t.id_turno = pa.id_turno JOIN estacao e ON e.id_estacao = pa.id_estacao
                JOIN motivo_parada mp ON mp.id_motivo = pa.id_motivo LEFT JOIN maquina mq ON mq.id_maquina = pa.id_maquina
                JOIN usuario u ON u.id_usuario = pa.registrado_por {filtro}
                ORDER BY pa.inicio DESC LIMIT ?""", (limite,))
        return [self._com_duracao(l) for l in linhas]

    def perdas_recentes(self, limite=30):
        linhas = self.repo.consultar(
            """SELECT pe.data, t.nome AS turno, e.nome AS estacao, p.modelo AS produto, tp.descricao AS tipo_perda,
                      pe.quantidade, pe.observacao, u.nome AS registrado_por, pe.id_importacao
               FROM perda pe JOIN turno t ON t.id_turno = pe.id_turno JOIN estacao e ON e.id_estacao = pe.id_estacao
               JOIN produto p ON p.id_produto = pe.id_produto JOIN tipo_perda tp ON tp.id_tipo_perda = pe.id_tipo_perda
               JOIN usuario u ON u.id_usuario = pe.registrado_por ORDER BY pe.data DESC, pe.id_perda DESC LIMIT ?""",
            (limite,))
        for l in linhas:
            l["origem"] = origem(l)
        return linhas

    @staticmethod
    def _com_duracao(linha):
        inicio = ler_data_hora(linha["inicio"])
        fim = ler_data_hora(linha["fim"]) if linha["fim"] else None
        linha["duracao_min"] = round(((fim or config.agora()) - inicio).total_seconds() / 60, 1)
        linha["situacao"] = "Encerrada" if fim else "Em andamento"
        linha["origem"] = origem(linha)
        return linha
