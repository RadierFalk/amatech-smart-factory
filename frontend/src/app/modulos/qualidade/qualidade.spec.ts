import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Usuario } from '../../core/modelos';
import { LayoutQld } from './layout-qld';
import { Ocorrencia, OpcoesQld, PermissoesQld } from './qld.modelos';
import { FormularioOcorrencia, agoraNaFabrica } from './paginas/formulario-ocorrencia';
import { HistoricoQld, paraCsv } from './paginas/historico';
import { inicioDoPeriodo } from './paginas/painel';

const INSPETORA: Usuario = { id: 3, matricula: 'QUA-0001', nome: 'Maria', perfil: 'Inspetor de Qualidade', ativo: true, criado_em: '' };

function opcoes(p: Partial<PermissoesQld>): OpcoesQld {
  return {
    classificacoes: { CRITICO: 'Crítico', MAIOR: 'Maior', MENOR: 'Menor' },
    situacoes: { APROVADO: 'Aprovado', REPROVADO: 'Reprovado', EM_REPROCESSO: 'Em reprocesso' },
    status: { ABERTA: 'Aberta', EM_ANALISE: 'Em análise', RESOLVIDA: 'Resolvida' },
    permissoes: { registrar: false, editar: false, ocultar: false, abrir_chamado: false, cadastros: false, ...p },
  };
}

function ocorrencia(o: Partial<Ocorrencia> = {}): Ocorrencia {
  return {
    id: 12, ocorrida_em: '2026-11-12T12:30:00Z', classificacao: 'MAIOR', situacao_produto: 'REPROVADO', status: 'ABERTA',
    observacao: 'Tela com linhas', acao_realizada: 'Retido', produto_id: 1, producao_id: 31, numero_serie: 'AMT-000031', modelo: 'AMT N18',
    estacao_id: 5, estacao_nome: 'Teste Funcional', tipo_defeito_id: 1, tipo_defeito_nome: 'Tela', equipamento_id: 4,
    equipamento_tag: 'TEST-02', equipamento_nome: 'Testador FCT', responsavel_id: 3, responsavel_nome: 'Maria',
    chamado_id: null, chamado_status: null, ...o,
  };
}

async function esperar(fixture: ComponentFixture<unknown>): Promise<void> {
  await new Promise((r) => setTimeout(r));
  await fixture.whenStable();
}

function botoes(el: HTMLElement): string[] {
  return [...el.querySelectorAll('button, a.btn')].map((b) => b.textContent!.trim());
}

