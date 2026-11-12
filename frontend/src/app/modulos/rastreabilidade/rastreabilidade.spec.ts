import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Usuario } from '../../core/modelos';
import { LayoutRas } from './layout-ras';
import { OpcoesRas, PermissoesRas, ProducaoDetalhe, Relatorio, Solicitacao } from './ras.modelos';
import { Materiais, saldo, sugestaoBaixa } from './paginas/materiais';
import { ProducaoDetalheTela } from './paginas/producao-detalhe';
import { celula, paraCsv } from './paginas/relatorios';

const OPERADOR: Usuario = { id: 2, matricula: 'OPE-0001', nome: 'João', perfil: 'Operador de Produção', ativo: true, criado_em: '' };

const ETAPAS = [
  { id: 1, nome: 'Em Fila', ordem: 1 }, { id: 2, nome: 'Em Montagem', ordem: 2 }, { id: 3, nome: 'Em Teste', ordem: 3 },
  { id: 8, nome: 'Reprovado', ordem: 91 },
];

function opcoes(p: Partial<PermissoesRas>): OpcoesRas {
  return {
    etapas: ETAPAS,
    responsaveis: [{ id: 2, nome: 'João', matricula: 'OPE-0001' }, { id: 5, nome: 'Maria', matricula: 'QUA-0001' }],
    status_solicitacao: ['PENDENTE', 'PARCIAL', 'ATENDIDA', 'CANCELADA'],
    limite_estoque_critico: 50,
    permissoes: { producao: false, excluir_producao: false, solicitar: false, baixar: false, componentes: false, modelos_etapas: false, ...p },
  };
}

function producao(p: Partial<ProducaoDetalhe> = {}): ProducaoDetalhe {
  return {
    id: 7, numero_serie: 'AMT-000007', id_unica: 'PRD-AMT-000007-20261111', modelo_id: 1, modelo_nome: 'AMT N14',
    modelo_codigo: 'N14-I5-8-256', etapa_id: 2, etapa_nome: 'Em Montagem', etapa_ordem: 2, responsavel_id: 2,
    responsavel_nome: 'João', criado_por_nome: 'João', iniciada_em: '2026-11-11T12:00:00Z', atualizada_em: '2026-11-11T13:00:00Z',
    passagens: [
      { id: 1, etapa_nome: 'Em Fila', usuario_nome: 'João', responsavel_nome: 'João', registrada_em: '2026-11-11T12:00:00Z', origem: 'MANUAL' },
      { id: 2, etapa_nome: 'Em Montagem', usuario_nome: 'João', responsavel_nome: 'João', registrada_em: '2026-11-11T13:00:00Z', origem: 'MAQUINA/IOT' },
    ],
    nao_conformidades: [], solicitacoes: [], materiais_pendentes: 0, mesmo_modelo: [], proxima_etapa_id: 3, ...p,
  };
}

function solicitacao(s: Partial<Solicitacao> = {}): Solicitacao {
  return {
    id: 40, producao_id: 7, numero_serie: 'AMT-000007', componente_id: 4, componente_nome: 'Memória 8GB', sku: 'RAM-8G-D4',
    estoque: 3, quantidade: 2, quantidade_baixada: 0, status: 'PENDENTE', solicitante_nome: 'João',
    criada_em: '2026-11-11T12:05:00Z', ...s,
  };
}

async function esperar(fixture: ComponentFixture<unknown>): Promise<void> {
  await new Promise((r) => setTimeout(r));
  await fixture.whenStable();
}

function botao(el: HTMLElement, texto: string): HTMLButtonElement | undefined {
  return [...el.querySelectorAll('button')].find((b) => b.textContent!.trim().includes(texto));
}

