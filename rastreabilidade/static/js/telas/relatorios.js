// Relatórios (RNF006): tela, impressão (PDF pelo navegador) e exportação CSV.
import { api, baixarArquivo } from '../api.js';
import { h, icone, tabelaSimples, toast } from '../ui.js';
import { cabecalhoTela } from './crud.js';

const TIPOS = [
  { id: 'producao', rotulo: 'Produções e etapa atual', datas: true },
  { id: 'materiais', rotulo: 'Solicitações e baixas de material', datas: true },
  { id: 'estoque', rotulo: 'Estoque de componentes e pendências', datas: false },
  { id: 'nao_conformidades', rotulo: 'Não conformidades', datas: true },
];

export async function telaRelatorios(container, ctx) {
  const tipo = h('select', { id: 'rel-tipo', onchange: ajustar }, TIPOS.map((t) => h('option', { value: t.id }, t.rotulo)));
  const ini = h('input', { type: 'date', id: 'rel-ini' });
  const fim = h('input', { type: 'date', id: 'rel-fim' });
  const blocoDatas = h('div', { class: 'rel-datas' },
    h('div', { class: 'campo' }, h('label', { for: 'rel-ini' }, 'De'), ini),
    h('div', { class: 'campo' }, h('label', { for: 'rel-fim' }, 'Até'), fim));
  const resultado = h('div', { class: 'rel-resultado' }, h('p', { class: 'vazio' }, 'Escolha o relatório e clique em Gerar relatório.'));
  let atual = null;

  const btnImprimir = h('button', { type: 'button', class: 'btn', disabled: true, onclick: () => window.print() }, icone('impressora', 14), 'Imprimir / salvar PDF');
  const btnCsv = h('button', { type: 'button', class: 'btn', disabled: true, onclick: exportar }, icone('baixar', 14), 'Exportar CSV');

  function ajustar() { blocoDatas.hidden = !TIPOS.find((t) => t.id === tipo.value).datas; }
  const consulta = () => {
    const qs = new URLSearchParams();
    if (!blocoDatas.hidden && ini.value) qs.set('data_ini', ini.value);
    if (!blocoDatas.hidden && fim.value) qs.set('data_fim', fim.value);
    const s = qs.toString();
    return `/api/relatorios/${tipo.value}` + (s ? '?' + s : '');
  };

  async function gerar() {
    try {
      atual = await api.get(consulta());
      const emitido = new Date().toLocaleString('pt-BR', { timeZone: 'America/Manaus' });
      const periodo = atual.data_ini || atual.data_fim ? ` · Período: ${atual.data_ini || '…'} a ${atual.data_fim || '…'}` : '';
      resultado.replaceChildren(
        h('div', { class: 'rel-cab-impressao' }, h('img', { src: 'img/logo-amatech.png', alt: 'AMATECH Electronics', height: 40 }),
          h('div', {}, h('b', {}, 'AMATECH Electronics — Sistema de Rastreabilidade de Produtos'),
            h('div', {}, `${atual.titulo}${periodo}`), h('div', {}, `Emitido em ${emitido} por ${ctx.usuario.nome} (${ctx.usuario.matricula})`))),
        h('h3', { class: 'sub' }, atual.titulo),
        tabelaSimples(atual.colunas.map((c) => ({ titulo: c.titulo, chave: c.chave, alinhar: typeof atual.linhas[0]?.[c.chave] === 'number' ? 'dir' : '' })),
          atual.linhas, 'Nenhum dado encontrado para o filtro informado.'),
        h('p', { class: 'rel-total' }, `${atual.linhas.length} registro(s)`));
      btnImprimir.disabled = btnCsv.disabled = false;
    } catch (e) { toast(e.message, 'erro'); }
  }
  async function exportar() {
    try { await baixarArquivo(consulta().replace(/(\?|$)/, '/csv$1'), `relatorio_${tipo.value}.csv`); }
    catch (e) { toast(e.message, 'erro'); }
  }

  container.append(
    cabecalhoTela('relatorio', 'Relatórios', 'Emita relatórios dos dados do sistema, imprima ou exporte para o Excel (CSV).'),
    h('div', { class: 'rel-filtros no-print' },
      h('div', { class: 'campo' }, h('label', { for: 'rel-tipo' }, 'Relatório'), tipo), blocoDatas,
      h('div', { class: 'rel-acoes' }, h('button', { type: 'button', class: 'btn btn-primario', onclick: gerar }, icone('grafico', 14), 'Gerar relatório'), btnImprimir, btnCsv)),
    resultado);
  ajustar();
}
