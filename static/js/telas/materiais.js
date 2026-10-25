// Fluxo de materiais (Problema 5): solicitações padronizadas pela lista do produto, baixas e controle de estoque.
import { api } from '../api.js';
import { h, icone, barra, grade, confirmar, dialogo, badgeSolicitacao, fmtData, fmtNum, toast } from '../ui.js';
import { cabecalhoTela } from './crud.js';

const podeBaixar = (u) => ['Administrador', 'Almoxarife'].includes(u.cargo);
const MOTIVO_BAIXA = 'Somente Almoxarife ou Administrador registram baixas de material.';
const saldoDe = (s) => s.quantidade_solicitada - s.quantidade_baixada;

// ------------------------------------------------------------------ diálogos compartilhados
function dialogoBaixa(s, aoConcluir) {
  const saldo = saldoDe(s);
  if (s.status_solicitacao === 'CANCELADA') { toast('Esta solicitação está cancelada.', 'erro'); return; }
  if (saldo <= 0) { toast('Esta solicitação já foi totalmente atendida.', 'erro'); return; }
  dialogo({
    titulo: `Dar baixa — solicitação #${s.id}`, icone: 'baixa', textoOk: 'Registrar baixa', largura: 500,
    topo: h('div', { class: 'info-grade um' },
      h('div', { class: 'info-item' }, h('span', {}, 'Componente'), h('b', {}, `${s.codigo_sku} — ${s.componente_nome}`)),
      h('div', { class: 'info-item' }, h('span', {}, 'Produção'), h('b', {}, s.numero_serie || '—')),
      h('div', { class: 'info-item' }, h('span', {}, 'Saldo da solicitação'), h('b', {}, fmtNum(saldo))),
      h('div', { class: 'info-item' }, h('span', {}, 'Estoque atual'), h('b', { class: s.qtd_estoque < saldo ? 'estoque-critico' : '' }, fmtNum(s.qtd_estoque)))),
    campos: [{ nome: 'quantidade', rotulo: 'Quantidade a baixar', tipo: 'numero', min: 1, passo: 1, obrigatorio: true,
      valor: Math.max(1, Math.min(saldo, s.qtd_estoque || 0)), span: 2 }],
    aoConfirmar: async (v) => {
      await api.post('/api/baixas', { solicitacao_id: s.id, quantidade_baixada: v.quantidade });
      toast('Baixa registrada e estoque atualizado.');
      if (aoConcluir) aoConcluir();
    },
  });
}

