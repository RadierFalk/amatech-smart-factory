import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { mensagemDeErro } from '../../core/erros';
import { PermissoesQld } from './qld.modelos';
import { QldService } from './qld.service';

interface Aba {
  rota: string;
  rotulo: string;
  permissao?: keyof PermissoesQld;
}

const ABAS: Aba[] = [
  { rota: 'painel', rotulo: 'Painel' },
  { rota: 'registrar', rotulo: 'Registrar ocorrência', permissao: 'registrar' },
  { rota: 'historico', rotulo: 'Histórico' },
  { rota: 'cadastros', rotulo: 'Cadastros', permissao: 'cadastros' },
];

/** Cabeçalho do módulo QLD + abas filtradas pelas permissões da persona. */
@Component({
  selector: 'am-layout-qld',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="topo">
      <div>
        <span class="selo-setor qld">QLD</span>
        <span class="titulo-modulo">Controle da Qualidade e Defeitos</span>
      </div>
      <nav class="abas" aria-label="Telas da qualidade">
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
export class LayoutQld implements OnInit {
  private readonly qld = inject(QldService);
  protected readonly erro = signal<string | null>(null);

  protected readonly abas = computed(() => {
    const p = this.qld.opcoes()?.permissoes;
    return p ? ABAS.filter((a) => !a.permissao || p[a.permissao]) : [];
  });

  ngOnInit(): void {
    this.qld.carregarOpcoes().catch((e) => this.erro.set(mensagemDeErro(e)));
  }
}
