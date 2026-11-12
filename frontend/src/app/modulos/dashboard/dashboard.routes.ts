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
        loadComponent: () => import('./paginas/painel').then((m) => m.PainelDsh),
        children: [
          { path: '', title: 'Visão geral · DSH', loadComponent: () => import('./paginas/aba-geral').then((m) => m.AbaGeral) },
          { path: 'producao', title: 'Produção · DSH', loadComponent: () => import('./paginas/aba-producao').then((m) => m.AbaProducao) },
          { path: 'qualidade', title: 'Qualidade · DSH', loadComponent: () => import('./paginas/aba-qualidade').then((m) => m.AbaQualidade) },
          { path: 'manutencao', title: 'Manutenção · DSH', loadComponent: () => import('./paginas/aba-manutencao').then((m) => m.AbaManutencao) },
          { path: 'materiais', title: 'Materiais · DSH', loadComponent: () => import('./paginas/aba-materiais').then((m) => m.AbaMateriais) },
        ],
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
