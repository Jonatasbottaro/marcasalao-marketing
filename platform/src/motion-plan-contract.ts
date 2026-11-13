/**
 * Contrato interno MotionPlan v1 — plano de efeitos de motion separado do
 * pedido de video, vinculado por requestId e por sceneId.
 *
 * O primeiro efeito e um contorno retangular com posicao e tamanho relativos ao
 * quadro final (0..1), cor, espessura e intervalo em milissegundos relativo a
 * cena. Comeca com um efeito por cena. Os tempos absolutos sao resolvidos pela
 * timeline canonica na camada de resolucao; este contrato e estrutural e puro.
 *
 * Parametros do efeito independentes de fornecedor ou LLM. Nucleo sem I/O, sem
 * rede, sem relogio, sem aleatoriedade, sem marca.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const MOTION_PLAN_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa. */
export const MOTION_PLAN_TOP_LEVEL_FIELDS = ['schemaVersion', 'requestId', 'effects'] as const

/** Campos conhecidos de cada efeito. */
export const MOTION_EFFECT_FIELDS = [
    'sceneId', 'region', 'color', 'thickness', 'startMs', 'endMs', 'fadeInMs', 'fadeOutMs',
] as const

/** Campos obrigatorios de cada efeito (fadeInMs/fadeOutMs opcionais). */
export const MOTION_EFFECT_REQUIRED_FIELDS = ['sceneId', 'region', 'color', 'thickness', 'startMs', 'endMs'] as const

/** Campos da regiao relativa ao quadro final. */
export const MOTION_REGION_FIELDS = ['x', 'y', 'w', 'h'] as const

/** Limites de espessura do contorno em pixels. */
export const MOTION_THICKNESS_MIN = 1
export const MOTION_THICKNESS_MAX = 40

/** Fade padrao de entrada/saida do contorno em milissegundos. */
export const MOTION_DEFAULT_FADE_MS = 200

/** Padrao hexadecimal #RRGGBB. */
export const MOTION_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/

export { KEBAB_CASE_PATTERN }

/** Regiao relativa ao quadro final (fracao 0..1). */
export interface MotionRegion {
    readonly x: number
    readonly y: number
    readonly w: number
    readonly h: number
}

/** Efeito de contorno retangular vinculado a uma cena. */
export interface MotionEffect {
    readonly sceneId: string
    readonly region: MotionRegion
    readonly color: string
    readonly thickness: number
    readonly startMs: number
    readonly endMs: number
    readonly fadeInMs?: number
    readonly fadeOutMs?: number
}

/** Plano de motion v1. */
export interface MotionPlan {
    readonly schemaVersion: 1
    readonly requestId: string
    readonly effects: readonly MotionEffect[]
}

/** Efeito resolvido com tempos absolutos pela timeline canonica. */
export interface ResolvedMotionEffect extends MotionEffect {
    readonly sceneStartMs: number
    readonly sceneDurationMs: number
    readonly absoluteStartMs: number
    readonly absoluteEndMs: number
    readonly resolvedFadeInMs: number
    readonly resolvedFadeOutMs: number
}

/** Codigos de falha estaveis. */
export type MotionPlanFailureCode =
    | 'MOTION_PLAN_INVALID'
    | 'MOTION_PLAN_SCHEMA_VERSION_UNSUPPORTED'
    | 'MOTION_PLAN_REQUEST_ID_INVALID'
    | 'MOTION_PLAN_EFFECTS_INVALID'
    | 'MOTION_EFFECT_SCENE_ID_INVALID'
    | 'MOTION_EFFECT_SCENE_DUPLICATE'
    | 'MOTION_EFFECT_REGION_INVALID'
    | 'MOTION_EFFECT_COLOR_INVALID'
    | 'MOTION_EFFECT_THICKNESS_INVALID'
    | 'MOTION_EFFECT_INTERVAL_INVALID'
    | 'MOTION_EFFECT_FADE_INVALID'
    | 'MOTION_PLAN_UNKNOWN_FIELD'
    | 'MOTION_SCENE_UNKNOWN'
    | 'MOTION_INTERVAL_OUT_OF_SCENE'
    | 'MOTION_SCENE_MOVING'

export type MotionPlanValidationResult =
    | { readonly ok: true; readonly plan: MotionPlan }
    | { readonly ok: false; readonly failureCode: MotionPlanFailureCode; readonly subject: string | null }

export type MotionPlanResolutionResult =
    | { readonly ok: true; readonly requestId: string; readonly effects: readonly ResolvedMotionEffect[] }
    | { readonly ok: false; readonly failureCode: MotionPlanFailureCode; readonly subject: string | null }