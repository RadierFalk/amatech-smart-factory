import { inject } from '@angular/core';
import { CanMatchFn, Router, Routes } from '@angular/router';

import { LayoutQld } from './layout-qld';
import { PermissoesQld } from './qld.modelos';
import { QldService } from './qld.service';

/** Só abre a tela se a persona tiver a permissão (lista do servidor). A API é quem protege de fato (403). */
function exigir(permissao: keyof PermissoesQld): CanMatchFn {
  return async () => {
    const router = inject(Router);
    try {
      return (await inject(QldService).pode(permissao)) || router.createUrlTree(['/qualidade']);
    } catch {
      return router.createUrlTree(['/qualidade']);
    }
  };
}

export const ROTAS_QUALIDADE: Routes = [
  {
    path: '',
    component: LayoutQld,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'painel' },
      {
        path: 'painel',
        title: 'Painel da qualidade · QLD',
        loadComponent: () => import('./paginas/painel').then((m) => m.PainelQld),
      },
      {
        path: 'registrar',
        title: 'Registrar ocorrência · QLD',
        canMatch: [exigir('registrar')],
        loadComponent: () => import('./paginas/formulario-ocorrencia').then((m) => m.FormularioOcorrencia),
      },
      {
        path: 'ocorrencias/:id/editar',
        title: 'Editar ocorrência · QLD',
        canMatch: [exigir('editar')],
        loadComponent: () => import('./paginas/formulario-ocorrencia').then((m) => m.FormularioOcorrencia),
      },
      {
        path: 'historico',
        title: 'Histórico de ocorrências · QLD',
        loadComponent: () => import('./paginas/historico').then((m) => m.HistoricoQld),
      },
      {
        path: 'cadastros',
        title: 'Cadastros · QLD',
        canMatch: [exigir('cadastros')],
        loadComponent: () => import('./paginas/cadastros').then((m) => m.CadastrosQld),
      },
    ],
  },
];
