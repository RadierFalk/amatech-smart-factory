import { Component, OnInit, computed, inject, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FiltroPainel, somarDias } from '../dsh.modelos';
import { DshService } from '../dsh.service';

const ATALHOS = [
  { dias: 1, rotulo: 'Hoje' },
  { dias: 7, rotulo: '7 dias' },
  { dias: 30, rotulo: '30 dias' },
];

/** Período (atalhos ou datas), turno e modelo numa linha só. "Hoje" vem do servidor: o dia da fábrica. */
@Component({
  selector: 'am-filtro-dsh',
  imports: [FormsModule],
  template: `
    <div class="filtros" role="group" aria-label="Filtros do período">
      <div class="segmentos" role="group" aria-label="Período">
        @for (a of atalhos; track a.dias) {
          <button type="button" [class.ativo]="atalho() === a.dias" [attr.aria-pressed]="atalho() === a.dias" (click)="usarAtalho(a.dias)">{{ a.rotulo }}</button>
        }
      </div>
      <label class="campo"><span>De</span><input type="date" [ngModel]="de()" (ngModelChange)="mudarData('de', $event)" [max]="hoje()" /></label>
      <label class="campo"><span>Até</span><input type="date" [ngModel]="ate()" (ngModelChange)="mudarData('ate', $event)" [max]="hoje()" /></label>
      <label class="campo"><span>Turno</span>
        <select [ngModel]="turno()" (ngModelChange)="turno.set(+$event); emitir()">
          <option [ngValue]="0">Todos</option>
          @for (t of turnos(); track t.id) { <option [ngValue]="t.id">{{ t.nome }} ({{ t.hora_inicio }}–{{ t.hora_fim }})</option> }
        </select></label>
      <label class="campo"><span>Modelo</span>
        <select [ngModel]="modelo()" (ngModelChange)="modelo.set(+$event); emitir()">
          <option [ngValue]="0">Todos</option>
          @for (m of modelos(); track m.id) { <option [ngValue]="m.id">{{ m.nome }}</option> }
        </select></label>
    </div>
  `,
  styles: `
    .filtros { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: flex-end; }
    .filtros .campo { min-width: 140px; flex: 1 1 140px; max-width: 220px; }
    .segmentos { display: inline-flex; border: 1px solid var(--linha-forte); border-radius: var(--radius-sm); overflow: hidden; }
    .segmentos button {
      background: var(--superficie); border: 0; padding: var(--space-2) var(--space-3); font: inherit; cursor: pointer; min-height: 40px;
      & + button { border-left: 1px solid var(--linha-forte); }
      &.ativo { background: var(--sinal); color: var(--on-sinal); }
    }
  `,
})
export class FiltroDsh implements OnInit {
  private readonly dsh = inject(DshService);
  readonly mudou = output<FiltroPainel>();

  protected readonly atalhos = ATALHOS;
  protected readonly hoje = computed(() => this.dsh.opcoes()?.hoje ?? '');
  protected readonly turnos = computed(() => this.dsh.opcoes()?.turnos ?? []);
  protected readonly modelos = computed(() => this.dsh.opcoes()?.modelos ?? []);
  protected readonly atalho = signal<number | null>(7);
  protected readonly de = signal('');
  protected readonly ate = signal('');
  protected readonly turno = signal(0);
  protected readonly modelo = signal(0);

  async ngOnInit(): Promise<void> {
    await this.dsh.carregarOpcoes();
    this.usarAtalho(7);
  }

  protected usarAtalho(dias: number): void {
    this.atalho.set(dias);
    this.ate.set(this.hoje());
    this.de.set(somarDias(this.hoje(), -(dias - 1)));
    this.emitir();
  }

  protected mudarData(campo: 'de' | 'ate', valor: string): void {
    if (!valor) return;
    this.atalho.set(null);
    (campo === 'de' ? this.de : this.ate).set(valor);
    if (this.de() > this.ate()) (campo === 'de' ? this.ate : this.de).set(valor);
    this.emitir();
  }

  protected emitir(): void {
    this.mudou.emit({ de: this.de(), ate: this.ate(), turno_id: this.turno() || null, modelo_id: this.modelo() || null });
  }
}
