import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormArray, FormControl, FormGroup, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { Componente, Etapa, Modelo } from '../ras.modelos';
import { RasService } from '../ras.service';

type Aba = 'componentes' | 'modelos' | 'etapas';
type LinhaLista = FormGroup<{ componente_id: FormControl<number>; quantidade: FormControl<number> }>;

/**
 * Cadastros da Rastreabilidade. Componentes e modelos são inativados, nunca apagados.
 * Componentes: Almoxarife, Supervisor e Administrador. Modelos e etapas: Supervisor e Administrador.
 */
@Component({
  selector: 'am-cadastros-ras',
  imports: [ReactiveFormsModule, Etiqueta],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Cadastros da rastreabilidade</h1>
        <p class="legenda">Componentes e modelos não são apagados, só inativados: as produções antigas continuam apontando para eles.</p>
      </div>

      <div class="abas" role="tablist">
        @for (a of abas(); track a.id) {
          <button type="button" role="tab" [attr.aria-selected]="aba() === a.id" [class.ativa]="aba() === a.id" (click)="trocar(a.id)">{{ a.rotulo }}</button>
        }
      </div>

      <div aria-live="polite">
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
        @if (sucesso(); as m) { <div class="aviso sucesso">{{ m }}</div> }
      </div>

      @switch (aba()) {
        @case ('componentes') {
          <form class="cartao grade-form" [formGroup]="formComponente" (ngSubmit)="criarComponente()" novalidate>
            <h2 class="titulo-secao largura-total">Novo componente</h2>
            <label class="campo"><span>SKU</span><input formControlName="sku" placeholder="Ex.: SSD-1T-NV" /></label>
            <label class="campo"><span>Nome</span><input formControlName="nome" /></label>
            <label class="campo"><span>Estoque inicial</span><input type="number" min="0" formControlName="estoque" /></label>
            <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Cadastrar componente</button></div>
          </form>
          <section class="cartao tabela-rolagem">
            <table class="tabela">
              <thead><tr><th scope="col">SKU</th><th scope="col">Nome</th><th scope="col" class="num">Estoque</th>
                <th scope="col" class="num">Pendente</th><th scope="col">Cadastro</th><th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>@for (c of componentes(); track c.id) {
                <tr [class.inativo]="!c.ativo">
                  <td class="codigo">{{ c.sku }}</td><td>{{ c.nome }}</td>
                  <td class="num">{{ c.estoque }} @if (c.estoque_critico) { <am-etiqueta texto="Crítico" tom="critico" /> }</td>
                  <td class="num">{{ c.pendente }}</td>
                  <td><am-etiqueta [texto]="c.ativo ? 'Ativo' : 'Inativo'" [tom]="c.ativo ? 'ok' : 'neutro'" /></td>
                  <td class="acoes">
                    <button type="button" class="btn pequeno" [disabled]="ocupado()" (click)="ajustarEstoque(c)">Ajustar estoque</button>
                    <button type="button" class="btn pequeno" [class.perigo]="c.ativo" [disabled]="ocupado()" (click)="alternarComponente(c)">{{ c.ativo ? 'Inativar' : 'Reativar' }}</button>
                  </td>
                </tr>
              }</tbody>
            </table>
          </section>
        }
        @case ('modelos') {
          <form class="cartao grade-form" [formGroup]="formModelo" (ngSubmit)="salvarModelo()" novalidate>
            <h2 class="titulo-secao largura-total">{{ editando() ? 'Editar modelo' : 'Novo modelo' }}</h2>
            <label class="campo"><span>Código</span><input formControlName="codigo" placeholder="Ex.: N19-I7-32-1T" /></label>
            <label class="campo"><span>Nome</span><input formControlName="nome" placeholder="Ex.: AMT N19" /></label>
            <label class="campo"><span>Meta (opcional)</span><input type="number" min="0" formControlName="meta" /></label>
            <fieldset class="largura-total lista" formArrayName="componentes">
              <legend>Lista de componentes (por notebook)</legend>
              @for (item of itens.controls; track $index; let i = $index) {
                <div class="linha-lista" [formGroupName]="i">
                  <select formControlName="componente_id" [attr.aria-label]="'Componente ' + (i + 1)">
                    <option [ngValue]="0" disabled>Componente…</option>
                    @for (c of componentesAtivos(); track c.id) { <option [ngValue]="c.id">{{ c.sku }} · {{ c.nome }}</option> }
                  </select>
                  <input type="number" min="1" formControlName="quantidade" [attr.aria-label]="'Quantidade ' + (i + 1)" />
                  <button type="button" class="btn pequeno" (click)="itens.removeAt(i)">Remover</button>
                </div>
              }
              <button type="button" class="btn pequeno" (click)="adicionarItem()">Adicionar componente</button>
            </fieldset>
            <div class="largura-total botoes">
              <button type="submit" class="btn primario" [disabled]="ocupado()">{{ editando() ? 'Salvar modelo' : 'Cadastrar modelo' }}</button>
              @if (editando()) { <button type="button" class="btn" (click)="novoModelo()">Cancelar edição</button> }
            </div>
          </form>
          <section class="cartao tabela-rolagem">
            <table class="tabela">
              <thead><tr><th scope="col">Código</th><th scope="col">Nome</th><th scope="col" class="num">Meta</th>
                <th scope="col" class="num">Componentes</th><th scope="col" class="num">Produções</th><th scope="col">Cadastro</th>
                <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>@for (m of modelos(); track m.id) {
                <tr [class.inativo]="!m.ativo">
                  <td class="codigo">{{ m.codigo }}</td><td>{{ m.nome }}</td><td class="num">{{ m.meta ?? '—' }}</td>
                  <td class="num">{{ m.componentes.length }}</td><td class="num">{{ m.producoes }}</td>
                  <td><am-etiqueta [texto]="m.ativo ? 'Ativo' : 'Inativo'" [tom]="m.ativo ? 'ok' : 'neutro'" /></td>
                  <td class="acoes">
                    <button type="button" class="btn pequeno" (click)="editarModelo(m)">Editar</button>
                    <button type="button" class="btn pequeno" [class.perigo]="m.ativo" [disabled]="ocupado()" (click)="alternarModelo(m)">{{ m.ativo ? 'Inativar' : 'Reativar' }}</button>
                  </td>
                </tr>
              }</tbody>
            </table>
          </section>
        }
        @case ('etapas') {
          <form class="cartao grade-form" [formGroup]="formEtapa" (ngSubmit)="criarEtapa()" novalidate>
            <h2 class="titulo-secao largura-total">Nova etapa</h2>
            <label class="campo"><span>Nome</span><input formControlName="nome" /></label>
            <label class="campo"><span>Ordem (opcional)</span><input type="number" min="0" formControlName="ordem" />
              <span class="campo-dica">Vazio: entra no fim do fluxo. 90 ou mais: etapa lateral (como Parado e Reprovado).</span></label>
            <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Cadastrar etapa</button></div>
          </form>
          <section class="cartao tabela-rolagem">
            <table class="tabela">
              <thead><tr><th scope="col" class="num">Ordem</th><th scope="col">Etapa</th><th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>@for (e of etapas(); track e.id) {
                <tr>
                  <td class="num">{{ e.ordem }}</td><td>{{ e.nome }}</td>
                  <td class="acoes">
                    <button type="button" class="btn pequeno" [disabled]="ocupado()" (click)="renomearEtapa(e)">Alterar</button>
                    <button type="button" class="btn pequeno perigo" [disabled]="ocupado()" (click)="excluirEtapa(e)">Excluir</button>
                  </td>
                </tr>
              }</tbody>
            </table>
          </section>
        }
      }
    </div>
  `,
  styles: `
    .abas { display: flex; flex-wrap: wrap; gap: var(--space-1); border-bottom: 1px solid var(--linha); }
    .abas button {
      background: none; border: 0; border-bottom: 3px solid transparent; padding: var(--space-2) var(--space-4);
      font: inherit; font-weight: 600; color: var(--tinta-2); cursor: pointer;
      &.ativa { color: var(--sinal); border-bottom-color: var(--sinal); }
    }
    .grade-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-4); }
    .largura-total { grid-column: 1 / -1; }
    .lista { border: 1px solid var(--linha); border-radius: var(--radius-sm); padding: var(--space-3); display: grid; gap: var(--space-2); }
    legend { font-weight: 600; padding: 0 var(--space-1); }
    .linha-lista { display: grid; grid-template-columns: minmax(0, 1fr) 80px auto; gap: var(--space-2); align-items: center; }
    .botoes, .acoes { display: flex; flex-wrap: wrap; gap: var(--space-1); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    tr.inativo td { color: var(--tinta-2); }
  `,
})
export class CadastrosRas implements OnInit {
  private readonly ras = inject(RasService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly abas = computed(() => {
    const p = this.ras.opcoes()?.permissoes;
    const lista: { id: Aba; rotulo: string }[] = [];
    if (p?.componentes) lista.push({ id: 'componentes', rotulo: 'Componentes' });
    if (p?.modelos_etapas) lista.push({ id: 'modelos', rotulo: 'Modelos' }, { id: 'etapas', rotulo: 'Etapas' });
    return lista;
  });
  protected readonly aba = signal<Aba>('componentes');
  protected readonly componentes = signal<Componente[]>([]);
  protected readonly componentesAtivos = computed(() => this.componentes().filter((c) => c.ativo));
  protected readonly modelos = signal<Modelo[]>([]);
  protected readonly etapas = computed(() => this.ras.opcoes()?.etapas ?? []);
  protected readonly editando = signal<number | null>(null);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);

  protected readonly formComponente = this.fb.group({
    sku: ['', [Validators.required, Validators.maxLength(50)]],
    nome: ['', [Validators.required, Validators.maxLength(100)]],
    estoque: [0, [Validators.required, Validators.min(0)]],
  });
  protected readonly formModelo = this.fb.group({
    codigo: ['', [Validators.required, Validators.maxLength(50)]],
    nome: ['', [Validators.required, Validators.maxLength(100)]],
    meta: this.fb.control<number | null>(null),
    componentes: this.fb.array<LinhaLista>([]),
  });
  protected readonly formEtapa = this.fb.group({
    nome: ['', [Validators.required, Validators.maxLength(50)]],
    ordem: this.fb.control<number | null>(null),
  });

  protected get itens(): FormArray<LinhaLista> {
    return this.formModelo.controls.componentes;
  }

  async ngOnInit(): Promise<void> {
    try {
      await this.ras.carregarOpcoes();
      this.aba.set(this.abas()[0]?.id ?? 'componentes');
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
    await this.carregar();
  }

  protected trocar(aba: Aba): void {
    this.aba.set(aba);
    this.erro.set(null);
    this.sucesso.set(null);
    void this.carregar();
  }

  private linhaLista(componenteId = 0, quantidade = 1): LinhaLista {
    return this.fb.group({ componente_id: [componenteId, Validators.min(1)], quantidade: [quantidade, Validators.min(1)] });
  }

  protected adicionarItem(): void {
    this.itens.push(this.linhaLista());
  }

  protected novoModelo(): void {
    this.editando.set(null);
    this.formModelo.reset();
    this.itens.clear();
  }

  protected editarModelo(m: Modelo): void {
    this.editando.set(m.id);
    this.formModelo.reset({ codigo: m.codigo, nome: m.nome, meta: m.meta });
    this.itens.clear();
    m.componentes.forEach((c) => this.itens.push(this.linhaLista(c.componente_id, c.quantidade)));
  }

  // ---- componentes
  protected criarComponente(): Promise<void> {
    if (this.formComponente.invalid) return this.invalido('Preencha SKU, nome e estoque (zero ou mais).');
    return this.executar(this.ras.criarComponente(this.formComponente.getRawValue()), (c: Componente) => {
      this.formComponente.reset();
      return `Componente ${c.sku} cadastrado.`;
    });
  }

  protected ajustarEstoque(c: Componente): Promise<void> {
    const texto = prompt(`Estoque de ${c.sku} após a contagem:`, String(c.estoque));
    if (texto === null) return Promise.resolve();
    const estoque = Number(texto);
    if (!Number.isInteger(estoque) || estoque < 0) return this.invalido('O estoque deve ser um número inteiro, zero ou mais.');
    return this.executar(this.ras.alterarComponente(c.id, { estoque }), (r: Componente) => `Estoque de ${r.sku}: ${r.estoque}.`);
  }

  protected alternarComponente(c: Componente): Promise<void> {
    return this.executar(this.ras.alterarComponente(c.id, { ativo: !c.ativo }), (r: Componente) =>
      `Componente ${r.sku} ${r.ativo ? 'reativado' : 'inativado'}.`);
  }

  // ---- modelos
  protected salvarModelo(): Promise<void> {
    if (this.formModelo.invalid) return this.invalido('Preencha código e nome, e escolha componente e quantidade em cada linha.');
    const f = this.formModelo.getRawValue();
    const dados = { codigo: f.codigo, nome: f.nome, meta: f.meta ?? null, componentes: f.componentes };
    const id = this.editando();
    const acao = id ? this.ras.alterarModelo(id, dados) : this.ras.criarModelo(dados);
    return this.executar(acao, (m: Modelo) => {
      this.novoModelo();
      return `Modelo ${m.nome} ${id ? 'salvo' : 'cadastrado'} com ${m.componentes.length} componente(s).`;
    });
  }

  protected alternarModelo(m: Modelo): Promise<void> {
    return this.executar(this.ras.alterarModelo(m.id, { ativo: !m.ativo }), (r: Modelo) =>
      `Modelo ${r.nome} ${r.ativo ? 'reativado' : 'inativado'}.`);
  }

  // ---- etapas
  protected criarEtapa(): Promise<void> {
    if (this.formEtapa.invalid) return this.invalido('Informe o nome da etapa.');
    const f = this.formEtapa.getRawValue();
    return this.executar(this.ras.criarEtapa({ nome: f.nome, ordem: f.ordem ?? null }), (e: Etapa) => {
      this.formEtapa.reset();
      return `Etapa ${e.nome} cadastrada (ordem ${e.ordem}).`;
    });
  }

  protected renomearEtapa(e: Etapa): Promise<void> {
    const nome = prompt('Nome da etapa:', e.nome);
    if (nome === null || !nome.trim()) return Promise.resolve();
    const ordemTexto = prompt('Ordem (90 ou mais = etapa lateral):', String(e.ordem));
    if (ordemTexto === null) return Promise.resolve();
    const ordem = Number(ordemTexto);
    if (!Number.isInteger(ordem) || ordem < 0) return this.invalido('A ordem deve ser um número inteiro, zero ou mais.');
    return this.executar(this.ras.alterarEtapa(e.id, { nome: nome.trim(), ordem }), (r: Etapa) => `Etapa ${r.nome} salva.`);
  }

  protected excluirEtapa(e: Etapa): Promise<void> {
    if (!confirm(`Excluir a etapa ${e.nome}? Só é possível se ela nunca foi usada.`)) return Promise.resolve();
    return this.executar(this.ras.excluirEtapa(e.id), () => `Etapa ${e.nome} excluída.`);
  }

  // ---- apoio
  private invalido(mensagem: string): Promise<void> {
    this.erro.set(mensagem);
    return Promise.resolve();
  }

  private async executar<T>(acao: Observable<T>, mensagem: (r: T) => string): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.sucesso.set(null);
    try {
      const r = await firstValueFrom(acao);
      this.sucesso.set(mensagem(r));
      await this.carregar();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }

  private async carregar(): Promise<void> {
    try {
      const aba = this.aba();
      if (aba === 'etapas') {
        await this.ras.carregarOpcoes(true); // as etapas vêm de /opcoes
        return;
      }
      this.componentes.set(await firstValueFrom(this.ras.componentes(true)));
      if (aba === 'modelos') this.modelos.set(await firstValueFrom(this.ras.modelos(true)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
