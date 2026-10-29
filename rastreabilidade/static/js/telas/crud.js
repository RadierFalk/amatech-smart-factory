// Tela de cadastro genérica no estilo TOTVS RM: barra de ícones (Novo/Editar/Excluir/Atualizar), grade com filtro
// por coluna e janela de registro com abas, navegação anterior/próximo e botões OK / Cancelar / Salvar.
import { api } from '../api.js';
import { h, icone, barra, grade, janela, confirmar, formulario, abas, toast } from '../ui.js';

export function cabecalhoTela(icone_, titulo, subtitulo) {
  return h('div', { class: 'tela-cab' }, h('div', { class: 'tela-cab-icone' }, icone(icone_, 24)),
    h('div', {}, h('h2', {}, titulo), subtitulo && h('p', {}, subtitulo)));
}

export async function telaCrud(container, ctx, cfg) {
  const podeAlterar = cfg.podeAlterar ? cfg.podeAlterar(ctx.usuario) : true;
  const motivoBloqueio = cfg.motivoBloqueio || 'Seu cargo não permite alterar este cadastro.';
  let lookups = cfg.preparar ? await cfg.preparar() : {};

  const g = grade({ colunas: cfg.colunas, id: cfg.chave, aoSelecionar: atualizarBotoes,
    aoAbrir: (r) => abrirForm(r), ordemInicial: cfg.ordemInicial });
  const tb = barra([
    { id: 'novo', icone: 'mais', rotulo: 'Novo', tipo: 'novo', titulo: 'Novo registro', aoClicar: () => abrirForm(null) },
    { id: 'editar', icone: 'lapis', rotulo: podeAlterar ? 'Editar' : 'Visualizar', tipo: 'editar', aoClicar: () => { const r = g.selecionado(); if (r) abrirForm(r); } },
    { id: 'excluir', icone: 'lixeira', rotulo: 'Excluir', tipo: 'perigo', aoClicar: () => excluirRegistro(g.selecionado()) },
    '|',
    { id: 'atualizar', icone: 'atualizar', rotulo: 'Atualizar', tipo: 'editar', aoClicar: carregar },
  ]);

  function atualizarBotoes(sel) {
    tb.habilitar('novo', podeAlterar, motivoBloqueio);
    tb.habilitar('editar', !!sel, 'Selecione um registro na grade');
    tb.habilitar('excluir', podeAlterar && !!sel, podeAlterar ? 'Selecione um registro na grade' : motivoBloqueio);
  }

  async function carregar() {
    try { g.setDados(await api.get(cfg.endpoint)); } catch (e) { toast(e.message, 'erro'); }
  }

  async function excluirRegistro(r) {
    if (!r) return false;
    const ok = await confirmar({ titulo: 'Excluir registro', textoOk: 'Excluir', perigo: true,
      mensagem: `Deseja realmente excluir "${cfg.rotuloRegistro(r)}"? Esta ação não pode ser desfeita.` });
    if (!ok) return false;
    try { await api.del(`${cfg.endpoint}/${r[cfg.chave]}`); toast('Registro excluído.'); await carregar(); return true; }
    catch (e) { toast(e.message, 'erro'); return false; }
  }

  async function abrirForm(reg) {
    const somenteLeitura = !podeAlterar;
    if (cfg.preparar) lookups = await cfg.preparar();
    let registro = reg;
    if (reg && cfg.carregarRegistro) {
      try { registro = await cfg.carregarRegistro(reg); } catch (e) { toast(e.message, 'erro'); return; }
    }
    let tabs;
    const estado = { registro, lookups, definirTituloAba: (id, t) => tabs && tabs.definirTitulo(id, t) };
    const defs = cfg.campos(lookups, registro).map((d) => (somenteLeitura ? { ...d, desabilitado: true } : d));
    const form = formulario(defs, registro || (cfg.novoVazio ? cfg.novoVazio() : {}));
    const extras = cfg.abasExtras ? cfg.abasExtras(estado, ctx, somenteLeitura) : [];
    tabs = abas([{ id: 'id', titulo: 'Identificação', icone: 'prancheta', conteudo: form.el }, ...extras]);

    const titulo = () => `${cfg.titulo}: ${estado.registro ? cfg.rotuloRegistro(estado.registro) : 'Novo registro'}`;
    const lista = g.visiveis();
    const posicao = () => (estado.registro ? lista.findIndex((r) => r[cfg.chave] === estado.registro[cfg.chave]) : -1);

    const nav = barra([
      { id: 'novo', icone: 'mais', titulo: 'Novo registro', tipo: 'novo', aoClicar: () => { j.fechar(); abrirForm(null); } },
      { id: 'excluir', icone: 'lixeira', titulo: 'Excluir este registro', tipo: 'perigo',
        aoClicar: async () => { if (await excluirRegistro(estado.registro)) j.fechar(); } },
      { id: 'salvar', icone: 'salvar', titulo: 'Salvar', tipo: 'editar', aoClicar: () => salvar() },
      '|',
      { id: 'ant', icone: 'esq', titulo: 'Registro anterior', aoClicar: () => irPara(-1) },
      { id: 'prox', icone: 'dir', titulo: 'Próximo registro', aoClicar: () => irPara(1) },
    ]);
    function estadoBotoes() {
      const i = posicao();
      nav.habilitar('novo', !somenteLeitura);
      nav.habilitar('excluir', !somenteLeitura && !!estado.registro);
      nav.habilitar('salvar', !somenteLeitura);
      nav.habilitar('ant', i > 0);
      nav.habilitar('prox', i >= 0 && i < lista.length - 1);
    }
    function irPara(delta) {
      const alvo = lista[posicao() + delta];
      if (alvo) { j.fechar(); abrirForm(alvo); }
    }

    async function salvar() {
      if (somenteLeitura) return null;
      if (!form.validar()) { tabs.ativar('id'); return null; }
      const corpo = cfg.payload ? cfg.payload(form.valores(), estado.registro, estado) : form.valores();
      try {
        const salvo = estado.registro
          ? await api.put(`${cfg.endpoint}/${estado.registro[cfg.chave]}`, corpo)
          : await api.post(cfg.endpoint, corpo);
        estado.registro = salvo;
        if (cfg.aposSalvar) cfg.aposSalvar(salvo, estado);
        j.setTitulo(titulo());
        estadoBotoes();
        toast('Registro salvo com sucesso.');
        await carregar();
        g.selecionarId(salvo[cfg.chave]);
        return salvo;
      } catch (e) { toast(e.message, 'erro'); return null; }
    }

    const botaoOk = h('button', { type: 'button', class: 'btn btn-primario', onclick: async () => { if (await salvar()) j.fechar(); } }, 'OK');
    const rodape = somenteLeitura
      ? [h('button', { type: 'button', class: 'btn', onclick: () => j.fechar() }, 'Fechar')]
      : [botaoOk, h('button', { type: 'button', class: 'btn', onclick: () => j.fechar() }, 'Cancelar'),
         h('button', { type: 'button', class: 'btn', onclick: () => salvar() }, 'Salvar')];
    const j = janela({ titulo: titulo(), icone: cfg.icone, largura: cfg.largura || 760, barra: nav, corpo: tabs.el, rodape });
    estadoBotoes();
  }

  container.append(cabecalhoTela(cfg.icone, cfg.titulo, cfg.subtitulo), tb.el, g.el);
  atualizarBotoes(null);
  await carregar();
}
