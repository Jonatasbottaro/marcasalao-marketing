/**
 * Codigos de falha estaveis do piloto TEMPORAL-01.
 *
 * A classe de cada codigo (retryable ou nao) fica registrada aqui para que
 * Workflow, Activities e testes consultem a mesma fonte. A mensagem livre e
 * secundaria: automacao depende do codigo.
 */
export const PILOT_FAILURE_CODES = {
    schemaUnsupported: 'TEMPORAL_PILOT_SCHEMA_UNSUPPORTED',
    requestIdRequired: 'TEMPORAL_PILOT_REQUEST_ID_REQUIRED',
    projectIdRequired: 'TEMPORAL_PILOT_PROJECT_ID_REQUIRED',
    operationInvalid: 'TEMPORAL_PILOT_OPERATION_INVALID',
    payloadInvalid: 'TEMPORAL_PILOT_PAYLOAD_INVALID',
    inputInvalid: 'TEMPORAL_PILOT_INPUT_INVALID',
    transientFailure: 'TEMPORAL_PILOT_ACTIVITY_TRANSIENT_FAILURE',
    nonRetryable: 'TEMPORAL_PILOT_ACTIVITY_NON_RETRYABLE',
    timeout: 'TEMPORAL_PILOT_TIMEOUT',
    workflowFailed: 'TEMPORAL_PILOT_WORKFLOW_FAILED',
    workflowIdConflict: 'TEMPORAL_PILOT_WORKFLOW_ID_CONFLICT',
} as const

export type PilotFailureCode = (typeof PILOT_FAILURE_CODES)[keyof typeof PILOT_FAILURE_CODES]

const CODE_VALUES: ReadonlySet<string> = new Set(Object.values(PILOT_FAILURE_CODES))

export function isPilotFailureCode(value: unknown): value is PilotFailureCode {
    return typeof value === 'string' && CODE_VALUES.has(value)
}
