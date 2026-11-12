import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { mensagemDeErro } from '../../core/erros';
import { Marca } from '../../shared/marca';

/** Contas de demonstração (README). Desligue em produção trocando para `false`. */
export const MOSTRAR_PERSONAS_DEMO = true;
const SENHA_DEMO = 'amatech1234';

const PERSONAS_DEMO = [
  { matricula: 'ADM-0001', rotulo: 'Administrador' },
  { matricula: 'GES-0001', rotulo: 'Supervisor' },
  { matricula: 'OPE-0001', rotulo: 'Operador' },
  { matricula: 'QUA-0001', rotulo: 'Inspetor QLD' },
  { matricula: 'TEC-2001', rotulo: 'Técnico MNT' },
  { matricula: 'ALM-0001', rotulo: 'Almoxarife' },
];

@Component({
  selector: 'am-login',
  imports: [ReactiveFormsModule, Marca],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly form = inject(NonNullableFormBuilder).group({
    matricula: ['', Validators.required],
    senha: ['', Validators.required],
  });
  protected readonly enviando = signal(false);
  protected readonly erro = signal<string | null>(null);
  protected readonly personas = MOSTRAR_PERSONAS_DEMO ? PERSONAS_DEMO : [];

  protected async entrar(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.erro.set('Informe a matrícula e a senha.');
      return;
    }
    const { matricula, senha } = this.form.getRawValue();
    await this.autenticar(matricula, senha);
  }

  protected async entrarComo(matricula: string): Promise<void> {
    this.form.setValue({ matricula, senha: SENHA_DEMO });
    await this.autenticar(matricula, SENHA_DEMO);
  }

  private async autenticar(matricula: string, senha: string): Promise<void> {
    this.enviando.set(true);
    this.erro.set(null);
    try {
      await this.auth.entrar(matricula.trim(), senha);
      await this.router.navigateByUrl('/');
    } catch (e) {
      this.erro.set(mensagemDeErro(e));
    } finally {
      this.enviando.set(false);
    }
  }
}
