import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensagemDeErro } from '../../../core/erros';
import { Etiqueta } from '../../../shared/etiqueta';
import { Auditoria, Equipamento, FUSO_FABRICA, ROTULO_STATUS_EQUIPAMENTO, TOM_STATUS_EQUIPAMENTO } from '../mnt.modelos';
import { MntService } from '../mnt.service';

/** Trilha de auditoria das mudanças de status das máquinas (RN08): quem mudou, quando e por qual OS. */
@Component({
  selector: 'am-auditoria-mnt',
  imports: [DatePipe, RouterLink, Etiqueta],
  template: `
    <div class="pagina">
      <div class="pagina-topo">
        <div>
          <h1 class="titulo-tela">Auditoria de status</h1>
          <p class="legenda">Registro imutável de cada mudança de status das máquinas (últimos 200).</p>
        </div>
        <label class="campo filtro"><span>Máquina</span>
          <select (change)="filtrar($any($event.target).value)">
            <option value="">Todas</option>
            @for (e of maquinas(); track e.id) { <option [value]="e.id">{{ e.codigo_tag }} · {{ e.nome }}</option> }
          </select>
        </label>
      </div>
      @if (erro(); as m) { <div class="aviso erro" role="alert">{{ m }}</div> }
      <section class="cartao tabela-rolagem">
        <table class="tabela">
          <thead><tr><th scope="col">Quando</th><th scope="col">Máquina</th><th scope="col">De</th><th scope="col">Para</th>
            <th scope="col">Por</th><th scope="col">OS</th></tr></thead>
          <tbody>
            @for (a of linhas(); track a.id) {
              <tr>
                <td>{{ a.alterado_em | date: 'dd/MM/yyyy HH:mm:ss' : fuso }}</td>
                <td class="codigo">{{ a.equipamento_tag }}</td>
                <td><am-etiqueta [texto]="rotulo[a.status_anterior]" [tom]="tom[a.status_anterior]" /></td>
                <td><am-etiqueta [texto]="rotulo[a.status_novo]" [tom]="tom[a.status_novo]" /></td>
                <td>{{ a.usuario_nome }} <span class="legenda">({{ a.usuario_perfil }})</span></td>
                <td>@if (a.chamado_id) { <a class="codigo" [routerLink]="['../ordens', a.chamado_id]">#{{ a.chamado_id }}</a> } @else { — }</td>
              </tr>
            } @empty { <tr><td colspan="6" class="legenda">Nenhuma mudança registrada.</td></tr> }
          </tbody>
        </table>
      </section>
    </div>
  `,
  styles: `.filtro { min-width: 260px; }`,
})
export class AuditoriaMnt implements OnInit {
  private readonly mnt = inject(MntService);
  protected readonly fuso = FUSO_FABRICA;
  protected readonly rotulo = ROTULO_STATUS_EQUIPAMENTO;
  protected readonly tom = TOM_STATUS_EQUIPAMENTO;
  protected readonly linhas = signal<Auditoria[]>([]);
  protected readonly maquinas = signal<Equipamento[]>([]);
  protected readonly erro = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    try {
      this.maquinas.set(await firstValueFrom(this.mnt.equipamentos(null, true)));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    }
    this.filtrar('');
  }

  protected filtrar(id: string): void {
    this.mnt.auditoria(id ? Number(id) : null).subscribe({
      next: (l) => this.linhas.set(l),
      error: (e) => this.erro.set(mensagemDeErro(e)),
    });
  }
}
