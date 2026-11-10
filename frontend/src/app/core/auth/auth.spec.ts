import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { Usuario } from '../modelos';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';
import { autenticadoGuard, moduloGuard, visitanteGuard } from './guards';

const ADMIN: Usuario = {
  id: 1,
  matricula: 'ADM-0001',
  nome: 'Ana Souza',
  perfil: 'Administrador',
  ativo: true,
  criado_em: '2026-11-10T00:00:00Z',
};

describe('Autenticação', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
  });

  afterEach(() => http.verify());

  async function logar(): Promise<void> {
    const promessa = auth.entrar('ADM-0001', 'amatech1234');
    http.expectOne('/api/auth/login').flush({ access_token: 'tok-123', token_type: 'bearer', usuario: ADMIN });
    await promessa;
  }

  function executarGuard<T>(fn: () => T): T {
    return TestBed.runInInjectionContext(fn);
  }

  it('entrar grava token e usuário na sessão', async () => {
    expect(auth.autenticado()).toBe(false);
    await logar();
    expect(auth.autenticado()).toBe(true);
    expect(auth.usuario()?.matricula).toBe('ADM-0001');
    expect(sessionStorage.getItem('amatech.token')).toBe('tok-123');
  });

  it('o login não envia Authorization; as outras chamadas enviam', async () => {
    const promessa = auth.entrar('ADM-0001', 'x');
    const reqLogin = http.expectOne('/api/auth/login');
    expect(reqLogin.request.headers.has('Authorization')).toBe(false);
    reqLogin.flush({ access_token: 'tok-123', token_type: 'bearer', usuario: ADMIN });
    await promessa;

    void firstValueFrom(TestBed.inject(HttpClient).get('/api/usuarios'));
    const req = http.expectOne('/api/usuarios');
    expect(req.request.headers.get('Authorization')).toBe('Bearer tok-123');
    req.flush([]);
  });

  it('401 numa chamada comum encerra a sessão e volta ao login', async () => {
    await logar();
    const chamada = firstValueFrom(TestBed.inject(HttpClient).get('/api/auth/me'));
    http.expectOne('/api/auth/me').flush({ detail: 'expirado' }, { status: 401, statusText: 'Unauthorized' });
    await expect(chamada).rejects.toBeTruthy();
    expect(auth.autenticado()).toBe(false);
    expect(sessionStorage.getItem('amatech.token')).toBeNull();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/login');
  });

  it('401 no próprio login (senha errada) não chama sair()', async () => {
    const sair = vi.spyOn(auth, 'sair');
    const promessa = auth.entrar('ADM-0001', 'errada');
    http.expectOne('/api/auth/login').flush({ detail: 'Matrícula ou senha incorreta.' }, { status: 401, statusText: 'x' });
    await expect(promessa).rejects.toBeTruthy();
    expect(sair).not.toHaveBeenCalled();
  });

  it('módulos vêm do servidor uma vez e ficam em cache', async () => {
    await logar();
    const p1 = auth.carregarModulos();
    http.expectOne('/api/auth/modulos').flush([{ id: 'usuarios', sigla: 'USR', nome: 'Usuários', descricao: '' }]);
    expect((await p1).map((m) => m.sigla)).toEqual(['USR']);
    expect(await auth.temModulo('usuarios')).toBe(true);
    expect(await auth.temModulo('manutencao')).toBe(false);
    http.expectNone('/api/auth/modulos');
  });

  it('autenticadoGuard manda visitante para /login; visitanteGuard manda logado para /', async () => {
    const r1 = executarGuard(() => autenticadoGuard({} as never, {} as never)) as UrlTree;
    expect(router.serializeUrl(r1)).toBe('/login');
    expect(executarGuard(() => visitanteGuard({} as never, {} as never))).toBe(true);

    await logar();
    expect(executarGuard(() => autenticadoGuard({} as never, {} as never))).toBe(true);
    const r2 = executarGuard(() => visitanteGuard({} as never, {} as never)) as UrlTree;
    expect(router.serializeUrl(r2)).toBe('/');
  });

  it('moduloGuard libera só os módulos da persona', async () => {
    await logar();
    const permitido = executarGuard(() => moduloGuard('usuarios')({} as never, [])) as Promise<boolean | UrlTree>;
    http.expectOne('/api/auth/modulos').flush([{ id: 'usuarios', sigla: 'USR', nome: 'Usuários', descricao: '' }]);
    expect(await permitido).toBe(true);

    const negado = (await executarGuard(() => moduloGuard('manutencao')({} as never, []))) as UrlTree;
    expect(router.serializeUrl(negado)).toBe('/');
  });
});
