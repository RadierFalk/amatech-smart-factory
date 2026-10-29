# modelos/ — Classes de dados

As 13 classes que representam as informações do sistema, uma para cada tabela principal do MER: Perfil, Usuario, Turno, Produto, Estacao, Maquina, MetaProducao, RegistroProducao, Defeito, Retrabalho, Parada, Perda e Importacao.

- No lugar das chaves estrangeiras, a classe guarda o objeto relacionado (ex.: `RegistroProducao.turno` é um `Turno`).
- Só a classe Parada tem um método: `calcular_duracao()`, em minutos.
- As listas de opções (tipo de defeito, motivo de parada, tipo de perda e limites do semáforo) entram como atributos das classes que as usam.

Diagrama: `docs/diagramas/classes_dashboard.png`.
