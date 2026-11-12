import { Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { ItemCadastro, Produto } from '../qld.modelos';
import { QldService, TipoItem } from '../qld.service';

type Aba = 'produtos' | TipoItem;

const ABAS: { id: Aba; rotulo: string; singular: string }[] = [
  { id: 'produtos', rotulo: 'Notebooks', singular: 'Notebook' },
  { id: 'estacoes', rotulo: 'Estações', singular: 'Estação' },
  { id: 'tipos-defeito', rotulo: 'Tipos de defeito', singular: 'Tipo de defeito' },
];

/**
 * Cadastros da Qualidade. Nada é apagado: as ocorrências antigas continuam apontando para os itens inativados.
 * Notebooks ficam aqui até o módulo de Rastreabilidade (dono deles) entrar na API única.
 */
@Component({
  selector: 'am-cadastros-qld',
  imports: [ReactiveFormsModule, Etiqueta],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Cadastros da qualidade</h1>
        <p class="legenda">Itens não são apagados, só inativados: as ocorrências antigas continuam apontando para eles.
          As máquinas vêm do cadastro da Manutenção.</p>
      </div>

      <div class="abas" role="tablist">
        @for (a of abas; track a.id) {
          <button type="button" role="tab" [attr.aria-selected]="aba() === a.id" [class.ativa]="aba() === a.id" (click)="trocar(a.id)">{{ a.rotulo }}</button>
        }
      </div>

      <div aria-live="polite">
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
        @if (sucesso(); as m) { <div class="aviso sucesso">{{ m }}</div> }
      </div>

      @if (aba() === 'produtos') {
        <form class="cartao grade-form" [formGroup]="formProduto" (ngSubmit)="criarProduto()" novalidate>
          <h2 class="titulo-secao largura-total">Novo notebook</h2>
          <label class="campo"><span>Número de série</span><input formControlName="numero_serie" placeholder="Ex.: AMT-000031" /></label>
          <label class="campo"><span>Modelo</span><input formControlName="modelo" placeholder="Ex.: AMT N16" /></label>
          <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Cadastrar notebook</button></div>
        </form>
        <section class="cartao tabela-rolagem">
          <table class="tabela">
            <thead><tr><th scope="col">Número de série</th><th scope="col">Modelo</th><th scope="col">Cadastro</th>
              <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
            <tbody>
              @for (p of produtos(); track p.id) {
                <tr [class.inativo]="!p.ativo">
                  <td class="codigo">{{ p.numero_serie }}</td><td>{{ p.modelo }}</td>
                  <td><am-etiqueta [texto]="p.ativo ? 'Ativo' : 'Inativo'" [tom]="p.ativo ? 'ok' : 'neutro'" /></td>
                  <td><button type="button" class="btn pequeno" [class.perigo]="p.ativo" [disabled]="ocupado()" (click)="alternarProduto(p)">
                    {{ p.ativo ? 'Inativar' : 'Reativar' }}</button></td>
                </tr>
              }
            </tbody>
          </table>
        </section>
      } @else {
        <form class="cartao grade-form" [formGroup]="formItem" (ngSubmit)="criarItem()" novalidate>
          <h2 class="titulo-secao largura-total">{{ aba() === 'estacoes' ? 'Nova estação' : 'Novo tipo de defeito' }}</h2>
          <label class="campo"><span>Nome</span><input formControlName="nome" /></label>
          <label class="campo"><span>Descrição (opcional)</span><input formControlName="descricao" /></label>
          <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Cadastrar</button></div>
        </form>
        <section class="cartao tabela-rolagem">
          <table class="tabela">
            <thead><tr><th scope="col">Nome</th><th scope="col">Descrição</th><th scope="col">Cadastro</th>
              <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
            <tbody>
              @for (i of itens(); track i.id) {
                <tr [class.inativo]="!i.ativo">
                  <td>{{ i.nome }}</td><td>{{ i.descricao ?? '—' }}</td>
                  <td><am-etiqueta [texto]="i.ativo ? 'Ativo' : 'Inativo'" [tom]="i.ativo ? 'ok' : 'neutro'" /></td>
                  <td><button type="button" class="btn pequeno" [class.perigo]="i.ativo" [disabled]="ocupado()" (click)="alternarItem(i)">
                    {{ i.ativo ? 'Inativar' : 'Reativar' }}</button></td>
                </tr>
              }
            </tbody>
          </table>
        </section>
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
    tr.inativo td { color: var(--tinta-2); }
  `,
})
export class CadastrosQld implements OnInit {
  private readonly qld = inject(QldService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly abas = ABAS;
  protected readonly aba = signal<Aba>('produtos');
  protected readonly produtos = signal<Produto[]>([]);
  protected readonly itens = signal<ItemCadastro[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);

  protected readonly formProduto = this.fb.group({
    numero_serie: ['', [Validators.required, Validators.maxLength(30)]],
    modelo: ['', [Validators.required, Validators.maxLength(50)]],
  });
  protected readonly formItem = this.fb.group({
    nome: ['', [Validators.required, Validators.maxLength(60)]],
    descricao: ['', Validators.maxLength(200)],
  });

  ngOnInit(): void {
    void this.carregar();
  }

  protected trocar(aba: Aba): void {
    this.aba.set(aba);
    this.erro.set(null);
    this.sucesso.set(null);
    void this.carregar();
  }

  protected criarProduto(): Promise<void> {
    if (this.formProduto.invalid) return this.invalido(this.formProduto, 'Preencha número de série e modelo.');
    return this.executar(this.qld.criarProduto(this.formProduto.getRawValue()), (p) => {
      this.formProduto.reset();
      return `Notebook ${p.numero_serie} cadastrado.`;
    });
  }

  protected criarItem(): Promise<void> {
    const tipo = this.aba() as TipoItem;
    if (this.formItem.invalid) return this.invalido(this.formItem, 'Preencha o nome.');
    const { nome, descricao } = this.formItem.getRawValue();
    return this.executar(this.qld.criarItem(tipo, { nome, descricao: descricao || null }), (i) => {
      this.formItem.reset();
      return `${this.singular()} "${i.nome}" cadastrado(a).`;
    });
  }

  protected alternarProduto(p: Produto): Promise<void> {
    return this.executar(this.qld.alterarProduto(p.id, { ativo: !p.ativo }), (r) =>
      `Notebook ${r.numero_serie} ${r.ativo ? 'reativado' : 'inativado'}.`,
    );
  }

  protected alternarItem(i: ItemCadastro): Promise<void> {
    return this.executar(this.qld.alterarItem(this.aba() as TipoItem, i.id, { ativo: !i.ativo }), (r) =>
      `${this.singular()} "${r.nome}" ${r.ativo ? 'reativado(a)' : 'inativado(a)'}.`,
    );
  }

  private singular(): string {
    return ABAS.find((a) => a.id === this.aba())!.singular;
  }

  private invalido(form: { markAllAsTouched(): void }, mensagem: string): Promise<void> {
    form.markAllAsTouched();
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
      if (aba === 'produtos') this.produtos.set(await firstValueFrom(this.qld.produtos(true)));
      else this.itens.set(await firstValueFrom(this.qld.itens(aba, true)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
