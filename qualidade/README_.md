> **Nota (OA3):** este documento descreve a primeira versão. A API agora é **FastAPI**, roda separada das telas e
> exige chave; veja `README.md` e `ESTRUTURA_E_INTEGRACAO.md`.

# Sistema de Controle da Qualidade — Documentação Técnica

## 1. Sobre o projeto

O **Sistema de Controle da Qualidade** foi desenvolvido para o Projeto Integrador — Ambiente Fabril I, com o objetivo de solucionar o problema de **controle manual de falhas** em uma fábrica de notebooks.

O sistema permite registrar, consultar, pesquisar, filtrar, editar e ocultar ocorrências de defeitos identificadas durante a produção.

Além do gerenciamento das ocorrências, o sistema apresenta indicadores e gráficos para auxiliar o acompanhamento da qualidade da produção.

Os dados são armazenados localmente em um banco de dados SQLite e podem ser disponibilizados para outros sistemas por meio de uma API HTTP acessível pela rede Wi-Fi.



# 2. Tecnologias utilizadas

| Tecnologia         | Utilização                                    |
| ------------------ | --------------------------------------------- |
| Python             | Linguagem principal e implementação da lógica |
| Streamlit          | Interface web da aplicação                    |
| SQLite             | Banco de dados                                |
| sqlite3            | Comunicação entre Python e SQLite             |
| Matplotlib         | Geração dos gráficos                          |
| Flask              | Disponibilização da API HTTP                  |
| Visual Studio Code | Desenvolvimento                               |



# 3. Estrutura do projeto


sistema_controle_qualidade/
│
├── app.py
├── api.py
├── banco.py
├── criar_banco.py
├── graficos.py
├── indicadores.py
├── ocorrencia.py
├── README.md
├── README_ESTUDO.md
│
├── banco/
│   └── controle_qualidade.db
│
└── telas/
    ├── dashboard.py
    ├── historico_ocorrencias.py
    └── registro_ocorrencia.py


Cada arquivo possui uma responsabilidade específica dentro da aplicação.



# 4. Arquivo `app.py`

O `app.py` é o ponto de entrada da aplicação.

Sua responsabilidade é:

* configurar o Streamlit;
* iniciar a API automaticamente;
* criar a navegação principal;
* direcionar o usuário para cada tela.

A navegação possui três opções:


Dashboard
Registrar ocorrência
Histórico


## Inicialização da API

A API é iniciada automaticamente em uma thread separada:


Streamlit
   │
   ├── Interface da aplicação
   │
   └── API Flask


Isso permite que o sistema e a API funcionem simultaneamente.

A API utiliza a porta:


5000


Enquanto o Streamlit utiliza a porta padrão:


8501


O projeto é iniciado normalmente com:

bash
streamlit run app.py


Não é necessário executar `api.py` separadamente.

---

# 5. Arquivo `api.py`

O `api.py` implementa a API HTTP do sistema.

A API permite que outros computadores e aplicações obtenham os dados das ocorrências pela rede.

## Fluxo


Outro sistema
     │
     │ HTTP GET
     ▼
    API
     │
     ▼
 banco.py
     │
     ▼
 SQLite


## Endpoint de status


GET /api/status


Exemplo:


http://IP_DO_COMPUTADOR:5000/api/status


Retorno:

json
{
    "sistema": "Controle da Qualidade",
    "status": "online"
}


## Endpoint de ocorrências


GET /api/ocorrencias


Esse endpoint consulta as ocorrências por meio de `banco.py` e retorna os dados em JSON.

A API é somente de consulta na versão atual.

Isso significa que um sistema externo pode:

* obter os dados;
* criar seus próprios dashboards;
* gerar seus próprios gráficos;
* realizar suas próprias análises;

mas não pode modificar diretamente as ocorrências através da API.

---

# 6. Arquivo `banco.py`

O `banco.py` representa a camada de **acesso aos dados**.

Ele é responsável por:

* abrir conexão com o SQLite;
* executar consultas;
* inserir ocorrências;
* editar ocorrências;
* ocultar ocorrências;
* pesquisar registros;
* aplicar consultas e filtros;
* obter dados relacionados.

A aplicação não acessa o SQLite diretamente pelas telas.

O fluxo utilizado é:


Tela
 ↓
ocorrencia.py
 ↓
banco.py
 ↓
SQLite


Isso mantém separadas a interface, as regras da aplicação e o acesso ao banco.

