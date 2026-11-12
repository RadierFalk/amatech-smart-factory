import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { mensagemDeErro } from '../../core/erros';
import { DshService } from './dsh.service';

const ABAS = [
  { rota: 'painel', rotulo: 'Painel' },
  { rota: 'historico', rotulo: 'Histórico' },
  { rota: 'lancamentos', rotulo: 'Metas e perdas', permissao: 'lancar' as const },
  { rota: 'configuracao', rotulo: 'Configuração', permissao: 'configurar' as const },
];

/** Cabeçalho do módulo DSH + abas filtradas pelas permissões da persona. */
@Component({
  selector: 'am-layout-dsh',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="topo">
      <div>
        <span class="selo-setor dsh">DSH</span>
        <span class="titulo-modulo">Dashboard Industrial e Metas</span>
      </div>
      <nav class="abas" aria-label="Telas do dashboard">
        @for (a of abas(); track a.rota) {
          <a [routerLink]="a.rota" routerLinkActive="ativa">{{ a.rotulo }}</a>
        }
      </nav>
    </div>
    @if (erro(); as m) {
      <div class="pagina"><div class="aviso erro" role="alert">{{ m }}</div></div>
    }
    <router-outlet />
  `,
  styles: `
    .topo {
      background: var(--superficie);
      border-bottom: 1px solid var(--linha);
      padding: var(--space-4) var(--space-6) 0;
      display: grid;
      gap: var(--space-3);
    }
    .titulo-modulo { margin-left: var(--space-2); font-weight: 600; }
    .abas { display: flex; flex-wrap: wrap; }
    .abas a {
      padding: var(--space-2) var(--space-3);
      color: var(--tinta-2);
      text-decoration: none;
      border-bottom: 3px solid transparent;
      font-weight: 600;
      &:hover { color: var(--tinta); }
      &.ativa { color: var(--sinal); border-bottom-color: var(--sinal); }
    }
  `,
})
export class LayoutDsh implements OnInit {
  private readonly dsh = inject(DshService);
  protected readonly erro = signal<string | null>(null);

  protected readonly abas = computed(() => {
    const p = this.dsh.opcoes()?.permissoes;
    return p ? ABAS.filter((a) => !a.permissao || p[a.permissao]) : [];
  });

  ngOnInit(): void {
    this.dsh.carregarOpcoes().catch((e) => this.erro.set(mensagemDeErro(e)));
  }
}
