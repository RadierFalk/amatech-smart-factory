import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../core/auth/auth.service';
import { Marca } from '../shared/marca';

/** Casca de todas as telas autenticadas: barra lateral `noite` com usuário, módulos e saída. */
@Component({
  selector: 'am-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Marca],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell implements OnInit {
  protected readonly auth = inject(AuthService);
  protected readonly menuAberto = signal(false);

  ngOnInit(): void {
    // Erros (ex.: 401) já são tratados pelo interceptor; aqui só evitamos promessa sem catch.
    this.auth.carregarModulos().catch(() => undefined);
  }

  protected alternarMenu(): void {
    this.menuAberto.update((v) => !v);
  }

  protected fecharMenu(): void {
    this.menuAberto.set(false);
  }
}
