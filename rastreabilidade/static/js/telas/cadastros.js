// Cadastros: Produtos (com vínculo de componentes), Componentes, Status de produção, Usuários e Integrações.
import { api, endereco } from '../api.js';
import { h, icone, barra, grade, janela, confirmar, dialogo, fmtData, fmtNum, toast } from '../ui.js';
import { telaCrud, cabecalhoTela } from './crud.js';

const ehAdmin = (u) => u.cargo === 'Administrador';
const sim = (v) => h('span', { class: 'badge ' + (v ? 'st-aprovado' : 'st-fila') }, v ? 'Sim' : 'Não');

// ------------------------------------------------------------------ COMPONENTES (RF013)
export function telaComponentes(container, ctx) {
  return telaCrud(container, ctx, {
    titulo: 'Componentes', subtitulo: 'Peças e materiais usados na montagem dos notebooks, com o saldo em estoque.',
    icone: 'cpu', endpoint: '/api/componentes', chave: 'idcmp', ordemInicial: { chave: 'nome', dir: 1 },
    rotuloRegistro: (r) => `${r.codigo_sku} - ${r.nome}`, largura: 560,
    colunas: [
      { chave: 'codigo_sku', titulo: 'SKU', largura: '130px' },
      { chave: 'nome', titulo: 'Componente' },
      { chave: 'qtd_estoque', titulo: 'Estoque', alinhar: 'dir', largura: '130px',
        render: (l) => h('span', { class: l.estoque_critico ? 'estoque-critico' : '' },
          l.estoque_critico && icone('alerta', 14), fmtNum(l.qtd_estoque)) },
      { chave: 'qtd_pendente', titulo: 'Solicitado e não baixado', alinhar: 'dir', largura: '190px', render: (l) => fmtNum(l.qtd_pendente) },
      { chave: 'saldo', titulo: 'Saldo após pendências', alinhar: 'dir', largura: '170px',
        ordem: (l) => l.qtd_estoque - l.qtd_pendente, texto: (l) => String(l.qtd_estoque - l.qtd_pendente),
        render: (l) => h('span', { class: l.qtd_estoque - l.qtd_pendente < 0 ? 'estoque-critico' : '' }, fmtNum(l.qtd_estoque - l.qtd_pendente)) },
      { chave: 'criado_por_nome', titulo: 'Cadastrado por' },
    ],
    campos: () => [
      { nome: 'codigo_sku', rotulo: 'Código SKU', obrigatorio: true, maxlength: 50 },
      { nome: 'qtd_estoque', rotulo: 'Quantidade em estoque', tipo: 'numero', min: 0, passo: 1, obrigatorio: true, valor: 0 },
      { nome: 'nome', rotulo: 'Nome do componente', obrigatorio: true, span: 2, maxlength: 100 },
    ],
    payload: (v) => ({ nome: v.nome, codigo_sku: v.codigo_sku, qtd_estoque: v.qtd_estoque ?? 0 }),
  });
}

