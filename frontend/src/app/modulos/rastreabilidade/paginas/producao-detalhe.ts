import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import { ProducaoDetalhe, ROTULO_SOLICITACAO, TOM_SOLICITACAO, rotuloOrigem } from '../ras.modelos';
import { RasService } from '../ras.service';

/** Ficha do notebook: etapa atual, mudança de etapa, histórico, não conformidades e materiais. */
@Component({
  selector: 'am-producao-detalhe',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, Etiqueta],
  template: `
    <div class="pagina">
      <p><a routerLink="/rastreabilidade/producoes">← Produções</a></p>

      <div aria-live="polite">
        @if (aviso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      </div>

      @if (p(); as p) {
        <div class="cartao cabecalho">
          <div>
            <h1 class="titulo-tela">{{ p.numero_serie }}</h1>
            <p class="legenda">{{ p.id_unica }} · {{ p.modelo_nome }} ({{ p.modelo_codigo }})</p>
          </div>
          <dl class="dados">
            <div><dt>Etapa atual</dt><dd><am-etiqueta [texto]="p.etapa_nome" /></dd></div>
            <div><dt>Responsável</dt><dd>{{ p.responsavel_nome }}</dd></div>
            <div><dt>Início</dt><dd>{{ p.iniciada_em | date: 'dd/MM/yy HH:mm' : fuso }} · por {{ p.criado_por_nome }}</dd></div>
            <div><dt>Materiais pendentes</dt><dd>{{ p.materiais_pendentes }}</dd></div>
          </dl>
        </div>

        @if (permissoes()?.producao) {
          <form class="cartao grade" [formGroup]="formEtapa" (ngSubmit)="mudarEtapa()" novalidate>
            <h2 class="titulo-secao largura-total">Mudar de etapa</h2>
            <label class="campo"><span>Nova etapa</span>
              <select formControlName="etapa_id">
                @for (e of etapas(); track e.id) {
                  <option [ngValue]="e.id" [disabled]="e.id === p.etapa_id">{{ e.nome }}{{ e.id === p.proxima_etapa_id ? ' (sugerida)' : '' }}</option>
                }
              </select></label>
            <label class="campo"><span>Responsável</span>
              <select formControlName="responsavel_id"><option [ngValue]="0">Manter {{ p.responsavel_nome }}</option>
                @for (r of responsaveis(); track r.id) { <option [ngValue]="r.id">{{ r.nome }}</option> }</select></label>
            @if (reprovando()) {
              <label class="campo largura-total"><span>Falha encontrada</span>
                <textarea formControlName="descricao_falha" rows="2" placeholder="Ex.: teclas não respondem no teste funcional"></textarea></label>
              <label class="campo largura-total"><span>Motivo da reprovação</span>
                <input formControlName="motivo_reprovacao" placeholder="Ex.: falha no teclado" /></label>
            }
            <div class="largura-total"><button type="submit" class="btn primario" [disabled]="ocupado()">
              {{ reprovando() ? 'Reprovar e registrar não conformidade' : 'Mudar etapa' }}</button></div>
          </form>
        }

        <div class="colunas">
          <section class="cartao">
            <h2 class="titulo-secao">Histórico de etapas</h2>
            <ol class="linha-tempo">
              @for (h of p.passagens; track h.id) {
                <li>
                  <span class="quando">{{ h.registrada_em | date: 'dd/MM HH:mm' : fuso }}</span>
                  <am-etiqueta [texto]="h.etapa_nome" />
                  <span class="legenda">por {{ h.usuario_nome }}{{ h.responsavel_nome ? ' · resp. ' + h.responsavel_nome : '' }} · {{ origem(h.origem) }}</span>
                </li>
              }
            </ol>
          </section>

          <section class="cartao">
            <h2 class="titulo-secao">Não conformidades</h2>
            @for (n of p.nao_conformidades; track n.id) {
              <div class="nc">
                <strong>{{ n.motivo_reprovacao }}</strong>
                <span>{{ n.descricao_falha }}</span>
                <span class="legenda">{{ n.registrada_em | date: 'dd/MM HH:mm' : fuso }} · {{ n.usuario_nome }}
                  {{ n.origem_sistema ? ' · ' + n.origem_sistema + (n.id_externo ? ' ' + n.id_externo : '') : '' }}</span>
              </div>
            } @empty { <p class="legenda">Nenhuma.</p> }
            @if (permissoes()?.producao) {
              <form class="grade-nc" [formGroup]="formNc" (ngSubmit)="registrarNc()" novalidate>
                <label class="campo"><span>Falha</span><input formControlName="descricao_falha" /></label>
                <label class="campo"><span>Motivo</span><input formControlName="motivo_reprovacao" /></label>
                <div><button type="submit" class="btn" [disabled]="ocupado()">Registrar sem mudar a etapa</button></div>
              </form>
            }
          </section>
        </div>

        <section class="cartao">
          <div class="titulo-acao">
            <h2 class="titulo-secao">Materiais</h2>
            @if (permissoes()?.solicitar) {
              <button type="button" class="btn" [disabled]="ocupado()" (click)="solicitarMateriais()">Solicitar a lista do modelo</button>
            }
          </div>
          @if (p.solicitacoes.length) {
            <div class="tabela-rolagem"><table class="tabela">
              <thead><tr><th scope="col">Componente</th><th scope="col" class="num">Pedida</th><th scope="col" class="num">Entregue</th>
                <th scope="col">Situação</th></tr></thead>
              <tbody>@for (s of p.solicitacoes; track s.id) {
                <tr><td><span class="codigo">{{ s.sku }}</span> {{ s.componente_nome }}</td>
                  <td class="num">{{ s.quantidade }}</td><td class="num">{{ s.quantidade_baixada }}</td>
                  <td><am-etiqueta [texto]="rotuloSolicitacao[s.status]" [tom]="tomSolicitacao[s.status]" /></td></tr>
              }</tbody>
            </table></div>
          } @else { <p class="legenda">Nenhum material solicitado.</p> }
        </section>

        @if (p.mesmo_modelo.length) {
          <section class="cartao">
            <h2 class="titulo-secao">Outros notebooks do modelo {{ p.modelo_nome }}</h2>
            <ul class="mesmo-modelo">
              @for (o of p.mesmo_modelo; track o.id) {
                <li><a class="codigo" [routerLink]="['/rastreabilidade/producoes', o.id]">{{ o.numero_serie }}</a> <am-etiqueta [texto]="o.etapa_nome" /></li>
              }
            </ul>
          </section>
        }

        @if (permissoes()?.excluir_producao) {
          <div><button type="button" class="btn perigo" [disabled]="ocupado()" (click)="excluir()">Excluir produção</button></div>
        }
      } @else if (!erro()) {
        <p class="legenda" role="status">Carregando a produção…</p>
      }
    </div>
  `,
  styles: `
    .cabecalho { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-4); }
    .dados { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-3); margin: 0; flex: 1; min-width: 280px; }
    dt { font-size: 12px; color: var(--tinta-2); font-weight: 600; }
    dd { margin: 0; }
    .grade { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-3); align-items: end; }
    .largura-total { grid-column: 1 / -1; }
    textarea { width: 100%; padding: var(--space-2) var(--space-3); font: inherit; border: 1px solid var(--linha-forte); border-radius: var(--radius-sm); }
    .colunas { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: var(--space-4); }
    .linha-tempo { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-2); }
    .linha-tempo li { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
    .quando { font-variant-numeric: tabular-nums; min-width: 88px; }
    .nc { display: grid; gap: 2px; padding: var(--space-2) 0; border-bottom: 1px solid var(--linha); }
    .grade-nc { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-2); align-items: end; margin-top: var(--space-3); }
    .titulo-acao { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--space-2); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .mesmo-modelo { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: var(--space-3); }
  `,
})
export class ProducaoDetalheTela implements OnInit {
  private readonly ras = inject(RasService);
  private readonly router = inject(Router);
  private readonly fb = inject(NonNullableFormBuilder);

