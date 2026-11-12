import { HttpErrorResponse } from '@angular/common/http';

/** Converte um erro HTTP da API numa frase para mostrar ao usuário. */
export function mensagemDeErro(erro: unknown): string {
  if (!(erro instanceof HttpErrorResponse)) {
    return 'Ocorreu um erro inesperado.';
  }
  if (erro.status === 0) {
    return 'Não foi possível falar com o servidor. Verifique se a API está no ar.';
  }
  const detalhe = erro.error?.detail;
  if (typeof detalhe === 'string') {
    return detalhe;
  }
  // 422 do FastAPI: lista de erros de validação
  if (Array.isArray(detalhe) && detalhe.length > 0) {
    const primeiro = detalhe[0];
    const campo = Array.isArray(primeiro.loc) ? primeiro.loc.at(-1) : '';
    return campo ? `${campo}: ${primeiro.msg}` : primeiro.msg;
  }
  return `Erro ${erro.status} ao falar com o servidor.`;
}
