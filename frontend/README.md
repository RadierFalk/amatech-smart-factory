# Frontend do ERP AMATECH (Angular)

Substitui as telas Streamlit. Consome a API única em `backend/`.

## Rodar

```bash
npm ci
npx ng serve          # http://localhost:4200 (as chamadas /api vão para http://localhost:8000, ver proxy.conf.json)
npx ng test --watch=false
npx ng build          # saída em dist/frontend
```

A API precisa estar no ar: veja `backend/` e `HANDOFF_POSTGRES.md` na raiz.

## Estrutura

| Pasta | O que tem |
| --- | --- |
| `src/app/core/` | Autenticação (signals + sessionStorage), interceptor JWT, guards por persona, tipos da API |
| `src/app/layout/` | Casca das telas logadas (barra lateral `noite`) |
| `src/app/paginas/` | Login, hub de módulos e tela "em construção" |
| `src/app/modulos/<modulo>/` | Um módulo por setor, carregado sob demanda (hoje: `usuarios`, `manutencao`, `qualidade`, `rastreabilidade`) |
| `src/app/shared/` | Peças da identidade visual (marca, etiqueta de estado) |

## Identidade visual

`src/styles/tokens.css` é **gerado**: edite `identidade/tokens.json` e rode `python identidade/gerar_temas.py` na raiz.
As classes globais (`.btn`, `.cartao`, `.tabela`, `.campo`, `.aviso`, `.selo-setor`...) ficam em `src/styles.scss`.

## Regras

- O RBAC de verdade é do servidor (403). Os guards só evitam abrir telas que a persona não pode usar.
- Componentes standalone, signals e o novo controle de fluxo (`@if`, `@for`); sem NgModules.
