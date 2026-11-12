/**
 * Testes unitarios do Worker local de validacao de Composition (TEMPORAL-02).
 *
 * Sem servidor: a guarda de endereco recusa antes de qualquer conexao e o
 * lifecycle e exercitado com um Worker falso (contagem de listeners).
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import type { Worker } from '@temporalio/worker'

import {
    COMPOSITION_VALIDATION_WORKFLOWS_PATH,
    createCompositionValidationWorker,
} from '../../src/worker/composition-validation-worker.js'
import {
    COMPOSITION_VALIDATION_SHUTDOWN_SIGNALS,
    attachWorkerShutdownSignals,
} from '../../src/worker/composition-validation-worker-lifecycle.js'
import { COMPOSITION_VALIDATION_TASK_QUEUE } from '../../src/client/composition-validation-start.js'

test('endereco remoto e recusado antes de qualquer conexao', async () => {
    for (const address of ['temporal.example.com:443', '10.0.0.5:7233', 'localhost', 'localhost:0']) {
        await assert.rejects(
            createCompositionValidationWorker({ address }),
            /localhost|porta|forma/,
            `endereco ${address} deveria ser recusado`,
        )
    }
})

test('a fabrica aponta para o Workflow integrado e a Task Queue dedicada', () => {
    assert.match(COMPOSITION_VALIDATION_WORKFLOWS_PATH.replace(/\\/g, '/'), /workflows\/composition-validation-workflow\.js$/)
    assert.equal(COMPOSITION_VALIDATION_TASK_QUEUE, 'composition-validation-v1')
    assert.notEqual(COMPOSITION_VALIDATION_TASK_QUEUE, 'marketing-temporal-pilot-v1')
})

test('attach registra handlers de SIGINT/SIGTERM e dispose remove exatamente os seus', () => {
    const fakeWorker = { shutdown: () => undefined } as unknown as Worker
    const before = COMPOSITION_VALIDATION_SHUTDOWN_SIGNALS.map((s) => process.listenerCount(s))
    const handle = attachWorkerShutdownSignals(fakeWorker)
    const during = COMPOSITION_VALIDATION_SHUTDOWN_SIGNALS.map((s) => process.listenerCount(s))
    handle.dispose()
    const after = COMPOSITION_VALIDATION_SHUTDOWN_SIGNALS.map((s) => process.listenerCount(s))
    assert.deepEqual(during, before.map((count) => count + 1))
    assert.deepEqual(after, before)
})