// ------------------------------------------------------------------ PRODUTOS + COMPONENTES (RF016)
function abaComponentesProduto(estado, ctx, somenteLeitura) {
  estado.componentes = (estado.registro?.componentes || []).map((c) => ({ ...c }));
  const tituloAba = () => `Componentes (${estado.componentes.length})`;

  const g = grade({
    compacto: true, id: 'componente_id', aoSelecionar: atualizarBotoes,
    aoAbrir: () => alterar(),
    colunas: [
      { chave: 'codigo_sku', titulo: 'SKU', largura: '140px' },
      { chave: 'nome', titulo: 'Componente' },
      { chave: 'quantidade_necessaria', titulo: 'Qtd. por notebook', alinhar: 'dir', largura: '150px' },
      { chave: 'qtd_estoque', titulo: 'Estoque atual', alinhar: 'dir', largura: '130px', render: (l) => fmtNum(l.qtd_estoque) },
    ],
  });
  const tb = barra([
    { id: 'vincular', icone: 'mais', rotulo: 'Vincular componente', tipo: 'novo', aoClicar: vincular },
    { id: 'qtd', icone: 'lapis', rotulo: 'Alterar quantidade', tipo: 'editar', aoClicar: alterar },
    { id: 'remover', icone: 'lixeira', rotulo: 'Remover vínculo', tipo: 'perigo', aoClicar: remover },
  ]);

  function atualizarBotoes() {
    const s = g.selecionado();
    tb.habilitar('vincular', !somenteLeitura);
    tb.habilitar('qtd', !!s && !somenteLeitura, 'Selecione um componente da lista');
    tb.habilitar('remover', !!s && !somenteLeitura, 'Selecione um componente da lista');
  }
  function redesenhar() {
    estado.componentes.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
    g.setDados(estado.componentes);
    estado.definirTituloAba('componentes', tituloAba());
  }
  estado.recarregarComponentes = (lista) => {
    estado.componentes = lista.map((c) => ({ ...c }));
    redesenhar();
  };

  function vincular() {
    const livres = estado.lookups.componentes.filter((c) => !estado.componentes.some((x) => x.componente_id === c.idcmp));
    if (!livres.length) { toast('Todos os componentes cadastrados já estão vinculados a este produto.', 'erro'); return; }
    dialogo({
      titulo: 'Vincular componente ao produto', icone: 'link', textoOk: 'Vincular', largura: 500,
      campos: [
        { nome: 'componente_id', rotulo: 'Componente', tipo: 'select', obrigatorio: true, span: 2,
          opcoes: livres.map((c) => ({ valor: c.idcmp, rotulo: `${c.codigo_sku} — ${c.nome}` })) },
        { nome: 'quantidade', rotulo: 'Quantidade usada em cada notebook', tipo: 'numero', min: 1, passo: 1, valor: 1, obrigatorio: true, span: 2 },
      ],
      aoConfirmar: (v) => {
        if (!(v.quantidade >= 1)) { toast('Informe uma quantidade maior que zero.', 'erro'); return false; }
        const c = livres.find((x) => x.idcmp === v.componente_id);
        estado.componentes.push({ componente_id: c.idcmp, nome: c.nome, codigo_sku: c.codigo_sku,
          qtd_estoque: c.qtd_estoque, quantidade_necessaria: Math.floor(v.quantidade) });
        redesenhar();
      },
    });
  }
  function alterar() {
    const s = g.selecionado();
    if (!s || somenteLeitura) return;
    dialogo({
      titulo: `Alterar quantidade — ${s.nome}`, icone: 'lapis', textoOk: 'Aplicar', largura: 440,
      campos: [{ nome: 'quantidade', rotulo: 'Quantidade usada em cada notebook', tipo: 'numero', min: 1, passo: 1,
        valor: s.quantidade_necessaria, obrigatorio: true, span: 2 }],
      aoConfirmar: (v) => {
        if (!(v.quantidade >= 1)) { toast('Informe uma quantidade maior que zero.', 'erro'); return false; }
        s.quantidade_necessaria = Math.floor(v.quantidade);
        redesenhar();
      },
    });
  }
  async function remover() {
    const s = g.selecionado();
    if (!s) return;
    if (!(await confirmar({ titulo: 'Remover vínculo', textoOk: 'Remover', perigo: true,
      mensagem: `Remover "${s.nome}" da lista de componentes deste produto?` }))) return;
    estado.componentes = estado.componentes.filter((c) => c.componente_id !== s.componente_id);
    redesenhar();
  }

  return [{
    id: 'componentes', titulo: tituloAba(), icone: 'cpu',
    conteudo: () => {
      redesenhar();
      atualizarBotoes();
      return h('div', { class: 'aba-componentes' },
        h('p', { class: 'dica-aba' }, 'Estes são os componentes usados em cada notebook deste modelo. Eles geram as solicitações de ' +
          'material da produção. As alterações da lista são gravadas ao clicar em OK ou Salvar.'),
        tb.el, g.el);
    },
  }];
}

