/** Contratos de /api/qld (espelham backend/app/modulos/qualidade/esquemas.py) e rótulos de tela. */
import { Tom } from '../../shared/etiqueta';
import { StatusChamado, StatusEquipamento } from '../manutencao/mnt.modelos';

export type Classificacao = 'CRITICO' | 'MAIOR' | 'MENOR';
export type SituacaoProduto = 'APROVADO' | 'REPROVADO' | 'EM_REPROCESSO';
export type StatusOcorrencia = 'ABERTA' | 'EM_ANALISE' | 'RESOLVIDA';

export interface PermissoesQld {
  registrar: boolean;
  editar: boolean;
  ocultar: boolean;
  abrir_chamado: boolean;
  cadastros: boolean;
}

export interface OpcoesQld {
  classificacoes: Record<Classificacao, string>;
  situacoes: Record<SituacaoProduto, string>;
  status: Record<StatusOcorrencia, string>;
  permissoes: PermissoesQld;
}

export interface Produto {
  id: number;
  numero_serie: string;
  modelo: string;
  ativo: boolean;
}

/** Estação ou tipo de defeito. */
export interface ItemCadastro {
  id: number;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

export interface Maquina {
  id: number;
  codigo_tag: string;
  nome: string;
  setor: string;
  status_operacional: StatusEquipamento;
}

export interface Ocorrencia {
  id: number;
  ocorrida_em: string;
  classificacao: Classificacao;
  situacao_produto: SituacaoProduto;
  status: StatusOcorrencia;
  observacao: string;
  acao_realizada: string;
  produto_id: number;
  numero_serie: string;
  modelo: string;
  estacao_id: number;
  estacao_nome: string;
  tipo_defeito_id: number;
  tipo_defeito_nome: string;
  equipamento_id: number;
  equipamento_tag: string;
  equipamento_nome: string;
  responsavel_id: number;
  responsavel_nome: string;
  chamado_id: number | null;
  chamado_status: StatusChamado | null;
}

/** Corpo do registro/edição. `ocorrida_em` sem fuso = hora da fábrica (Manaus). */
export interface OcorrenciaEntrada {
  ocorrida_em: string;
  classificacao: Classificacao;
  situacao_produto: SituacaoProduto;
  status: StatusOcorrencia;
  observacao: string;
  acao_realizada: string;
  produto_id: number;
  estacao_id: number;
  tipo_defeito_id: number;
  equipamento_id: number;
}

export interface AvisoIntegracao {
  tipo: 'sucesso' | 'aviso';
  mensagem: string;
}

export interface RegistroSaida {
  ocorrencia: Ocorrencia;
  avisos: AvisoIntegracao[];
}

export interface Contagem {
  rotulo: string;
  ocorrencias: number;
}

export interface IndicadoresQld {
  total_ocorrencias: number;
  ocorrencias_abertas: number;
  ocorrencias_em_analise: number;
  produtos_reprovados: number;
  criticas: number;
  estacao_critica: string | null;
  por_tipo_defeito: Contagem[];
  por_estacao: Contagem[];
  por_maquina: Contagem[];
  por_classificacao: Contagem[];
  por_dia: { data: string; ocorrencias: number }[];
}

export const ROTULO_CLASSIFICACAO: Record<Classificacao, string> = { CRITICO: 'Crítico', MAIOR: 'Maior', MENOR: 'Menor' };
export const TOM_CLASSIFICACAO: Record<Classificacao, Tom> = { CRITICO: 'critico', MAIOR: 'atencao', MENOR: 'neutro' };

export const ROTULO_SITUACAO: Record<SituacaoProduto, string> = {
  APROVADO: 'Aprovado',
  REPROVADO: 'Reprovado',
  EM_REPROCESSO: 'Em reprocesso',
};
export const TOM_SITUACAO: Record<SituacaoProduto, Tom> = { APROVADO: 'ok', REPROVADO: 'critico', EM_REPROCESSO: 'atencao' };

export const ROTULO_STATUS: Record<StatusOcorrencia, string> = { ABERTA: 'Aberta', EM_ANALISE: 'Em análise', RESOLVIDA: 'Resolvida' };
export const TOM_STATUS: Record<StatusOcorrencia, Tom> = { ABERTA: 'critico', EM_ANALISE: 'atencao', RESOLVIDA: 'ok' };

export const CLASSIFICACOES: Classificacao[] = ['CRITICO', 'MAIOR', 'MENOR'];
export const SITUACOES: SituacaoProduto[] = ['REPROVADO', 'EM_REPROCESSO', 'APROVADO'];
export const STATUS: StatusOcorrencia[] = ['ABERTA', 'EM_ANALISE', 'RESOLVIDA'];
