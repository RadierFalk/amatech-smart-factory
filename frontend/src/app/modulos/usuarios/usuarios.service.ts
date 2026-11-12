import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Perfil, Usuario } from '../../core/modelos';

export interface NovoUsuario {
  nome: string;
  perfil: Perfil;
  senha: string;
  matricula?: string | null;
}

export interface AlteracaoUsuario {
  nome?: string;
  perfil?: Perfil;
  ativo?: boolean;
}

/** Chamadas a /api/usuarios (só Administrador; a API responde 403 aos demais). */
@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/usuarios';

  listar(): Observable<Usuario[]> {
    return this.http.get<Usuario[]>(this.base);
  }

  criar(dados: NovoUsuario): Observable<Usuario> {
    return this.http.post<Usuario>(this.base, dados);
  }

  alterar(id: number, dados: AlteracaoUsuario): Observable<Usuario> {
    return this.http.patch<Usuario>(`${this.base}/${id}`, dados);
  }

  redefinirSenha(id: number, novaSenha: string): Observable<void> {
    return this.http.post<void>(`${this.base}/${id}/senha`, { nova_senha: novaSenha });
  }
}
