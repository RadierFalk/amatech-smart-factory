// Comunicação com a API FastAPI (fetch + token de login).
let tokenMemoria = null;
let aoNaoAutorizado = () => {};

export class ErroApi extends Error {
  constructor(mensagem, status) { super(mensagem); this.status = status; }
}

export function guardarToken(t) {
  tokenMemoria = t;
  try { t ? sessionStorage.setItem('amatech_token', t) : sessionStorage.removeItem('amatech_token'); } catch { /* sem storage */ }
}
export function lerToken() {
  if (tokenMemoria) return tokenMemoria;
  try { return sessionStorage.getItem('amatech_token'); } catch { return null; }
}
export function quandoNaoAutorizado(fn) { aoNaoAutorizado = fn; }

async function requisitar(metodo, url, corpo) {
  const headers = {};
  const token = lerToken();
  if (token) headers.Authorization = 'Bearer ' + token;
  const opcoes = { method: metodo, headers };
  if (corpo !== undefined) { headers['Content-Type'] = 'application/json'; opcoes.body = JSON.stringify(corpo); }
  let resp;
  try { resp = await fetch(url, opcoes); }
  catch { throw new ErroApi('Não foi possível conectar ao servidor. Verifique se o sistema está em execução.', 0); }
  if (resp.status === 401 && !url.includes('/auth/login')) aoNaoAutorizado();
  let dados = null;
  try { dados = await resp.json(); } catch { /* resposta sem corpo */ }
  if (!resp.ok) {
    const detalhe = dados && dados.detail;
    throw new ErroApi(typeof detalhe === 'string' ? detalhe : 'Erro ' + resp.status, resp.status);
  }
  return dados;
}

export const api = {
  get: (url) => requisitar('GET', url),
  post: (url, corpo = {}) => requisitar('POST', url, corpo),
  put: (url, corpo = {}) => requisitar('PUT', url, corpo),
  del: (url) => requisitar('DELETE', url),
};

// Baixa um arquivo (ex.: CSV) mantendo o cabeçalho de autenticação.
export async function baixarArquivo(url, nomeArquivo) {
  const resp = await fetch(url, { headers: { Authorization: 'Bearer ' + lerToken() } });
  if (!resp.ok) throw new ErroApi('Não foi possível gerar o arquivo.', resp.status);
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = nomeArquivo;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
