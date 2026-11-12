/** Contratos de /api/ras (espelham backend/app/modulos/rastreabilidade/esquemas.py) e rótulos de tela. */
import { Tom } from '../../shared/etiqueta';

export type StatusSolicitacao = 'PENDENTE' | 'PARCIAL' | 'ATENDIDA' | 'CANCELADA';

export interface PermissoesRas {
  producao: boolean;
  excluir_producao: boolean;
  solicitar: boolean;
  baixar: boolean;
  componentes: boolean;
  modelos_etapas: boolean;
}

export interface Etapa {
  id: number;
  nome: string;
  ordem: number;
}

export interface Responsavel {
  id: number;
  nome: string;
  matricula: string;
}

export interface OpcoesRas {
  etapas: Etapa[];
  responsaveis: Responsavel[];
  status_solicitacao: StatusSolicitacao[];
  limite_estoque_critico: number;
  permissoes: PermissoesRas;
}

export interface Componente {
  id: number;
  sku: string;
  nome: string;
  estoque: number;
  ativo: boolean;
  estoque_critico: boolean;
  pendente: number;
}

export interface ItemLista {
  componente_id: number;
  sku: string;
  nome: string;
  estoque: number;
  quantidade: number;
}

export interface Modelo {
  id: number;
  codigo: string;
  nome: string;
  meta: number | null;
  ativo: boolean;
  producoes: number;
  componentes: ItemLista[];
}

export interface Producao {
  id: number;
  numero_serie: string;
  id_unica: string;
  modelo_id: number;
  modelo_nome: string;
  modelo_codigo: string;
  etapa_id: number;
  etapa_nome: string;
  etapa_ordem: number;
  responsavel_id: number;
  responsavel_nome: string;
  criado_por_nome: string;
  iniciada_em: string;
  atualizada_em: string;
}

export interface Passagem {
  id: number;
  etapa_nome: string;
  usuario_nome: string;
  responsavel_nome: string | null;
  registrada_em: string;
  origem: string;
}

export interface NaoConformidade {
  id: number;
  descricao_falha: string;
  motivo_reprovacao: string;
  usuario_nome: string;
  registrada_em: string;
  origem_sistema: string | null;
  id_externo: string | null;
}

export interface Solicitacao {
  id: number;
  producao_id: number;
  numero_serie: string;
  componente_id: number;
  componente_nome: string;
  sku: string;
  estoque: number;
  quantidade: number;
  quantidade_baixada: number;
  status: StatusSolicitacao;
  solicitante_nome: string;
  criada_em: string;
}

export interface Baixa {
  id: number;
  solicitacao_id: number;
  numero_serie: string;
  componente_nome: string;
  sku: string;
  quantidade: number;
  usuario_nome: string;
  registrada_em: string;
}

export interface ProducaoDetalhe extends Producao {
  passagens: Passagem[];
  nao_conformidades: NaoConformidade[];
  solicitacoes: Solicitacao[];
  materiais_pendentes: number;
  mesmo_modelo: Producao[];
  proxima_etapa_id: number | null;
}

export interface PainelRas {
  kpis: {
    iniciadas_hoje: number;
    em_producao: number;
    aprovados: number;
    reprovados: number;
    solicitacoes_pendentes: number;
    estoque_critico: number;
  };
  por_etapa: { etapa: string; ordem: number; quantidade: number }[];
  ultimos_dias: { data: string; quantidade: number }[];
  estoque_critico: { id: number; sku: string; nome: string; estoque: number }[];
  limite_estoque_critico: number;
}

export interface ColunaRelatorio {
  chave: string;
  titulo: string;
  formato: 'texto' | 'numero' | 'data';
}

export interface Relatorio {
  tipo: string;
  titulo: string;
  colunas: ColunaRelatorio[];
  linhas: Record<string, string | number | null>[];
}

export const ROTULO_SOLICITACAO: Record<StatusSolicitacao, string> = {
  PENDENTE: 'Pendente',
  PARCIAL: 'Parcial',
  ATENDIDA: 'Atendida',
  CANCELADA: 'Cancelada',
};
export const TOM_SOLICITACAO: Record<StatusSolicitacao, Tom> = {
  PENDENTE: 'atencao',
  PARCIAL: 'atencao',
  ATENDIDA: 'ok',
  CANCELADA: 'neutro',
};

/** Origem da passagem de etapa, em palavras. */
export function rotuloOrigem(origem: string): string {
  return { MANUAL: 'Manual', 'MAQUINA/IOT': 'Máquina', QUALIDADE: 'Qualidade' }[origem] ?? origem;
}
