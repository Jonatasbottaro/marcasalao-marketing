/**
 * Contrato BeatPlan v1 — uma fatia do nucleo modular da Content Factory.
 *
 * BeatPlan e a traducao temporal de uma Composition valida: uma sequencia
 * ordenada de beats, cada um com inicio, duracao, funcao narrativa, texto e
 * intencoes visuais. Nao e roteiro, nao e Composition e nao e renderizacao.
 *
 * O plano NAO gera beats automaticamente, NAO contem comandos de ferramenta,
 * NAO contem provider de midia e NAO cria arquivos. Narration e somente texto
 * (nao ha TTS nem arquivo de audio); motionIntent e transicoes descrevem
 * intencao e nao executam movimento nem animacao.
 *
 * O nucleo NAO conhece nenhum projeto especifico: o plano e sempre validado
 * contra um ProjectManifest e uma Composition informados explicitamente.
 *
 * Ver docs/decisoes/MKT-VIDEO-001-producao-modular.md,
 * docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md e
 * docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const BEAT_PLAN_SCHEMA_VERSION = 1

/** Funcoes narrativas neutras; nenhuma e especifica de um projeto consumidor. */
export const BEAT_NARRATIVE_FUNCTIONS = [
    'hook',
    'context',
    'problem',
    'demonstration',
    'explanation',
    'proof',
    'transition',
    'cta',
    'closing',
] as const

export type BeatNarrativeFunction = (typeof BEAT_NARRATIVE_FUNCTIONS)[number]

/** Intencoes de movimento neutras: descrevem, nao executam. */
export const BEAT_MOTION_INTENTS = [
    'none',
    'slow-zoom',
    'parallax-depth',
    'camera-orbit',
    'pan',
    'tilt',
    'hold',
] as const

export type BeatMotionIntent = (typeof BEAT_MOTION_INTENTS)[number]

/** Intencoes de transicao neutras: descrevem, nao executam animacao. */
export const BEAT_TRANSITIONS = [
    'none',
    'cut',
    'fade',
    'dissolve',
    'slide',
    'material-dissolve',
] as const

export type BeatTransition = (typeof BEAT_TRANSITIONS)[number]

/**
 * Estado tecnico do beat dentro do pipeline. "validated" significa apenas
 * revisao tecnica: nao concede aprovacao editorial, autorizacao de gravacao,
 * de producao nem de publicacao.
 */
export const BEAT_VALIDATION_STATUSES = ['draft', 'review', 'validated', 'rejected'] as const

export type BeatValidationStatus = (typeof BEAT_VALIDATION_STATUSES)[number]

/** Status de metadata do plano; "validated" tambem e apenas tecnico. */
export const BEAT_PLAN_METADATA_STATUSES = ['draft', 'review', 'validated', 'archived'] as const

export type BeatPlanMetadataStatus = (typeof BEAT_PLAN_METADATA_STATUSES)[number]

/** Limite documentado de tags em metadata. */
export const BEAT_PLAN_MAX_TAGS = 8

/** Limite tecnico (heuristica) de caracteres em narration.text para warning. */
export const BEAT_PLAN_MAX_NARRATION_LENGTH = 240

/** Limite tecnico (heuristica) de caracteres em onScreenText para warning. */
export const BEAT_PLAN_MAX_ON_SCREEN_TEXT_LENGTH = 160

/** Piso da duracao minima estimada de leitura, em milissegundos. */
export const BEAT_PLAN_MIN_READING_MS = 1000

/** Custo de leitura por palavra, em milissegundos. */
export const BEAT_PLAN_MS_PER_WORD = 300

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
export const BEAT_PLAN_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'projectId',
    'compositionId',
    'id',
    'locale',
    'beats',
    'metadata',
] as const

/** Campos conhecidos de um beat, em ordem fixa de verificacao. */
export const BEAT_FIELDS = [
    'id',
    'order',
    'sceneIds',
    'narrativeFunction',
    'startMs',
    'durationMs',
    'narration',
    'onScreenText',
    'visualIntent',
    'motionIntent',
    'transitionIn',
    'transitionOut',
    'editorialEvidence',
    'validationStatus',
] as const

export { KEBAB_CASE_PATTERN }

/**
 * Narracao como texto canonico. Nao ha provider, voz, arquivo nem configuracao
 * de TTS: o AudioPlan pertence a uma fatia futura.
 */
export interface BeatNarration {
    text: string
}

/**
 * Um recorte temporal da Composition. Cena e beat nao possuem relacao
 * obrigatoria de um para um: um beat pode atravessar mais de uma cena e uma
 * cena pode ser referenciada por mais de um beat.
 */
export interface Beat {
    id: string
    /** Inteiro a partir de 1, unico, sem lacunas e igual a posicao no array. */
    order: number
    sceneIds: string[]
    narrativeFunction: BeatNarrativeFunction
    /** Inteiro maior ou igual a zero, em milissegundos. */
    startMs: number
    /** Inteiro maior que zero, em milissegundos. */
    durationMs: number
    narration?: BeatNarration
    /** Texto canonico editavel; nunca fica incorporado a imagem. */
    onScreenText?: string
    /** Descricao declarativa de intencao visual; nao e prompt de fornecedor. */
    visualIntent: string
    motionIntent: BeatMotionIntent
    transitionIn: BeatTransition
    transitionOut: BeatTransition
    /** Identificadores conceituais; a existencia fisica nao e verificada. */
    editorialEvidence: string[]
    validationStatus: BeatValidationStatus
}

/** Metadata opcional e pequena; "validated" nao concede autorizacao editorial. */
export interface BeatPlanMetadata {
    status?: BeatPlanMetadataStatus
    description?: string
    tags?: string[]
}

/** Traducao temporal declarativa de uma Composition, vinculada por ids. */
export interface BeatPlan {
    schemaVersion: number
    projectId: string
    compositionId: string
    id: string
    locale: string
    beats: Beat[]
    metadata?: BeatPlanMetadata
}
