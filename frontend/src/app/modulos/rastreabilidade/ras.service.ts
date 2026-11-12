import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  Baixa,
  Componente,
  Etapa,
  Modelo,
  OpcoesRas,
  PainelRas,
  PermissoesRas,
  Producao,
  ProducaoDetalhe,
  Relatorio,
  Solicitacao,
  StatusSolicitacao,
} from './ras.modelos';

export interface DadosModelo {
  codigo: string;
  nome: string;
  meta: number | null;
  componentes: { componente_id: number; quantidade: number }[];
}

/** Chamadas a /api/ras. As permissões e as etapas vêm de /opcoes e ficam em cache na sessão. */
@Injectable({ providedIn: 'root' })
export class RasService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly base = '/api/ras';
  private readonly _opcoes = signal<OpcoesRas | null>(null);
  private donoDoCache: number | null = null;
  readonly opcoes = this._opcoes.asReadonly();

  async carregarOpcoes(forcar = false): Promise<OpcoesRas> {
    // O cache vale só para quem o carregou: outro login no mesmo navegador busca de novo.
    const usuarioId = this.auth.usuario()?.id ?? null;
    const emCache = this._opcoes();
    if (!forcar && emCache && this.donoDoCache === usuarioId) return emCache;
    const opcoes = await firstValueFrom(this.http.get<OpcoesRas>(`${this.base}/opcoes`));
    this._opcoes.set(opcoes);
    this.donoDoCache = usuarioId;
    return opcoes;
  }

  async pode(permissao: keyof PermissoesRas): Promise<boolean> {
    return (await this.carregarOpcoes()).permissoes[permissao];
  }

  // ---- painel e relatórios
  painel(): Observable<PainelRas> {
    return this.http.get<PainelRas>(`${this.base}/painel`);
  }

  relatorio(tipo: string, de?: string | null, ate?: string | null): Observable<Relatorio> {
    let params = new HttpParams();
    if (de) params = params.set('de', de);
    if (ate) params = params.set('ate', ate);
    return this.http.get<Relatorio>(`${this.base}/relatorios/${tipo}`, { params });
  }

  // ---- cadastros
  criarEtapa(dados: { nome: string; ordem: number | null }) {
    return this.http.post<Etapa>(`${this.base}/etapas`, dados);
  }

  alterarEtapa(id: number, dados: { nome: string; ordem: number | null }) {
    return this.http.put<Etapa>(`${this.base}/etapas/${id}`, dados);
  }

  excluirEtapa(id: number) {
    return this.http.delete<void>(`${this.base}/etapas/${id}`);
  }

  componentes(incluirInativos = false): Observable<Componente[]> {
    return this.http.get<Componente[]>(`${this.base}/componentes`, { params: this.inativos(incluirInativos) });
  }

  criarComponente(dados: { sku: string; nome: string; estoque: number }) {
    return this.http.post<Componente>(`${this.base}/componentes`, dados);
  }

  alterarComponente(id: number, dados: Partial<Pick<Componente, 'sku' | 'nome' | 'estoque' | 'ativo'>>) {
    return this.http.patch<Componente>(`${this.base}/componentes/${id}`, dados);
  }

  modelos(incluirInativos = false): Observable<Modelo[]> {
    return this.http.get<Modelo[]>(`${this.base}/modelos`, { params: this.inativos(incluirInativos) });
  }

  criarModelo(dados: DadosModelo) {
    return this.http.post<Modelo>(`${this.base}/modelos`, dados);
  }

  alterarModelo(id: number, dados: Partial<DadosModelo> & { ativo?: boolean }) {
    return this.http.patch<Modelo>(`${this.base}/modelos/${id}`, dados);
  }

  // ---- produções
  producoes(filtro: { busca?: string; etapa_id?: number; modelo_id?: number } = {}): Observable<Producao[]> {
    let params = new HttpParams();
    for (const [chave, valor] of Object.entries(filtro)) {
      if (valor !== undefined && valor !== null && valor !== '' && valor !== 0) params = params.set(chave, String(valor));
    }
    return this.http.get<Producao[]>(`${this.base}/producoes`, { params });
  }

  producao(id: number): Observable<ProducaoDetalhe> {
    return this.http.get<ProducaoDetalhe>(`${this.base}/producoes/${id}`);
  }

  criarProducao(dados: { modelo_id: number; responsavel_id: number | null }) {
    return this.http.post<ProducaoDetalhe>(`${this.base}/producoes`, dados);
  }

  alterarProducao(id: number, dados: { modelo_id: number; responsavel_id: number | null }) {
    return this.http.put<ProducaoDetalhe>(`${this.base}/producoes/${id}`, dados);
  }

  excluirProducao(id: number) {
    return this.http.delete<void>(`${this.base}/producoes/${id}`);
  }

  mudarEtapa(id: number, dados: { etapa_id: number; responsavel_id: number | null; descricao_falha?: string; motivo_reprovacao?: string }) {
    return this.http.post<ProducaoDetalhe>(`${this.base}/producoes/${id}/etapa`, dados);
  }

  registrarNaoConformidade(id: number, dados: { descricao_falha: string; motivo_reprovacao: string }) {
    return this.http.post<ProducaoDetalhe>(`${this.base}/producoes/${id}/nao-conformidades`, dados);
  }

  solicitarMateriais(id: number) {
    return this.http.post<{ criadas: number; ignoradas: number }>(`${this.base}/producoes/${id}/solicitar-materiais`, {});
  }

  // ---- materiais
  solicitacoes(status?: StatusSolicitacao | null, producaoId?: number | null): Observable<Solicitacao[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    if (producaoId) params = params.set('producao_id', producaoId);
    return this.http.get<Solicitacao[]>(`${this.base}/solicitacoes`, { params });
  }

  alterarSolicitacao(id: number, dados: { quantidade: number; cancelada: boolean }) {
    return this.http.put<Solicitacao>(`${this.base}/solicitacoes/${id}`, dados);
  }

  excluirSolicitacao(id: number) {
    return this.http.delete<void>(`${this.base}/solicitacoes/${id}`);
  }

  baixas(): Observable<Baixa[]> {
    return this.http.get<Baixa[]>(`${this.base}/baixas`);
  }

  baixar(solicitacaoId: number, quantidade: number) {
    return this.http.post<Baixa>(`${this.base}/baixas`, { solicitacao_id: solicitacaoId, quantidade });
  }

  alterarBaixa(id: number, quantidade: number) {
    return this.http.put<Baixa>(`${this.base}/baixas/${id}`, { quantidade });
  }

  excluirBaixa(id: number) {
    return this.http.delete<void>(`${this.base}/baixas/${id}`);
  }

  private inativos(incluir: boolean): HttpParams | undefined {
    return incluir ? new HttpParams().set('incluir_inativos', 'true') : undefined;
  }
}
