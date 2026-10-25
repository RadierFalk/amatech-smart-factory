// Produção e rastreabilidade: consulta por número de série, histórico de passagem, avançar etapa e não conformidades.
import { api } from '../api.js';
import { h, icone, barra, grade, janela, confirmar, dialogo, formulario, abas, tabelaSimples,
  badgeStatus, badgeSolicitacao, badgeOrigem, fmtData, fmtNum, toast } from '../ui.js';
import { cabecalhoTela } from './crud.js';

const opcoesUsuarios = (usuarios) => usuarios.map((u) => ({ valor: u.id, rotulo: `${u.nome} (${u.matricula})` }));
const ehReprovado = (s) => !!s && s.nome_status.trim().toLowerCase() === 'reprovado';

// ------------------------------------------------------------------ Nova produção (RF002, RF004, RF005)
export async function abrirNovaProducao(ctx, aoCriar) {
  let produtos, usuarios;
  try { [produtos, usuarios] = await Promise.all([api.get('/api/produtos'), api.get('/api/usuarios?apenas_ativos=1')]); }
  catch (e) { toast(e.message, 'erro'); return; }
  if (!produtos.length) { toast('Cadastre um produto antes de iniciar uma produção.', 'erro'); return; }
  dialogo({
    titulo: 'Nova produção', icone: 'caixa', textoOk: 'Iniciar produção', largura: 500,
    topo: h('p', { class: 'dica-aba' }, 'O número de série e o ID único da produção são gerados automaticamente.'),
    campos: [
      { nome: 'produto_id', rotulo: 'Modelo (produto)', tipo: 'select', obrigatorio: true, span: 2,
        opcoes: produtos.map((p) => ({ valor: p.idprd, rotulo: `${p.nome_modelo} — ${p.codigo_modelo}` })) },
      { nome: 'responsavel_etapa_id', rotulo: 'Responsável pela etapa', tipo: 'select', semVazio: true, span: 2,
        valor: ctx.usuario.id, opcoes: opcoesUsuarios(usuarios) },
    ],
    aoConfirmar: async (v) => {
      const p = await api.post('/api/producoes', { produto_id: v.produto_id, responsavel_etapa_id: v.responsavel_etapa_id });
      toast(`Produção ${p.numero_serie} iniciada.`);
      if (aoCriar) aoCriar(p);
    },
  });
}

// ------------------------------------------------------------------ Avançar etapa (RF006, RF008, RF012)
export function abrirAvancar(d, status, usuarios, ctx, aoConcluir) {
  const opcoes = status.filter((s) => s.id !== d.status_atual_id).map((s) => ({ valor: s.id, rotulo: s.nome_status }));
  const aviso = d.materiais_pendentes > 0
    ? h('div', { class: 'aviso' }, icone('alerta'), `Atenção: ${d.materiais_pendentes} solicitação(ões) de material desta produção ainda não foram totalmente baixadas.`)
    : null;
  const dlg = dialogo({
    titulo: `Avançar etapa — ${d.numero_serie}`, icone: 'avancar', textoOk: 'Confirmar', largura: 520, aviso,
    topo: h('p', { class: 'dica-aba' }, 'Etapa atual: ', badgeStatus(d.status_nome)),
    campos: [
      { nome: 'status_id', rotulo: 'Nova etapa', tipo: 'select', semVazio: true, obrigatorio: true, span: 2, opcoes,
        valor: d.proxima_etapa_sugerida_id ?? opcoes[0]?.valor },
      { nome: 'responsavel_etapa_id', rotulo: 'Responsável pela nova etapa', tipo: 'select', semVazio: true, span: 2,
        valor: ctx.usuario.id, opcoes: opcoesUsuarios(usuarios) },
      { nome: 'descricao_falha', rotulo: 'Falha encontrada', tipo: 'textarea', span: 2, placeholder: 'Ex.: teclas não respondem no teste funcional' },
      { nome: 'motivo_reprovacao', rotulo: 'Motivo da reprovação', tipo: 'textarea', span: 2, placeholder: 'Ex.: falha no teclado' },
    ],
    aoConfirmar: async (v) => {
      const r = await api.post(`/api/producoes/${d.id}/avancar`, { status_id: v.status_id, responsavel_etapa_id: v.responsavel_etapa_id,
        descricao_falha: v.descricao_falha || null, motivo_reprovacao: v.motivo_reprovacao || null });
      toast(`${d.numero_serie}: etapa alterada para ${r.status_nome}.`);
      if (aoConcluir) aoConcluir(r);
    },
  });
  const c = dlg.form.campos;
  const atualizar = () => {
    const rep = ehReprovado(status.find((s) => s.id === c.status_id.get()));
    c.descricao_falha.mostrar(rep); c.motivo_reprovacao.mostrar(rep);
    c.descricao_falha.obrigatorio = rep; c.motivo_reprovacao.obrigatorio = rep;
  };
  c.status_id.input.addEventListener('change', atualizar);
  atualizar();
}

