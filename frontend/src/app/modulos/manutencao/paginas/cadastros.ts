import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { Equipamento, Peca, ROTULO_STATUS_EQUIPAMENTO, TOM_STATUS_EQUIPAMENTO } from '../mnt.modelos';
import { MntService } from '../mnt.service';

/** Cadastro de máquinas (TAGs) e do catálogo de peças. Nada é apagado: inativa-se (RN07). */
@Component({
  selector: 'am-cadastros-mnt',
  imports: [ReactiveFormsModule, Etiqueta],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Cadastros da manutenção</h1>
        <p class="legenda">Máquinas e peças não são apagadas, só inativadas: o histórico das OS continua apontando para elas.</p>
      </div>

      <div class="abas" role="tablist">
        <button type="button" role="tab" [attr.aria-selected]="aba() === 'maquinas'" [class.ativa]="aba() === 'maquinas'" (click)="aba.set('maquinas')">Máquinas</button>
        <button type="button" role="tab" [attr.aria-selected]="aba() === 'pecas'" [class.ativa]="aba() === 'pecas'" (click)="aba.set('pecas')">Peças</button>
      </div>

      <div aria-live="polite">
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
        @if (sucesso(); as m) { <div class="aviso sucesso">{{ m }}</div> }
      </div>

      @if (aba() === 'maquinas') {
        <form class="cartao grade-form" [formGroup]="formMaquina" (ngSubmit)="criarMaquina()" novalidate>
          <h2 class="titulo-secao largura-total">Nova máquina</h2>
          <label class="campo"><span>TAG</span><input formControlName="codigo_tag" placeholder="Ex.: SMT-04" /></label>
          <label class="campo"><span>Nome</span><input formControlName="nome" /></label>
          <label class="campo"><span>Setor</span>
            <input formControlName="setor" list="setores-mnt" />
            <datalist id="setores-mnt">@for (s of setores(); track s) { <option [value]="s"></option> }</datalist>
          </label>
          <label class="campo"><span>Posto (opcional)</span><input formControlName="posto_trabalho" placeholder="Posto 01" /></label>
          <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Cadastrar máquina</button></div>
        </form>

        <section class="cartao tabela-rolagem">
          <table class="tabela">
            <thead><tr><th scope="col">TAG</th><th scope="col">Nome</th><th scope="col">Setor</th><th scope="col">Posto</th>
              <th scope="col">Status</th><th scope="col">Cadastro</th><th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
            <tbody>
              @for (e of maquinas(); track e.id) {
                <tr [class.inativo]="!e.ativo">
                  <td class="codigo">{{ e.codigo_tag }}</td><td>{{ e.nome }}</td><td>{{ e.setor }}</td><td>{{ e.posto_trabalho ?? '—' }}</td>
                  <td><am-etiqueta [texto]="rotuloStatus[e.status_operacional]" [tom]="tomStatus[e.status_operacional]" /></td>
                  <td><am-etiqueta [texto]="e.ativo ? 'Ativa' : 'Inativa'" [tom]="e.ativo ? 'ok' : 'neutro'" /></td>
                  <td><button type="button" class="btn pequeno" [class.perigo]="e.ativo" [disabled]="ocupado()" (click)="alternarMaquina(e)">
                    {{ e.ativo ? 'Inativar' : 'Reativar' }}</button></td>
                </tr>
              }
            </tbody>
          </table>
        </section>
      } @else {
        <form class="cartao grade-form" [formGroup]="formPeca" (ngSubmit)="criarPeca()" novalidate>
          <h2 class="titulo-secao largura-total">Nova peça</h2>
          <label class="campo"><span>Código (part number)</span><input formControlName="codigo_peca" placeholder="Ex.: PN-ROL-608" /></label>
          <label class="campo"><span>Nome</span><input formControlName="nome" /></label>
          <label class="campo"><span>Unidade</span><input formControlName="unidade_medida" /></label>
          <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Cadastrar peça</button></div>
        </form>

        <section class="cartao tabela-rolagem">
          <table class="tabela">
            <thead><tr><th scope="col">Código</th><th scope="col">Nome</th><th scope="col">Unidade</th><th scope="col">Cadastro</th>
              <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
            <tbody>
              @for (p of pecas(); track p.id) {
                <tr [class.inativo]="!p.ativo">
                  <td class="codigo">{{ p.codigo_peca }}</td><td>{{ p.nome }}</td><td>{{ p.unidade_medida }}</td>
                  <td><am-etiqueta [texto]="p.ativo ? 'Ativa' : 'Inativa'" [tom]="p.ativo ? 'ok' : 'neutro'" /></td>
                  <td><button type="button" class="btn pequeno" [class.perigo]="p.ativo" [disabled]="ocupado()" (click)="alternarPeca(p)">
                    {{ p.ativo ? 'Inativar' : 'Reativar' }}</button></td>
                </tr>
              }
            </tbody>
          </table>
        </section>
      }
    </div>
  `,
  styles: `
    .abas { display: flex; gap: var(--space-1); border-bottom: 1px solid var(--linha); }
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
export class Cadastros implements OnInit {
  private readonly mnt = inject(MntService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly rotuloStatus = ROTULO_STATUS_EQUIPAMENTO;
  protected readonly tomStatus = TOM_STATUS_EQUIPAMENTO;
  protected readonly aba = signal<'maquinas' | 'pecas'>('maquinas');
  protected readonly maquinas = signal<Equipamento[]>([]);
  protected readonly pecas = signal<Peca[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);
  protected readonly setores = computed(() => this.mnt.opcoes()?.setores ?? []);

  protected readonly formMaquina = this.fb.group({
    codigo_tag: ['', [Validators.required, Validators.maxLength(30)]],
    nome: ['', [Validators.required, Validators.maxLength(100)]],
    setor: ['', [Validators.required, Validators.maxLength(50)]],
    posto_trabalho: ['', Validators.maxLength(50)],
  });
  protected readonly formPeca = this.fb.group({
    codigo_peca: ['', [Validators.required, Validators.maxLength(50)]],
    nome: ['', [Validators.required, Validators.maxLength(100)]],
    unidade_medida: ['UN', [Validators.required, Validators.maxLength(10)]],
  });

  ngOnInit(): void {
    void this.carregar();
  }

  protected criarMaquina(): Promise<void> {
    if (this.formMaquina.invalid) return this.invalido(this.formMaquina, 'Preencha TAG, nome e setor.');
    const dados = this.formMaquina.getRawValue();
    return this.executar(this.mnt.criarEquipamento({ ...dados, posto_trabalho: dados.posto_trabalho || null }), (e) => {
      this.formMaquina.reset();
      return `Máquina ${e.codigo_tag} cadastrada.`;
    });
  }

  protected criarPeca(): Promise<void> {
    if (this.formPeca.invalid) return this.invalido(this.formPeca, 'Preencha código, nome e unidade.');
    return this.executar(this.mnt.criarPeca(this.formPeca.getRawValue()), (p) => {
      this.formPeca.reset();
      return `Peça ${p.codigo_peca} cadastrada.`;
    });
  }

  protected alternarMaquina(e: Equipamento): Promise<void> {
    return this.executar(this.mnt.alterarEquipamento(e.id, { ativo: !e.ativo }), (r) =>
      `Máquina ${r.codigo_tag} ${r.ativo ? 'reativada' : 'inativada'}.`,
    );
  }

  protected alternarPeca(p: Peca): Promise<void> {
    return this.executar(this.mnt.alterarPeca(p.id, { ativo: !p.ativo }), (r) => `Peça ${r.codigo_peca} ${r.ativo ? 'reativada' : 'inativada'}.`);
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
      const [maquinas, pecas] = await Promise.all([
        firstValueFrom(this.mnt.equipamentos(null, true)),
        firstValueFrom(this.mnt.pecas(true)),
      ]);
      this.maquinas.set([...maquinas].sort((a, b) => a.codigo_tag.localeCompare(b.codigo_tag)));
      this.pecas.set(pecas);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
