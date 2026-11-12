import { Component, computed, inject, signal } from '@angular/core';

import { mensagemDeErro } from '../../../core/erros';
import { atualizarPeriodicamente } from '../atualizacao';
import { Chamado } from '../mnt.modelos';
import { MntService } from '../mnt.service';
import { TabelaChamados } from '../tabela-chamados';

/** OS em andamento: as do próprio técnico (o Administrador vê todas). Clique no número para abrir a OS. */
@Component({
  selector: 'am-ordens-mnt',
  imports: [TabelaChamados],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Ordens de serviço em andamento</h1>
        <p class="legenda">{{ todas() ? 'Todas as OS em atendimento.' : 'As OS que você assumiu.' }} Clique no número para registrar laudo, peças e concluir.</p>
      </div>
      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      <section class="cartao">
        <am-tabela-chamados
          [chamados]="chamados()"
          [colunas]="['os', 'maquina', 'prioridade', 'tipo', 'falha', 'tecnico', 'downtime']"
          vazio="Nenhuma OS em andamento. Assuma um chamado na fila."
        />
      </section>
    </div>
  `,
})
export class Ordens {
  private readonly mnt = inject(MntService);
  protected readonly chamados = signal<Chamado[]>([]);
  protected readonly erro = signal<string | null>(null);
  /** Quem conclui OS de qualquer técnico (gestão) vê todas; o técnico vê as suas. */
  protected readonly todas = computed(() => this.mnt.opcoes()?.permissoes.concluir_qualquer ?? false);

  constructor() {
    atualizarPeriodicamente(async () => {
      try {
        await this.mnt.carregarOpcoes();
        this.mnt.chamados({ status: ['EM_ANDAMENTO'], meus_atendimentos: !this.todas() }).subscribe({
          next: (l) => this.chamados.set(l),
          error: (e) => this.erro.set(mensagemDeErro(e)),
        });
      } catch (e) {
        this.erro.set(mensagemDeErro(e));
      }
    });
  }
}
