"""Testes da API HTTP (login, permissões, mensagens de erro, CSV e integração com máquinas).
Rodar:  python -m unittest discover -s tests -v      (precisa de: pip install httpx)
"""
import tempfile
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from app import config, seed
from app.main import app


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = Path(cls.tmp.name) / "api.db"
        seed.recriar_banco()
        cls.cm = TestClient(app)
        cls.client = cls.cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)
        cls.tmp.cleanup()

    def login(self, matricula, senha=seed.SENHA_DEMO):
        r = self.client.post("/api/auth/login", json={"matricula": matricula, "senha": senha, "turno": "Turno 1"})
        return r

    def auth(self, matricula):
        token = self.login(matricula).json()["token"]
        return {"Authorization": "Bearer " + token}

    def test_login_ok_e_falha(self):
        r = self.login("mat-00421")                      # a matrícula não diferencia maiúsculas
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["usuario"]["cargo"], "Operador")
        self.assertEqual(self.login("MAT-00421", "errada").status_code, 401)
        self.assertEqual(self.login("MAT-IOT", "!").status_code, 401)   # usuário de serviço não faz login

    def test_rotas_exigem_login(self):
        self.assertEqual(self.client.get("/api/producoes").status_code, 401)
        self.assertEqual(self.client.get("/api/producoes", headers={"Authorization": "Bearer x"}).status_code, 401)

    def test_permissoes_por_cargo(self):
        op, almox, adm = self.auth("MAT-00421"), self.auth("MAT-0100"), self.auth("MAT-0001")
        self.assertEqual(self.client.get("/api/usuarios", headers=op).status_code, 200)
        self.assertEqual(self.client.post("/api/status", json={"nome_status": "Teste"}, headers=op).status_code, 403)
        self.assertEqual(self.client.post("/api/status", json={"nome_status": "Retrabalho"}, headers=adm).status_code, 201)
        sols = self.client.get("/api/solicitacoes?status=PENDENTE", headers=op).json()
        sid = next(s["id"] for s in sols if s["codigo_sku"] == "KBD-ABNT2")
        corpo = {"solicitacao_id": sid, "quantidade_baixada": 1}
        self.assertEqual(self.client.post("/api/baixas", json=corpo, headers=op).status_code, 403)
        self.assertEqual(self.client.post("/api/baixas", json=corpo, headers=almox).status_code, 201)

    def test_erros_amigaveis(self):
        adm = self.auth("MAT-0001")
        r = self.client.post("/api/componentes", json={"nome": "X", "codigo_sku": "KBD-ABNT2", "qtd_estoque": 1}, headers=adm)
        self.assertEqual(r.status_code, 409)
        self.assertIn("codigo_sku", r.json()["detail"])
        r = self.client.post("/api/componentes", json={"nome": "", "codigo_sku": "Z", "qtd_estoque": -1}, headers=adm)
        self.assertEqual(r.status_code, 422)
        self.assertIn("Dados inválidos", r.json()["detail"])
        self.assertEqual(self.client.get("/api/producoes/9999", headers=adm).status_code, 404)

    def test_fluxo_producao_pela_api(self):
        h = self.auth("MAT-00421")
        produto = self.client.get("/api/produtos", headers=h).json()[0]
        p = self.client.post("/api/producoes", json={"produto_id": produto["idprd"]}, headers=h).json()
        self.assertTrue(p["numero_serie"].startswith("AMT-"))
        status = {s["nome_status"]: s["id"] for s in self.client.get("/api/status", headers=h).json()}
        r = self.client.post(f"/api/producoes/{p['id']}/avancar", json={"status_id": status["Em Montagem"]}, headers=h)
        self.assertEqual(r.json()["status_nome"], "Em Montagem")
        r = self.client.post(f"/api/producoes/{p['id']}/solicitar-materiais", headers=h)
        self.assertEqual(r.status_code, 201)
        self.assertGreater(r.json()["criadas"], 5)
        self.assertEqual(len(self.client.get(f"/api/producoes?q={p['numero_serie']}", headers=h).json()), 1)

    def test_vinculo_de_componentes_pela_api(self):
        h = self.auth("MAT-00421")
        comps = self.client.get("/api/componentes", headers=h).json()
        corpo = {"nome_modelo": "AMT Z1", "codigo_modelo": "Z1", "quantidade": 5,
                 "componentes": [{"componente_id": comps[0]["idcmp"], "quantidade_necessaria": 2}]}
        r = self.client.post("/api/produtos", json=corpo, headers=h)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["componentes"][0]["quantidade_necessaria"], 2)
        self.assertEqual(self.client.delete(f"/api/produtos/{r.json()['idprd']}", headers=h).status_code, 200)

    def test_maquina_atualiza_status_com_chave(self):
        h = self.auth("MAT-00421")
        corpo = {"numero_serie": "AMT-000030", "status": "Em Montagem", "maquina": "Montadora 01"}
        self.assertEqual(self.client.post("/api/maquinas/status", json=corpo).status_code, 401)
        r = self.client.post("/api/maquinas/status", json=corpo, headers={"X-API-Key": config.API_KEY_MAQUINAS})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["alterado"])
        d = self.client.get("/api/producoes/30", headers=h).json()
        self.assertEqual(d["historico"][-1]["origem_atualizacao"], "MAQUINA/IOT")

    def test_dashboard_e_csv(self):
        h = self.auth("MAT-0001")
        d = self.client.get("/api/dashboard", headers=h).json()
        self.assertIn("produtos_dia", d["kpis"])
        r = self.client.get("/api/relatorios/estoque/csv", headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers["content-type"])
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertTrue(r.content.startswith(b"\xef\xbb\xbfSKU;Componente"))

    def test_frontend_e_servido(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])


