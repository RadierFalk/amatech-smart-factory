import { Component, Injectable, computed, inject, input, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta, Tom } from '../../../shared/etiqueta';
import { FiltroPainel, Painel } from '../dsh.modelos';
import { DshService } from '../dsh.service';
import { FiltroDsh } from './filtro';

/**
 * Dados do painel compartilhados pelas abas (Visão geral, Produção, Qualidade, Manutenção, Materiais).
 * Uma chamada só a /api/dsh/painel por filtro: trocar de aba não busca de novo.
 */
@Injectable()
export class EstadoPainel {
  readonly dados = signal<Painel | null>(null);
  readonly filtro = signal<FiltroPainel | null>(null);
  /** O período termina hoje: o último dia ainda está em curso. */
  readonly incluiHoje = computed(() => this.filtro()?.ate === this.dsh.opcoes()?.hoje);
  private readonly dsh = inject(DshService);
}

/** Painel (T02): filtro do período em cima e a aba escolhida embaixo. */
@Component({
  selector: 'am-painel-dsh',
  imports: [RouterOutlet, FiltroDsh],
  providers: [EstadoPainel],
  template: `
    <div class="pagina">
      <am-filtro-dsh (mudou)="carregar($event)" />
      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      @if (estado.dados()) { <router-outlet /> }
      @else if (!erro()) { <p class="legenda" role="status">Carregando os indicadores…</p> }
    </div>
  `,
})
export class PainelDsh {
  private readonly dsh = inject(DshService);
  protected readonly estado = inject(EstadoPainel);
  protected readonly erro = signal<string | null>(null);

  protected async carregar(f: FiltroPainel): Promise<void> {
    try {
      this.erro.set(null);
      const dados = await firstValueFrom(this.dsh.painel(f));
      this.estado.filtro.set(f);
      this.estado.dados.set(dados);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}

/** Indicador compacto: rótulo, número e uma legenda curta. Cabem seis numa linha. */
@Component({
  selector: 'am-kpi',
  imports: [Etiqueta],
  host: { class: 'kpi', '[class.ok]': "tom() === 'ok'", '[class.atencao]': "tom() === 'atencao'", '[class.critico]': "tom() === 'critico'" },
  template: `
    <span class="kpi-rot">{{ rotulo() }}</span>
    <span class="kpi-linha"><span class="kpi-val">{{ valor() }}</span>
      @if (etiqueta()) { <am-etiqueta [texto]="etiqueta()!" [tom]="tom() ?? 'neutro'" /> }</span>
    @if (legenda()) { <span class="kpi-leg" [title]="legenda()">{{ legenda() }}</span> }
  `,
  styles: `
    :host {
      background: var(--superficie); border: 1px solid var(--linha); border-top: 3px solid var(--sinal);
      border-radius: var(--radius-md); box-shadow: var(--sombra-cartao);
      padding: var(--space-2) var(--space-3); display: flex; flex-direction: column; gap: 2px; min-width: 0;
    }
    :host(.ok) { border-top-color: var(--ok); }
    :host(.atencao) { border-top-color: var(--atencao); }
    :host(.critico) { border-top-color: var(--critico); }
    .kpi-rot { font-size: 11px; line-height: 16px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
      color: var(--tinta-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .kpi-linha { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
    .kpi-val { font-family: var(--font-display); font-size: 24px; line-height: 30px; font-weight: 600;
      font-variant-numeric: tabular-nums; white-space: nowrap; }
    .kpi-leg { font-size: 12px; line-height: 16px; color: var(--tinta-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  `,
})
export class Kpi {
  readonly rotulo = input.required<string>();
  readonly valor = input.required<string>();
  readonly legenda = input('');
  /** Texto da etiqueta ao lado do número; a cor nunca vai sozinha. */
  readonly etiqueta = input<string | null>(null);
  readonly tom = input<Tom | null>(null);
}
