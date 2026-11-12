import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { IdModulo, ModuloERP, RespostaLogin, Usuario } from '../modelos';

const CHAVE_TOKEN = 'amatech.token';
const CHAVE_USUARIO = 'amatech.usuario';

/**
 * Sessão do usuário. O token fica no sessionStorage: some ao fechar a aba,
 * o que combina com terminais compartilhados no chão de fábrica.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly _token = signal<string | null>(ler(CHAVE_TOKEN));
  private readonly _usuario = signal<Usuario | null>(lerJson<Usuario>(CHAVE_USUARIO));
  private readonly _modulos = signal<ModuloERP[] | null>(null);

  readonly token = this._token.asReadonly();
  readonly usuario = this._usuario.asReadonly();
  readonly modulos = this._modulos.asReadonly();
  readonly autenticado = computed(() => this._token() !== null && this._usuario() !== null);

  async entrar(matricula: string, senha: string): Promise<void> {
    const resposta = await firstValueFrom(
      this.http.post<RespostaLogin>('/api/auth/login', { matricula, senha }),
    );
    gravar(CHAVE_TOKEN, resposta.access_token);
    gravar(CHAVE_USUARIO, JSON.stringify(resposta.usuario));
    this._token.set(resposta.access_token);
    this._usuario.set(resposta.usuario);
    this._modulos.set(null);
  }

  /** Módulos da persona, vindos do servidor (a fonte da verdade do RBAC). Fica em cache na sessão. */
  async carregarModulos(): Promise<ModuloERP[]> {
    const emCache = this._modulos();
    if (emCache) {
      return emCache;
    }
    const modulos = await firstValueFrom(this.http.get<ModuloERP[]>('/api/auth/modulos'));
    this._modulos.set(modulos);
    return modulos;
  }

  async temModulo(id: IdModulo): Promise<boolean> {
    return (await this.carregarModulos()).some((m) => m.id === id);
  }

  sair(): void {
    remover(CHAVE_TOKEN);
    remover(CHAVE_USUARIO);
    this._token.set(null);
    this._usuario.set(null);
    this._modulos.set(null);
    void this.router.navigateByUrl('/login');
  }
}

// O storage pode estar bloqueado (modo privado, política do navegador): a sessão só não persiste.
function ler(chave: string): string | null {
  try {
    return sessionStorage.getItem(chave);
  } catch {
    return null;
  }
}

function lerJson<T>(chave: string): T | null {
  const texto = ler(chave);
  if (!texto) {
    return null;
  }
  try {
    return JSON.parse(texto) as T;
  } catch {
    return null;
  }
}

function gravar(chave: string, valor: string): void {
  try {
    sessionStorage.setItem(chave, valor);
  } catch {
    /* sem persistência */
  }
}

function remover(chave: string): void {
  try {
    sessionStorage.removeItem(chave);
  } catch {
    /* nada a remover */
  }
}
