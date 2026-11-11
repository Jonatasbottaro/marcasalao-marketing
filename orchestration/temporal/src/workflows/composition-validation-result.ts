/**
 * Contrato de resultado e construtores puros do Workflow de validacao de
 * Composition v1 em TEMPORAL-02 (fatia Workflow).
 *
 * Modulo puro e deterministico: zero imports de @temporalio/*, zero imports de
 * runtime externos, zero I/O e zero leitura de ambiente. Preserva os
 * identificadores vindos exclusivamente do relatorio validado em valid/invalid
 * e mantem null em failed.
 */
import type { validateCompositionActivity } from '../activities/composition-validation-activity.js'

export type CompositionValidationReport = Awaited<ReturnType<typeof validateCompositionActivity>>

export const COMPOSITION_VALIDATION_RESULT_SCHEMA_VERSION = 1 as const

export const COMPOSITION_VALIDATION_STEP = 'validate-composition' as const

export type CompositionValidationCompletedStep = typeof COMPOSITION_VALIDATION_STEP

export const COMPOSITION_WORKFLOW_FAILURE_CODES = Object.freeze({
    activityFailed: 'TEMPORAL_COMPOSITION_ACTIVITY_FAILED',
    timeout: 'TEMPORAL_COMPOSITION_TIMEOUT',
    transientFailure: 'TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE',
} as const)

export type CompositionWorkflowFailureCode =
    (typeof COMPOSITION_WORKFLOW_FAILURE_CODES)[keyof typeof COMPOSITION_WORKFLOW_FAILURE_CODES]

export const NON_RETRYABLE_COMPOSITION_ACTIVITY_ERROR_TYPES = Object.freeze([
    COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
] as const)

const WORKFLOW_FAILURE_CODE_SET: ReadonlySet<string> = new Set(
    Object.values(COMPOSITION_WORKFLOW_FAILURE_CODES),
)

export function isCompositionWorkflowFailureCode(
    value: unknown,
): value is CompositionWorkflowFailureCode {
    return typeof value === 'string' && WORKFLOW_FAILURE_CODE_SET.has(value)
}

export type CompositionValidationWorkflowStatus = 'valid' | 'invalid' | 'failed'

export interface CompositionValidationWorkflowResult {
    readonly schemaVersion: typeof COMPOSITION_VALIDATION_RESULT_SCHEMA_VERSION
    readonly requestId: string
    readonly projectId: string | null
    readonly compositionId: string | null
    readonly status: CompositionValidationWorkflowStatus
    readonly validation: CompositionValidationReport | null
    readonly completedSteps: readonly CompositionValidationCompletedStep[]
    readonly failureCode: CompositionWorkflowFailureCode | null
}

export function resultFromCompositionValidationReport(
    requestId: string,
    report: CompositionValidationReport,
): CompositionValidationWorkflowResult {
    return {
        schemaVersion: COMPOSITION_VALIDATION_RESULT_SCHEMA_VERSION,
        requestId,
        projectId: report.projectId,
        compositionId: report.compositionId,
        status: report.valid ? 'valid' : 'invalid',
        validation: report,
        completedSteps: [COMPOSITION_VALIDATION_STEP],
        failureCode: null,
    }
}

export function failedCompositionValidationResult(
    requestId: string,
    failureCode: CompositionWorkflowFailureCode,
): CompositionValidationWorkflowResult {
    return {
        schemaVersion: COMPOSITION_VALIDATION_RESULT_SCHEMA_VERSION,
        requestId,
        projectId: null,
        compositionId: null,
        status: 'failed',
        validation: null,
        completedSteps: [],
        failureCode,
    }
}
