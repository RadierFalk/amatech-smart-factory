import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Usuario } from '../../core/modelos';
import { LayoutMnt } from './layout-mnt';
import { Chamado, OpcoesMnt, PermissoesMnt } from './mnt.modelos';
import { OrdemServico } from './paginas/ordem-servico';
import { paraCsv } from './paginas/historico';

const TECNICO: Usuario = { id: 5, matricula: 'TEC-2001', nome: 'João Lima', perfil: 'Técnico de Manutenção', ativo: true, criado_em: '' };

function opcoes(p: Partial<PermissoesMnt>): OpcoesMnt {
  return {
    prioridades: ['BAIXA', 'MEDIA', 'ALTA', 'CRITICA'],
    tipos_manutencao: ['CORRETIVA', 'PREVENTIVA'],
    status_chamado: ['ABERTO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO'],
    status_equipamento: { OPERACIONAL: 'Funcionando', EM_MANUTENCAO: 'Em manutenção', PARADA: 'Indisponível' },
    setores: ['SMT'],
    causas_raiz: ['Desgaste natural do componente'],
    permissoes: { abrir_chamado: false, atender: false, concluir_qualquer: false, cancelar: false, cadastros: false, indicadores: false, ...p },
  };
}

function chamado(c: Partial<Chamado> = {}): Chamado {
  return {
    id: 7, equipamento_id: 1, equipamento_tag: 'SMT-01', equipamento_nome: 'Insersora', setor: 'SMT', posto_trabalho: null,
    status_equipamento: 'EM_MANUTENCAO', prioridade: 'ALTA', tipo_manutencao: 'CORRETIVA', status_chamado: 'EM_ANDAMENTO',
    descricao_falha: 'Travamento no feeder', diagnostico_tecnico: null, causa_raiz: null, motivo_cancelamento: null,
    operador_id: 2, operador_nome: 'João', tecnico_id: 5, tecnico_nome: 'João Lima',
    data_hora_abertura: '2026-11-10T12:00:00Z', data_hora_inicio_atendimento: '2026-11-10T12:15:00Z', data_hora_fim_atendimento: null,
    downtime_minutos: null, minutos_desde_abertura: 30, minutos_em_atendimento: 15, origem_sistema: null, id_externo: null,
    pecas: [], ...c,
  };
}

async function esperar(fixture: ComponentFixture<unknown>): Promise<void> {
  await new Promise((r) => setTimeout(r));
  await fixture.whenStable();
}