  /** :id da rota */
  readonly id = input.required<string>();

  protected readonly fuso = FUSO_FABRICA;
  protected readonly rotuloSolicitacao = ROTULO_SOLICITACAO;
  protected readonly tomSolicitacao = TOM_SOLICITACAO;
  protected readonly origem = rotuloOrigem;

  protected readonly p = signal<ProducaoDetalhe | null>(null);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly aviso = signal<string | null>(this.router.getCurrentNavigation()?.extras.state?.['aviso'] ?? null);
  protected readonly permissoes = computed(() => this.ras.opcoes()?.permissoes);
  protected readonly etapas = computed(() => this.ras.opcoes()?.etapas ?? []);
  protected readonly responsaveis = computed(() => this.ras.opcoes()?.responsaveis ?? []);

  protected readonly formEtapa = this.fb.group({
    etapa_id: [0, Validators.min(1)],
    responsavel_id: 0,
    descricao_falha: '',
    motivo_reprovacao: '',
  });
  protected readonly formNc = this.fb.group({
    descricao_falha: ['', Validators.required],
    motivo_reprovacao: ['', Validators.required],
  });
  private readonly etapaEscolhida = signal(0);
  protected readonly reprovando = computed(
    () => this.etapas().find((e) => e.id === this.etapaEscolhida())?.nome.toLowerCase() === 'reprovado',
  );