---

# 7. Arquivo `ocorrencia.py`

O `ocorrencia.py` representa a camada de **lógica da aplicação**.

É nessa camada que ficam as regras relacionadas às ocorrências.

Entre suas responsabilidades estão:

* validar dados;
* registrar ocorrência;
* editar ocorrência;
* ocultar ocorrência;
* pesquisar ocorrências;
* filtrar ocorrências;
* consultar uma ocorrência específica.

## Validações

As classificações permitidas são:


Critico
Maior
Menor


As situações possíveis do produto são:


Aprovado
Reprovado
Em_reprocesso


Os status possíveis são:


Aberta
Em_analise
Resolvida


Campos obrigatórios incluem:

* data;
* hora;
* classificação;
* situação do produto;
* status;
* produto;
* estação;
* tipo de defeito;
* máquina;
* usuário;
* observação;
* ação realizada.

---

# 8. Arquivo `indicadores.py`

O `indicadores.py` concentra os cálculos utilizados pelos indicadores do Dashboard.

As funções principais são:


total_ocorrencias()
ocorrencias_abertas()
produtos_reprovados()
estacao_com_mais_ocorrencias()
obter_indicadores()


Os indicadores utilizados no Dashboard são:


Total de ocorrências
Ocorrências abertas
Produtos reprovados
Estação com mais ocorrências


Os valores são calculados a partir dos dados armazenados no banco.

---

# 9. Arquivo `graficos.py`

O `graficos.py` prepara os dados utilizados nos gráficos.

As principais funções são:


ocorrencias_por_tipo_defeito()
ocorrencias_por_estacao()
ocorrencias_por_data()


Os dados são agrupados utilizando `Counter`.

## Gráfico por tipo de defeito

As ocorrências são agrupadas pelo tipo de defeito e ordenadas pela quantidade.

Exemplo:


Tela
Bateria
Teclado
Wi-Fi



## Gráfico por estação

As ocorrências são agrupadas pela estação de origem.

Exemplo:


Inspeção de Qualidade
Teste Funcional
Montagem Final



## Tendência por data

As ocorrências são agrupadas pela data da ocorrência.

Isso permite visualizar a quantidade de registros ao longo dos dias.

Os gráficos são gerados utilizando:


Matplotlib


---

# 10. Pasta `telas`

A pasta `telas` contém os módulos responsáveis pela interface do sistema.


telas/
├── dashboard.py
├── registro_ocorrencia.py
└── historico_ocorrencias.py


Cada arquivo representa uma tela principal.

---

# 11. `telas/dashboard.py`

O Dashboard apresenta uma visão geral dos dados de qualidade.

A tela possui quatro indicadores principais:


Total de ocorrências
Ocorrências abertas
Produtos reprovados
Estação com mais ocorrências


Também apresenta gráficos de:


Ocorrências por tipo de defeito
Ocorrências por estação
Tendência de ocorrências


O Dashboard obtém seus dados através das camadas da aplicação.

Fluxo:


Dashboard
   ↓
indicadores.py / graficos.py
   ↓
banco.py
   ↓
SQLite


---

# 12. `telas/registro_ocorrencia.py`

Essa tela permite cadastrar uma nova ocorrência.

Os dados utilizados no formulário incluem:


Produto
Número de série do produto
Estação
Tipo de defeito
Máquina
Classificação do defeito
Situação do produto
Ação realizada
Observação da ocorrência


Os dados de produtos, estações, tipos de defeito, máquinas e usuários são carregados do banco.

Após o preenchimento, a tela chama:


ocorrencia.registrar_ocorrencia()


A função valida os dados antes de enviá-los para o banco.

Fluxo:


Usuário
   ↓
Formulário Streamlit
   ↓
ocorrencia.py
   ↓
Validação
   ↓
banco.py
   ↓
SQLite


---

# 13. `telas/historico_ocorrencias.py`

A tela de histórico permite consultar as ocorrências registradas.

Funcionalidades:

* pesquisa;
* filtro por tipo de defeito;
* filtro por estação;
* filtro por classificação;
* filtro por status;
* edição;
* ocultação.

A tabela apresenta informações como:


ID
Data
Produto
Tipo de defeito
Estação
Classificação
Status
Ações


---

# 14. Pesquisa por ocorrência

A pesquisa pode ser realizada por o.

Quando o usuário informa um ID numérico, o sistema procura especificamente a ocorrência correspondente.

