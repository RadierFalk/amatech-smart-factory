import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Meta, Perda, ResultadoImportacao, numero, somarDias } from '../dsh.modelos';
import { DshService, TipoPlanilha } from '../dsh.service';

/** Lê o arquivo escolhido como texto (UTF-8; o Excel salva CSV com BOM, que o servidor ignora). */
export function lerArquivo(arquivo: File): Promise<string> {
  return arquivo.text();
}

/** Metas, perdas e importação de planilhas (T03, T06 e T07 do sistema antigo). Supervisor e Administrador. */
@Component({
  selector: 'am-lancamentos',
  imports: [ReactiveFormsModule, DatePipe],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Metas e perdas</h1>
        <p class="legenda">Produção, defeitos e paradas não são lançados aqui: vêm da Rastreabilidade, da Qualidade e da Manutenção.</p>
      </div>

      <div aria-live="polite">
        @if (sucesso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      </div>

      <div class="colunas">
        <form class="cartao grade" [formGroup]="formMeta" (ngSubmit)="gravarMeta()" novalidate>
          <h2 class="titulo-secao largura-total">Meta de produção</h2>
          <label class="campo"><span>Dia</span><input type="date" formControlName="data" /></label>
          <label class="campo"><span>Turno</span><select formControlName="turno_id">
            @for (t of opcoes()?.turnos ?? []; track t.id) { <option [ngValue]="t.id">{{ t.nome }}</option> }</select></label>
          <label class="campo"><span>Modelo</span><select formControlName="modelo_id"><option [ngValue]="0" disabled>Selecione…</option>
            @for (m of opcoes()?.modelos ?? []; track m.id) { <option [ngValue]="m.id">{{ m.nome }}</option> }</select></label>
          <label class="campo"><span>Quantidade</span><input type="number" min="1" formControlName="quantidade" /></label>
          <p class="legenda largura-total">Gravar de novo o mesmo dia, turno e modelo substitui a meta anterior.</p>
          <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Gravar meta</button></div>
        </form>

        <form class="cartao grade" [formGroup]="formPerda" (ngSubmit)="registrarPerda()" novalidate>
          <h2 class="titulo-secao largura-total">Perda</h2>
          <label class="campo"><span>Dia</span><input type="date" formControlName="data" [max]="opcoes()?.hoje ?? ''" /></label>
          <label class="campo"><span>Turno</span><select formControlName="turno_id">
            @for (t of opcoes()?.turnos ?? []; track t.id) { <option [ngValue]="t.id">{{ t.nome }}</option> }</select></label>
          <label class="campo"><span>Estação</span><select formControlName="estacao_id"><option [ngValue]="0" disabled>Selecione…</option>
            @for (e of opcoes()?.estacoes ?? []; track e.id) { <option [ngValue]="e.id">{{ e.nome }}</option> }</select></label>
          <label class="campo"><span>Modelo</span><select formControlName="modelo_id"><option [ngValue]="0" disabled>Selecione…</option>
            @for (m of opcoes()?.modelos ?? []; track m.id) { <option [ngValue]="m.id">{{ m.nome }}</option> }</select></label>
          <label class="campo"><span>Tipo</span><select formControlName="tipo_perda_id"><option [ngValue]="0" disabled>Selecione…</option>
            @for (t of tiposAtivos(); track t.id) { <option [ngValue]="t.id">{{ t.nome }}</option> }</select></label>
          <label class="campo"><span>Quantidade</span><input type="number" min="1" formControlName="quantidade" /></label>
          <label class="campo largura-total"><span>Observação (opcional)</span><input formControlName="observacao" /></label>
          <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">Registrar perda</button></div>
        </form>
      </div>

      <section class="cartao planilha">
        <h2 class="titulo-secao">Importar planilha</h2>
        <p class="legenda">Tudo ou nada: se uma linha tiver erro, nenhuma é gravada, e a lista abaixo diz linha, coluna e problema.</p>
        <div class="linha-planilha">
          <label class="campo"><span>Tipo</span>
            <select [value]="tipoPlanilha()" (change)="tipoPlanilha.set($any($event.target).value)">
              <option value="metas">Metas</option><option value="perdas">Perdas</option></select></label>
          <label class="campo"><span>Arquivo CSV</span><input type="file" accept=".csv,text/csv" (change)="importar($event)" [disabled]="ocupado()" /></label>
          <button type="button" class="btn" (click)="baixarModelo()">Baixar planilha modelo</button>
        </div>
        @if (importacao(); as r) {
          @if (r.erros.length) {
            <div class="aviso erro" role="alert">Nada foi importado: {{ r.erros.length }} problema(s) em {{ r.linhas_lidas }} linha(s).</div>
            <div class="tabela-rolagem"><table class="tabela">
              <thead><tr><th scope="col" class="num">Linha</th><th scope="col">Coluna</th><th scope="col">Problema</th></tr></thead>
              <tbody>@for (e of r.erros; track $index) { <tr><td class="num">{{ e.linha }}</td><td>{{ e.coluna }}</td><td>{{ e.mensagem }}</td></tr> }</tbody>
            </table></div>
          }
        }
      </section>

      <div class="colunas">
        <section class="cartao">
          <h2 class="titulo-secao">Metas dos últimos 30 dias</h2>
          @if (metas().length) {
            <div class="tabela-rolagem"><table class="tabela">
              <thead><tr><th scope="col">Dia</th><th scope="col">Turno</th><th scope="col">Modelo</th><th scope="col" class="num">Meta</th>
                <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>@for (m of metas(); track m.id) {
                <tr><td class="nowrap">{{ m.data | date: 'dd/MM/yyyy' : 'UTC' }}</td><td>{{ m.turno_nome }}</td><td>{{ m.modelo_nome }}</td>
                  <td class="num">{{ numero(m.quantidade) }}</td>
                  <td><button type="button" class="btn pequeno perigo" [disabled]="ocupado()" (click)="excluirMeta(m)">Excluir</button></td></tr>
              }</tbody>
            </table></div>
          } @else { <p class="legenda">Nenhuma meta.</p> }
        </section>
        <section class="cartao">
          <h2 class="titulo-secao">Perdas dos últimos 30 dias</h2>
          @if (perdas().length) {
            <div class="tabela-rolagem"><table class="tabela">
              <thead><tr><th scope="col">Dia</th><th scope="col">Tipo</th><th scope="col">Modelo</th><th scope="col" class="num">Qtd.</th>
                <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>@for (p of perdas(); track p.id) {
                <tr><td class="nowrap">{{ p.data | date: 'dd/MM/yyyy' : 'UTC' }}</td><td>{{ p.tipo_nome }}</td><td>{{ p.modelo_nome }}</td>
                  <td class="num">{{ numero(p.quantidade) }}</td>
                  <td><button type="button" class="btn pequeno perigo" [disabled]="ocupado()" (click)="excluirPerda(p)">Excluir</button></td></tr>
              }</tbody>
            </table></div>
          } @else { <p class="legenda">Nenhuma perda.</p> }
        </section>
      </div>
    </div>
  `,
  styles: `
    .colunas { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(380px, 100%), 1fr)); gap: var(--space-4); align-items: start; }
    .grade { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-3); align-items: end; }
    .largura-total { grid-column: 1 / -1; }
    .planilha { display: grid; gap: var(--space-3); }
    .linha-planilha { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: flex-end; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .nowrap { white-space: nowrap; }
  `,
})
export class Lancamentos implements OnInit {
  private readonly dsh = inject(DshService);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly numero = numero;
  protected readonly opcoes = this.dsh.opcoes;
  protected readonly tiposAtivos = computed(() => (this.opcoes()?.tipos_perda ?? []).filter((t) => t.ativo));
  protected readonly metas = signal<Meta[]>([]);
  protected readonly perdas = signal<Perda[]>([]);
  protected readonly tipoPlanilha = signal<TipoPlanilha>('metas');
  protected readonly importacao = signal<ResultadoImportacao | null>(null);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);

  protected readonly formMeta = this.fb.group({
    data: ['', Validators.required], turno_id: [0, Validators.min(1)], modelo_id: [0, Validators.min(1)],
    quantidade: [0, [Validators.required, Validators.min(1)]],
  });
  protected readonly formPerda = this.fb.group({
    data: ['', Validators.required], turno_id: [0, Validators.min(1)], estacao_id: [0, Validators.min(1)],
    modelo_id: [0, Validators.min(1)], tipo_perda_id: [0, Validators.min(1)],
    quantidade: [1, [Validators.required, Validators.min(1)]], observacao: '',
  });

  async ngOnInit(): Promise<void> {
    try {
      const o = await this.dsh.carregarOpcoes();
      const turno = o.turnos[0]?.id ?? 0;
      this.formMeta.patchValue({ data: o.hoje, turno_id: turno });
      this.formPerda.patchValue({ data: o.hoje, turno_id: turno });
      await this.carregarListas();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  private async carregarListas(): Promise<void> {
    const hoje = this.opcoes()!.hoje;
    const de = somarDias(hoje, -29);
    const [metas, perdas] = await Promise.all([
      firstValueFrom(this.dsh.metas(de, somarDias(hoje, 30))), // metas também podem ser planejadas adiante
      firstValueFrom(this.dsh.perdas({ de, ate: hoje })),
    ]);
    this.metas.set(metas);
    this.perdas.set(perdas);
  }

  protected gravarMeta(): Promise<void> {
    if (this.formMeta.invalid) return this.falhar('Preencha dia, turno, modelo e uma quantidade maior que zero.');
    return this.executar(this.dsh.gravarMeta(this.formMeta.getRawValue()), (m: Meta) =>
      `Meta de ${numero(m.quantidade)} gravada para ${m.modelo_nome}, ${m.turno_nome}.`);
  }

  protected registrarPerda(): Promise<void> {
    if (this.formPerda.invalid) return this.falhar('Preencha dia, turno, estação, modelo, tipo e quantidade.');
    const f = this.formPerda.getRawValue();
    return this.executar(this.dsh.registrarPerda({ ...f, observacao: f.observacao || null }), (p: Perda) => {
      this.formPerda.patchValue({ quantidade: 1, observacao: '' });
      return `Perda de ${numero(p.quantidade)} un. registrada (${p.tipo_nome}).`;
    });
  }

  protected excluirMeta(m: Meta): Promise<void> {
    if (!confirm(`Excluir a meta de ${m.modelo_nome} (${m.turno_nome})?`)) return Promise.resolve();
    return this.executar(this.dsh.excluirMeta(m.id), () => 'Meta excluída.');
  }

  protected excluirPerda(p: Perda): Promise<void> {
    if (!confirm(`Excluir a perda de ${p.quantidade} un. (${p.tipo_nome})?`)) return Promise.resolve();
    return this.executar(this.dsh.excluirPerda(p.id), () => 'Perda excluída.');
  }

  protected async importar(evento: Event): Promise<void> {
    const campo = evento.target as HTMLInputElement;
    const arquivo = campo.files?.[0];
    if (!arquivo) return;
    this.importacao.set(null);
    await this.executar(this.dsh.importar(this.tipoPlanilha(), await lerArquivo(arquivo)), (r: ResultadoImportacao) => {
      this.importacao.set(r);
      return r.erros.length ? '' : `${r.importadas} linha(s) importada(s) de ${arquivo.name}.`;
    });
    campo.value = '';
  }

  protected async baixarModelo(): Promise<void> {
    try {
      const blob = await firstValueFrom(this.dsh.modeloPlanilha(this.tipoPlanilha()));
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `modelo_${this.tipoPlanilha()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  private falhar(mensagem: string): Promise<void> {
    this.sucesso.set(null);
    this.erro.set(mensagem);
    return Promise.resolve();
  }

  private async executar<T>(acao: Observable<T>, mensagem: (r: T) => string): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.sucesso.set(null);
    try {
      const r = await firstValueFrom(acao);
      this.sucesso.set(mensagem(r) || null);
      await this.carregarListas();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }
}
