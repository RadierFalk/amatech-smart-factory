import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { atualizarPeriodicamente } from '../atualizacao';
import {
  Equipamento,
  FUSO_FABRICA,
  ROTULO_PRIORIDADE,
  ROTULO_STATUS_EQUIPAMENTO,
  StatusEquipamento,
  TOM_PRIORIDADE,
  TOM_STATUS_EQUIPAMENTO,
  duracao,
} from '../mnt.modelos';
import { MntService } from '../mnt.service';

/** Painel sinótico: todas as máquinas, paradas primeiro, com a OS ativa de cada uma. */
@Component({
  selector: 'am-painel-mnt',
  imports: [RouterLink, DatePipe, Etiqueta],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Painel de máquinas</h1>
          <p class="legenda">
            Atualizado às {{ atualizadoEm() | date: 'HH:mm:ss' : fuso }} · atualização automática a cada 30 s
          </p>
        </div>
        <label class="campo filtro">
          <span>Setor</span>
          <select [value]="setor()" (change)="setor.set($any($event.target).value)">
            <option value="">Todos</option>
            @for (s of setores(); track s) { <option [value]="s">{{ s }}</option> }
          </select>
        </label>
      </div>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      <div class="resumo" aria-label="Resumo das máquinas">
        @for (r of resumo(); track r.status) {
          <div class="cartao contador">
            <span class="rotulo">{{ r.rotulo }}</span>
            <span class="numero">{{ r.qtd }}</span>
          </div>
        }
      </div>

      <div class="grade">
        @for (e of filtradas(); track e.id) {
          <article class="cartao maquina" [class]="e.status_operacional.toLowerCase()">
            <div class="cabeca">
              <span class="codigo">{{ e.codigo_tag }}</span>
              <am-etiqueta [texto]="rotuloStatus[e.status_operacional]" [tom]="tomStatus[e.status_operacional]" />
            </div>
            <h2 class="titulo-secao">{{ e.nome }}</h2>
            <p class="legenda">{{ e.setor }}{{ e.posto_trabalho ? ' · ' + e.posto_trabalho : '' }}</p>

            @if (e.os_ativa; as os) {
              <div class="os">
                <div class="os-linha">
                  <a class="codigo" [routerLink]="['../ordens', os.id]">OS #{{ os.id }}</a>
                  <am-etiqueta [texto]="rotuloPrioridade[os.prioridade]" [tom]="tomPrioridade[os.prioridade]" />
                </div>
                <p class="falha">{{ os.descricao_falha }}</p>
                <p class="legenda">
                  {{ os.tecnico_nome ? 'Técnico: ' + os.tecnico_nome : 'Aguardando técnico' }} ·
                  há {{ duracao(os.minutos_desde_abertura) }}
                </p>
              </div>
            } @else if (podeAbrir() && e.status_operacional === 'OPERACIONAL') {
              <a class="btn pequeno" routerLink="../abrir" [queryParams]="{ equipamento: e.id }">Abrir chamado</a>
            }
          </article>
        } @empty {
          @if (!carregando()) { <p class="legenda">Nenhuma máquina neste setor.</p> }
        }
      </div>
    </div>
  `,
  styles: `
    .filtro { min-width: 220px; }
    .resumo { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-3); }
    .contador { display: grid; gap: var(--space-1); }
    .numero { font-family: var(--font-display); font-size: 32px; line-height: 36px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--space-4); }
    .maquina { display: grid; align-content: start; gap: var(--space-2); border-top: 4px solid var(--ok); }
    .maquina.parada { border-top-color: var(--critico); }
    .maquina.em_manutencao { border-top-color: var(--atencao-sinal); }
    .maquina p { margin: 0; }
    .cabeca, .os-linha { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); }
    .os { display: grid; gap: var(--space-1); padding-top: var(--space-2); border-top: 1px solid var(--linha); }
    .falha { font-size: 13px; }
    .btn { justify-self: start; }
  `,
})
export class Painel {
  private readonly mnt = inject(MntService);

  protected readonly fuso = FUSO_FABRICA;
  protected readonly duracao = duracao;
  protected readonly rotuloStatus = ROTULO_STATUS_EQUIPAMENTO;
  protected readonly tomStatus = TOM_STATUS_EQUIPAMENTO;
  protected readonly rotuloPrioridade = ROTULO_PRIORIDADE;
  protected readonly tomPrioridade = TOM_PRIORIDADE;

  protected readonly equipamentos = signal<Equipamento[]>([]);
  protected readonly carregando = signal(true);
  protected readonly erro = signal<string | null>(null);
  protected readonly atualizadoEm = signal<Date | null>(null);
  protected readonly setor = signal('');

  protected readonly podeAbrir = computed(() => this.mnt.opcoes()?.permissoes.abrir_chamado ?? false);
  protected readonly setores = computed(() => [...new Set(this.equipamentos().map((e) => e.setor))].sort());
  protected readonly filtradas = computed(() =>
    this.setor() ? this.equipamentos().filter((e) => e.setor === this.setor()) : this.equipamentos(),
  );
  protected readonly resumo = computed(() => {
    const ordem: StatusEquipamento[] = ['OPERACIONAL', 'EM_MANUTENCAO', 'PARADA'];
    return ordem.map((s) => ({
      status: s,
      rotulo: ROTULO_STATUS_EQUIPAMENTO[s],
      tom: TOM_STATUS_EQUIPAMENTO[s],
      qtd: this.filtradas().filter((e) => e.status_operacional === s).length,
    }));
  });

  constructor() {
    atualizarPeriodicamente(() => this.carregar());
  }

  private carregar(): void {
    this.mnt.equipamentos().subscribe({
      next: (lista) => {
        this.equipamentos.set(lista);
        this.atualizadoEm.set(new Date());
        this.erro.set(null);
        this.carregando.set(false);
      },
      error: (e) => {
        this.erro.set(mensagemDeErro(e));
        this.carregando.set(false);
      },
    });
  }
}
