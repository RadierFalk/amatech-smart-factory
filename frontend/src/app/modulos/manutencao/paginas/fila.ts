import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { atualizarPeriodicamente } from '../atualizacao';
import { Chamado } from '../mnt.modelos';
import { MntService } from '../mnt.service';
import { TabelaChamados } from '../tabela-chamados';

/** Fila técnica: chamados abertos, Crítica primeiro e, empatados, quem espera há mais tempo. */
@Component({
  selector: 'am-fila-mnt',
  imports: [TabelaChamados],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Fila de chamados</h1>
          <p class="legenda">{{ chamados().length }} aguardando técnico · atualização automática a cada 30 s</p>
        </div>
        <label class="campo filtro">
          <span>Setor</span>
          <select [value]="setor()" (change)="filtrar($any($event.target).value)">
            <option value="">Todos</option>
            @for (s of setores(); track s) { <option [value]="s">{{ s }}</option> }
          </select>
        </label>
      </div>
      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      <section class="cartao">
        <am-tabela-chamados
          [chamados]="chamados()"
          [colunas]="['os', 'maquina', 'prioridade', 'tipo', 'falha', 'espera', 'operador']"
          [acao]="podeAssumir() ? botaoAssumir : null"
          vazio="Nenhum chamado aguardando atendimento."
        />
        <ng-template #botaoAssumir let-c>
          <button type="button" class="btn primario pequeno" [disabled]="assumindo() === c.id" (click)="assumir(c)">
            {{ assumindo() === c.id ? 'Assumindo…' : 'Assumir' }}
          </button>
        </ng-template>
      </section>
    </div>
  `,
  styles: `.filtro { min-width: 220px; }`,
})
export class Fila {
  private readonly mnt = inject(MntService);
  private readonly router = inject(Router);

  protected readonly chamados = signal<Chamado[]>([]);
  protected readonly setor = signal('');
  protected readonly erro = signal<string | null>(null);
  protected readonly assumindo = signal<number | null>(null);
  protected readonly setores = computed(() => this.mnt.opcoes()?.setores ?? []);
  protected readonly podeAssumir = computed(() => this.mnt.opcoes()?.permissoes.atender ?? false);

  constructor() {
    atualizarPeriodicamente(() => this.carregar());
  }

  protected filtrar(setor: string): void {
    this.setor.set(setor);
    this.carregar();
  }

  protected async assumir(c: Chamado): Promise<void> {
    this.assumindo.set(c.id);
    this.erro.set(null);
    try {
      await firstValueFrom(this.mnt.assumir(c.id));
      await this.router.navigate(['/manutencao/ordens', c.id]);
    } catch (e) {
      // Ex.: outro técnico assumiu antes (409). Recarrega para a fila refletir o estado real.
      this.erro.set(mensagemDeErro(e));
      this.carregar();
    } finally {
      this.assumindo.set(null);
    }
  }

  private carregar(): void {
    this.mnt.fila(this.setor()).subscribe({
      next: (l) => this.chamados.set(l),
      error: (e) => this.erro.set(mensagemDeErro(e)),
    });
  }
}