if __name__ == "__main__":
    unittest.main()


class TestIntegracao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = Path(cls.tmp.name) / "integ.db"
        config.CHAVES_DEMO = {}   # estes testes criam as próprias chaves "qualidade" e "manutencao"
        seed.recriar_banco()
        cls.cm = TestClient(app)
        cls.client = cls.cm.__enter__()
        token = cls.client.post("/api/auth/login", json={"matricula": "MAT-0001", "senha": seed.SENHA_DEMO}).json()["token"]
        cls.admin = {"Authorization": "Bearer " + token}
        r = cls.client.post("/api/integracoes", json={"nome": "Qualidade"}, headers=cls.admin)
        cls.chave = {"X-API-Key": r.json()["chave"]}
        cls.cliente_id = r.json()["id"]

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)
        cls.tmp.cleanup()

    def test_saude_publica_e_chave_obrigatoria(self):
        self.assertEqual(self.client.get("/api/v1/saude").json()["status"], "ok")
        self.assertEqual(self.client.get("/api/v1/producoes").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/producoes", headers={"X-API-Key": "errada"}).status_code, 401)

    def test_leituras_do_contrato_v1(self):
        r = self.client.get("/api/v1/producoes?limite=5", headers=self.chave)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 5)
        self.assertTrue(r.json()[0]["atualizada_em"].endswith("Z"))
        d = self.client.get("/api/v1/producoes/AMT-000001", headers=self.chave).json()
        self.assertEqual(d["status"], "Expedição")
        self.assertGreater(len(d["historico"]), 3)
        self.assertGreater(len(self.client.get("/api/v1/produtos", headers=self.chave).json()[0]["componentes"]), 5)
        self.assertEqual(self.client.get("/api/v1/producoes/NAO-EXISTE", headers=self.chave).status_code, 404)
        filtradas = self.client.get("/api/v1/producoes?status=em fila", headers=self.chave).json()
        self.assertTrue(filtradas and all(p["status"] == "Em Fila" for p in filtradas))
        futuro = self.client.get("/api/v1/producoes?atualizado_apos=2999-01-01T00:00:00Z", headers=self.chave).json()
        self.assertEqual(futuro, [])

    def test_status_externo_grava_origem_e_gera_evento(self):
        ultimo = self.client.get("/api/v1/eventos?limite=1000", headers=self.chave).json()["ultimo_id"]
        r = self.client.post("/api/v1/producoes/AMT-000030/status", json={"status": "Em Montagem", "maquina": "Linha 1"},
                             headers=self.chave)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["alterado"])
        d = self.client.get("/api/v1/producoes/AMT-000030", headers=self.chave).json()
        self.assertEqual(d["historico"][-1]["origem"], "API:qualidade")
        ev = self.client.get(f"/api/v1/eventos?apos_id={ultimo}", headers=self.chave).json()
        self.assertEqual([e["tipo"] for e in ev["eventos"]], ["producao.etapa_alterada"])
        self.assertEqual(ev["eventos"][0]["dados"]["status_novo"], "Em Montagem")
        self.assertEqual(self.client.get(f"/api/v1/eventos?apos_id={ev['ultimo_id']}", headers=self.chave).json()["eventos"], [])

    def test_nao_conformidade_externa_nao_duplica(self):
        corpo = {"numero_serie": "AMT-000029", "descricao_falha": "Risco na tampa", "motivo_reprovacao": "Estético",
                 "id_externo": "QLD-77"}
        a = self.client.post("/api/v1/nao-conformidades", json=corpo, headers=self.chave)
        b = self.client.post("/api/v1/nao-conformidades", json=corpo, headers=self.chave)
        self.assertEqual((a.status_code, a.json()["criada"]), (201, True))
        self.assertFalse(b.json()["criada"])
        d = self.client.get("/api/v1/producoes/AMT-000029", headers=self.chave).json()
        self.assertEqual(len(d["nao_conformidades"]), 1)
        self.assertEqual(d["nao_conformidades"][0]["origem"], "qualidade")

    def test_chaves_podem_ser_revogadas_e_trocadas(self):
        c = self.client.post("/api/integracoes", json={"nome": "manutencao"}, headers=self.admin).json()
        h = {"X-API-Key": c["chave"]}
        self.assertEqual(self.client.get("/api/v1/componentes", headers=h).status_code, 200)
        nova = self.client.post(f"/api/integracoes/{c['id']}/nova-chave", headers=self.admin).json()["chave"]
        self.assertEqual(self.client.get("/api/v1/componentes", headers=h).status_code, 401)   # a antiga parou de valer
        h2 = {"X-API-Key": nova}
        self.client.put(f"/api/integracoes/{c['id']}", json={"ativo": False}, headers=self.admin)
        self.assertEqual(self.client.get("/api/v1/componentes", headers=h2).status_code, 401)
        lista = self.client.get("/api/integracoes", headers=self.admin).json()
        self.assertNotIn("chave", lista[0])
        self.assertNotIn("chave_hash", lista[0])
        op = self.client.post("/api/auth/login", json={"matricula": "MAT-00421", "senha": seed.SENHA_DEMO}).json()["token"]
        self.assertEqual(self.client.get("/api/integracoes", headers={"Authorization": "Bearer " + op}).status_code, 403)


