/**
 * Contrato interno TextOverlayPlan v1 — plano declarativo de sobreposicao
 * de titulos editaveis sobre imagem ou video por beat.
 *
 * Permite corrigir ou revisar chamadas na tela reaproveitando o visual e
 * preservando a sincronizacao de legendas, SRT e roteiro de narracao.
 *
 * Nucleo estritamente puro e deterministico: sem I/O, sem rede, sem relogio,
 * sem aleatoriedade, sem mutacao da entrada.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const TEXT_OVERLAY_PLAN_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa. */
export const TEXT_OVERLAY_PLAN_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'caseId',
    'overlays',
] as const

/** Campos de cada item de overlay, em ordem fixa. */
export const TEXT_OVERLAY_BINDING_FIELDS = ['beatId', 'text'] as const

/** Ligacao explicita de um beat a um texto de titulo sobreposto. */
export interface TextOverlayBinding {
    readonly beatId: string
    readonly text: string
}

/** Plano declarativo de sobreposicao textual. */
export interface TextOverlayPlan {
    readonly schemaVersion: 1
    readonly caseId: string
    readonly overlays: readonly TextOverlayBinding[]
}

/** Titulo resolvido com intervalo temporal derivado do pacote canonico. */
export interface ResolvedTextOverlay {
    readonly beatId: string
    readonly text: string
    readonly startMs: number
    readonly endMs: number
    readonly durationMs: number
}

/** Codigos de falha estaveis para validacao do plano de sobreposicao. */
export type TextOverlayPlanFailureCode =
    | 'PACKAGE_INVALID'
    | 'OVERLAY_PLAN_INVALID'
    | 'CASE_ID_MISMATCH'
    | 'OVERLAY_BEAT_DUPLICATE'
    | 'UNKNOWN_BEAT_REFERENCE'
    | 'OVERLAY_TEXT_EMPTY'

export type TextOverlayPlanValidationResult =
    | {
        readonly ok: true
        readonly plan: TextOverlayPlan
        readonly resolvedOverlays: readonly ResolvedTextOverlay[]
    }
    | {
        readonly ok: false
        readonly failureCode: TextOverlayPlanFailureCode
        readonly subject: string | null
    }

export { KEBAB_CASE_PATTERN }