export function telaProdutos(container, ctx) {
  return telaCrud(container, ctx, {
    titulo: 'Produtos', subtitulo: 'Modelos de notebook e a lista de componentes de cada um.',
    icone: 'caixa', endpoint: '/api/produtos', chave: 'idprd', ordemInicial: { chave: 'nome_modelo', dir: 1 },
    rotuloRegistro: (r) => `${r.codigo_modelo} - ${r.nome_modelo}`, largura: 820,
    preparar: async () => ({ componentes: await api.get('/api/componentes') }),
    carregarRegistro: (r) => api.get(`/api/produtos/${r.idprd}`),
    colunas: [
      { chave: 'codigo_modelo', titulo: 'Código', largura: '160px' },
      { chave: 'nome_modelo', titulo: 'Modelo' },
      { chave: 'quantidade', titulo: 'Quantidade', alinhar: 'dir', largura: '120px', render: (l) => (l.quantidade == null ? '' : fmtNum(l.quantidade)) },
      { chave: 'qtd_componentes', titulo: 'Componentes', alinhar: 'dir', largura: '130px' },
      { chave: 'qtd_producoes', titulo: 'Produções', alinhar: 'dir', largura: '110px' },
      { chave: 'criado_por_nome', titulo: 'Cadastrado por' },
    ],
    campos: () => [
      { nome: 'codigo_modelo', rotulo: 'Código do modelo', obrigatorio: true, maxlength: 50 },
      { nome: 'nome_modelo', rotulo: 'Nome do modelo', obrigatorio: true, maxlength: 100 },
      { nome: 'quantidade', rotulo: 'Quantidade', tipo: 'numero', min: 0, passo: 1, dica: 'Meta/lote planejado deste modelo (opcional).' },
    ],
    abasExtras: abaComponentesProduto,
    aposSalvar: (salvo, estado) => estado.recarregarComponentes && estado.recarregarComponentes(salvo.componentes),
    payload: (v, reg, estado) => ({
      nome_modelo: v.nome_modelo, codigo_modelo: v.codigo_modelo, quantidade: v.quantidade,
      componentes: estado.componentes.map((c) => ({ componente_id: c.componente_id, quantidade_necessaria: c.quantidade_necessaria })),
    }),
  });
}

// ------------------------------------------------------------------ STATUS DE PRODUÇÃO (RF003)
export function telaStatus(container, ctx) {
  return telaCrud(container, ctx, {
    titulo: 'Status de produção', subtitulo: 'Etapas do fluxo fabril, na ordem em que acontecem.',
    icone: 'camadas', endpoint: '/api/status', chave: 'id', ordemInicial: { chave: 'ordem', dir: 1 },
    rotuloRegistro: (r) => r.nome_status, largura: 520,
    podeAlterar: ehAdmin, motivoBloqueio: 'Somente administradores podem alterar os status.',
    colunas: [
      { chave: 'ordem', titulo: 'Ordem', alinhar: 'dir', largura: '100px' },
      { chave: 'nome_status', titulo: 'Status' },
      { chave: 'criado_em', titulo: 'Cadastrado em', render: (l) => fmtData(l.criado_em) },
    ],
    campos: () => [
      { nome: 'nome_status', rotulo: 'Nome do status', obrigatorio: true, maxlength: 50, span: 2 },
      { nome: 'ordem', rotulo: 'Ordem', tipo: 'numero', passo: 1, dica: 'Fluxo normal: 1 a 89. Parado e Reprovado usam 90 ou mais (ficam fora do fluxo).' },
    ],
    payload: (v) => ({ nome_status: v.nome_status, ordem: v.ordem }),
  });
}

