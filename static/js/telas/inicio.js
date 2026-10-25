// Início: "Terminal do Operador" com indicadores, consulta por número de série, produtos recentes e gráficos.
import { api } from '../api.js';
import { h, icone, grade, badgeStatus, classeStatus, fmtData, fmtNum, toast } from '../ui.js';
import { barrasHorizontais, colunasVerticais } from '../charts.js';
import { abrirDetalheProducao, abrirNovaProducao } from './producao.js';

export async function telaInicio(container, ctx) {
  let dash, recentes;
  try { [dash, recentes] = await Promise.all([api.get('/api/dashboard'), api.get('/api/producoes')]); }
  catch (e) { toast(e.message, 'erro'); return; }
  const k = dash.kpis;

  const kpi = (tom, ic, rotulo, valor, sub, destino) => h(destino ? 'button' : 'div', { type: destino ? 'button' : null, class: 'kpi ' + tom,
    onclick: destino ? () => ctx.abrirTela(destino.tela, destino.params) : null },
    h('div', { class: 'kpi-icone' }, icone(ic, 22)),
    h('div', {}, h('small', {}, rotulo), h('strong', {}, fmtNum(valor)), h('span', {}, sub)));

  const busca = h('input', { type: 'search', 'aria-label': 'Número de série do produto', placeholder: 'Digite o número de série do produto…',
    onkeydown: (e) => { if (e.key === 'Enter') consultar(); } });
  const consultar = () => ctx.abrirTela('producao', { busca: busca.value.trim() });

  const g = grade({
    id: 'id', comFiltros: false, compacto: true, aoAbrir: (r) => abrirDetalheProducao(r.id, ctx, () => ctx.recarregar()),
    colunas: [
      { chave: 'numero_serie', titulo: 'Nº de série' }, { chave: 'nome_modelo', titulo: 'Modelo' },
      { chave: 'status_nome', titulo: 'Etapa atual', render: (l) => badgeStatus(l.status_nome) },
      { chave: 'responsavel_nome', titulo: 'Responsável' },
      { chave: 'atualizado_em', titulo: 'Última atualização', render: (l) => fmtData(l.atualizado_em) },
      { titulo: 'Ação', ordenavel: false, render: (l) => h('button', { type: 'button', class: 'btn btn-mini',
        onclick: (e) => { e.stopPropagation(); abrirDetalheProducao(l.id, ctx, () => ctx.recarregar()); } }, icone('olho', 14), 'Ver detalhes') },
    ],
  });
  g.setDados(recentes.slice(0, 8));

  const dias = dash.ultimos_dias.map((d) => ({
    rotulo: new Date(d.data + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' }).replace(/[.,]/g, ''),
    valor: d.quantidade }));

  container.append(
    h('div', { class: 'tela-cab' }, h('div', { class: 'tela-cab-icone' }, icone('computador', 26)),
      h('div', {}, h('h2', {}, 'TERMINAL DO OPERADOR'), h('p', {}, 'Acompanhe e consulte os produtos da linha de produção.'))),
    h('div', { class: 'kpis' },
      kpi('azul', 'caixa', 'Produtos do dia', k.produtos_dia, 'unidades iniciadas hoje', { tela: 'producao' }),
      kpi('verde', 'atividade', 'Em produção', k.em_producao, 'unidades na linha', { tela: 'producao' }),
      kpi('verde', 'checkcirculo', 'Aprovados', k.aprovados, 'aguardando embalagem', null),
      kpi('vermelho', 'xcirculo', 'Reprovados', k.reprovados, 'para retrabalho', null),
      kpi('ambar', 'carrinho', 'Materiais pendentes', k.solicitacoes_pendentes, 'solicitações sem baixa', { tela: 'solicitacoes', params: { status: 'PENDENTE' } }),
      kpi(k.estoque_critico ? 'vermelho' : 'verde', 'alerta', 'Estoque crítico', k.estoque_critico, `componentes ≤ ${dash.limite_estoque_critico}`, { tela: 'componentes' })),
    h('section', { class: 'bloco' },
      h('h3', { class: 'sub' }, 'CONSULTAR PRODUTO'),
      h('div', { class: 'consulta-linha' }, busca, h('button', { type: 'button', class: 'btn btn-primario', onclick: consultar }, icone('buscar', 14), 'Buscar'))),
    h('section', { class: 'bloco' },
      h('h3', { class: 'sub' }, 'PRODUTOS RECENTES'), g.el,
      h('div', { class: 'bloco-rodape' },
        h('span', { class: 'dica' }, icone('info', 14), ' Clique em "Ver detalhes" para visualizar o histórico completo do produto.'),
        h('button', { type: 'button', class: 'btn btn-primario', onclick: () => abrirNovaProducao(ctx, (p) => { ctx.recarregar(); abrirDetalheProducao(p.id, ctx, () => ctx.recarregar()); }) },
          icone('mais', 14), 'Novo produto'))),
    h('div', { class: 'duas-colunas' },
      h('section', { class: 'bloco' }, h('h3', { class: 'sub' }, 'Produções por etapa'),
        barrasHorizontais(dash.por_status.map((s) => ({ rotulo: s.status, valor: s.quantidade, classe: classeStatus(s.status) })))),
      h('section', { class: 'bloco' }, h('h3', { class: 'sub' }, 'Produções iniciadas nos últimos 7 dias'), colunasVerticais(dias))),
    h('section', { class: 'bloco' }, h('h3', { class: 'sub' }, 'Alerta de estoque crítico'),
      dash.estoque_critico.length
        ? h('ul', { class: 'lista-alerta' }, dash.estoque_critico.map((c) => h('li', {}, icone('alerta', 14), h('b', {}, c.codigo_sku), ' ' + c.nome, h('span', {}, ` — ${fmtNum(c.qtd_estoque)} em estoque`))))
        : h('p', { class: 'dica' }, 'Nenhum componente abaixo do limite.')));
}
