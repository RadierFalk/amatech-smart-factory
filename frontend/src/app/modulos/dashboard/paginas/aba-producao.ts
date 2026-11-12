import { Component, computed, inject } from '@angular/core';

import { BarrasHorizontais, PontoGrafico } from '../../../shared/graficos';
import { duracao } from '../../manutencao/mnt.modelos';
import { ROTULO_SEMAFORO, TOM_SEMAFORO, numero, percentual, somarDias } from '../dsh.modelos';
import { DshService } from '../dsh.service';
import { MatrizMeta, ProducaoMetaDia } from './graficos-dsh';
import { EstadoPainel, Kpi } from './painel';

/** Aba Produção: da Rastreabilidade (passagens por Aprovado/Reprovado, etapa atual e chegada na Expedição). */
@Component({
  selector: 'am-aba-producao',
  imports: [Kpi, BarrasHorizontais, ProducaoMetaDia, MatrizMeta],
  template: `
    @if (estado.dados(); as d) {
      <div class="cabecalho-aba">
        <h1 class="titulo-tela titulo-aba">Produção</h1>
        <p class="legenda">Da Rastreabilidade: notebooks que passaram por Aprovado ou Reprovado, etapa atual de cada produção
          e tempo até a expedição.</p>
      </div>

      <section class="kpis" aria-label="Indicadores da produção">
        <am-kpi rotulo="Produzidos" [valor]="numero(d.producao.realizada) + ' un.'" legenda="aprovados + reprovados" />
        <am-kpi rotulo="Atendimento da meta" [valor]="percentual(d.atendimento_meta.valor)"
          [legenda]="d.producao.meta ? 'meta ' + numero(d.producao.meta) : 'sem meta no período'"
          [etiqueta]="d.atendimento_meta.semaforo ? rotulo[d.atendimento_meta.semaforo] : 'Sem meta'"
          [tom]="d.atendimento_meta.semaforo ? tom[d.atendimento_meta.semaforo] : 'neutro'" />
        <am-kpi rotulo="Lead time médio" [valor]="duracao(d.lead_time.minutos)"
          [legenda]="d.lead_time.expedidos + ' expedido(s) · início → expedição'" />
        <am-kpi rotulo="Produtividade" [valor]="d.produtividade.valor === null ? '—' : numero(d.produtividade.valor, 1) + ' un/h'"
          [legenda]="duracao(d.produtividade.minutos_produtivos) + ' produtivos'" />
        <am-kpi rotulo="Em produção agora" [valor]="numero(d.em_producao.total)" legenda="ainda não expedidos" />
        <am-kpi rotulo="Aprovados" [valor]="numero(d.producao.aprovada)"
          [etiqueta]="d.producao.realizada ? percentual((d.producao.aprovada / d.producao.realizada) * 100) : null"
          tom="ok" legenda="dos produzidos" />
      </section>

      <section class="cartao">
        <am-producao-meta-dia [dias]="d.graficos.producao_por_dia" [parcial]="estado.incluiHoje()" [limites]="limites()" />
      </section>

      <div class="duas">
        <section class="cartao">
          <am-barras-horizontais titulo="Em produção agora, por etapa"
            [subtitulo]="numero(d.em_producao.total) + ' notebooks ainda não expedidos · a etapa com mais notebooks é o gargalo'"
            [pontos]="etapas()" rotuloCategoria="Etapa" rotuloValor="Notebooks" [formatar]="formatarNumero" />
          <p class="chave-cor"><i></i>Vermelho = fora do fluxo (Parado, Reprovado)</p>
        </section>
        <section class="cartao">
          <am-barras-horizontais titulo="Lead time por modelo" subtitulo="Tempo médio do início da produção até a expedição"
            [pontos]="leadTime()" rotuloCategoria="Modelo" rotuloValor="Lead time" rotuloReferencia="Média da fábrica"
            [formatar]="formatarMin" />
        </section>
      </div>

      <section class="cartao">
        <am-matriz-meta [linhas]="d.producao_por_turno" [dias]="dias()" [turnos]="turnos()" [parcial]="estado.incluiHoje()"
          [limites]="limites()" />
      </section>
    }
  `,
  styleUrl: './abas.scss',
})
export class AbaProducao {
  protected readonly estado = inject(EstadoPainel);
  private readonly dsh = inject(DshService);
  protected readonly numero = numero;
  protected readonly percentual = percentual;
  protected readonly duracao = duracao;
  protected readonly rotulo = ROTULO_SEMAFORO;
  protected readonly tom = TOM_SEMAFORO;
  protected readonly formatarNumero = (v: number) => numero(v);
  protected readonly formatarMin = (v: number) => duracao(Math.round(v));
  protected readonly limites = computed(() => this.dsh.opcoes()?.limites ?? []);

  /** Com o filtro de turno, a matriz mostra só esse turno. */
  protected readonly turnos = computed(() => {
    const todos = this.dsh.opcoes()?.turnos ?? [];
    const id = this.estado.filtro()?.turno_id;
    return id ? todos.filter((t) => t.id === id) : todos;
  });

  protected readonly dias = computed(() => {
    const f = this.estado.filtro();
    if (!f) return [];
    const lista: string[] = [];
    for (let d = f.de; d <= f.ate; d = somarDias(d, 1)) lista.push(d);
    return lista;
  });

  protected readonly etapas = computed<PontoGrafico[]>(() =>
    (this.estado.dados()?.em_producao.por_etapa ?? []).map((e) => ({
      rotulo: e.rotulo, valor: e.quantidade, tom: e.lateral ? 'critico' : undefined,
    })),
  );

  protected readonly leadTime = computed<PontoGrafico[]>(() => {
    const lt = this.estado.dados()?.lead_time;
    return (lt?.por_modelo ?? []).map((m) => ({
      rotulo: m.modelo, valor: m.minutos, referencia: lt?.minutos ?? undefined, detalhe: `${m.expedidos} expedido(s)`,
    }));
  });
}
