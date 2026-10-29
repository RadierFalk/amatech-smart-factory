// Gráficos simples em HTML/CSS (sem biblioteca externa, funcionam offline).
import { h, fmtNum } from './ui.js';

// Barras horizontais: dados = [{ rotulo, valor, classe }]
export function barrasHorizontais(dados) {
  const max = Math.max(1, ...dados.map((d) => d.valor));
  const resumo = dados.map((d) => `${d.rotulo}: ${d.valor}`).join('; ');
  return h('div', { class: 'barras-h', role: 'img', 'aria-label': 'Produções por etapa. ' + resumo },
    dados.map((d) => h('div', { class: 'barra-linha', title: `${d.rotulo}: ${d.valor}` },
      h('span', { class: 'barra-rotulo' }, d.rotulo),
      h('span', { class: 'barra-trilho' }, h('span', { class: 'barra-preench ' + (d.classe || ''), style: { width: (d.valor / max * 100) + '%' } })),
      h('span', { class: 'barra-valor' }, fmtNum(d.valor)))));
}

// Colunas verticais: dados = [{ rotulo, valor }]
export function colunasVerticais(dados) {
  const max = Math.max(1, ...dados.map((d) => d.valor));
  const resumo = dados.map((d) => `${d.rotulo}: ${d.valor}`).join('; ');
  return h('div', { class: 'colunas-v', role: 'img', 'aria-label': 'Produções iniciadas por dia. ' + resumo },
    dados.map((d) => h('div', { class: 'coluna', title: `${d.rotulo}: ${d.valor}` },
      h('span', { class: 'coluna-valor' }, fmtNum(d.valor)),
      h('span', { class: 'coluna-barra', style: { height: Math.max(d.valor / max * 100, d.valor ? 4 : 1) + '%' } }),
      h('span', { class: 'coluna-rotulo' }, d.rotulo))));
}
