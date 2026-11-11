/**
 * Classificador deterministico de falhas tecnicas para o Workflow de validacao
 * de Composition v1 (TEMPORAL-02).
 *
 * Unica camada desta fatia que inspeciona classes de erro da SDK Temporal
 * (@temporalio/workflow). Percorre a cadeia de causes defensivamente (com
 * protecao contra ciclos) e devolve somente codigos conhecidos e sanitizados,
 * sem mensagem bruta, stack, details ou payload.
 */
import { ApplicationFailure, TemporalFailure, TimeoutFailure } from '@temporalio/workflow'

import {
    COMPOSITION_WORKFLOW_FAILURE_CODES,
    type CompositionWorkflowFailureCode,
} from './composition-validation-result.js'

export function classifyCompositionActivityFailure(
    error: unknown,
): CompositionWorkflowFailureCode {
    if (!(error instanceof Error)) {
        return COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed
    }

    const visited = new Set<unknown>()
    let current: unknown = error
    let deepestApplicationFailure: ApplicationFailure | null = null

    while (current instanceof Error && !visited.has(current)) {
        visited.add(current)

        if (current instanceof TimeoutFailure) {
            return COMPOSITION_WORKFLOW_FAILURE_CODES.timeout
        }

        if (current instanceof ApplicationFailure) {
            deepestApplicationFailure = current
        }

        current = current instanceof TemporalFailure
            ? current.cause
            : (current as { cause?: unknown }).cause
    }

    if (deepestApplicationFailure !== null) {
        if (deepestApplicationFailure.type === COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed) {
            return COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed
        }
        if (deepestApplicationFailure.type === COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure) {
            return COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure
        }
        return COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed
    }

    return COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed
}
