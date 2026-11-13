import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  Classificacao,
  IndicadoresQld,
  ItemCadastro,
  Maquina,
  Notebook,
  Ocorrencia,
  OcorrenciaEntrada,
  OpcoesQld,
  PermissoesQld,
  Produto,
  RegistroSaida,
  SituacaoProduto,
  StatusOcorrencia,
} from './qld.modelos';

export interface FiltroOcorrencias {
  busca?: string;
  classificacao?: Classificacao;
  situacao?: SituacaoProduto;
  status?: StatusOcorrencia;
  estacao_id?: number;
  tipo_defeito_id?: number;
  equipamento_id?: number;
  de?: string;
  ate?: string;
}

/** Estações e tipos de defeito usam as mesmas rotas e o mesmo formato. */
export type TipoItem = 'estacoes' | 'tipos-defeito';

/** Chamadas a /api/qld. As permissões vêm do servidor em /opcoes e ficam em cache na sessão. */
@Injectable({ providedIn: 'root' })
export class QldService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly base = '/api/qld';
  private readonly _opcoes = signal<OpcoesQld | null>(null);
  private donoDoCache: number | null = null;
  readonly opcoes = this._opcoes.asReadonly();

  async carregarOpcoes(): Promise<OpcoesQld> {
    // O cache vale só para quem o carregou: outro login no mesmo navegador busca de novo.
    const usuarioId = this.auth.usuario()?.id ?? null;
    const emCache = this._opcoes();
    if (emCache && this.donoDoCache === usuarioId) return emCache;
    const opcoes = await firstValueFrom(this.http.get<OpcoesQld>(`${this.base}/opcoes`));
    this._opcoes.set(opcoes);
    this.donoDoCache = usuarioId;
    return opcoes;
  }

  async pode(permissao: keyof PermissoesQld): Promise<boolean> {
    return (await this.carregarOpcoes()).permissoes[permissao];
  }

  // ---- cadastros
  maquinas(): Observable<Maquina[]> {
    return this.http.get<Maquina[]>(`${this.base}/maquinas`);
  }

  /** Produções da Rastreabilidade ainda não expedidas (as mexidas por último primeiro). */
  notebooks(busca = ''): Observable<Notebook[]> {
    const params = busca.trim() ? new HttpParams().set('busca', busca.trim()) : undefined;
    return this.http.get<Notebook[]>(`${this.base}/notebooks`, { params });
  }

  /** Notebooks que já tiveram ocorrência e os do histórico. Só consulta: eles vêm da Rastreabilidade. */
  produtos(incluirInativos = false): Observable<Produto[]> {
    return this.http.get<Produto[]>(`${this.base}/produtos`, { params: this.inativos(incluirInativos) });
  }

  itens(tipo: TipoItem, incluirInativos = false): Observable<ItemCadastro[]> {
    return this.http.get<ItemCadastro[]>(`${this.base}/${tipo}`, { params: this.inativos(incluirInativos) });
  }

  criarItem(tipo: TipoItem, dados: { nome: string; descricao: string | null }) {
    return this.http.post<ItemCadastro>(`${this.base}/${tipo}`, dados);
  }

  alterarItem(tipo: TipoItem, id: number, dados: Partial<Pick<ItemCadastro, 'nome' | 'descricao' | 'ativo'>>) {
    return this.http.patch<ItemCadastro>(`${this.base}/${tipo}/${id}`, dados);
  }

  // ---- ocorrências
  ocorrencias(filtro: FiltroOcorrencias = {}): Observable<Ocorrencia[]> {
    let params = new HttpParams();
    for (const [chave, valor] of Object.entries(filtro)) {
      if (valor === undefined || valor === null || valor === '') continue;
      params = params.set(chave, String(valor));
    }
    return this.http.get<Ocorrencia[]>(`${this.base}/ocorrencias`, { params });
  }

  ocorrencia(id: number): Observable<Ocorrencia> {
    return this.http.get<Ocorrencia>(`${this.base}/ocorrencias/${id}`);
  }

  registrar(dados: OcorrenciaEntrada & { abrir_chamado: boolean }) {
    return this.http.post<RegistroSaida>(`${this.base}/ocorrencias`, dados);
  }

  editar(id: number, dados: OcorrenciaEntrada) {
    return this.http.put<Ocorrencia>(`${this.base}/ocorrencias/${id}`, dados);
  }

  ocultar(id: number) {
    return this.http.post<void>(`${this.base}/ocorrencias/${id}/ocultar`, {});
  }

  abrirChamado(id: number) {
    return this.http.post<RegistroSaida>(`${this.base}/ocorrencias/${id}/chamado`, {});
  }

  // ---- painel
  indicadores(de?: string | null, ate?: string | null): Observable<IndicadoresQld> {
    let params = new HttpParams();
    if (de) params = params.set('de', de);
    if (ate) params = params.set('ate', ate);
    return this.http.get<IndicadoresQld>(`${this.base}/indicadores`, { params });
  }

  private inativos(incluir: boolean): HttpParams | undefined {
    return incluir ? new HttpParams().set('incluir_inativos', 'true') : undefined;
  }
}
