import { DatePipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';

import { BarrasHorizontais, ColunasTempo, PontoGrafico } from '../../../shared/graficos';
import { FUSO_FABRICA, duracao } from '../../manutencao/mnt.modelos';
import { diaMes, numero, percentual } from '../dsh.modelos';
import { EstadoPainel, Kpi } from './painel';

const SEM_LAUDO = 'Em diagnóstico / aguardando laudo';

/** Aba Manutenção: chamados do período, tempo de máquina parada e confiabilidade (fórmulas da Manutenção). */
@Component({
  selector: 'am-aba-manutencao',
  imports: [DatePipe, Kpi, BarrasHorizontais, ColunasTempo],
  template: `
    @if (estado.dados(); as d) {
      <div class="cabecalho-aba">
        <h1 class="titulo-tela titulo-aba">Manutenção</h1>
        <p class="legenda">Da Manutenção: chamados abertos no período, tempo de máquina parada e indicadores de confiabilidade
          sobre o tempo de turno. O filtro de modelo não se aplica: chamados não têm modelo.</p>
      </div>

      @for (p of d.paradas_em_andamento; track p.chamado_id) {
        <div class="aviso erro parada-agora paradas" role="status">
          <strong>Parada agora</strong>
          <span><span class="codigo">{{ p.maquina }}</span> {{ p.nome }} · setor {{ p.setor }} · OS #{{ p.chamado_id }} ·
            desde {{ p.desde | date: 'dd/MM HH:mm' : fuso }} ({{ duracao(p.minutos) }}) · {{ p.motivo }}</span>
        </div>
      }

      <section class="kpis" aria-label="Indicadores da manutenção">
        <am-kpi rotulo="Disponibilidade" [valor]="percentual(m().disponibilidade)" legenda="do tempo de turno" />
        <am-kpi rotulo="MTTR" [valor]="duracao(arred(m().mttr_minutos))" legenda="tempo médio de reparo" />
        <am-kpi rotulo="MTBF" [valor]="duracao(arred(m().mtbf_minutos))" legenda="tempo médio entre falhas" />
        <am-kpi rotulo="MTTA" [valor]="duracao(arred(m().mtta_minutos))" legenda="até o técnico assumir" />
        <am-kpi rotulo="Tempo parado" [valor]="duracao(d.tempo_parada.minutos)"
          [legenda]="d.tempo_parada.paradas + ' parada(s)'" [tom]="d.tempo_parada.em_andamento ? 'critico' : null"
          [etiqueta]="d.tempo_parada.em_andamento ? d.tempo_parada.em_andamento + ' em andamento' : null" />
        <am-kpi rotulo="Chamados" [valor]="numero(m().chamados)" legenda="não cancelados"
          [etiqueta]="m().chamados_ativos ? m().chamados_ativos + ' aberto(s)' : null" [tom]="m().chamados_ativos ? 'atencao' : null" />
      </section>

      <div class="duas">
        <section class="cartao">
          <am-barras-horizontais titulo="Tempo parado por setor" [subtitulo]="resumoSetor()" [pontos]="porSetor()"
            rotuloCategoria="Setor" rotuloValor="Tempo parado" [formatar]="formatarMin" />
        </section>
        <section class="cartao">
          <am-barras-horizontais titulo="Tempo parado por máquina" subtitulo="As máquinas com mais tempo parado"
            [pontos]="porMaquina()" rotuloCategoria="Máquina" rotuloValor="Tempo parado" [formatar]="formatarMin" />
          @if (temParadaAgora()) { <p class="chave-cor"><i></i>Vermelho = parada agora</p> }
        </section>
      </div>

      <div class="duas">
        <section class="cartao">
          <am-colunas-tempo titulo="Tempo parado por dia"
            [subtitulo]="'Pelo dia de abertura do chamado' + (estado.incluiHoje() ? ' · hoje é parcial (hachurado)' : '')"
            [pontos]="porDia()" rotuloValor="Tempo parado" [formatar]="formatarMin" />
        </section>
        <section class="cartao">
          <am-barras-horizontais titulo="Chamados por causa raiz" [subtitulo]="numero(m().chamados) + ' chamado(s) no período'"
            [pontos]="porCausa()" rotuloCategoria="Causa raiz" rotuloValor="Chamados" />
        </section>
      </div>
    }
  `,
  styleUrl: './abas.scss',
})
export class AbaManutencao {
  protected readonly estado = inject(EstadoPainel);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly numero = numero;
  protected readonly percentual = percentual;
  protected readonly duracao = duracao;
  protected readonly formatarMin = (v: number) => duracao(Math.round(v));

  protected readonly m = computed(() => this.estado.dados()!.manutencao);

  protected arred(v: number | null): number | null {
    return v === null ? null : Math.round(v);
  }

  protected readonly porSetor = computed<PontoGrafico[]>(() =>
    this.m().por_setor.map((s) => ({ rotulo: s.setor, valor: s.minutos, detalhe: `${s.paradas} parada(s)` })),
  );

  protected readonly resumoSetor = computed(() => {
    const lista = this.m().por_setor;
    const total = lista.reduce((s, x) => s + x.minutos, 0);
    if (!lista.length || !total) return 'Soma das paradas das máquinas de cada setor';
    return `Soma das paradas das máquinas de cada setor · ${lista[0].setor} concentra ${numero((lista[0].minutos / total) * 100, 0)}%`;
  });

  protected readonly porMaquina = computed<PontoGrafico[]>(() =>
    this.m().por_maquina.map((x) => ({
      rotulo: `${x.maquina} · ${x.setor}`, valor: x.minutos, tom: x.parada_agora ? 'critico' : undefined,
      detalhe: `${x.nome} · ${x.paradas} parada(s)${x.parada_agora ? ' · parada agora' : ''}`,
    })),
  );

  protected readonly temParadaAgora = computed(() => this.m().por_maquina.some((x) => x.parada_agora));

  protected readonly porDia = computed<PontoGrafico[]>(() => {
    const lista = this.m().por_dia;
    return lista.map((d, i) => ({
      rotulo: diaMes(d.data), valor: d.minutos, parcial: this.estado.incluiHoje() && i === lista.length - 1,
    }));
  });

  protected readonly porCausa = computed<PontoGrafico[]>(() =>
    this.m().por_causa.map((c) => ({ rotulo: c.rotulo, valor: c.quantidade, tom: c.rotulo === SEM_LAUDO ? 'neutro' : undefined })),
  );
}
