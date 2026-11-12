import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { BarrasHorizontais, ColunasTempo, PontoGrafico } from '../../../shared/graficos';
import { Graficos, Indicadores, duracao } from '../mnt.modelos';
import { MntService } from '../mnt.service';

const PERIODOS = [
  { dias: 7, rotulo: '7 dias' },
  { dias: 30, rotulo: '30 dias' },
  { dias: 90, rotulo: '90 dias' },
  { dias: null, rotulo: 'Tudo' },
];

/** Painel de gestão: disponibilidade, MTTR, MTTA, MTBF, downtime e onde ele se concentra. */
@Component({
  selector: 'am-indicadores-mnt',
  imports: [BarrasHorizontais, ColunasTempo],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Indicadores de manutenção</h1>
          <p class="legenda">Disponibilidade sobre {{ ind()?.total_maquinas ?? 0 }} máquinas × 600 min programados por turno.</p>
        </div>
        <!-- Filtros numa linha só, acima dos gráficos -->
        <div class="filtros">
          <div class="segmentos" role="group" aria-label="Período">
            @for (p of periodos; track p.rotulo) {
              <button type="button" [class.ativo]="periodo() === p.dias" [attr.aria-pressed]="periodo() === p.dias" (click)="mudarPeriodo(p.dias)">{{ p.rotulo }}</button>
            }
          </div>
          <label class="campo"><span class="so-leitor">Setor</span>
            <select (change)="mudarSetor($any($event.target).value)">
              <option value="">Todos os setores</option>
              @for (s of setores(); track s) { <option [value]="s">{{ s }}</option> }
            </select>
          </label>
        </div>
      </div>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      @if (ind(); as i) {
        <div class="kpis">
          <div class="cartao kpi destaque">
            <span class="rotulo">Disponibilidade</span>
            <span class="numero">{{ i.disponibilidade_pct.toLocaleString('pt-BR') }}%</span>
            <span class="legenda">{{ duracao(i.downtime_total_minutos) }} de máquina parada</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">MTTR</span>
            <span class="numero">{{ duracao(arred(i.mttr_minutos)) }}</span>
            <span class="legenda">tempo médio de reparo</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">MTTA</span>
            <span class="numero">{{ duracao(arred(i.mtta_minutos)) }}</span>
            <span class="legenda">tempo médio até o técnico assumir</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">MTBF</span>
            <span class="numero">{{ duracao(arred(i.mtbf_minutos)) }}</span>
            <span class="legenda">tempo médio entre falhas</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Chamados</span>
            <span class="numero">{{ i.total_chamados }}</span>
            <span class="legenda">{{ i.chamados_abertos }} abertos · {{ i.chamados_em_andamento }} em andamento · {{ i.chamados_concluidos }} concluídos</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Preventiva / corretiva</span>
            <span class="numero">{{ i.preventivas }} / {{ i.corretivas }}</span>
            <span class="legenda">mais preventivas tende a reduzir o downtime</span>
          </div>
        </div>
      }

      @if (graf(); as g) {
        <div class="graficos">
          <section class="cartao">
            <am-barras-horizontais titulo="Downtime por máquina" subtitulo="Onde a linha mais parou"
              [pontos]="porMaquina()" rotuloCategoria="Máquina" rotuloValor="Downtime" [formatar]="formatarMin" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Chamados por causa raiz" subtitulo="Causas mais frequentes"
              [pontos]="porCausa()" rotuloCategoria="Causa raiz" rotuloValor="Chamados" />
          </section>
          <section class="cartao largo">
            <am-colunas-tempo titulo="Downtime por dia" subtitulo="Dia da fábrica (Manaus)"
              [pontos]="porDia()" rotuloValor="Downtime" [formatar]="formatarMin" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Downtime por setor" [pontos]="porSetor()" rotuloCategoria="Setor"
              rotuloValor="Downtime" [formatar]="formatarMin" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Peças mais consumidas" [pontos]="pecas()" rotuloCategoria="Peça" rotuloValor="Quantidade" />
          </section>
        </div>
      }
    </div>
  `,
  styles: `
    .filtros { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
    .segmentos { display: inline-flex; border: 1px solid var(--linha-forte); border-radius: var(--radius-sm); overflow: hidden; }
    .segmentos button {
      background: var(--superficie); border: 0; padding: var(--space-2) var(--space-3); font: inherit; cursor: pointer;
      & + button { border-left: 1px solid var(--linha-forte); }
      &.ativo { background: var(--sinal); color: var(--on-sinal); }
    }
    /* No máximo 3 colunas: 6 cartões viram 2 linhas de 3, sem cartão órfão. */
    .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(max(200px, calc((100% - 2 * var(--space-4)) / 3)), 1fr)); gap: var(--space-4); }
    .kpi { display: grid; gap: var(--space-1); align-content: start; }
    .destaque { border-top: 4px solid var(--sinal); }
    .numero { font-family: var(--font-display); font-size: 32px; line-height: 36px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .graficos { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-4); }
    .largo { grid-column: 1 / -1; }
    @media (max-width: 480px) { .graficos { grid-template-columns: 1fr; } }
  `,
})
export class IndicadoresMnt implements OnInit {
  private readonly mnt = inject(MntService);
  protected readonly periodos = PERIODOS;
  protected readonly duracao = duracao;
  protected readonly formatarMin = (v: number) => duracao(v);
  protected readonly arred = Math.round;

  protected readonly periodo = signal<number | null>(30);
  protected readonly setor = signal('');
  protected readonly ind = signal<Indicadores | null>(null);
  protected readonly graf = signal<Graficos | null>(null);
  protected readonly erro = signal<string | null>(null);
  protected readonly setores = computed(() => this.mnt.opcoes()?.setores ?? []);

  protected readonly porMaquina = computed<PontoGrafico[]>(() =>
    (this.graf()?.downtime_por_maquina ?? [])
      .filter((m) => m.chamados > 0)
      .slice(0, 10)
      .map((m) => ({ rotulo: m.codigo_tag, valor: m.downtime_minutos, detalhe: `${m.nome} · ${plural(m.chamados, 'chamado')}` })),
  );
  protected readonly porCausa = computed<PontoGrafico[]>(() =>
    (this.graf()?.chamados_por_causa_raiz ?? [])
      .slice(0, 8)
      .map((c) => ({ rotulo: c.causa_raiz, valor: c.chamados, detalhe: `${duracao(c.downtime_minutos)} de downtime` })),
  );
  protected readonly porDia = computed<PontoGrafico[]>(() =>
    (this.graf()?.evolucao_diaria ?? []).map((d) => ({
      rotulo: d.data.slice(8, 10) + '/' + d.data.slice(5, 7),
      valor: d.downtime_minutos,
      detalhe: plural(d.chamados, 'chamado'),
    })),
  );
  protected readonly porSetor = computed<PontoGrafico[]>(() =>
    (this.graf()?.downtime_por_setor ?? [])
      .filter((s) => s.chamados > 0)
      .map((s) => ({ rotulo: s.setor, valor: s.downtime_minutos, detalhe: plural(s.chamados, 'chamado') })),
  );
  protected readonly pecas = computed<PontoGrafico[]>(() =>
    (this.graf()?.pecas_consumidas ?? []).slice(0, 8).map((p) => ({ rotulo: p.codigo_peca, valor: p.quantidade, detalhe: p.nome })),
  );

  ngOnInit(): void {
    void this.carregar();
  }

  protected mudarPeriodo(dias: number | null): void {
    this.periodo.set(dias);
    void this.carregar();
  }

  protected mudarSetor(setor: string): void {
    this.setor.set(setor);
    void this.carregar();
  }

  private async carregar(): Promise<void> {
    const filtro = { periodo_dias: this.periodo(), setor: this.setor() || null };
    try {
      this.erro.set(null);
      const [ind, graf] = await Promise.all([
        firstValueFrom(this.mnt.indicadores(filtro)),
        firstValueFrom(this.mnt.graficos(filtro)),
      ]);
      this.ind.set(ind);
      this.graf.set(graf);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}

function plural(n: number, palavra: string): string {
  return `${n} ${palavra}${n === 1 ? '' : 's'}`;
}
