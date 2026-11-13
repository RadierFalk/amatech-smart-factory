import { DatePipe } from '@angular/common';
import { Component, ElementRef, HostListener, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { FUSO_FABRICA } from '../modulos/manutencao/mnt.modelos';
import { Alerta, AlertasService } from './alertas.service';

/** Sino de alertas: número de não lidos (sempre com texto) e a lista com atalho para onde agir. */
@Component({
  selector: 'am-sino',
  imports: [DatePipe],
  template: `
    <button type="button" class="sino" (click)="aberto.set(!aberto())" [attr.aria-expanded]="aberto()"
            [attr.aria-label]="servico.naoLidos() ? 'Alertas: ' + servico.naoLidos() + ' não lido(s)' : 'Alertas: nenhum novo'">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor"
        d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"/></svg>
      <span>Alertas</span>
      @if (servico.naoLidos()) { <span class="contador" aria-hidden="true">{{ servico.naoLidos() }}</span> }
    </button>

    @if (aberto()) {
      <section class="painel" role="dialog" aria-label="Alertas">
        <div class="topo">
          <h2>Alertas</h2>
          @if (servico.naoLidos()) {
            <button type="button" class="link" (click)="marcarTodos()">Marcar todos como lidos</button>
          }
        </div>
        @for (a of servico.alertas(); track a.id) {
          <button type="button" class="alerta" [class.nao-lido]="a.ativo && !a.lido" [class.resolvido]="!a.ativo" (click)="abrir(a)">
            <span class="linha1">
              <span class="selo-setor" [class]="'selo-setor ' + a.modulo.toLowerCase()">{{ a.modulo }}</span>
              <strong>{{ a.titulo }}</strong>
            </span>
            <span class="detalhe">{{ a.detalhe }}</span>
            <span class="quando">
              {{ a.criado_em | date: 'dd/MM HH:mm' : fuso }}
              @if (!a.ativo) { · Resolvido } @else if (!a.lido) { · Novo }
            </span>
          </button>
        } @empty {
          <p class="vazio">Nenhum alerta para o seu perfil agora.</p>
        }
      </section>
    }
  `,
  styles: `
    :host { position: relative; display: block; }
    .sino {
      display: flex; align-items: center; gap: var(--space-2); width: 100%;
      padding: var(--space-2) var(--space-3); border: 0; border-radius: var(--radius-sm);
      background: var(--noite-2); color: var(--on-noite); font: inherit; cursor: pointer;
      &:hover { filter: brightness(1.15); }
    }
    .contador {
      margin-left: auto; min-width: 22px; padding: 0 6px; border-radius: var(--radius-pill);
      background: var(--critico); color: var(--on-sinal); font-size: 12px; font-weight: 600; text-align: center;
    }
    .painel {
      position: fixed; z-index: 50; top: var(--space-4); left: calc(264px + var(--space-4));
      width: min(420px, calc(100vw - 2 * var(--space-4))); max-height: min(70vh, 640px); overflow-y: auto;
      background: var(--superficie); color: var(--tinta); border: 1px solid var(--linha);
      border-radius: var(--radius-md); box-shadow: 0 12px 32px rgba(13, 27, 42, 0.25);
      padding: var(--space-3); display: grid; gap: var(--space-2);
    }
    .topo { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); }
    h2 { margin: 0; font-size: 16px; }
    .link { background: none; border: 0; color: var(--sinal); font: inherit; font-size: 13px; cursor: pointer; text-decoration: underline; }
    .alerta {
      display: grid; gap: 2px; text-align: left; font: inherit; cursor: pointer;
      padding: var(--space-2) var(--space-3); background: var(--superficie); color: var(--tinta);
      border: 1px solid var(--linha); border-left: 4px solid var(--linha-forte); border-radius: var(--radius-sm);
      &:hover { background: var(--superficie-2); }
      &.nao-lido { border-left-color: var(--critico); }
      &.resolvido { opacity: 0.7; }
    }
    .linha1 { display: flex; align-items: center; gap: var(--space-2); }
    .detalhe { font-size: 13px; color: var(--tinta-2); }
    .quando { font-size: 12px; color: var(--tinta-2); }
    .vazio { margin: 0; color: var(--tinta-2); font-size: 14px; }
    @media (max-width: 800px) { .painel { top: 64px; left: var(--space-4); } }
  `,
})
export class Sino {
  protected readonly servico = inject(AlertasService);
  private readonly router = inject(Router);
  private readonly elemento = inject(ElementRef<HTMLElement>);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly aberto = signal(false);

  /** Fecha ao clicar fora ou apertar Esc. */
  @HostListener('document:click', ['$event'])
  protected cliqueFora(e: MouseEvent): void {
    if (this.aberto() && !this.elemento.nativeElement.contains(e.target as Node)) this.aberto.set(false);
  }

  @HostListener('document:keydown.escape')
  protected esc(): void {
    this.aberto.set(false);
  }

  protected async abrir(a: Alerta): Promise<void> {
    this.aberto.set(false);
    if (!a.lido) void this.servico.marcarLidos([a.id]).catch(() => undefined);
    await this.router.navigateByUrl(a.link);
  }

  protected marcarTodos(): void {
    void this.servico.marcarLidos().catch(() => undefined);
  }
}
