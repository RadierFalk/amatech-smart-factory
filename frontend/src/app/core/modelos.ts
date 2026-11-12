/** Contratos da API (espelham backend/app/modulos/usuarios/esquemas.py e backend/app/core/rbac.py). */

export const PERFIS = [
  'Administrador',
  'Supervisor / Gestor',
  'Inspetor de Qualidade',
  'Operador de Produção',
  'Técnico de Manutenção',
  'Almoxarife',
] as const;

export type Perfil = (typeof PERFIS)[number];

export type IdModulo = 'rastreabilidade' | 'qualidade' | 'manutencao' | 'dashboard' | 'usuarios';

export interface Usuario {
  id: number;
  matricula: string;
  nome: string;
  perfil: Perfil;
  ativo: boolean;
  criado_em: string;
}

export interface ModuloERP {
  id: IdModulo;
  sigla: string;
  nome: string;
  descricao: string;
}

export interface RespostaLogin {
  access_token: string;
  token_type: 'bearer';
  usuario: Usuario;
}