// ------------------------------------------------------------------ SOLICITAÇÕES (RF014)
export async function telaSolicitacoes(container, ctx) {
  const filtroStatus = h('select', { 'aria-label': 'Filtrar por situação', onchange: carregar },
    h('option', { value: '' }, 'Todas as situações'), ...['PENDENTE', 'PARCIAL', 'ATENDIDA', 'CANCELADA'].map((s) =>
      h('option', { value: s }, { PENDENTE: 'Pendentes', PARCIAL: 'Parciais', ATENDIDA: 'Atendidas', CANCELADA: 'Canceladas' }[s])));
  if (ctx.params?.status) filtroStatus.value = ctx.params.status;

  const g = grade({
    id: 'id', aoSelecionar: atualizarBotoes, aoAbrir: () => editar(), ordemInicial: { chave: 'id', dir: -1 },
    colunas: [
      { chave: 'id', titulo: 'Nº', alinhar: 'dir', largura: '70px' },
      { chave: 'criado_em', titulo: 'Data', render: (l) => fmtData(l.criado_em), largura: '140px' },
      { chave: 'numero_serie', titulo: 'Nº de série', largura: '120px' },
      { chave: 'componente_nome', titulo: 'Componente', texto: (l) => `${l.codigo_sku} ${l.componente_nome}`, render: (l) => `${l.codigo_sku} — ${l.componente_nome}` },
      { chave: 'quantidade_solicitada', titulo: 'Solicitada', alinhar: 'dir', largura: '100px' },
      { chave: 'quantidade_baixada', titulo: 'Baixada', alinhar: 'dir', largura: '90px' },
      { chave: 'saldo', titulo: 'Saldo', alinhar: 'dir', largura: '80px', ordem: saldoDe, texto: (l) => String(saldoDe(l)), render: (l) => fmtNum(saldoDe(l)) },
      { chave: 'qtd_estoque', titulo: 'Estoque', alinhar: 'dir', largura: '90px',
        render: (l) => h('span', { class: l.status_solicitacao !== 'ATENDIDA' && l.status_solicitacao !== 'CANCELADA' && l.qtd_estoque < saldoDe(l) ? 'estoque-critico' : '' }, fmtNum(l.qtd_estoque)) },
      { chave: 'status_solicitacao', titulo: 'Situação', render: (l) => badgeSolicitacao(l.status_solicitacao), largura: '120px' },
      { chave: 'solicitante_nome', titulo: 'Solicitante' },
    ],
  });
  const tb = barra([
    { id: 'nova', icone: 'mais', rotulo: 'Nova solicitação', tipo: 'novo', aoClicar: nova },
    { id: 'gerar', icone: 'caixa', rotulo: 'Gerar da lista do produto', tipo: 'novo', aoClicar: gerar },
    { id: 'editar', icone: 'lapis', rotulo: 'Editar', tipo: 'editar', aoClicar: editar },
    { id: 'baixa', icone: 'baixa', rotulo: 'Dar baixa', tipo: 'editar', aoClicar: () => { const s = g.selecionado(); if (s) dialogoBaixa(s, carregar); } },
    { id: 'excluir', icone: 'lixeira', rotulo: 'Excluir', tipo: 'perigo', aoClicar: excluir },
    '|',
    { id: 'atualizar', icone: 'atualizar', rotulo: 'Atualizar', tipo: 'editar', aoClicar: carregar },
  ]);
  function atualizarBotoes(sel) {
    tb.habilitar('editar', !!sel, 'Selecione uma solicitação');
    tb.habilitar('baixa', !!sel && podeBaixar(ctx.usuario), podeBaixar(ctx.usuario) ? 'Selecione uma solicitação' : MOTIVO_BAIXA);
    tb.habilitar('excluir', !!sel, 'Selecione uma solicitação');
  }
  async function carregar() {
    try { g.setDados(await api.get('/api/solicitacoes' + (filtroStatus.value ? '?status=' + filtroStatus.value : ''))); }
    catch (e) { toast(e.message, 'erro'); }
  }

  async function nova() {
    let producoes, componentes;
    try { [producoes, componentes] = await Promise.all([api.get('/api/producoes'), api.get('/api/componentes')]); } catch (e) { toast(e.message, 'erro'); return; }
    dialogo({
      titulo: 'Nova solicitação de material', icone: 'carrinho', textoOk: 'Solicitar', largura: 560,
      campos: [
        { nome: 'producao_id', rotulo: 'Produção', tipo: 'select', obrigatorio: true, span: 2,
          opcoes: producoes.map((p) => ({ valor: p.id, rotulo: `${p.numero_serie} — ${p.nome_modelo} (${p.status_nome})` })) },
        { nome: 'componente_id', rotulo: 'Componente', tipo: 'select', obrigatorio: true, span: 2,
          opcoes: componentes.map((c) => ({ valor: c.idcmp, rotulo: `${c.codigo_sku} — ${c.nome} (estoque ${c.qtd_estoque})` })) },
        { nome: 'quantidade_solicitada', rotulo: 'Quantidade', tipo: 'numero', min: 1, passo: 1, valor: 1, obrigatorio: true },
      ],
      aoConfirmar: async (v) => {
        await api.post('/api/solicitacoes', { producao_id: v.producao_id, componente_id: v.componente_id, quantidade_solicitada: v.quantidade_solicitada });
        toast('Solicitação criada.'); await carregar();
      },
    });
  }
  async function gerar() {
    let producoes;
    try { producoes = await api.get('/api/producoes'); } catch (e) { toast(e.message, 'erro'); return; }
    const sel = g.selecionado();
    dialogo({
      titulo: 'Gerar solicitações pela lista de componentes do produto', icone: 'caixa', textoOk: 'Gerar solicitações', largura: 560,
      topo: h('p', { class: 'dica-aba' }, 'Cria uma solicitação para cada componente do modelo, com a quantidade padrão. Componentes que já têm solicitação ativa nesta produção são ignorados.'),
      campos: [{ nome: 'producao_id', rotulo: 'Produção', tipo: 'select', obrigatorio: true, span: 2,
        valor: sel?.producao_id, opcoes: producoes.map((p) => ({ valor: p.id, rotulo: `${p.numero_serie} — ${p.nome_modelo} (${p.status_nome})` })) }],
      aoConfirmar: async (v) => {
        const r = await api.post(`/api/producoes/${v.producao_id}/solicitar-materiais`);
        toast(`${r.criadas} solicitação(ões) criada(s)` + (r.ignoradas ? `; ${r.ignoradas} já existia(m).` : '.'));
        await carregar();
      },
    });
  }
  function editar() {
    const s = g.selecionado();
    if (!s) return;
    dialogo({
      titulo: `Editar solicitação #${s.id}`, icone: 'lapis', textoOk: 'Salvar', largura: 500,
      topo: h('p', { class: 'dica-aba' }, `${s.numero_serie || ''} — ${s.codigo_sku} ${s.componente_nome} · já baixado: ${fmtNum(s.quantidade_baixada)}`),
      campos: [
        { nome: 'quantidade_solicitada', rotulo: 'Quantidade solicitada', tipo: 'numero', min: 1, passo: 1, obrigatorio: true, valor: s.quantidade_solicitada },
        { nome: 'cancelada', rotulo: 'Solicitação cancelada', tipo: 'checkbox', valor: s.status_solicitacao === 'CANCELADA' },
      ],
      aoConfirmar: async (v) => {
        await api.put(`/api/solicitacoes/${s.id}`, { quantidade_solicitada: v.quantidade_solicitada, cancelada: v.cancelada });
        toast('Solicitação atualizada.'); await carregar(); g.selecionarId(s.id);
      },
    });
  }
  async function excluir() {
    const s = g.selecionado();
    if (!s || !(await confirmar({ titulo: 'Excluir solicitação', textoOk: 'Excluir', perigo: true, mensagem: `Excluir a solicitação #${s.id}?` }))) return;
    try { await api.del(`/api/solicitacoes/${s.id}`); toast('Solicitação excluída.'); await carregar(); } catch (e) { toast(e.message, 'erro'); }
  }

  container.append(
    cabecalhoTela('carrinho', 'Solicitações de material', 'Pedidos padronizados de componentes para cada produção, com saldo e situação.'),
    h('div', { class: 'consulta' }, h('div', { class: 'consulta-linha' }, filtroStatus)),
    tb.el, g.el);
  atualizarBotoes(null);
  await carregar();
}

