import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { mensagemDeErro } from '../../core/erros';
import { PERFIS, Perfil, Usuario } from '../../core/modelos';
import { Etiqueta } from '../../shared/etiqueta';
import { UsuariosService } from './usuarios.service';

export const SENHA_MINIMA = 8; // igual a backend/app/modulos/usuarios/esquemas.py

/** Módulo USR: cadastro de colaboradores, troca de persona, ativação/bloqueio e senha. */
@Component({
  selector: 'am-usuarios',
  imports: [ReactiveFormsModule, DatePipe, Etiqueta],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.scss',
})
export class Usuarios implements OnInit {
  private readonly servico = inject(UsuariosService);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly auth = inject(AuthService);

  protected readonly perfis = PERFIS;
  protected readonly senhaMinima = SENHA_MINIMA;

  protected readonly usuarios = signal<Usuario[]>([]);
  protected readonly carregando = signal(true);
  protected readonly ocupado = signal<number | 'novo' | null>(null);
  protected readonly erro = signal<string | null>(null);
  protected readonly sucesso = signal<string | null>(null);
  protected readonly busca = signal('');
  protected readonly formularioAberto = signal(false);
  protected readonly senhaDe = signal<Usuario | null>(null);

  protected readonly filtrados = computed(() => {
    const termo = this.busca().trim().toLowerCase();
    if (!termo) return this.usuarios();
    return this.usuarios().filter((u) =>
      [u.matricula, u.nome, u.perfil].some((v) => v.toLowerCase().includes(termo)),
    );
  });

  protected readonly formNovo = this.fb.group({
    nome: ['', [Validators.required, Validators.maxLength(100)]],
    perfil: this.fb.control<Perfil>('Operador de Produção', Validators.required),
    senha: ['', [Validators.required, Validators.minLength(SENHA_MINIMA)]],
    matricula: ['', Validators.maxLength(20)],
  });

  protected readonly formSenha = this.fb.group({
    novaSenha: ['', [Validators.required, Validators.minLength(SENHA_MINIMA)]],
  });

  ngOnInit(): void {
    void this.carregar();
  }

  protected ehEuMesmo(u: Usuario): boolean {
    return u.id === this.auth.usuario()?.id;
  }

  protected async carregar(): Promise<void> {
    this.carregando.set(true);
    try {
      this.usuarios.set(await firstValueFrom(this.servico.listar()));
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.carregando.set(false);
    }
  }

  protected async criar(): Promise<void> {
    if (this.formNovo.invalid) {
      this.formNovo.markAllAsTouched();
      return;
    }
    const { nome, perfil, senha, matricula } = this.formNovo.getRawValue();
    await this.executar('novo', async () => {
      const novo = await firstValueFrom(
        this.servico.criar({ nome, perfil, senha, matricula: matricula.trim() || null }),
      );
      this.usuarios.update((lista) => [...lista, novo].sort((a, b) => a.matricula.localeCompare(b.matricula)));
      this.formNovo.reset();
      this.formularioAberto.set(false);
      return `Usuário ${novo.matricula} (${novo.nome}) criado.`;
    });
  }

  protected async trocarPerfil(u: Usuario, seletor: HTMLSelectElement): Promise<void> {
    const perfil = seletor.value as Perfil;
    const ok = await this.executar(u.id, async () => {
      this.substituir(await firstValueFrom(this.servico.alterar(u.id, { perfil })));
      return `Perfil de ${u.matricula} alterado para ${perfil}.`;
    });
    if (!ok) {
      seletor.value = u.perfil; // a API recusou: o seletor volta a mostrar a persona real
    }
  }

  protected async alternarAtivo(u: Usuario): Promise<void> {
    await this.executar(u.id, async () => {
      const atualizado = await firstValueFrom(this.servico.alterar(u.id, { ativo: !u.ativo }));
      this.substituir(atualizado);
      return `Conta ${u.matricula} ${atualizado.ativo ? 'ativada' : 'desativada'}.`;
    });
  }

  protected abrirSenha(u: Usuario): void {
    this.formSenha.reset();
    this.senhaDe.set(u);
  }

  protected async salvarSenha(): Promise<void> {
    const u = this.senhaDe();
    if (!u || this.formSenha.invalid) {
      this.formSenha.markAllAsTouched();
      return;
    }
    await this.executar(u.id, async () => {
      await firstValueFrom(this.servico.redefinirSenha(u.id, this.formSenha.getRawValue().novaSenha));
      this.senhaDe.set(null);
      return `Senha de ${u.matricula} redefinida.`;
    });
  }

  protected invalido(form: 'novo' | 'senha', campo: string): boolean {
    const c = form === 'novo' ? this.formNovo.get(campo) : this.formSenha.get(campo);
    return !!c && c.touched && c.invalid;
  }

  private substituir(atualizado: Usuario): void {
    this.usuarios.update((lista) => lista.map((u) => (u.id === atualizado.id ? atualizado : u)));
  }

  private async executar(alvo: number | 'novo', acao: () => Promise<string>): Promise<boolean> {
    this.ocupado.set(alvo);
    this.erro.set(null);
    this.sucesso.set(null);
    try {
      this.sucesso.set(await acao());
      return true;
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
      return false;
    } finally {
      this.ocupado.set(null);
    }
  }
}
