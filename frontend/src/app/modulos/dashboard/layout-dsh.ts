import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { mensagemDeErro } from '../../core/erros';
import { DshService } from './dsh.service';

/** Abas do painel: uma visão geral e uma por setor. */
const SETORES = [
  { rota: 'painel', rotulo: 'Visão geral', exata: true },
  { rota: 'painel/producao', rotulo: 'Produção', exata: false },
  { rota: 'painel/qualidade', rotulo: 'Qualidade', exata: false },
  { rota: 'painel/manutencao', rotulo: 'Manutenção', exata: false },
  { rota: 'painel/materiais', rotulo: 'Materiais', exata: false },
];

/** Outras telas do módulo, filtradas pelas permissões da persona. */
const OUTRAS = [
  { rota: 'historico', rotulo: 'Histórico' },
  { rota: 'lancamentos', rotulo: 'Metas e perdas', permissao: 'lancar' as const },
  { rota: 'configuracao', rotulo: 'Configuração', permissao: 'configurar' as const },
];

/** Cabeçalho do módulo DSH: abas dos setores à esquerda, demais telas à direita. */
@Component({
  selector: 'am-layout-dsh',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="topo">
      <div>
        <span class="selo-setor dsh">DSH</span>
        <span class="titulo-modulo">Dashboard Industrial e Metas</span>
      </div>
      <div class="navs">
        <nav class="abas" aria-label="Abas do painel">
          @for (a of setores; track a.rota) {
            <a [routerLink]="a.rota" routerLinkActive="ativa" [routerLinkActiveOptions]="{ exact: a.exata }" ariaCurrentWhenActive="page">{{ a.rotulo }}</a>
          }
        </nav>
        <nav class="outras" aria-label="Outras telas do dashboard">
          @for (a of outras(); track a.rota) {
            <a [routerLink]="a.rota" routerLinkActive="ativa" ariaCurrentWhenActive="page">{{ a.rotulo }}</a>
          }
        </nav>
      </div>
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
    .navs { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: var(--space-2); }
    .abas, .outras { display: flex; flex-wrap: wrap; }
    .abas a {
      padding: var(--space-2) var(--space-3);
      color: var(--tinta-2);
      text-decoration: none;
      border-bottom: 3px solid transparent;
      font-weight: 600;
      &:hover { color: var(--tinta); }
      &.ativa { color: var(--sinal); border-bottom-color: var(--sinal); }
    }
    .outras { gap: var(--space-1); padding-bottom: var(--space-2); }
    .outras a {
      padding: var(--space-1) var(--space-2);
      font-size: 13px;
      color: var(--tinta-2);
      text-decoration: none;
      border-radius: var(--radius-sm);
      &:hover { color: var(--tinta); background: var(--superficie-2); }
      &.ativa { color: var(--sinal); background: var(--sinal-suave); font-weight: 600; }
    }
  `,
})
export class LayoutDsh implements OnInit {
  private readonly dsh = inject(DshService);
  protected readonly erro = signal<string | null>(null);
  protected readonly setores = SETORES;

  protected readonly outras = computed(() => {
    const p = this.dsh.opcoes()?.permissoes;
    return p ? OUTRAS.filter((a) => !a.permissao || p[a.permissao]) : [];
  });

  ngOnInit(): void {
    this.dsh.carregarOpcoes().catch((e) => this.erro.set(mensagemDeErro(e)));
  }
}
