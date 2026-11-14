/**
 * Contrato interno PlanningSuggestion v1 — sugestoes estruturadas por etapa
 * para a aba Planejamento do Video Studio.
 *
 * Duas etapas suportadas via uniao discriminada pelo campo `stage`:
 *   - 'briefing': consolidacao de ideia, campos do briefing, lacunas, perguntas
 *     curtas e afirmacoes com classificacao de confirmacao;
 *   - 'creative': opcoes de hook, roteiro em cenas, carrossel, textos por canal
 *     e sugestoes de destaque para Motion (indicando cena e elemento).
 *
 * Nucleo estritamente puro e deterministico: sem I/O, sem rede, sem relogio,
 * sem aleatoriedade e sem dependencia de marca ou provedor de LLM/imagem.
 */

import { BEAT_NARRATIVE_FUNCTIONS, type BeatNarrativeFunction } from './beat-plan-contract.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const PLANNING_SUGGESTION_SCHEMA_VERSION = 1

/** Etapas suportadas nas sugestoes versionadas de planejamento. */
export const PLANNING_SUGGESTION_STAGES = ['briefing', 'creative'] as const

export type PlanningSuggestionStage = (typeof PLANNING_SUGGESTION_STAGES)[number]

/** Dimensoes suportadas nas perguntas curtas de esclarecimento. */
export const PLANNING_QUESTION_DIMENSIONS = [
    'product',
    'audience',
    'objective',
    'coreMessage',
    'supportEvidence',
    'cta',
    'tone',
    'channels',
] as const

export type PlanningQuestionDimension = (typeof PLANNING_QUESTION_DIMENSIONS)[number]

/** Estados editoriais possiveis para uma afirmacao do briefing. */
export const PLANNING_CLAIM_STATUSES = ['confirmed', 'hypothesis', 'pending_validation'] as const

export type PlanningClaimStatus = (typeof PLANNING_CLAIM_STATUSES)[number]

/** Papis estruturais aceitos para cards de carrossel sugeridos. */
export const PLANNING_CAROUSEL_ROLES = ['cover', 'content', 'cta'] as const

export type PlanningCarouselRole = (typeof PLANNING_CAROUSEL_ROLES)[number]

/** Intencoes de movimento aceitas pelo recorte local de video. */
export const PLANNING_SCENE_MOTION_INTENTS = ['none', 'slow-zoom'] as const

export type PlanningSceneMotionIntent = (typeof PLANNING_SCENE_MOTION_INTENTS)[number]

/** Funcoes narrativas neutras reutilizadas do BeatPlan. */
export const PLANNING_NARRATIVE_FUNCTIONS = BEAT_NARRATIVE_FUNCTIONS

/** Limites de duracao por cena sugerida em milissegundos. */
export const PLANNING_SCENE_DURATION_MIN_MS = 1000
export const PLANNING_SCENE_DURATION_MAX_MS = 60000

/** Padrao hexadecimal #RRGGBB para sugestao de cor de destaque. */
export const PLANNING_SUGGESTION_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/

/** Campos da etapa 'briefing'. */
export const BRIEFING_SUGGESTION_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'stage',
    'product',
    'objective',
    'audience',
    'coreMessage',
    'supportEvidence',
    'cta',
    'tone',
    'recommendedProfiles',
    'gaps',
    'questions',
    'claims',
] as const

export const BRIEFING_SUGGESTION_REQUIRED_FIELDS = BRIEFING_SUGGESTION_TOP_LEVEL_FIELDS

export const PLANNING_QUESTION_FIELDS = ['id', 'dimension', 'question', 'suggestedAnswer'] as const
export const PLANNING_QUESTION_REQUIRED_FIELDS = ['id', 'dimension', 'question'] as const

export const PLANNING_CLAIM_FIELDS = [
    'id',
    'statement',
    'status',
    'requiresConfirmation',
    'evidenceMediaId',
    'warning',
] as const
export const PLANNING_CLAIM_REQUIRED_FIELDS = [
    'id',
    'statement',
    'status',
    'requiresConfirmation',
] as const

/** Campos da etapa 'creative'. */
export const CREATIVE_SUGGESTION_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'stage',
    'hookOptions',
    'selectedHookId',
    'scriptSummary',
    'videoScenes',
    'carouselCards',
    'channelCopies',
    'motionSuggestions',
] as const

export const CREATIVE_SUGGESTION_REQUIRED_FIELDS = [
    'schemaVersion',
    'stage',
    'hookOptions',
    'scriptSummary',
    'videoScenes',
    'carouselCards',
    'channelCopies',
] as const

export const PLANNING_HOOK_OPTION_FIELDS = ['id', 'text', 'angle'] as const
export const PLANNING_HOOK_OPTION_REQUIRED_FIELDS = ['id', 'text'] as const

export const PLANNING_VIDEO_SCENE_FIELDS = [
    'id',
    'objective',
    'narrativeFunction',
    'durationMs',
    'titleOverlay',
    'caption',
    'narration',
    'requiredMediaDescriptor',
    'mediaId',
    'motionIntent',
] as const

export const PLANNING_VIDEO_SCENE_REQUIRED_FIELDS = [
    'id',
    'objective',
    'narrativeFunction',
    'durationMs',
    'titleOverlay',
    'caption',
    'narration',
    'requiredMediaDescriptor',
] as const

export const PLANNING_CAROUSEL_CARD_FIELDS = [
    'id',
    'role',
    'title',
    'body',
    'requiredMediaDescriptor',
    'mediaId',
] as const

