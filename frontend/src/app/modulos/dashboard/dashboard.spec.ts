import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Usuario } from '../../core/modelos';
import { BarrasHorizontais } from '../../shared/graficos';
import { OpcoesDsh, Painel, somarDias } from './dsh.modelos';
import { LayoutDsh } from './layout-dsh';
import { csv } from './paginas/historico';
import { Lancamentos } from './paginas/lancamentos';
import { PainelDsh } from './paginas/painel';

const SUPERVISOR: Usuario = { id: 2, matricula: 'GES-0001', nome: 'Orlando', perfil: 'Supervisor / Gestor', ativo: true, criado_em: '' };

function opcoes(gestao: boolean): OpcoesDsh {
  return {
    turnos: [{ id: 1, nome: '1º turno', hora_inicio: '06:00', hora_fim: '14:00', duracao_min: 480 },
             { id: 2, nome: '2º turno', hora_inicio: '14:00', hora_fim: '22:00', duracao_min: 480 }],
    modelos: [{ id: 1, nome: 'AMT N14', codigo: 'N14-I5-8-256' }],
    estacoes: [{ id: 3, nome: 'Montagem Final' }],
    tipos_perda: [{ id: 1, nome: 'Componente danificado', ativo: true }],
    limites: [],
    hoje: '2026-08-15',
    permissoes: { lancar: gestao, configurar: gestao },
  };
}

function painel(p: Partial<Painel> = {}): Painel {
  return {
    periodo: { de: '2026-08-09', ate: '2026-08-15' },
    producao: { realizada: 1420, aprovada: 1360, reprovada: 60, meta: 1500 },
    atendimento_meta: { valor: 94.7, semaforo: 'amarelo' },
    indice_defeitos: { valor: 4.2, semaforo: 'amarelo' },
    indice_retrabalho: { valor: 0, retrabalho: 0, semaforo: 'verde' },
    produtividade: { valor: 215.7, minutos_turno: 480, minutos_produtivos: 395 },
    tempo_parada: { minutos: 85, paradas: 1, em_andamento: 0 },
    perdas: { total: 8, por_tipo: [{ rotulo: 'Componente danificado', quantidade: 8 }] },
    graficos: {
      producao_x_meta: [{ modelo: 'AMT N14', realizada: 1420, meta: 1500 }],
      producao_por_dia: [{ data: '2026-08-15', realizada: 1420, meta: 1500 }],
      defeitos_por_estacao: [], retrabalho_por_estacao: [], parada_por_turno: [{ rotulo: '1º turno', minutos: 85 }],
    },
    paradas_em_andamento: [],
    ...p,
  };
}

async function esperar(fixture: ComponentFixture<unknown>): Promise<void> {
  await new Promise((r) => setTimeout(r));
  await fixture.whenStable();
}

