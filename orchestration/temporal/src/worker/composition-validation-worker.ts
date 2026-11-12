/**
 * Worker local dedicado a validacao de Composition (TEMPORAL-02).
 *
 * Registra o Workflow e a Activity ja integrados na Task Queue dedicada
 * composition-validation-v1. Somente localhost: a guarda compartilhada de
 * src/local-address.ts recusa endereco remoto antes de qualquer conexao.
 * Importar este modulo nao cria Worker, nao abre conexao e nao polla nada.
 */
import { fileURLToPath } from 'node:url'

import { NativeConnection, Worker } from '@temporalio/worker'

import { validateCompositionActivity } from '../activities/composition-validation-activity.js'
import {
    COMPOSITION_VALIDATION_NAMESPACE,
    COMPOSITION_VALIDATION_TASK_QUEUE,
} from '../client/composition-validation-start.js'
import { DEFAULT_PILOT_ADDRESS, checkLocalAddress } from '../local-address.js'
import { attachWorkerShutdownSignals } from './composition-validation-worker-lifecycle.js'

/** O bundle do Workflow e gerado pelo webpack a partir deste arquivo-fonte. */
export const COMPOSITION_VALIDATION_WORKFLOWS_PATH = fileURLToPath(
    new URL('../workflows/composition-validation-workflow.js', import.meta.url),
)

export interface CompositionValidationWorkerOptions {
    readonly address?: string
    readonly namespace?: string
}

export interface CompositionValidationWorkerRuntime {
    readonly worker: Worker
    readonly connection: NativeConnection
    readonly address: string
    readonly namespace: string
}

export async function createCompositionValidationWorker(
    options: CompositionValidationWorkerOptions = {},
): Promise<CompositionValidationWorkerRuntime> {
    const address = options.address ?? DEFAULT_PILOT_ADDRESS
    const problem = checkLocalAddress(address)
    if (problem !== null) {
        throw new Error(problem)
    }
    const namespace = options.namespace ?? COMPOSITION_VALIDATION_NAMESPACE
    const connection = await NativeConnection.create({ address })
    try {
        const worker = await Worker.create({
            connection,
            namespace,
            taskQueue: COMPOSITION_VALIDATION_TASK_QUEUE,
            workflowsPath: COMPOSITION_VALIDATION_WORKFLOWS_PATH,
            activities: { validateCompositionActivity },
        })
        return { worker, connection, address, namespace }
    } catch (error: unknown) {
        await connection.close()
        throw error
    }
}

export async function runCompositionValidationWorker(
    options: CompositionValidationWorkerOptions = {},
): Promise<number> {
    const runtime = await createCompositionValidationWorker(options)
    const signals = attachWorkerShutdownSignals(runtime.worker)
    try {
        process.stdout.write(
            `worker de validacao de composition na task queue ${COMPOSITION_VALIDATION_TASK_QUEUE} namespace ${runtime.namespace} contra ${runtime.address}\n`,
        )
        await runtime.worker.run()
        process.stdout.write('worker de validacao de composition encerrado\n')
        return 0
    } finally {
        signals.dispose()
        await runtime.connection.close()
    }
}