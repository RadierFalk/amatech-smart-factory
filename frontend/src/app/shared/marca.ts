import { Component, input } from '@angular/core';

/** Símbolo + nome AMATECH. Só sobre fundo `noite` (o LED do símbolo não lê sobre fundo claro). */
@Component({
  selector: 'am-marca',
  template: `
    <img src="amatech-simbolo.svg" alt="" [width]="tamanho()" [height]="tamanho()" />
    <span class="nome">AMATECH</span>
  `,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      color: var(--on-noite);
    }
    .nome {
      font-family: var(--font-display);
      font-size: 18px;
      line-height: 22px;
      font-weight: 700;
      letter-spacing: 0.08em;
    }
  `,
})
export class Marca {
  readonly tamanho = input(32);
}
