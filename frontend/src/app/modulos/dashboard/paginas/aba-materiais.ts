import { Component, computed, inject } from '@angular/core';

import { Etiqueta } from '../../../shared/etiqueta';
import { BarrasHorizontais, PontoGrafico } from '../../../shared/graficos';
import { numero } from '../dsh.modelos';
import { EstadoPainel, Kpi } from './painel';

/** Aba Materiais: estoque e pedidos de material da Rastreabilidade, perdas lançadas no Dashboard. */
@Component({
  selector: 'am-aba-materiais',
  imports: [Kpi, Etiqueta, BarrasHorizontais],
  template: `
    @if (estado.dados(); as d) {
      <div class="cabecalho-aba">
        <h1 class="titulo-tela titulo-aba">Materiais</h1>
        <p class="legenda">Da Rastreabilidade: estoque de componentes e pedidos em aberto (agora) e baixas no período.
          Perdas lançadas no Dashboard.</p>
      </div>

      <section class="kpis" aria-label="Indicadores de materiais">
        <am-kpi rotulo="Produções com pendência" [valor]="numero(mt().producoes_com_pendencia)"
          [legenda]="mt().pendentes + ' pedido(s) pendente(s) · ' + mt().parciais + ' parcial(is)'"
          [tom]="mt().producoes_com_pendencia ? 'atencao' : null" />
        <am-kpi rotulo="Estoque crítico" [valor]="numero(mt().estoque_critico.length)"
          [legenda]="'componentes com até ' + mt().limite_critico + ' un.'"
          [etiqueta]="insuficientes() ? insuficientes() + ' insuficiente(s)' : null" [tom]="insuficientes() ? 'critico' : null" />
        <am-kpi rotulo="Baixas de material" [valor]="numero(mt().baixas)" [legenda]="numero(mt().unidades_baixadas) + ' unidades no período'" />
        <am-kpi rotulo="Perdas" [valor]="numero(d.perdas.total) + ' un.'" legenda="lançadas no período" />
      </section>

      <section class="cartao">
        <div class="cab"><div><h2 class="titulo-secao">Estoque crítico</h2>
          <p class="legenda">Componentes com até {{ mt().limite_critico }} unidades ou com menos do que os pedidos em aberto</p></div></div>
        @if (mt().estoque_critico.length) {
          <div class="tabela-rolagem">
            <table class="tabela">
              <thead><tr><th scope="col">Código</th><th scope="col">Componente</th><th scope="col" class="num">Em estoque</th>
                <th scope="col" class="num">Pedido em aberto</th><th scope="col">Cobertura do pedido</th><th scope="col">Situação</th></tr></thead>
              <tbody>
                @for (c of mt().estoque_critico; track c.sku) {
                  <tr>
                    <td class="codigo">{{ c.sku }}</td>
                    <td>{{ c.nome }}</td>
                    <td class="num"><strong>{{ numero(c.estoque) }}</strong></td>
                    <td class="num">{{ numero(c.pedido) }}</td>
                    <td>@if (c.pedido) {
                      <span class="cobertura"><span class="trilho"><span [class.falta]="c.insuficiente" [style.width.%]="cobertura(c.estoque, c.pedido)"></span></span>
                        <span class="legenda">{{ cobertura(c.estoque, c.pedido) }}%</span></span>
                    } @else { <span class="legenda">sem pedido</span> }</td>
                    <td><am-etiqueta [texto]="c.insuficiente ? 'Insuficiente' : 'Crítico'" [tom]="c.insuficiente ? 'critico' : 'atencao'" /></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <p class="legenda">Nenhum componente em estoque crítico.</p>
        }
      </section>

      <div class="duas">
        <section class="cartao">
          <am-barras-horizontais titulo="Pendências por componente" subtitulo="Produções esperando cada componente"
            [pontos]="pendencias()" rotuloCategoria="Componente" rotuloValor="Produções" />
          @if (insuficientes()) { <p class="chave-cor"><i></i>Vermelho = o estoque não cobre o que falta</p> }
        </section>
        <section class="cartao">
          <am-barras-horizontais titulo="Perdas por tipo" [subtitulo]="numero(d.perdas.total) + ' unidade(s) no período'"
            [pontos]="perdas()" rotuloCategoria="Tipo" rotuloValor="Unidades" />
        </section>
      </div>
    }
  `,
  styleUrl: './abas.scss',
  styles: `
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .cobertura { display: flex; align-items: center; gap: var(--space-2); min-width: 140px; }
    .trilho { flex: 1; height: 8px; background: var(--neutro-suave); border-radius: 4px; display: flex;
      span { height: 100%; border-radius: 4px; background: var(--ok); &.falta { background: var(--critico); } } }
  `,
})
export class AbaMateriais {
  protected readonly estado = inject(EstadoPainel);
  protected readonly numero = numero;

  protected readonly mt = computed(() => this.estado.dados()!.materiais);
  protected readonly insuficientes = computed(() => this.mt().estoque_critico.filter((c) => c.insuficiente).length);

  protected cobertura(estoque: number, pedido: number): number {
    return Math.min(100, Math.round((estoque / pedido) * 100));
  }

  protected readonly pendencias = computed<PontoGrafico[]>(() =>
    this.mt().pendencias_por_componente.slice(0, 10).map((p) => ({
      rotulo: p.sku, valor: p.producoes, tom: p.insuficiente ? 'critico' : undefined,
      detalhe: `${p.nome} · faltam ${numero(p.quantidade)} un.${p.insuficiente ? ' · estoque insuficiente' : ''}`,
    })),
  );

  protected readonly perdas = computed<PontoGrafico[]>(() =>
    (this.estado.dados()?.perdas.por_tipo ?? []).map((p) => ({ rotulo: p.rotulo, valor: p.quantidade })),
  );
}
