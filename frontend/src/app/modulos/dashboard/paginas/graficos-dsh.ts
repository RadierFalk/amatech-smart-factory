import { Component, computed, input, signal } from '@angular/core';

import {
  Limite,
  LinhaHistorico,
  ROTULO_SEMAFORO,
  Semaforo,
  Turno,
  diaMes,
  diaSemana,
  numero,
  semaforoMeta,
} from '../dsh.modelos';

export interface DiaProducao {
  data: string;
  realizada: number;
  meta: number;
}

/** Passo da grade arredondado para cima em 1, 2 ou 5 × 10^n (inteiro, para o rótulo não virar "2,5" arredondado). */
function passoRedondo(v: number): number {
  if (v <= 0) return 1;
  const base = 10 ** Math.floor(Math.log10(v));
  return Math.max(1, ([1, 2, 5, 10].find((m) => m * base >= v) ?? 10) * base);
}

/**
 * Produção realizada × meta por dia: colunas com a meta como traço neutro e, embaixo, o atendimento da meta
 * em linha própria (escala própria, nada de eixo duplo). Hoje, se estiver no período, sai hachurado.
 */
@Component({
  selector: 'am-producao-meta-dia',
  template: `
    <figure class="grafico">
      <div class="cabeca">
        <div>
          <figcaption class="titulo-secao">Produção realizada × meta</figcaption>
          <p class="legenda">Por dia da fábrica (Manaus){{ parcial() ? ' · hoje é parcial' : '' }}</p>
        </div>
        <p class="chaves legenda">
          <span><i class="amostra"></i>Realizada</span>
          <span><i class="amostra-meta"></i>Meta</span>
          @if (parcial()) { <span><i class="amostra parcial"></i>Parcial</span> }
        </p>
      </div>

      @if (tabela()) {
        <table class="tabela">
          <thead><tr><th scope="col">Dia</th><th scope="col">Realizada</th><th scope="col">Meta</th><th scope="col">Atendimento</th></tr></thead>
          <tbody>@for (c of colunas(); track c.data) {
            <tr><td>{{ c.rotulo }}{{ c.parcial ? ' (parcial)' : '' }}</td><td>{{ numero(c.realizada) }}</td>
              <td>{{ c.meta ? numero(c.meta) : 'sem meta' }}</td><td>{{ c.textoAtendimento }}</td></tr>
          }</tbody>
        </table>
      } @else {
        <div class="plano">
          <div class="eixo-y" aria-hidden="true">
            @for (g of grade(); track g.v) { <span [style.bottom.%]="g.pos">{{ numero(g.v) }}</span> }
          </div>
          <ul class="colunas" [style.background-size]="tamanhoGrade()">
            @for (c of colunas(); track c.data) {
              <li tabindex="0" [attr.aria-label]="c.dica">
                @if (c.parcial) { <span class="hoje" aria-hidden="true">Hoje</span> }
                <span class="coluna" [class.parcial]="c.parcial" [style.height.%]="c.altura"></span>
                @if (c.meta) { <span class="meta" [style.bottom.%]="c.alturaMeta" aria-hidden="true"></span> }
                <span class="dica" role="tooltip">{{ c.dica }}</span>
              </li>
            }
          </ul>
          <span></span>
          <div class="rotulos" aria-hidden="true">
            @for (c of colunas(); track c.data; let i = $index) {
              <span [class.hoje-rot]="c.parcial">@if (mostraRotulo(i)) { <b>{{ c.rotulo }}</b><br />{{ c.semana }} }</span>
            }
          </div>
        </div>

        @if (atendimento() && linha().pontos.length) {
          <div class="atendimento">
            <div class="cabeca">
              <h3 class="titulo-secao sub">Atendimento da meta por dia</h3>
              <p class="chaves legenda">
                <span><i class="ponto verde"></i>No alvo (≥ {{ linha().verde }}%)</span>
                <span><i class="ponto amarelo"></i>Atenção</span>
                <span><i class="ponto vermelho"></i>Fora do alvo (&lt; {{ linha().amarelo }}%)</span>
              </p>
            </div>
            <div class="plano">
              <div class="eixo-y" aria-hidden="true"><span [style.top.%]="linha().yAlvo" class="alvo">{{ linha().verde }}%</span></div>
              <div class="area-linha" role="img" [attr.aria-label]="linha().descricao">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                  <line x1="0" x2="100" [attr.y1]="linha().yAlvo" [attr.y2]="linha().yAlvo" class="alvo" vector-effect="non-scaling-stroke" />
                  @for (s of linha().segmentos; track $index) {
                    <line [attr.x1]="s.x1" [attr.y1]="s.y1" [attr.x2]="s.x2" [attr.y2]="s.y2" [class.tracejada]="s.parcial" vector-effect="non-scaling-stroke" />
                  }
                </svg>
                @for (p of linha().pontos; track p.x) {
                  <span class="marca" [class]="'marca ' + p.semaforo" [class.parcial]="p.parcial" [style.left.%]="p.x" [style.top.%]="p.y"></span>
                  @if (mostraValores()) {
                    <span class="valor" [class.abaixo]="p.y < 25" [class.critico]="p.semaforo === 'vermelho'" [style.left.%]="p.x" [style.top.%]="p.y">{{ p.texto }}</span>
                  }
                }
              </div>
            </div>
          </div>
        }
      }
      <button type="button" class="alternar" (click)="tabela.set(!tabela())">{{ tabela() ? 'Ver gráfico' : 'Ver como tabela' }}</button>
    </figure>
  `,
  styleUrl: './graficos-dsh.scss',
})
export class ProducaoMetaDia {
  readonly dias = input.required<DiaProducao[]>();
  /** O último dia ainda está em curso. */
  readonly parcial = input(false);
  /** Mostra a linha de atendimento da meta embaixo das colunas. */
  readonly atendimento = input(true);
  readonly limites = input<Limite[]>([]);

