import { HttpErrorResponse } from '@angular/common/http';

import { mensagemDeErro } from '../core/erros';
import { tomPeloTexto } from './etiqueta';

describe('tomPeloTexto', () => {
  it.each([
    ['Ativo', 'ok'],
    ['Inativo', 'critico'],
    ['Reprovado', 'critico'],
    ['Em manutenção', 'atencao'],
    ['Aprovado', 'ok'],
    ['Em fila', 'neutro'],
    ['Qualquer', 'info'],
  ])('%s → %s', (texto, tom) => {
    expect(tomPeloTexto(texto)).toBe(tom);
  });
});

describe('mensagemDeErro', () => {
  it('usa o detail em texto da API', () => {
    const e = new HttpErrorResponse({ status: 409, error: { detail: 'Matrícula já cadastrada.' } });
    expect(mensagemDeErro(e)).toBe('Matrícula já cadastrada.');
  });

  it('resume o 422 do FastAPI pelo primeiro campo', () => {
    const e = new HttpErrorResponse({
      status: 422,
      error: { detail: [{ loc: ['body', 'senha'], msg: 'String should have at least 8 characters' }] },
    });
    expect(mensagemDeErro(e)).toBe('senha: String should have at least 8 characters');
  });

  it('avisa quando o servidor está fora do ar', () => {
    expect(mensagemDeErro(new HttpErrorResponse({ status: 0 }))).toContain('Não foi possível falar com o servidor');
  });
});
