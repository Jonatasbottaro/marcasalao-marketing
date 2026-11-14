/**
 * Contrato interno ImageRequest v1 — pedido visual revisavel derivado do
 * descritor de midia de uma cena de video ou card de carrossel.
 *
 * O pedido registra prompt editavel, finalidade, enquadramento, proporcao e
 * geometria derivadas do perfil selecionado, a referencia visual escolhida
 * (VisualAnchor) e o snapshot do contexto que o originou (descritor +
 * contextSha256 calculado pela camada de ferramentas). Titulos, legendas e
 * CTA permanecem nos campos editaveis da peca, fora deste contrato.
 *
 * O provedor de geracao e escolhido por acao na camada de ferramentas; o
 * contrato e independente de fornecedor para aceitar novos adaptadores sem
 * alterar pedidos existentes. Nucleo sem I/O, sem rede, sem relogio.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import { SHA256_HEX_PATTERN } from './visual-anchor-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const IMAGE_REQUEST_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa. */
export const IMAGE_REQUEST_TOP_LEVEL_FIELDS = [
    'schemaVersion', 'id', 'target', 'profileId', 'prompt', 'purpose', 'framing',
    'aspectRatio', 'geometry', 'anchor', 'context',
] as const

/** Campos do alvo (cena ou card). */
export const IMAGE_REQUEST_TARGET_FIELDS = ['kind', 'id'] as const

/** Tipos de alvo suportados. */
export const IMAGE_REQUEST_TARGET_KINDS = ['video_scene', 'carousel_card'] as const

/** Campos da geometria em pixels. */
export const IMAGE_REQUEST_GEOMETRY_FIELDS = ['width', 'height'] as const

/** Campos do vinculo de referencia visual no pedido. */
export const IMAGE_REQUEST_ANCHOR_FIELDS = ['anchorId', 'versionId', 'sha256', 'sendToProvider'] as const

/** Campos do snapshot de contexto. */
export const IMAGE_REQUEST_CONTEXT_FIELDS = ['descriptor', 'contextSha256'] as const

/** Proporcoes suportadas (derivadas dos perfis locais). */
export const IMAGE_REQUEST_ASPECT_RATIOS = ['9:16', '1:1', '16:9', '4:5'] as const

/** Limites de texto e geometria. */
export const IMAGE_REQUEST_PROMPT_MAX = 4000
export const IMAGE_REQUEST_PURPOSE_MAX = 300
export const IMAGE_REQUEST_FRAMING_MAX = 300
export const IMAGE_REQUEST_DESCRIPTOR_MAX = 2000
export const IMAGE_REQUEST_GEOMETRY_MIN = 16
export const IMAGE_REQUEST_GEOMETRY_MAX = 8192

/** Tolerancia relativa de coerencia entre geometria e proporcao declarada. */
export const IMAGE_REQUEST_ASPECT_TOLERANCE = 0.02

export { KEBAB_CASE_PATTERN, SHA256_HEX_PATTERN }

export type ImageRequestTargetKind = (typeof IMAGE_REQUEST_TARGET_KINDS)[number]
export type ImageRequestAspectRatio = (typeof IMAGE_REQUEST_ASPECT_RATIOS)[number]

/** Alvo do pedido: cena de video ou card de carrossel. */
export interface ImageRequestTarget {
    readonly kind: ImageRequestTargetKind
    readonly id: string
}

/** Geometria alvo em pixels. */
export interface ImageRequestGeometry {
    readonly width: number
    readonly height: number
}

/** Referencia visual escolhida para o pedido (opcional). */
export interface ImageRequestAnchor {
    readonly anchorId: string
    readonly versionId: string
    readonly sha256: string
    readonly sendToProvider: boolean
}

/** Snapshot do contexto que originou o pedido. */
export interface ImageRequestContext {
    readonly descriptor: string
    readonly contextSha256: string
}

/** Pedido visual revisavel v1. */
export interface ImageRequest {
    readonly schemaVersion: 1
    readonly id: string
    readonly target: ImageRequestTarget
    readonly profileId: string
    readonly prompt: string
    readonly purpose: string
    readonly framing: string
    readonly aspectRatio: ImageRequestAspectRatio
    readonly geometry: ImageRequestGeometry
    readonly anchor: ImageRequestAnchor | null
    readonly context: ImageRequestContext
}

/** Codigos de falha estaveis. */
export type ImageRequestFailureCode =
    | 'IMAGE_REQUEST_INVALID'
    | 'IMAGE_REQUEST_SCHEMA_VERSION_UNSUPPORTED'
    | 'IMAGE_REQUEST_UNKNOWN_FIELD'
    | 'IMAGE_REQUEST_ID_INVALID'
    | 'IMAGE_REQUEST_TARGET_INVALID'
    | 'IMAGE_REQUEST_PROFILE_INVALID'
    | 'IMAGE_REQUEST_PROMPT_INVALID'
    | 'IMAGE_REQUEST_PURPOSE_INVALID'
    | 'IMAGE_REQUEST_FRAMING_INVALID'
    | 'IMAGE_REQUEST_ASPECT_INVALID'
    | 'IMAGE_REQUEST_GEOMETRY_INVALID'
    | 'IMAGE_REQUEST_GEOMETRY_MISMATCH'
    | 'IMAGE_REQUEST_ANCHOR_INVALID'
    | 'IMAGE_REQUEST_CONTEXT_INVALID'

export type ImageRequestValidationResult =
    | { readonly ok: true; readonly request: ImageRequest }
    | { readonly ok: false; readonly failureCode: ImageRequestFailureCode; readonly subject: string | null }