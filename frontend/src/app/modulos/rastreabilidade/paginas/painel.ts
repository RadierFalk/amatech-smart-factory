import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { BarrasHorizontais, ColunasTempo, PontoGrafico } from '../../../shared/graficos';
import { atualizarPeriodicamente } from '../../manutencao/atualizacao';
import { PainelRas as Painel } from '../ras.modelos';
import { RasService } from '../ras.service';

/** Painel da produção: onde estão os notebooks, ritmo dos últimos dias e alertas de material. */
@Component({
  selector: 'am-painel-ras',
  imports: [RouterLink, BarrasHorizontais, ColunasTempo],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Painel da produção</h1>
        <p class="legenda">Atualiza sozinho a cada 30 segundos. Dias no horário da fábrica (Manaus).</p>
      </div>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      @if (dados(); as d) {
        <div class="kpis">
          <div class="cartao kpi destaque"><span class="rotulo">Em produção</span><span class="numero">{{ d.kpis.em_producao }}</span>
            <span class="legenda">fora da expedição</span></div>
          <div class="cartao kpi"><span class="rotulo">Iniciadas hoje</span><span class="numero">{{ d.kpis.iniciadas_hoje }}</span>
            <span class="legenda">notebooks que entraram na linha</span></div>
          <div class="cartao kpi"><span class="rotulo">Aprovados</span><span class="numero">{{ d.kpis.aprovados }}</span>
            <span class="legenda">esperando embalagem</span></div>
          <div class="cartao kpi" [class.alerta]="d.kpis.reprovados > 0"><span class="rotulo">Reprovados</span>
            <span class="numero">{{ d.kpis.reprovados }}</span><span class="legenda">aguardando retrabalho</span></div>
          <div class="cartao kpi" [class.alerta]="d.kpis.solicitacoes_pendentes > 0"><span class="rotulo">Solicitações pendentes</span>
            <span class="numero">{{ d.kpis.solicitacoes_pendentes }}</span><span class="legenda">material ainda não entregue</span></div>
          <div class="cartao kpi" [class.alerta]="d.kpis.estoque_critico > 0"><span class="rotulo">Estoque crítico</span>
            <span class="numero">{{ d.kpis.estoque_critico }}</span><span class="legenda">componente(s) com até {{ d.limite_estoque_critico }} un.</span></div>
        </div>

        <div class="graficos">
          <section class="cartao">
            <am-barras-horizontais titulo="Notebooks por etapa" subtitulo="Onde cada notebook está agora"
              [pontos]="porEtapa()" rotuloCategoria="Etapa" rotuloValor="Notebooks" />
          </section>
          <section class="cartao">
            <am-colunas-tempo titulo="Produções iniciadas nos últimos 7 dias" [pontos]="porDia()" rotuloValor="Produções" />
          </section>
          <section class="cartao largo">
            <h2 class="titulo-secao">Componentes com estoque crítico</h2>
            @if (d.estoque_critico.length) {
              <div class="tabela-rolagem"><table class="tabela">
                <thead><tr><th scope="col">SKU</th><th scope="col">Componente</th><th scope="col" class="num">Estoque</th></tr></thead>
                <tbody>@for (c of d.estoque_critico; track c.id) {
                  <tr><td class="codigo">{{ c.sku }}</td><td>{{ c.nome }}</td><td class="num">{{ c.estoque }}</td></tr>
                }</tbody>
              </table></div>
              <p class="legenda"><a routerLink="/rastreabilidade/relatorios">Ver o relatório de estoque com as pendências</a></p>
            } @else {
              <p class="legenda">Nenhum componente abaixo do limite.</p>
            }
          </section>
        </div>
      }
    </div>
  `,
  styles: `
    .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(max(180px, calc((100% - 2 * var(--space-4)) / 3)), 1fr)); gap: var(--space-4); }
    .kpi { display: grid; gap: var(--space-1); align-content: start; }
    .destaque { border-top: 4px solid var(--sinal); }
    .alerta { border-top: 4px solid var(--critico); }
    .numero { font-family: var(--font-display); font-size: 32px; line-height: 36px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .graficos { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-4); }
    .largo { grid-column: 1 / -1; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    @media (max-width: 480px) { .graficos { grid-template-columns: 1fr; } }
  `,
})
export class PainelRas {
  private readonly ras = inject(RasService);
  protected readonly dados = signal<Painel | null>(null);
  protected readonly erro = signal<string | null>(null);

  protected readonly porEtapa = computed<PontoGrafico[]>(() =>
    (this.dados()?.por_etapa ?? []).filter((e) => e.quantidade > 0).map((e) => ({ rotulo: e.etapa, valor: e.quantidade })),
  );
  protected readonly porDia = computed<PontoGrafico[]>(() =>
    (this.dados()?.ultimos_dias ?? []).map((d) => ({ rotulo: d.data.slice(8, 10) + '/' + d.data.slice(5, 7), valor: d.quantidade })),
  );

  constructor() {
    // Carrega agora e de novo a cada 30 s enquanto a tela estiver aberta.
    atualizarPeriodicamente(() => void this.carregar());
  }

  private async carregar(): Promise<void> {
    try {
      this.dados.set(await firstValueFrom(this.ras.painel()));
      this.erro.set(null);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