Exemplo:


Pesquisa:
15


Resultado:


Ocorrência 15


Para pesquisas uais, a consulta pode utilizar informações disponíveis nas ocorrências.

---

# 15. Filtros

O histórico permite combinar a consulta com filtros.

Exemplos:


Tipo de defeito: Tela
Estação: Teste Funcional


Ou:


Tipo de defeito: Bateria
Status: Aberta


Os filtros são aplicados sobre os registros retornados pelo sistema.

---

# 16. Edição de ocorrência

A função de edição permite alterar os dados de uma ocorrência existente.

O processo é:


Histórico
   ↓
Editar
   ↓
Carregar ocorrência
   ↓
Alterar dados
   ↓
Validar
   ↓
Atualizar banco


A ocorrência continua possuindo o mesmo identificador:


id_ocorrencia


Apenas os dados são atualizados.

---

# 17. Ocultação de ocorrência

O sistema não exclui fisicamente uma ocorrência do banco.

Quando o usuário escolhe:


Ocultar


o sistema altera:


visibilidade_ocorrencia


para:


Oculta


O registro continua armazenado no SQLite.

Isso permite preservar o histórico dos dados sem exibi-lo nas consultas padrão.

Fluxo:


Ocorrência
    │
    ├── Visível → aparece normalmente
    │
    └── Oculta → permanece no banco, mas não aparece
                  nas consultas padrão


---

# 18. Banco de dados

O banco utilizado é:


SQLite


Arquivo:


banco/controle_qualidade.db


O banco possui seis entidades principais:


produto
estacao
tipo_defeito
maquina
usuario
ocorrencia


---

# 19. Tabela `produto`

Representa os produtos fabricados.

Campos:


id_produto
numero_serie_produto
modelo_produto


`id_produto` é a chave primária.

---

# 20. Tabela `estacao`

Representa as estações da linha de produção.

Campos:


id_estacao
nome_estacao
descricao_estacao


---

# 21. Tabela `tipo_defeito`

Representa os tipos de defeitos identificados.

Campos:


id_tipo_defeito
nome_tipo_defeito
descricao_tipo_defeito


Tipos utilizados no projeto:


Armazenamento
Bateria
Câmera
Desempenho
Montagem
Software
Teclado
Tela
Touchpad
USB
Wi-Fi
Áudio


---

# 22. Tabela `maquina`

Representa as máquinas relacionadas às ocorrências.

Campos:


id_maquina
nome_maquina
descricao_maquina


Máquinas utilizadas:


INS-01
MONT-01
QC-01
SMT-01
TEST-01
TEST-02


---

# 23. Tabela `usuario`

Representa o usuário responsável pelo registro.

Campos:


id_usuario
nome_usuario
perfil_usuario


---

# 24. Tabela `ocorrencia`

A tabela `ocorrencia` é a entidade central do sistema.

Ela conecta:


Produto
Estação
Tipo de defeito
Máquina
Usuário


Campos:


id_ocorrencia
data_ocorrencia
hora_ocorrencia
classificacao_defeito
situacao_produto
observacao_ocorrencia
acao_realizada
status_ocorrencia
visibilidade_ocorrencia
id_produto
id_estacao
id_tipo_defeito
id_maquina
id_usuario


As cinco últimas informações são chaves estrangeiras.

---

# 25. Relacionamentos do banco

Os relacionamentos principais são:


produto       1 ───── N ocorrencia
estacao       1 ───── N ocorrencia
tipo_defeito  1 ───── N ocorrencia
maquina       1 ───── N ocorrencia
usuario       1 ───── N ocorrencia


Uma ocorrência possui:

* um produto;
* uma estação;
* um tipo de defeito;
* uma máquina;
* um usuário.

Uma mesma entidade relacionada pode aparecer em várias ocorrências.

---

# 26. Criação do banco

O arquivo:


criar_banco.py


é responsável pela criação inicial do banco.

Ele:

1. cria o arquivo SQLite;
2. habilita as chaves estrangeiras;
3. cria as tabelas;
4. insere dados iniciais;
5. cria ocorrências iniciais para teste.

### Atenção

O `criar_banco.py` recria as tabelas.

Portanto, ele **não deve ser executado para iniciar normalmente o sistema**, pois pode apagar e recriar os dados existentes.

Ele deve ser utilizado para preparar uma instalação inicial ou reconstruir o banco de teste.

