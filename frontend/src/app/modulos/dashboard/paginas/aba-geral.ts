import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Etiqueta, Tom } from '../../../shared/etiqueta';
import { duracao } from '../../manutencao/mnt.modelos';
import { ROTULO_SEMAFORO, TOM_SEMAFORO, diaMes, numero, percentual } from '../dsh.modelos';
import { DshService } from '../dsh.service';
import { ProducaoMetaDia } from './graficos-dsh';
import { EstadoPainel, Kpi } from './painel';

interface Alerta {
  texto: string;
  detalhe: string;
  tom: Tom;
  aba: string;
}

/** Visão geral: o mais importante de cada setor, com atalho para a aba de cada um. */
@Component({
  selector: 'am-aba-geral',
  imports: [RouterLink, Kpi, Etiqueta, ProducaoMetaDia],
  template: `
    @if (estado.dados(); as d) {
      <div class="cabecalho-aba">
        <h1 class="titulo-tela titulo-aba">Visão geral da fábrica</h1>
        <p class="legenda">Os números principais de cada setor no período. Clique num setor para ver os detalhes.</p>
      </div>

      <section class="kpis" aria-label="Indicadores principais">
        <am-kpi rotulo="Produzidos" [valor]="numero(d.producao.realizada) + ' un.'"
          [legenda]="d.producao.meta ? 'meta ' + numero(d.producao.meta) : 'sem meta no período'" />
        <am-kpi rotulo="Atendimento da meta" [valor]="percentual(d.atendimento_meta.valor)" legenda="realizado ÷ meta"
          [etiqueta]="d.atendimento_meta.semaforo ? rotulo[d.atendimento_meta.semaforo] : 'Sem meta'"
          [tom]="d.atendimento_meta.semaforo ? tom[d.atendimento_meta.semaforo] : 'neutro'" />
        <am-kpi rotulo="Lead time médio" [valor]="duracao(d.lead_time.minutos)" legenda="início → expedição" />
        <am-kpi rotulo="Índice de defeitos" [valor]="percentual(d.indice_defeitos.valor)"
          [legenda]="numero(d.producao.reprovada) + ' reprovado(s)'"
          [etiqueta]="d.indice_defeitos.semaforo ? rotulo[d.indice_defeitos.semaforo] : null"
          [tom]="d.indice_defeitos.semaforo ? tom[d.indice_defeitos.semaforo] : null" />
        <am-kpi rotulo="Disponibilidade" [valor]="percentual(d.manutencao.disponibilidade)" legenda="das máquinas no turno"
          [etiqueta]="d.paradas_em_andamento.length ? d.paradas_em_andamento.length + ' parada(s) agora' : null"
          [tom]="d.paradas_em_andamento.length ? 'critico' : null" />
        <am-kpi rotulo="Pendências de material" [valor]="numero(d.materiais.producoes_com_pendencia)" legenda="produções esperando material"
          [etiqueta]="insuficientes() ? insuficientes() + ' insuficiente(s)' : null" [tom]="insuficientes() ? 'critico' : null" />
      </section>

      <section class="setores" aria-label="Resumo por setor">
        <article class="cartao setor">
          <div class="cab"><h2 class="titulo-secao"><span class="selo-setor ras">RAS</span> Produção</h2>
            <a class="ver" routerLink="producao">Ver produção →</a></div>
          <dl class="mini">
            <div><dt>Produzidos</dt><dd>{{ numero(d.producao.realizada) }}</dd></div>
            <div><dt>Meta</dt><dd>{{ percentual(d.atendimento_meta.valor) }}</dd></div>
            <div><dt>Lead time</dt><dd>{{ duracao(d.lead_time.minutos) }}</dd></div>
          </dl>
          <div class="minibarras" role="img" [attr.aria-label]="descricaoDias()">
            @for (b of miniDias(); track b.data) {
              <span [class.parcial]="b.parcial" [style.height.%]="b.altura" [title]="b.titulo"></span>
            }
          </div>
          <p class="legenda">Produção por dia{{ estado.incluiHoje() ? ' · hoje é parcial' : '' }}</p>
        </article>

        <article class="cartao setor">
          <div class="cab"><h2 class="titulo-secao"><span class="selo-setor qld">QLD</span> Qualidade</h2>
            <a class="ver" routerLink="qualidade">Ver qualidade →</a></div>
          <dl class="mini">
            <div><dt>Defeitos</dt><dd>{{ percentual(d.indice_defeitos.valor) }}</dd></div>
            <div><dt>Retrabalho</dt><dd>{{ percentual(d.indice_retrabalho.valor) }}</dd></div>
            <div><dt>Abertas</dt><dd>{{ numero(d.qualidade.abertas) }}</dd></div>
          </dl>
          <p class="legenda">Defeitos mais comuns</p>
          @if (d.qualidade.por_tipo.length) {
            <ul class="lista">
              @for (t of d.qualidade.por_tipo.slice(0, 3); track t.rotulo) { <li><span>{{ t.rotulo }}</span><strong>{{ numero(t.quantidade) }}</strong></li> }
            </ul>
          } @else { <p class="legenda">Nenhuma ocorrência no período.</p> }
        </article>

        <article class="cartao setor">
          <div class="cab"><h2 class="titulo-secao"><span class="selo-setor mnt">MNT</span> Manutenção</h2>
            <a class="ver" routerLink="manutencao">Ver manutenção →</a></div>
          <dl class="mini">
            <div><dt>Disponib.</dt><dd>{{ percentual(d.manutencao.disponibilidade) }}</dd></div>
            <div><dt>MTTR</dt><dd>{{ duracao(arred(d.manutencao.mttr_minutos)) }}</dd></div>
            <div><dt>MTBF</dt><dd>{{ duracao(arred(d.manutencao.mtbf_minutos)) }}</dd></div>
          </dl>
          @if (d.paradas_em_andamento.length) {
            <ul class="lista">
              @for (p of d.paradas_em_andamento.slice(0, 3); track p.chamado_id) {
                <li><span><span class="codigo">{{ p.maquina }}</span> OS #{{ p.chamado_id }}</span>
                  <am-etiqueta [texto]="'Parada · ' + duracao(p.minutos)" tom="critico" /></li>
              }
            </ul>
          } @else { <p class="legenda">Nenhuma máquina parada agora · {{ duracao(d.tempo_parada.minutos) }} parado no período.</p> }
        </article>

        <article class="cartao setor">
          <div class="cab"><h2 class="titulo-secao"><span class="selo-setor ras">RAS</span> Materiais</h2>
            <a class="ver" routerLink="materiais">Ver materiais →</a></div>
          <dl class="mini">
            <div><dt>Pendentes</dt><dd>{{ numero(d.materiais.producoes_com_pendencia) }}</dd></div>
            <div><dt>Baixas</dt><dd>{{ numero(d.materiais.baixas) }}</dd></div>
            <div><dt>Perdas</dt><dd>{{ numero(d.perdas.total) }} un.</dd></div>
          </dl>
          @if (d.materiais.estoque_critico.length) {
            <ul class="lista">
              @for (c of d.materiais.estoque_critico.slice(0, 3); track c.sku) {
                <li><span><span class="codigo">{{ c.sku }}</span> {{ c.nome }}</span>
                  <am-etiqueta [texto]="(c.insuficiente ? 'Insuficiente' : 'Crítico') + ' · ' + numero(c.estoque) + ' un.'"
                    [tom]="c.insuficiente ? 'critico' : 'atencao'" /></li>
              }
            </ul>
          } @else { <p class="legenda">Nenhum componente em estoque crítico.</p> }
        </article>
      </section>

      <div class="fundo">
        <section class="cartao grafico">
          <am-producao-meta-dia [dias]="d.graficos.producao_por_dia" [parcial]="estado.incluiHoje()" [atendimento]="false"
            [limites]="limites()" />
        </section>
        <section class="cartao alertas" aria-label="Alertas agora">
          <h2 class="titulo-secao">Alertas agora</h2>
          @for (a of alertas(); track a.texto) {
            <a class="alerta" [class]="'alerta ' + a.tom" [routerLink]="a.aba">
              <am-etiqueta [texto]="a.tom === 'critico' ? 'Crítico' : 'Atenção'" [tom]="a.tom" />
              <span><strong>{{ a.texto }}</strong><br /><span class="legenda">{{ a.detalhe }}</span></span>
            </a>
          } @empty {
            <p class="legenda">Nenhum alerta agora.</p>
          }
        </section>
      </div>
    }
  `,
  styleUrl: './abas.scss',
  styles: `
    .setores { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); gap: var(--space-4); }
    .setor h2 { display: flex; align-items: center; gap: var(--space-2); font-size: 16px; }
    .mini { display: grid; grid-template-columns: repeat(auto-fit, minmax(72px, 1fr)); gap: var(--space-2) var(--space-3); margin: 0;
      dt { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--tinta-2); }
      dd { margin: 0; font-size: 16px; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; } }
    .minibarras { display: flex; align-items: flex-end; gap: 4px; height: 56px; border-bottom: 1px solid var(--linha-forte);
      span { flex: 1; background: var(--grafico-1); border-radius: 2px 2px 0 0; min-height: 1px; }
      .parcial { background: repeating-linear-gradient(135deg, var(--grafico-1) 0 4px, var(--sinal-suave) 4px 6px); } }
    .lista { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); font-size: 13px;
      li { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); } }
    .fundo { display: flex; flex-wrap: wrap; gap: var(--space-4); align-items: flex-start; }
    .fundo .grafico { flex: 999 1 560px; }
    .fundo .alertas { flex: 1 1 320px; }
    .alerta { display: flex; gap: var(--space-2); align-items: flex-start; padding: var(--space-2) var(--space-3);
      border: 1px solid var(--linha); border-left: 4px solid var(--atencao); border-radius: var(--radius-sm);
      color: var(--tinta); text-decoration: none; font-size: 13px;
      &.critico { border-left-color: var(--critico); }
      &:hover { background: var(--superficie-2); } }
  `,
})
export class AbaGeral {
  protected readonly estado = inject(EstadoPainel);
  private readonly dsh = inject(DshService);
  protected readonly numero = numero;
  protected readonly percentual = percentual;
  protected readonly duracao = duracao;
  protected readonly rotulo = ROTULO_SEMAFORO;
  protected readonly tom = TOM_SEMAFORO;
  protected readonly limites = computed(() => this.dsh.opcoes()?.limites ?? []);

