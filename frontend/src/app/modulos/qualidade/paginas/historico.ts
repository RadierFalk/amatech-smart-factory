import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { FUSO_FABRICA, ROTULO_STATUS_CHAMADO } from '../../manutencao/mnt.modelos';
import {
  CLASSIFICACOES,
  Classificacao,
  ItemCadastro,
  Ocorrencia,
  ROTULO_CLASSIFICACAO,
  ROTULO_SITUACAO,
  ROTULO_STATUS,
  SITUACOES,
  STATUS,
  SituacaoProduto,
  StatusOcorrencia,
  TOM_CLASSIFICACAO,
  TOM_SITUACAO,
  TOM_STATUS,
} from '../qld.modelos';
import { FiltroOcorrencias, QldService } from '../qld.service';

/** Histórico com busca, filtros, edição, ocultação, chamado na manutenção e exportação CSV. */
@Component({
  selector: 'am-historico-qld',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, Etiqueta],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Histórico de ocorrências</h1>
          <p class="legenda">{{ ocorrencias().length }} ocorrência(s){{ ocorrencias().length >= 500 ? ' (limite de 500: refine os filtros)' : '' }}.
            Ocorrências ocultadas não aparecem aqui nem no painel.</p>
        </div>
        <button type="button" class="btn" [disabled]="!ocorrencias().length" (click)="exportar()">Exportar CSV</button>
      </div>

      <form class="cartao filtros" [formGroup]="form" (ngSubmit)="buscar()">
        <label class="campo busca"><span>Busca</span>
          <input formControlName="busca" placeholder="Nº de série, #ocorrência, TAG, estação, defeito, responsável…" /></label>
        <label class="campo"><span>Tipo de defeito</span>
          <select formControlName="tipo_defeito_id"><option [ngValue]="0">Todos</option>
            @for (t of tipos(); track t.id) { <option [ngValue]="t.id">{{ t.nome }}</option> }</select></label>
        <label class="campo"><span>Estação</span>
          <select formControlName="estacao_id"><option [ngValue]="0">Todas</option>
            @for (e of estacoes(); track e.id) { <option [ngValue]="e.id">{{ e.nome }}</option> }</select></label>
        <label class="campo"><span>Classificação</span>
          <select formControlName="classificacao"><option value="">Todas</option>
            @for (c of classificacoes; track c) { <option [value]="c">{{ rotuloClassificacao[c] }}</option> }</select></label>
        <label class="campo"><span>Situação do produto</span>
          <select formControlName="situacao"><option value="">Todas</option>
            @for (s of situacoes; track s) { <option [value]="s">{{ rotuloSituacao[s] }}</option> }</select></label>
        <label class="campo"><span>Status</span>
          <select formControlName="status"><option value="">Todos</option>
            @for (s of statusLista; track s) { <option [value]="s">{{ rotuloStatus[s] }}</option> }</select></label>
        <label class="campo"><span>De</span><input type="date" formControlName="de" /></label>
        <label class="campo"><span>Até</span><input type="date" formControlName="ate" /></label>
        <div class="botoes"><button type="submit" class="btn primario">Filtrar</button>
          <button type="button" class="btn" (click)="limpar()">Limpar</button></div>
      </form>

      <div aria-live="polite">
        @if (aviso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
        @if (avisoIntegracao(); as a) { <div class="aviso" [class.sucesso]="a.tipo === 'sucesso'" [class.atencao]="a.tipo === 'aviso'" role="status">{{ a.mensagem }}</div> }
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      </div>

      <section class="cartao tabela-rolagem">
        @if (ocorrencias().length) {
          <table class="tabela">
            <thead><tr>
              <th scope="col">#</th><th scope="col">Data</th><th scope="col">Notebook</th><th scope="col">Estação</th>
              <th scope="col">Defeito</th><th scope="col">Máquina</th><th scope="col">Classificação</th>
              <th scope="col">Produto</th><th scope="col">Status</th><th scope="col">Responsável</th>
              <th scope="col">Manutenção</th><th scope="col"><span class="so-leitor">Ações</span></th>
            </tr></thead>
            <tbody>
              @for (o of ocorrencias(); track o.id) {
                <tr>
                  <td class="codigo">{{ o.id }}</td>
                  <td class="nowrap">{{ o.ocorrida_em | date: 'dd/MM/yy HH:mm' : fuso }}</td>
                  <td class="nowrap"><span class="codigo">{{ o.numero_serie }}</span><br /><span class="legenda">{{ o.modelo }}</span></td>
                  <td>{{ o.estacao_nome }}</td>
                  <td><strong>{{ o.tipo_defeito_nome }}</strong><br /><span class="legenda">{{ o.observacao }}</span></td>
                  <td class="codigo">{{ o.equipamento_tag }}</td>
                  <td><am-etiqueta [texto]="rotuloClassificacao[o.classificacao]" [tom]="tomClassificacao[o.classificacao]" /></td>
                  <td><am-etiqueta [texto]="rotuloSituacao[o.situacao_produto]" [tom]="tomSituacao[o.situacao_produto]" /></td>
                  <td><am-etiqueta [texto]="rotuloStatus[o.status]" [tom]="tomStatus[o.status]" /></td>
                  <td>{{ o.responsavel_nome }}</td>
                  <td class="nowrap">
                    @if (o.chamado_id) { OS #{{ o.chamado_id }}<br /><span class="legenda">{{ rotuloChamado[o.chamado_status!] }}</span> }
                    @else if (permissoes()?.abrir_chamado) {
                      <button type="button" class="btn pequeno" [disabled]="ocupado()" (click)="abrirChamado(o)">Abrir chamado</button>
                    } @else { — }
                  </td>
                  <td class="acoes">
                    @if (permissoes()?.editar) { <a class="btn pequeno" [routerLink]="['/qualidade/ocorrencias', o.id, 'editar']">Editar</a> }
                    @if (permissoes()?.ocultar) {
                      <button type="button" class="btn pequeno perigo" [disabled]="ocupado()" (click)="ocultar(o)">Ocultar</button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        } @else {
          <p class="legenda">Nenhuma ocorrência com esses filtros.</p>
        }
      </section>
    </div>
  `,
  styles: `
    .filtros { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: var(--space-3); align-items: end; }
    .busca { grid-column: 1 / -1; }
    .botoes { display: flex; gap: var(--space-2); }
    .acoes { display: flex; gap: var(--space-1); }
    .nowrap { white-space: nowrap; }
  `,
})
export class HistoricoQld implements OnInit {
  private readonly qld = inject(QldService);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly classificacoes = CLASSIFICACOES;
  protected readonly situacoes = SITUACOES;
  protected readonly statusLista = STATUS;
  protected readonly rotuloClassificacao = ROTULO_CLASSIFICACAO;
  protected readonly rotuloSituacao = ROTULO_SITUACAO;
  protected readonly rotuloStatus = ROTULO_STATUS;
  protected readonly rotuloChamado = ROTULO_STATUS_CHAMADO;
  protected readonly tomClassificacao = TOM_CLASSIFICACAO;
  protected readonly tomSituacao = TOM_SITUACAO;
  protected readonly tomStatus = TOM_STATUS;

  protected readonly ocorrencias = signal<Ocorrencia[]>([]);
  protected readonly estacoes = signal<ItemCadastro[]>([]);
  protected readonly tipos = signal<ItemCadastro[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly aviso = signal<string | null>(inject(Router).getCurrentNavigation()?.extras.state?.['aviso'] ?? null);
  protected readonly avisoIntegracao = signal<{ tipo: string; mensagem: string } | null>(null);
  protected readonly permissoes = computed(() => this.qld.opcoes()?.permissoes);

  protected readonly form = inject(NonNullableFormBuilder).group({
    busca: '',
    tipo_defeito_id: 0,
    estacao_id: 0,
    classificacao: '',
    situacao: '',
    status: '',
    de: '',
    ate: '',
  });

  async ngOnInit(): Promise<void> {
    try {
      await this.qld.carregarOpcoes();
      const [estacoes, tipos] = await Promise.all([
        firstValueFrom(this.qld.itens('estacoes', true)),
        firstValueFrom(this.qld.itens('tipos-defeito', true)),
      ]);
      this.estacoes.set(estacoes);
      this.tipos.set(tipos);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
    await this.buscar();
  }

  protected limpar(): void {
    this.form.reset();
    void this.buscar();
  }

  protected async buscar(): Promise<void> {
    const f = this.form.getRawValue();
    const filtro: FiltroOcorrencias = {
      busca: f.busca.trim() || undefined,
      tipo_defeito_id: f.tipo_defeito_id || undefined,
      estacao_id: f.estacao_id || undefined,
      classificacao: (f.classificacao || undefined) as Classificacao | undefined,
      situacao: (f.situacao || undefined) as SituacaoProduto | undefined,
      status: (f.status || undefined) as StatusOcorrencia | undefined,
      de: f.de || undefined,
      ate: f.ate || undefined,
    };
    try {
      this.erro.set(null);
      this.ocorrencias.set(await firstValueFrom(this.qld.ocorrencias(filtro)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected async ocultar(o: Ocorrencia): Promise<void> {
    if (!confirm(`Ocultar a ocorrência #${o.id}? Ela deixa de aparecer no histórico e no painel.`)) return;
    await this.executar(async () => {
      await firstValueFrom(this.qld.ocultar(o.id));
      this.aviso.set(`Ocorrência #${o.id} ocultada.`);
    });
  }

  protected async abrirChamado(o: Ocorrencia): Promise<void> {
    await this.executar(async () => {
      const r = await firstValueFrom(this.qld.abrirChamado(o.id));
      this.avisoIntegracao.set(r.avisos[0] ?? null);
    });
  }

  private async executar(acao: () => Promise<void>): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.aviso.set(null);
    this.avisoIntegracao.set(null);
    try {
      await acao();
      await this.buscar();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }

  protected exportar(): void {
    baixarCsv(`ocorrencias-qualidade-${new Date().toISOString().slice(0, 10)}.csv`, paraCsv(this.ocorrencias()));
  }
}

const CABECALHO = [
  'Ocorrência', 'Data e hora (UTC)', 'Nº de série', 'Modelo', 'Estação', 'Tipo de defeito', 'Máquina', 'Classificação',
  'Situação do produto', 'Status', 'Observação', 'Ação realizada', 'Responsável', 'Chamado na manutenção',
];

export function paraCsv(ocorrencias: Ocorrencia[]): string {
  const celula = (v: unknown) => {
    const texto = v === null || v === undefined ? '' : String(v);
    return /[";\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
  };
  const linhas = ocorrencias.map((o) =>
    [
      o.id, o.ocorrida_em, o.numero_serie, o.modelo, o.estacao_nome, o.tipo_defeito_nome, o.equipamento_tag,
      ROTULO_CLASSIFICACAO[o.classificacao], ROTULO_SITUACAO[o.situacao_produto], ROTULO_STATUS[o.status],
      o.observacao, o.acao_realizada, o.responsavel_nome, o.chamado_id ? `OS #${o.chamado_id}` : '',
    ].map(celula).join(';'),
  );
  // ";" e BOM: o Excel em português abre direto, com acentos.
  return '﻿' + [CABECALHO.join(';'), ...linhas].join('\r\n');
}

function baixarCsv(nome: string, conteudo: string): void {
  const url = URL.createObjectURL(new Blob([conteudo], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  a.click();
  URL.revokeObjectURL(url);
}
