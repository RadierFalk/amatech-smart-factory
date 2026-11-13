import { DatePipe, formatDate } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../core/erros';
import { Etiqueta, Tom } from '../../shared/etiqueta';
import { FUSO_FABRICA } from '../manutencao/mnt.modelos';

export type AcaoAuditoria = 'CRIOU' | 'ALTEROU' | 'EXCLUIU';

/** Linha de /api/auditoria (espelha backend/app/modulos/auditoria/rotas.py). */
export interface RegistroAuditoria {
  id: number;
  registrada_em: string;
  usuario_matricula: string | null;
  usuario_nome: string | null;
  modulo: string;
  entidade: string;
  entidade_id: string;
  descricao: string;
  acao: AcaoAuditoria;
  alteracoes: Record<string, [unknown, unknown]>;
}

const ROTULO_ACAO: Record<AcaoAuditoria, string> = { CRIOU: 'Criou', ALTEROU: 'Alterou', EXCLUIU: 'Excluiu' };
const TOM_ACAO: Record<AcaoAuditoria, Tom> = { CRIOU: 'info', ALTEROU: 'atencao', EXCLUIU: 'critico' };
const MODULOS = ['RAS', 'QLD', 'MNT', 'DSH', 'USR'];
const LIMITE = 200;
const DATA_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;

/** Dia da fábrica (Manaus) no formato do campo date, deslocado em dias. */
function diaNaFabrica(deslocamento = 0, agora = new Date()): string {
  return formatDate(new Date(agora.getTime() + deslocamento * 86_400_000), 'yyyy-MM-dd', 'en-US', FUSO_FABRICA);
}

/** Valor de um campo para leitura: vazio vira "—", sim/não, datas no horário da fábrica. */
export function valorLegivel(valor: unknown): string {
  if (valor === null || valor === undefined || valor === '') return '—';
  if (typeof valor === 'boolean') return valor ? 'Sim' : 'Não';
  if (typeof valor === 'string' && DATA_ISO.test(valor)) return formatDate(valor, 'dd/MM/yyyy HH:mm', 'en-US', FUSO_FABRICA);
  return String(valor);
}

