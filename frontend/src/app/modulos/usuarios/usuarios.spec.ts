import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Usuario } from '../../core/modelos';
import { Usuarios } from './usuarios';

const LISTA: Usuario[] = [
  { id: 1, matricula: 'ADM-0001', nome: 'Ana Souza', perfil: 'Administrador', ativo: true, criado_em: '2026-11-10T00:00:00Z' },
  { id: 2, matricula: 'OPE-0001', nome: 'João Silva', perfil: 'Operador de Produção', ativo: true, criado_em: '2026-11-10T00:00:00Z' },
];

describe('Usuarios (USR)', () => {
  let fixture: ComponentFixture<Usuarios>;
  let http: HttpTestingController;
  let el: HTMLElement;

  beforeEach(async () => {
    sessionStorage.clear();
    sessionStorage.setItem('amatech.token', 't');
    sessionStorage.setItem('amatech.usuario', JSON.stringify(LISTA[0]));
    TestBed.configureTestingModule({
      imports: [Usuarios],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Usuarios);
    el = fixture.nativeElement;
    fixture.detectChanges();
    http.expectOne('/api/usuarios').flush(LISTA);
    await estabilizar();
  });

  afterEach(() => http.verify());

  // Espera as promessas do componente (firstValueFrom) e a renderização que elas disparam.
  async function estabilizar(): Promise<void> {
    await new Promise((r) => setTimeout(r));
    await fixture.whenStable();
  }

  function botao(texto: string): HTMLButtonElement[] {
    return [...el.querySelectorAll('button')].filter((b) => b.textContent?.trim() === texto);
  }

  it('lista os usuários e marca a própria conta', () => {
    const linhas = el.querySelectorAll('tbody tr');
    expect(linhas.length).toBe(2);
    expect(linhas[0].textContent).toContain('(você)');
  });

  it('não deixa o administrador desativar a própria conta', () => {
    const [desativarProprio, desativarOutro] = botao('Desativar');
    expect(desativarProprio.disabled).toBe(true);
    expect(desativarOutro.disabled).toBe(false);
  });

  it('busca filtra pela matrícula, nome ou persona', async () => {
    const busca = el.querySelector<HTMLInputElement>('input[type=search]')!;
    busca.value = 'operador';
    busca.dispatchEvent(new Event('input'));
    await estabilizar();
    expect(el.querySelectorAll('tbody tr').length).toBe(1);
    expect(el.textContent).toContain('1 de 2');
  });

  it('desativar chama PATCH e atualiza a etiqueta', async () => {
    botao('Desativar')[1].click();
    const req = http.expectOne('/api/usuarios/2');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ ativo: false });
    req.flush({ ...LISTA[1], ativo: false });
    await estabilizar();
    expect(el.querySelectorAll('tbody tr')[1].textContent).toContain('Inativo');
    expect(el.textContent).toContain('Conta OPE-0001 desativada.');
  });

  it('criar usuário envia matrícula nula quando em branco e mostra erro da API', async () => {
    botao('Novo usuário')[0].click();
    await estabilizar();
    const form = el.querySelector<HTMLFormElement>('form')!;
    const [nome, senha] = [form.querySelector<HTMLInputElement>('[formcontrolname=nome]')!, form.querySelector<HTMLInputElement>('[formcontrolname=senha]')!];
    nome.value = 'Paula';
    nome.dispatchEvent(new Event('input'));
    senha.value = 'senha-forte-1';
    senha.dispatchEvent(new Event('input'));
    form.dispatchEvent(new Event('submit'));

    const req = http.expectOne('/api/usuarios');
    expect(req.request.body).toEqual({ nome: 'Paula', perfil: 'Operador de Produção', senha: 'senha-forte-1', matricula: null });
    req.flush({ detail: "A matrícula 'OPE-0002' já está cadastrada." }, { status: 409, statusText: 'Conflict' });
    await estabilizar();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('já está cadastrada');
  });

  it('senha curta não chega a ir para a API', async () => {
    botao('Novo usuário')[0].click();
    await estabilizar();
    el.querySelector<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'));
    await estabilizar();
    http.expectNone('/api/usuarios');
    expect(el.querySelector('[formcontrolname=senha]')?.getAttribute('aria-invalid')).toBe('true');
  });
});
