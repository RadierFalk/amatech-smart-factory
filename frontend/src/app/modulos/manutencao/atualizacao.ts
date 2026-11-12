import { DestroyRef, inject } from '@angular/core';

/**
 * Executa `carregar` agora e a cada `segundos` enquanto a tela estiver aberta
 * (painel e fila acompanham o chão de fábrica sem o usuário apertar F5).
 * Pausa quando a aba do navegador está escondida.
 */
export function atualizarPeriodicamente(carregar: () => void, segundos = 30): void {
  carregar();
  const id = setInterval(() => {
    if (document.visibilityState === 'visible') carregar();
  }, segundos * 1000);
  inject(DestroyRef).onDestroy(() => clearInterval(id));
}