class TestEcossistema(unittest.TestCase):
    """Integração da OA3: chaves de demonstração, histórico de etapas (/passagens) e reprovação vinda da Qualidade."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = Path(cls.tmp.name) / "eco.db"
        config.CHAVES_DEMO = {"qualidade": "amt_demo_qualidade", "dashboard": "amt_demo_dashboard"}
        seed.recriar_banco()
        cls.cm = TestClient(app)
        cls.client = cls.cm.__enter__()   # inicia o sistema: cria as chaves de demonstração
        cls.qualidade = {"X-API-Key": "amt_demo_qualidade"}
        cls.dashboard = {"X-API-Key": "amt_demo_dashboard"}

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)
        cls.tmp.cleanup()

    def test_chaves_de_demonstracao(self):
        self.assertEqual(self.client.get("/api/v1/produtos", headers=self.dashboard).status_code, 200)
        from app.db import conectar
        from app.servicos import integracao
        conn = conectar()
        config.CHAVES_DEMO = {"dashboard": "outra-chave"}
        integracao.garantir_chaves_demo(conn)   # cliente já existe: a chave não é trocada
        conn.close()
        self.assertEqual(self.client.get("/api/v1/produtos", headers=self.dashboard).status_code, 200)

    def test_passagens_incluem_o_historico_de_demonstracao(self):
        todas = self.client.get("/api/v1/passagens", headers=self.dashboard).json()
        self.assertGreater(len(todas), 30)
        self.assertTrue(all(p["em"].endswith("Z") for p in todas))
        self.assertEqual(set(todas[0]), {"numero_serie", "modelo", "status", "em", "origem"})
        aprovados = self.client.get("/api/v1/passagens?status=aprovado", headers=self.dashboard).json()
        self.assertTrue(aprovados and all(p["status"] == "Aprovado" for p in aprovados))
        meio = todas[len(todas) // 2]["em"]
        depois = self.client.get(f"/api/v1/passagens?de={meio}", headers=self.dashboard).json()
        self.assertTrue(0 < len(depois) < len(todas) and all(p["em"] >= meio for p in depois))

    def test_reprovacao_da_qualidade_usa_a_falha_real_e_nao_duplica(self):
        corpo = {"status": "Reprovado", "descricao_falha": "Teclado sem resposta", "motivo_reprovacao": "Teclado",
                 "id_externo": "QLD-15"}
        r = self.client.post("/api/v1/producoes/AMT-000028/status", json=corpo, headers=self.qualidade)
        self.assertTrue(r.json()["alterado"])
        self.client.post("/api/v1/producoes/AMT-000028/status", json={"status": "Em Montagem"}, headers=self.qualidade)
        de_novo = self.client.post("/api/v1/producoes/AMT-000028/status", json=corpo, headers=self.qualidade)
        self.assertFalse(de_novo.json()["alterado"])   # reenvio do mesmo QLD-15: não reprova de novo
        d = self.client.get("/api/v1/producoes/AMT-000028", headers=self.qualidade).json()
        self.assertEqual(d["status"], "Em Montagem")
        ncs = [n for n in d["nao_conformidades"] if n["id_externo"] == "QLD-15"]
        self.assertEqual(len(ncs), 1)
        self.assertEqual((ncs[0]["falha"], ncs[0]["motivo"], ncs[0]["origem"]),
                         ("Teclado sem resposta", "Teclado", "qualidade"))

    def test_maquina_sem_falha_continua_com_o_texto_padrao(self):
        r = self.client.post("/api/v1/producoes/AMT-000027/status", json={"status": "Reprovado", "maquina": "TEST-01"},
                             headers=self.qualidade)
        self.assertTrue(r.json()["alterado"])
        nc = self.client.get("/api/v1/producoes/AMT-000027", headers=self.qualidade).json()["nao_conformidades"][-1]
        self.assertEqual(nc["falha"], "Reprovado automaticamente pela máquina TEST-01")
