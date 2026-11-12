import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { FUSO_FABRICA } from '../../manutencao/mnt.modelos';
import { Baixa, ROTULO_SOLICITACAO, Solicitacao, StatusSolicitacao, TOM_SOLICITACAO } from '../ras.modelos';
import { RasService } from '../ras.service';

/** Saldo que ainda falta entregar numa solicitação. */
export function saldo(s: Solicitacao): number {
  return s.quantidade - s.quantidade_baixada;
}

/** Quanto dá para baixar agora: o saldo, limitado ao estoque. */
export function sugestaoBaixa(s: Solicitacao): number {
  return Math.max(0, Math.min(saldo(s), s.estoque));
}

/** Fila do almoxarifado: solicitações de material por produção e baixas no estoque. */
@Component({
  selector: 'am-materiais',
  imports: [FormsModule, RouterLink, DatePipe, Etiqueta],
  template: `
    <div class="pagina">
      <div>
        <h1 class="titulo-tela">Materiais</h1>
        <p class="legenda">A baixa tira do estoque e não passa do saldo da solicitação nem do estoque disponível.
          Alterar ou excluir uma baixa devolve a diferença ao estoque.</p>
      </div>

      <div class="abas" role="tablist">
        <button type="button" role="tab" [attr.aria-selected]="aba() === 'solicitacoes'" [class.ativa]="aba() === 'solicitacoes'" (click)="trocar('solicitacoes')">Solicitações</button>
        <button type="button" role="tab" [attr.aria-selected]="aba() === 'baixas'" [class.ativa]="aba() === 'baixas'" (click)="trocar('baixas')">Baixas</button>
      </div>

      <div aria-live="polite">
        @if (aviso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      </div>

      @if (aba() === 'solicitacoes') {
        <div class="filtro">
          <label class="campo"><span>Situação</span>
            <select [ngModel]="status()" (ngModelChange)="status.set($event); carregar()">
              <option value="">Em aberto (pendente ou parcial)</option>
              @for (s of todosStatus; track s) { <option [value]="s">{{ rotulo[s] }}</option> }
            </select></label>
        </div>
        <section class="cartao tabela-rolagem">
          @if (solicitacoes().length) {
            <table class="tabela">
              <thead><tr><th scope="col">Nº</th><th scope="col">Notebook</th><th scope="col">Componente</th>
                <th scope="col" class="num">Pedida</th><th scope="col" class="num">Entregue</th><th scope="col" class="num">Estoque</th>
                <th scope="col">Situação</th><th scope="col">Pedido</th><th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>
                @for (s of solicitacoes(); track s.id) {
                  <tr>
                    <td class="codigo">{{ s.id }}</td>
                    <td><a class="codigo" [routerLink]="['/rastreabilidade/producoes', s.producao_id]">{{ s.numero_serie }}</a></td>
                    <td><span class="codigo">{{ s.sku }}</span> {{ s.componente_nome }}</td>
                    <td class="num">{{ s.quantidade }}</td><td class="num">{{ s.quantidade_baixada }}</td>
                    <td class="num" [class.falta]="s.estoque < saldo(s)">{{ s.estoque }}</td>
                    <td><am-etiqueta [texto]="rotulo[s.status]" [tom]="tom[s.status]" /></td>
                    <td class="nowrap">{{ s.criada_em | date: 'dd/MM HH:mm' : fuso }}<br /><span class="legenda">{{ s.solicitante_nome }}</span></td>
                    <td class="acoes">
                      @if (permissoes()?.baixar && s.status !== 'CANCELADA' && saldo(s) > 0) {
                        <label class="so-leitor" [for]="'qtd-' + s.id">Quantidade a baixar</label>
                        <input class="qtd" type="number" min="1" [max]="saldo(s)" [id]="'qtd-' + s.id" [(ngModel)]="quantidades[s.id]" />
                        <button type="button" class="btn pequeno primario" [disabled]="ocupado()" (click)="baixar(s)">Dar baixa</button>
                      }
                      @if (permissoes()?.solicitar && s.status !== 'CANCELADA' && s.status !== 'ATENDIDA') {
                        <button type="button" class="btn pequeno perigo" [disabled]="ocupado()" (click)="cancelar(s)">Cancelar</button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          } @else { <p class="legenda">Nenhuma solicitação nessa situação.</p> }
        </section>
      } @else {
        <section class="cartao tabela-rolagem">
          @if (baixas().length) {
            <table class="tabela">
              <thead><tr><th scope="col">Data</th><th scope="col">Notebook</th><th scope="col">Componente</th>
                <th scope="col" class="num">Quantidade</th><th scope="col">Por</th><th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
              <tbody>
                @for (b of baixas(); track b.id) {
                  <tr>
                    <td class="nowrap">{{ b.registrada_em | date: 'dd/MM HH:mm' : fuso }}</td>
                    <td class="codigo">{{ b.numero_serie }}</td>
                    <td><span class="codigo">{{ b.sku }}</span> {{ b.componente_nome }}</td>
                    <td class="num">{{ b.quantidade }}</td>
                    <td>{{ b.usuario_nome }}</td>
                    <td class="acoes">
                      @if (permissoes()?.baixar) {
                        <button type="button" class="btn pequeno" [disabled]="ocupado()" (click)="alterarBaixa(b)">Alterar</button>
                        <button type="button" class="btn pequeno perigo" [disabled]="ocupado()" (click)="excluirBaixa(b)">Excluir</button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          } @else { <p class="legenda">Nenhuma baixa registrada.</p> }
        </section>
      }
    </div>
  `,
  styles: `
    .abas { display: flex; gap: var(--space-1); border-bottom: 1px solid var(--linha); }
    .abas button {
      background: none; border: 0; border-bottom: 3px solid transparent; padding: var(--space-2) var(--space-4);
      font: inherit; font-weight: 600; color: var(--tinta-2); cursor: pointer;
      &.ativa { color: var(--sinal); border-bottom-color: var(--sinal); }
    }
    .filtro { max-width: 320px; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .falta { color: var(--critico); font-weight: 600; }
    .nowrap { white-space: nowrap; }
    .acoes { display: flex; flex-wrap: wrap; gap: var(--space-1); align-items: center; }
    .qtd { width: 72px; }
  `,
})
export class Materiais implements OnInit {
  private readonly ras = inject(RasService);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly rotulo = ROTULO_SOLICITACAO;
  protected readonly tom = TOM_SOLICITACAO;
  protected readonly todosStatus: StatusSolicitacao[] = ['PENDENTE', 'PARCIAL', 'ATENDIDA', 'CANCELADA'];
  protected readonly saldo = saldo;

