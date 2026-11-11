import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Chamado, Equipamento, Prioridade, ROTULO_PRIORIDADE } from '../mnt.modelos';
import { MntService } from '../mnt.service';
import { TabelaChamados } from '../tabela-chamados';

/** Técnico programa preventivas: entram na fila sem parar a máquina; ela para quando a OS é assumida. */
@Component({
  selector: 'am-preventivas',
  imports: [ReactiveFormsModule, TabelaChamados],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Manutenção preventiva</h1>
        <p class="legenda">A preventiva entra na fila sem parar a máquina. Ela só para quando um técnico assume a OS.</p>
      </div>

      <div class="contadores">
        <div class="cartao"><span class="rotulo">Preventivas</span><span class="numero">{{ lista().length }}</span></div>
        <div class="cartao"><span class="rotulo">Aguardando</span><span class="numero">{{ contar('ABERTO') }}</span></div>
        <div class="cartao"><span class="rotulo">Concluídas</span><span class="numero">{{ contar('CONCLUIDO') }}</span></div>
      </div>

      <form class="cartao formulario" [formGroup]="form" (ngSubmit)="programar()" novalidate>
        <h2 class="titulo-secao">Programar preventiva</h2>
        <label class="campo">
          <span>Máquina</span>
          <select formControlName="equipamento_id">
            <option [ngValue]="0" disabled>Selecione…</option>
            @for (e of disponiveis(); track e.id) { <option [ngValue]="e.id">{{ e.codigo_tag }} · {{ e.nome }}</option> }
          </select>
        </label>
        <label class="campo">
          <span>Prioridade</span>
          <select formControlName="prioridade">
            @for (p of prioridades; track p) { <option [value]="p">{{ rotulos[p] }}</option> }
          </select>
        </label>
        <label class="campo largura-total">
          <span>Plano / atividades</span>
          <input formControlName="descricao_falha" placeholder="Ex.: lubrificação dos trilhos e troca de filtros" />
        </label>
        @if (erro(); as m) { <div class="aviso erro largura-total" role="alert">{{ m }}</div> }
        @if (sucesso(); as m) { <div class="aviso sucesso largura-total">{{ m }}</div> }
        <div class="largura-total"><button type="submit" class="btn primario" [disabled]="enviando()">Programar</button></div>
      </form>

      <section class="cartao">
        <h2 class="titulo-secao">Preventivas registradas</h2>
        <am-tabela-chamados [chamados]="lista()" [colunas]="['os', 'maquina', 'prioridade', 'status', 'falha', 'abertura', 'tecnico']"
                            vazio="Nenhuma preventiva registrada." />
      </section>
    </div>
  `,
  styles: `
    .contadores { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-4); }
    .contadores .cartao { display: grid; gap: var(--space-1); }
    .numero { font-family: var(--font-display); font-size: 32px; line-height: 36px; font-weight: 600; }
    .formulario { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-4); }
    .formulario h2, .largura-total { grid-column: 1 / -1; }
  `,
})
export class Preventivas implements OnInit {
  private readonly mnt = inject(MntService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly prioridades: Prioridade[] = ['BAIXA', 'MEDIA', 'ALTA', 'CRITICA'];
  protected readonly rotulos = ROTULO_PRIORIDADE;
  protected readonly lista = signal<Chamado[]>([]);
  protected readonly maquinas = signal<Equipamento[]>([]);
  protected readonly disponiveis = computed(() => this.maquinas().filter((e) => e.status_operacional === 'OPERACIONAL' && !e.os_ativa));
  protected readonly enviando = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);

  protected readonly form = this.fb.group({
    equipamento_id: [0, Validators.min(1)],
    prioridade: this.fb.control<Prioridade>('BAIXA'),
    descricao_falha: ['Manutenção preventiva programada conforme plano de manutenção do ativo.', [Validators.required, Validators.minLength(5)]],
  });

  ngOnInit(): void {
    void this.carregar();
  }

  protected contar(status: Chamado['status_chamado']): number {
    return this.lista().filter((c) => c.status_chamado === status).length;
  }

  protected async programar(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.erro.set('Escolha a máquina e descreva o plano (mínimo de 5 caracteres).');
      return;
    }
    this.enviando.set(true);
    this.erro.set(null);
    this.sucesso.set(null);
    try {
      const os = await firstValueFrom(this.mnt.programarPreventiva(this.form.getRawValue()));
      this.sucesso.set(`Preventiva OS #${os.id} programada para ${os.equipamento_tag}.`);
      this.form.controls.equipamento_id.reset();
      await this.carregar();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.enviando.set(false);
    }
  }

  private async carregar(): Promise<void> {
    try {
      const [lista, maquinas] = await Promise.all([
        firstValueFrom(this.mnt.chamados({ tipo: 'PREVENTIVA' })),
        firstValueFrom(this.mnt.equipamentos()),
      ]);
      this.lista.set(lista);
      this.maquinas.set(maquinas);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }
}
