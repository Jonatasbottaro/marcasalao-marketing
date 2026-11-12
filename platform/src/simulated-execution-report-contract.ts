/**
 * Contrato interno SimulatedExecutionReport v1 — relatorio imutavel da
 * execucao local simulada de um SimulatedExecutionPlan.
 *
 * Estados e eventos sao deterministicos: nenhuma data real, nenhum caminho
 * absoluto, nenhum stack trace, nenhuma mensagem variavel, nenhum payload
 * completo de documento. O tempo logico vem da timeline do pacote; a ordem
 * vem de `sequence` inteira. Cancelado nao e falho; falho exige failureCode;
 * concluido exige todos os steps do plano.
 */

/** Estados da execucao simulada. */
export type SimulatedExecutionStatus =
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'cancelled'

export const SIMULATED_EXECUTION_STATUSES: readonly SimulatedExecutionStatus[] = Object.freeze([
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled',
] as const)

/** Tipos de evento, na semantica do lifecycle simulado. */
export type SimulatedExecutionEventType =
    | 'execution-started'
    | 'step-started'
    | 'artifact-created'
    | 'step-completed'
    | 'step-failed'
    | 'execution-cancelled'
    | 'execution-completed'
    | 'execution-failed'

export const SIMULATED_EXECUTION_EVENT_TYPES: readonly SimulatedExecutionEventType[] = Object.freeze([
    'execution-started',
    'step-started',
    'artifact-created',
    'step-completed',
    'step-failed',
    'execution-cancelled',
    'execution-completed',
    'execution-failed',
] as const)

/**
 * Evento deterministico: somente sequencia, tipo, executionId e referencias
 * opcionais de step/artefato/falha. Sem timestamp real.
 */
export interface SimulatedExecutionEvent {
    readonly sequence: number
    readonly type: SimulatedExecutionEventType
    readonly executionId: string
    readonly stepId?: string
    readonly artifactId?: string
    readonly failureCode?: string
}

/** Relatorio de um artefato textual simulado, com hash SHA-256 do conteudo. */
export interface SimulatedArtifactReport {
    readonly id: string
    readonly logicalName: string
    readonly contentType: string
    readonly sha256: string
}

export const SIMULATED_REPORT_SCHEMA_VERSION = 1

/** Campos de topo do relatorio, em ordem canonica de serializacao. */
export const SIMULATED_REPORT_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'executionId',
    'packageId',
    'status',
    'resumedFromStatus',
    'completedSteps',
    'failedStepId',
    'failureCode',
    'artifactCount',
    'artifacts',
    'events',
    'summary',
] as const

export interface SimulatedExecutionReport {
    readonly schemaVersion: 1
    readonly executionId: string
    readonly packageId: string
    readonly status: SimulatedExecutionStatus
    /** Estado anterior quando a execucao foi retomada; null em execucao nova. */
    readonly resumedFromStatus: SimulatedExecutionStatus | null
    readonly completedSteps: readonly string[]
    readonly failedStepId: string | null
    readonly failureCode: string | null
    readonly artifactCount: number
    readonly artifacts: readonly SimulatedArtifactReport[]
    readonly events: readonly SimulatedExecutionEvent[]
    readonly summary: string
}

/** Codigos de falha de etapa do executor simulado (controladas, deterministicas). */
export const SIMULATED_STEP_FAILURE_CODE = 'SIMULATED_STEP_FAILURE'

/** Codigos de incompatibilidade da retomada local. */
export type SimulatedResumeIncompatibilityCode =
    | 'REPORT_INVALID'
    | 'EXECUTION_ID_MISMATCH'
    | 'PACKAGE_ID_MISMATCH'
    | 'STATUS_NOT_RESUMABLE'
    | 'ARTIFACT_HASH_MISMATCH'

export const SIMULATED_EXECUTION_COMPLETED_SUMMARY = 'Simulated execution completed.'
export const SIMULATED_EXECUTION_FAILED_SUMMARY = 'Simulated execution failed.'
export const SIMULATED_EXECUTION_CANCELLED_SUMMARY = 'Simulated execution cancelled.'

export function simulatedReportSummary(status: SimulatedExecutionStatus): string {
    if (status === 'completed') return SIMULATED_EXECUTION_COMPLETED_SUMMARY
    if (status === 'failed') return SIMULATED_EXECUTION_FAILED_SUMMARY
    if (status === 'cancelled') return SIMULATED_EXECUTION_CANCELLED_SUMMARY
    return `Simulated execution is ${status}.`
}

export const SIMULATED_REPORT_VALID_SUMMARY = 'Simulated execution report is valid.'

export function simulatedReportInvalidSummary(errorCount: number): string {
    return `Simulated execution report is invalid: ${errorCount} error(s).`
}