  async ngOnInit(): Promise<void> {
    this.formEtapa.controls.etapa_id.valueChanges.subscribe((v) => this.etapaEscolhida.set(v));
    try {
      await this.ras.carregarOpcoes();
      this.mostrar(await firstValueFrom(this.ras.producao(Number(this.id()))));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  private mostrar(p: ProducaoDetalhe): void {
    this.p.set(p);
    this.formEtapa.reset({ etapa_id: p.proxima_etapa_id ?? 0, responsavel_id: 0, descricao_falha: '', motivo_reprovacao: '' });
  }

  protected mudarEtapa(): Promise<void> {
    const f = this.formEtapa.getRawValue();
    if (!f.etapa_id) {
      this.erro.set('Escolha a nova etapa.');
      return Promise.resolve();
    }
    if (this.reprovando() && !(f.descricao_falha.trim() && f.motivo_reprovacao.trim())) {
      this.erro.set('Para reprovar, informe a falha encontrada e o motivo da reprovação.');
      return Promise.resolve();
    }
    const nome = this.etapas().find((e) => e.id === f.etapa_id)?.nome;
    return this.executar(
      this.ras.mudarEtapa(this.p()!.id, {
        etapa_id: f.etapa_id,
        responsavel_id: f.responsavel_id || null,
        ...(this.reprovando() ? { descricao_falha: f.descricao_falha, motivo_reprovacao: f.motivo_reprovacao } : {}),
      }),
      `Etapa alterada para ${nome}.`,
    );
  }

  protected registrarNc(): Promise<void> {
    if (this.formNc.invalid) {
      this.erro.set('Informe a falha e o motivo.');
      return Promise.resolve();
    }
    return this.executar(this.ras.registrarNaoConformidade(this.p()!.id, this.formNc.getRawValue()), 'Não conformidade registrada.', () =>
      this.formNc.reset(),
    );
  }

  protected async solicitarMateriais(): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    try {
      const r = await firstValueFrom(this.ras.solicitarMateriais(this.p()!.id));
      this.aviso.set(`${r.criadas} solicitação(ões) criada(s)${r.ignoradas ? `; ${r.ignoradas} componente(s) já tinham pedido ativo` : ''}.`);
      this.mostrar(await firstValueFrom(this.ras.producao(this.p()!.id)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }

  protected async excluir(): Promise<void> {
    const p = this.p()!;
    if (!confirm(`Excluir a produção ${p.numero_serie}? O histórico, as não conformidades e as solicitações dela também saem.`)) return;
    this.ocupado.set(true);
    try {
      await firstValueFrom(this.ras.excluirProducao(p.id));
      await this.router.navigate(['/rastreabilidade/producoes'], { state: { aviso: `Produção ${p.numero_serie} excluída.` } });
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }

  private async executar(acao: Observable<ProducaoDetalhe>, mensagem: string, depois?: () => void): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.aviso.set(null);
    try {
      this.mostrar(await firstValueFrom(acao));
      this.aviso.set(mensagem);
      depois?.();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }
}