// ------------------------------------------------------------------ USUÁRIOS (RF001)
export function telaUsuarios(container, ctx) {
  return telaCrud(container, ctx, {
    titulo: 'Usuários', subtitulo: 'Operadores, almoxarifes e inspetores com acesso ao sistema.',
    icone: 'usuario', endpoint: '/api/usuarios', chave: 'id', ordemInicial: { chave: 'nome', dir: 1 },
    rotuloRegistro: (r) => `${r.matricula} - ${r.nome}`, largura: 640,
    podeAlterar: ehAdmin, motivoBloqueio: 'Somente administradores podem alterar usuários.',
    preparar: async () => ({ cargos: (await api.get('/api/cargos')).filter((c) => c !== 'Integração') }),
    colunas: [
      { chave: 'matricula', titulo: 'Matrícula', largura: '130px' },
      { chave: 'nome', titulo: 'Nome' },
      { chave: 'email', titulo: 'E-mail' },
      { chave: 'cargo', titulo: 'Cargo' },
      { chave: 'ativo', titulo: 'Ativo', largura: '90px', texto: (l) => (l.ativo ? 'sim' : 'não'), render: (l) => sim(l.ativo) },
    ],
    novoVazio: () => ({ ativo: 1 }),
    campos: (lk, reg) => [
      { nome: 'matricula', rotulo: 'Matrícula', obrigatorio: true, maxlength: 20, placeholder: 'MAT-00000' },
      { nome: 'cargo', rotulo: 'Cargo', tipo: 'select', obrigatorio: true, opcoes: lk.cargos.map((c) => ({ valor: c, rotulo: c })) },
      { nome: 'nome', rotulo: 'Nome completo', obrigatorio: true, span: 2, maxlength: 100 },
      { nome: 'email', rotulo: 'E-mail', tipo: 'email', obrigatorio: true, span: 2, maxlength: 100 },
      { nome: 'senha', rotulo: reg ? 'Nova senha' : 'Senha', tipo: 'senha', obrigatorio: !reg,
        dica: reg ? 'Deixe em branco para manter a senha atual.' : 'Mínimo de 6 caracteres.' },
      { nome: 'ativo', rotulo: 'Usuário ativo', tipo: 'checkbox' },
    ],
    payload: (v) => ({ matricula: v.matricula, nome: v.nome, email: v.email, cargo: v.cargo, ativo: v.ativo ? 1 : 0,
      senha: v.senha || null }),
  });
}

// ------------------------------------------------------------------ INTEGRAÇÕES (chaves de API dos outros sistemas)
function mostrarChave(titulo, chave) {
  const codigo = h('code', { class: 'chave-api' }, chave);
  const copiar = h('button', { type: 'button', class: 'btn', onclick: async () => {
    try { await navigator.clipboard.writeText(chave); toast('Chave copiada.'); }
    catch { const r = document.createRange(); r.selectNodeContents(codigo); const s = getSelection(); s.removeAllRanges(); s.addRange(r); toast('Selecione e copie (Ctrl+C).'); }
  } }, icone('arquivo', 14), 'Copiar');
  const j = janela({ titulo, icone: 'link', largura: 560,
    corpo: [h('p', {}, 'Entregue esta chave à equipe responsável pelo sistema. Ela é enviada no cabeçalho ',
      h('code', {}, 'X-API-Key'), ' e ', h('b', {}, 'não será exibida novamente'), '.'), codigo],
    rodape: [copiar, h('button', { type: 'button', class: 'btn btn-primario', onclick: () => j.fechar() }, 'Já guardei a chave')] });
}

