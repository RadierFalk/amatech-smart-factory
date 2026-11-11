import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Chamado, Prioridade, ROTULO_PRIORIDADE, ROTULO_STATUS_CHAMADO, ROTULO_TIPO, StatusChamado, TipoManutencao } from '../mnt.modelos';
import { FiltroChamados, MntService } from '../mnt.service';
import { TabelaChamados } from '../tabela-chamados';

/** Histórico de chamados com filtros e exportação CSV (abre no Excel com acentos). */
@Component({
  selector: 'am-historico-mnt',
  imports: [ReactiveFormsModule, TabelaChamados],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Histórico de chamados</h1>
          <p class="legenda">{{ chamados().length }} chamado(s) encontrado(s){{ chamados().length >= 500 ? ' (limite de 500: refine os filtros)' : '' }}.</p>
        </div>
        <button type="button" class="btn" [disabled]="!chamados().length" (click)="exportar()">Exportar CSV</button>
      </div>

      <form class="cartao filtros" [formGroup]="form" (ngSubmit)="buscar()">
        <label class="campo"><span>Busca</span><input formControlName="busca" placeholder="TAG, máquina, falha, causa…" /></label>
        <label class="campo"><span>Situação</span>
          <select formControlName="status"><option value="">Todas</option>
            @for (s of statusLista; track s) { <option [value]="s">{{ rotuloStatus[s] }}</option> }</select></label>
        <label class="campo"><span>Tipo</span>
          <select formControlName="tipo"><option value="">Todos</option>
            @for (t of tipos; track t) { <option [value]="t">{{ rotuloTipo[t] }}</option> }</select></label>
        <label class="campo"><span>Prioridade</span>
          <select formControlName="prioridade"><option value="">Todas</option>
            @for (p of prioridades; track p) { <option [value]="p">{{ rotuloPrioridade[p] }}</option> }</select></label>
        <label class="campo"><span>Setor</span>
          <select formControlName="setor"><option value="">Todos</option>
            @for (s of setores(); track s) { <option [value]="s">{{ s }}</option> }</select></label>
        <label class="campo"><span>De</span><input type="date" formControlName="de" /></label>
        <label class="campo"><span>Até</span><input type="date" formControlName="ate" /></label>
        <div class="botoes"><button type="submit" class="btn primario">Filtrar</button>
          <button type="button" class="btn" (click)="limpar()">Limpar</button></div>
      </form>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      <section class="cartao">
        <am-tabela-chamados [chamados]="chamados()"
          [colunas]="['os', 'maquina', 'tipo', 'status', 'falha', 'abertura', 'tecnico', 'downtime', 'causa']"
          vazio="Nenhum chamado com esses filtros." />
      </section>
    </div>
  `,
  styles: `
    .filtros { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: var(--space-3); align-items: end; }
    .botoes { display: flex; gap: var(--space-2); }
  `,
})
export class Historico implements OnInit {
  private readonly mnt = inject(MntService);
  protected readonly statusLista: StatusChamado[] = ['ABERTO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO'];
  protected readonly tipos: TipoManutencao[] = ['CORRETIVA', 'PREVENTIVA'];
  protected readonly prioridades: Prioridade[] = ['CRITICA', 'ALTA', 'MEDIA', 'BAIXA'];
  protected readonly rotuloStatus = ROTULO_STATUS_CHAMADO;
  protected readonly rotuloTipo = ROTULO_TIPO;
  protected readonly rotuloPrioridade = ROTULO_PRIORIDADE;
  protected readonly setores = computed(() => this.mnt.opcoes()?.setores ?? []);

  protected readonly chamados = signal<Chamado[]>([]);
  protected readonly erro = signal<string | null>(null);

  protected readonly form = inject(NonNullableFormBuilder).group({
    busca: '',
    status: '',
    tipo: '',
    prioridade: '',
    setor: '',
    de: '',
    ate: '',
  });

  ngOnInit(): void {
    void this.buscar();
  }

  protected limpar(): void {
    this.form.reset();
    void this.buscar();
  }

  protected async buscar(): Promise<void> {
    const f = this.form.getRawValue();
    const filtro: FiltroChamados = {
      busca: f.busca || undefined,
      status: f.status ? [f.status as StatusChamado] : undefined,
      tipo: (f.tipo || undefined) as TipoManutencao | undefined,
      prioridade: (f.prioridade || undefined) as Prioridade | undefined,
      setor: f.setor || undefined,
      de: f.de || undefined,
      ate: f.ate || undefined,
    };
    try {
      this.erro.set(null);
      this.chamados.set(await firstValueFrom(this.mnt.chamados(filtro)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected exportar(): void {
    baixarCsv(`chamados-manutencao-${new Date().toISOString().slice(0, 10)}.csv`, paraCsv(this.chamados()));
  }
}

const CABECALHO = [
  'OS', 'TAG', 'Máquina', 'Setor', 'Tipo', 'Prioridade', 'Situação', 'Falha', 'Aberto por', 'Técnico',
  'Abertura (UTC)', 'Início (UTC)', 'Fim (UTC)', 'Downtime (min)', 'Diagnóstico', 'Causa raiz', 'Peças', 'Motivo do cancelamento',
];

export function paraCsv(chamados: Chamado[]): string {
  const celula = (v: unknown) => {
    const texto = v === null || v === undefined ? '' : String(v);
    return /[";\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
  };
  const linhas = chamados.map((c) =>
    [
      c.id, c.equipamento_tag, c.equipamento_nome, c.setor, ROTULO_TIPO[c.tipo_manutencao], ROTULO_PRIORIDADE[c.prioridade],
      ROTULO_STATUS_CHAMADO[c.status_chamado], c.descricao_falha, c.operador_nome, c.tecnico_nome,
      c.data_hora_abertura, c.data_hora_inicio_atendimento, c.data_hora_fim_atendimento, c.downtime_minutos,
      c.diagnostico_tecnico, c.causa_raiz, c.pecas.map((p) => `${p.codigo_peca} (${p.quantidade} ${p.unidade_medida})`).join(', '),
      c.motivo_cancelamento,
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
