import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable, firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { Limite, Turno } from '../dsh.modelos';
import { DshService } from '../dsh.service';

/** Configuração do Dashboard (T09): turnos, tipos de perda e limites do semáforo (UC16). */
@Component({
  selector: 'am-configuracao-dsh',
  imports: [FormsModule, Etiqueta],
  template: `
    <div class="pagina">
      <h1 class="titulo-tela">Configuração</h1>

      <div aria-live="polite">
        @if (sucesso(); as m) { <div class="aviso sucesso" role="status">{{ m }}</div> }
        @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      </div>

      <section class="cartao">
        <h2 class="titulo-secao">Limites do semáforo</h2>
        <p class="legenda">Maior é melhor (atendimento da meta): verde a partir do primeiro limite, amarelo a partir do segundo.
          Menor é melhor (defeitos, retrabalho): verde até o primeiro limite, amarelo até o segundo. Acima ou abaixo disso, vermelho.</p>
        <div class="tabela-rolagem"><table class="tabela">
          <thead><tr><th scope="col">Indicador</th><th scope="col">Sentido</th><th scope="col">Verde (%)</th><th scope="col">Amarelo (%)</th>
            <th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
          <tbody>@for (l of limites(); track l.indicador) {
            <tr>
              <td>{{ l.nome }}</td>
              <td>{{ l.sentido === 'maior_melhor' ? 'Maior é melhor' : 'Menor é melhor' }}</td>
              <td><input class="num-campo" type="number" min="0" step="0.5" [(ngModel)]="l.limite_verde" [attr.aria-label]="'Verde de ' + l.nome" /></td>
              <td><input class="num-campo" type="number" min="0" step="0.5" [(ngModel)]="l.limite_amarelo" [attr.aria-label]="'Amarelo de ' + l.nome" /></td>
              <td><button type="button" class="btn pequeno primario" [disabled]="ocupado()" (click)="salvarLimite(l)">Salvar</button></td>
            </tr>
          }</tbody>
        </table></div>
      </section>

      <section class="cartao">
        <h2 class="titulo-secao">Turnos</h2>
        <p class="legenda">Eventos fora dos turnos não entram nos indicadores. Os turnos não podem se sobrepor.</p>
        <div class="tabela-rolagem"><table class="tabela">
          <thead><tr><th scope="col">Nome</th><th scope="col">Início</th><th scope="col">Fim</th><th scope="col"><span class="so-leitor">Ações</span></th></tr></thead>
          <tbody>@for (t of turnos(); track t.id) {
            <tr>
              <td><input [(ngModel)]="t.nome" [attr.aria-label]="'Nome do turno ' + t.id" /></td>
              <td><input type="time" [(ngModel)]="t.hora_inicio" [attr.aria-label]="'Início de ' + t.nome" /></td>
              <td><input type="time" [(ngModel)]="t.hora_fim" [attr.aria-label]="'Fim de ' + t.nome" /></td>
              <td><button type="button" class="btn pequeno primario" [disabled]="ocupado()" (click)="salvarTurno(t)">Salvar</button></td>
            </tr>
          }</tbody>
        </table></div>
      </section>

      <section class="cartao">
        <h2 class="titulo-secao">Tipos de perda</h2>
        <form class="novo" (ngSubmit)="criarTipo()">
          <label class="campo"><span>Novo tipo</span><input name="novoTipo" [(ngModel)]="novoTipo" /></label>
          <button type="submit" class="btn primario" [disabled]="ocupado() || !novoTipo.trim()">Cadastrar</button>
        </form>
        <ul class="tipos">
          @for (t of opcoes()?.tipos_perda ?? []; track t.id) {
            <li><span>{{ t.nome }}</span> <am-etiqueta [texto]="t.ativo ? 'Ativo' : 'Inativo'" [tom]="t.ativo ? 'ok' : 'neutro'" />
              <button type="button" class="btn pequeno" [class.perigo]="t.ativo" [disabled]="ocupado()" (click)="alternarTipo(t.id, !t.ativo)">
                {{ t.ativo ? 'Inativar' : 'Reativar' }}</button></li>
          }
        </ul>
      </section>
    </div>
  `,
  styles: `
    .num-campo { width: 96px; }
    .novo { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: flex-end; margin-bottom: var(--space-3); }
    .tipos { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-2); }
    .tipos li { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
  `,
})
export class ConfiguracaoDsh implements OnInit {
  private readonly dsh = inject(DshService);
  protected readonly opcoes = this.dsh.opcoes;
  // Cópias editáveis (o cache de /opcoes só muda depois de salvar).
  protected readonly limites = signal<Limite[]>([]);
  protected readonly turnos = signal<Turno[]>([]);
  protected readonly ocupado = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);
  protected novoTipo = '';

  async ngOnInit(): Promise<void> {
    try {
      this.copiar(await this.dsh.carregarOpcoes(true));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
  }

  private copiar(o: { limites: Limite[]; turnos: Turno[] }): void {
    this.limites.set(o.limites.map((l) => ({ ...l })));
    this.turnos.set(o.turnos.map((t) => ({ ...t })));
  }

  protected salvarLimite(l: Limite): Promise<void> {
    return this.executar(this.dsh.salvarLimites(l.indicador, { limite_verde: Number(l.limite_verde), limite_amarelo: Number(l.limite_amarelo) }),
      `Limites de ${l.nome} salvos.`);
  }

  protected salvarTurno(t: Turno): Promise<void> {
    return this.executar(this.dsh.alterarTurno(t.id, { nome: t.nome, hora_inicio: t.hora_inicio, hora_fim: t.hora_fim }), `${t.nome} salvo.`);
  }

  protected async criarTipo(): Promise<void> {
    await this.executar(this.dsh.criarTipoPerda(this.novoTipo.trim()), `Tipo de perda "${this.novoTipo.trim()}" cadastrado.`);
    if (!this.erro()) this.novoTipo = '';
  }

  protected alternarTipo(id: number, ativo: boolean): Promise<void> {
    return this.executar(this.dsh.alterarTipoPerda(id, ativo), ativo ? 'Tipo de perda reativado.' : 'Tipo de perda inativado.');
  }

  private async executar(acao: Observable<unknown>, mensagem: string): Promise<void> {
    this.ocupado.set(true);
    this.erro.set(null);
    this.sucesso.set(null);
    try {
      await firstValueFrom(acao);
      this.sucesso.set(mensagem);
      this.copiar(await this.dsh.carregarOpcoes(true));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.ocupado.set(false);
    }
  }
}
