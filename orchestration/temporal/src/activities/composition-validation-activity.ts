/**
 * Activity real de validacao de Composition v1 contra ProjectManifest (TEMPORAL-02-03).
 *
 * Consome exclusivamente a fronteira publica de `marcasalao-marketing-platform` e
 * delega diretamente para `validateComposition(composition, project)` (ordem estrita:
 * Composition primeiro, ProjectManifest depois).
 *
 * Pureza estrita na fronteira externa:
 * - zero rede
 * - zero filesystem / I/O
 * - zero subprocesso
 * - zero mutacao dos inputs
 * - zero duplicacao do validador do nucleo
 *
 * Resultados de dominio com `valid: false` sao retornados normalmente como
 * CompositionValidationReport sem lancar excecao. Falhas inesperadas capturadas
 * na fronteira sao convertidas em ApplicationFailure nao-retryable com codigo
 * TEMPORAL_COMPOSITION_ACTIVITY_FAILED e mensagem fixa sanitizada.
 */

import { ApplicationFailure } from '@temporalio/common'
import {
    validateComposition,
    type CompositionValidationReport,
} from 'marcasalao-marketing-platform'

export const TEMPORAL_COMPOSITION_ACTIVITY_FAILED = 'TEMPORAL_COMPOSITION_ACTIVITY_FAILED' as const

export const TEMPORAL_COMPOSITION_ACTIVITY_FAILED_MESSAGE =
    'Composition validation activity failed unexpectedly.' as const

export interface CompositionValidationActivityInput {
    readonly project: unknown
    readonly composition: unknown
}

export async function validateCompositionActivity(
    input: CompositionValidationActivityInput,
): Promise<CompositionValidationReport> {
    try {
        if (!input || typeof input !== 'object') {
            throw new TypeError('Activity input must be an object with project and composition properties.')
        }

        const { composition, project } = input
        return validateComposition(composition, project)
    } catch (error: unknown) {
        if (error instanceof ApplicationFailure) {
            throw error
        }

        throw ApplicationFailure.create({
            type: TEMPORAL_COMPOSITION_ACTIVITY_FAILED,
            message: TEMPORAL_COMPOSITION_ACTIVITY_FAILED_MESSAGE,
            nonRetryable: true,
        })
    }
}
