import { formatDate } from '@angular/common';
import { Component, DestroyRef, OnInit, computed, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import {
  AvisoIntegracao,
  CLASSIFICACOES,
  Classificacao,
  ItemCadastro,
  Maquina,
  Notebook,
  OcorrenciaEntrada,
  Produto,
  ROTULO_CLASSIFICACAO,
  ROTULO_SITUACAO,
  ROTULO_STATUS,
  SITUACOES,
  STATUS,
  SituacaoProduto,
  StatusOcorrencia,
} from '../qld.modelos';
import { QldService } from '../qld.service';

/** Data e hora de agora na fábrica (Manaus), nos formatos dos campos date e time. */
export function agoraNaFabrica(agora = new Date()): { data: string; hora: string } {
  return {
    data: formatDate(agora, 'yyyy-MM-dd', 'en-US', FUSO_FABRICA),
    hora: formatDate(agora, 'HH:mm', 'en-US', FUSO_FABRICA),
  };
}

/** Registro de ocorrência (/registrar) e edição (/ocorrencias/:id/editar). */
@Component({
  selector: 'am-formulario-ocorrencia',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">{{ id() ? 'Editar ocorrência #' + id() : 'Registrar ocorrência' }}</h1>
        <p class="legenda">
          @if (id()) { O responsável continua sendo quem registrou. }
          @else { Você fica como responsável. Data e hora são da fábrica (Manaus). }
        </p>
      </div>

      <div aria-live="polite">
        @if (registrada(); as r) {
          <div class="aviso sucesso" role="status">
            Ocorrência #{{ r }} registrada. <a routerLink="/qualidade/historico">Ver no histórico</a>
          </div>
        }
        @for (a of avisos(); track a.mensagem) {
          <div class="aviso" [class.sucesso]="a.tipo === 'sucesso'" [class.atencao]="a.tipo === 'aviso'" role="status">{{ a.mensagem }}</div>
        }
      </div>

      <form class="cartao formulario" [formGroup]="form" (ngSubmit)="enviar()" novalidate>
        <h2 class="titulo-secao largura-total">Produto e local</h2>
        @if (historico(); as h) {
          <div class="campo">
            <span>Notebook (número de série)</span>
            <p class="fixo"><span class="codigo">{{ h.numero_serie }}</span> · {{ h.modelo }}
              <span class="legenda">Do histórico, sem produção na Rastreabilidade</span></p>
          </div>
        } @else {
          <div class="campo notebook">
            <label for="busca-notebook">Notebook (número de série)</label>
            <input id="busca-notebook" type="search" placeholder="Buscar: ex. 000031" autocomplete="off"
                   [value]="busca()" (input)="buscar($any($event.target).value)" />
            <select formControlName="producao_id" aria-label="Notebook encontrado" [attr.aria-invalid]="invalido('producao_id')">
              <option [ngValue]="0" disabled>{{ notebooks().length ? 'Selecione…' : 'Nenhum notebook em produção encontrado' }}</option>
              @for (n of notebooks(); track n.id) {
                <option [ngValue]="n.id">{{ n.numero_serie }} · {{ n.modelo }}{{ n.etapa ? ' · ' + n.etapa : '' }}</option>
              }
            </select>
            <span class="campo-dica">Produções da Rastreabilidade ainda não expedidas.</span>
          </div>
        }
        <label class="campo"><span>Estação</span>
          <select formControlName="estacao_id" [attr.aria-invalid]="invalido('estacao_id')">
            <option [ngValue]="0" disabled>Selecione…</option>
            @for (e of estacoes(); track e.id) { <option [ngValue]="e.id">{{ e.nome }}</option> }
          </select>
        </label>
        <label class="campo"><span>Máquina</span>
          <select formControlName="equipamento_id" [attr.aria-invalid]="invalido('equipamento_id')">
            <option [ngValue]="0" disabled>Selecione…</option>
            @for (m of maquinas(); track m.id) { <option [ngValue]="m.id">{{ m.codigo_tag }} · {{ m.nome }}</option> }
          </select>
        </label>
        <label class="campo"><span>Data</span><input type="date" formControlName="data" [attr.aria-invalid]="invalido('data')" /></label>
        <label class="campo"><span>Hora</span><input type="time" formControlName="hora" [attr.aria-invalid]="invalido('hora')" /></label>

        <h2 class="titulo-secao largura-total">Defeito</h2>
        <label class="campo"><span>Tipo de defeito</span>
          <select formControlName="tipo_defeito_id" [attr.aria-invalid]="invalido('tipo_defeito_id')">
            <option [ngValue]="0" disabled>Selecione…</option>
            @for (t of tipos(); track t.id) { <option [ngValue]="t.id">{{ t.nome }}</option> }
          </select>
        </label>
        <fieldset class="campo">
          <legend>Classificação</legend>
          <div class="opcoes">
            @for (c of classificacoes; track c) {
              <label class="opcao" [class.marcada]="form.controls.classificacao.value === c">
                <input type="radio" formControlName="classificacao" [value]="c" /> {{ rotuloClassificacao[c] }}
              </label>
            }
          </div>
        </fieldset>
        <label class="campo"><span>Situação do produto</span>
          <select formControlName="situacao_produto">
            @for (s of situacoes; track s) { <option [value]="s">{{ rotuloSituacao[s] }}</option> }
          </select>
        </label>
        <label class="campo"><span>Status da ocorrência</span>
          <select formControlName="status">
            @for (s of statusLista; track s) { <option [value]="s">{{ rotuloStatus[s] }}</option> }
          </select>
        </label>

        <label class="campo largura-total"><span>Observação</span>
          <textarea formControlName="observacao" rows="3" [attr.aria-invalid]="invalido('observacao')"
                    placeholder="O que foi encontrado no notebook"></textarea>
        </label>
        <label class="campo largura-total"><span>Ação realizada</span>
          <textarea formControlName="acao_realizada" rows="2" [attr.aria-invalid]="invalido('acao_realizada')"
                    placeholder="Ex.: produto retido para reprocesso"></textarea>
        </label>

        @if (!id() && podeAbrirChamado()) {
          <label class="marcar largura-total">
            <input type="checkbox" formControlName="abrir_chamado" />
            <span><strong>Abrir chamado na manutenção</strong> (defeito causado pela máquina).
              A máquina fica parada até o técnico concluir a OS.</span>
          </label>
        }

        @if (erro(); as m) { <div class="aviso erro largura-total" role="alert">{{ m }}</div> }

        <div class="botoes largura-total">
          <button type="submit" class="btn primario" [disabled]="enviando()">
            {{ enviando() ? 'Salvando…' : id() ? 'Salvar alterações' : 'Registrar ocorrência' }}
          </button>
          @if (id()) { <a class="btn" routerLink="/qualidade/historico">Cancelar</a> }
        </div>
      </form>
    </div>
  `,
  styles: `
    .formulario { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-4); max-width: 960px; }
    .largura-total { grid-column: 1 / -1; }
    fieldset { border: 0; padding: 0; margin: 0; }
    legend { font-weight: 600; margin-bottom: var(--space-1); }
    .opcoes { display: flex; flex-wrap: wrap; gap: var(--space-2); }
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
    .marcar { display: flex; gap: var(--space-2); align-items: flex-start; input { width: auto; min-height: 0; margin-top: 4px; } }
    .notebook { display: grid; gap: var(--space-1); label { font-weight: 600; } }
    .fixo { margin: 0; display: grid; gap: 2px; }
    .botoes { display: flex; gap: var(--space-2); }
  `,
})
export class FormularioOcorrencia implements OnInit {
  private readonly qld = inject(QldService);
  private readonly router = inject(Router);
  private readonly fb = inject(NonNullableFormBuilder);
  private temporizador: ReturnType<typeof setTimeout> | undefined;
  /** Notebooks já vistos, para o escolhido continuar na lista quando a busca muda. */
  private readonly conhecidos = new Map<number, Notebook>();

  /** :id da rota de edição (ausente no registro). */
  readonly id = input<string | undefined>();

  protected readonly classificacoes = CLASSIFICACOES;
  protected readonly situacoes = SITUACOES;
  protected readonly statusLista = STATUS;
  protected readonly rotuloClassificacao = ROTULO_CLASSIFICACAO;
  protected readonly rotuloSituacao = ROTULO_SITUACAO;
  protected readonly rotuloStatus = ROTULO_STATUS;

  protected readonly notebooks = signal<Notebook[]>([]);
  protected readonly busca = signal('');
  /** Edição de ocorrência antiga cujo notebook não tem produção na Rastreabilidade: fica fixo. */
  protected readonly historico = signal<Pick<Produto, 'id' | 'numero_serie' | 'modelo'> | null>(null);
  protected readonly estacoes = signal<ItemCadastro[]>([]);
  protected readonly tipos = signal<ItemCadastro[]>([]);
  protected readonly maquinas = signal<Maquina[]>([]);
  protected readonly enviando = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly registrada = signal<number | null>(null);
  protected readonly avisos = signal<AvisoIntegracao[]>([]);
  protected readonly podeAbrirChamado = computed(() => this.qld.opcoes()?.permissoes.abrir_chamado ?? false);

  protected readonly form = this.fb.group({
    producao_id: [0, Validators.min(1)],
    estacao_id: [0, Validators.min(1)],
    equipamento_id: [0, Validators.min(1)],
    tipo_defeito_id: [0, Validators.min(1)],
    data: ['', Validators.required],
    hora: ['', Validators.required],
    classificacao: this.fb.control<Classificacao>('MAIOR'),
    situacao_produto: this.fb.control<SituacaoProduto>('REPROVADO'),
    status: this.fb.control<StatusOcorrencia>('ABERTA'),
    observacao: ['', [Validators.required, Validators.maxLength(2000)]],
    acao_realizada: ['', [Validators.required, Validators.maxLength(2000)]],
    abrir_chamado: false,
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.temporizador));
  }

  async ngOnInit(): Promise<void> {
    const agora = agoraNaFabrica();
    this.form.patchValue({ data: agora.data, hora: agora.hora });
    try {
      await this.qld.carregarOpcoes();
      const id = Number(this.id());
      // Na edição, a lista inclui itens inativados depois do registro (para o valor atual aparecer).
      const [notebooks, estacoes, tipos, maquinas] = await Promise.all([
        firstValueFrom(this.qld.notebooks()),
        firstValueFrom(this.qld.itens('estacoes', !!id)),
        firstValueFrom(this.qld.itens('tipos-defeito', !!id)),
        firstValueFrom(this.qld.maquinas()),
      ]);
      this.mostrarNotebooks(notebooks);
      this.estacoes.set(estacoes);
      this.tipos.set(tipos);
      this.maquinas.set(maquinas);
      if (id) {
        const oc = await firstValueFrom(this.qld.ocorrencia(id));
        const { producao_id, produto_id, numero_serie, modelo, ...resto } = oc;
        this.form.patchValue({
          ...resto,
          data: formatDate(oc.ocorrida_em, 'yyyy-MM-dd', 'en-US', FUSO_FABRICA),
          hora: formatDate(oc.ocorrida_em, 'HH:mm', 'en-US', FUSO_FABRICA),
        });
        if (producao_id) {
          // O notebook pode já ter sido expedido (fora da lista): entra como opção para manter o valor.
          this.conhecidos.set(producao_id, this.conhecidos.get(producao_id) ?? { id: producao_id, numero_serie, modelo, etapa: '' });
          this.form.controls.producao_id.setValue(producao_id);
          this.mostrarNotebooks(this.notebooks());
        } else {
          this.historico.set({ id: produto_id, numero_serie, modelo });
          this.form.controls.producao_id.clearValidators();
          this.form.controls.producao_id.updateValueAndValidity();
        }
        if (!maquinas.some((m) => m.id === oc.equipamento_id)) {
          // Máquina inativada depois: mantém a opção para não perder o valor.
          this.maquinas.update((l) => [...l, { id: oc.equipamento_id, codigo_tag: oc.equipamento_tag, nome: oc.equipamento_nome, setor: '', status_operacional: 'OPERACIONAL' }]);
        }
      }
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  /** Busca no servidor 300 ms depois da última tecla. */
  protected buscar(texto: string): void {
    this.busca.set(texto);
    clearTimeout(this.temporizador);
    this.temporizador = setTimeout(async () => {
      try {
        this.mostrarNotebooks(await firstValueFrom(this.qld.notebooks(texto)));
      } catch (e) {
        this.erro.set(mensagemDeErro(e));
      }
    }, 300);
  }

  /** Lista da busca, com o notebook escolhido sempre presente (senão o select perderia o valor). */
  private mostrarNotebooks(lista: Notebook[]): void {
    for (const n of lista) this.conhecidos.set(n.id, n);
    const escolhido = this.form.controls.producao_id.value;
    const atual = escolhido && !lista.some((n) => n.id === escolhido) ? this.conhecidos.get(escolhido) : undefined;
    this.notebooks.set(atual ? [atual, ...lista] : lista);
  }

  protected invalido(campo: keyof typeof this.form.controls): boolean {
    const c = this.form.controls[campo];
    return c.touched && c.invalid;
  }

  protected async enviar(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.erro.set('Preencha notebook, estação, máquina, tipo de defeito, data, hora, observação e ação realizada.');
      return;
    }
    const f = this.form.getRawValue();
    const historico = this.historico();
    const dados: OcorrenciaEntrada = {
      ocorrida_em: `${f.data}T${f.hora}:00`,
      classificacao: f.classificacao,
      situacao_produto: f.situacao_produto,
      status: f.status,
      observacao: f.observacao,
      acao_realizada: f.acao_realizada,
      producao_id: historico ? null : f.producao_id,
      produto_id: historico ? historico.id : null,
      estacao_id: f.estacao_id,
      tipo_defeito_id: f.tipo_defeito_id,
      equipamento_id: f.equipamento_id,
    };
    this.enviando.set(true);
    this.erro.set(null);
    this.registrada.set(null);
    this.avisos.set([]);
    try {
      const id = Number(this.id());
      if (id) {
        await firstValueFrom(this.qld.editar(id, dados));
        await this.router.navigate(['/qualidade/historico'], { state: { aviso: `Ocorrência #${id} atualizada.` } });
        return;
      }
      const r = await firstValueFrom(this.qld.registrar({ ...dados, abrir_chamado: f.abrir_chamado && this.podeAbrirChamado() }));
      this.registrada.set(r.ocorrencia.id);
      this.avisos.set(r.avisos);
      // Mantém produto, estação e máquina (o inspetor costuma registrar vários defeitos seguidos).
      this.form.patchValue({ observacao: '', acao_realizada: '', abrir_chamado: false });
      this.form.controls.observacao.markAsUntouched();
      this.form.controls.acao_realizada.markAsUntouched();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.enviando.set(false);
    }
  }
}
