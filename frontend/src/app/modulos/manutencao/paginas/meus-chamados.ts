import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { mensagemDeErro } from '../../../core/erros';
import { atualizarPeriodicamente } from '../atualizacao';
import { Chamado } from '../mnt.modelos';
import { MntService } from '../mnt.service';
import { TabelaChamados } from '../tabela-chamados';

/** Chamados que o operador abriu, para acompanhar o atendimento. */
@Component({
  selector: 'am-meus-chamados',
  imports: [TabelaChamados, RouterLink],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Meus chamados</h1>
          <p class="legenda">Chamados abertos por você. A lista se atualiza sozinha.</p>
        </div>
        <a class="btn primario" routerLink="../abrir">Abrir chamado</a>
      </div>
      @if (aviso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      <section class="cartao">
        <am-tabela-chamados
          [chamados]="chamados()"
          [colunas]="['os', 'maquina', 'prioridade', 'status', 'falha', 'abertura', 'tecnico', 'downtime']"
          vazio="Você ainda não abriu chamados."
        />
      </section>
    </div>
  `,
})
export class MeusChamados {
  private readonly mnt = inject(MntService);
  protected readonly chamados = signal<Chamado[]>([]);
  protected readonly erro = signal<string | null>(null);
  protected readonly aviso = signal<string | null>(inject(Router).getCurrentNavigation()?.extras.state?.['aviso'] ?? null);

  constructor() {
    atualizarPeriodicamente(() =>
      this.mnt.chamados({ meus_abertos: true }).subscribe({
        next: (l) => this.chamados.set(l),
        error: (e) => this.erro.set(mensagemDeErro(e)),
      }),
    );
  }
}
