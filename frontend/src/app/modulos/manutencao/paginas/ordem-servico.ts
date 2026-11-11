import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import {
  Chamado,
  FUSO_FABRICA,
  Peca,
  ROTULO_PRIORIDADE,
  ROTULO_STATUS_CHAMADO,
  ROTULO_STATUS_EQUIPAMENTO,
  ROTULO_TIPO,
  TOM_PRIORIDADE,
  TOM_STATUS_CHAMADO,
  TOM_STATUS_EQUIPAMENTO,
  TipoManutencao,
  duracao,
} from '../mnt.modelos';
import { MntService } from '../mnt.service';

/** Detalhe da OS. O técnico responsável registra laudo e peças e conclui; a gestão também conclui e cancela. */
@Component({
  selector: 'am-ordem-servico',
  imports: [ReactiveFormsModule, DatePipe, RouterLink, Etiqueta],
  templateUrl: './ordem-servico.html',
  styleUrl: './ordem-servico.scss',
})
export class OrdemServico implements OnInit {
  private readonly mnt = inject(MntService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly id = input.required<string>();

  protected readonly fuso = FUSO_FABRICA;
  protected readonly duracao = duracao;
  protected readonly r = {
    prioridade: ROTULO_PRIORIDADE,
    tomPrioridade: TOM_PRIORIDADE,
    status: ROTULO_STATUS_CHAMADO,
    tomStatus: TOM_STATUS_CHAMADO,
    equip: ROTULO_STATUS_EQUIPAMENTO,
    tomEquip: TOM_STATUS_EQUIPAMENTO,
    tipo: ROTULO_TIPO,
  };
  protected readonly tipos: TipoManutencao[] = ['CORRETIVA', 'PREVENTIVA'];

  protected readonly os = signal<Chamado | null>(null);
  protected readonly pecas = signal<Peca[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);
  protected readonly cancelando = signal(false);

  protected readonly causas = computed(() => this.mnt.opcoes()?.causas_raiz ?? []);
  private readonly permissoes = computed(() => this.mnt.opcoes()?.permissoes);

  /** Pode assumir: chamado aberto e persona técnica. */
  protected readonly podeAssumir = computed(() => this.os()?.status_chamado === 'ABERTO' && !!this.permissoes()?.atender);

  /** Pode editar laudo/peças: OS em andamento e (responsável com perfil técnico, ou gestão). Espelha a RN03 da API. */
  protected readonly podeEditar = computed(() => {
    const os = this.os();
    const p = this.permissoes();
    if (!os || !p || os.status_chamado !== 'EM_ANDAMENTO') return false;
    const souResponsavel = os.tecnico_id === this.auth.usuario()?.id;
    return p.concluir_qualquer || (p.atender && souResponsavel);
  });
  /** Gestão sem perfil técnico (Supervisor) só conclui; peças e rascunho são do técnico. */
  protected readonly podeMexerEmPecas = computed(() => this.podeEditar() && !!this.permissoes()?.atender);
  protected readonly podeCancelar = computed(() => {
    const s = this.os()?.status_chamado;
    return (s === 'ABERTO' || s === 'EM_ANDAMENTO') && !!this.permissoes()?.cancelar;
  });

  protected readonly formLaudo = this.fb.group({
    diagnostico_tecnico: ['', [Validators.required, Validators.maxLength(4000)]],
    causa_raiz: ['', [Validators.required, Validators.maxLength(150)]],
    tipo_manutencao: this.fb.control<TipoManutencao>('CORRETIVA'),
  });
  protected readonly formPeca = this.fb.group({
    peca_id: [0, Validators.min(1)],
    quantidade: [1, [Validators.required, Validators.min(0.01)]],
  });
  protected readonly formCancelar = this.fb.group({
    motivo: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(500)]],
  });

  async ngOnInit(): Promise<void> {
    try {
      await this.mnt.carregarOpcoes();
      this.preencher(await firstValueFrom(this.mnt.chamado(Number(this.id()))));
      if (this.podeMexerEmPecas()) {
        this.pecas.set(await firstValueFrom(this.mnt.pecas()));
      }
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected assumir(): Promise<void> {
    const os = this.os()!;
    return this.executar(this.mnt.assumir(os.id), 'OS assumida. A máquina está em manutenção.', async () => {
      this.pecas.set(await firstValueFrom(this.mnt.pecas()));
    });
  }

  protected salvarRascunho(): Promise<void> {
    return this.executar(this.mnt.salvarLaudo(this.os()!.id, this.formLaudo.getRawValue()), 'Rascunho do laudo salvo.');
  }

  protected concluir(): Promise<void> {
    if (this.formLaudo.invalid) {
      this.formLaudo.markAllAsTouched();
      this.erro.set('Para concluir, preencha o diagnóstico técnico e a causa raiz (RN04).');
      return Promise.resolve();
    }
    return this.executar(
      this.mnt.concluir(this.os()!.id, this.formLaudo.getRawValue()),
      'OS concluída. A máquina voltou a funcionar.',
    );
  }

  protected adicionarPeca(): Promise<void> {
    if (this.formPeca.invalid) {
      this.formPeca.markAllAsTouched();
      this.erro.set('Escolha a peça e uma quantidade maior que zero (RN09).');
      return Promise.resolve();
    }
    const { peca_id, quantidade } = this.formPeca.getRawValue();
    return this.executar(this.mnt.adicionarPeca(this.os()!.id, peca_id, quantidade), 'Peça registrada.', async () => {
      this.formPeca.reset();
    });
  }

  protected removerPeca(itemId: number): Promise<void> {
    return this.executar(this.mnt.removerPeca(this.os()!.id, itemId), 'Peça removida.');
  }

  protected cancelar(): Promise<void> {
    if (this.formCancelar.invalid) {
      this.formCancelar.markAllAsTouched();
      this.erro.set('Informe o motivo do cancelamento (mínimo de 5 caracteres).');
      return Promise.resolve();
    }
    return this.executar(
      this.mnt.cancelar(this.os()!.id, this.formCancelar.getRawValue().motivo),
      'OS cancelada. A máquina voltou a funcionar.',
      async () => this.cancelando.set(false),
    );
  }

  protected invalido(form: 'laudo' | 'peca' | 'cancelar', campo: string): boolean {
    const c =
      form === 'laudo' ? this.formLaudo.get(campo) : form === 'peca' ? this.formPeca.get(campo) : this.formCancelar.get(campo);
    return !!c && c.touched && c.invalid;
  }

  private preencher(os: Chamado): void {
    this.os.set(os);
    this.formLaudo.setValue(
      { diagnostico_tecnico: os.diagnostico_tecnico ?? '', causa_raiz: os.causa_raiz ?? '', tipo_manutencao: os.tipo_manutencao },
      { emitEvent: false },
    );
  }

  private async executar(acao: Observable<Chamado>, mensagem: string, depois?: () => Promise<void>): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.sucesso.set(null);
    try {
      const os = await firstValueFrom(acao);
      // Em andamento, o formulário mantém o que o técnico está digitando (ex.: ao registrar uma peça).
      if (os.status_chamado === 'EM_ANDAMENTO') this.os.set(os);
      else this.preencher(os);
      await depois?.();
      this.sucesso.set(mensagem);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }
}
