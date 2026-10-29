// Casca do sistema: login, cabeçalho, faixa de módulos (estilo TOTVS RM), abas de telas abertas e rodapé.
import { api, endereco, guardarToken, lerToken, quandoNaoAutorizado } from './api.js';
import { h, icone, toast } from './ui.js';
import { telaInicio } from './telas/inicio.js';
import { telaProdutos, telaComponentes, telaStatus, telaUsuarios, telaIntegracoes } from './telas/cadastros.js';
import { telaProducao } from './telas/producao.js';
import { telaSolicitacoes, telaBaixas } from './telas/materiais.js';
import { telaRelatorios } from './telas/relatorios.js';

const TELAS = {
  inicio: { titulo: 'Terminal do Operador', icone: 'computador', render: telaInicio },
  produtos: { titulo: 'Produtos', icone: 'caixa', render: telaProdutos },
  componentes: { titulo: 'Componentes', icone: 'cpu', render: telaComponentes },
  status: { titulo: 'Status de produção', icone: 'camadas', render: telaStatus },
  usuarios: { titulo: 'Usuários', icone: 'usuario', render: telaUsuarios },
  integracoes: { titulo: 'Integrações', icone: 'link', render: telaIntegracoes },
  producao: { titulo: 'Produção', icone: 'prancheta', render: telaProducao },
  solicitacoes: { titulo: 'Solicitações de material', icone: 'carrinho', render: telaSolicitacoes },
  baixas: { titulo: 'Baixas de material', icone: 'baixa', render: telaBaixas },
  relatorios: { titulo: 'Relatórios', icone: 'relatorio', render: telaRelatorios },
};

const MODULOS = [
  { id: 'inicio', titulo: 'Início', grupos: [{ titulo: 'Painel', telas: ['inicio'] }] },
  { id: 'cadastros', titulo: 'Cadastros', grupos: [{ titulo: 'Produtos e estoque', telas: ['produtos', 'componentes'] },
    { titulo: 'Parâmetros', telas: ['status', 'usuarios', 'integracoes'] }] },
  { id: 'producao', titulo: 'Produção', grupos: [{ titulo: 'Rastreabilidade', telas: ['producao'] }] },
  { id: 'materiais', titulo: 'Materiais', grupos: [{ titulo: 'Fluxo de materiais', telas: ['solicitacoes', 'baixas'] }] },
  { id: 'relatorios', titulo: 'Relatórios', grupos: [{ titulo: 'Emissão', telas: ['relatorios'] }] },
];

const app = document.getElementById('app');
let sessao = null;      // { usuario, turno }

// ------------------------------------------------------------------ login
async function mostrarLogin(aviso) {
  let turnos = ['Turno 1', 'Turno 2'];
  try { turnos = await (await fetch(endereco('/api/auth/turnos'))).json(); } catch { /* usa o padrão */ }
  const matricula = h('input', { id: 'l-mat', type: 'text', autocomplete: 'username', placeholder: 'MAT-00000', required: true });
  const senha = h('input', { id: 'l-senha', type: 'password', autocomplete: 'current-password', placeholder: 'Senha', required: true });
  const turno = h('select', { id: 'l-turno' }, turnos.map((t) => h('option', { value: t }, t)));
  const erro = h('div', { class: 'login-erro', role: 'alert' }, aviso || '');
  const botao = h('button', { type: 'submit', class: 'btn-entrar' }, 'ENTRAR');
  const form = h('form', { class: 'login-form', onsubmit: async (e) => {
    e.preventDefault();
    erro.textContent = '';
    botao.disabled = true;
    try {
      const r = await api.post('/api/auth/login', { matricula: matricula.value, senha: senha.value, turno: turno.value });
      guardarToken(r.token);
      sessao = { usuario: r.usuario, turno: r.turno };
      iniciarSistema();
    } catch (ex) { erro.textContent = ex.message; senha.value = ''; senha.focus(); }
    finally { botao.disabled = false; }
  } },
  h('div', { class: 'login-avatar' }, icone('usuario', 34)),
  h('h2', {}, 'ACESSO DO OPERADOR'), h('p', {}, 'Informe suas credenciais para acessar o sistema'),
  h('label', { for: 'l-mat' }, 'Matrícula/Usuário'), matricula,
  h('label', { for: 'l-senha' }, 'Senha'), senha,
  h('label', { for: 'l-turno' }, 'Turno'), turno, erro, botao);
  app.replaceChildren(h('div', { class: 'login-pagina' },
    h('div', { class: 'login-topo' }, h('img', { src: 'img/logo-amatech.png', alt: 'AMATECH Electronics' })),
    h('h1', { class: 'login-titulo' }, 'SISTEMA DE RASTREABILIDADE', h('br'), 'DE PRODUTOS'),
    h('div', { class: 'login-cartao' }, form),
    h('p', { class: 'login-rodape' }, 'AMATECH Electronics Indústria e Comércio Ltda. · Polo Industrial de Manaus - AM')));
  matricula.focus();
}

function sair(aviso) {
  const token = lerToken();
  if (token) api.post('/api/auth/logout').catch(() => {});
  guardarToken(null);
  sessao = null;
  mostrarLogin(aviso);
}

