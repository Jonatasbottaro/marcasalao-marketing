/**
 * Contrato interno VisualAnchor v1 — referencia visual reutilizavel dentro de
 * um trabalho, vinculada a uma versao de midia da biblioteca pelo ID da versao
 * e pelo SHA-256 do arquivo.
 *
 * Registra direcao visual, elementos obrigatorios e elementos a evitar. A
 * mesma referencia pode ser usada por varias cenas e cards; cada pedido de
 * imagem decide se a referencia sera enviada ao provedor.
 *
 * Independente de fornecedor, LLM ou marca. Nucleo sem I/O, sem rede, sem
 * relogio, sem aleatoriedade.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const VISUAL_ANCHOR_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa. */
export const VISUAL_ANCHOR_TOP_LEVEL_FIELDS = [
    'schemaVersion', 'id', 'title', 'reference', 'direction', 'mustInclude', 'mustAvoid', 'origin', 'license',
] as const

/** Campos da referencia de midia (versao + hash). */
export const VISUAL_ANCHOR_REFERENCE_FIELDS = ['mediaId', 'versionId', 'sha256'] as const

/** Limites de texto do contrato. */
export const VISUAL_ANCHOR_TITLE_MAX = 120
export const VISUAL_ANCHOR_DIRECTION_MAX = 2000
export const VISUAL_ANCHOR_ELEMENT_MAX = 200
export const VISUAL_ANCHOR_ELEMENTS_MAX = 20
export const VISUAL_ANCHOR_ORIGIN_MAX = 120
export const VISUAL_ANCHOR_LICENSE_MAX = 120

/** Padrao SHA-256 hexadecimal minusculo. */
export const SHA256_HEX_PATTERN = /^[0-9a-f]{64}$/

export { KEBAB_CASE_PATTERN }

/** Vinculo da referencia com uma versao especifica de midia da biblioteca. */
export interface VisualAnchorReference {
    readonly mediaId: string
    readonly versionId: string
    readonly sha256: string
}

/** Referencia visual ancorada v1. */
export interface VisualAnchor {
    readonly schemaVersion: 1
    readonly id: string
    readonly title: string
    readonly reference: VisualAnchorReference
    readonly direction: string
    readonly mustInclude: readonly string[]
    readonly mustAvoid: readonly string[]
    readonly origin: string
    readonly license: string
}

/** Codigos de falha estaveis. */
export type VisualAnchorFailureCode =
    | 'VISUAL_ANCHOR_INVALID'
    | 'VISUAL_ANCHOR_SCHEMA_VERSION_UNSUPPORTED'
    | 'VISUAL_ANCHOR_UNKNOWN_FIELD'
    | 'VISUAL_ANCHOR_ID_INVALID'
    | 'VISUAL_ANCHOR_TITLE_INVALID'
    | 'VISUAL_ANCHOR_REFERENCE_INVALID'
    | 'VISUAL_ANCHOR_DIRECTION_INVALID'
    | 'VISUAL_ANCHOR_ELEMENTS_INVALID'
    | 'VISUAL_ANCHOR_ORIGIN_INVALID'
    | 'VISUAL_ANCHOR_LICENSE_INVALID'

export type VisualAnchorValidationResult =
    | { readonly ok: true; readonly anchor: VisualAnchor }
    | { readonly ok: false; readonly failureCode: VisualAnchorFailureCode; readonly subject: string | null }