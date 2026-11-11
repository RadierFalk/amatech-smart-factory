import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { mensagemDeErro } from '../../core/erros';
import { PermissoesMnt } from './mnt.modelos';
import { MntService } from './mnt.service';

interface Aba {
  rota: string;
  rotulo: string;
  permissao?: keyof PermissoesMnt;
}

const GRUPOS: { titulo: string; abas: Aba[] }[] = [
  {
    titulo: 'Operação',
    abas: [
      { rota: 'painel', rotulo: 'Painel de máquinas' },
      { rota: 'abrir', rotulo: 'Abrir chamado', permissao: 'abrir_chamado' },
      { rota: 'meus-chamados', rotulo: 'Meus chamados', permissao: 'abrir_chamado' },
    ],
  },
  {
    titulo: 'Manutenção técnica',
    abas: [
      { rota: 'fila', rotulo: 'Fila', permissao: 'atender' },
      { rota: 'ordens', rotulo: 'Ordens de serviço', permissao: 'atender' },
      { rota: 'preventivas', rotulo: 'Preventivas', permissao: 'atender' },
    ],
  },
  {
    titulo: 'Gestão',
    abas: [
      { rota: 'indicadores', rotulo: 'Indicadores', permissao: 'indicadores' },
      { rota: 'historico', rotulo: 'Histórico', permissao: 'indicadores' },
      { rota: 'cadastros', rotulo: 'Cadastros', permissao: 'cadastros' },
      { rota: 'auditoria', rotulo: 'Auditoria', permissao: 'indicadores' },
    ],
  },
];

/** Cabeçalho do módulo MNT + abas agrupadas, filtradas pelas permissões da persona. */
@Component({
  selector: 'am-layout-mnt',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="topo">
      <div>
        <span class="selo-setor mnt">MNT</span>
        <span class="titulo-modulo">Gestão da Manutenção de Ativos</span>
      </div>
      <nav class="abas" aria-label="Telas da manutenção">
        @for (g of grupos(); track g.titulo) {
          <div class="grupo">
            <span class="rotulo">{{ g.titulo }}</span>
            <div class="links">
              @for (a of g.abas; track a.rota) {
                <a [routerLink]="a.rota" routerLinkActive="ativa">{{ a.rotulo }}</a>
              }
            </div>
          </div>
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
    .abas { display: flex; flex-wrap: wrap; gap: var(--space-6); }
    .grupo { display: grid; gap: 2px; }
    .links { display: flex; flex-wrap: wrap; }
    .links a {
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
export class LayoutMnt implements OnInit {
  private readonly mnt = inject(MntService);
  protected readonly erro = signal<string | null>(null);

  protected readonly grupos = computed(() => {
    const p = this.mnt.opcoes()?.permissoes;
    if (!p) return [];
    return GRUPOS.map((g) => ({ ...g, abas: g.abas.filter((a) => !a.permissao || p[a.permissao]) })).filter(
      (g) => g.abas.length > 0,
    );
  });

  ngOnInit(): void {
    this.mnt.carregarOpcoes().catch((e) => this.erro.set(mensagemDeErro(e)));
  }
}
