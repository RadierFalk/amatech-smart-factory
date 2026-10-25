// Componentes de interface reutilizáveis: janelas, barra de ferramentas, grade, formulários, abas e avisos.

// ---------------------------------------------------------------- criação de elementos
const PROPRIEDADES = ['value', 'checked', 'disabled', 'selected', 'readOnly', 'hidden'];

export function h(tag, props, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (PROPRIEDADES.includes(k)) el[k] = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  adicionar(el, filhos);
  return el;
}

function adicionar(el, filhos) {
  for (const f of filhos.flat(Infinity)) {
    if (f === null || f === undefined || f === false) continue;
    el.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
}

// ---------------------------------------------------------------- ícones (traçado simples, sem dependências externas)
const ICONES = {
  mais: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  lapis: '<path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>',
  lixeira: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
  atualizar: '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15"/>',
  salvar: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
  buscar: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  fechar: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  ok: '<polyline points="20 6 9 17 4 12"/>',
  esq: '<polyline points="15 18 9 12 15 6"/>',
  dir: '<polyline points="9 18 15 12 9 6"/>',
  avancar: '<polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/>',
  caixa: '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.3 7 12 12 20.7 7"/><line x1="12" y1="22" x2="12" y2="12"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
  usuario: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  relogio: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  impressora: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  baixar: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  grafico: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  alerta: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  sair: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  casa: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  caminhao: '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  camadas: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  prancheta: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="14" y2="16"/>',
  arquivo: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
  olho: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  carrinho: '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>',
  baixa: '<circle cx="12" cy="12" r="10"/><polyline points="8 12 12 16 16 12"/><line x1="12" y1="8" x2="12" y2="16"/>',
  computador: '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
  atividade: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  ajuda: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  checkcirculo: '<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><polyline points="22 4 12 14 9 11"/>',
  xcirculo: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
  relatorio: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="18" x2="8" y2="14"/><line x1="12" y1="18" x2="12" y2="11"/><line x1="16" y1="18" x2="16" y2="16"/>',
};

export function icone(nome, tamanho = 16) {
  const el = document.createElement('span');
  el.className = 'ic';
  el.innerHTML = `<svg viewBox="0 0 24 24" width="${tamanho}" height="${tamanho}" fill="none" stroke="currentColor" ` +
    `stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[nome] || ''}</svg>`;
  return el;
}

// ---------------------------------------------------------------- formatação
export function fmtData(s) {
  if (!s) return '';
  const d = new Date(s.replace(' ', 'T') + 'Z');          // o banco guarda em UTC
  if (isNaN(d)) return s;
  return d.toLocaleString('pt-BR', { timeZone: 'America/Manaus', day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit' }).replace(',', '');
}
export const fmtNum = (n) => (n ?? 0).toLocaleString('pt-BR');

const CLASSE_STATUS = { 'em fila': 'st-fila', 'em montagem': 'st-montagem', 'em teste': 'st-teste', 'aprovado': 'st-aprovado',
  'reprovado': 'st-reprovado', 'parado': 'st-parado', 'embalagem': 'st-embalagem', 'expedição': 'st-expedicao' };
export const classeStatus = (nome) => CLASSE_STATUS[(nome || '').toLowerCase()] || 'st-fila';
export const badgeStatus = (nome) => h('span', { class: 'badge ' + classeStatus(nome) }, nome || '—');

const CLASSE_SOLIC = { PENDENTE: 'st-teste', PARCIAL: 'st-montagem', ATENDIDA: 'st-aprovado', CANCELADA: 'st-fila' };
const ROTULO_SOLIC = { PENDENTE: 'Pendente', PARCIAL: 'Parcial', ATENDIDA: 'Atendida', CANCELADA: 'Cancelada' };
export const badgeSolicitacao = (s) => h('span', { class: 'badge ' + (CLASSE_SOLIC[s] || 'st-fila') }, ROTULO_SOLIC[s] || s);
export const badgeOrigem = (o) => h('span', { class: 'badge ' + (o === 'MANUAL' ? 'st-fila' : 'st-embalagem') },
  o === 'MANUAL' ? 'Manual' : o === 'MAQUINA/IOT' ? 'Máquina/IoT' : (o || '').startsWith('API:') ? 'API · ' + o.slice(4) : o);

// ---------------------------------------------------------------- avisos
export function toast(mensagem, tipo = 'ok') {
  const area = document.getElementById('toasts');
  const t = h('div', { class: 'toast ' + tipo, role: tipo === 'erro' ? 'alert' : 'status' },
    icone(tipo === 'erro' ? 'xcirculo' : 'checkcirculo', 18), h('span', {}, mensagem));
  area.append(t);
  setTimeout(() => t.remove(), tipo === 'erro' ? 7000 : 3500);
}

// ---------------------------------------------------------------- barra de ferramentas (estilo TOTVS RM)
export function barra(itens) {
  const el = h('div', { class: 'barra', role: 'toolbar' });
  const botoes = {};
  for (const it of itens) {
    if (it === '|') { el.append(h('span', { class: 'barra-sep' })); continue; }
    const b = h('button', { type: 'button', class: 'btn-barra ' + (it.tipo || ''), title: it.titulo || it.rotulo,
      'aria-label': it.titulo || it.rotulo, onclick: () => it.aoClicar && it.aoClicar() },
      it.icone && icone(it.icone), it.rotulo && h('span', {}, it.rotulo));
    botoes[it.id || it.rotulo] = { b, tituloPadrao: it.titulo || it.rotulo };
    el.append(b);
  }
  return {
    el,
    habilitar(id, sim, motivo) {
      const x = botoes[id];
      if (!x) return;
      x.b.disabled = !sim;
      x.b.title = !sim && motivo ? motivo : x.tituloPadrao;
    },
  };
}

// ---------------------------------------------------------------- janelas (modais)
let zBase = 1000;
const pilha = [];

export function janela({ titulo, icone: ic, largura = 720, corpo, rodape, barra: barraFerramentas, aoFechar }) {
  const fundo = h('div', { class: 'janela-fundo', style: { zIndex: ++zBase } });
  const tituloEl = h('span', { class: 'janela-titulo', id: 'jt' + zBase }, titulo);
  const corpoEl = h('div', { class: 'janela-corpo' }, corpo);
  const win = h('div', { class: 'janela', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': tituloEl.id,
    style: { width: `min(${largura}px, 96vw)` } },
    h('div', { class: 'janela-barra-titulo' }, ic && icone(ic), tituloEl,
      h('button', { type: 'button', class: 'janela-x', 'aria-label': 'Fechar janela', onclick: () => fechar() }, icone('fechar'))),
    barraFerramentas && (barraFerramentas.el || barraFerramentas),
    corpoEl,
    rodape && h('div', { class: 'janela-rodape' }, rodape));
  fundo.append(win);
  document.body.append(fundo);
  pilha.push(fundo);

  function fechar() {
    if (!fundo.isConnected) return;
    fundo.remove();
    pilha.splice(pilha.indexOf(fundo), 1);
    if (aoFechar) aoFechar();
  }
  fundo._fechar = fechar;
  const primeiro = corpoEl.querySelector('input:not([disabled]):not([type=hidden]), select:not([disabled]), textarea:not([disabled])');
  if (primeiro) primeiro.focus();
  return { el: win, corpoEl, fechar, setTitulo: (t) => { tituloEl.textContent = t; } };
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && pilha.length) pilha[pilha.length - 1]._fechar();
});

export function confirmar({ titulo = 'Confirmação', mensagem, textoOk = 'Confirmar', perigo = false }) {
  return new Promise((resolver) => {
    let feito = false;
    const fim = (v) => { if (feito) return; feito = true; j.fechar(); resolver(v); };
    const ok = h('button', { type: 'button', class: 'btn ' + (perigo ? 'btn-perigo' : 'btn-primario'), onclick: () => fim(true) }, textoOk);
    const cancelar = h('button', { type: 'button', class: 'btn', onclick: () => fim(false) }, 'Cancelar');
    const j = janela({ titulo, icone: perigo ? 'alerta' : 'ajuda', largura: 440,
      corpo: h('p', { class: 'confirm-msg' }, mensagem), rodape: [ok, cancelar], aoFechar: () => fim(false) });
    (perigo ? cancelar : ok).focus();
  });
}

// ---------------------------------------------------------------- campos e formulários
let seq = 0;

export function campo(def) {
  const id = `f_${def.nome}_${++seq}`;
  const tipo = def.tipo || 'texto';
  let input;
  if (tipo === 'select') {
    input = h('select', { id, disabled: def.desabilitado });
    if (!def.semVazio) input.append(h('option', { value: '' }, def.placeholder || 'Selecione…'));
    for (const o of def.opcoes || []) input.append(h('option', { value: String(o.valor) }, o.rotulo));
  } else if (tipo === 'textarea') {
    input = h('textarea', { id, rows: def.linhas || 3, disabled: def.desabilitado, placeholder: def.placeholder });
  } else if (tipo === 'checkbox') {
    input = h('input', { id, type: 'checkbox', disabled: def.desabilitado });
  } else {
    const tipoHtml = { texto: 'text', numero: 'number', senha: 'password', email: 'email', data: 'date' }[tipo] || 'text';
    input = h('input', { id, type: tipoHtml, disabled: def.desabilitado, placeholder: def.placeholder,
      min: def.min, max: def.max, step: def.passo, maxlength: def.maxlength, autocomplete: tipo === 'senha' ? 'new-password' : 'off' });
  }
  const erroEl = h('small', { class: 'erro-campo', role: 'alert' });
  const rotuloEl = h('label', { for: id }, def.rotulo, def.obrigatorio && h('span', { class: 'req', 'aria-hidden': 'true' }, '*'));
  const el = h('div', { class: 'campo' + (def.span === 2 ? ' span2' : '') + (tipo === 'checkbox' ? ' check' : '') },
    tipo === 'checkbox' ? [input, rotuloEl] : [rotuloEl, input],
    def.dica && h('small', { class: 'dica' }, def.dica), erroEl);

  const c = {
    el, input, nome: def.nome, obrigatorio: !!def.obrigatorio,
    get() {
      if (tipo === 'checkbox') return input.checked;
      if (tipo === 'numero') return input.value === '' ? null : Number(input.value);
      if (tipo === 'select') {
        if (input.value === '') return null;
        const o = (def.opcoes || []).find((x) => String(x.valor) === input.value);
        return o ? o.valor : input.value;
      }
      return input.value.trim();
    },
    set(v) { if (tipo === 'checkbox') input.checked = !!v; else input.value = v ?? ''; },
    erro(msg) { erroEl.textContent = msg || ''; el.classList.toggle('invalido', !!msg); },
    mostrar(sim) { el.hidden = !sim; },
    desabilitar(sim) { input.disabled = sim; },
  };
  c.set(def.valor);
  input.addEventListener('input', () => c.erro(null));
  return c;
}

export function formulario(defs, valores = {}) {
  const campos = {};
  const el = h('form', { class: 'form-grid', novalidate: '', onsubmit: (e) => e.preventDefault() });
  for (const d of defs) {
    const c = campo({ ...d, valor: valores[d.nome] !== undefined && valores[d.nome] !== null ? valores[d.nome] : d.valor });
    campos[d.nome] = c;
    el.append(c.el);
  }
  return {
    el, campos,
    valores() {
      const r = {};
      for (const [k, c] of Object.entries(campos)) r[k] = c.get();
      return r;
    },
    validar() {
      let primeiro = null;
      for (const c of Object.values(campos)) {
        c.erro(null);
        const v = c.get();
        if (c.obrigatorio && !c.el.hidden && (v === null || v === '' || v === undefined)) {
          c.erro('Campo obrigatório');
          primeiro = primeiro || c;
        }
      }
      if (primeiro) primeiro.input.focus();
      return !primeiro;
    },
  };
}

// Janela pequena com formulário: usada para "Nova produção", "Avançar etapa", "Nova baixa" etc.
export function dialogo({ titulo, icone: ic, campos, valores = {}, largura = 480, textoOk = 'Confirmar', topo, aviso, aoConfirmar }) {
  const f = formulario(campos, valores);
  let ocupado = false;
  const ok = h('button', { type: 'button', class: 'btn btn-primario', onclick: aoOk }, textoOk);
  async function aoOk() {
    if (ocupado || !f.validar()) return;
    ocupado = true;
    ok.disabled = true;
    try {
      const r = await aoConfirmar(f.valores(), f);
      if (r !== false) j.fechar();
    } catch (e) {
      toast(e.message, 'erro');
    } finally {
      ocupado = false;
      ok.disabled = false;
    }
  }
  const j = janela({ titulo, icone: ic, largura, corpo: [topo, aviso, f.el],
    rodape: [ok, h('button', { type: 'button', class: 'btn', onclick: () => j.fechar() }, 'Cancelar')] });
  return { ...j, form: f };
}

// ---------------------------------------------------------------- abas
export function abas(itens) {
  const barraEl = h('div', { class: 'abas', role: 'tablist' });
  const paineis = h('div', { class: 'abas-paineis' });
  const mapa = {};
  let atual = null;
  for (const it of itens) {
    const b = h('button', { type: 'button', class: 'aba', role: 'tab', onclick: () => ativar(it.id) },
      it.icone && icone(it.icone, 14), h('span', {}, it.titulo));
    const p = h('div', { class: 'aba-painel', role: 'tabpanel', hidden: true });
    mapa[it.id] = { b, p, it, montado: false };
    barraEl.append(b);
    paineis.append(p);
  }
  function ativar(id) {
    atual = id;
    for (const [k, m] of Object.entries(mapa)) {
      const on = k === id;
      m.b.classList.toggle('ativa', on);
      m.b.setAttribute('aria-selected', String(on));
      m.p.hidden = !on;
      if (on && !m.montado) {
        m.montado = true;
        m.p.append(typeof m.it.conteudo === 'function' ? m.it.conteudo() : m.it.conteudo);
      }
    }
  }
  ativar(itens[0].id);
  return {
    el: h('div', { class: 'abas-caixa' }, barraEl, paineis), ativar, atual: () => atual,
    definirTitulo(id, t) { if (mapa[id]) mapa[id].b.lastChild.textContent = t; },
  };
}

// ---------------------------------------------------------------- grade de dados (filtro por coluna, ordenação, seleção)
export function grade({ colunas, id = 'id', aoSelecionar, aoAbrir, vazio = 'Nenhum registro encontrado.', compacto = false, ordemInicial, comFiltros = true }) {
  let dados = [];
  let visiveis = [];
  let selId = null;
  const ord = { chave: ordemInicial?.chave || null, dir: ordemInicial?.dir || 1 };
  const filtros = {};
  const tbody = h('tbody');
  const rodape = h('div', { class: 'grade-rodape' });
  const trCab = h('tr');
  const trFil = h('tr', { class: 'grade-filtros' });

  for (const c of colunas) {
    const seta = h('span', { class: 'seta', 'aria-hidden': 'true' });
    const th = h('th', { scope: 'col', class: c.alinhar === 'dir' ? 'dir' : '', style: c.largura ? { width: c.largura } : null,
      'aria-sort': 'none', onclick: c.ordenavel === false ? null : () => ordenar(c) }, c.titulo, seta);
    c.__th = th; c.__seta = seta;
    trCab.append(th);
    const tf = h('th', { class: 'filtro' });
    if (c.filtro !== false) {
      tf.append(h('input', { type: 'search', 'aria-label': 'Filtrar ' + c.titulo, placeholder: 'filtrar',
        oninput: (e) => { filtros[c.chave] = e.target.value.toLowerCase(); desenhar(); } }));
    }
    trFil.append(tf);
  }
  const wrap = h('div', { class: 'grade-wrap', tabindex: '0', onkeydown: teclado },
    h('table', { class: 'grade' + (compacto ? ' compacto' : '') }, h('thead', {}, trCab, comFiltros && trFil), tbody));
  const el = h('div', { class: 'grade-caixa' }, wrap, rodape);

  const textoDe = (c, l) => String(c.texto ? c.texto(l) : (l[c.chave] ?? '')).toLowerCase();

  function ordenar(c) {
    if (ord.chave === c.chave) ord.dir *= -1; else { ord.chave = c.chave; ord.dir = 1; }
    desenhar();
  }

  function desenhar() {
    visiveis = dados.filter((l) => colunas.every((c) => !filtros[c.chave] || textoDe(c, l).includes(filtros[c.chave])));
    const col = colunas.find((c) => c.chave === ord.chave);
    if (col) {
      const valor = (l) => (col.ordem ? col.ordem(l) : l[col.chave]);
      visiveis.sort((a, b) => {
        const x = valor(a), y = valor(b);
        const r = (typeof x === 'number' && typeof y === 'number') ? x - y
          : String(x ?? '').localeCompare(String(y ?? ''), 'pt-BR', { numeric: true });
        return r * ord.dir;
      });
    }
    for (const c of colunas) {
      const ativo = c.chave === ord.chave;
      c.__th.setAttribute('aria-sort', ativo ? (ord.dir === 1 ? 'ascending' : 'descending') : 'none');
      c.__seta.textContent = ativo ? (ord.dir === 1 ? ' ▲' : ' ▼') : '';
    }
    tbody.replaceChildren();
    if (!visiveis.length) {
      tbody.append(h('tr', {}, h('td', { colspan: colunas.length, class: 'vazio' }, vazio)));
    }
    for (const l of visiveis) {
      tbody.append(h('tr', { dataset: { id: l[id] }, class: l[id] === selId ? 'sel' : '',
        onclick: () => selecionarId(l[id]), ondblclick: () => aoAbrir && aoAbrir(l) },
        colunas.map((c) => h('td', { class: c.alinhar === 'dir' ? 'dir' : '' }, c.render ? c.render(l) : (l[c.chave] ?? '')))));
    }
    rodape.textContent = dados.length === visiveis.length
      ? `${dados.length} registro(s)` : `${visiveis.length} de ${dados.length} registro(s)`;
  }

  function marcar() {
    for (const tr of tbody.children) tr.classList.toggle('sel', tr.dataset.id === String(selId));
  }
  function selecionarId(v, rolar = false) {
    selId = v;
    marcar();
    if (rolar) tbody.querySelector('tr.sel')?.scrollIntoView({ block: 'nearest' });
    if (aoSelecionar) aoSelecionar(selecionado());
  }
  const selecionado = () => dados.find((l) => l[id] === selId) || null;

  function teclado(e) {
    if (!['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key) || e.target.tagName === 'INPUT') return;
    e.preventDefault();
    if (e.key === 'Enter') { const s = selecionado(); if (s && aoAbrir) aoAbrir(s); return; }
    const i = visiveis.findIndex((l) => l[id] === selId);
    const prox = visiveis[Math.min(visiveis.length - 1, Math.max(0, i + (e.key === 'ArrowDown' ? 1 : -1)))];
    if (prox) selecionarId(prox[id], true);
  }

  desenhar();
  return {
    el,
    setDados(arr) {
      dados = arr;
      if (selId !== null && !dados.some((l) => l[id] === selId)) selId = null;
      desenhar();
      if (aoSelecionar) aoSelecionar(selecionado());
    },
    selecionado, selecionarId, visiveis: () => visiveis, todos: () => dados,
  };
}

// ---------------------------------------------------------------- tabela simples (somente leitura, sem filtros)
export function tabelaSimples(colunas, linhas, vazio = 'Nenhum registro.') {
  const corpo = linhas.length
    ? linhas.map((l) => h('tr', {}, colunas.map((c) => h('td', { class: c.alinhar === 'dir' ? 'dir' : '' },
      c.render ? c.render(l) : (l[c.chave] ?? '')))))
    : [h('tr', {}, h('td', { colspan: colunas.length, class: 'vazio' }, vazio))];
  return h('div', { class: 'grade-caixa simples' }, h('div', { class: 'grade-wrap' },
    h('table', { class: 'grade compacto' },
      h('thead', {}, h('tr', {}, colunas.map((c) => h('th', { scope: 'col', class: c.alinhar === 'dir' ? 'dir' : '' }, c.titulo)))),
      h('tbody', {}, corpo))));
}
