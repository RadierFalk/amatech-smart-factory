import { inject } from '@angular/core';
import { CanActivateFn, CanMatchFn, Router } from '@angular/router';

import { IdModulo } from '../modelos';
import { AuthService } from './auth.service';

/** Só entra quem está logado; os outros vão para o login. */
export const autenticadoGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.autenticado() || inject(Router).createUrlTree(['/login']);
};

/** A tela de login não faz sentido para quem já está logado. */
export const visitanteGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return !auth.autenticado() || inject(Router).createUrlTree(['/']);
};

/**
 * Só carrega o módulo se a persona tiver acesso (lista vinda do servidor).
 * É conveniência de navegação: quem protege os dados de verdade é a API, que responde 403.
 */
export function moduloGuard(id: IdModulo): CanMatchFn {
  return async () => {
    const router = inject(Router);
    try {
      return (await inject(AuthService).temModulo(id)) || router.createUrlTree(['/']);
    } catch {
      return router.createUrlTree(['/']);
    }
  };
}
