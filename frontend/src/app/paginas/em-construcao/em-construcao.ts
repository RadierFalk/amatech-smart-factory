import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

/** Marcador das telas dos módulos cuja API ainda não foi portada para o backend único. */
@Component({
  selector: 'am-em-construcao',
  imports: [RouterLink],
  template: `
    <div class="pagina">
      <div>
        <span class="selo-setor" [class]="sigla().toLowerCase()">{{ sigla() }}</span>
        <h1 class="titulo-tela">{{ nome() }}</h1>
      </div>
      <div class="aviso info" role="status">
        Este módulo está sendo migrado para o novo ERP. As telas aparecem aqui assim que a API dele estiver pronta.
      </div>
      <a class="btn" routerLink="/">Voltar ao hub</a>
    </div>
  `,
  styles: `.btn { justify-self: start; }`,
})
export class EmConstrucao {
  // Preenchidos pelo `data` da rota (withComponentInputBinding).
  readonly sigla = input('');
  readonly nome = input('');
}
