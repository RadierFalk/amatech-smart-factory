/** Contratos de /api/dsh (espelham backend/app/modulos/dashboard/esquemas.py e calculo.py) e rótulos de tela. */
import { Tom } from '../../shared/etiqueta';

export type Semaforo = 'verde' | 'amarelo' | 'vermelho';
export type IndicadorSemaforo = 'atendimento_meta' | 'indice_defeitos' | 'indice_retrabalho';

export interface Turno {
  id: number;
  nome: string;
  hora_inicio: string;
  hora_fim: string;
  duracao_min: number;
}

export interface TipoPerda {
  id: number;
  nome: string;
  ativo: boolean;
}

export interface Limite {
  indicador: IndicadorSemaforo;
  nome: string;
  limite_verde: number;
  limite_amarelo: number;
  sentido: 'maior_melhor' | 'menor_melhor';
}

export interface OpcoesDsh {
  turnos: Turno[];
  modelos: { id: number; nome: string; codigo: string }[];
  estacoes: { id: number; nome: string }[];
  tipos_perda: TipoPerda[];
  limites: Limite[];
  hoje: string;
  permissoes: { lancar: boolean; configurar: boolean };
}

export interface ValorSemaforo {
  valor: number | null;
  semaforo: Semaforo | null;
}

export interface Contagem {
  rotulo: string;
  quantidade: number;
}

export interface ParadaAgora {
  chamado_id: number;
  maquina: string;
  nome: string;
  setor: string;
  status_chamado: string;
  motivo: string;
  desde: string;
  minutos: number;
}

export interface Painel {
  periodo: { de: string; ate: string };
  producao: { realizada: number; aprovada: number; reprovada: number; meta: number };
  atendimento_meta: ValorSemaforo;
  indice_defeitos: ValorSemaforo;
  indice_retrabalho: ValorSemaforo & { retrabalho: number };
  produtividade: { valor: number | null; minutos_turno: number; minutos_produtivos: number };
  tempo_parada: { minutos: number; paradas: number; em_andamento: number };
  perdas: { total: number; por_tipo: Contagem[] };
  graficos: {
    producao_x_meta: { modelo: string; realizada: number; meta: number }[];
    producao_por_dia: { data: string; realizada: number; meta: number }[];
    defeitos_por_estacao: Contagem[];
    retrabalho_por_estacao: Contagem[];
    parada_por_turno: { rotulo: string; minutos: number }[];
  };
  paradas_em_andamento: ParadaAgora[];
  lead_time: { minutos: number | null; expedidos: number; por_modelo: { modelo: string; minutos: number; expedidos: number }[] };
  em_producao: { total: number; por_etapa: (Contagem & { lateral: boolean })[] };
  producao_por_turno: LinhaHistorico[];
  qualidade: Qualidade;
  manutencao: Manutencao;
  materiais: Materiais;
}

export interface Qualidade {
  ocorrencias: number;
  abertas: number;
  em_analise: number;
  resolvidas: number;
  criticas: number;
  criticas_pendentes: number;
  por_tipo: Contagem[];
  por_dia: { data: string; quantidade: number }[];
  criticas_recentes: {
    id: number; ocorrida_em: string; defeito: string; numero_serie: string; modelo: string; estacao: string;
    status: 'ABERTA' | 'EM_ANALISE' | 'RESOLVIDA';
  }[];
}

export interface Manutencao {
  disponibilidade: number | null;
  mttr_minutos: number | null;
  mtta_minutos: number | null;
  mtbf_minutos: number | null;
  chamados: number;
  chamados_ativos: number;
  por_setor: { setor: string; minutos: number; paradas: number }[];
  por_maquina: { maquina: string; nome: string; setor: string; minutos: number; paradas: number; parada_agora: boolean }[];
  por_dia: { data: string; minutos: number }[];
  por_causa: Contagem[];
}

export interface Materiais {
  pendentes: number;
  parciais: number;
  producoes_com_pendencia: number;
  baixas: number;
  unidades_baixadas: number;
  limite_critico: number;
  estoque_critico: { sku: string; nome: string; estoque: number; pedido: number; insuficiente: boolean }[];
  pendencias_por_componente: { sku: string; nome: string; producoes: number; quantidade: number; insuficiente: boolean }[];
}

export const ROTULO_STATUS_OCORRENCIA = { ABERTA: 'Aberta', EM_ANALISE: 'Em análise', RESOLVIDA: 'Resolvida' } as const;
export const TOM_STATUS_OCORRENCIA: Record<keyof typeof ROTULO_STATUS_OCORRENCIA, Tom> = {
  ABERTA: 'critico', EM_ANALISE: 'atencao', RESOLVIDA: 'ok',
};

export interface FiltroPainel {
  de: string;
  ate: string;
  turno_id?: number | null;
  modelo_id?: number | null;
}

export interface Meta {
  id: number;
  data: string;
  turno_id: number;
  turno_nome: string;
  modelo_id: number;
  modelo_nome: string;
  quantidade: number;
  registrado_por_nome: string;
}

export interface Perda {
  id: number;
  data: string;
  turno_nome: string;
  estacao_nome: string;
  modelo_nome: string;
  tipo_nome: string;
  quantidade: number;
  observacao: string | null;
  origem: 'manual' | 'csv';
  registrado_por_nome: string;
  registrado_em: string;
}

export interface LinhaHistorico {
  data: string;
  turno_id: number;
  turno: string;
  modelo: string;
  realizada: number;
  aprovada: number;
  reprovada: number;
  meta: number;
  atendimento_meta: number | null;
}

export interface ResultadoImportacao {
  linhas_lidas: number;
  importadas: number;
  erros: { linha: number; coluna: string; mensagem: string }[];
}

/** O semáforo nunca é só cor: a etiqueta sempre leva o texto. */
export const ROTULO_SEMAFORO: Record<Semaforo, string> = { verde: 'No alvo', amarelo: 'Atenção', vermelho: 'Fora do alvo' };
export const TOM_SEMAFORO: Record<Semaforo, Tom> = { verde: 'ok', amarelo: 'atencao', vermelho: 'critico' };

/** Número no formato brasileiro (1.420; 94,7). */
export function numero(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined) return '—';
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function percentual(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? '—' : `${numero(valor, 1)}%`;
}

/** Data AAAA-MM-DD deslocada em dias, sem passar por fuso (as datas da API já são do dia da fábrica). */
export function somarDias(data: string, dias: number): string {
  const d = new Date(`${data}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

/** Semáforo do atendimento da meta pelos limites cadastrados (sem limite: o padrão 95% / 75%). */
export function semaforoMeta(valor: number | null, limites: Limite[] = []): Semaforo | null {
  if (valor === null) return null;
  const l = limites.find((x) => x.indicador === 'atendimento_meta');
  const verde = l?.limite_verde ?? 95;
  const amarelo = l?.limite_amarelo ?? 75;
  return valor >= verde ? 'verde' : valor >= amarelo ? 'amarelo' : 'vermelho';
}

/** "2026-08-15" -> "sáb". */
export function diaSemana(data: string): string {
  return ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'][new Date(`${data}T12:00:00Z`).getUTCDay()];
}

/** "2026-08-15" -> "15/08". */
export function diaMes(data: string): string {
  return `${data.slice(8, 10)}/${data.slice(5, 7)}`;
}
