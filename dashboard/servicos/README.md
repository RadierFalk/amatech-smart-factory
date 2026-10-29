# servicos/ — Camada 2: Regras de negócio

Aqui ficam todas as regras e as fórmulas dos indicadores. Esta camada chama apenas `acesso_dados/`.

| Classe | Arquivo sugerido | Responsabilidade | Requisitos |
| --- | --- | --- | --- |
| ServicoAutenticacao | `autenticacao.py` | Login, hash de senha, permissões por perfil | RF18, RF19, RNF07 |
| ServicoRegistro | `registro.py` | Valida (RN01–RN09) e grava produção, defeito, retrabalho, parada (incluindo encerrar_parada) e perda | RF01–RF05, RF15 |
| ImportadorCSV | `importador_csv.py` | Lê e valida planilhas; grava tudo ou nada | RF16, RN06 |
| CalculadoraIndicadores | `calculadora.py` | Os seis indicadores de um período | RF06–RF09 |
| AvaliadorAlertas | `alertas.py` | Cor do semáforo a partir da tabela parametro_alerta | RF17, RN08 |
| Filtro | `filtro.py` | Data inicial, data final, turno e produto | RF12, RN05 |

Fórmulas e limites: `docs/relatorio_oa2.md`, seções 2.4 e 2.5.
