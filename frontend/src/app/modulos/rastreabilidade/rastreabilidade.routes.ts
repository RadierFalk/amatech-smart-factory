import { inject } from '@angular/core';
import { CanMatchFn, Router, Routes } from '@angular/router';

import { LayoutRas } from './layout-ras';
import { PermissoesRas } from './ras.modelos';
import { RasService } from './ras.service';

/** Só abre a tela se a persona tiver alguma das permissões (lista do servidor). A API é quem protege de fato. */
function exigirAlguma(...permissoes: (keyof PermissoesRas)[]): CanMatchFn {
  return async () => {
    const router = inject(Router);
    try {
      const p = (await inject(RasService).carregarOpcoes()).permissoes;
      return permissoes.some((k) => p[k]) || router.createUrlTree(['/rastreabilidade']);
    } catch {
      return router.createUrlTree(['/rastreabilidade']);
    }
  };
}

export const ROTAS_RASTREABILIDADE: Routes = [
  {
    path: '',
    component: LayoutRas,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'painel' },
      {
        path: 'painel',
        title: 'Painel da produção · RAS',
        loadComponent: () => import('./paginas/painel').then((m) => m.PainelRas),
      },
      {
        path: 'producoes',
        title: 'Produções · RAS',
        loadComponent: () => import('./paginas/producoes').then((m) => m.Producoes),
      },
      {
        path: 'producoes/:id',
        title: 'Produção · RAS',
        loadComponent: () => import('./paginas/producao-detalhe').then((m) => m.ProducaoDetalheTela),
      },
      {
        path: 'materiais',
        title: 'Materiais · RAS',
        loadComponent: () => import('./paginas/materiais').then((m) => m.Materiais),
      },
      {
        path: 'relatorios',
        title: 'Relatórios · RAS',
        loadComponent: () => import('./paginas/relatorios').then((m) => m.RelatoriosRas),
      },
      {
        path: 'cadastros',
        title: 'Cadastros · RAS',
        canMatch: [exigirAlguma('componentes', 'modelos_etapas')],
        loadComponent: () => import('./paginas/cadastros').then((m) => m.CadastrosRas),
      },
    ],
  },
];
