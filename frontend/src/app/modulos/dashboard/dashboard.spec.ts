import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Usuario } from '../../core/modelos';
import { BarrasHorizontais } from '../../shared/graficos';
import { OpcoesDsh, Painel, somarDias } from './dsh.modelos';
import { DshService } from './dsh.service';
import { LayoutDsh } from './layout-dsh';
import { AbaGeral } from './paginas/aba-geral';
import { AbaManutencao } from './paginas/aba-manutencao';
import { AbaMateriais } from './paginas/aba-materiais';
import { AbaProducao } from './paginas/aba-producao';
import { csv } from './paginas/historico';
import { Lancamentos } from './paginas/lancamentos';
import { EstadoPainel, PainelDsh } from './paginas/painel';

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
    lead_time: { minutos: 400, expedidos: 3, por_modelo: [{ modelo: 'AMT N14', minutos: 400, expedidos: 3 }] },
    em_producao: { total: 5, por_etapa: [{ rotulo: 'Em Teste', quantidade: 4, lateral: false },
                                         { rotulo: 'Parado', quantidade: 1, lateral: true }] },
    producao_por_turno: [{ data: '2026-08-15', turno_id: 1, turno: '1º turno', modelo: 'AMT N14', realizada: 1420, aprovada: 1360,
                           reprovada: 60, meta: 1500, atendimento_meta: 94.7 }],
    qualidade: { ocorrencias: 3, abertas: 1, em_analise: 1, resolvidas: 1, criticas: 1, criticas_pendentes: 1,
                 por_tipo: [{ rotulo: 'Tela', quantidade: 3 }], por_dia: [{ data: '2026-08-15', quantidade: 3 }], criticas_recentes: [] },
    manutencao: { disponibilidade: 91.15, mttr_minutos: 75, mtta_minutos: 10, mtbf_minutos: 875, chamados: 1, chamados_ativos: 0,
                  por_setor: [{ setor: 'Testes', minutos: 85, paradas: 1 }], por_dia: [{ data: '2026-08-15', minutos: 85 }],
                  por_maquina: [{ maquina: 'TEST-02', nome: 'Testador', setor: 'Testes', minutos: 85, paradas: 1, parada_agora: false }],
                  por_causa: [] },
    materiais: { pendentes: 1, parciais: 1, producoes_com_pendencia: 1, baixas: 1, unidades_baixadas: 4, limite_critico: 50,
                 estoque_critico: [{ sku: 'BAT-45WH', nome: 'Bateria 45 Wh', estoque: 4, pedido: 18, insuficiente: true }],
                 pendencias_por_componente: [{ sku: 'BAT-45WH', nome: 'Bateria 45 Wh', producoes: 1, quantidade: 18, insuficiente: true }] },
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
    TestBed.configureTestingModule({ providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting(), EstadoPainel] });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('abas dos setores para todos; Metas e perdas e Configuração só para a gestão', async () => {
    const f = TestBed.createComponent(LayoutDsh);
    f.detectChanges();
    http.expectOne('/api/dsh/opcoes').flush(opcoes(false));
    await esperar(f);
    const textos = (sel: string) => [...f.nativeElement.querySelectorAll(sel)].map((a: Element) => a.textContent!.trim());
    expect(textos('.abas a')).toEqual(['Visão geral', 'Produção', 'Qualidade', 'Manutenção', 'Materiais']);
    expect(textos('.outras a')).toEqual(['Histórico']);
  });

  it('o painel busca 7 dias até o "hoje" do servidor e guarda os dados para as abas', async () => {
    const f = TestBed.createComponent(PainelDsh);
    f.detectChanges();
    http.expectOne('/api/dsh/opcoes').flush(opcoes(true));
    await esperar(f);
    // Período padrão: 7 dias terminando no "hoje" do servidor (dia da fábrica), não no relógio do navegador.
    const req = http.expectOne((r) => r.url === '/api/dsh/painel');
    expect(req.request.params.get('de')).toBe('2026-08-09');
    expect(req.request.params.get('ate')).toBe('2026-08-15');
    req.flush(painel());
    await esperar(f);
    const estado = f.debugElement.injector.get(EstadoPainel);
    expect(estado.dados()!.producao.realizada).toBe(1420);
    expect(estado.incluiHoje()).toBe(true);
  });

  /** Abre uma aba com os dados já carregados, como se viesse do painel. */
  async function abrirAba<T>(tipo: Type<T>, dados: Painel): Promise<HTMLElement> {
    const carregando = TestBed.inject(DshService).carregarOpcoes();
    http.expectOne('/api/dsh/opcoes').flush(opcoes(true));
    await carregando;
    const f = TestBed.createComponent(tipo);
    const estado = f.debugElement.injector.get(EstadoPainel);
    estado.filtro.set({ de: '2026-08-15', ate: '2026-08-15' });
    estado.dados.set(dados);
    f.detectChanges();
    await esperar(f);
    return f.nativeElement as HTMLElement;
  }

  const textoKpis = (el: HTMLElement) => [...el.querySelectorAll('am-kpi')].map((k) => k.textContent!.replace(/\s+/g, ' ').trim());
  const PARADA = {
    chamado_id: 7, maquina: 'TEST-02', nome: 'Testador', setor: 'Testes', status_chamado: 'ABERTO',
    motivo: 'Sondas sem contato', desde: '2026-08-15T12:00:00Z', minutos: 30,
  };

  it('visão geral: seis cartões, semáforo com texto e alertas do momento', async () => {
    const el = await abrirAba(AbaGeral, painel({ paradas_em_andamento: [PARADA] }));
    const kpis = textoKpis(el);
    expect(kpis.length).toBe(6);
    expect(kpis[0]).toContain('1.420 un.');
    expect(kpis[1]).toContain('94,7%');
    expect(kpis[1]).toContain('Atenção'); // amarelo nunca é só cor
    expect(kpis[2]).toContain('6 h 40 min');
    expect(kpis[4]).toContain('1 parada(s) agora');
    const alertas = el.querySelector('.alertas')!.textContent!;
    expect(alertas).toContain('TEST-02 parada');
    expect(alertas).toContain('BAT-45WH insuficiente');
    expect([...el.querySelectorAll('.setor h2')].map((h) => h.textContent!.replace(/\s+/g, ' ').trim())).toEqual(
      ['RAS Produção', 'QLD Qualidade', 'MNT Manutenção', 'RAS Materiais']);
  });

  it('visão geral sem meta mostra "Sem meta"', async () => {
    const el = await abrirAba(AbaGeral, painel({
      atendimento_meta: { valor: null, semaforo: null }, producao: { realizada: 10, aprovada: 10, reprovada: 0, meta: 0 },
    }));
    expect(textoKpis(el)[1]).toContain('Sem meta');
  });

  it('produção: meta como traço de referência, etapas fora do fluxo em vermelho e matriz com texto', async () => {
    const el = await abrirAba(AbaProducao, painel());
    expect(el.querySelectorAll('am-producao-meta-dia .meta').length).toBe(1);
    expect(el.querySelector('am-producao-meta-dia .hoje')!.textContent).toContain('Hoje');
    expect(el.querySelectorAll('.barra.critico').length).toBe(1); // Parado
    expect(el.textContent).toContain('Vermelho = fora do fluxo');
    const celulas = [...el.querySelectorAll('.matriz td[tabindex]')];
    expect(celulas.map((c) => c.firstChild!.textContent)).toEqual(['94%', '—']); // 1º turno com meta; 2º turno vazio
    expect(celulas[0].className).toContain('cel-atencao'); // 94,7% fica abaixo dos 95% do alvo
  });

  it('manutenção: aviso da máquina parada agora e MTTR/MTBF formatados', async () => {
    const el = await abrirAba(AbaManutencao, painel({ paradas_em_andamento: [PARADA] }));
    expect(el.querySelector('.paradas')!.textContent).toContain('OS #7');
    const kpis = textoKpis(el);
    expect(kpis[0]).toContain('91,2%');
    expect(kpis[1]).toContain('1 h 15 min');
    expect(kpis[2]).toContain('14 h 35 min');
  });

  it('materiais: estoque que não cobre o pedido aparece como Insuficiente', async () => {
    const el = await abrirAba(AbaMateriais, painel());
    expect(el.querySelector('tbody')!.textContent).toContain('Insuficiente');
    expect(el.querySelector<HTMLElement>('.trilho span')!.style.width).toBe('22%'); // 4 de 18
    expect(el.textContent).toContain('Vermelho = o estoque não cobre o que falta');
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
