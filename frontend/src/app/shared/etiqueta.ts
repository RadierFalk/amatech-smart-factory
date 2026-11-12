import { Component, computed, input } from '@angular/core';

export type Tom = 'ok' | 'atencao' | 'critico' | 'neutro' | 'info';

/**
 * Etiqueta de estado (Ativo, Reprovado, Em manutenção...). A cor nunca é a única pista:
 * o texto vai sempre junto. Sem `tom`, ele é deduzido do texto, como em identidade/amatech.py.
 */
@Component({
  selector: 'am-etiqueta',
  template: '<span class="etiqueta" [class]="tomFinal()">{{ texto() }}</span>',
  styles: `
    .etiqueta {
      display: inline-block;
      padding: 2px 10px;
      border-radius: var(--radius-pill);
      font-size: 12px;
      font-weight: 600;
      line-height: 18px;
      white-space: nowrap;
    }
    .ok { background: var(--ok-suave); color: var(--ok); }
    .atencao { background: var(--atencao-suave); color: var(--atencao); }
    .critico { background: var(--critico-suave); color: var(--critico); }
    .neutro { background: var(--neutro-suave); color: var(--tinta-2); }
    .info { background: var(--sinal-suave); color: var(--sinal-forte); }
  `,
})
export class Etiqueta {
  readonly texto = input.required<string>();
  readonly tom = input<Tom | undefined>(undefined);

  protected readonly tomFinal = computed<Tom>(() => this.tom() ?? tomPeloTexto(this.texto()));
}

export function tomPeloTexto(texto: string): Tom {
  const t = texto.toLowerCase();
  if (/(reprovad|parad|indispon|crític|critic|inativ|bloquead|erro)/.test(t)) return 'critico';
  if (/(manuten|reprocesso|alta|atenção|atencao|pendente)/.test(t)) return 'atencao';
  if (/(aprovad|funcionando|ativ|ok|concluíd|concluid)/.test(t)) return 'ok';
  if (/(fila|baixa|cancelad)/.test(t)) return 'neutro';
  return 'info';
}
