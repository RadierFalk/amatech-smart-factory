"""Gera o tema do Streamlit ([theme] e [theme.sidebar]) de cada sistema a partir de identidade/tokens.json.

Uso (na raiz do repositório):  python identidade/gerar_temas.py
Troca só as seções de tema do .streamlit/config.toml de cada sistema; [server] e [client] ficam como estão
(o [client] ganha toolbarMode = "minimal" se não tiver, para esconder o botão "Deploy").
Também escreve rastreabilidade/static/css/identidade.css (os tokens em CSS) e copia o símbolo para lá.
Rode de novo sempre que tokens.json mudar.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SISTEMAS = ["qualidade", "manutencao", "dashboard"]

GOOGLE = "https://fonts.googleapis.com/css2?family="


def cores():
    tokens = json.loads((RAIZ / "identidade" / "tokens.json").read_text(encoding="utf-8"))
    brutos = {t["name"]: t["value"] for t in tokens["color"]["tokens"]}
    return {n: (brutos[v[1:-1]] if v.startswith("{") else v) for n, v in brutos.items()}


def tema(c):
    fonte = f'IBM Plex Sans:{GOOGLE}IBM+Plex+Sans:wght@400;600&display=swap, Segoe UI, sans-serif'
    titulos = f'IBM Plex Sans Condensed:{GOOGLE}IBM+Plex+Sans+Condensed:wght@600;700&display=swap, Segoe UI, sans-serif'
    codigo = f'IBM Plex Mono:{GOOGLE}IBM+Plex+Mono:wght@500&display=swap, Consolas, monospace'
    series = [c["grafico-1"], c["grafico-2"], c["grafico-3"], c["grafico-4"], c["setor-mnt"],
              c["grafico-meta"], c["ok"], c["atencao"], c["critico"], c["tinta-2"]]
    sequencia = ["#e6eefc", "#c9daf8", "#a8c3f2", "#86abec", "#6393e5", "#407bdd", "#1f5fd6", "#1a52b9",
                 "#1747a6", "#103379"]
    linhas = [
        "# Gerado por identidade/gerar_temas.py a partir de identidade/tokens.json: não edite à mão.",
        "[theme]",
        'base = "light"',
        f'primaryColor = "{c["sinal"]}"',
        f'backgroundColor = "{c["chao"]}"',
        f'secondaryBackgroundColor = "{c["superficie-2"]}"',
        f'textColor = "{c["tinta"]}"',
        f'linkColor = "{c["sinal"]}"',
        f'borderColor = "{c["linha"]}"',
        "showWidgetBorder = true",
        f'dataframeBorderColor = "{c["linha"]}"',
        f'dataframeHeaderBackgroundColor = "{c["superficie-2"]}"',
        f'dataframeHeaderTextColor = "{c["tinta-2"]}"',
        f'font = "{fonte}"',
        f'headingFont = "{titulos}"',
        f'codeFont = "{codigo}"',
        "baseFontSize = 14",
        "headingFontWeights = 600",
        'headingFontSizes = ["1.75rem", "1.25rem", "1.0625rem"]',
        'metricValueFontWeight = 600',
        'baseRadius = "6px"',
        'buttonRadius = "4px"',
        f'redColor = "{c["critico"]}"', f'redBackgroundColor = "{c["critico-suave"]}"', f'redTextColor = "{c["critico"]}"',
        f'orangeColor = "{c["grafico-4"]}"', f'orangeBackgroundColor = "{c["atencao-suave"]}"', f'orangeTextColor = "{c["atencao"]}"',
        f'yellowColor = "{c["atencao-sinal"]}"', f'yellowBackgroundColor = "{c["atencao-suave"]}"', f'yellowTextColor = "{c["atencao"]}"',
        f'greenColor = "{c["ok"]}"', f'greenBackgroundColor = "{c["ok-suave"]}"', f'greenTextColor = "{c["ok"]}"',
        f'blueColor = "{c["sinal"]}"', f'blueBackgroundColor = "{c["sinal-suave"]}"', f'blueTextColor = "{c["sinal-forte"]}"',
        f'violetColor = "{c["setor-qld"]}"', f'grayColor = "{c["tinta-2"]}"',
        f'grayBackgroundColor = "{c["neutro-suave"]}"', f'grayTextColor = "{c["tinta-2"]}"',
        "chartCategoricalColors = [" + ", ".join(f'"{s}"' for s in series) + "]",
        "chartSequentialColors = [" + ", ".join(f'"{s}"' for s in sequencia) + "]",
        "",
        "[theme.sidebar]",
        f'backgroundColor = "{c["noite"]}"',
        f'secondaryBackgroundColor = "{c["noite-2"]}"',
        f'textColor = "{c["on-noite"]}"',
        f'primaryColor = "{c["sinal"]}"',
        f'linkColor = "{c["led"]}"',
        f'borderColor = "{c["noite-2"]}"',
        f'codeTextColor = "{c["led"]}"',
        f'codeBackgroundColor = "{c["noite-2"]}"',
        f'grayTextColor = "{c["on-noite-suave"]}"',
    ]
    return "\n".join(linhas) + "\n"


def secoes(texto):
    """Divide o TOML em [(cabeçalho, linhas)]; o bloco antes do primeiro cabeçalho tem cabeçalho None."""
    partes, atual = [], [None, []]
    for linha in texto.splitlines():
        if re.match(r"^\[[^\]]+\]\s*$", linha):
            partes.append(atual)
            atual = [linha.strip(), []]
        else:
            atual[1].append(linha)
    partes.append(atual)
    return partes


def gerar(sistema, c):
    arquivo = RAIZ / sistema / ".streamlit" / "config.toml"
    texto = arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""
    mantidas = []
    for cabecalho, linhas in secoes(texto):
        if cabecalho in ("[theme]", "[theme.sidebar]"):
            continue
        corpo = [l for l in linhas if not l.startswith("# Gerado por identidade/")]
        if cabecalho == "[client]" and not any(l.startswith("toolbarMode") for l in corpo):
            corpo.insert(0, 'toolbarMode = "minimal"')
        while corpo and not corpo[-1].strip():
            corpo.pop()
        if cabecalho is None and not any(l.strip() for l in corpo):
            continue
        mantidas.append("\n".join(([cabecalho] if cabecalho else []) + corpo))
    if not any(s.startswith("[client]") for s in mantidas):
        mantidas.append('[client]\ntoolbarMode = "minimal"')
    arquivo.parent.mkdir(exist_ok=True)
    arquivo.write_text("\n\n".join(mantidas) + "\n\n" + tema(c), encoding="utf-8", newline="\n")
    print(f"{arquivo.relative_to(RAIZ)} atualizado")


def css_tokens():
    """Os tokens como variáveis CSS em :root, com o @import das fontes IBM Plex."""
    tokens = json.loads((RAIZ / "identidade" / "tokens.json").read_text(encoding="utf-8"))
    c = cores()
    linhas = [f"  --{n}: {v};" for n, v in c.items()]
    for familia in ("spacing", "radius", "shadow"):
        linhas += [f"  --{t['name']}: {t['value']};" for t in tokens[familia]["tokens"]]
    linhas += [f"  --font-{k}: {v};" for k, v in tokens["type"]["families"].items()]
    fontes = (f'{GOOGLE}IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans+Condensed:wght@600;700'
              f'&family=IBM+Plex+Sans:wght@400;600&display=swap')
    return ("/* Gerado por identidade/gerar_temas.py a partir de identidade/tokens.json: não edite à mão. */\n"
            f'@import url("{fontes}");\n:root {{\n' + "\n".join(linhas) + "\n}\n")


def gerar_frontend():
    """O frontend Angular recebe os tokens em src/styles/tokens.css e o símbolo em public/."""
    destino = RAIZ / "frontend"
    if not destino.exists():
        return
    (destino / "src" / "styles").mkdir(parents=True, exist_ok=True)
    (destino / "src" / "styles" / "tokens.css").write_text(css_tokens(), encoding="utf-8", newline="\n")
    (destino / "public" / "amatech-simbolo.svg").write_bytes((RAIZ / "identidade" / "amatech-simbolo.svg").read_bytes())
    print("frontend/src/styles/tokens.css e public/amatech-simbolo.svg atualizados")


def gerar_rastreabilidade():
    """A Rastreabilidade serve só a própria pasta static/: recebe uma cópia dos tokens em CSS e do símbolo."""
    tokens = json.loads((RAIZ / "identidade" / "tokens.json").read_text(encoding="utf-8"))
    c = cores()
    linhas = [f"  --{n}: {v};" for n, v in c.items()]
    for familia in ("spacing", "radius", "shadow"):
        linhas += [f"  --{t['name']}: {t['value']};" for t in tokens[familia]["tokens"]]
    linhas += [f"  --font-{k}: {v};" for k, v in tokens["type"]["families"].items()]
    fontes = (f'{GOOGLE}IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans+Condensed:wght@600;700'
              f'&family=IBM+Plex+Sans:wght@400;600&display=swap')
    css = ("/* Gerado por identidade/gerar_temas.py a partir de identidade/tokens.json: não edite à mão. */\n"
           f'@import url("{fontes}");\n:root {{\n' + "\n".join(linhas) + "\n}\n")
    destino = RAIZ / "rastreabilidade" / "static"
    (destino / "css" / "identidade.css").write_text(css, encoding="utf-8", newline="\n")
    (destino / "img" / "amatech-simbolo.svg").write_bytes((RAIZ / "identidade" / "amatech-simbolo.svg").read_bytes())
    print("rastreabilidade/static/css/identidade.css e img/amatech-simbolo.svg atualizados")


if __name__ == "__main__":
    paleta = cores()
    for nome in SISTEMAS:
        gerar(nome, paleta)
    gerar_rastreabilidade()
    gerar_frontend()