describe('Qualidade', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('amatech.token', 't');
    sessionStorage.setItem('amatech.usuario', JSON.stringify(INSPETORA));
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('menu do módulo mostra só as abas da persona', async () => {
    const f = TestBed.createComponent(LayoutQld);
    f.detectChanges();
    http.expectOne('/api/qld/opcoes').flush(opcoes({}));  // almoxarife: só consulta
    await esperar(f);
    const abas = [...f.nativeElement.querySelectorAll('.abas a')].map((a: Element) => a.textContent!.trim());
    expect(abas).toEqual(['Painel', 'Histórico']);
  });

  async function abrirFormulario(perm: Partial<PermissoesQld>, id?: number) {
    const f = TestBed.createComponent(FormularioOcorrencia);
    if (id) f.componentRef.setInput('id', String(id));
    f.detectChanges();
    http.expectOne('/api/qld/opcoes').flush(opcoes(perm));
    await esperar(f);
    const inativos = id ? '?incluir_inativos=true' : '';
    http.expectOne('/api/qld/notebooks').flush([{ id: 31, numero_serie: 'AMT-000031', modelo: 'AMT N18', etapa: 'Em Teste' }]);
    http.expectOne(`/api/qld/estacoes${inativos}`).flush([{ id: 5, nome: 'Teste Funcional', descricao: null, ativo: true }]);
    http.expectOne(`/api/qld/tipos-defeito${inativos}`).flush([{ id: 1, nome: 'Tela', descricao: null, ativo: true }]);
    http.expectOne('/api/qld/maquinas').flush([{ id: 4, codigo_tag: 'TEST-02', nome: 'Testador FCT', setor: 'Testes', status_operacional: 'OPERACIONAL' }]);
    await esperar(f);
    return f;
  }

  function escolher(el: HTMLElement, campo: string, indice = 1): void {
    const sel = el.querySelector<HTMLSelectElement>(`[formcontrolname=${campo}]`)!;
    sel.value = sel.options[indice].value;
    sel.dispatchEvent(new Event('change'));
  }

  function digitar(el: HTMLElement, campo: string, valor: string): void {
    const c = el.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[formcontrolname=${campo}]`)!;
    c.value = valor;
    c.dispatchEvent(new Event('input'));
  }

  it('registra com hora da fábrica sem fuso, abre chamado e mostra os avisos da integração', async () => {
    const f = await abrirFormulario({ registrar: true, abrir_chamado: true });
    const el: HTMLElement = f.nativeElement;
    for (const campo of ['producao_id', 'estacao_id', 'equipamento_id', 'tipo_defeito_id']) escolher(el, campo);
    digitar(el, 'data', '2026-11-12');
    digitar(el, 'hora', '08:30');
    digitar(el, 'observacao', 'Tela com linhas');
    digitar(el, 'acao_realizada', 'Retido');
    const chamado = el.querySelector<HTMLInputElement>('[formcontrolname=abrir_chamado]')!;
    chamado.click();
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Registrar ocorrência'))!.click();

    const req = http.expectOne('/api/qld/ocorrencias');
    expect(req.request.body).toMatchObject({
      ocorrida_em: '2026-11-12T08:30:00', producao_id: 31, produto_id: null, estacao_id: 5, equipamento_id: 4, tipo_defeito_id: 1,
      classificacao: 'MAIOR', situacao_produto: 'REPROVADO', status: 'ABERTA', abrir_chamado: true,
    });
    req.flush({ ocorrencia: ocorrencia({ chamado_id: 9 }), avisos: [{ tipo: 'aviso', mensagem: 'Manutenção: o chamado não foi aberto. RN02' }] });
    await esperar(f);
    expect(el.textContent).toContain('Ocorrência #12 registrada');
    expect(el.querySelector('.aviso.atencao')?.textContent).toContain('RN02');
    expect(el.querySelector<HTMLTextAreaElement>('[formcontrolname=observacao]')!.value).toBe('');
  });

  it('sem permissão de chamado, a opção não aparece', async () => {
    const f = await abrirFormulario({ registrar: true });
    expect(f.nativeElement.querySelector('[formcontrolname=abrir_chamado]')).toBeNull();
  });

  it('formulário incompleto avisa e não chama a API', async () => {
    const f = await abrirFormulario({ registrar: true });
    const el: HTMLElement = f.nativeElement;
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Registrar ocorrência'))!.click();
    await esperar(f);
    http.expectNone('/api/qld/ocorrencias');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Preencha');
  });

  it('edição carrega a ocorrência com data e hora de Manaus', async () => {
    const f = await abrirFormulario({ registrar: true, editar: true }, 12);
    http.expectOne('/api/qld/ocorrencias/12').flush(ocorrencia());
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector<HTMLInputElement>('[formcontrolname=data]')!.value).toBe('2026-11-12');
    expect(el.querySelector<HTMLInputElement>('[formcontrolname=hora]')!.value).toBe('08:30');
    expect(el.querySelector('[formcontrolname=abrir_chamado]')).toBeNull();
    expect(botoes(el)).toContain('Salvar alterações');
  });

  it('busca o notebook pelo número de série na Rastreabilidade e mantém o escolhido na lista', async () => {
    const f = await abrirFormulario({ registrar: true });
    const el: HTMLElement = f.nativeElement;
    escolher(el, 'producao_id');
    const busca = el.querySelector<HTMLInputElement>('#busca-notebook')!;
    busca.value = '000040';
    busca.dispatchEvent(new Event('input'));
    await new Promise((r) => setTimeout(r, 350));
    http.expectOne('/api/qld/notebooks?busca=000040').flush([{ id: 40, numero_serie: 'AMT-000040', modelo: 'AMT N14', etapa: 'Em Fila' }]);
    await esperar(f);
    const opcoes = [...el.querySelectorAll<HTMLOptionElement>('[formcontrolname=producao_id] option')].map((o) => o.textContent!.trim());
    expect(opcoes).toEqual(['Selecione…', 'AMT-000031 · AMT N18 · Em Teste', 'AMT-000040 · AMT N14 · Em Fila']);
  });

  it('edição de ocorrência do histórico mantém o notebook fixo e manda produto_id', async () => {
    const f = await abrirFormulario({ registrar: true, editar: true }, 12);
    http.expectOne('/api/qld/ocorrencias/12').flush(ocorrencia({ producao_id: null, numero_serie: 'AMT-000017', modelo: 'AMT N16' }));
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector('#busca-notebook')).toBeNull();
    expect(el.textContent).toContain('Do histórico, sem produção na Rastreabilidade');
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Salvar alterações'))!.click();
    const req = http.expectOne('/api/qld/ocorrencias/12');
    expect(req.request.body).toMatchObject({ produto_id: 1, producao_id: null });
    req.flush(ocorrencia());
    await esperar(f);
  });

  async function abrirHistorico(perm: Partial<PermissoesQld>, lista: Ocorrencia[]) {
    const f = TestBed.createComponent(HistoricoQld);
    f.detectChanges();
    http.expectOne('/api/qld/opcoes').flush(opcoes(perm));
    await esperar(f);
    http.expectOne('/api/qld/estacoes?incluir_inativos=true').flush([]);
    http.expectOne('/api/qld/tipos-defeito?incluir_inativos=true').flush([]);
    await esperar(f);
    http.expectOne('/api/qld/ocorrencias').flush(lista);
    await esperar(f);
    return f;
  }

  it('operador edita e abre chamado, mas não oculta', async () => {
    const f = await abrirHistorico({ registrar: true, editar: true, abrir_chamado: true }, [ocorrencia()]);
    const b = botoes(f.nativeElement);
    expect(b).toContain('Editar');
    expect(b).toContain('Abrir chamado');
    expect(b).not.toContain('Ocultar');
  });

  it('almoxarife só consulta; chamado existente aparece como OS', async () => {
    const f = await abrirHistorico({}, [ocorrencia({ chamado_id: 9, chamado_status: 'EM_ANDAMENTO' })]);
    const el: HTMLElement = f.nativeElement;
    expect(botoes(el)).not.toContain('Editar');
    expect(botoes(el)).not.toContain('Ocultar');
    expect(el.textContent).toContain('OS #9');
  });

  it('abrir chamado depois mostra o aviso e recarrega a lista', async () => {
    const f = await abrirHistorico({ abrir_chamado: true }, [ocorrencia()]);
    const el: HTMLElement = f.nativeElement;
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Abrir chamado'))!.click();
    http.expectOne('/api/qld/ocorrencias/12/chamado').flush({
      ocorrencia: ocorrencia({ chamado_id: 9 }), avisos: [{ tipo: 'sucesso', mensagem: 'Manutenção: chamado OS #9 aberto.' }],
    });
    await esperar(f);
    http.expectOne('/api/qld/ocorrencias').flush([ocorrencia({ chamado_id: 9, chamado_status: 'ABERTO' })]);
    await esperar(f);
    expect(el.querySelector('.aviso.sucesso')?.textContent).toContain('OS #9 aberto');
  });

  it('CSV usa ";" e BOM e escapa aspas e quebras de linha', () => {
    const csv = paraCsv([ocorrencia({ observacao: 'Tela "piscando"\nno teste', chamado_id: 9 })]);
    expect(csv.startsWith('﻿Ocorrência;')).toBe(true);
    expect(csv).toContain('"Tela ""piscando""\nno teste"');
    expect(csv).toContain('OS #9');
  });

  it('datas no horário da fábrica (UTC-4)', () => {
    // 02:00 UTC de 13/11 ainda é 22:00 de 12/11 em Manaus.
    const agora = new Date('2026-11-13T02:00:00Z');
    expect(agoraNaFabrica(agora)).toEqual({ data: '2026-11-12', hora: '22:00' });
    expect(inicioDoPeriodo(7, agora)).toBe('2026-11-06');
  });
});
