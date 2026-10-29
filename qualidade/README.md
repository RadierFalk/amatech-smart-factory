# Sistema de Controle da Qualidade

## Acesso aos dados pela API

O Sistema de Controle da Qualidade disponibiliza os dados das ocorrências por meio de uma API HTTP.

A API é iniciada automaticamente junto com o sistema e fica disponível na porta `5000`.

### 1. Requisitos

Para acessar a API:

* O computador que executa o sistema deve estar conectado à rede Wi-Fi.
* O computador que irá consumir os dados deve estar conectado à mesma rede Wi-Fi.
* O sistema de Controle da Qualidade deve estar em execução.

---

## 2. Descobrir o endereço da API

No computador que executa o Sistema de Controle da Qualidade, abra o Prompt de Comando e execute:

```bash
ipconfig
```

Procure o **Endereço IPv4** do adaptador de rede Wi-Fi.

Exemplo:

```text
Endereço IPv4. . . . . . . . . . . : 192.168.1.100
```

Nesse caso, o endereço da API será:

```text
http://192.168.1.100:5000
```

> O endereço IP pode mudar dependendo da rede. Sempre utilize o IPv4 atual do computador que está executando o sistema.

---

## 3. Verificar se a API está funcionando

Abra um navegador no computador que irá consumir os dados e acesse:

```text
http://IP_DO_COMPUTADOR:5000/api/status
```

Exemplo:

```text
http://192.168.1.100:5000/api/status
```

Se a API estiver funcionando, será retornado:

```json
{
    "sistema": "Controle da Qualidade",
    "status": "online"
}
```

---

## 4. Consultar as ocorrências

Os dados das ocorrências estão disponíveis em:

```text
GET /api/ocorrencias
```

Exemplo:

```text
http://192.168.1.100:5000/api/ocorrencias
```

O retorno será um JSON contendo as ocorrências disponíveis no sistema.

Exemplo:

```json
[
    {
        "id_ocorrencia": 1,
        "data_ocorrencia": "2026-09-20",
        "hora_ocorrencia": "08:30:00",
        "produto": "AMT-NB001",
        "modelo_produto": "Notebook AMATECH",
        "tipo_defeito": "Tela",
        "estacao": "Teste Funcional",
        "maquina": "TEST-01",
        "usuario": "Ana Souza",
        "classificacao_defeito": "Maior",
        "situacao_produto": "Reprovado",
        "observacao_ocorrencia": "Falha na exibição da tela.",
        "acao_realizada": "Produto encaminhado para reprocesso.",
        "status_ocorrencia": "Em_analise"
    }
]
```

---

## 5. Consumir os dados em Python

Instale as bibliotecas necessárias:

```bash
pip install requests pandas
```

Depois:

```python
import requests
import pandas as pd


URL = "http://IP_DO_COMPUTADOR:5000/api/ocorrencias"

resposta = requests.get(URL)

resposta.raise_for_status()

dados = resposta.json()

df = pd.DataFrame(dados)

print(df)
```

Substitua:

```text
IP_DO_COMPUTADOR
```

pelo IPv4 do computador que está executando o sistema.

Exemplo:

```python
URL = "http://192.168.1.100:5000/api/ocorrencias"
```

---

## 6. Utilização em dashboards

Após obter os dados, eles podem ser utilizados normalmente para criar gráficos, indicadores e outros dashboards.

Exemplo:

```python
import requests
import pandas as pd


URL = "http://192.168.1.100:5000/api/ocorrencias"

resposta = requests.get(URL)
resposta.raise_for_status()

df = pd.DataFrame(resposta.json())


# Exemplo de consulta
ocorrencias_por_estacao = (
    df["estacao"]
    .value_counts()
)

print(ocorrencias_por_estacao)
```

O dashboard não precisa ter acesso ao arquivo SQLite.

A comunicação ocorre da seguinte forma:

```text
Sistema de Controle da Qualidade
            │
            │ API HTTP
            │ Wi-Fi
            ▼
      Dados das ocorrências
            │
      ┌─────┴─────┐
      ▼           ▼
 Dashboard A   Dashboard B
```

---

## 7. Endpoint disponível

| Método | Endpoint           | Função                         |
| ------ | ------------------ | ------------------------------ |
| GET    | `/api/status`      | Verificar se a API está online |
| GET    | `/api/ocorrencias` | Obter as ocorrências           |

A API disponibiliza os dados apenas para consulta. O acesso pela API não permite alterar ou excluir registros do banco de dados.

---

## 8. Importante

O Sistema de Controle da Qualidade precisa estar aberto para que a API esteja disponível.

A API é iniciada automaticamente quando o projeto é executado com:

```bash
streamlit run app.py
```

Não é necessário executar `api.py` separadamente.

O computador que fornece os dados e o computador que consome os dados devem estar na mesma rede Wi-Fi.

Se a API não puder ser acessada por outro computador, verifique o endereço IPv4 e as configurações do Firewall do Windows.

---

## 9. Integração com a Rastreabilidade e a Manutenção (OA3)

O sistema conversa com os outros setores da fábrica pelas APIs deles. Se algum estiver fora do ar, a Qualidade continua
funcionando normalmente e só mostra um aviso.

| Sistema | Endereço padrão | Para quê |
| --- | --- | --- |
| Rastreabilidade | `http://localhost:8000` | Números de série e modelos dos notebooks; etapa de cada notebook |
| Manutenção | `http://localhost:5002` | TAGs das máquinas; abertura de chamados |

**Cadastros dos setores donos.** Ao abrir o sistema (e no botão *Atualizar cadastros dos setores*, na barra lateral), os
notebooks são buscados na Rastreabilidade e as máquinas na Manutenção. Só o que falta é acrescentado; nada é apagado. O
banco já vem com os notebooks `AMT-000001` a `AMT-000030` (modelos AMT N14 a N18) e as TAGs da Manutenção.

**Ao registrar uma ocorrência**, a Rastreabilidade é avisada pela situação do produto:

| Situação | O que acontece na Rastreabilidade |
| --- | --- |
| Reprovado | O notebook vai para a etapa *Reprovado*, com a observação como falha e o tipo de defeito como motivo |
| Em_reprocesso | O notebook é reprovado e volta para *Em Montagem* |
| Aprovado | O notebook vai para *Aprovado*, se ainda não tiver passado por essa etapa |

Com a opção **Abrir chamado na manutenção** marcada, um chamado é aberto para a máquina da ocorrência, com prioridade pela
classificação (Crítico → CRITICA, Maior → ALTA, Menor → MEDIA). Cada ocorrência é enviada com o identificador `QLD-<id>`;
um reenvio não duplica nada nos outros sistemas.

**Filtro por período na API:** `GET /api/ocorrencias?de=2026-10-01&ate=2026-10-31` (datas da ocorrência, inclusive).

**Variáveis de ambiente** (opcionais):

| Variável | Padrão |
| --- | --- |
| `RASTREABILIDADE_URL` | `http://localhost:8000` |
| `RASTREABILIDADE_CHAVE` | `amt_demo_qualidade` |
| `MANUTENCAO_URL` | `http://localhost:5002` |
| `MANUTENCAO_CHAVE` | `amatech-manutencao-demo` |
| `INTEGRACAO_TEMPO_LIMITE` | `3` (segundos) |

A tela do Streamlit fica na porta `8502` (`.streamlit/config.toml`), para os quatro sistemas poderem rodar juntos.

Testes da integração (não precisam dos outros sistemas no ar): `python -m pytest tests -q`
