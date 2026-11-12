import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { FiltroPainel, LinhaHistorico, Perda, numero, percentual } from '../dsh.modelos';
import { DshService } from '../dsh.service';
import { FiltroDsh } from './filtro';

export function csv(cabecalho: string[], linhas: (string | number | null)[][]): string {
  const celula = (v: string | number | null) => {
    const t = v === null || v === undefined ? '' : String(v);
    return /[";\n\r]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
  };
  // ";" e BOM: o Excel em português abre direto, com acentos.
  return '﻿' + [cabecalho, ...linhas].map((l) => l.map(celula).join(';')).join('\r\n');
}

function baixar(nome: string, conteudo: string): void {
  const url = URL.createObjectURL(new Blob([conteudo], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  a.click();
  URL.revokeObjectURL(url);
}

/** Histórico (T08): produção e meta por dia, turno e modelo, e as perdas do período, com download em CSV. */
@Component({
  selector: 'am-historico-dsh',
  imports: [DatePipe, FiltroDsh],
  template: `
    <div class="pagina">
      <h1 class="titulo-tela">Histórico</h1>
      <am-filtro-dsh (mudou)="carregar($event)" />
      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      <section class="cartao">
        <div class="titulo-acao">
          <h2 class="titulo-secao">Produção e meta por dia, turno e modelo</h2>
          <button type="button" class="btn" [disabled]="!producao().length" (click)="exportarProducao()">Exportar CSV</button>
        </div>
        @if (producao().length) {
          <div class="tabela-rolagem"><table class="tabela">
            <thead><tr><th scope="col">Dia</th><th scope="col">Turno</th><th scope="col">Modelo</th><th scope="col" class="num">Realizada</th>
              <th scope="col" class="num">Aprovada</th><th scope="col" class="num">Reprovada</th><th scope="col" class="num">Meta</th>
              <th scope="col" class="num">Atendimento</th></tr></thead>
            <tbody>@for (l of producao(); track $index) {
              <tr><td class="nowrap">{{ l.data | date: 'dd/MM/yyyy' : 'UTC' }}</td><td>{{ l.turno }}</td><td>{{ l.modelo }}</td>
                <td class="num">{{ numero(l.realizada) }}</td><td class="num">{{ numero(l.aprovada) }}</td><td class="num">{{ numero(l.reprovada) }}</td>
                <td class="num">{{ l.meta ? numero(l.meta) : '—' }}</td><td class="num">{{ percentual(l.atendimento_meta) }}</td></tr>
            }</tbody>
          </table></div>
        } @else { <p class="legenda">Sem produção nem meta no período.</p> }
      </section>

      <section class="cartao">
        <div class="titulo-acao">
          <h2 class="titulo-secao">Perdas</h2>
          <button type="button" class="btn" [disabled]="!perdas().length" (click)="exportarPerdas()">Exportar CSV</button>
        </div>
        @if (perdas().length) {
          <div class="tabela-rolagem"><table class="tabela">
            <thead><tr><th scope="col">Dia</th><th scope="col">Turno</th><th scope="col">Estação</th><th scope="col">Modelo</th>
              <th scope="col">Tipo</th><th scope="col" class="num">Quantidade</th><th scope="col">Observação</th></tr></thead>
            <tbody>@for (p of perdas(); track p.id) {
              <tr><td class="nowrap">{{ p.data | date: 'dd/MM/yyyy' : 'UTC' }}</td><td>{{ p.turno_nome }}</td><td>{{ p.estacao_nome }}</td>
                <td>{{ p.modelo_nome }}</td><td>{{ p.tipo_nome }}</td><td class="num">{{ numero(p.quantidade) }}</td><td>{{ p.observacao ?? '' }}</td></tr>
            }</tbody>
          </table></div>
        } @else { <p class="legenda">Nenhuma perda no período.</p> }
      </section>
    </div>
  `,
  styles: `
    .titulo-acao { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--space-2); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .nowrap { white-space: nowrap; }
  `,
})
export class HistoricoDsh {
  private readonly dsh = inject(DshService);
  protected readonly numero = numero;
  protected readonly percentual = percentual;
  protected readonly producao = signal<LinhaHistorico[]>([]);
  protected readonly perdas = signal<Perda[]>([]);
  protected readonly erro = signal<string | null>(null);
  private filtro: FiltroPainel | null = null;

  protected async carregar(f: FiltroPainel): Promise<void> {
    this.filtro = f;
    try {
      this.erro.set(null);
      const [producao, perdas] = await Promise.all([firstValueFrom(this.dsh.historicoProducao(f)), firstValueFrom(this.dsh.perdas(f))]);
      this.producao.set(producao);
      this.perdas.set(perdas);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected exportarProducao(): void {
    baixar(`producao-${this.filtro?.de}-a-${this.filtro?.ate}.csv`, csv(
      ['Dia', 'Turno', 'Modelo', 'Realizada', 'Aprovada', 'Reprovada', 'Meta', 'Atendimento (%)'],
      this.producao().map((l) => [l.data, l.turno, l.modelo, l.realizada, l.aprovada, l.reprovada, l.meta || null,
        l.atendimento_meta === null ? null : String(l.atendimento_meta).replace('.', ',')]),
    ));
  }

  protected exportarPerdas(): void {
    baixar(`perdas-${this.filtro?.de}-a-${this.filtro?.ate}.csv`, csv(
      ['Dia', 'Turno', 'Estação', 'Modelo', 'Tipo', 'Quantidade', 'Observação', 'Origem', 'Registrado por'],
      this.perdas().map((p) => [p.data, p.turno_nome, p.estacao_nome, p.modelo_nome, p.tipo_nome, p.quantidade, p.observacao,
        p.origem === 'csv' ? 'Planilha' : 'Manual', p.registrado_por_nome]),
    ));
  }
}
