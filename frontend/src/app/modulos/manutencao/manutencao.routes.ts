import { inject } from '@angular/core';
import { CanMatchFn, Router, Routes } from '@angular/router';

import { PermissoesMnt } from './mnt.modelos';
import { MntService } from './mnt.service';
import { LayoutMnt } from './layout-mnt';

/** Só abre a tela se a persona tiver a permissão (lista do servidor). A API é quem protege de fato (403). */
function exigir(permissao: keyof PermissoesMnt): CanMatchFn {
  return async () => {
    const router = inject(Router);
    try {
      return (await inject(MntService).pode(permissao)) || router.createUrlTree(['/manutencao']);
    } catch {
      return router.createUrlTree(['/manutencao']);
    }
  };
}

export const ROTAS_MANUTENCAO: Routes = [
  {
    path: '',
    component: LayoutMnt,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'painel' },
      {
        path: 'painel',
        title: 'Painel de máquinas · MNT',
        loadComponent: () => import('./paginas/painel').then((m) => m.Painel),
      },
      {
        path: 'abrir',
        title: 'Abrir chamado · MNT',
        canMatch: [exigir('abrir_chamado')],
        loadComponent: () => import('./paginas/abrir-chamado').then((m) => m.AbrirChamado),
      },
      {
        path: 'meus-chamados',
        title: 'Meus chamados · MNT',
        canMatch: [exigir('abrir_chamado')],
        loadComponent: () => import('./paginas/meus-chamados').then((m) => m.MeusChamados),
      },
      {
        path: 'fila',
        title: 'Fila de chamados · MNT',
        canMatch: [exigir('atender')],
        loadComponent: () => import('./paginas/fila').then((m) => m.Fila),
      },
      {
        path: 'ordens',
        title: 'Ordens de serviço · MNT',
        canMatch: [exigir('atender')],
        loadComponent: () => import('./paginas/ordens').then((m) => m.Ordens),
      },
      {
        path: 'ordens/:id',
        title: 'Ordem de serviço · MNT',
        loadComponent: () => import('./paginas/ordem-servico').then((m) => m.OrdemServico),
      },
      {
        path: 'preventivas',
        title: 'Preventivas · MNT',
        canMatch: [exigir('atender')],
        loadComponent: () => import('./paginas/preventivas').then((m) => m.Preventivas),
      },
      {
        path: 'indicadores',
        title: 'Indicadores · MNT',
        canMatch: [exigir('indicadores')],
        loadComponent: () => import('./paginas/indicadores').then((m) => m.IndicadoresMnt),
      },
      {
        path: 'historico',
        title: 'Histórico · MNT',
        canMatch: [exigir('indicadores')],
        loadComponent: () => import('./paginas/historico').then((m) => m.Historico),
      },
      {
        path: 'cadastros',
        title: 'Cadastros · MNT',
        canMatch: [exigir('cadastros')],
        loadComponent: () => import('./paginas/cadastros').then((m) => m.Cadastros),
      },
      {
        path: 'auditoria',
        title: 'Auditoria · MNT',
        canMatch: [exigir('indicadores')],
        loadComponent: () => import('./paginas/auditoria').then((m) => m.AuditoriaMnt),
      },
    ],
  },
];