/** "tipo_defeito_id" -> "Tipo defeito id". */
export function nomeDoCampo(campo: string): string {
  const texto = campo.replace(/_/g, ' ');
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Trilha de auditoria de todos os módulos (Administrador e Supervisor). Só consulta. */
@Component({
  selector: 'am-auditoria',
  imports: [DatePipe, FormsModule, Etiqueta],
  template: `
    <div class="pagina">
      <div>
        <span class="selo-setor aud">AUD</span>
        <h1 class="titulo-tela">Auditoria</h1>
        <p class="legenda">Quem criou, alterou ou excluiu cada registro, em todos os módulos, com os valores antes e depois.
          Senhas nunca aparecem aqui.</p>
      </div>

      <form class="cartao filtros" (ngSubmit)="carregar()" aria-label="Filtros da auditoria">
        <label class="campo"><span>De</span><input type="date" name="de" [(ngModel)]="de" [max]="ate" /></label>
        <label class="campo"><span>Até</span><input type="date" name="ate" [(ngModel)]="ate" [min]="de" /></label>
        <label class="campo"><span>Módulo</span>
          <select name="modulo" [(ngModel)]="modulo">
            <option value="">Todos</option>
            @for (m of modulos; track m) { <option [value]="m">{{ m }}</option> }
          </select></label>
        <label class="campo"><span>Ação</span>
          <select name="acao" [(ngModel)]="acao">
            <option value="">Todas</option>
            @for (a of acoes; track a) { <option [value]="a">{{ rotuloAcao[a] }}</option> }
          </select></label>
        <label class="campo busca"><span>Registro ou pessoa</span>
          <input type="search" name="busca" [(ngModel)]="busca" placeholder="Ex.: AMT-000025, OS #9, Maria" /></label>
        <div class="acoes"><button type="submit" class="btn primario" [disabled]="carregando()">Filtrar</button></div>
      </form>

      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }

      <section class="cartao">
        @if (carregando()) {
          <p class="legenda" role="status">Carregando a trilha…</p>
        } @else if (registros().length) {
          <p class="legenda">{{ registros().length === limite ? 'Mostrando os ' + limite + ' mais recentes: refine o filtro para ver mais.'
            : registros().length + ' registro(s).' }}</p>
          <div class="tabela-rolagem">
            <table class="tabela">
              <thead><tr><th scope="col">Quando</th><th scope="col">Quem</th><th scope="col">Módulo</th><th scope="col">Ação</th>
                <th scope="col">Registro</th><th scope="col">O que mudou</th></tr></thead>
              <tbody>
                @for (r of registros(); track r.id) {
                  <tr>
                    <td class="quando">{{ r.registrada_em | date: 'dd/MM/yyyy HH:mm' : fuso }}</td>
                    <td>@if (r.usuario_nome) { {{ r.usuario_nome }} <span class="codigo legenda">{{ r.usuario_matricula }}</span> }
                      @else { <span class="legenda">Sistema</span> }</td>
                    <td><span class="selo-setor" [class]="'selo-setor ' + r.modulo.toLowerCase()">{{ r.modulo }}</span></td>
                    <td><am-etiqueta [texto]="rotuloAcao[r.acao]" [tom]="tomAcao[r.acao]" /></td>
                    <td>{{ r.descricao }}</td>
                    <td class="mudancas">
                      <details>
                        <summary>{{ campos(r).length }} campo(s)</summary>
                        <dl>
                          @for (c of campos(r); track c) {
                            <div class="mudanca">
                              <dt>{{ nomeDoCampo(c) }}</dt>
                              <dd>
                                @if (r.acao !== 'CRIOU') { <span class="antes">{{ valorLegivel(r.alteracoes[c][0]) }}</span> }
                                @if (r.acao === 'ALTEROU') { <span aria-hidden="true">→</span><span class="so-leitor">para</span> }
                                @if (r.acao !== 'EXCLUIU') { <span class="depois">{{ valorLegivel(r.alteracoes[c][1]) }}</span> }
                              </dd>
                            </div>
                          }
                        </dl>
                      </details>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <p class="legenda">Nada registrado com esses filtros.</p>
        }
      </section>
    </div>
  `,
  styles: `
    .filtros { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: flex-end; }
    .filtros .campo { flex: 1 1 150px; max-width: 220px; }
    .filtros .busca { flex: 2 1 240px; max-width: 360px; }
    .quando { white-space: nowrap; font-variant-numeric: tabular-nums; }
    .mudancas { min-width: 260px; }
    summary { cursor: pointer; color: var(--sinal); }
    dl { margin: var(--space-2) 0 0; display: grid; gap: var(--space-1); }
    .mudanca { display: grid; grid-template-columns: minmax(110px, auto) 1fr; gap: var(--space-2); font-size: 13px; }
    dt { color: var(--tinta-2); }
    dd { margin: 0; display: flex; flex-wrap: wrap; gap: var(--space-1); align-items: baseline; overflow-wrap: anywhere; }
    .antes { color: var(--tinta-2); text-decoration: line-through; }
    .depois { font-weight: 600; }
  `,
})
export class Auditoria implements OnInit {
  private readonly http = inject(HttpClient);

  protected readonly fuso = FUSO_FABRICA;
  protected readonly modulos = MODULOS;
  protected readonly acoes: AcaoAuditoria[] = ['CRIOU', 'ALTEROU', 'EXCLUIU'];
  protected readonly rotuloAcao = ROTULO_ACAO;
  protected readonly tomAcao = TOM_ACAO;
  protected readonly limite = LIMITE;
  protected readonly valorLegivel = valorLegivel;
  protected readonly nomeDoCampo = nomeDoCampo;

  protected de = diaNaFabrica(-6);
  protected ate = diaNaFabrica();
  protected modulo = '';
  protected acao = '';
  protected busca = '';

  protected readonly registros = signal<RegistroAuditoria[]>([]);
  protected readonly carregando = signal(false);
  protected readonly erro = signal<string | null>(null);

  ngOnInit(): void {
    void this.carregar();
  }

  protected campos(r: RegistroAuditoria): string[] {
    return Object.keys(r.alteracoes);
  }

  protected async carregar(): Promise<void> {
    let params = new HttpParams().set('limite', LIMITE);
    for (const [chave, valor] of Object.entries({ de: this.de, ate: this.ate, modulo: this.modulo, acao: this.acao, busca: this.busca.trim() })) {
      if (valor) params = params.set(chave, valor);
    }
    this.carregando.set(true);
    this.erro.set(null);
    try {
      this.registros.set(await firstValueFrom(this.http.get<RegistroAuditoria[]>('/api/auditoria', { params })));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.carregando.set(false);
    }
  }
}