export async function avancarPorId(id, ctx, aoConcluir) {
  try {
    const [d, status, usuarios] = await Promise.all([api.get(`/api/producoes/${id}`), api.get('/api/status'), api.get('/api/usuarios?apenas_ativos=1')]);
    abrirAvancar(d, status, usuarios, ctx, aoConcluir);
  } catch (e) { toast(e.message, 'erro'); }
}

// ------------------------------------------------------------------ Detalhe da produção (histórico completo, RF007/RF009/RF010)
export async function abrirDetalheProducao(id, ctx, aoAlterar) {
  let d, status, usuarios, produtos;
  try {
    [d, status, usuarios, produtos] = await Promise.all([api.get(`/api/producoes/${id}`), api.get('/api/status'),
      api.get('/api/usuarios?apenas_ativos=1'), api.get('/api/produtos')]);
  } catch (e) { toast(e.message, 'erro'); return; }

  const corpo = h('div');
  let tabs = null;
  let formResumo = null;

  const tb = barra([
    { id: 'avancar', icone: 'avancar', rotulo: 'Avançar etapa', tipo: 'novo', aoClicar: () => abrirAvancar(d, status, usuarios, ctx, recarregar) },
    { id: 'nc', icone: 'alerta', rotulo: 'Registrar não conformidade', tipo: 'perigo', aoClicar: registrarNC },
    { id: 'mat', icone: 'carrinho', rotulo: 'Solicitar materiais do produto', tipo: 'editar', aoClicar: solicitarMateriais },
    '|',
    { id: 'atualizar', icone: 'atualizar', rotulo: 'Atualizar', tipo: 'editar', aoClicar: recarregar },
  ]);

  async function recarregar() {
    try { d = await api.get(`/api/producoes/${id}`); } catch (e) { toast(e.message, 'erro'); return; }
    desenhar();
    if (aoAlterar) aoAlterar(d);
  }

  function registrarNC() {
    dialogo({
      titulo: `Registrar não conformidade — ${d.numero_serie}`, icone: 'alerta', textoOk: 'Registrar', largura: 520,
      campos: [
        { nome: 'descricao_falha', rotulo: 'Falha encontrada', tipo: 'textarea', obrigatorio: true, span: 2 },
        { nome: 'motivo_reprovacao', rotulo: 'Motivo da reprovação', tipo: 'textarea', obrigatorio: true, span: 2 },
      ],
      aoConfirmar: async (v) => {
        await api.post(`/api/producoes/${id}/nao-conformidades`, { descricao_falha: v.descricao_falha, motivo_reprovacao: v.motivo_reprovacao });
        toast('Não conformidade registrada.');
        await recarregar();
        tabs.ativar('nc');
      },
    });
  }

  async function solicitarMateriais() {
    try {
      const r = await api.post(`/api/producoes/${id}/solicitar-materiais`);
      toast(`${r.criadas} solicitação(ões) criada(s)` + (r.ignoradas ? `; ${r.ignoradas} já existia(m).` : '.'));
      await recarregar();
      tabs.ativar('materiais');
    } catch (e) { toast(e.message, 'erro'); }
  }

  function aba(idAba, titulo, ic, conteudo) { return { id: idAba, titulo, icone: ic, conteudo }; }

  function abaResumo() {
    formResumo = formulario([
      { nome: 'produto_id', rotulo: 'Modelo (produto)', tipo: 'select', semVazio: true, obrigatorio: true,
        opcoes: produtos.map((p) => ({ valor: p.idprd, rotulo: `${p.nome_modelo} — ${p.codigo_modelo}` })) },
      { nome: 'responsavel_etapa_id', rotulo: 'Responsável atual da etapa', tipo: 'select', semVazio: true, opcoes: opcoesUsuarios(usuarios) },
    ], d);
    const item = (r, v) => h('div', { class: 'info-item' }, h('span', {}, r), h('b', {}, v));
    return h('div', {},
      d.materiais_pendentes > 0 && h('div', { class: 'aviso' }, icone('alerta'),
        `${d.materiais_pendentes} solicitação(ões) de material com baixa pendente (veja a aba Materiais).`),
      h('div', { class: 'info-grade' },
        item('Número de série', d.numero_serie), item('ID da produção', d.id_unica_producao),
        item('Etapa atual', badgeStatus(d.status_nome)), item('Início', fmtData(d.data_inicio)),
        item('Última atualização', fmtData(d.atualizado_em)), item('Criada por', d.criado_por_nome || '—')),
      h('h3', { class: 'sub' }, 'Editar produção'), formResumo.el);
  }

  const colunasHist = [
    { titulo: '#', render: (l) => l.__n, alinhar: 'dir' },
    { titulo: 'Data/hora', render: (l) => fmtData(l.data_horario) },
    { titulo: 'Etapa', render: (l) => badgeStatus(l.status_nome) },
    { titulo: 'Atualizado por', chave: 'usuario_nome' },
    { titulo: 'Responsável da etapa', chave: 'responsavel_nome' },
    { titulo: 'Origem', render: (l) => badgeOrigem(l.origem_atualizacao) },
  ];

  function desenhar() {
    const atual = tabs ? tabs.atual() : 'resumo';
    tabs = abas([
      aba('resumo', 'Resumo', 'prancheta', abaResumo()),
      aba('historico', `Histórico (${d.historico.length})`, 'relogio',
        tabelaSimples(colunasHist, d.historico.map((x, i) => ({ ...x, __n: i + 1 })))),
      aba('materiais', `Materiais (${d.solicitacoes.length})`, 'carrinho', tabelaSimples([
        { titulo: 'SKU', chave: 'codigo_sku' }, { titulo: 'Componente', chave: 'componente_nome' },
        { titulo: 'Solicitada', chave: 'quantidade_solicitada', alinhar: 'dir' }, { titulo: 'Baixada', chave: 'quantidade_baixada', alinhar: 'dir' },
        { titulo: 'Status', render: (l) => badgeSolicitacao(l.status_solicitacao) }],
      d.solicitacoes, 'Nenhuma solicitação de material. Use "Solicitar materiais do produto" na barra acima.')),
      aba('nc', `Não conformidades (${d.nao_conformidades.length})`, 'alerta', tabelaSimples([
        { titulo: 'Data/hora', render: (l) => fmtData(l.data_registro) }, { titulo: 'Falha', chave: 'descricao_falha' },
        { titulo: 'Motivo da reprovação', chave: 'motivo_reprovacao' }, { titulo: 'Registrado por', chave: 'usuario_nome' }],
      d.nao_conformidades, 'Nenhuma não conformidade registrada.')),
      aba('modelo', `Mesmo modelo (${d.mesmo_modelo.length})`, 'caixa', tabelaSimples([
        { titulo: 'Nº de série', render: (l) => h('button', { type: 'button', class: 'link', onclick: () => abrirDetalheProducao(l.id, ctx, aoAlterar) }, l.numero_serie) },
        { titulo: 'Etapa atual', render: (l) => badgeStatus(l.status_nome) }, { titulo: 'Início', render: (l) => fmtData(l.data_inicio) }],
      d.mesmo_modelo)),
    ]);
    if (atual !== 'resumo') tabs.ativar(atual);
    corpo.replaceChildren(tabs.el);
    j.setTitulo(`Produção: ${d.numero_serie} — ${d.nome_modelo || ''}`);
  }

  const salvar = h('button', { type: 'button', class: 'btn btn-primario', onclick: async () => {
    if (!formResumo.validar()) return;
    const v = formResumo.valores();
    try {
      await api.put(`/api/producoes/${id}`, { produto_id: v.produto_id, responsavel_etapa_id: v.responsavel_etapa_id });
      toast('Produção atualizada.');
      await recarregar();
    } catch (e) { toast(e.message, 'erro'); }
  } }, 'Salvar alterações');
  const j = janela({ titulo: 'Produção', icone: 'prancheta', largura: 940, barra: tb, corpo, rodape: [salvar, h('button', { type: 'button', class: 'btn', onclick: () => j.fechar() }, 'Fechar')] });
  desenhar();
}

