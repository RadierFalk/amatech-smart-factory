"""Testes das regras de negócio (SQLite temporário, sem precisar subir o servidor).
Rodar:  python -m unittest discover -s tests -v
"""
import tempfile
import unittest
from pathlib import Path

from app import config, seed
from app.db import conectar, um
from app.erros import ErroNegocio
from app.servicos import cadastros, materiais, producao, relatorios


class BaseBanco(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = Path(self.tmp.name) / "teste.db"
        seed.recriar_banco()
        self.conn = conectar()
        self.admin = um(self.conn, "SELECT id, nome FROM usuarios WHERE matricula = 'MAT-0001'")
        self.almox = um(self.conn, "SELECT id, nome FROM usuarios WHERE matricula = 'MAT-0100'")
        self.status = {s["nome_status"]: s["id"] for s in cadastros.listar_status(self.conn)}
        self.produto = cadastros.listar_produtos(self.conn)[0]["idprd"]

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()


class TestProducao(BaseBanco):
    def test_criar_gera_serie_id_unico_e_historico(self):
        a = producao.criar_producao(self.conn, self.produto, None, self.admin)
        b = producao.criar_producao(self.conn, self.produto, None, self.admin)
        self.assertEqual(a["numero_serie"], "AMT-000031")
        self.assertEqual(b["numero_serie"], "AMT-000032")
        self.assertTrue(a["id_unica_producao"].startswith("PRD-AMT-000031-"))
        self.assertEqual(a["status_nome"], "Em Fila")
        self.assertEqual(len(a["historico"]), 1)

    def test_numero_de_serie_nao_e_reutilizado_apos_excluir(self):
        a = producao.criar_producao(self.conn, self.produto, None, self.admin)
        producao.excluir_producao(self.conn, a["id"])
        b = producao.criar_producao(self.conn, self.produto, None, self.admin)
        self.assertEqual(b["numero_serie"], "AMT-000032")

    def test_avancar_etapa_grava_historico_com_responsavel(self):
        a = producao.criar_producao(self.conn, self.produto, None, self.admin)
        r = producao.avancar_etapa(self.conn, a["id"], self.status["Em Montagem"], self.almox["id"], self.admin)
        self.assertEqual(r["status_nome"], "Em Montagem")
        self.assertEqual(r["responsavel_nome"], self.almox["nome"])
        self.assertEqual([h["status_nome"] for h in r["historico"]], ["Em Fila", "Em Montagem"])
        self.assertEqual(r["historico"][-1]["usuario_nome"], self.admin["nome"])
        self.assertEqual(r["proxima_etapa_sugerida_id"], self.status["Em Teste"])

    def test_nao_avanca_para_a_mesma_etapa(self):
        a = producao.criar_producao(self.conn, self.produto, None, self.admin)
        with self.assertRaises(ErroNegocio) as e:
            producao.avancar_etapa(self.conn, a["id"], self.status["Em Fila"], None, self.admin)
        self.assertEqual(e.exception.status, 409)

    def test_reprovar_exige_falha_e_motivo_e_registra_nao_conformidade(self):
        a = producao.criar_producao(self.conn, self.produto, None, self.admin)
        with self.assertRaises(ErroNegocio):
            producao.avancar_etapa(self.conn, a["id"], self.status["Reprovado"], None, self.admin)
        r = producao.avancar_etapa(self.conn, a["id"], self.status["Reprovado"], None, self.admin,
                                   "Tela quebrada", "Defeito de tela")
        self.assertEqual(len(r["nao_conformidades"]), 1)
        self.assertEqual(r["nao_conformidades"][0]["motivo_reprovacao"], "Defeito de tela")

    def test_atualizacao_por_maquina(self):
        a = producao.criar_producao(self.conn, self.produto, None, self.admin)
        r = producao.atualizar_por_maquina(self.conn, a["numero_serie"], "em teste", "Testador 02")
        self.assertTrue(r["alterado"])
        self.assertEqual(r["producao"]["historico"][-1]["origem_atualizacao"], "MAQUINA/IOT")
        de_novo = producao.atualizar_por_maquina(self.conn, a["numero_serie"], "Em Teste")
        self.assertFalse(de_novo["alterado"])
        with self.assertRaises(ErroNegocio):
            producao.atualizar_por_maquina(self.conn, "AMT-999999", "Em Teste")

    def test_consulta_por_serie_traz_producoes_do_mesmo_modelo(self):
        r = producao.listar_producoes(self.conn, q="AMT-000001")
        self.assertEqual(len(r), 1)
        d = producao.obter_producao(self.conn, r[0]["id"])
        self.assertGreater(len(d["mesmo_modelo"]), 1)
        self.assertGreater(len(d["historico"]), 3)

    def test_excluir_producao_com_baixa_e_bloqueado(self):
        with self.assertRaises(ErroNegocio) as e:
            producao.excluir_producao(self.conn, 1)
        self.assertEqual(e.exception.status, 409)


class TestProdutosComponentes(BaseBanco):
    def _dois_componentes(self):
        comps = cadastros.listar_componentes(self.conn)
        return comps[0]["idcmp"], comps[1]["idcmp"], comps[2]["idcmp"]

    def test_vinculo_cria_altera_e_remove(self):
        c1, c2, c3 = self._dois_componentes()
        p = cadastros.criar_produto(self.conn, {"nome_modelo": "AMT X", "codigo_modelo": "x1", "quantidade": 10,
                                                "componentes": [{"componente_id": c1, "quantidade_necessaria": 1},
                                                                {"componente_id": c2, "quantidade_necessaria": 2}]}, self.admin)
        self.assertEqual(p["codigo_modelo"], "X1")
        self.assertEqual({c["componente_id"]: c["quantidade_necessaria"] for c in p["componentes"]}, {c1: 1, c2: 2})
        p = cadastros.atualizar_produto(self.conn, p["idprd"], {"nome_modelo": "AMT X", "codigo_modelo": "X1", "quantidade": 10,
                                                                "componentes": [{"componente_id": c2, "quantidade_necessaria": 4},
                                                                                {"componente_id": c3, "quantidade_necessaria": 1}]}, self.admin)
        self.assertEqual({c["componente_id"]: c["quantidade_necessaria"] for c in p["componentes"]}, {c2: 4, c3: 1})

    def test_componente_duplicado_no_mesmo_produto_e_recusado_e_nada_e_gravado(self):
        c1, _, _ = self._dois_componentes()
        antes = len(cadastros.listar_produtos(self.conn))
        with self.assertRaises(ErroNegocio):
            cadastros.criar_produto(self.conn, {"nome_modelo": "AMT Y", "codigo_modelo": "Y1", "quantidade": None,
                                                "componentes": [{"componente_id": c1, "quantidade_necessaria": 1},
                                                                {"componente_id": c1, "quantidade_necessaria": 2}]}, self.admin)
        self.assertEqual(len(cadastros.listar_produtos(self.conn)), antes)   # rollback da transação

    def test_excluir_produto_com_producoes_e_bloqueado(self):
        with self.assertRaises(ErroNegocio) as e:
            cadastros.excluir_produto(self.conn, self.produto)
        self.assertEqual(e.exception.status, 409)

    def test_chave_estrangeira_esta_ativa(self):
        with self.assertRaises(ErroNegocio):
            cadastros.excluir_status(self.conn, self.status["Em Fila"])   # status em uso
        with self.assertRaises(ErroNegocio):
            cadastros.excluir_componente(self.conn, cadastros.listar_componentes(self.conn)[0]["idcmp"])


class TestMateriais(BaseBanco):
    def setUp(self):
        super().setUp()
        self.prod = producao.criar_producao(self.conn, self.produto, None, self.admin)

    def _estoque(self, idcmp):
        return cadastros.obter_componente(self.conn, idcmp)["qtd_estoque"]

    def _componente(self):
        """Teclado: tem bastante estoque (a bateria do seed está com estoque crítico de propósito)."""
        return next(x["idcmp"] for x in cadastros.listar_componentes(self.conn) if x["codigo_sku"] == "KBD-ABNT2")

    def test_solicitacoes_vem_da_lista_do_produto_sem_duplicar(self):
        n = len(cadastros.obter_produto(self.conn, self.produto)["componentes"])
        r = materiais.gerar_solicitacoes_da_producao(self.conn, self.prod["id"], self.admin)
        self.assertEqual(r, {"criadas": n, "ignoradas": 0})
        r2 = materiais.gerar_solicitacoes_da_producao(self.conn, self.prod["id"], self.admin)
        self.assertEqual(r2, {"criadas": 0, "ignoradas": n})

    def test_baixa_parcial_total_e_devolucao_de_estoque(self):
        c = self._componente()
        s = materiais.criar_solicitacao(self.conn, self.prod["id"], c, 5, self.admin)
        est0 = self._estoque(c)
        b1 = materiais.criar_baixa(self.conn, s["id"], 2, self.almox)
        self.assertEqual(materiais.obter_solicitacao(self.conn, s["id"])["status_solicitacao"], "PARCIAL")
        self.assertEqual(self._estoque(c), est0 - 2)
        materiais.criar_baixa(self.conn, s["id"], 3, self.almox)
        self.assertEqual(materiais.obter_solicitacao(self.conn, s["id"])["status_solicitacao"], "ATENDIDA")
        materiais.excluir_baixa(self.conn, b1["id"])
        self.assertEqual(materiais.obter_solicitacao(self.conn, s["id"])["status_solicitacao"], "PARCIAL")
        self.assertEqual(self._estoque(c), est0 - 3)

    def test_baixa_maior_que_saldo_ou_estoque_e_recusada(self):
        c = self._componente()
        s = materiais.criar_solicitacao(self.conn, self.prod["id"], c, 5, self.admin)
        with self.assertRaises(ErroNegocio) as e:
            materiais.criar_baixa(self.conn, s["id"], 6, self.almox)
        self.assertIn("saldo", e.exception.mensagem)
        bat = next(x for x in cadastros.listar_componentes(self.conn) if x["codigo_sku"] == "BAT-45WH")
        s2 = materiais.criar_solicitacao(self.conn, self.prod["id"], bat["idcmp"], 10, self.admin)
        with self.assertRaises(ErroNegocio) as e:
            materiais.criar_baixa(self.conn, s2["id"], 10, self.almox)   # estoque = 4
        self.assertIn("Estoque insuficiente", e.exception.mensagem)
        self.assertEqual(self._estoque(bat["idcmp"]), 4)                 # nada foi baixado

    def test_editar_baixa_ajusta_estoque(self):
        c = self._componente()
        s = materiais.criar_solicitacao(self.conn, self.prod["id"], c, 5, self.admin)
        est0 = self._estoque(c)
        b = materiais.criar_baixa(self.conn, s["id"], 2, self.almox)
        materiais.atualizar_baixa(self.conn, b["id"], 4)
        self.assertEqual(self._estoque(c), est0 - 4)
        materiais.atualizar_baixa(self.conn, b["id"], 1)
        self.assertEqual(self._estoque(c), est0 - 1)

    def test_cancelar_e_excluir_solicitacao(self):
        c = self._componente()
        s = materiais.criar_solicitacao(self.conn, self.prod["id"], c, 5, self.admin)
        s = materiais.atualizar_solicitacao(self.conn, s["id"], 5, True)
        self.assertEqual(s["status_solicitacao"], "CANCELADA")
        with self.assertRaises(ErroNegocio):
            materiais.criar_baixa(self.conn, s["id"], 1, self.almox)
        materiais.excluir_solicitacao(self.conn, s["id"])
        s2 = materiais.criar_solicitacao(self.conn, self.prod["id"], c, 5, self.admin)
        materiais.criar_baixa(self.conn, s2["id"], 1, self.almox)
        with self.assertRaises(ErroNegocio):
            materiais.excluir_solicitacao(self.conn, s2["id"])


class TestRelatorios(BaseBanco):
    def test_dashboard_e_relatorios(self):
        d = relatorios.dashboard(self.conn)
        self.assertEqual(sum(x["quantidade"] for x in d["por_status"]), 30)
        self.assertEqual(len(d["ultimos_dias"]), 7)
        self.assertEqual(sum(x["quantidade"] for x in d["ultimos_dias"]), 30)
        self.assertEqual({x["codigo_sku"] for x in d["estoque_critico"]}, {"BAT-45WH", "LCD-156-FHD"})
        for tipo in relatorios.RELATORIOS:
            rel = relatorios.gerar_relatorio(self.conn, tipo)
            self.assertTrue(rel["linhas"], tipo)
            self.assertTrue(relatorios.relatorio_csv(rel).startswith(b"\xef\xbb\xbf"))
        vazio = relatorios.gerar_relatorio(self.conn, "producao", "2000-01-01", "2000-01-02")
        self.assertEqual(vazio["linhas"], [])
        with self.assertRaises(ErroNegocio):
            relatorios.gerar_relatorio(self.conn, "inexistente")


if __name__ == "__main__":
    unittest.main()


class TestMigracoes(unittest.TestCase):
    def test_banco_existente_de_outra_equipe_nao_e_apagado_e_conflito_e_avisado(self):
        import sqlite3
        from app import migracoes
        with tempfile.TemporaryDirectory() as tmp:
            config.DB_PATH = Path(tmp) / "compartilhado.db"
            outro = sqlite3.connect(config.DB_PATH)
            outro.execute("CREATE TABLE manutencoes (id INTEGER PRIMARY KEY, maquina TEXT)")
            outro.execute("INSERT INTO manutencoes (maquina) VALUES ('Testador 02')")
            outro.commit()
            outro.close()
            from app import db
            db.inicializar()                                  # banco já existia: migra, sem apagar e sem dados de demo
            conn = conectar()
            self.assertEqual(um(conn, "SELECT COUNT(*) AS n FROM manutencoes")["n"], 1)
            self.assertEqual(um(conn, "SELECT COUNT(*) AS n FROM usuarios")["n"], 0)
            self.assertEqual(um(conn, "SELECT COUNT(*) AS n FROM _migracoes")["n"], 2)
            db.inicializar()                                  # idempotente: rodar de novo não muda nada
            conn.close()
        with tempfile.TemporaryDirectory() as tmp:
            config.DB_PATH = Path(tmp) / "conflito.db"
            outro = sqlite3.connect(config.DB_PATH)
            outro.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, login TEXT)")   # 'usuarios' de outra equipe
            outro.commit()
            c = conectar()
            with self.assertRaises(RuntimeError) as e:
                migracoes.aplicar(c)
            self.assertIn("usuarios", str(e.exception))
            c.close()
            outro.close()
