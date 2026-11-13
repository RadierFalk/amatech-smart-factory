import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { Alerta, AlertasService } from './alertas.service';
import { Sino } from './sino';

function alerta(a: Partial<Alerta> = {}): Alerta {
  return {
    id: 1, tipo: 'CHAMADO_ABERTO', modulo: 'MNT', titulo: 'OS #9 aberta: TEST-03', detalhe: 'Prioridade alta · Tela com linhas',
    link: '/manutencao/ordens/9', ativo: true, lido: false, criado_em: '2026-11-13T13:01:00Z', resolvido_em: null, ...a,
  };
}

async function esperar(f: ComponentFixture<unknown>): Promise<void> {
  await new Promise((r) => setTimeout(r));
  await f.whenStable();
  f.detectChanges();
}

describe('Sino de alertas', () => {
  let http: HttpTestingController;
  let servico: AlertasService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    servico = TestBed.inject(AlertasService);
  });

  afterEach(() => {
    servico.parar();
    http.verify();
  });

  async function abrirComAlertas(lista: Alerta[], naoLidos: number) {
    const f = TestBed.createComponent(Sino);
    servico.iniciar();
    http.expectOne('/api/alertas').flush({ nao_lidos: naoLidos, alertas: lista });
    await esperar(f);
    return f;
  }

  it('mostra o número de não lidos com texto para leitor de tela', async () => {
    const f = await abrirComAlertas([alerta(), alerta({ id: 2, ativo: false, lido: false, titulo: 'BAT-45WH sem estoque suficiente' })], 1);
    const botao: HTMLButtonElement = f.nativeElement.querySelector('.sino');
    expect(botao.getAttribute('aria-label')).toBe('Alertas: 1 não lido(s)');
    expect(botao.querySelector('.contador')!.textContent).toBe('1');
    botao.click();
    f.detectChanges();
    const itens = [...f.nativeElement.querySelectorAll('.alerta')].map((e: Element) => e.textContent!.replace(/\s+/g, ' '));
    expect(itens[0]).toContain('OS #9 aberta: TEST-03');
    expect(itens[0]).toContain('Novo');
    expect(itens[1]).toContain('Resolvido');
  });

  it('clicar no alerta marca como lido e leva até onde agir', async () => {
    const f = await abrirComAlertas([alerta()], 1);
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    f.nativeElement.querySelector('.sino').click();
    f.detectChanges();
    f.nativeElement.querySelector('.alerta').click();
    const req = http.expectOne('/api/alertas/lidos');
    expect(req.request.body).toEqual({ ids: [1] });
    req.flush(null);
    await esperar(f);
    expect(navegar).toHaveBeenCalledWith('/manutencao/ordens/9');
    expect(servico.naoLidos()).toBe(0);
  });

  it('sem alertas, avisa que não há nada', async () => {
    const f = await abrirComAlertas([], 0);
    f.nativeElement.querySelector('.sino').click();
    f.detectChanges();
    expect(f.nativeElement.textContent).toContain('Nenhum alerta para o seu perfil agora.');
    expect(f.nativeElement.querySelector('.contador')).toBeNull();
  });
});
