import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { mensagemDeErro } from '../../core/erros';
import { PermissoesRas } from './ras.modelos';
import { RasService } from './ras.service';

interface Aba {
  rota: string;
  rotulo: string;
  /** Mostra a aba se a persona tiver qualquer uma destas permissões. */
  permissoes?: (keyof PermissoesRas)[];
}

const ABAS: Aba[] = [
  { rota: 'painel', rotulo: 'Painel' },
  { rota: 'producoes', rotulo: 'Produções' },
  { rota: 'materiais', rotulo: 'Materiais' },
  { rota: 'relatorios', rotulo: 'Relatórios' },
  { rota: 'cadastros', rotulo: 'Cadastros', permissoes: ['componentes', 'modelos_etapas'] },
];

/** Cabeçalho do módulo RAS + abas filtradas pelas permissões da persona. */
@Component({
  selector: 'am-layout-ras',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="topo">
      <div>
        <span class="selo-setor ras">RAS</span>
        <span class="titulo-modulo">Rastreabilidade e Materiais</span>
      </div>
      <nav class="abas" aria-label="Telas da rastreabilidade">
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
export class LayoutRas implements OnInit {
  private readonly ras = inject(RasService);
  protected readonly erro = signal<string | null>(null);

  protected readonly abas = computed(() => {
    const p = this.ras.opcoes()?.permissoes;
    return p ? ABAS.filter((a) => !a.permissoes || a.permissoes.some((k) => p[k])) : [];
  });

  ngOnInit(): void {
    this.ras.carregarOpcoes().catch((e) => this.erro.set(mensagemDeErro(e)));
  }
}
