import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Auditoria, RegistroAuditoria, nomeDoCampo, valorLegivel } from './auditoria';

function registro(r: Partial<RegistroAuditoria> = {}): RegistroAuditoria {
  return {
    id: 1, registrada_em: '2026-11-13T13:01:00Z', usuario_matricula: 'QUA-0001', usuario_nome: 'Maria', modulo: 'QLD',
    entidade: 'qld.ocorrencias', entidade_id: '17', descricao: 'Ocorrência #17', acao: 'ALTEROU',
    alteracoes: { status: ['ABERTA', 'RESOLVIDA'], oculta: [false, true] }, ...r,
  };
}

async function esperar(f: ComponentFixture<unknown>): Promise<void> {
  await new Promise((r) => setTimeout(r));
  await f.whenStable();
  f.detectChanges();
}

describe('Auditoria', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('mostra quem fez, a ação com texto e o antes e depois de cada campo', async () => {
    const f = TestBed.createComponent(Auditoria);
    f.detectChanges();
    const req = http.expectOne((r) => r.url === '/api/auditoria');
    expect(req.request.params.get('limite')).toBe('200');
    expect(req.request.params.get('de')).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    req.flush([registro(), registro({ id: 2, usuario_nome: null, usuario_matricula: null, acao: 'CRIOU', alteracoes: { nome: [null, 'SMT'] } })]);
    await esperar(f);
    const linhas = [...f.nativeElement.querySelectorAll('tbody tr')] as HTMLElement[];
    expect(linhas[0].textContent).toContain('Maria');
    expect(linhas[0].textContent).toContain('Alterou');
    expect(linhas[0].textContent).toContain('ABERTA');
    expect(linhas[0].textContent).toContain('RESOLVIDA');
    expect(linhas[0].textContent).toContain('Não');
    expect(linhas[0].querySelector('summary')!.textContent).toContain('2 campo(s)');
    expect(linhas[1].textContent).toContain('Sistema');
    expect(linhas[1].querySelector('.antes')).toBeNull(); // na criação não há "antes"
  });

  it('filtros vão como parâmetros da consulta', async () => {
    const f = TestBed.createComponent(Auditoria);
    f.detectChanges();
    http.expectOne((r) => r.url === '/api/auditoria').flush([]);
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    const modulo = el.querySelector<HTMLSelectElement>('select[name=modulo]')!;
    modulo.value = 'MNT';
    modulo.dispatchEvent(new Event('change'));
    const busca = el.querySelector<HTMLInputElement>('input[name=busca]')!;
    busca.value = ' OS #9 ';
    busca.dispatchEvent(new Event('input'));
    el.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    const req = http.expectOne((r) => r.url === '/api/auditoria');
    expect(req.request.params.get('modulo')).toBe('MNT');
    expect(req.request.params.get('busca')).toBe('OS #9');
    req.flush([]);
    await esperar(f);
    expect(el.textContent).toContain('Nada registrado com esses filtros.');
  });

  it('valores e campos legíveis', () => {
    expect(valorLegivel(null)).toBe('—');
    expect(valorLegivel(true)).toBe('Sim');
    expect(valorLegivel('2026-11-13T13:01:00+00:00')).toBe('13/11/2026 09:01');
    expect(nomeDoCampo('tipo_defeito_id')).toBe('Tipo defeito id');
  });
});
