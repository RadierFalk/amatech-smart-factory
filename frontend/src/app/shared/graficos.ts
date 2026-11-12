import { Component, computed, input, signal } from '@angular/core';

/**
 * Gráficos simples em HTML/CSS, sem biblioteca, para uma série (cor `--grafico-1`).
 * Regras (skill de dataviz): barras finas com ponta arredondada no valor, um eixo só,
 * rótulo de valor direto, dica no hover/foco (teclado incluído) e versão em tabela.
 */
export interface PontoGrafico {
  rotulo: string;
  valor: number;
  /** Texto da dica (ex.: "3 chamados · 2 h 10 min"). */
  detalhe?: string;
  /** Valor de referência (ex.: meta), desenhado como um traço em tinta neutra sobre o trilho. */
  referencia?: number;
}

/** Ranking horizontal: maior valor no topo. */
@Component({
  selector: 'am-barras-horizontais',
  template: `
    <figure class="grafico">
      <figcaption class="titulo-secao">{{ titulo() }}</figcaption>
      @if (subtitulo()) { <p class="legenda">{{ subtitulo() }}</p> }
      @if (tabela()) {
        <table class="tabela">
          <thead><tr><th scope="col">{{ rotuloCategoria() }}</th><th scope="col">{{ rotuloValor() }}</th>
            @if (rotuloReferencia()) { <th scope="col">{{ rotuloReferencia() }}</th> }</tr></thead>
          <tbody>@for (p of pontos(); track p.rotulo) {
            <tr><td>{{ p.rotulo }}</td><td>{{ formatar()(p.valor) }}</td>
              @if (rotuloReferencia()) { <td>{{ p.referencia === undefined ? '—' : formatar()(p.referencia) }}</td> }</tr>
          }</tbody>
        </table>
      } @else if (pontos().length) {
        <ul class="barras">
          @for (p of pontos(); track p.rotulo) {
            <li tabindex="0" [attr.aria-label]="p.rotulo + ': ' + formatar()(p.valor) + textoReferencia(p) + (p.detalhe ? ' · ' + p.detalhe : '')">
              <span class="rot">{{ p.rotulo }}</span>
              <span class="trilho"><span class="barra" [style.width.%]="largura(p.valor)"></span>
                @if (p.referencia !== undefined) { <span class="ref" [style.left.%]="posicao(p.referencia)" aria-hidden="true"></span> }</span>
              <span class="val">{{ formatar()(p.valor) }}</span>
              @if (p.detalhe || p.referencia !== undefined) {
                <span class="dica" role="tooltip">{{ p.rotulo }}<br />{{ formatar()(p.valor) }}{{ textoReferencia(p) }}{{ p.detalhe ? ' · ' + p.detalhe : '' }}</span>
              }
            </li>
          }
        </ul>
        @if (rotuloReferencia()) {
          <p class="legenda-grafico"><span class="amostra-barra"></span> {{ rotuloValor() }} <span class="amostra-ref"></span> {{ rotuloReferencia() }}</p>
        }
      } @else {
        <p class="legenda">Sem dados no período.</p>
      }
      <button type="button" class="alternar" (click)="tabela.set(!tabela())">{{ tabela() ? 'Ver gráfico' : 'Ver como tabela' }}</button>
    </figure>
  `,
  styleUrl: './graficos.scss',
})
export class BarrasHorizontais {
  readonly titulo = input.required<string>();
  readonly subtitulo = input('');
  readonly pontos = input.required<PontoGrafico[]>();
  readonly rotuloCategoria = input('Categoria');
  readonly rotuloValor = input('Valor');
  readonly formatar = input<(v: number) => string>((v) => String(v));
  /** Nome da marca de referência (ex.: "Meta"). Vazio: o gráfico não tem referência. */
  readonly rotuloReferencia = input('');

  protected readonly tabela = signal(false);
  private readonly maximo = computed(() => Math.max(1, ...this.pontos().flatMap((p) => [p.valor, p.referencia ?? 0])));

  protected largura(valor: number): number {
    // Valor > 0 sempre aparece (mínimo de 1%), para não sumir ao lado de um valor muito maior.
    return valor > 0 ? Math.max(1, (valor / this.maximo()) * 100) : 0;
  }

  protected posicao(referencia: number): number {
    return Math.min(100, (referencia / this.maximo()) * 100);
  }

  protected textoReferencia(p: PontoGrafico): string {
    return p.referencia === undefined ? '' : ` de ${this.formatar()(p.referencia)} (${this.rotuloReferencia() || 'referência'})`;
  }
}

/** Colunas verticais no tempo (ex.: downtime por dia). Eixo Y implícito: o maior valor vai escrito. */
@Component({
  selector: 'am-colunas-tempo',
  template: `
    <figure class="grafico">
      <figcaption class="titulo-secao">{{ titulo() }}</figcaption>
      @if (subtitulo()) { <p class="legenda">{{ subtitulo() }}</p> }
      @if (tabela()) {
        <table class="tabela">
          <thead><tr><th scope="col">{{ rotuloCategoria() }}</th><th scope="col">{{ rotuloValor() }}</th></tr></thead>
          <tbody>@for (p of pontos(); track p.rotulo) { <tr><td>{{ p.rotulo }}</td><td>{{ formatar()(p.valor) }}</td></tr> }</tbody>
        </table>
      } @else if (pontos().length) {
        <div class="area">
          <span class="max legenda">{{ formatar()(maximo()) }}</span>
          <ul class="colunas">
            @for (p of pontos(); track p.rotulo) {
              <li tabindex="0" [attr.aria-label]="p.rotulo + ': ' + formatar()(p.valor) + (p.detalhe ? ' · ' + p.detalhe : '')">
                <span class="coluna" [style.height.%]="altura(p.valor)"></span>
                <span class="dica" role="tooltip">{{ p.rotulo }}<br />{{ formatar()(p.valor) }}{{ p.detalhe ? ' · ' + p.detalhe : '' }}</span>
              </li>
            }
          </ul>
          <div class="eixo legenda"><span>{{ pontos()[0].rotulo }}</span>@if (pontos().length > 1) { <span>{{ pontos()[pontos().length - 1].rotulo }}</span> }</div>
        </div>
      } @else {
        <p class="legenda">Sem dados no período.</p>
      }
      <button type="button" class="alternar" (click)="tabela.set(!tabela())">{{ tabela() ? 'Ver gráfico' : 'Ver como tabela' }}</button>
    </figure>
  `,
  styleUrl: './graficos.scss',
})
export class ColunasTempo {
  readonly titulo = input.required<string>();
  readonly subtitulo = input('');
  readonly pontos = input.required<PontoGrafico[]>();
  readonly rotuloCategoria = input('Data');
  readonly rotuloValor = input('Valor');
  readonly formatar = input<(v: number) => string>((v) => String(v));

  protected readonly tabela = signal(false);
  protected readonly maximo = computed(() => Math.max(1, ...this.pontos().map((p) => p.valor)));

  protected altura(valor: number): number {
    return valor > 0 ? Math.max(2, (valor / this.maximo()) * 100) : 0;
  }
}