describe('Dashboard', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('amatech.token', 't');
    sessionStorage.setItem('amatech.usuario', JSON.stringify(SUPERVISOR));
    TestBed.configureTestingModule({ providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('menu mostra Metas e perdas e Configuração só para a gestão', async () => {
    const f = TestBed.createComponent(LayoutDsh);
    f.detectChanges();
    http.expectOne('/api/dsh/opcoes').flush(opcoes(false));
    await esperar(f);
    const abas = [...f.nativeElement.querySelectorAll('.abas a')].map((a: Element) => a.textContent!.trim());
    expect(abas).toEqual(['Painel', 'Histórico']);
  });

  async function abrirPainel(dados: Painel) {
    const f = TestBed.createComponent(PainelDsh);
    f.detectChanges();
    http.expectOne('/api/dsh/opcoes').flush(opcoes(true));
    await esperar(f);
    // Período padrão: 7 dias terminando no "hoje" do servidor (dia da fábrica), não no relógio do navegador.
    const req = http.expectOne((r) => r.url === '/api/dsh/painel');
    expect(req.request.params.get('de')).toBe('2026-08-09');
    expect(req.request.params.get('ate')).toBe('2026-08-15');
    req.flush(dados);
    await esperar(f);
    return f;
  }

  it('cartões mostram valor no formato brasileiro e o semáforo com texto', async () => {
    const el: HTMLElement = (await abrirPainel(painel())).nativeElement;
    const kpis = [...el.querySelectorAll('.kpi')].map((k) => k.textContent!.replace(/\s+/g, ' ').trim());
    expect(kpis[0]).toContain('94,7%');
    expect(kpis[0]).toContain('1.420 de 1.500');
    expect(kpis[0]).toContain('Atenção'); // amarelo nunca é só cor
    expect(kpis[3]).toContain('215,7 un/h');
    expect(kpis[4]).toContain('1 h 25 min');
  });

  it('sem meta mostra "Sem meta" e avisa as máquinas paradas agora', async () => {
    const el: HTMLElement = (await abrirPainel(painel({
      atendimento_meta: { valor: null, semaforo: null },
      producao: { realizada: 10, aprovada: 10, reprovada: 0, meta: 0 },
      paradas_em_andamento: [{ chamado_id: 7, maquina: 'TEST-02', nome: 'Testador', setor: 'Testes', status_chamado: 'ABERTO',
                               motivo: 'Sondas sem contato', desde: '2026-08-15T12:00:00Z', minutos: 30 }],
    }))).nativeElement;
    expect(el.querySelector('.kpi')!.textContent).toContain('Sem meta');
    expect(el.querySelector('.paradas')!.textContent).toContain('TEST-02');
    expect(el.querySelector('.paradas')!.textContent).toContain('OS #7');
  });

  it('produção × meta desenha a meta como marca de referência', async () => {
    const el: HTMLElement = (await abrirPainel(painel())).nativeElement;
    const ref = el.querySelector<HTMLElement>('.ref')!;
    expect(ref).not.toBeNull();
    expect(ref.style.left).toBe('100%'); // a meta (1.500) é o maior valor do gráfico
    expect(el.querySelector('.legenda-grafico')!.textContent).toContain('Meta');
  });

  it('importação com erro mostra linha, coluna e problema', async () => {
    const f = TestBed.createComponent(Lancamentos);
    f.detectChanges();
    http.expectOne('/api/dsh/opcoes').flush(opcoes(true));
    await esperar(f);
    http.expectOne((r) => r.url === '/api/dsh/metas').flush([]);
    http.expectOne((r) => r.url === '/api/dsh/perdas').flush([]);
    await esperar(f);

    const entrada: HTMLInputElement = f.nativeElement.querySelector('input[type=file]');
    const arquivo = new File(['data;turno;modelo;quantidade\n2026-08-15;3º turno;AMT N14;10\n'], 'metas.csv', { type: 'text/csv' });
    Object.defineProperty(entrada, 'files', { value: [arquivo] });
    entrada.dispatchEvent(new Event('change'));
    await esperar(f);
    const req = http.expectOne('/api/dsh/importacao/metas');
    expect(req.request.body.conteudo).toContain('3º turno');
    req.flush({ linhas_lidas: 1, importadas: 0, erros: [{ linha: 2, coluna: 'turno', mensagem: "Turno '3º turno' não cadastrado(a)." }] });
    await esperar(f);
    http.expectOne((r) => r.url === '/api/dsh/metas').flush([]);
    http.expectOne((r) => r.url === '/api/dsh/perdas').flush([]);
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector('[role=alert]')!.textContent).toContain('Nada foi importado');
    expect(el.querySelector('.planilha tbody')!.textContent).toContain('3º turno');
  });

  it('datas e CSV', () => {
    expect(somarDias('2026-03-01', -1)).toBe('2026-02-28');
    const texto = csv(['Dia', 'Obs'], [['2026-08-15', 'Conector "quebrado"; troca']]);
    expect(texto.startsWith('﻿Dia;Obs')).toBe(true);
    expect(texto).toContain('"Conector ""quebrado""; troca"');
  });

  it('barras com referência incluem a meta na escala e na tabela', async () => {
    const f = TestBed.createComponent(BarrasHorizontais);
    f.componentRef.setInput('titulo', 'Produção × meta');
    f.componentRef.setInput('pontos', [{ rotulo: 'N14', valor: 50, referencia: 100 }, { rotulo: 'N16', valor: 80 }]);
    f.componentRef.setInput('rotuloReferencia', 'Meta');
    f.detectChanges();
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector<HTMLElement>('.barra')!.style.width).toBe('50%'); // 50 de um máximo de 100 (a meta)
    expect(el.querySelectorAll('.ref').length).toBe(1);
    el.querySelector<HTMLButtonElement>('.alternar')!.click();
    f.detectChanges();
    expect([...el.querySelectorAll('th')].map((t) => t.textContent!.trim())).toEqual(['Categoria', 'Valor', 'Meta']);
    expect(el.querySelector('tbody tr:last-child')!.textContent).toContain('—');
  });
});