  protected readonly numero = numero;
  protected readonly tabela = signal(false);

  /** Grade com passo redondo (1, 2 ou 5 × 10^n) e o topo logo acima do maior valor: o eixo nunca mostra 3, 7, 10. */
  private readonly maior = computed(() => Math.max(1, ...this.dias().flatMap((d) => [d.realizada, d.meta])) * 1.05);
  private readonly passo = computed(() => passoRedondo(this.maior() / 4));
  private readonly faixas = computed(() => Math.max(1, Math.ceil(this.maior() / this.passo())));
  private readonly escala = computed(() => this.passo() * this.faixas());
  protected readonly grade = computed(() => Array.from({ length: this.faixas() + 1 }, (_, i) => ({
    v: this.passo() * i, pos: (100 / this.faixas()) * i,
  })));
  protected readonly tamanhoGrade = computed(() => `100% ${100 / this.faixas()}%`);
  protected readonly mostraValores = computed(() => this.dias().length <= 10);

  protected readonly colunas = computed(() => {
    const ultimo = this.dias().length - 1;
    return this.dias().map((d, i) => {
      const parcial = this.parcial() && i === ultimo;
      const pct = d.meta ? (d.realizada / d.meta) * 100 : null;
      const textoAtendimento = pct === null ? 'sem meta' : `${numero(pct, 1)}%`;
      return {
        ...d, parcial, rotulo: diaMes(d.data), semana: diaSemana(d.data), textoAtendimento,
        altura: (d.realizada / this.escala()) * 100,
        alturaMeta: (d.meta / this.escala()) * 100,
        dica: `${diaMes(d.data)} · ${numero(d.realizada)}${d.meta ? ` de ${numero(d.meta)} · ${textoAtendimento}` : ' · sem meta'}${parcial ? ' (parcial)' : ''}`,
      };
    });
  });

  protected mostraRotulo(i: number): boolean {
    const n = this.dias().length;
    const passo = n <= 14 ? 1 : Math.ceil(n / 10);
    return i % passo === 0 || i === n - 1;
  }

  /** Pontos em % da área (x no centro de cada coluna); o domínio sempre mostra o alvo. */
  protected readonly linha = computed(() => {
    const l = this.limites().find((x) => x.indicador === 'atendimento_meta');
    const verde = l?.limite_verde ?? 95;
    const amarelo = l?.limite_amarelo ?? 75;
    const n = this.dias().length;
    const ultimo = n - 1;
    const valores = this.dias().map((d, i) => ({ i, v: d.meta ? (d.realizada / d.meta) * 100 : null }));
    const existentes = valores.filter((x) => x.v !== null).map((x) => x.v!);
    const lo = Math.min(amarelo - 5, ...existentes.map((v) => v - 5));
    const hi = Math.max(verde + 10, ...existentes.map((v) => v + 8));
    const y = (v: number) => 8 + ((hi - v) / (hi - lo)) * 84;
    const pontos = valores.filter((x) => x.v !== null).map(({ i, v }) => ({
      x: ((i + 0.5) / n) * 100, y: y(v!), parcial: this.parcial() && i === ultimo,
      semaforo: semaforoMeta(v, this.limites()) as Semaforo, texto: `${numero(v!, 1)}%${this.parcial() && i === ultimo ? ' parcial' : ''}`,
    }));
    const segmentos = pontos.slice(1).map((p, k) => ({ x1: pontos[k].x, y1: pontos[k].y, x2: p.x, y2: p.y, parcial: p.parcial }));
    const descricao = `Atendimento da meta por dia (alvo ${verde}%): ` + pontos.map((p, k) =>
      `${diaMes(this.dias()[valores.filter((x) => x.v !== null)[k].i].data)} ${p.texto} (${ROTULO_SEMAFORO[p.semaforo]})`).join(', ');
    return { pontos, segmentos, verde, amarelo, yAlvo: y(verde), descricao };
  });
}