describe('Manutenção', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('amatech.token', 't');
    sessionStorage.setItem('amatech.usuario', JSON.stringify(TECNICO));
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function abrirOs(perm: Partial<PermissoesMnt>, os: Chamado) {
    const fixture = TestBed.createComponent(OrdemServico);
    fixture.componentRef.setInput('id', String(os.id));
    fixture.detectChanges();
    http.expectOne('/api/mnt/opcoes').flush(opcoes(perm));
    await esperar(fixture);
    http.expectOne(`/api/mnt/chamados/${os.id}`).flush(os);
    await esperar(fixture);
    return fixture;
  }

  function botoes(el: HTMLElement): string[] {
    return [...el.querySelectorAll('button')].map((b) => b.textContent!.trim());
  }

  it('técnico responsável edita laudo, peças e conclui', async () => {
    const f = await abrirOs({ atender: true }, chamado());
    http.expectOne('/api/mnt/pecas').flush([{ id: 1, codigo_peca: 'PN-SEN-030', nome: 'Sensor', unidade_medida: 'UN', ativo: true }]);
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    expect(botoes(el)).toContain('Concluir OS e liberar máquina');
    expect(botoes(el)).toContain('Salvar rascunho');
    expect(botoes(el)).toContain('Adicionar');
    expect(botoes(el)).not.toContain('Cancelar OS');
  });

  it('outro técnico só visualiza a OS (RN03)', async () => {
    const f = await abrirOs({ atender: true }, chamado({ tecnico_id: 99, tecnico_nome: 'Mariana' }));
    http.expectNone('/api/mnt/pecas'); // sem poder editar, nem carrega o catálogo de peças
    expect(botoes(f.nativeElement)).not.toContain('Concluir OS e liberar máquina');
    expect(botoes(f.nativeElement)).not.toContain('Adicionar');
  });

  it('supervisor conclui e cancela, mas não mexe em peças', async () => {
    const f = await abrirOs({ concluir_qualquer: true, cancelar: true }, chamado({ tecnico_id: 99 }));
    const b = botoes(f.nativeElement);
    expect(b).toContain('Concluir OS e liberar máquina');
    expect(b).toContain('Cancelar OS');
    expect(b).not.toContain('Adicionar');
    expect(b).not.toContain('Salvar rascunho');
  });

  it('concluir sem laudo avisa a RN04 e não chama a API', async () => {
    const f = await abrirOs({ atender: true }, chamado());
    http.expectOne('/api/mnt/pecas').flush([]);
    await esperar(f);
    const el: HTMLElement = f.nativeElement;
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Concluir OS'))!.click();
    await esperar(f);
    http.expectNone('/api/mnt/chamados/7/concluir');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('RN04');
  });

  it('chamado aberto mostra "Assumir" para quem atende e mantém o laudo digitado ao registrar peça', async () => {
    const f = await abrirOs({ atender: true }, chamado({ status_chamado: 'ABERTO', tecnico_id: null, tecnico_nome: null }));
    const el: HTMLElement = f.nativeElement;
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Assumir'))!.click();
    http.expectOne('/api/mnt/chamados/7/assumir').flush(chamado());
    await esperar(f);
    http.expectOne('/api/mnt/pecas').flush([{ id: 1, codigo_peca: 'PN-SEN-030', nome: 'Sensor', unidade_medida: 'UN', ativo: true }]);
    await esperar(f);

    const diag = el.querySelector<HTMLTextAreaElement>('[formcontrolname=diagnostico_tecnico]')!;
    diag.value = 'Sensor sujo';
    diag.dispatchEvent(new Event('input'));
    const sel = el.querySelector<HTMLSelectElement>('[formcontrolname=peca_id]')!;
    sel.value = sel.options[1].value;
    sel.dispatchEvent(new Event('change'));
    [...el.querySelectorAll('button')].find((b) => b.textContent!.trim() === 'Adicionar')!.click();
    const req = http.expectOne('/api/mnt/chamados/7/pecas');
    expect(req.request.body).toEqual({ peca_id: 1, quantidade: 1 });
    req.flush(chamado({ pecas: [{ id: 3, peca_id: 1, codigo_peca: 'PN-SEN-030', nome: 'Sensor', unidade_medida: 'UN', quantidade: 1 }] }));
    await esperar(f);
    expect(el.querySelector<HTMLTextAreaElement>('[formcontrolname=diagnostico_tecnico]')!.value).toBe('Sensor sujo');
    expect(el.textContent).toContain('PN-SEN-030');
  });

  it('menu do módulo mostra só as abas da persona', async () => {
    const f = TestBed.createComponent(LayoutMnt);
    f.detectChanges();
    http.expectOne('/api/mnt/opcoes').flush(opcoes({ abrir_chamado: true }));
    await esperar(f);
    const abas = [...f.nativeElement.querySelectorAll('.links a')].map((a: Element) => a.textContent!.trim());
    expect(abas).toEqual(['Painel de máquinas', 'Abrir chamado', 'Meus chamados']);
  });

  it('CSV usa ";" e BOM e escapa aspas e quebras de linha', () => {
    const csv = paraCsv([chamado({ descricao_falha: 'Falha "intermitente"\nna zona 4' })]);
    expect(csv.startsWith('﻿OS;TAG;')).toBe(true);
    expect(csv).toContain('"Falha ""intermitente""\nna zona 4"');
  });
});
