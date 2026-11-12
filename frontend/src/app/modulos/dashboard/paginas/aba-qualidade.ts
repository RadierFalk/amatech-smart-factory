import { DatePipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';

import { Etiqueta } from '../../../shared/etiqueta';
import { BarrasHorizontais, ColunasTempo, PontoGrafico } from '../../../shared/graficos';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import {
  Contagem,
  ROTULO_SEMAFORO,
  ROTULO_STATUS_OCORRENCIA,
  TOM_SEMAFORO,
  TOM_STATUS_OCORRENCIA,
  diaMes,
  numero,
  percentual,
} from '../dsh.modelos';
import { EstadoPainel, Kpi } from './painel';

/** Aba Qualidade: ocorrências da Qualidade no período; o índice de defeitos usa a produção da Rastreabilidade. */
@Component({
  selector: 'am-aba-qualidade',
  imports: [DatePipe, Kpi, Etiqueta, BarrasHorizontais, ColunasTempo],
  template: `
    @if (estado.dados(); as d) {
      <div class="cabecalho-aba">
        <h1 class="titulo-tela titulo-aba">Qualidade</h1>
        <p class="legenda">Da Qualidade: ocorrências registradas nas estações. O índice de defeitos é calculado sobre os
          {{ numero(d.producao.realizada) }} produzidos.</p>
      </div>

      <section class="kpis" aria-label="Indicadores da qualidade">
        <am-kpi rotulo="Ocorrências" [valor]="numero(q().ocorrencias)" legenda="no período" />
        <am-kpi rotulo="Índice de defeitos" [valor]="percentual(d.indice_defeitos.valor)"
          [legenda]="numero(d.producao.reprovada) + ' reprovado(s)'"
          [etiqueta]="d.indice_defeitos.semaforo ? rotulo[d.indice_defeitos.semaforo] : null"
          [tom]="d.indice_defeitos.semaforo ? tom[d.indice_defeitos.semaforo] : null" />
        <am-kpi rotulo="Abertas" [valor]="numero(q().abertas)" legenda="aguardando análise" />
        <am-kpi rotulo="Em análise" [valor]="numero(q().em_analise)" legenda="com responsável" />
        <am-kpi rotulo="Retrabalho" [valor]="percentual(d.indice_retrabalho.valor)"
          [legenda]="numero(d.indice_retrabalho.retrabalho) + ' em reprocesso'"
          [etiqueta]="d.indice_retrabalho.semaforo ? rotulo[d.indice_retrabalho.semaforo] : null"
          [tom]="d.indice_retrabalho.semaforo ? tom[d.indice_retrabalho.semaforo] : null" />
        <am-kpi rotulo="Críticas" [valor]="numero(q().criticas)" legenda="gravidade crítica"
          [etiqueta]="q().criticas_pendentes ? q().criticas_pendentes + ' sem resolução' : null"
          [tom]="q().criticas_pendentes ? 'critico' : null" />
      </section>

      <div class="duas">
        <section class="cartao">
          <am-barras-horizontais titulo="Defeitos por tipo" [subtitulo]="resumoTipos()" [pontos]="porTipo()"
            rotuloCategoria="Tipo de defeito" rotuloValor="Ocorrências" />
        </section>
        <section class="cartao">
          <am-barras-horizontais titulo="Ocorrências por estação" subtitulo="Onde o defeito foi encontrado"
            [pontos]="contagem(d.graficos.defeitos_por_estacao)" rotuloCategoria="Estação" rotuloValor="Ocorrências" />
        </section>
      </div>

      <div class="duas">
        <section class="cartao">
          <am-colunas-tempo titulo="Ocorrências por dia" [subtitulo]="estado.incluiHoje() ? 'Hoje é parcial (hachurado)' : ''"
            [pontos]="porDia()" rotuloValor="Ocorrências" />
        </section>
        <section class="cartao">
          <div class="cab"><div><h2 class="titulo-secao">Críticas recentes</h2>
            <p class="legenda">As 5 últimas de gravidade crítica no período</p></div></div>
          @if (q().criticas_recentes.length) {
            <div class="tabela-rolagem">
              <table class="tabela">
                <thead><tr><th scope="col">Nº</th><th scope="col">Quando</th><th scope="col">Defeito · série</th>
                  <th scope="col">Estação</th><th scope="col">Situação</th></tr></thead>
                <tbody>
                  @for (c of q().criticas_recentes; track c.id) {
                    <tr>
                      <td class="codigo">#{{ c.id }}</td>
                      <td>{{ c.ocorrida_em | date: 'dd/MM HH:mm' : fuso }}</td>
                      <td><strong>{{ c.defeito }}</strong><br /><span class="codigo legenda">{{ c.numero_serie }}</span> {{ c.modelo }}</td>
                      <td>{{ c.estacao }}</td>
                      <td><am-etiqueta [texto]="rotuloStatus[c.status]" [tom]="tomStatus[c.status]" /></td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <p class="legenda">Nenhuma ocorrência crítica no período.</p>
          }
        </section>
      </div>
    }
  `,
  styleUrl: './abas.scss',
})
export class AbaQualidade {
  protected readonly estado = inject(EstadoPainel);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly numero = numero;
  protected readonly percentual = percentual;
  protected readonly rotulo = ROTULO_SEMAFORO;
  protected readonly tom = TOM_SEMAFORO;
  protected readonly rotuloStatus = ROTULO_STATUS_OCORRENCIA;
  protected readonly tomStatus = TOM_STATUS_OCORRENCIA;

  protected readonly q = computed(() => this.estado.dados()!.qualidade);

  protected readonly porTipo = computed<PontoGrafico[]>(() => {
    const total = this.q().ocorrencias;
    return this.q().por_tipo.slice(0, 10).map((t) => ({
      rotulo: t.rotulo, valor: t.quantidade, detalhe: total ? `${numero((t.quantidade / total) * 100, 0)}% das ocorrências` : undefined,
    }));
  });

  protected readonly resumoTipos = computed(() => {
    const [a, b] = this.q().por_tipo;
    const total = this.q().ocorrencias;
    if (!a || !total) return 'Ocorrências no período';
    const soma = a.quantidade + (b?.quantidade ?? 0);
    return `Ocorrências no período · ${b ? `${a.rotulo} e ${b.rotulo} somam` : `${a.rotulo} é`} ${numero((soma / total) * 100, 0)}%`;
  });

  protected readonly porDia = computed<PontoGrafico[]>(() => {
    const lista = this.q().por_dia;
    return lista.map((d, i) => ({
      rotulo: diaMes(d.data), valor: d.quantidade, parcial: this.estado.incluiHoje() && i === lista.length - 1,
    }));
  });

  protected contagem(lista: Contagem[]): PontoGrafico[] {
    return lista.slice(0, 10).map((c) => ({ rotulo: c.rotulo, valor: c.quantidade }));
  }
}
