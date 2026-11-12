import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { BarrasHorizontais, ColunasTempo, PontoGrafico } from '../../../shared/graficos';
import { FUSO_FABRICA, duracao } from '../../manutencao/mnt.modelos';
import {
  Contagem,
  FiltroPainel,
  Painel,
  ROTULO_SEMAFORO,
  Semaforo,
  TOM_SEMAFORO,
  diaMes,
  numero,
  percentual,
} from '../dsh.modelos';
import { DshService } from '../dsh.service';
import { FiltroDsh } from './filtro';

/** Painel de indicadores (T02): seis indicadores com semáforo, máquinas paradas agora e os gráficos do período. */
@Component({
  selector: 'am-painel-dsh',
  imports: [DatePipe, Etiqueta, BarrasHorizontais, ColunasTempo, FiltroDsh],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Painel de indicadores</h1>
        <p class="legenda">Calculado na hora com os dados da Rastreabilidade (produção), da Qualidade (retrabalho e defeitos)
          e da Manutenção (paradas). Dias e turnos no horário da fábrica (Manaus).</p>
      </div>

      <am-filtro-dsh (mudou)="carregar($event)" />

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      @if (dados(); as d) {
        @if (d.paradas_em_andamento.length) {
          <section class="aviso erro paradas" role="status">
            <strong>{{ d.paradas_em_andamento.length }} máquina(s) parada(s) agora</strong>
            <ul>
              @for (p of d.paradas_em_andamento; track p.chamado_id) {
                <li><span class="codigo">{{ p.maquina }}</span> {{ p.nome }} · OS #{{ p.chamado_id }} ·
                  desde {{ p.desde | date: 'dd/MM HH:mm' : fuso }} ({{ duracao(p.minutos) }}) · {{ p.motivo }}</li>
              }
            </ul>
          </section>
        }

        <div class="kpis">
          <div class="cartao kpi">
            <span class="rotulo">Atendimento da meta</span>
            <span class="numero">{{ percentual(d.atendimento_meta.valor) }}</span>
            <span class="legenda">{{ numero(d.producao.realizada) }} de {{ d.producao.meta ? numero(d.producao.meta) : 'sem meta' }}</span>
            @if (d.atendimento_meta.semaforo; as s) { <am-etiqueta [texto]="rotuloSemaforo[s]" [tom]="tomSemaforo[s]" /> }
            @else { <am-etiqueta texto="Sem meta" tom="neutro" /> }
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Índice de defeitos</span>
            <span class="numero">{{ percentual(d.indice_defeitos.valor) }}</span>
            <span class="legenda">{{ numero(d.producao.reprovada) }} reprovado(s) na produção</span>
            @if (d.indice_defeitos.semaforo; as s) { <am-etiqueta [texto]="rotuloSemaforo[s]" [tom]="tomSemaforo[s]" /> }
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Índice de retrabalho</span>
            <span class="numero">{{ percentual(d.indice_retrabalho.valor) }}</span>
            <span class="legenda">{{ numero(d.indice_retrabalho.retrabalho) }} notebook(s) em reprocesso</span>
            @if (d.indice_retrabalho.semaforo; as s) { <am-etiqueta [texto]="rotuloSemaforo[s]" [tom]="tomSemaforo[s]" /> }
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Produtividade</span>
            <span class="numero">{{ d.produtividade.valor === null ? '—' : numero(d.produtividade.valor, 1) + ' un/h' }}</span>
            <span class="legenda">{{ duracao(d.produtividade.minutos_produtivos) }} produtivos de {{ duracao(d.produtividade.minutos_turno) }} de turno</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Tempo de parada</span>
            <span class="numero">{{ duracao(d.tempo_parada.minutos) }}</span>
            <span class="legenda">{{ d.tempo_parada.paradas }} parada(s){{ d.tempo_parada.em_andamento ? ', ' + d.tempo_parada.em_andamento + ' em andamento' : '' }}</span>
          </div>
          <div class="cartao kpi">
            <span class="rotulo">Perdas</span>
            <span class="numero">{{ numero(d.perdas.total) }} un.</span>
            <span class="legenda">{{ d.perdas.por_tipo.length ? principaisPerdas(d.perdas.por_tipo) : 'nenhuma no período' }}</span>
          </div>
        </div>

        <div class="graficos">
          <section class="cartao">
            <am-barras-horizontais titulo="Produção realizada × meta" subtitulo="Por modelo; o traço marca a meta"
              [pontos]="producaoMeta()" rotuloCategoria="Modelo" rotuloValor="Realizada" rotuloReferencia="Meta" [formatar]="formatarNumero" />
          </section>
          <section class="cartao">
            <am-colunas-tempo titulo="Produção por dia" subtitulo="Aprovados + reprovados na Rastreabilidade"
              [pontos]="producaoDia()" rotuloValor="Produzidos" [formatar]="formatarNumero" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Defeitos por estação" subtitulo="Ocorrências da Qualidade"
              [pontos]="pontos(d.graficos.defeitos_por_estacao)" rotuloCategoria="Estação" rotuloValor="Ocorrências" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Retrabalho por estação" subtitulo="Onde o defeito do reprocesso foi encontrado"
              [pontos]="pontos(d.graficos.retrabalho_por_estacao)" rotuloCategoria="Estação" rotuloValor="Notebooks" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Tempo de parada por turno" subtitulo="Chamados da Manutenção"
              [pontos]="paradaTurno()" rotuloCategoria="Turno" rotuloValor="Parada" [formatar]="formatarMin" />
          </section>
          <section class="cartao">
            <am-barras-horizontais titulo="Perdas por tipo" [pontos]="pontos(d.perdas.por_tipo)" rotuloCategoria="Tipo" rotuloValor="Unidades" />
          </section>
        </div>
      }
    </div>
  `,
  styles: `
    /* No máximo 3 colunas: 6 cartões viram 2 linhas de 3. */
    .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(max(200px, calc((100% - 2 * var(--space-4)) / 3)), 1fr)); gap: var(--space-4); }
    .kpi { display: grid; gap: var(--space-1); align-content: start; justify-items: start; }
    .numero { font-family: var(--font-display); font-size: 32px; line-height: 36px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .graficos { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(360px, 100%), 1fr)); gap: var(--space-4); }
    .paradas ul { margin: var(--space-1) 0 0; padding-left: var(--space-4); }
  `,
})
export class PainelDsh {
  private readonly dsh = inject(DshService);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly rotuloSemaforo: Record<Semaforo, string> = ROTULO_SEMAFORO;
  protected readonly tomSemaforo = TOM_SEMAFORO;
  protected readonly numero = numero;
  protected readonly percentual = percentual;
  protected readonly duracao = duracao;
  protected readonly formatarNumero = (v: number) => numero(v);
  protected readonly formatarMin = (v: number) => duracao(v);

  protected readonly dados = signal<Painel | null>(null);
  protected readonly erro = signal<string | null>(null);

  protected readonly producaoMeta = computed<PontoGrafico[]>(() =>
    (this.dados()?.graficos.producao_x_meta ?? []).map((l) => ({
      rotulo: l.modelo, valor: l.realizada, referencia: l.meta || undefined,
      detalhe: l.meta ? `${numero((l.realizada / l.meta) * 100, 1)}% da meta` : 'sem meta',
    })),
  );
  protected readonly producaoDia = computed<PontoGrafico[]>(() =>
    (this.dados()?.graficos.producao_por_dia ?? []).map((d) => ({
      rotulo: diaMes(d.data), valor: d.realizada, detalhe: d.meta ? `meta ${numero(d.meta)}` : 'sem meta',
    })),
  );
  protected readonly paradaTurno = computed<PontoGrafico[]>(() =>
    (this.dados()?.graficos.parada_por_turno ?? []).map((t) => ({ rotulo: t.rotulo, valor: t.minutos })),
  );

  protected pontos(lista: Contagem[]): PontoGrafico[] {
    return lista.slice(0, 10).map((c) => ({ rotulo: c.rotulo, valor: c.quantidade }));
  }

  protected principaisPerdas(lista: Contagem[]): string {
    return lista.slice(0, 2).map((p) => `${p.rotulo} (${numero(p.quantidade)})`).join(', ');
  }

  protected async carregar(f: FiltroPainel): Promise<void> {
    try {
      this.erro.set(null);
      this.dados.set(await firstValueFrom(this.dsh.painel(f)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
