import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, TemplateRef, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Etiqueta } from '../../shared/etiqueta';
import {
  Chamado,
  FUSO_FABRICA,
  ROTULO_PRIORIDADE,
  ROTULO_STATUS_CHAMADO,
  ROTULO_TIPO,
  TOM_PRIORIDADE,
  TOM_STATUS_CHAMADO,
  duracao,
} from './mnt.modelos';

export type ColunaChamado = 'os' | 'maquina' | 'prioridade' | 'tipo' | 'status' | 'falha' | 'abertura' | 'espera' | 'operador' | 'tecnico' | 'downtime' | 'causa';

/** Tabela de chamados usada na fila, em "meus chamados", nas preventivas e no histórico. */
@Component({
  selector: 'am-tabela-chamados',
  imports: [DatePipe, RouterLink, NgTemplateOutlet, Etiqueta],
  template: `
    <div class="tabela-rolagem">
      <table class="tabela">
        <thead>
          <tr>
            @if (tem('os')) { <th scope="col">OS</th> }
            @if (tem('maquina')) { <th scope="col">Máquina</th> }
            @if (tem('prioridade')) { <th scope="col">Prioridade</th> }
            @if (tem('tipo')) { <th scope="col">Tipo</th> }
            @if (tem('status')) { <th scope="col">Situação</th> }
            @if (tem('falha')) { <th scope="col">Falha relatada</th> }
            @if (tem('abertura')) { <th scope="col">Abertura</th> }
            @if (tem('espera')) { <th scope="col">Aguardando</th> }
            @if (tem('operador')) { <th scope="col">Aberto por</th> }
            @if (tem('tecnico')) { <th scope="col">Técnico</th> }
            @if (tem('downtime')) { <th scope="col">Downtime</th> }
            @if (tem('causa')) { <th scope="col">Causa raiz</th> }
            @if (acao()) { <th scope="col"><span class="so-leitor">Ações</span></th> }
          </tr>
        </thead>
        <tbody>
          @for (c of chamados(); track c.id) {
            <tr>
              @if (tem('os')) { <td><a class="codigo" [routerLink]="['/manutencao/ordens', c.id]">#{{ c.id }}</a></td> }
              @if (tem('maquina')) {
                <td><span class="codigo">{{ c.equipamento_tag }}</span><div class="legenda">{{ c.equipamento_nome }} · {{ c.setor }}</div></td>
              }
              @if (tem('prioridade')) { <td><am-etiqueta [texto]="rotuloPrioridade[c.prioridade]" [tom]="tomPrioridade[c.prioridade]" /></td> }
              @if (tem('tipo')) { <td>{{ rotuloTipo[c.tipo_manutencao] }}</td> }
              @if (tem('status')) { <td><am-etiqueta [texto]="rotuloStatus[c.status_chamado]" [tom]="tomStatus[c.status_chamado]" /></td> }
              @if (tem('falha')) { <td class="falha">{{ c.descricao_falha }}</td> }
              @if (tem('abertura')) { <td class="nowrap">{{ c.data_hora_abertura | date: 'dd/MM HH:mm' : fuso }}</td> }
              @if (tem('espera')) { <td class="nowrap">{{ duracao(c.minutos_desde_abertura) }}</td> }
              @if (tem('operador')) { <td>{{ c.operador_nome }}</td> }
              @if (tem('tecnico')) { <td>{{ c.tecnico_nome ?? '—' }}</td> }
              @if (tem('downtime')) { <td class="nowrap">{{ duracao(c.downtime_minutos ?? c.minutos_desde_abertura) }}</td> }
              @if (tem('causa')) { <td>{{ c.causa_raiz ?? '—' }}</td> }
              @if (acao(); as tpl) { <td class="acoes"><ng-container *ngTemplateOutlet="tpl; context: { $implicit: c }" /></td> }
            </tr>
          } @empty {
            <tr><td [attr.colspan]="colunas().length + 1" class="legenda">{{ vazio() }}</td></tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: `
    .falha { max-width: 360px; }
    .nowrap { white-space: nowrap; }
    .acoes { text-align: right; white-space: nowrap; }
  `,
})
export class TabelaChamados {
  readonly chamados = input.required<Chamado[]>();
  readonly colunas = input<ColunaChamado[]>(['os', 'maquina', 'prioridade', 'status', 'falha', 'abertura']);
  readonly acao = input<TemplateRef<{ $implicit: Chamado }> | null>(null);
  readonly vazio = input('Nenhum chamado.');

  protected readonly fuso = FUSO_FABRICA;
  protected readonly duracao = duracao;
  protected readonly rotuloPrioridade = ROTULO_PRIORIDADE;
  protected readonly tomPrioridade = TOM_PRIORIDADE;
  protected readonly rotuloStatus = ROTULO_STATUS_CHAMADO;
  protected readonly tomStatus = TOM_STATUS_CHAMADO;
  protected readonly rotuloTipo = ROTULO_TIPO;

  protected tem(coluna: ColunaChamado): boolean {
    return this.colunas().includes(coluna);
  }
}
