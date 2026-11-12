/**
 * Execucao local REAL de TEMPORAL-02: servidor efemero completo do SDK
 * (createLocal, sem time-skipping), Worker real criado pela mesma fabrica do
 * CLI de worker, cliente real, start real, resultado real e shutdown real.
 *
 * Tres caminhos medidos: valid, invalid e colisao de Workflow ID. Nenhum
 * servidor externo, nenhum Docker, nenhum namespace remoto. O binario do
 * servidor usa o TEMP do processo (redirecionavel para dentro da raiz).
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { TestWorkflowEnvironment } from '@temporalio/testing'

import type { JsonObject } from '../../src/composition-validation/composition-validation-input.js'
import {
    executeCompositionValidation,
    startCompositionValidation,
} from '../../src/client/composition-validation-start.js'
import { createCompositionValidationWorker } from '../../src/worker/composition-validation-worker.js'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const repositoryRoot = path.resolve(testDir, '../../../../..')

const project = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, 'platform/examples/projects/marca-salao.project.json'), 'utf8'),
) as JsonObject

const composition = JSON.parse(
    fs.readFileSync(
        path.join(repositoryRoot, 'platform/examples/compositions/marca-salao-pilot.composition.json'),
        'utf8',
    ),
) as JsonObject

async function withLocalWorker(run: (env: TestWorkflowEnvironment) => Promise<void>): Promise<void> {
    const env = await TestWorkflowEnvironment.createLocal()
    const runtime = await createCompositionValidationWorker({ address: env.address })
    const workerRun = runtime.worker.run()
    try {
        await run(env)
    } finally {
        runtime.worker.shutdown()
        await workerRun
        await runtime.connection.close()
        await env.teardown()
    }
}

test('execucao local real: valid com Worker e cliente reais', async () => {
    await withLocalWorker(async (env) => {
        const execution = await executeCompositionValidation(env.client, {
            schemaVersion: 1,
            requestId: 'req-local-test-valid',
            project,
            composition,
        })
        assert.equal(execution.ok, true)
        if (execution.ok) {
            assert.equal(execution.result.status, 'valid')
            assert.equal(execution.result.failureCode, null)
            assert.deepEqual(execution.result.completedSteps, ['validate-composition'])
            assert.equal(execution.start.workflowId, 'composition-validation-req-local-test-valid')
            assert.ok(execution.start.runId.length > 0)
        }
    })
})

test('execucao local real: invalid de dominio preservado sem remapeamento', async () => {
    await withLocalWorker(async (env) => {
        const execution = await executeCompositionValidation(env.client, {
            schemaVersion: 1,
            requestId: 'req-local-test-invalid',
            project,
            composition: { ...composition, projectId: 'outro-projeto-incompativel' },
        })
        assert.equal(execution.ok, true)
        if (execution.ok) {
            assert.equal(execution.result.status, 'invalid')
            assert.equal(execution.result.failureCode, null)
            assert.ok(execution.result.validation && execution.result.validation.errors.length > 0)
        }
    })
})

test('execucao local real: colisao recusa o segundo start e preserva a execucao original', async () => {
    await withLocalWorker(async (env) => {
        const input = { schemaVersion: 1, requestId: 'req-local-test-collision', project, composition }
        const first = await executeCompositionValidation(env.client, input)
        assert.equal(first.ok, true)
        if (first.ok) assert.equal(first.result.status, 'valid')

        const second = await startCompositionValidation(env.client, input)
        assert.equal(second.ok, false)
        if (!second.ok) {
            assert.equal(second.failureCode, 'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT')
        }

        if (first.ok) {
            const preserved = await first.start.handle.result()
            assert.equal(preserved.status, 'valid')
        }
    })
})