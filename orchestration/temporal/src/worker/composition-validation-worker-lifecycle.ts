/**
 * Lifecycle do Worker local de validacao de Composition (TEMPORAL-02).
 *
 * Encerramento controlado por SIGINT/SIGTERM: o handler pede shutdown gracioso
 * ao Worker (para de pollar, deixa a Activity em curso terminar) e o dispose
 * remove os listeners. No Windows a entrega de SIGTERM pelo sistema operacional
 * nao e comprovada; o caminho medido e o shutdown programatico e o finally dos
 * entrypoints (limitacao documentada no README, herdada de TEMPORAL-01).
 */
import type { Worker } from '@temporalio/worker'

export const COMPOSITION_VALIDATION_SHUTDOWN_SIGNALS: readonly NodeJS.Signals[] = ['SIGINT', 'SIGTERM']

export interface WorkerShutdownHandle {
    dispose(): void
}

export function attachWorkerShutdownSignals(
    worker: Worker,
    signals: readonly NodeJS.Signals[] = COMPOSITION_VALIDATION_SHUTDOWN_SIGNALS,
): WorkerShutdownHandle {
    const handler = (): void => {
        worker.shutdown()
    }
    for (const signal of signals) {
        process.on(signal, handler)
    }
    return {
        dispose(): void {
            for (const signal of signals) {
                process.removeListener(signal, handler)
            }
        },
    }
}