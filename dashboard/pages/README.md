# pages/ — Camada 1: Apresentação

Telas do sistema em Streamlit. O login e o menu ficam em `app.py`, na raiz: ele monta o menu com `st.navigation`, mostrando só as telas que o perfil do usuário pode abrir. `comum.py` reúne o que todas as telas usam (usuário logado, permissões, formatação brasileira, cartões do semáforo e filtros).

| Tela | Arquivo sugerido | Perfis | Requisitos |
| --- | --- | --- | --- |
| T02 Painel de indicadores | `1_Painel.py` | Supervisor, Gestor, Diretoria | RF06–RF12, RF17 |
| T03 Produção e metas | `2_Producao_e_metas.py` | Operador, Supervisor | RF01, RF02 |
| T04 Qualidade | `3_Qualidade.py` | Operador, Inspetor, Supervisor | RF03, RF04 |
| T05 Paradas | `4_Paradas.py` | Manutenção, Supervisor | RF05 |
| T06 Perdas | `5_Perdas.py` | Supervisor | RF15 |
| T07 Importação de planilhas | `6_Importacao.py` | Supervisor | RF16 |
| T08 Histórico | `7_Historico.py` | Supervisor, Gestor, Diretoria | RF13 |
| T09 Cadastros | `8_Cadastros.py` | Administrador (Supervisor: só limites do semáforo) | RF17, RN08 |
| T10 Usuários | `9_Usuarios.py` | Administrador | RF19 |

Regras desta camada: as telas **não calculam indicadores e não acessam o banco**; elas chamam as classes de `servicos/`. Os wireframes estão em `docs/wireframes/`.