---

# 27. Dados simulados

O projeto também possui um mecanismo para geração de dados simulados.

O objetivo é permitir testar:

* Dashboard;
* gráficos;
* filtros;
* histórico;
* indicadores;
* consultas.

Os dados simulados representam ocorrências de uma fábrica de notebooks.

A geração utiliza diferentes probabilidades para tipos de defeito, estações, classificações, situações e status.

Isso permite produzir um conjunto de dados mais próximo de um cenário de produção para testes.

---

# 28. Arquitetura da aplicação

A aplicação segue uma separação em camadas:


┌─────────────────────────────┐
│         Apresentação        │
│          Streamlit          │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│    Lógica da aplicação      │
│        ocorrencia.py        │
│    indicadores.py           │
│    graficos.py              │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│      Acesso aos dados       │
│          banco.py           │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│       Persistência          │
│           SQLite            │
└─────────────────────────────┘


A API funciona como uma interface externa de consulta:


                         ┌───────────────┐
                         │ Outro sistema │
                         └───────┬───────┘
                                 │
                              HTTP/Wi-Fi
                                 │
                         ┌───────▼───────┐
                         │    api.py     │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │   banco.py    │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │    SQLite     │
                         └───────────────┘


---

# 29. Fluxo completo de registro

Quando uma ocorrência é registrada:


1. Usuário abre o formulário
        ↓
2. Streamlit apresenta os campos
        ↓
3. Usuário informa os dados
        ↓
4. registro_ocorrencia.py recebe os dados
        ↓
5. ocorrencia.py valida os dados
        ↓
6. banco.py executa o INSERT
        ↓
7. SQLite armazena a ocorrência
        ↓
8. Dashboard e Histórico passam a utilizar o novo registro


---

# 30. Fluxo completo de consulta

Quando o sistema precisa consultar ocorrências:


1. Tela solicita os dados
        ↓
2. Função da aplicação é chamada
        ↓
3. banco.py executa a consulta
        ↓
4. SQLite retorna os registros
        ↓
5. banco.py organiza o resultado
        ↓
6. Tela recebe os dados
        ↓
7. Streamlit apresenta os resultados


---

# 31. Fluxo da API

Quando outro computador solicita dados:


Outro computador
       │
       │ GET /api/ocorrencias
       ▼
    Flask
       │
       ▼
    banco.py
       │
       ▼
    SQLite
       │
       ▼
    banco.py
       │
       ▼
    Flask
       │
       │ JSON
       ▼
Outro computador


O consumidor pode então transformar o JSON em um DataFrame ou utilizá-lo diretamente.

---

# 32. Comunicação pela rede

A API utiliza:


HTTP


e pode ser acessada pela rede Wi-Fi local.

Exemplo:


Computador do sistema:
192.168.1.100


API:


http://192.168.1.100:5000


Endpoint:


http://192.168.1.100:5000/api/ocorrencias


Os computadores precisam estar conectados à mesma rede para realizar esse acesso diretamente.

---

# 33. Segurança e limitações atuais

A API foi projetada para o cenário acadêmico e de rede local do projeto.

Na versão atual:

* não existe autenticação de usuário na API;
* não existe token de acesso;
* a API é somente leitura;
* não existem operações de alteração pelo endpoint;
* o acesso é destinado à rede local.

Por isso, a API não deve ser exposta diretamente à Internet sem a implementação de mecanismos adicionais de segurança.

---

# 34. Como executar o projeto

## Instalar as dependências

No terminal:

bash
pip install streamlit flask pandas matplotlib


Caso seja necessário consumir a API a partir de outro projeto:

bash
pip install requests


## Preparar o banco

Caso seja uma instalação nova:

bash
python criar_banco.py


## Executar o sistema

bash
streamlit run app.py


A aplicação Streamlit e a API serão iniciadas juntas.

---

# 35. Endereços durante a execução

Localmente, o Streamlit normalmente estará disponível em:


http://localhost:8501


A API estará disponível em:


http://localhost:5000


Na rede local, utilizando o IPv4 do computador:


http://IP_DO_COMPUTADOR:8501


e:


http://IP_DO_COMPUTADOR:5000


---

# 36. Exemplo de consumo externo

Um projeto externo pode obter os dados utilizando:

python
import requests
import pandas as pd


URL = "http://192.168.1.100:5000/api/ocorrencias"

resposta = requests.get(URL)

resposta.raise_for_status()