describe('Rastreabilidade', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('amatech.token', 't');
    sessionStorage.setItem('amatech.usuario', JSON.stringify(OPERADOR));
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('menu mostra Cadastros só para quem cuida de componentes, modelos ou etapas', async () => {
    const f = TestBed.createComponent(LayoutRas);
    f.detectChanges();
    http.expectOne('/api/ras/opcoes').flush(opcoes({ producao: true, solicitar: true }));
    await esperar(f);
    const abas = [...f.nativeElement.querySelectorAll('.abas a')].map((a: Element) => a.textContent!.trim());
    expect(abas).toEqual(['Painel', 'Produções', 'Materiais', 'Relatórios']);
  });

  async function abrirProducao(perm: Partial<PermissoesRas>, p = producao()) {
    const f = TestBed.createComponent(ProducaoDetalheTela);
    f.componentRef.setInput('id', String(p.id));
    f.detectChanges();
    http.expectOne('/api/ras/opcoes').flush(opcoes(perm));
    await esperar(f);
    http.expectOne(`/api/ras/producoes/${p.id}`).flush(p);
    await esperar(f);
    return f;
  }

  it('ficha mostra o histórico e sugere a próxima etapa', async () => {
    const f = await abrirProducao({ producao: true });
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector('h1')!.textContent).toContain('AMT-000007');
    expect(el.querySelectorAll('.linha-tempo li').length).toBe(2);
    expect(el.textContent).toContain('Máquina'); // origem MAQUINA/IOT em palavras
    const sel = el.querySelector<HTMLSelectElement>('[formcontrolname=etapa_id]')!;
    expect(sel.options[sel.selectedIndex].textContent).toContain('Em Teste (sugerida)');

    botao(el, 'Mudar etapa')!.click();
    const req = http.expectOne('/api/ras/producoes/7/etapa');
    expect(req.request.body).toEqual({ etapa_id: 3, responsavel_id: null });
    req.flush(producao({ etapa_id: 3, etapa_nome: 'Em Teste', proxima_etapa_id: null }));
    await esperar(f);
    expect(el.querySelector('.aviso.sucesso')?.textContent).toContain('Em Teste');
  });

  it('reprovar pede falha e motivo antes de chamar a API', async () => {
    const f = await abrirProducao({ producao: true });
    const el: HTMLElement = f.nativeElement;
    const sel = el.querySelector<HTMLSelectElement>('[formcontrolname=etapa_id]')!;
    sel.value = sel.options[3].value; // Reprovado
    sel.dispatchEvent(new Event('change'));
    await esperar(f);
    botao(el, 'Reprovar')!.click();
    await esperar(f);
    http.expectNone('/api/ras/producoes/7/etapa');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('falha');

    for (const [campo, valor] of [['descricao_falha', 'Tela com pixels mortos'], ['motivo_reprovacao', 'Defeito de tela']]) {
      const c = el.querySelector<HTMLInputElement>(`[formcontrolname=${campo}]`)!;
      c.value = valor;
      c.dispatchEvent(new Event('input'));
    }
    botao(el, 'Reprovar')!.click();
    const req = http.expectOne('/api/ras/producoes/7/etapa');
    expect(req.request.body).toEqual({ etapa_id: 8, responsavel_id: null, descricao_falha: 'Tela com pixels mortos', motivo_reprovacao: 'Defeito de tela' });
    req.flush(producao({ etapa_id: 8, etapa_nome: 'Reprovado' }));
    await esperar(f);
  });

  it('almoxarife só consulta a ficha (sem mudar etapa nem excluir)', async () => {
    const f = await abrirProducao({ solicitar: true, baixar: true });
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector('[formcontrolname=etapa_id]')).toBeNull();
    expect(botao(el, 'Excluir produção')).toBeUndefined();
    expect(botao(el, 'Solicitar a lista do modelo')).toBeDefined();
  });

  it('baixa sugere o que cabe no estoque e só aparece para quem pode baixar', async () => {
    expect(saldo(solicitacao({ quantidade_baixada: 1 }))).toBe(1);
    expect(sugestaoBaixa(solicitacao({ quantidade: 10, estoque: 3 }))).toBe(3);

    const f = TestBed.createComponent(Materiais);
    f.detectChanges();
    http.expectOne('/api/ras/opcoes').flush(opcoes({ baixar: true }));
    await esperar(f);
    http.expectOne('/api/ras/solicitacoes').flush([solicitacao(), solicitacao({ id: 41, status: 'ATENDIDA', quantidade_baixada: 2 })]);
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelectorAll('tbody tr').length).toBe(1); // "em aberto" esconde a atendida
    expect(el.querySelector<HTMLInputElement>('#qtd-40')!.value).toBe('2');

    botao(el, 'Dar baixa')!.click();
    const req = http.expectOne('/api/ras/baixas');
    expect(req.request.body).toEqual({ solicitacao_id: 40, quantidade: 2 });
    req.flush({});
    await esperar(f);
    http.expectOne('/api/ras/solicitacoes').flush([]);
    await esperar(f);
    expect(el.querySelector('.aviso.sucesso')?.textContent).toContain('RAM-8G-D4');
  });

  it('relatório formata datas no horário da fábrica e exporta CSV com BOM', () => {
    const r: Relatorio = {
      tipo: 'nao_conformidades', titulo: 'NCs',
      colunas: [{ chave: 'data', titulo: 'Data', formato: 'data' }, { chave: 'falha', titulo: 'Falha', formato: 'texto' }],
      linhas: [{ data: '2026-11-12T02:30:00Z', falha: 'Tela "piscando"; sem imagem' }],
    };
    expect(celula(r.colunas[0], r.linhas[0]['data'])).toBe('11/11/2026 22:30');
    const csv = paraCsv(r);
    expect(csv.startsWith('﻿Data;Falha')).toBe(true);
    expect(csv).toContain('11/11/2026 22:30;"Tela ""piscando""; sem imagem"');
  });
});
