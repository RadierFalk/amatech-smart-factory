# Cadastros comuns do ecossistema AMATECH Smart Factory

Os quatro sistemas da OA3 (Rastreabilidade, Controle da Qualidade, Manutenção e Dashboard Industrial) trocam dados por API. Para um dado ser aceito pelo Dashboard, **os nomes e códigos precisam corresponder aos cadastros dele**. Este documento diz qual sistema é dono de cada cadastro e como os nomes de cada setor são traduzidos.

A tradução está em `servicos/cadastros_comuns.py`. A comparação ignora maiúsculas, acentos e espaços extras: "INSPEÇÃO de qualidade" e "inspecao de qualidade" são o mesmo nome. Só as diferenças de verdade precisam de sinônimo.

## Quem é o dono de cada cadastro

| Cadastro | Dono | Como chega ao Dashboard |
| --- | --- | --- |
| Modelos de notebook | Rastreabilidade (Projeto 2) | Criados automaticamente na sincronização (`GET /api/v1/produtos`) |
| Números de série | Rastreabilidade | Não são guardados: o Dashboard trabalha com totais por turno e modelo |
| Máquinas (tags como `TEST-01`) | Manutenção (Projeto 5) | Criadas automaticamente na sincronização (`GET /api/equipamentos`) |
| Estações, turnos, tipos de defeito e motivos de parada | Lista comum (abaixo) | Cadastrados no Dashboard; os outros nomes passam pelos sinônimos |

## Listas comuns

**Turnos** (horário local de Manaus, UTC-4)

| Nome | Início | Fim | Também aceito |
| --- | --- | --- | --- |
| 1º turno | 06:00 | 14:00 | `1`, `turno 1`, `primeiro turno` |
| 2º turno | 14:00 | 22:00 | `2`, `turno 2`, `segundo turno` |

Eventos fora desses horários são ignorados na sincronização (aparecem como "ignorados", sem erro).

**Estações**

| Dashboard | Qualidade | Manutenção (setor) |
| --- | --- | --- |
| Linha SMT | SMT | SMT |
| Inserção manual | Inserção Manual | — |
| Montagem final | Montagem Final | Montagem Final |
| Instalação de software | Instalação de Software | — |
| Teste funcional | Teste Funcional | Testes Funcionais, Testes |
| Inspeção da qualidade | Inspeção de Qualidade | — |
| Embalagem | Embalagem | Embalagem |

**Tipos de defeito**

| Dashboard | Qualidade |
| --- | --- |
| Tela com defeito | Tela |
| Falha no teclado | Teclado |
| Falha no touchpad | Touchpad |
| Falha de USB | USB |
| Falha de áudio | Áudio |
| Falha no Wi-Fi | Wi-Fi |
| Falha na câmera | Câmera |
| Falha na bateria | Bateria |
| Falha no armazenamento | Armazenamento |
| Desempenho insuficiente | Desempenho |
| Falha de montagem | Montagem |
| Falha de software | Software |
| Etiqueta incorreta | — |

**Motivos de parada**

| Dashboard | Tipo | Manutenção (tipo de manutenção) |
| --- | --- | --- |
| Falha de equipamento | corretiva | CORRETIVA |
| Manutenção programada | preventiva | PREVENTIVA |
| Falta de material | operacional | — |

## Horários

O Dashboard grava horário local (UTC-4). A Rastreabilidade envia UTC com "Z" e a Manutenção grava UTC; a sincronização converte os dois para o horário local antes de escolher o turno.

## Como acrescentar um nome novo

1. Se o item não existe no Dashboard, o Administrador o cadastra na tela **Cadastros**.
2. Se ele já existe com outro nome, acrescente o sinônimo em `SINONIMOS`, em `servicos/cadastros_comuns.py` (chave já sem acento e em minúsculas), e atualize esta página.
