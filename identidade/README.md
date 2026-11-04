# Identidade visual AMATECH

Cores, fontes, marca e peças de tela comuns aos quatro sistemas. O guia completo, com as regras de uso de cada cor e componente, está no guia de estilo **AMATECH Smart Factory**: https://claude.ai/artifact/C3CWPyn9GCUeRik1P2Fb2J

| Arquivo | O que é |
| --- | --- |
| `tokens.json` | A fonte única das cores, fontes, espaçamentos e raios (os mesmos do guia) |
| `amatech-simbolo.svg` | O símbolo da marca (o "A" com o LED), já com o fundo `noite` |
| `amatech.py` | Peças para as telas em Streamlit: estilos, cabeçalho, login, cartão de indicador, etiqueta de estado e tema do Matplotlib |
| `gerar_temas.py` | Gera, a partir de `tokens.json`, o tema de cada `.streamlit/config.toml` e o `rastreabilidade/static/css/identidade.css` |

## Mudar uma cor ou fonte

1. Edite `tokens.json`.
2. Rode, na raiz do repositório: `python identidade/gerar_temas.py`.
3. Reinicie as telas (o tema do Streamlit só é lido na partida).

Não edite à mão as seções `[theme]` dos `config.toml` nem o `identidade.css` da Rastreabilidade: o gerador as reescreve.

## Usar numa tela em Streamlit

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # raiz do repositório
from identidade import amatech

amatech.configurar_pagina("QLD", layout="wide")   # título da aba e símbolo
amatech.aplicar_estilos()
amatech.cabecalho("QLD", [("Turno", amatech.turno_atual())])
amatech.cartao("Índice de defeitos", "4,2%", "60 reprovados", estado="ok")
st.html(amatech.etiqueta("Reprovado"))          # o tom vem do texto: Reprovado → critico
```

Códigos dos setores: `RAS` (Rastreabilidade), `QLD` (Qualidade), `MNT` (Manutenção) e `DSH` (Dashboard).
