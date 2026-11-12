import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';

import {
  Auditoria,
  Chamado,
  Equipamento,
  Graficos,
  Indicadores,
  OpcoesMnt,
  Peca,
  PermissoesMnt,
  Prioridade,
  StatusChamado,
  TipoManutencao,
} from './mnt.modelos';

export interface FiltroChamados {
  status?: StatusChamado[];
  tipo?: TipoManutencao;
  prioridade?: Prioridade;
  setor?: string;
  meus_abertos?: boolean;
  meus_atendimentos?: boolean;
  de?: string;
  ate?: string;
  busca?: string;
}

export interface FiltroPeriodo {
  periodo_dias?: number | null;
  setor?: string | null;
}

/** Chamadas a /api/mnt. As permissões vêm do servidor em /opcoes e ficam em cache na sessão. */
@Injectable({ providedIn: 'root' })
export class MntService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/mnt';
  private readonly auth = inject(AuthService);
  private readonly _opcoes = signal<OpcoesMnt | null>(null);
  private donoDoCache: number | null = null;
  readonly opcoes = this._opcoes.asReadonly();

  async carregarOpcoes(): Promise<OpcoesMnt> {
    // O cache vale só para quem o carregou: outro login no mesmo navegador busca de novo.
    const usuarioId = this.auth.usuario()?.id ?? null;
    const emCache = this._opcoes();
    if (emCache && this.donoDoCache === usuarioId) return emCache;
    const opcoes = await firstValueFrom(this.http.get<OpcoesMnt>(`${this.base}/opcoes`));
    this._opcoes.set(opcoes);
    this.donoDoCache = usuarioId;
    return opcoes;
  }

  async pode(permissao: keyof PermissoesMnt): Promise<boolean> {
    return (await this.carregarOpcoes()).permissoes[permissao];
  }

  // ---- máquinas e peças
  equipamentos(setor?: string | null, incluirInativos = false): Observable<Equipamento[]> {
    let params = new HttpParams();
    if (setor) params = params.set('setor', setor);
    if (incluirInativos) params = params.set('incluir_inativos', 'true');
    return this.http.get<Equipamento[]>(`${this.base}/equipamentos`, { params });
  }

  criarEquipamento(dados: { codigo_tag: string; nome: string; setor: string; posto_trabalho?: string | null }) {
    return this.http.post<Equipamento>(`${this.base}/equipamentos`, dados);
  }

  alterarEquipamento(id: number, dados: Partial<Pick<Equipamento, 'nome' | 'setor' | 'posto_trabalho' | 'ativo'>>) {
    return this.http.patch<Equipamento>(`${this.base}/equipamentos/${id}`, dados);
  }

  pecas(incluirInativas = false): Observable<Peca[]> {
    const params = incluirInativas ? new HttpParams().set('incluir_inativas', 'true') : undefined;
    return this.http.get<Peca[]>(`${this.base}/pecas`, { params });
  }

  criarPeca(dados: { codigo_peca: string; nome: string; unidade_medida: string }) {
    return this.http.post<Peca>(`${this.base}/pecas`, dados);
  }

  alterarPeca(id: number, dados: Partial<Pick<Peca, 'nome' | 'unidade_medida' | 'ativo'>>) {
    return this.http.patch<Peca>(`${this.base}/pecas/${id}`, dados);
  }

  // ---- chamados
  abrirChamado(dados: { equipamento_id: number; prioridade: Prioridade; descricao_falha: string }) {
    return this.http.post<Chamado>(`${this.base}/chamados`, dados);
  }

  programarPreventiva(dados: { equipamento_id: number; prioridade: Prioridade; descricao_falha: string }) {
    return this.http.post<Chamado>(`${this.base}/preventivas`, dados);
  }

  fila(setor?: string | null): Observable<Chamado[]> {
    const params = setor ? new HttpParams().set('setor', setor) : undefined;
    return this.http.get<Chamado[]>(`${this.base}/chamados/fila`, { params });
  }

  chamados(filtro: FiltroChamados = {}): Observable<Chamado[]> {
    let params = new HttpParams();
    for (const [chave, valor] of Object.entries(filtro)) {
      if (valor === undefined || valor === null || valor === '' || valor === false) continue;
      if (Array.isArray(valor)) valor.forEach((v) => (params = params.append(chave, v)));
      else params = params.set(chave, String(valor));
    }
    return this.http.get<Chamado[]>(`${this.base}/chamados`, { params });
  }

  chamado(id: number): Observable<Chamado> {
    return this.http.get<Chamado>(`${this.base}/chamados/${id}`);
  }

  assumir(id: number) {
    return this.http.post<Chamado>(`${this.base}/chamados/${id}/assumir`, {});
  }

  salvarLaudo(id: number, dados: { diagnostico_tecnico: string; causa_raiz: string; tipo_manutencao: TipoManutencao }) {
    return this.http.put<Chamado>(`${this.base}/chamados/${id}/laudo`, dados);
  }

  adicionarPeca(id: number, pecaId: number, quantidade: number) {
    return this.http.post<Chamado>(`${this.base}/chamados/${id}/pecas`, { peca_id: pecaId, quantidade });
  }

  removerPeca(id: number, itemId: number) {
    return this.http.delete<Chamado>(`${this.base}/chamados/${id}/pecas/${itemId}`);
  }

  concluir(id: number, dados: { diagnostico_tecnico: string; causa_raiz: string; tipo_manutencao: TipoManutencao }) {
    return this.http.post<Chamado>(`${this.base}/chamados/${id}/concluir`, dados);
  }

  cancelar(id: number, motivo: string) {
    return this.http.post<Chamado>(`${this.base}/chamados/${id}/cancelar`, { motivo });
  }

  // ---- gestão
  indicadores(filtro: FiltroPeriodo): Observable<Indicadores> {
    return this.http.get<Indicadores>(`${this.base}/indicadores`, { params: this.paramsPeriodo(filtro) });
  }

  graficos(filtro: FiltroPeriodo): Observable<Graficos> {
    return this.http.get<Graficos>(`${this.base}/graficos`, { params: this.paramsPeriodo(filtro) });
  }

  auditoria(equipamentoId?: number | null, limite = 200): Observable<Auditoria[]> {
    let params = new HttpParams().set('limite', limite);
    if (equipamentoId) params = params.set('equipamento_id', equipamentoId);
    return this.http.get<Auditoria[]>(`${this.base}/auditoria`, { params });
  }

  private paramsPeriodo(filtro: FiltroPeriodo): HttpParams {
    let params = new HttpParams();
    if (filtro.periodo_dias) params = params.set('periodo_dias', filtro.periodo_dias);
    if (filtro.setor) params = params.set('setor', filtro.setor);
    return params;
  }
}
