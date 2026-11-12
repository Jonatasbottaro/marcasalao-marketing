/**
 * Testes de integracao da execucao de TEMPORAL-02 com cliente real da aplicacao
 * (startCompositionValidation / executeCompositionValidation) sobre
 * TestWorkflowEnvironment.createTimeSkipping e Worker efemero por teste.
 *
 * Cobre colisao com execucao aberta e concluida, requestId diferente, preflight
 * invalido com zero execucao, espera de resultado e shutdown do Worker.
 * Cada teste sobe o proprio servidor efemero: a Task Queue dedicada e exclusiva
 * por ambiente, sem compartilhamento entre testes.
 */
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { TestWorkflowEnvironment } from '@temporalio/testing'
import { Worker, bundleWorkflowCode, type WorkflowBundleWithSourceMap } from '@temporalio/worker'

import {
    validateCompositionActivity,
    type CompositionValidationActivityInput,
} from '../../src/activities/composition-validation-activity.js'
import {
    COMPOSITION_VALIDATION_TASK_QUEUE,
    executeCompositionValidation,
    startCompositionValidation,
} from '../../src/client/composition-validation-start.js'
import type {
    CompositionValidationWorkflowInput,
    JsonObject,
} from '../../src/composition-validation/composition-validation-input.js'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const workflowsPath = fileURLToPath(
    new URL('../../src/workflows/composition-validation-workflow.js', import.meta.url),
)
const repositoryRoot = path.resolve(testDir, '../../../../..')

const marcaSalaoProject = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, 'platform/examples/projects/marca-salao.project.json'), 'utf8'),
) as JsonObject

const marcaSalaoComposition = JSON.parse(
    fs.readFileSync(
        path.join(repositoryRoot, 'platform/examples/compositions/marca-salao-pilot.composition.json'),
        'utf8',
    ),
) as JsonObject

let cachedBundlePromise: Promise<WorkflowBundleWithSourceMap> | null = null

function getWorkflowBundle(): Promise<WorkflowBundleWithSourceMap> {
    if (cachedBundlePromise === null) {
        cachedBundlePromise = bundleWorkflowCode({ workflowsPath })
    }
    return cachedBundlePromise
}

function makeInput(requestId: string, composition: JsonObject = marcaSalaoComposition): CompositionValidationWorkflowInput {
    return { schemaVersion: 1, requestId, project: marcaSalaoProject, composition }
}

async function withClientWorker(
    activities: Record<string, unknown>,
    run: (env: TestWorkflowEnvironment, worker: Worker) => Promise<void>,
    beforeTeardown?: () => void,
): Promise<void> {
    const workflowBundle = await getWorkflowBundle()
    const env = await TestWorkflowEnvironment.createTimeSkipping()
    const worker = await Worker.create({
        connection: env.nativeConnection,
        taskQueue: COMPOSITION_VALIDATION_TASK_QUEUE,
        workflowBundle,
        activities,
    })
    const workerRun = worker.run()
    try {
        await run(env, worker)
    } finally {
        if (beforeTeardown) beforeTeardown()
        worker.shutdown()
        await workerRun
        await env.teardown()
    }
}

const realActivities = {
    validateCompositionActivity: (input: CompositionValidationActivityInput) => validateCompositionActivity(input),
}

test('colisao com execucao em andamento recusa o segundo start sem nova chamada de Activity', async () => {
    let attempts = 0
    const abandoned: Array<() => void> = []
    const hangingActivities = {
        validateCompositionActivity: async () => {
            attempts += 1
            return new Promise<never>((_resolve, reject) => {
                abandoned.push(() => reject(new Error('test cleanup')))
            })
        },
    }

    await withClientWorker(
        hangingActivities,
        async (env) => {
            const input = makeInput(`req-coll-run-${randomUUID()}`)
            const first = await startCompositionValidation(env.client, input)
            assert.equal(first.ok, true)

            // Espera a Activity realmente iniciar antes de medir a colisao.
            const deadline = Date.now() + 5000
            while (attempts === 0 && Date.now() < deadline) {
                await new Promise((resolve) => setTimeout(resolve, 50))
            }
            assert.equal(attempts, 1)

            const second = await startCompositionValidation(env.client, input)
            assert.equal(second.ok, false)
            if (!second.ok) {
                assert.equal(second.failureCode, 'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT')
                assert.equal(second.workflowId, first.ok ? first.workflowId : null)
            }
            assert.equal(attempts, 1)
        },
        () => {
            for (const rejectPending of abandoned) rejectPending()
        },
    )
})

