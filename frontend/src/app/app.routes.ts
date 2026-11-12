import { Routes } from '@angular/router';

import { autenticadoGuard, moduloGuard, visitanteGuard } from './core/auth/guards';
import { Shell } from './layout/shell';

export const routes: Routes = [
  {
    path: 'login',
    title: 'Entrar · ERP AMATECH',
    canActivate: [visitanteGuard],
    loadComponent: () => import('./paginas/login/login').then((m) => m.Login),
  },
  {
    path: '',
    component: Shell,
    canActivate: [autenticadoGuard],
    children: [
      {
        path: '',
        title: 'Módulos · ERP AMATECH',
        loadComponent: () => import('./paginas/hub/hub').then((m) => m.Hub),
      },
      {
        path: 'usuarios',
        title: 'Usuários · ERP AMATECH',
        canMatch: [moduloGuard('usuarios')],
        loadComponent: () => import('./modulos/usuarios/usuarios').then((m) => m.Usuarios),
      },
      {
        path: 'rastreabilidade',
        title: 'Rastreabilidade · ERP AMATECH',
        canMatch: [moduloGuard('rastreabilidade')],
        loadChildren: () => import('./modulos/rastreabilidade/rastreabilidade.routes').then((m) => m.ROTAS_RASTREABILIDADE),
      },
      {
        path: 'qualidade',
        title: 'Qualidade · ERP AMATECH',
        canMatch: [moduloGuard('qualidade')],
        loadChildren: () => import('./modulos/qualidade/qualidade.routes').then((m) => m.ROTAS_QUALIDADE),
      },
      {
        path: 'manutencao',
        title: 'Manutenção · ERP AMATECH',
        canMatch: [moduloGuard('manutencao')],
        loadChildren: () => import('./modulos/manutencao/manutencao.routes').then((m) => m.ROTAS_MANUTENCAO),
      },
      {
        path: 'dashboard',
        title: 'Dashboard · ERP AMATECH',
        canMatch: [moduloGuard('dashboard')],
        loadChildren: () => import('./modulos/dashboard/dashboard.routes').then((m) => m.ROTAS_DASHBOARD),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