export async function telaIntegracoes(container, ctx) {
  if (!ehAdmin(ctx.usuario)) {
    container.append(cabecalhoTela('link', 'Integrações', 'Somente administradores podem gerenciar as integrações.'));
    return;
  }
  const g = grade({
    id: 'id', aoSelecionar: atualizarBotoes,
    colunas: [
      { chave: 'nome', titulo: 'Sistema', largura: '220px' },
      { chave: 'ativo', titulo: 'Situação', largura: '120px', texto: (l) => (l.ativo ? 'ativo' : 'inativo'),
        render: (l) => h('span', { class: 'badge ' + (l.ativo ? 'st-aprovado' : 'st-fila') }, l.ativo ? 'Ativo' : 'Inativo') },
      { chave: 'ultimo_uso_em', titulo: 'Último uso', render: (l) => (l.ultimo_uso_em ? fmtData(l.ultimo_uso_em) : 'Nunca usou') },
      { chave: 'criado_em', titulo: 'Cadastrado em', render: (l) => fmtData(l.criado_em) },
    ],
  });
  const tb = barra([
    { id: 'novo', icone: 'mais', rotulo: 'Novo sistema', tipo: 'novo', aoClicar: novo },
    { id: 'chave', icone: 'atualizar', rotulo: 'Gerar nova chave', tipo: 'editar', aoClicar: novaChave },
    { id: 'ativo', icone: 'lapis', rotulo: 'Ativar / Inativar', tipo: 'editar', aoClicar: alternarAtivo },
    { id: 'excluir', icone: 'lixeira', rotulo: 'Excluir', tipo: 'perigo', aoClicar: excluir },
    '|',
    { id: 'atualizar', icone: 'atualizar', rotulo: 'Atualizar', tipo: 'editar', aoClicar: carregar },
  ]);
  function atualizarBotoes(sel) { for (const id of ['chave', 'ativo', 'excluir']) tb.habilitar(id, !!sel, 'Selecione um sistema na grade'); }
  async function carregar() { try { g.setDados(await api.get('/api/integracoes')); } catch (e) { toast(e.message, 'erro'); } }
  function novo() {
    dialogo({ titulo: 'Novo sistema integrado', icone: 'link', textoOk: 'Criar e gerar chave', largura: 480,
      campos: [{ nome: 'nome', rotulo: 'Nome do sistema', obrigatorio: true, span: 2, maxlength: 50,
        placeholder: 'ex.: qualidade, manutencao, dashboard', dica: 'Só letras, números, "-" e "_". Aparece no histórico como API:<nome>.' }],
      aoConfirmar: async (v) => { const r = await api.post('/api/integracoes', { nome: v.nome }); await carregar(); mostrarChave(`Chave do sistema "${r.nome}"`, r.chave); } });
  }
  async function novaChave() {
    const s = g.selecionado();
    if (!s || !(await confirmar({ titulo: 'Gerar nova chave', textoOk: 'Gerar', perigo: true,
      mensagem: `A chave atual de "${s.nome}" deixará de funcionar imediatamente. Continuar?` }))) return;
    try { const r = await api.post(`/api/integracoes/${s.id}/nova-chave`); mostrarChave(`Nova chave de "${r.nome}"`, r.chave); } catch (e) { toast(e.message, 'erro'); }
  }
  async function alternarAtivo() {
    const s = g.selecionado();
    if (!s) return;
    try { await api.put(`/api/integracoes/${s.id}`, { ativo: !s.ativo }); await carregar(); g.selecionarId(s.id); } catch (e) { toast(e.message, 'erro'); }
  }
  async function excluir() {
    const s = g.selecionado();
    if (!s || !(await confirmar({ titulo: 'Excluir sistema', textoOk: 'Excluir', perigo: true, mensagem: `Excluir "${s.nome}" e revogar a chave?` }))) return;
    try { await api.del(`/api/integracoes/${s.id}`); toast('Sistema excluído.'); await carregar(); } catch (e) { toast(e.message, 'erro'); }
  }

  const base = location.origin + endereco('/').replace(/\/$/, '');   // inclui a rota do servidor, se houver
  container.append(
    cabecalhoTela('link', 'Integrações', 'Sistemas de outras equipes autorizados a consultar e enviar dados para este sistema.'),
    h('div', { class: 'aviso info' }, icone('info'),
      h('div', {}, 'Endereço da API: ', h('code', {}, base + '/api/v1'), ' · Documentação interativa: ',
        h('a', { href: 'docs', target: '_blank', rel: 'noopener' }, 'docs'),
        ' · Teste rápido: ', h('code', {}, base + '/api/v1/saude'))),
    tb.el, g.el);
  atualizarBotoes(null);
  await carregar();
}