// ------------------------------------------------------------------ BAIXAS (RF015)
export async function telaBaixas(container, ctx) {
  const pode = podeBaixar(ctx.usuario);
  const g = grade({
    id: 'id', aoSelecionar: atualizarBotoes, aoAbrir: () => editar(), ordemInicial: { chave: 'id', dir: -1 },
    colunas: [
      { chave: 'id', titulo: 'Nº', alinhar: 'dir', largura: '70px' },
      { chave: 'data_baixa', titulo: 'Data', render: (l) => fmtData(l.data_baixa), largura: '140px' },
      { chave: 'solicitacao_id', titulo: 'Solicitação', alinhar: 'dir', largura: '110px' },
      { chave: 'numero_serie', titulo: 'Nº de série', largura: '120px' },
      { chave: 'componente_nome', titulo: 'Componente', texto: (l) => `${l.codigo_sku} ${l.componente_nome}`, render: (l) => `${l.codigo_sku} — ${l.componente_nome}` },
      { chave: 'quantidade_baixada', titulo: 'Quantidade', alinhar: 'dir', largura: '100px' },
      { chave: 'usuario_nome', titulo: 'Baixa feita por' },
    ],
  });
  const tb = barra([
    { id: 'nova', icone: 'mais', rotulo: 'Nova baixa', tipo: 'novo', aoClicar: nova },
    { id: 'editar', icone: 'lapis', rotulo: 'Editar quantidade', tipo: 'editar', aoClicar: editar },
    { id: 'excluir', icone: 'lixeira', rotulo: 'Excluir (devolve ao estoque)', tipo: 'perigo', aoClicar: excluir },
    '|',
    { id: 'atualizar', icone: 'atualizar', rotulo: 'Atualizar', tipo: 'editar', aoClicar: carregar },
  ]);
  function atualizarBotoes(sel) {
    tb.habilitar('nova', pode, MOTIVO_BAIXA);
    tb.habilitar('editar', pode && !!sel, pode ? 'Selecione uma baixa' : MOTIVO_BAIXA);
    tb.habilitar('excluir', pode && !!sel, pode ? 'Selecione uma baixa' : MOTIVO_BAIXA);
  }
  async function carregar() { try { g.setDados(await api.get('/api/baixas')); } catch (e) { toast(e.message, 'erro'); } }

  async function nova() {
    let abertas;
    try { abertas = (await api.get('/api/solicitacoes')).filter((s) => ['PENDENTE', 'PARCIAL'].includes(s.status_solicitacao)); } catch (e) { toast(e.message, 'erro'); return; }
    if (!abertas.length) { toast('Não há solicitações pendentes para dar baixa.', 'erro'); return; }
    const porId = Object.fromEntries(abertas.map((s) => [s.id, s]));
    const dlg = dialogo({
      titulo: 'Nova baixa de material', icone: 'baixa', textoOk: 'Registrar baixa', largura: 580,
      campos: [
        { nome: 'solicitacao_id', rotulo: 'Solicitação', tipo: 'select', obrigatorio: true, span: 2,
          opcoes: abertas.map((s) => ({ valor: s.id, rotulo: `#${s.id} · ${s.numero_serie || '—'} · ${s.codigo_sku} ${s.componente_nome} · saldo ${saldoDe(s)}` })) },
        { nome: 'quantidade_baixada', rotulo: 'Quantidade a baixar', tipo: 'numero', min: 1, passo: 1, obrigatorio: true, valor: 1,
          dica: 'Não pode passar do saldo da solicitação nem do estoque do componente.' },
      ],
      aoConfirmar: async (v) => {
        await api.post('/api/baixas', { solicitacao_id: v.solicitacao_id, quantidade_baixada: v.quantidade_baixada });
        toast('Baixa registrada e estoque atualizado.'); await carregar();
      },
    });
    dlg.form.campos.solicitacao_id.input.addEventListener('change', () => {
      const s = porId[dlg.form.campos.solicitacao_id.get()];
      if (s) dlg.form.campos.quantidade_baixada.set(Math.max(1, Math.min(saldoDe(s), s.qtd_estoque || 0)));
    });
  }
  function editar() {
    const b = g.selecionado();
    if (!b || !pode) return;
    dialogo({
      titulo: `Editar baixa #${b.id}`, icone: 'lapis', textoOk: 'Salvar', largura: 480,
      topo: h('p', { class: 'dica-aba' }, `${b.numero_serie || ''} — ${b.codigo_sku} ${b.componente_nome}`),
      campos: [{ nome: 'quantidade_baixada', rotulo: 'Quantidade baixada', tipo: 'numero', min: 1, passo: 1, obrigatorio: true, valor: b.quantidade_baixada, span: 2 }],
      aoConfirmar: async (v) => { await api.put(`/api/baixas/${b.id}`, { quantidade_baixada: v.quantidade_baixada }); toast('Baixa atualizada.'); await carregar(); g.selecionarId(b.id); },
    });
  }
  async function excluir() {
    const b = g.selecionado();
    if (!b || !(await confirmar({ titulo: 'Excluir baixa', textoOk: 'Excluir', perigo: true,
      mensagem: `Excluir a baixa #${b.id}? A quantidade (${b.quantidade_baixada}) volta para o estoque.` }))) return;
    try { await api.del(`/api/baixas/${b.id}`); toast('Baixa excluída e estoque devolvido.'); await carregar(); } catch (e) { toast(e.message, 'erro'); }
  }

  container.append(
    cabecalhoTela('baixa', 'Baixas de material', 'Saídas de componentes do estoque para a produção (Almoxarife e Administrador).'),
    tb.el, g.el);
  atualizarBotoes(null);
  await carregar();
}
