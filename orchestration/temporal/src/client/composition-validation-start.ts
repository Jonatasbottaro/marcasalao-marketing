/**
 * Cliente de aplicacao da validacao de Composition em TEMPORAL-02.
 *
 * Unica camada que constroi Workflow ID, opcoes de start e classifica colisao.
 * Todo start passa obrigatoriamente por startAfterCompositionPreflight antes de
 * tocar o cliente Temporal: entrada invalida, sensivel ou grande demais nunca
 * estabelece execucao nem persiste payload na history.
 *
 * Saida sanitizada: nenhum stack, cause, mensagem de transporte, payload,
 * project, composition ou connection string sai deste modulo.
 */
import { WorkflowExecutionAlreadyStartedError } from '@temporalio/common'
import {
    WorkflowIdConflictPolicy,
    WorkflowIdReusePolicy,
    type Client,
    type WorkflowHandle,
} from '@temporalio/client'

import type { CompositionValidationPreflightFailureCode } from '../composition-validation/composition-validation-failures.js'
import type { CompositionValidationWorkflowInput } from '../composition-validation/composition-validation-input.js'
import { startAfterCompositionPreflight } from '../composition-validation/composition-validation-preflight.js'
import type { CompositionValidationWorkflowResult } from '../workflows/composition-validation-result.js'

export const COMPOSITION_VALIDATION_TASK_QUEUE = 'composition-validation-v1'

export const COMPOSITION_VALIDATION_WORKFLOW_TYPE = 'validateCompositionWorkflow'

export const COMPOSITION_VALIDATION_NAMESPACE = 'default'

/** Fonte unica dos codigos da via B (conflito de start) e de transporte do cliente. */
export const COMPOSITION_VALIDATION_START_FAILURE_CODES = Object.freeze({
    workflowIdConflict: 'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT',
    connectionFailed: 'TEMPORAL_COMPOSITION_CONNECTION_FAILED',
    startFailed: 'TEMPORAL_COMPOSITION_START_FAILED',
} as const)

export type CompositionValidationStartFailureCode =
    (typeof COMPOSITION_VALIDATION_START_FAILURE_CODES)[keyof typeof COMPOSITION_VALIDATION_START_FAILURE_CODES]

const CONNECTION_ERROR_CODES: ReadonlySet<string> = new Set(['ECONNREFUSED', 'UNAVAILABLE', '14'])

export interface CompositionValidationStartSuccess {
    readonly ok: true
    readonly requestId: string
    readonly workflowId: string
    readonly runId: string
    readonly handle: WorkflowHandle
}

export interface CompositionValidationStartFailure {
    readonly ok: false
    readonly requestId: string | null
    readonly workflowId: string | null
    readonly failureCode: CompositionValidationStartFailureCode | CompositionValidationPreflightFailureCode
}

export type CompositionValidationStartResult =
    | CompositionValidationStartSuccess
    | CompositionValidationStartFailure

export type CompositionValidationExecutionResult =
    | {
          readonly ok: true
          readonly start: CompositionValidationStartSuccess
          readonly result: CompositionValidationWorkflowResult
      }
    | {
          readonly ok: false
          readonly start: CompositionValidationStartFailure
      }

/** Workflow ID deterministico: sem data, sem aleatoriedade, sem hash, sem contentHash. */
export function compositionValidationWorkflowId(requestId: string): string {
    return `composition-validation-${requestId}`
}

export function compositionValidationStartOptions(input: CompositionValidationWorkflowInput) {
    return {
        taskQueue: COMPOSITION_VALIDATION_TASK_QUEUE,
        workflowId: compositionValidationWorkflowId(input.requestId),
        args: [input] as [CompositionValidationWorkflowInput],
        workflowIdReusePolicy: WorkflowIdReusePolicy.REJECT_DUPLICATE,
        workflowIdConflictPolicy: WorkflowIdConflictPolicy.FAIL,
    }
}

/** Colisao tem codigo proprio; transporte e erro desconhecido nunca vazam mensagem variavel. */
export function classifyCompositionValidationStartFailure(
    error: unknown,
): CompositionValidationStartFailureCode {
    if (error instanceof WorkflowExecutionAlreadyStartedError) {
        return COMPOSITION_VALIDATION_START_FAILURE_CODES.workflowIdConflict
    }
    const code = (error as { code?: unknown } | null)?.code
    if (typeof code === 'string' || typeof code === 'number') {
        if (CONNECTION_ERROR_CODES.has(String(code).toUpperCase())) {
            return COMPOSITION_VALIDATION_START_FAILURE_CODES.connectionFailed
        }
    }
    return COMPOSITION_VALIDATION_START_FAILURE_CODES.startFailed
}

/** Inicia exatamente uma vez, depois do preflight; nao aguarda o resultado. */
export async function startCompositionValidation(
    client: Client,
    input: unknown,
): Promise<CompositionValidationStartResult> {
    const gate = await startAfterCompositionPreflight(input, async (validated) => {
        const options = compositionValidationStartOptions(validated)
        try {
            const handle = await client.workflow.start(COMPOSITION_VALIDATION_WORKFLOW_TYPE, options)
            return {
                ok: true as const,
                requestId: validated.requestId,
                workflowId: options.workflowId,
                runId: handle.firstExecutionRunId,
                handle,
            }
        } catch (error: unknown) {
            return {
                ok: false as const,
                requestId: validated.requestId,
                workflowId: options.workflowId,
                failureCode: classifyCompositionValidationStartFailure(error),
            }
        }
    })
    if (!gate.ok) {
        return { ok: false, requestId: null, workflowId: null, failureCode: gate.code }
    }
    return gate.startResult
}

/** Inicia e aguarda handle.result(), preservando valid, invalid e failed sem remapear. */
export async function executeCompositionValidation(
    client: Client,
    input: unknown,
): Promise<CompositionValidationExecutionResult> {
    const start = await startCompositionValidation(client, input)
    if (!start.ok) {
        return { ok: false, start }
    }
    const result = (await start.handle.result()) as CompositionValidationWorkflowResult
    return { ok: true, start, result }
}