// ------------------------------------------------------------------ Tela "Produção" (lista + consulta por número de série)
export async function telaProducao(container, ctx) {
  let status = [];
  try { status = await api.get('/api/status'); } catch (e) { toast(e.message, 'erro'); }

  const busca = h('input', { type: 'search', 'aria-label': 'Número de série, ID da produção ou modelo', value: ctx.params?.busca || '',
    placeholder: 'Digite o número de série, o ID da produção ou o modelo…', onkeydown: (e) => { if (e.key === 'Enter') carregar(); } });
  const filtroStatus = h('select', { 'aria-label': 'Filtrar por etapa', onchange: carregar },
    h('option', { value: '' }, 'Todas as etapas'), status.map((s) => h('option', { value: s.id }, s.nome_status)));

  const g = grade({
    id: 'id', aoSelecionar: atualizarBotoes, aoAbrir: (r) => abrirDetalheProducao(r.id, ctx, carregar),
    colunas: [
      { chave: 'numero_serie', titulo: 'Nº de série', largura: '130px' },
      { chave: 'id_unica_producao', titulo: 'ID da produção' },
      { chave: 'nome_modelo', titulo: 'Modelo', largura: '110px' },
      { chave: 'status_nome', titulo: 'Etapa atual', render: (l) => badgeStatus(l.status_nome) },
      { chave: 'responsavel_nome', titulo: 'Responsável' },
      { chave: 'data_inicio', titulo: 'Início', render: (l) => fmtData(l.data_inicio) },
      { chave: 'atualizado_em', titulo: 'Última atualização', render: (l) => fmtData(l.atualizado_em) },
      { titulo: 'Ação', filtro: false, ordenavel: false, render: (l) => h('button', { type: 'button', class: 'btn btn-mini',
        onclick: (e) => { e.stopPropagation(); abrirDetalheProducao(l.id, ctx, carregar); } }, icone('olho', 14), 'Ver detalhes') },
    ],
  });
  const tb = barra([
    { id: 'nova', icone: 'mais', rotulo: 'Nova produção', tipo: 'novo', aoClicar: () => abrirNovaProducao(ctx, (p) => { carregar(); abrirDetalheProducao(p.id, ctx, carregar); }) },
    { id: 'detalhes', icone: 'olho', rotulo: 'Detalhes', tipo: 'editar', aoClicar: () => { const r = g.selecionado(); if (r) abrirDetalheProducao(r.id, ctx, carregar); } },
    { id: 'avancar', icone: 'avancar', rotulo: 'Avançar etapa', tipo: 'novo', aoClicar: () => { const r = g.selecionado(); if (r) avancarPorId(r.id, ctx, carregar); } },
    { id: 'excluir', icone: 'lixeira', rotulo: 'Excluir', tipo: 'perigo', aoClicar: excluir },
    '|',
    { id: 'atualizar', icone: 'atualizar', rotulo: 'Atualizar', tipo: 'editar', aoClicar: carregar },
  ]);
  function atualizarBotoes(sel) { for (const id of ['detalhes', 'avancar', 'excluir']) tb.habilitar(id, !!sel, 'Selecione uma produção na grade'); }

  async function carregar() {
    const qs = new URLSearchParams();
    if (busca.value.trim()) qs.set('q', busca.value.trim());
    if (filtroStatus.value) qs.set('status_id', filtroStatus.value);
    try { g.setDados(await api.get('/api/producoes?' + qs)); } catch (e) { toast(e.message, 'erro'); }
  }
  async function excluir() {
    const r = g.selecionado();
    if (!r || !(await confirmar({ titulo: 'Excluir produção', textoOk: 'Excluir', perigo: true,
      mensagem: `Excluir a produção ${r.numero_serie} com todo o histórico e solicitações? Esta ação não pode ser desfeita.` }))) return;
    try { await api.del(`/api/producoes/${r.id}`); toast('Produção excluída.'); await carregar(); } catch (e) { toast(e.message, 'erro'); }
  }

  container.append(
    cabecalhoTela('prancheta', 'Produção', 'Rastreie cada notebook: etapa atual, histórico de passagem, responsáveis e materiais.'),
    h('div', { class: 'consulta' }, h('label', {}, 'CONSULTAR PRODUTO'), h('div', { class: 'consulta-linha' }, busca, filtroStatus,
      h('button', { type: 'button', class: 'btn btn-primario', onclick: carregar }, icone('buscar', 14), 'Buscar'))),
    tb.el, g.el);
  atualizarBotoes(null);
  await carregar();
}