quandoNaoAutorizado(() => { if (sessao) sair('Sessão expirada. Entre novamente.'); });

// ------------------------------------------------------------------ sistema (após o login)
function iniciarSistema() {
  const abertas = [];            // [{ id, params }]
  let ativa = null;
  let modulo = 'inicio';

  const conteudo = h('main', { class: 'conteudo', id: 'conteudo' });
  const tela = h('div', { class: 'tela' });
  const docs = h('div', { class: 'docs', role: 'tablist', 'aria-label': 'Telas abertas' });
  const modulosEl = h('nav', { class: 'modulos', 'aria-label': 'Módulos' });
  const ribbon = h('div', { class: 'ribbon' });
  conteudo.append(tela);

  const ctx = {
    get usuario() { return sessao.usuario; }, get turno() { return sessao.turno; }, params: {},
    abrirTela, recarregar: () => renderizar(),
  };

  function desenharModulos() {
    modulosEl.replaceChildren(...MODULOS.map((m) => h('button', { type: 'button', class: 'modulo' + (m.id === modulo ? ' ativo' : ''),
      onclick: () => { modulo = m.id; desenharModulos(); } }, m.titulo)));
    const m = MODULOS.find((x) => x.id === modulo);
    ribbon.replaceChildren(...m.grupos.map((gr) => h('div', { class: 'grupo' },
      h('div', { class: 'grupo-botoes' }, gr.telas.map((id) => h('button', { type: 'button', class: 'btn-grande' + (abertas.some((a) => a.id === id) ? ' aberta' : ''),
        onclick: () => abrirTela(id) }, icone(TELAS[id].icone, 30), h('span', {}, TELAS[id].titulo)))),
      h('div', { class: 'grupo-titulo' }, gr.titulo))));
  }

  function desenharDocs() {
    docs.replaceChildren(...abertas.map((a) => h('div', { class: 'doc' + (a.id === ativa ? ' ativa' : ''), role: 'tab', 'aria-selected': String(a.id === ativa) },
      h('button', { type: 'button', class: 'doc-nome', onclick: () => abrirTela(a.id) }, icone(TELAS[a.id].icone, 14), TELAS[a.id].titulo),
      a.id !== 'inicio' && h('button', { type: 'button', class: 'doc-x', 'aria-label': 'Fechar ' + TELAS[a.id].titulo, onclick: () => fecharTela(a.id) }, icone('fechar', 12)))));
  }

  async function renderizar() {
    const a = abertas.find((x) => x.id === ativa);
    ctx.params = a.params || {};
    tela.replaceChildren(h('p', { class: 'carregando' }, 'Carregando…'));
    const nova = h('div', { class: 'tela-corpo' });
    try {
      await TELAS[a.id].render(nova, ctx);
      if (ativa === a.id) tela.replaceChildren(nova);
    } catch (e) { tela.replaceChildren(h('p', { class: 'vazio' }, 'Não foi possível carregar a tela: ' + e.message)); }
  }

  function abrirTela(id, params) {
    const existente = abertas.find((a) => a.id === id);
    if (existente) existente.params = params || {}; else abertas.push({ id, params: params || {} });
    ativa = id;
    const dono = MODULOS.find((m) => m.grupos.some((gr) => gr.telas.includes(id)));
    if (dono) modulo = dono.id;
    desenharModulos(); desenharDocs();
    return renderizar();
  }

  function fecharTela(id) {
    const i = abertas.findIndex((a) => a.id === id);
    abertas.splice(i, 1);
    if (ativa === id) ativa = (abertas[i] || abertas[i - 1] || abertas[0]).id;
    desenharModulos(); desenharDocs(); renderizar();
  }

  const u = sessao.usuario;
  app.replaceChildren(
    h('header', { class: 'cabecalho' },
      h('img', { src: 'img/logo-amatech.png', alt: 'AMATECH Electronics' }), h('span', { class: 'sep' }),
      h('div', { class: 'cab-titulo' }, 'SISTEMA DE RASTREABILIDADE', h('br'), 'DE PRODUTOS'),
      h('div', { class: 'cab-info' },
        h('div', { class: 'cab-item' }, icone('usuario', 22), h('div', {}, h('small', {}, 'Operador'), h('b', {}, u.matricula), h('small', {}, u.nome + ' · ' + u.cargo))),
        h('div', { class: 'cab-item' }, icone('relogio', 22), h('div', {}, h('small', {}, 'Turno'), h('b', {}, sessao.turno))),
        h('button', { type: 'button', class: 'btn-sair', onclick: () => sair() }, icone('sair', 18), 'SAIR'))),
    modulosEl, ribbon, docs, conteudo,
    h('footer', { class: 'rodape-app' }, h('span', {}, 'AMATECH Electronics Indústria e Comércio Ltda. | Polo Industrial de Manaus - AM'), h('span', {}, 'Versão 1.0.0')));
  abrirTela('inicio');
}

// ------------------------------------------------------------------ partida
(async function iniciar() {
  if (lerToken()) {
    try { sessao = await api.get('/api/auth/me'); iniciarSistema(); return; }
    catch { guardarToken(null); }
  }
  mostrarLogin();
})();
