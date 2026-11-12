import { formatDate } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { BarrasHorizontais, ColunasTempo, PontoGrafico } from '../../../shared/graficos';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import { Classificacao, Contagem, IndicadoresQld, ROTULO_CLASSIFICACAO } from '../qld.modelos';
import { QldService } from '../qld.service';

const PERIODOS = [
  { dias: 7, rotulo: '7 dias' },
  { dias: 30, rotulo: '30 dias' },
  { dias: 90, rotulo: '90 dias' },
  { dias: null, rotulo: 'Tudo' },
];

/** Primeiro dia (inclusive) de um período que termina hoje, no dia da fábrica. */
export function inicioDoPeriodo(dias: number, hoje = new Date()): string {
  const inicio = new Date(hoje.getTime() - (dias - 1) * 86_400_000);
  return formatDate(inicio, 'yyyy-MM-dd', 'en-US', FUSO_FABRICA);
}

/** Painel da qualidade: volume de ocorrências, pendências e onde os defeitos se concentram. */
@Component({
  selector: 'am-painel-qld',
  imports: [BarrasHorizontais, ColunasTempo],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Painel da qualidade</h1>
          <p class="legenda">Só ocorrências visíveis. Dias contados no horário da fábrica (Manaus).</p>
        </div>
        <div class="segmentos" role="group" aria-label="Período">
          @for (p of periodos; track p.rotulo) {
            <button type="button" [class.ativo]="periodo() === p.dias" [attr.aria-pressed]="periodo() === p.dias" (click)="mudarPeriodo(p.dias)">{{ p.rotulo }}</button>
          }
        </div>
      </div>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      @if (ind(); as i) {
        <div class="kpis">
          <div class="cartao kpi destaque">
            <span class="rotulo">Ocorrências</span>
            <span class="numero">{{ i.total_ocorrencias }}</span>
            <span class="legenda">{{ i.criticas }} crítica(s)</span>
          </div>
          <div class="cartao kpi" [class.alerta]="i.ocorrencias_abertas > 0">
            <span class="rotulo">Abertas</span>
            <span class="numero">{{ i.ocorrencias_abertas }}</span>
            <span class="legenda">{{ i.ocorrencias_em_analise }} em análise</span>
          </div>
          <div class="cartao kpi" [class.alerta]="i.produtos_reprovados > 0">
            <span class="rotulo">Notebooks reprovados</span>
            <span class="numero">{{ i.produtos_reprovados }}</span>
            <span class="legenda">retidos por defeito</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Estação crítica</span>
            <span class="numero texto">{{ i.estacao_critica ?? 'Nenhuma' }}</span>
            <span class="legenda">mais ocorrências no período</span>
          </div>
        </div>

        <div class="graficos">
          <section class="cartao">
            <am-barras-horizontais titulo="Ocorrências por tipo de defeito" subtitulo="Defeitos mais frequentes"
              [pontos]="pontos(i.por_tipo_defeito)" rotuloCategoria="Tipo de defeito" rotuloValor="Ocorrências" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Ocorrências por estação" [pontos]="pontos(i.por_estacao)"
              rotuloCategoria="Estação" rotuloValor="Ocorrências" />
          </section>
          <section class="cartao largo">
            <am-colunas-tempo titulo="Ocorrências por dia" subtitulo="Dia da fábrica (Manaus)" [pontos]="porDia()" rotuloValor="Ocorrências" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Ocorrências por máquina" subtitulo="Onde investigar causa de máquina"
              [pontos]="pontos(i.por_maquina)" rotuloCategoria="Máquina" rotuloValor="Ocorrências" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Ocorrências por classificação" [pontos]="porClassificacao()"
              rotuloCategoria="Classificação" rotuloValor="Ocorrências" />
          </section>
        </div>
      }
    </div>
  `,
  styles: `
    .segmentos { display: inline-flex; border: 1px solid var(--linha-forte); border-radius: var(--radius-sm); overflow: hidden; }
    .segmentos button {
      background: var(--superficie); border: 0; padding: var(--space-2) var(--space-3); font: inherit; cursor: pointer;
      & + button { border-left: 1px solid var(--linha-forte); }
      &.ativo { background: var(--sinal); color: var(--on-sinal); }
    }
    .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-4); }
    .kpi { display: grid; gap: var(--space-1); align-content: start; }
    .destaque { border-top: 4px solid var(--sinal); }
    .alerta { border-top: 4px solid var(--critico); }
    .numero { font-family: var(--font-display); font-size: 32px; line-height: 36px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .numero.texto { font-size: 22px; line-height: 36px; }
    .graficos { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-4); }
    .largo { grid-column: 1 / -1; }
    @media (max-width: 480px) { .graficos { grid-template-columns: 1fr; } }
  `,
})
export class PainelQld implements OnInit {
  private readonly qld = inject(QldService);
  protected readonly periodos = PERIODOS;
  // "Tudo" por padrão, como a tela antiga (os dados de demonstração são de set-out/2026).
  protected readonly periodo = signal<number | null>(null);
  protected readonly ind = signal<IndicadoresQld | null>(null);
  protected readonly erro = signal<string | null>(null);

  protected readonly porDia = computed<PontoGrafico[]>(() =>
    (this.ind()?.por_dia ?? []).map((d) => ({ rotulo: d.data.slice(8, 10) + '/' + d.data.slice(5, 7), valor: d.ocorrencias })),
  );
  protected readonly porClassificacao = computed<PontoGrafico[]>(() =>
    (this.ind()?.por_classificacao ?? []).map((c) => ({ rotulo: ROTULO_CLASSIFICACAO[c.rotulo as Classificacao] ?? c.rotulo, valor: c.ocorrencias })),
  );

  ngOnInit(): void {
    void this.carregar();
  }

  protected pontos(lista: Contagem[]): PontoGrafico[] {
    return lista.slice(0, 10).map((c) => ({ rotulo: c.rotulo, valor: c.ocorrencias }));
  }

  protected mudarPeriodo(dias: number | null): void {
    this.periodo.set(dias);
    void this.carregar();
  }

  private async carregar(): Promise<void> {
    const dias = this.periodo();
    try {
      this.erro.set(null);
      this.ind.set(await firstValueFrom(this.qld.indicadores(dias ? inicioDoPeriodo(dias) : null)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
