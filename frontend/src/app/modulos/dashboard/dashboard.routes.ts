import { inject } from '@angular/core';
import { CanMatchFn, Router, Routes } from '@angular/router';

import { LayoutDsh } from './layout-dsh';
import { DshService } from './dsh.service';

/** Só abre a tela se a persona tiver a permissão (lista do servidor). A API é quem protege de fato (403). */
function exigir(permissao: 'lancar' | 'configurar'): CanMatchFn {
  return async () => {
    const router = inject(Router);
    try {
      return (await inject(DshService).carregarOpcoes()).permissoes[permissao] || router.createUrlTree(['/dashboard']);
    } catch {
      return router.createUrlTree(['/dashboard']);
    }
  };
}

export const ROTAS_DASHBOARD: Routes = [
  {
    path: '',
    component: LayoutDsh,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'painel' },
      {
        path: 'painel',
        title: 'Painel de indicadores · DSH',
        loadComponent: () => import('./paginas/painel').then((m) => m.PainelDsh),
      },
      {
        path: 'historico',
        title: 'Histórico · DSH',
        loadComponent: () => import('./paginas/historico').then((m) => m.HistoricoDsh),
      },
      {
        path: 'lancamentos',
        title: 'Metas e perdas · DSH',
        canMatch: [exigir('lancar')],
        loadComponent: () => import('./paginas/lancamentos').then((m) => m.Lancamentos),
      },
      {
        path: 'configuracao',
        title: 'Configuração · DSH',
        canMatch: [exigir('configurar')],
        loadComponent: () => import('./paginas/configuracao').then((m) => m.ConfiguracaoDsh),
      },
    ],
  },
];
