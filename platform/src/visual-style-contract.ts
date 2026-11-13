/**
 * Contrato interno VisualStyle v1 — direcao visual compartilhada para sobreposicoes
 * de texto (titulos editaveis).
 *
 * Define e documenta unidades e limites em relacao ao quadro de referencia vertical
 * de 1080x1920 (PlayResX=1080, PlayResY=1920).
 *
 * Nucleo estritamente puro e deterministico: sem I/O, sem rede, sem relogio,
 * sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const VISUAL_STYLE_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa. */
export const VISUAL_STYLE_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'id',
    'title',
] as const

/** Campos da secao title, em ordem fixa. */
export const VISUAL_STYLE_TITLE_FIELDS = [
    'textColor',
    'outlineColor',
    'fontSize',
    'marginTop',
    'marginHorizontal',
] as const

/** Padrao para cores hexadecimais #RRGGBB. */
export const HEX_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/

/**
 * Limites e unidades de configuracao em relacao ao quadro de referencia (1080x1920):
 * - fontSize: tamanho em pixels da fonte do titulo (min: 16px, max: 160px).
 * - marginTop: margem superior em pixels a partir do topo do quadro (min: 0px, max: 600px).
 * - marginHorizontal: margem lateral esquerda e direita em pixels (min: 0px, max: 400px).
 */
export const VISUAL_STYLE_LIMITS = {
    fontSize: { min: 16, max: 160 },
    marginTop: { min: 0, max: 600 },
    marginHorizontal: { min: 0, max: 400 },
} as const

/** Secao title com estilos de renderizacao de titulos editaveis. */
export interface VisualStyleTitle {
    readonly textColor: string
    readonly outlineColor: string
    readonly fontSize: number
    readonly marginTop: number
    readonly marginHorizontal: number
}

/** Documento declarativo VisualStyle v1. */
export interface VisualStyle {
    readonly schemaVersion: 1
    readonly id: string
    readonly title: VisualStyleTitle
}

/** Codigos de falha estaveis para validacao do estilo visual. */
export type VisualStyleFailureCode =
    | 'STYLE_INVALID'
    | 'STYLE_ID_INVALID'
    | 'STYLE_TITLE_INVALID'
    | 'STYLE_COLOR_INVALID'
    | 'STYLE_FONT_SIZE_INVALID'
    | 'STYLE_MARGIN_INVALID'

export type VisualStyleValidationResult =
    | {
        readonly ok: true
        readonly style: VisualStyle
    }
    | {
        readonly ok: false
        readonly failureCode: VisualStyleFailureCode
        readonly subject: string | null
    }

export { KEBAB_CASE_PATTERN }