dados = resposta.json()

df = pd.DataFrame(dados)

print(df)


Depois disso, o projeto externo pode utilizar `df` para criar seus próprios:

* gráficos;
* indicadores;
* filtros;
* dashboards;
* relatórios;
* análises.

---

# 37. Princípio de funcionamento

O projeto foi estruturado para manter uma separação entre:


Interface
    ↓
Regras da aplicação
    ↓
Acesso aos dados
    ↓
Banco de dados


A interface não precisa conhecer os detalhes de como o SQLite funciona.

Da mesma forma, o banco não precisa conhecer a interface do Streamlit.

A API também não acessa o banco diretamente: ela utiliza a camada `banco.py`.

Isso permite que diferentes partes do sistema utilizem os mesmos dados sem duplicar a lógica de acesso ao banco.

---

# 38. Como estudar o projeto

Uma sequência recomendada para estudar o código é:

### 1. `app.py`

Entender como a aplicação é iniciada e como as telas são selecionadas.

### 2. `telas/registro_ocorrencia.py`

Entender como os dados entram no sistema.

### 3. `ocorrencia.py`

Entender as validações e regras aplicadas aos dados.

### 4. `banco.py`

Entender como Python se comunica com o SQLite.

### 5. `criar_banco.py`

Entender como as tabelas e dados iniciais são criados.

### 6. `telas/historico_ocorrencias.py`

Entender pesquisa, filtros, edição e ocultação.

### 7. `indicadores.py`

Entender como os indicadores são calculados.

### 8. `graficos.py`

Entender como os dados são preparados para os gráficos.

### 9. `telas/dashboard.py`

Entender como os dados preparados são apresentados.

### 10. `api.py`

Por fim, entender como os dados do sistema são disponibilizados para outros projetos.

---

# 39. Resumo da responsabilidade de cada arquivo

| Arquivo                    | Responsabilidade                   |
| -------------------------- | ---------------------------------- |
| `app.py`                   | Inicialização e navegação          |
| `api.py`                   | API HTTP                           |
| `banco.py`                 | Acesso ao SQLite                   |
| `criar_banco.py`           | Criação do banco e dados iniciais  |
| `ocorrencia.py`            | Regras e validações de ocorrências |
| `indicadores.py`           | Cálculo dos indicadores            |
| `graficos.py`              | Preparação dos dados dos gráficos  |
| `dashboard.py`             | Interface do Dashboard             |
| `registro_ocorrencia.py`   | Interface de registro              |
| `historico_ocorrencias.py` | Interface de histórico             |

---

# 40. Conceito geral do sistema

O sistema pode ser resumido da seguinte forma:


                    USUÁRIO
                       │
                       ▼
                 STREAMLIT
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
      Ocorrências              Indicadores
          │                         │
          ▼                         ▼
   ocorrencia.py             indicadores.py
          │
          ▼
       banco.py
          │
          ▼
       SQLite
          │
          ├──────────────────────┐
          │                      │
          ▼                      ▼
      Dashboard                API
                                 │
                              Wi-Fi
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
             Dashboard A                 Dashboard B


O SQLite funciona como a fonte de dados do sistema, enquanto o Streamlit fornece a interface principal e a API permite que outros sistemas consumam os dados sem precisar acessar diretamente o arquivo do banco.

---

# 41. Relação com o Projeto Integrador

A implementação atende ao problema definido no projeto:

**Problema 3 — Controle manual de falhas.**

A solução centraliza:

* registro de falhas;
* classificação;
* estação de origem;
* produto afetado;
* máquina envolvida;
* usuário responsável;
* situação do produto;
* ações realizadas;
* status;
* histórico;
* indicadores;
* gráficos.

A aplicação também fornece uma forma de disponibilizar os dados para outros sistemas por meio da API, permitindo que diferentes dashboards utilizem a mesma fonte de dados.

---

# 42. Estado do projeto

O projeto possui atualmente:

* banco SQLite funcional;
* cadastro de ocorrências;
* validação dos dados;
* histórico;
* pesquisa;
* filtros;
* edição;
* ocultação de ocorrências;
* indicadores;
* gráficos;
* Dashboard;
* dados simulados;
* API HTTP;
* acesso dos dados pela rede Wi-Fi.

A implementação pode ser expandida posteriormente com autenticação, controle de permissões, novos endpoints, novos indicadores, novos filtros ou integração com outros sistemas.
