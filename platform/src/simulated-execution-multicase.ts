/**
 * Agregacao multicase da execucao simulada v1.
 *
 * Funcao pura sobre resultados individuais: ordem estavel, contagens por
 * estado, isolamento de falhas e nenhuma regra por marca. A orquestracao
 * (leitura dos pacotes, execucao e escrita) vive na CLI; cada pacote e
 * executado sequencialmente em diretorio separado por executionId.
 */

import type {
    SimulatedExecutionReport,
    SimulatedExecutionStatus,
} from './simulated-execution-report-contract.js'

export type SimulatedExecutionCaseStatus =
    | SimulatedExecutionStatus
    | 'package-invalid'
    | 'plan-invalid'
    | 'write-failed'

export interface SimulatedExecutionCaseResult {
    /** Nome logico do arquivo de pacote (basename); nunca caminho absoluto. */
    readonly sourceName: string
    readonly packageId: string | null
    readonly executionId: string | null
    readonly status: SimulatedExecutionCaseStatus
    readonly report: SimulatedExecutionReport | null
    readonly failureCode: string | null
    readonly summary: string
}

export interface SimulatedExecutionsReport {
    readonly schemaVersion: 1
    readonly valid: boolean
    readonly packageCount: number
    readonly completedCount: number
    readonly failedCount: number
    readonly cancelledCount: number
    readonly errorCount: number
    readonly executions: readonly SimulatedExecutionCaseResult[]
    readonly summary: string
}

export const SIMULATED_EXECUTIONS_VALID_SUMMARY = 'All simulated executions completed.'

export function simulatedExecutionsSummary(report: Omit<SimulatedExecutionsReport, 'summary' | 'valid'>): string {
    if (report.packageCount > 0 && report.completedCount === report.packageCount) {
        return SIMULATED_EXECUTIONS_VALID_SUMMARY
    }
    return `Simulated executions finished: ${report.completedCount} completed, ${report.failedCount} failed, ${report.cancelledCount} cancelled, ${report.errorCount} error(s).`
}

/** Agrega resultados individuais sem altera-los; lista vazia nunca e valida. */
export function aggregateSimulatedExecutions(
    results: readonly SimulatedExecutionCaseResult[],
): SimulatedExecutionsReport {
    const completedCount = results.filter((result) => result.status === 'completed').length
    const failedCount = results.filter((result) => result.status === 'failed').length
    const cancelledCount = results.filter((result) => result.status === 'cancelled').length
    const errorCount = results.filter(
        (result) => result.status === 'package-invalid' || result.status === 'plan-invalid' || result.status === 'write-failed',
    ).length
    const base = {
        schemaVersion: 1 as const,
        packageCount: results.length,
        completedCount,
        failedCount,
        cancelledCount,
        errorCount,
        executions: results,
    }
    const valid = results.length > 0 && completedCount === results.length
    return { ...base, valid, summary: simulatedExecutionsSummary(base) }
}
