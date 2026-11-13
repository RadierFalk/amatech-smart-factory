import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

/** Linha de /api/alertas (espelha backend/app/modulos/alertas/rotas.py). */
export interface Alerta {
  id: number;
  tipo: 'CHAMADO_ABERTO' | 'PARADA_SEM_TECNICO' | 'ESTOQUE_INSUFICIENTE' | 'OCORRENCIA_CRITICA';
  modulo: string;
  titulo: string;
  detalhe: string;
  link: string;
  ativo: boolean;
  lido: boolean;
  criado_em: string;
  resolvido_em: string | null;
}

/** De quanto em quanto tempo o sino consulta a API. */
export const INTERVALO_ALERTAS_MS = 30_000;

/**
 * Alertas da pessoa logada, consultados a cada 30 s enquanto a casca (Shell) está aberta. Um serviço só: os dois
 * sinos (barra lateral e barra do celular) mostram o mesmo estado e não duplicam a consulta.
 */
@Injectable({ providedIn: 'root' })
export class AlertasService {
  private readonly http = inject(HttpClient);
  private temporizador: ReturnType<typeof setInterval> | undefined;

  readonly alertas = signal<Alerta[]>([]);
  readonly naoLidos = signal(0);

  iniciar(): void {
    if (this.temporizador) return;
    void this.atualizar();
    this.temporizador = setInterval(() => void this.atualizar(), INTERVALO_ALERTAS_MS);
  }

  parar(): void {
    clearInterval(this.temporizador);
    this.temporizador = undefined;
  }

  async atualizar(): Promise<void> {
    try {
      const r = await firstValueFrom(this.http.get<{ nao_lidos: number; alertas: Alerta[] }>('/api/alertas'));
      this.alertas.set(r.alertas);
      this.naoLidos.set(r.nao_lidos);
    } catch {
      // Sem rede ou sessão expirada: o interceptor trata o 401; o sino só espera a próxima rodada.
    }
  }

  /** Marca como lidos (todos os visíveis, sem `ids`) e já reflete no sino. */
  async marcarLidos(ids?: number[]): Promise<void> {
    await firstValueFrom(this.http.post<void>('/api/alertas/lidos', ids ? { ids } : {}));
    const alvo = ids ? new Set(ids) : null;
    this.alertas.update((lista) => lista.map((a) => (!alvo || alvo.has(a.id) ? { ...a, lido: true } : a)));
    this.naoLidos.set(this.alertas().filter((a) => a.ativo && !a.lido).length);
  }
}