  protected readonly insuficientes = computed(() =>
    (this.estado.dados()?.materiais.estoque_critico ?? []).filter((c) => c.insuficiente).length);

  protected arred(v: number | null): number | null {
    return v === null ? null : Math.round(v);
  }

  protected readonly miniDias = computed(() => {
    const dias = this.estado.dados()?.graficos.producao_por_dia ?? [];
    const max = Math.max(1, ...dias.map((d) => d.realizada));
    return dias.map((d, i) => ({
      data: d.data, altura: (d.realizada / max) * 100, parcial: this.estado.incluiHoje() && i === dias.length - 1,
      titulo: `${diaMes(d.data)}: ${numero(d.realizada)}`,
    }));
  });

  protected readonly descricaoDias = computed(() =>
    'Produção por dia: ' + this.miniDias().map((d) => d.titulo + (d.parcial ? ' (parcial)' : '')).join(', '));

  protected readonly alertas = computed<Alerta[]>(() => {
    const d = this.estado.dados();
    if (!d) return [];
    const lista: Alerta[] = [];
    for (const p of d.paradas_em_andamento) {
      lista.push({ texto: `${p.maquina} parada`, detalhe: `OS #${p.chamado_id} · ${duracao(p.minutos)} · ${p.motivo}`, tom: 'critico', aba: 'manutencao' });
    }
    for (const c of d.materiais.estoque_critico.filter((x) => x.insuficiente)) {
      lista.push({ texto: `${c.sku} insuficiente`, detalhe: `${numero(c.estoque)} em estoque para ${numero(c.pedido)} pedidos`, tom: 'critico', aba: 'materiais' });
    }
    if (d.atendimento_meta.semaforo === 'vermelho' || d.atendimento_meta.semaforo === 'amarelo') {
      lista.push({ texto: `Atendimento da meta em ${percentual(d.atendimento_meta.valor)}`,
        detalhe: `${numero(d.producao.realizada)} de ${numero(d.producao.meta)} no período`,
        tom: d.atendimento_meta.semaforo === 'vermelho' ? 'critico' : 'atencao', aba: 'producao' });
    }
    if (d.qualidade.criticas_pendentes) {
      lista.push({ texto: `${d.qualidade.criticas_pendentes} ocorrência(s) crítica(s) sem resolução`,
        detalhe: 'gravidade crítica, ainda abertas ou em análise', tom: 'atencao', aba: 'qualidade' });
    }
    return lista;
  });
}
