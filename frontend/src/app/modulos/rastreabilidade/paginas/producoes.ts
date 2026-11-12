import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import { Modelo, Producao } from '../ras.modelos';
import { RasService } from '../ras.service';

/** Lista de produções (busca por série, ID ou modelo) e início de uma produção nova. */
@Component({
  selector: 'am-producoes',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, Etiqueta],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Produções</h1>
          <p class="legenda">{{ producoes().length }} notebook(s){{ producoes().length >= 500 ? ' (limite de 500: refine a busca)' : '' }}.
            Mais recentes primeiro.</p>
        </div>
      </div>

      @if (permissoes()?.producao) {
        <form class="cartao nova" [formGroup]="formNova" (ngSubmit)="iniciar()" novalidate>
          <h2 class="titulo-secao largura-total">Iniciar produção</h2>
          <label class="campo"><span>Modelo</span>
            <select formControlName="modelo_id"><option [ngValue]="0" disabled>Selecione…</option>
              @for (m of modelos(); track m.id) { <option [ngValue]="m.id">{{ m.nome }} · {{ m.codigo }}</option> }</select></label>
          <label class="campo"><span>Responsável pela etapa</span>
            <select formControlName="responsavel_id"><option [ngValue]="0">Eu mesmo(a)</option>
              @for (r of responsaveis(); track r.id) { <option [ngValue]="r.id">{{ r.nome }} ({{ r.matricula }})</option> }</select></label>
          <div class="botao"><button type="submit" class="btn primario" [disabled]="ocupado()">Iniciar e gerar nº de série</button></div>
        </form>
      }

      <form class="cartao filtros" [formGroup]="form" (ngSubmit)="buscar()">
        <label class="campo busca"><span>Busca</span><input formControlName="busca" placeholder="Nº de série, ID da produção ou modelo" /></label>
        <label class="campo"><span>Etapa</span>
          <select formControlName="etapa_id"><option [ngValue]="0">Todas</option>
            @for (e of etapas(); track e.id) { <option [ngValue]="e.id">{{ e.nome }}</option> }</select></label>
        <label class="campo"><span>Modelo</span>
          <select formControlName="modelo_id"><option [ngValue]="0">Todos</option>
            @for (m of modelos(); track m.id) { <option [ngValue]="m.id">{{ m.nome }}</option> }</select></label>
        <div class="botoes"><button type="submit" class="btn primario">Buscar</button>
          <button type="button" class="btn" (click)="limpar()">Limpar</button></div>
      </form>

      <div aria-live="polite">
        @if (aviso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      </div>

      <section class="cartao tabela-rolagem">
        @if (producoes().length) {
          <table class="tabela">
            <thead><tr><th scope="col">Nº de série</th><th scope="col">Modelo</th><th scope="col">Etapa</th>
              <th scope="col">Responsável</th><th scope="col">Início</th><th scope="col">Última atualização</th></tr></thead>
            <tbody>
              @for (p of producoes(); track p.id) {
                <tr>
                  <td><a class="codigo" [routerLink]="['/rastreabilidade/producoes', p.id]">{{ p.numero_serie }}</a></td>
                  <td>{{ p.modelo_nome }}</td>
                  <td><am-etiqueta [texto]="p.etapa_nome" /></td>
                  <td>{{ p.responsavel_nome }}</td>
                  <td class="nowrap">{{ p.iniciada_em | date: 'dd/MM HH:mm' : fuso }}</td>
                  <td class="nowrap">{{ p.atualizada_em | date: 'dd/MM HH:mm' : fuso }}</td>
                </tr>
              }
            </tbody>
          </table>
        } @else {
          <p class="legenda">Nenhuma produção encontrada.</p>
        }
      </section>
    </div>
  `,
  styles: `
    .nova, .filtros { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-3); align-items: end; }
    .largura-total, .busca { grid-column: 1 / -1; }
    .botoes { display: flex; gap: var(--space-2); }
    .nowrap { white-space: nowrap; }
  `,
})
export class Producoes implements OnInit {
  private readonly ras = inject(RasService);
  private readonly router = inject(Router);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly fuso = FUSO_FABRICA;

  protected readonly producoes = signal<Producao[]>([]);
  protected readonly modelos = signal<Modelo[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly aviso = signal<string | null>(this.router.getCurrentNavigation()?.extras.state?.['aviso'] ?? null);
  protected readonly permissoes = computed(() => this.ras.opcoes()?.permissoes);
  protected readonly etapas = computed(() => this.ras.opcoes()?.etapas ?? []);
  protected readonly responsaveis = computed(() => this.ras.opcoes()?.responsaveis ?? []);

  protected readonly form = this.fb.group({ busca: '', etapa_id: 0, modelo_id: 0 });
  protected readonly formNova = this.fb.group({ modelo_id: [0, Validators.min(1)], responsavel_id: 0 });

  async ngOnInit(): Promise<void> {
    try {
      await this.ras.carregarOpcoes();
      this.modelos.set(await firstValueFrom(this.ras.modelos()));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
    await this.buscar();
  }

  protected limpar(): void {
    this.form.reset();
    void this.buscar();
  }

  protected async buscar(): Promise<void> {
    const f = this.form.getRawValue();
    try {
      this.erro.set(null);
      this.producoes.set(await firstValueFrom(this.ras.producoes({ busca: f.busca.trim(), etapa_id: f.etapa_id, modelo_id: f.modelo_id })));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected async iniciar(): Promise<void> {
    if (this.formNova.invalid) {
      this.erro.set('Escolha o modelo do notebook.');
      return;
    }
    const f = this.formNova.getRawValue();
    this.ocupado.set(true);
    this.erro.set(null);
    try {
      const p = await firstValueFrom(this.ras.criarProducao({ modelo_id: f.modelo_id, responsavel_id: f.responsavel_id || null }));
      await this.router.navigate(['/rastreabilidade/producoes', p.id], {
        state: { aviso: `Produção iniciada: ${p.numero_serie} (${p.id_unica}).` },
      });
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }
}