export const PLANNING_CAROUSEL_CARD_REQUIRED_FIELDS = ['id', 'role', 'title'] as const

export const PLANNING_CHANNEL_COPY_FIELDS = [
    'profileId',
    'title',
    'postText',
    'cta',
    'destinationUrl',
    'hashtags',
    'flags',
] as const

export const PLANNING_CHANNEL_COPY_REQUIRED_FIELDS = [
    'profileId',
    'title',
    'postText',
    'cta',
    'destinationUrl',
    'hashtags',
] as const

export const PLANNING_MOTION_SUGGESTION_FIELDS = [
    'sceneId',
    'targetElement',
    'suggestedColor',
    'suggestedStartMs',
    'suggestedEndMs',
    'note',
] as const

export const PLANNING_MOTION_SUGGESTION_REQUIRED_FIELDS = ['sceneId', 'targetElement'] as const

export { KEBAB_CASE_PATTERN }

export interface PlanningQuestion {
    readonly id: string
    readonly dimension: PlanningQuestionDimension
    readonly question: string
    readonly suggestedAnswer?: string
}

export interface PlanningClaim {
    readonly id: string
    readonly statement: string
    readonly status: PlanningClaimStatus
    readonly requiresConfirmation: boolean
    readonly evidenceMediaId?: string
    readonly warning?: string
}

export interface BriefingStageSuggestion {
    readonly schemaVersion: 1
    readonly stage: 'briefing'
    readonly product: string
    readonly objective: string
    readonly audience: string
    readonly coreMessage: string
    readonly supportEvidence: string
    readonly cta: string
    readonly tone: string
    readonly recommendedProfiles: readonly string[]
    readonly gaps: readonly string[]
    readonly questions: readonly PlanningQuestion[]
    readonly claims: readonly PlanningClaim[]
}

export interface PlanningHookOption {
    readonly id: string
    readonly text: string
    readonly angle?: string
}

export interface PlanningVideoScene {
    readonly id: string
    readonly objective: string
    readonly narrativeFunction: BeatNarrativeFunction
    readonly durationMs: number
    readonly titleOverlay: string
    readonly caption: string
    readonly narration: string
    readonly requiredMediaDescriptor: string
    readonly mediaId?: string
    readonly motionIntent?: PlanningSceneMotionIntent
}

export interface PlanningCarouselCard {
    readonly id: string
    readonly role: PlanningCarouselRole
    readonly title: string
    readonly body?: string
    readonly requiredMediaDescriptor?: string
    readonly mediaId?: string
}

export interface PlanningChannelCopy {
    readonly profileId: string
    readonly title: string
    readonly postText: string
    readonly cta: string
    readonly destinationUrl: string
    readonly hashtags: string
    readonly flags?: readonly string[]
}

export interface PlanningMotionSuggestion {
    readonly sceneId: string
    readonly targetElement: string
    readonly suggestedColor?: string
    readonly suggestedStartMs?: number
    readonly suggestedEndMs?: number
    readonly note?: string
}

export interface CreativeStageSuggestion {
    readonly schemaVersion: 1
    readonly stage: 'creative'
    readonly hookOptions: readonly PlanningHookOption[]
    readonly selectedHookId?: string
    readonly scriptSummary: string
    readonly videoScenes: readonly PlanningVideoScene[]
    readonly carouselCards: readonly PlanningCarouselCard[]
    readonly channelCopies: readonly PlanningChannelCopy[]
    readonly motionSuggestions?: readonly PlanningMotionSuggestion[]
}

export type PlanningSuggestion = BriefingStageSuggestion | CreativeStageSuggestion

/** Codigos de falha estaveis para automacao e diagnosticos no Studio. */
export type PlanningSuggestionFailureCode =
    | 'PLANNING_SUGGESTION_INVALID'
    | 'PLANNING_SUGGESTION_SCHEMA_VERSION_UNSUPPORTED'
    | 'PLANNING_SUGGESTION_STAGE_INVALID'
    | 'PLANNING_SUGGESTION_UNKNOWN_FIELD'
    | 'PLANNING_SUGGESTION_FIELD_INVALID'
    | 'PLANNING_QUESTION_INVALID'
    | 'PLANNING_QUESTION_ID_DUPLICATE'
    | 'PLANNING_CLAIM_INVALID'
    | 'PLANNING_CLAIM_ID_DUPLICATE'
    | 'PLANNING_HOOK_INVALID'
    | 'PLANNING_HOOK_ID_DUPLICATE'
    | 'PLANNING_SELECTED_HOOK_UNKNOWN'
    | 'PLANNING_SCENE_INVALID'
    | 'PLANNING_SCENE_ID_DUPLICATE'
    | 'PLANNING_CARD_INVALID'
    | 'PLANNING_CARD_ID_DUPLICATE'
    | 'PLANNING_CHANNEL_COPY_INVALID'
    | 'PLANNING_CHANNEL_COPY_DUPLICATE'
    | 'PLANNING_MOTION_SUGGESTION_INVALID'
    | 'PLANNING_MOTION_SCENE_UNKNOWN'
    | 'PLANNING_MOTION_SCENE_MOVING'
    | 'PLANNING_PROFILE_NOT_ALLOWED'

export type PlanningSuggestionValidationResult =
    | { readonly ok: true; readonly suggestion: PlanningSuggestion }
    | {
          readonly ok: false
          readonly failureCode: PlanningSuggestionFailureCode
          readonly subject: string | null
          readonly message: string
      }
