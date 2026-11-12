import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';

/** Seletor de módulos pós-login: só aparecem os módulos da persona (lista do servidor). */
@Component({
  selector: 'am-hub',
  imports: [RouterLink],
  template: `
    <div class="pagina">
      <div>
        <div class="rotulo">ERP AMATECH</div>
        <h1 class="titulo-tela">Olá, {{ primeiroNome() }}</h1>
        <p class="legenda">Escolha um módulo. Você vê apenas os habilitados para o perfil {{ auth.usuario()?.perfil }}.</p>
      </div>

      <div class="grade">
        @for (m of auth.modulos() ?? []; track m.id) {
          <a class="cartao modulo" [routerLink]="'/' + m.id">
            <span class="selo-setor" [class]="m.sigla.toLowerCase()">{{ m.sigla }}</span>
            <h2 class="titulo-secao">{{ m.nome }}</h2>
            <p class="legenda">{{ m.descricao }}</p>
          </a>
        } @empty {
          <p class="legenda">Carregando módulos…</p>
        }
      </div>
    </div>
  `,
  styles: `
    .grade {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: var(--space-4);
    }
    .modulo {
      display: grid;
      align-content: start;
      gap: var(--space-2);
      color: inherit;
      text-decoration: none;
      transition: border-color 0.15s;
      &:hover { border-color: var(--sinal); }
      p { margin: 0; }
    }
    .selo-setor { justify-self: start; }
  `,
})
export class Hub {
  protected readonly auth = inject(AuthService);

  protected primeiroNome(): string {
    return this.auth.usuario()?.nome.split(' ')[0] ?? '';
  }
}
