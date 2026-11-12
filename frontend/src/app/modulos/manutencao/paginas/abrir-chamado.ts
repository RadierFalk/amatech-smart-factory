import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Equipamento, Prioridade, ROTULO_PRIORIDADE } from '../mnt.modelos';
import { MntService } from '../mnt.service';

/** Operador abre chamado corretivo: a máquina fica PARADA até a conclusão da OS. */
@Component({
  selector: 'am-abrir-chamado',
  imports: [ReactiveFormsModule],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Abrir chamado de manutenção</h1>
        <p class="legenda">A máquina fica parada até a conclusão da OS. Só aparecem máquinas funcionando.</p>
      </div>

      <form class="cartao formulario" [formGroup]="form" (ngSubmit)="enviar()" novalidate>
        <label class="campo">
          <span>Máquina</span>
          <select formControlName="equipamento_id" [attr.aria-invalid]="invalido('equipamento_id')">
            <option [ngValue]="0" disabled>Selecione…</option>
            @for (e of disponiveis(); track e.id) {
              <option [ngValue]="e.id">{{ e.codigo_tag }} · {{ e.nome }} ({{ e.setor }})</option>
            }
          </select>
        </label>

        <fieldset class="campo">
          <legend>Prioridade</legend>
          <div class="prioridades">
            @for (p of prioridades; track p) {
              <label class="opcao" [class.marcada]="form.controls.prioridade.value === p">
                <input type="radio" formControlName="prioridade" [value]="p" />
                {{ rotulos[p] }}
              </label>
            }
          </div>
        </fieldset>

        <label class="campo">
          <span>O que aconteceu?</span>
          <textarea formControlName="descricao_falha" rows="4" [attr.aria-invalid]="invalido('descricao_falha')"
                    placeholder="Ex.: travamento no feeder de alimentação de resistores"></textarea>
          <span class="campo-dica">Descreva o sintoma observado (mínimo de 5 caracteres).</span>
        </label>

        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

        <div><button type="submit" class="btn primario" [disabled]="enviando()">
          {{ enviando() ? 'Abrindo…' : 'Abrir chamado e parar máquina' }}
        </button></div>
      </form>
    </div>
  `,
  styles: `
    .formulario { display: grid; gap: var(--space-4); max-width: 640px; }
    fieldset { border: 0; padding: 0; margin: 0; }
    legend { font-weight: 600; margin-bottom: var(--space-1); }
    .prioridades { display: flex; flex-wrap: wrap; gap: var(--space-2); }
    .opcao {
      display: flex; align-items: center; gap: var(--space-1);
      padding: var(--space-2) var(--space-3);
      border: 1px solid var(--linha-forte); border-radius: var(--radius-sm); cursor: pointer;
      input { width: auto; min-height: 0; }
      &.marcada { border-color: var(--sinal); background: var(--sinal-suave); }
    }
    textarea {
      width: 100%; padding: var(--space-2) var(--space-3); font: inherit;
      border: 1px solid var(--linha-forte); border-radius: var(--radius-sm);
      &[aria-invalid='true'] { border-color: var(--critico); }
    }
  `,
})
export class AbrirChamado implements OnInit {
  private readonly mnt = inject(MntService);
  private readonly router = inject(Router);
  private readonly fb = inject(NonNullableFormBuilder);

  /** ?equipamento=ID vindo do painel */
  readonly equipamento = input<string | undefined>();

  protected readonly prioridades: Prioridade[] = ['BAIXA', 'MEDIA', 'ALTA', 'CRITICA'];
  protected readonly rotulos = ROTULO_PRIORIDADE;
  protected readonly maquinas = signal<Equipamento[]>([]);
  protected readonly disponiveis = computed(() => this.maquinas().filter((e) => e.status_operacional === 'OPERACIONAL'));
  protected readonly enviando = signal(false);
  protected readonly erro = signal<string | null>(null);

  protected readonly form = this.fb.group({
    equipamento_id: [0, Validators.min(1)],
    prioridade: this.fb.control<Prioridade>('MEDIA'),
    descricao_falha: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(2000)]],
  });


  async ngOnInit(): Promise<void> {
    try {
      this.maquinas.set(await firstValueFrom(this.mnt.equipamentos()));
      const pre = Number(this.equipamento());
      if (pre && this.disponiveis().some((e) => e.id === pre)) {
        this.form.controls.equipamento_id.setValue(pre);
      }
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected invalido(campo: 'equipamento_id' | 'descricao_falha'): boolean {
    const c = this.form.controls[campo];
    return c.touched && c.invalid;
  }

  protected async enviar(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.erro.set('Escolha a máquina e descreva a falha.');
      return;
    }
    this.enviando.set(true);
    this.erro.set(null);
    try {
      const os = await firstValueFrom(this.mnt.abrirChamado(this.form.getRawValue()));
      await this.router.navigate(['/manutencao/meus-chamados'], { state: { aviso: `Chamado OS #${os.id} aberto para ${os.equipamento_tag}.` } });
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.enviando.set(false);
    }
  }
}