test('colisao apos conclusao recusa reuso do Workflow ID sem segunda execucao', async () => {
    let attempts = 0
    const spyActivities = {
        validateCompositionActivity: async (input: CompositionValidationActivityInput) => {
            attempts += 1
            return validateCompositionActivity(input)
        },
    }

    await withClientWorker(spyActivities, async (env) => {
        const input = makeInput(`req-coll-done-${randomUUID()}`)
        const first = await executeCompositionValidation(env.client, input)
        assert.equal(first.ok, true)
        if (first.ok) assert.equal(first.result.status, 'valid')

        const second = await startCompositionValidation(env.client, input)
        assert.equal(second.ok, false)
        if (!second.ok) assert.equal(second.failureCode, 'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT')
        assert.equal(attempts, 1)
    })
})

test('requestId diferente gera execucao diferente com Workflow ID distinto', async () => {
    await withClientWorker(realActivities, async (env) => {
        const suffix = randomUUID()
        const first = await startCompositionValidation(env.client, makeInput(`req-a-${suffix}`))
        const second = await startCompositionValidation(env.client, makeInput(`req-b-${suffix}`))
        assert.equal(first.ok, true)
        assert.equal(second.ok, true)
        if (first.ok && second.ok) {
            assert.notEqual(first.workflowId, second.workflowId)
            assert.notEqual(first.runId, second.runId)
            assert.equal(first.workflowId, `composition-validation-req-a-${suffix}`)
            assert.equal(second.workflowId, `composition-validation-req-b-${suffix}`)
        }
    })
})

test('preflight invalido nao estabelece execucao alguma no servidor', async () => {
    let attempts = 0
    const spyActivities = {
        validateCompositionActivity: async (input: CompositionValidationActivityInput) => {
            attempts += 1
            return validateCompositionActivity(input)
        },
    }
    await withClientWorker(spyActivities, async (env) => {
        const requestId = `req-bad-${randomUUID()}`
        const bad = { ...makeInput(requestId), schemaVersion: 9 }
        const result = await startCompositionValidation(env.client, bad)
        assert.equal(result.ok, false)
        if (!result.ok) assert.equal(result.failureCode, 'TEMPORAL_COMPOSITION_INPUT_INVALID')

        const orphan = env.client.workflow.getHandle(`composition-validation-${requestId}`)
        await assert.rejects(orphan.describe())
        assert.equal(attempts, 0)
    })
})

test('executeCompositionValidation aguarda o resultado real valid e invalid', async () => {
    await withClientWorker(realActivities, async (env) => {
        const suffix = randomUUID()
        const valid = await executeCompositionValidation(env.client, makeInput(`req-exec-valid-${suffix}`))
        assert.equal(valid.ok, true)
        if (valid.ok) {
            assert.equal(valid.result.status, 'valid')
            assert.deepEqual(valid.result.completedSteps, ['validate-composition'])
        }

        const invalid = await executeCompositionValidation(
            env.client,
            makeInput(`req-exec-invalid-${suffix}`, { ...marcaSalaoComposition, projectId: 'outro-projeto' }),
        )
        assert.equal(invalid.ok, true)
        if (invalid.ok) {
            assert.equal(invalid.result.status, 'invalid')
            assert.equal(invalid.result.failureCode, null)
            assert.ok(invalid.result.validation && invalid.result.validation.errors.length > 0)
        }
    })
})

test('shutdown do Worker encerra o run sem handle residual', async () => {
    const workflowBundle = await getWorkflowBundle()
    const env = await TestWorkflowEnvironment.createTimeSkipping()
    const worker = await Worker.create({
        connection: env.nativeConnection,
        taskQueue: COMPOSITION_VALIDATION_TASK_QUEUE,
        workflowBundle,
        activities: realActivities,
    })
    const workerRun = worker.run()
    try {
        const execution = await executeCompositionValidation(env.client, makeInput(`req-shutdown-${randomUUID()}`))
        assert.equal(execution.ok, true)
        worker.shutdown()
        await workerRun
    } finally {
        await env.teardown()
    }
})