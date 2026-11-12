import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  FiltroPainel,
  IndicadorSemaforo,
  Limite,
  LinhaHistorico,
  Meta,
  OpcoesDsh,
  Painel,
  Perda,
  ResultadoImportacao,
  TipoPerda,
  Turno,
} from './dsh.modelos';

export type TipoPlanilha = 'metas' | 'perdas';

/** Chamadas a /api/dsh. As opções (turnos, modelos, permissões) ficam em cache na sessão. */
@Injectable({ providedIn: 'root' })
export class DshService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly base = '/api/dsh';
  private readonly _opcoes = signal<OpcoesDsh | null>(null);
  private donoDoCache: number | null = null;
  readonly opcoes = this._opcoes.asReadonly();

  async carregarOpcoes(forcar = false): Promise<OpcoesDsh> {
    const usuarioId = this.auth.usuario()?.id ?? null;
    const emCache = this._opcoes();
    if (!forcar && emCache && this.donoDoCache === usuarioId) return emCache;
    const opcoes = await firstValueFrom(this.http.get<OpcoesDsh>(`${this.base}/opcoes`));
    this._opcoes.set(opcoes);
    this.donoDoCache = usuarioId;
    return opcoes;
  }

  painel(f: FiltroPainel): Observable<Painel> {
    return this.http.get<Painel>(`${this.base}/painel`, { params: this.params(f) });
  }

  historicoProducao(f: FiltroPainel): Observable<LinhaHistorico[]> {
    return this.http.get<LinhaHistorico[]>(`${this.base}/historico/producao`, { params: this.params(f) });
  }

  // ---- metas e perdas
  metas(de: string, ate: string): Observable<Meta[]> {
    return this.http.get<Meta[]>(`${this.base}/metas`, { params: this.params({ de, ate }) });
  }

  gravarMeta(dados: { data: string; turno_id: number; modelo_id: number; quantidade: number }) {
    return this.http.put<Meta>(`${this.base}/metas`, dados);
  }

  excluirMeta(id: number) {
    return this.http.delete<void>(`${this.base}/metas/${id}`);
  }

  perdas(f: FiltroPainel): Observable<Perda[]> {
    return this.http.get<Perda[]>(`${this.base}/perdas`, { params: this.params(f) });
  }

  registrarPerda(dados: {
    data: string; turno_id: number; estacao_id: number; modelo_id: number; tipo_perda_id: number; quantidade: number; observacao: string | null;
  }) {
    return this.http.post<Perda>(`${this.base}/perdas`, dados);
  }

  excluirPerda(id: number) {
    return this.http.delete<void>(`${this.base}/perdas/${id}`);
  }

  importar(tipo: TipoPlanilha, conteudo: string) {
    return this.http.post<ResultadoImportacao>(`${this.base}/importacao/${tipo}`, { conteudo });
  }

  modeloPlanilha(tipo: TipoPlanilha): Observable<Blob> {
    return this.http.get(`${this.base}/importacao/${tipo}/modelo`, { responseType: 'blob' });
  }

  // ---- configuração
  alterarTurno(id: number, dados: { nome: string; hora_inicio: string; hora_fim: string }) {
    return this.http.put<Turno>(`${this.base}/turnos/${id}`, dados);
  }

  criarTipoPerda(nome: string) {
    return this.http.post<TipoPerda>(`${this.base}/tipos-perda`, { nome });
  }

  alterarTipoPerda(id: number, ativo: boolean) {
    return this.http.patch<TipoPerda>(`${this.base}/tipos-perda/${id}`, { ativo });
  }

  salvarLimites(indicador: IndicadorSemaforo, dados: { limite_verde: number; limite_amarelo: number }) {
    return this.http.put<Limite>(`${this.base}/limites/${indicador}`, dados);
  }

  private params(f: Partial<FiltroPainel>): HttpParams {
    let params = new HttpParams();
    for (const [chave, valor] of Object.entries(f)) {
      if (valor !== undefined && valor !== null && valor !== '' && valor !== 0) params = params.set(chave, String(valor));
    }
    return params;
  }
}