  protected readonly aba = signal<'solicitacoes' | 'baixas'>('solicitacoes');
  protected readonly status = signal<StatusSolicitacao | ''>('');
  protected readonly solicitacoes = signal<Solicitacao[]>([]);
  protected readonly baixas = signal<Baixa[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly aviso = signal<string | null>(null);
  protected readonly permissoes = computed(() => this.ras.opcoes()?.permissoes);
  protected quantidades: Record<number, number> = {};

  async ngOnInit(): Promise<void> {
    try {
      await this.ras.carregarOpcoes();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
    await this.carregar();
  }

  protected trocar(aba: 'solicitacoes' | 'baixas'): void {
    this.aba.set(aba);
    this.aviso.set(null);
    this.erro.set(null);
    void this.carregar();
  }

  protected async carregar(): Promise<void> {
    try {
      if (this.aba() === 'baixas') {
        this.baixas.set(await firstValueFrom(this.ras.baixas()));
        return;
      }
      const status = this.status();
      const lista = status
        ? await firstValueFrom(this.ras.solicitacoes(status))
        : (await firstValueFrom(this.ras.solicitacoes())).filter((s) => s.status === 'PENDENTE' || s.status === 'PARCIAL');
      this.quantidades = Object.fromEntries(lista.map((s) => [s.id, sugestaoBaixa(s) || saldo(s)]));
      this.solicitacoes.set(lista);
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  protected baixar(s: Solicitacao): Promise<void> {
    const qtd = Number(this.quantidades[s.id]);
    if (!Number.isInteger(qtd) || qtd < 1) {
      this.erro.set('Informe uma quantidade inteira maior que zero.');
      return Promise.resolve();
    }
    return this.executar(this.ras.baixar(s.id, qtd), `Baixa de ${qtd} × ${s.sku} para ${s.numero_serie}.`);
  }

  protected cancelar(s: Solicitacao): Promise<void> {
    if (!confirm(`Cancelar a solicitação nº ${s.id} (${s.sku} para ${s.numero_serie})?`)) return Promise.resolve();
    return this.executar(this.ras.alterarSolicitacao(s.id, { quantidade: s.quantidade, cancelada: true }), `Solicitação nº ${s.id} cancelada.`);
  }

  protected alterarBaixa(b: Baixa): Promise<void> {
    const texto = prompt(`Nova quantidade da baixa de ${b.sku} (${b.numero_serie}):`, String(b.quantidade));
    if (texto === null) return Promise.resolve();
    const qtd = Number(texto);
    if (!Number.isInteger(qtd) || qtd < 1) {
      this.erro.set('Informe uma quantidade inteira maior que zero.');
      return Promise.resolve();
    }
    return this.executar(this.ras.alterarBaixa(b.id, qtd), 'Baixa alterada; a diferença voltou ao estoque.');
  }

  protected excluirBaixa(b: Baixa): Promise<void> {
    if (!confirm(`Excluir a baixa de ${b.quantidade} × ${b.sku}? A quantidade volta ao estoque.`)) return Promise.resolve();
    return this.executar(this.ras.excluirBaixa(b.id), 'Baixa excluída; a quantidade voltou ao estoque.');
  }

  private async executar(acao: Observable<unknown>, mensagem: string): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.aviso.set(null);
    try {
      await firstValueFrom(acao);
      this.aviso.set(mensagem);
      await this.carregar();
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }
}
