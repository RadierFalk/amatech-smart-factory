/** Contratos de /api/mnt (espelham backend/app/modulos/manutencao/esquemas.py) e rótulos de tela. */
import { Tom } from '../../shared/etiqueta';

export type StatusEquipamento = 'OPERACIONAL' | 'EM_MANUTENCAO' | 'PARADA';
export type StatusChamado = 'ABERTO' | 'EM_ANDAMENTO' | 'CONCLUIDO' | 'CANCELADO';
export type Prioridade = 'BAIXA' | 'MEDIA' | 'ALTA' | 'CRITICA';
export type TipoManutencao = 'CORRETIVA' | 'PREVENTIVA';

export interface PermissoesMnt {
  abrir_chamado: boolean;
  atender: boolean;
  concluir_qualquer: boolean;
  cancelar: boolean;
  cadastros: boolean;
  indicadores: boolean;
}

export interface OpcoesMnt {
  prioridades: Prioridade[];
  tipos_manutencao: TipoManutencao[];
  status_chamado: StatusChamado[];
  status_equipamento: Record<StatusEquipamento, string>;
  setores: string[];
  causas_raiz: string[];
  permissoes: PermissoesMnt;
}

export interface OsAtivaResumo {
  id: number;
  status_chamado: StatusChamado;
  prioridade: Prioridade;
  tipo_manutencao: TipoManutencao;
  descricao_falha: string;
  tecnico_nome: string | null;
  data_hora_abertura: string;
  minutos_desde_abertura: number;
}

export interface Equipamento {
  id: number;
  codigo_tag: string;
  nome: string;
  setor: string;
  posto_trabalho: string | null;
  status_operacional: StatusEquipamento;
  ativo: boolean;
  os_ativa: OsAtivaResumo | null;
}

export interface Peca {
  id: number;
  codigo_peca: string;
  nome: string;
  unidade_medida: string;
  ativo: boolean;
}

export interface PecaTrocada {
  id: number;
  peca_id: number;
  codigo_peca: string;
  nome: string;
  unidade_medida: string;
  quantidade: number;
}

export interface Chamado {
  id: number;
  equipamento_id: number;
  equipamento_tag: string;
  equipamento_nome: string;
  setor: string;
  posto_trabalho: string | null;
  status_equipamento: StatusEquipamento;
  prioridade: Prioridade;
  tipo_manutencao: TipoManutencao;
  status_chamado: StatusChamado;
  descricao_falha: string;
  diagnostico_tecnico: string | null;
  causa_raiz: string | null;
  motivo_cancelamento: string | null;
  operador_id: number;
  operador_nome: string;
  tecnico_id: number | null;
  tecnico_nome: string | null;
  data_hora_abertura: string;
  data_hora_inicio_atendimento: string | null;
  data_hora_fim_atendimento: string | null;
  downtime_minutos: number | null;
  minutos_desde_abertura: number | null;
  minutos_em_atendimento: number | null;
  origem_sistema: string | null;
  id_externo: string | null;
  pecas: PecaTrocada[];
}

export interface Auditoria {
  id: number;
  equipamento_id: number;
  equipamento_tag: string;
  chamado_id: number | null;
  usuario_nome: string;
  usuario_perfil: string;
  status_anterior: StatusEquipamento;
  status_novo: StatusEquipamento;
  alterado_em: string;
}

export interface Indicadores {
  downtime_total_minutos: number;
  downtime_concluido_minutos: number;
  downtime_ativo_minutos: number;
  mttr_minutos: number;
  mtta_minutos: number;
  mtbf_minutos: number;
  disponibilidade_pct: number;
  total_chamados: number;
  chamados_abertos: number;
  chamados_em_andamento: number;
  chamados_concluidos: number;
  chamados_cancelados: number;
  preventivas: number;
  corretivas: number;
  total_maquinas: number;
  maquinas_operacionais: number;
  maquinas_em_manutencao: number;
  maquinas_paradas: number;
}

export interface LinhaGrafico {
  chamados: number;
  downtime_minutos: number;
}

export interface Graficos {
  downtime_por_maquina: (LinhaGrafico & { codigo_tag: string; nome: string; setor: string })[];
  downtime_por_setor: (LinhaGrafico & { setor: string })[];
  chamados_por_causa_raiz: (LinhaGrafico & { causa_raiz: string })[];
  evolucao_diaria: (LinhaGrafico & { data: string })[];
  pecas_consumidas: { codigo_peca: string; nome: string; unidade_medida: string; quantidade: number }[];
}

/** A fábrica fica em Manaus: todas as datas da tela usam UTC-4. */
export const FUSO_FABRICA = '-0400';

export const ROTULO_STATUS_EQUIPAMENTO: Record<StatusEquipamento, string> = {
  OPERACIONAL: 'Funcionando',
  EM_MANUTENCAO: 'Em manutenção',
  PARADA: 'Parada',
};

export const TOM_STATUS_EQUIPAMENTO: Record<StatusEquipamento, Tom> = {
  OPERACIONAL: 'ok',
  EM_MANUTENCAO: 'atencao',
  PARADA: 'critico',
};

export const ROTULO_STATUS_CHAMADO: Record<StatusChamado, string> = {
  ABERTO: 'Aberto',
  EM_ANDAMENTO: 'Em andamento',
  CONCLUIDO: 'Concluído',
  CANCELADO: 'Cancelado',
};

export const TOM_STATUS_CHAMADO: Record<StatusChamado, Tom> = {
  ABERTO: 'critico',
  EM_ANDAMENTO: 'atencao',
  CONCLUIDO: 'ok',
  CANCELADO: 'neutro',
};

export const ROTULO_PRIORIDADE: Record<Prioridade, string> = {
  BAIXA: 'Baixa',
  MEDIA: 'Média',
  ALTA: 'Alta',
  CRITICA: 'Crítica',
};

export const TOM_PRIORIDADE: Record<Prioridade, Tom> = {
  BAIXA: 'neutro',
  MEDIA: 'info',
  ALTA: 'atencao',
  CRITICA: 'critico',
};

export const ROTULO_TIPO: Record<TipoManutencao, string> = {
  CORRETIVA: 'Corretiva',
  PREVENTIVA: 'Preventiva',
};

/** "95 min" → "1 h 35 min". */
export function duracao(minutos: number | null | undefined): string {
  if (minutos === null || minutos === undefined) return '—';
  if (minutos < 60) return `${minutos} min`;
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
