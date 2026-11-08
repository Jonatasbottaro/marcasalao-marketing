/**
 * Desfecho de uma execucao do piloto TEMPORAL-01 a partir de um sinal neutro.
 *
 * Camada de nucleo: nao importa nada de @temporalio. A camada de orquestracao
 * traduz o erro da SDK para `PilotFailureSignal` e recebe daqui o par
 * status + codigo estavel. Violacao de contrato e sempre `rejected`; falha
 * tecnica e sempre `failed`; nada aqui inventa status nem codigo.
 */
import { NON_RETRYABLE_PILOT_CODES, PILOT_FAILURE_CODES, isPilotFailureCode, type PilotFailureCode } from './failures.js'
import type { PilotStatus } from './pilot-result.js'

export type PilotFailureSignal =
    | { kind: 'application'; code: string; nonRetryable: boolean }
    | { kind: 'timeout' }
    | { kind: 'unknown' }

export interface PilotOutcome {
    status: PilotStatus
    failureCode: PilotFailureCode
}

/** Codigo que significa "o piloto recusou a execucao", nao "quebrou". Derivado da fonte unica. */
const REJECTION_CODES: ReadonlySet<PilotFailureCode> = new Set(NON_RETRYABLE_PILOT_CODES)

export function outcomeFor(signal: PilotFailureSignal): PilotOutcome {
    if (signal.kind === 'timeout') {
        return { status: 'failed', failureCode: PILOT_FAILURE_CODES.timeout }
    }
    if (signal.kind !== 'application') {
        return { status: 'failed', failureCode: PILOT_FAILURE_CODES.workflowFailed }
    }

    if (!isPilotFailureCode(signal.code)) {
        return signal.nonRetryable
            ? { status: 'rejected', failureCode: PILOT_FAILURE_CODES.nonRetryable }
            : { status: 'failed', failureCode: PILOT_FAILURE_CODES.workflowFailed }
    }

    return { status: REJECTION_CODES.has(signal.code) ? 'rejected' : 'failed', failureCode: signal.code }
}