/** Matriz modelo × dia × turno com o atendimento da meta de cada célula (cor + texto + legenda). */
@Component({
  selector: 'am-matriz-meta',
  template: `
    <div class="cabeca">
      <div>
        <h2 class="titulo-secao">Matriz de atendimento da meta</h2>
        <p class="legenda">Realizado ÷ meta por modelo, dia e turno · passe o mouse numa célula para ver os números</p>
        <p class="chaves-matriz">
          <span class="cel-ok">No alvo</span><span class="cel-atencao">Atenção</span>
          <span class="cel-critico">Fora do alvo</span><span class="cel-neutro">— Sem produção ou sem meta</span>
        </p>
      </div>
    </div>
    @if (modelos().length) {
      <div class="tabela-rolagem">
        <table class="matriz">
          <caption class="so-leitor">Atendimento da meta por modelo, dia e turno</caption>
          <thead>
            <tr><th scope="col" rowspan="2" class="modelo">Modelo</th>
              @for (d of dias(); track d) { <th scope="colgroup" [attr.colspan]="turnos().length" [class.hoje]="parcial() && $last">{{ rotuloDia(d) }}</th> }
              <th scope="col" rowspan="2" class="total">Realizado</th></tr>
            <tr>@for (d of dias(); track d) { @for (t of turnos(); track t.id) { <th scope="col" class="turno">{{ abreviar(t.nome) }}</th> } }</tr>
          </thead>
          <tbody>
            @for (m of modelos(); track m.nome) {
              <tr><th scope="row" class="modelo">{{ m.nome }}</th>
                @for (c of m.celulas; track $index) {
                  <td tabindex="0" [class]="'cel-' + c.tom" [attr.aria-label]="c.dica"><span>{{ c.texto }}</span><span class="dica" role="tooltip">{{ c.dica }}</span></td>
                }
                <td class="total">{{ numero(m.total) }}</td></tr>
            }
          </tbody>
        </table>
      </div>
    } @else {
      <p class="legenda">Sem produção nem meta no período.</p>
    }
  `,
  styleUrl: './matriz-meta.scss',
})
export class MatrizMeta {
  readonly linhas = input.required<LinhaHistorico[]>();
  readonly dias = input.required<string[]>();
  readonly turnos = input.required<Turno[]>();
  readonly parcial = input(false);
  readonly limites = input<Limite[]>([]);

  protected readonly numero = numero;

  protected rotuloDia(d: string): string {
    return `${diaMes(d)} ${diaSemana(d)}`;
  }

  protected abreviar(turno: string): string {
    return turno.replace(/\s*turno$/i, '');
  }

  protected readonly modelos = computed(() => {
    const porChave = new Map(this.linhas().map((l) => [`${l.modelo}|${l.data}|${l.turno_id}`, l]));
    const nomes = [...new Set(this.linhas().map((l) => l.modelo))].sort();
    return nomes.map((nome) => ({
      nome,
      total: this.linhas().filter((l) => l.modelo === nome).reduce((s, l) => s + l.realizada, 0),
      celulas: this.dias().flatMap((d) => this.turnos().map((t) => {
        const l = porChave.get(`${nome}|${d}|${t.id}`);
        const base = `${nome}, ${diaMes(d)}, ${t.nome}`;
        if (!l || !l.meta) {
          return { texto: '—', tom: 'neutro', dica: l ? `${base}: ${numero(l.realizada)} produzidos, sem meta` : `${base}: sem produção` };
        }
        const pct = (l.realizada / l.meta) * 100;
        const s = semaforoMeta(pct, this.limites())!;
        return {
          // Truncado: 94,7% vira "94%", nunca "95%" pintado de Atenção.
          texto: `${Math.floor(pct)}%`,
          tom: s === 'verde' ? 'ok' : s === 'amarelo' ? 'atencao' : 'critico',
          dica: `${base}: ${numero(l.realizada)} de ${numero(l.meta)} (${numero(pct, 1)}% · ${ROTULO_SEMAFORO[s]})`,
        };
      })),
    }));
  });
}
