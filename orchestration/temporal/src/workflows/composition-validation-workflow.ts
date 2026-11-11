/**
 * Workflow deterministico de validacao de Composition v1 contra ProjectManifest
 * em TEMPORAL-02 (fatia Workflow).
 *
 * Orquestra uma unica chamada tipada via proxyActivities para
 * `validateCompositionActivity` usando a Retry Policy e o timeout canonicos do
 * PRD. Nao realiza preflight, nao importa o nucleo modular, nao acessa I/O e
 * devolve sempre um resultado estruturado e sanitizado
 * (`CompositionValidationWorkflowResult`).
 */
import { proxyActivities, type ActivityOptions } from '@temporalio/workflow'

import type * as compositionValidationActivities from '../activities/composition-validation-activity.js'
import type { CompositionValidationWorkflowInput } from '../composition-validation/composition-validation-input.js'
import { classifyCompositionActivityFailure } from './composition-validation-failure-classifier.js'
import {
    NON_RETRYABLE_COMPOSITION_ACTIVITY_ERROR_TYPES,
    failedCompositionValidationResult,
    resultFromCompositionValidationReport,
    type CompositionValidationWorkflowResult,
} from './composition-validation-result.js'

export const COMPOSITION_VALIDATION_ACTIVITY_OPTIONS: ActivityOptions = {
    startToCloseTimeout: '5 seconds',
    retry: {
        initialInterval: '1 second',
        backoffCoefficient: 2,
        maximumInterval: '2 seconds',
        maximumAttempts: 2,
        nonRetryableErrorTypes: [...NON_RETRYABLE_COMPOSITION_ACTIVITY_ERROR_TYPES],
    },
}

const { validateCompositionActivity } = proxyActivities<typeof compositionValidationActivities>(
    COMPOSITION_VALIDATION_ACTIVITY_OPTIONS,
)

export async function validateCompositionWorkflow(
    input: CompositionValidationWorkflowInput,
): Promise<CompositionValidationWorkflowResult> {
    const requestId = typeof input?.requestId === 'string' ? input.requestId : ''

    try {
        const report = await validateCompositionActivity({
            project: input.project,
            composition: input.composition,
        })
        return resultFromCompositionValidationReport(requestId, report)
    } catch (error: unknown) {
        const failureCode = classifyCompositionActivityFailure(error)
        return failedCompositionValidationResult(requestId, failureCode)
    }
}
