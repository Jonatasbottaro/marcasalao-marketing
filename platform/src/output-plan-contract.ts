import type { OutputMediaKind, RuleContext } from './output-profiles/types.js'

/**
 * Contrato do OutputPlan v1: o plano canonico produzido a partir do catalogo.
 *
 * Camada de tipos e limites **estruturais**, sem logica de validacao e sem
 * conexao com o catalogo: quem decide se um numero bate com o preset do perfil
 * e o validador do core (`validate-output-plan.ts`), nunca uma tabela paralela
 * aqui. O plano descreve forma geometrica planejada; nao certifica arquivo
 * nenhum, nao carrega duracao e nao publica nada.
 *
 * Ver docs/planejamento/R001-formatos-sociais.md (secoes 6.1, 6.2.1 e 6.4).
 */

/** Unica versao de OutputPlan suportada. */
export const OUTPUT_PLAN_SCHEMA_VERSION = 1

/** Superficie fechada do topo do plano, na ordem canonica de serializacao. */
export const OUTPUT_PLAN_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'projectId',
    'catalogVersion',
    'profileId',
    'profileRevision',
    'mediaKind',
    'ruleContext',
    'image',
    'video',
] as const

/** Campos permitidos no payload de imagem: sem fps, sem duracao, sem contener. */
export const OUTPUT_PLAN_IMAGE_FIELDS = ['width', 'height', 'aspectRatio'] as const

/** Campos permitidos no payload de video: `fps` existe aqui e so aqui. */
export const OUTPUT_PLAN_VIDEO_FIELDS = ['width', 'height', 'aspectRatio', 'fps'] as const

/** Limites estruturais de `fps` do plano: inteiros 1-120, como na Composition v1. */
export const OUTPUT_PLAN_FPS_MIN = 1
export const OUTPUT_PLAN_FPS_MAX = 120

/** Forma `W:H` com inteiros positivos; a relacao com a geometria e semantica. */
export const OUTPUT_PLAN_ASPECT_RATIO_PATTERN = /^\d+:\d+$/

/**
 * Necessidades de inspecao que nenhum relatorio desta fatia resolve. Enum
 * estavel e ordem fixa: o plano pode listar o que falta, jamais afirmar que
 * um arquivo existe, que tem certo formato, certo peso ou certa faixa de audio.
 */
export const REQUIRES_INSPECTION_VALUES = [
    'media-file',
    'image-format',
    'codec',
    'bytes',
    'audio-streams',
    'publication',
] as const
export type RequiresInspection = (typeof REQUIRES_INSPECTION_VALUES)[number]

/** Ordem emitida para planos de imagem (§6.2.1). */
export const REQUIRES_INSPECTION_IMAGE: readonly RequiresInspection[] = [
    'media-file',
    'image-format',
    'bytes',
    'publication',
]

/** Ordem emitida para planos de video (§6.2.1). */
export const REQUIRES_INSPECTION_VIDEO: readonly RequiresInspection[] = [
    'media-file',
    'codec',
    'bytes',
    'audio-streams',
    'publication',
]

/** Geometria planejada: dimensoes e proporcao declarada, nada de arquivo. */
export interface OutputPlanGeometry {
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
}

/** Payload de imagem: `fps` nao existe neste ramo, nem como nulo. */
export interface ImageOutputPlanPayload extends OutputPlanGeometry {}

/** Payload de video: dimensoes, proporcao e frame rate planejados. */
export interface VideoOutputPlanPayload extends OutputPlanGeometry {
    readonly fps: number
}

interface OutputPlanBase {
    readonly schemaVersion: 1
    /** `id` do ProjectManifest consumido; opaco alem do vinculo declarado. */
    readonly projectId: string
    /** Versao do catalogo usada para resolver; traca a tabela, nao o conteudo. */
    readonly catalogVersion: string
    readonly profileId: string
    readonly profileRevision: number
    readonly mediaKind: OutputMediaKind
    /** Ausente = contexto nao informado. Nunca `null` no JSON canonico (§2.1.1). */
    readonly ruleContext?: RuleContext
}

export interface ImageOutputPlan extends OutputPlanBase {
    readonly mediaKind: 'image'
    readonly image: ImageOutputPlanPayload
    readonly video?: never
}

export interface VideoOutputPlan extends OutputPlanBase {
    readonly mediaKind: 'video'
    readonly video: VideoOutputPlanPayload
    readonly image?: never
}

/** Uniao discriminada por `mediaKind`; `image` e `video` sao mutuamente exclusivos. */
export type OutputPlan = ImageOutputPlan | VideoOutputPlan

/** Narrowing publico, espelhando `CompositionSceneOfType`. */
export type OutputPlanOf<T extends OutputMediaKind> = Extract<OutputPlan, { mediaKind: T }>

/** Escopo de avaliacao de regras: que tipo de dado a camada chamada traz. */
export type RuleAssessmentScope = 'output-plan' | 'composition-output'
