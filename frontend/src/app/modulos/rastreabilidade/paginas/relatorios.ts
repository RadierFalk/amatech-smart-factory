import { formatDate } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import { ColunaRelatorio, Relatorio } from '../ras.modelos';
import { RasService } from '../ras.service';

const TIPOS = [
  { id: 'producao', rotulo: 'Produções e etapa atual', periodo: true },
  { id: 'estoque', rotulo: 'Estoque e pendências de material', periodo: false },
  { id: 'materiais', rotulo: 'Solicitações e baixas', periodo: true },
  { id: 'nao_conformidades', rotulo: 'Não conformidades', periodo: true },
];

/** Valor de uma célula como aparece na tela e no CSV (datas no horário da fábrica). */
export function celula(coluna: ColunaRelatorio, valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined) return '';
  if (coluna.formato === 'data') return formatDate(String(valor), 'dd/MM/yyyy HH:mm', 'en-US', FUSO_FABRICA);
  return String(valor);
}

export function paraCsv(r: Relatorio): string {
  const escapar = (t: string) => (/[";\n\r]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t);
  const linhas = r.linhas.map((l) => r.colunas.map((c) => escapar(celula(c, l[c.chave]))).join(';'));
  // ";" e BOM: o Excel em português abre direto, com acentos.
  return '﻿' + [r.colunas.map((c) => escapar(c.titulo)).join(';'), ...linhas].join('\r\n');
}

/** Relatórios da produção e dos materiais, com filtro de período e exportação CSV. */
@Component({
  selector: 'am-relatorios-ras',
  imports: [ReactiveFormsModule],
  template: `
    <div class="pagina">
      <h1 class="titulo-tela">Relatórios</h1>

      <form class="cartao filtros" [formGroup]="form" (ngSubmit)="gerar()">
        <label class="campo"><span>Relatório</span>
          <select formControlName="tipo">@for (t of tipos; track t.id) { <option [value]="t.id">{{ t.rotulo }}</option> }</select></label>
        @if (temPeriodo()) {
          <label class="campo"><span>De</span><input type="date" formControlName="de" /></label>
          <label class="campo"><span>Até</span><input type="date" formControlName="ate" /></label>
        }
        <div class="botoes">
          <button type="submit" class="btn primario">Gerar</button>
          <button type="button" class="btn" [disabled]="!rel()?.linhas?.length" (click)="exportar()">Exportar CSV</button>
        </div>
      </form>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      @if (rel(); as r) {
        <section class="cartao">
          <h2 class="titulo-secao">{{ r.titulo }}</h2>
          <p class="legenda">{{ r.linhas.length }} linha(s). Datas no horário da fábrica (Manaus).</p>
          @if (r.linhas.length) {
            <div class="tabela-rolagem"><table class="tabela">
              <thead><tr>@for (c of r.colunas; track c.chave) { <th scope="col" [class.num]="c.formato === 'numero'">{{ c.titulo }}</th> }</tr></thead>
              <tbody>@for (l of r.linhas; track $index) {
                <tr>@for (c of r.colunas; track c.chave) { <td [class.num]="c.formato === 'numero'" [class.nowrap]="c.formato === 'data'">{{ celula(c, l[c.chave]) }}</td> }</tr>
              }</tbody>
            </table></div>
          }
        </section>
      }
    </div>
  `,
  styles: `
    .filtros { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--space-3); align-items: end; }
    .botoes { display: flex; gap: var(--space-2); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .nowrap { white-space: nowrap; }
  `,
})
export class RelatoriosRas implements OnInit {
  private readonly ras = inject(RasService);
  protected readonly tipos = TIPOS;
  protected readonly celula = celula;
  protected readonly rel = signal<Relatorio | null>(null);
  protected readonly erro = signal<string | null>(null);
  protected readonly form = inject(NonNullableFormBuilder).group({ tipo: 'producao', de: '', ate: '' });
  protected readonly temPeriodo = signal(true);

  ngOnInit(): void {
    this.form.controls.tipo.valueChanges.subscribe((t) => this.temPeriodo.set(TIPOS.find((x) => x.id === t)!.periodo));
    void this.gerar();
  }

  protected async gerar(): Promise<void> {
    const f = this.form.getRawValue();
    try {
      this.erro.set(null);
      const periodo = this.temPeriodo();
      this.rel.set(await firstValueFrom(this.ras.relatorio(f.tipo, periodo ? f.de : null, periodo ? f.ate : null)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected exportar(): void {
    const r = this.rel();
    if (!r) return;
    const url = URL.createObjectURL(new Blob([paraCsv(r)], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `relatorio-${r.tipo}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
