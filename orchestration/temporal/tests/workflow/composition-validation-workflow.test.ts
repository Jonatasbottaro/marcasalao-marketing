/**
 * Testes de integracao do Workflow validateCompositionWorkflow com
 * TestWorkflowEnvironment e Worker efemero por teste (TEMPORAL-02, fatia Workflow).
 *
 * Nao altera Worker nem cliente de producao e nao testa replay formal nem
 * colisao de Workflow ID (reservados a etapas posteriores).
 */
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { ApplicationFailure } from '@temporalio/common'
import { TestWorkflowEnvironment } from '@temporalio/testing'
import { Worker, bundleWorkflowCode, type WorkflowBundleWithSourceMap } from '@temporalio/worker'

import {
    validateCompositionActivity,
    type CompositionValidationActivityInput,
} from '../../src/activities/composition-validation-activity.js'
import type {
    CompositionValidationWorkflowInput,
    JsonObject,
} from '../../src/composition-validation/composition-validation-input.js'
import {
    COMPOSITION_WORKFLOW_FAILURE_CODES,
    type CompositionValidationWorkflowResult,
} from '../../src/workflows/composition-validation-result.js'

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

function makeWorkflowInput(
    requestId: string,
    overrides: Partial<CompositionValidationWorkflowInput> = {},
): CompositionValidationWorkflowInput {
    return {
        schemaVersion: 1,
        requestId,
        project: marcaSalaoProject,
        composition: marcaSalaoComposition,
        ...overrides,
    }
}

interface EphemeralContext {
    env: TestWorkflowEnvironment
    taskQueue: string
    runWorkflow: (input: CompositionValidationWorkflowInput) => Promise<CompositionValidationWorkflowResult>
}

async function withEphemeralWorker(
    activities: Record<string, unknown>,
    run: (ctx: EphemeralContext) => Promise<void>,
    beforeTeardown?: () => void,
): Promise<void> {
    const workflowBundle = await getWorkflowBundle()
    const env = await TestWorkflowEnvironment.createTimeSkipping()
    const taskQueue = `test-comp-val-${randomUUID()}`
    const worker = await Worker.create({
        connection: env.nativeConnection,
        taskQueue,
        workflowBundle,
        activities,
    })
    const workerRun = worker.run()

    try {
        const runWorkflow = async (
            input: CompositionValidationWorkflowInput,
        ): Promise<CompositionValidationWorkflowResult> => {
            const handle = await env.client.workflow.start('validateCompositionWorkflow', {
                args: [input],
                taskQueue,
                workflowId: `test-wf-${randomUUID()}`,
            })
            return (await handle.result()) as CompositionValidationWorkflowResult
        }

        await run({ env, taskQueue, runWorkflow })
    } finally {
        if (beforeTeardown) {
            beforeTeardown()
        }
        worker.shutdown()
        await workerRun
        await env.teardown()
    }
}

test('caminho feliz: validacao com Activity real retorna valid e completedSteps preenchido', async () => {
    let attempts = 0
    const spyActivities = {
        validateCompositionActivity: async (input: CompositionValidationActivityInput) => {
            attempts += 1
            return validateCompositionActivity(input)
        },
    }

    await withEphemeralWorker(spyActivities, async ({ runWorkflow }) => {
        const result = await runWorkflow(makeWorkflowInput('req-valid-e2e'))

        assert.equal(attempts, 1)
        assert.equal(result.schemaVersion, 1)
        assert.equal(result.requestId, 'req-valid-e2e')
        assert.equal(result.status, 'valid')
        assert.equal(result.failureCode, null)
        assert.deepEqual(result.completedSteps, ['validate-composition'])
        assert.ok(result.validation)
        assert.equal(result.validation.valid, true)
        assert.equal(result.projectId, result.validation.projectId)
        assert.equal(result.compositionId, result.validation.compositionId)
    })
})

test('composicao semanticamente invalida retorna status invalid em uma tentativa sem retry', async () => {
    let attempts = 0
    const spyActivities = {
        validateCompositionActivity: async (input: CompositionValidationActivityInput) => {
            attempts += 1
            return validateCompositionActivity(input)
        },
    }

    const mismatchedComposition: JsonObject = {
        ...marcaSalaoComposition,
        projectId: 'outro-projeto-incompativel',
    }

    await withEphemeralWorker(spyActivities, async ({ runWorkflow }) => {
        const result = await runWorkflow(
            makeWorkflowInput('req-invalid-e2e', { composition: mismatchedComposition }),
        )

        assert.equal(attempts, 1)
        assert.equal(result.schemaVersion, 1)
        assert.equal(result.requestId, 'req-invalid-e2e')
        assert.equal(result.status, 'invalid')
        assert.equal(result.failureCode, null)
        assert.deepEqual(result.completedSteps, ['validate-composition'])
        assert.ok(result.validation)
        assert.equal(result.validation.valid, false)
        assert.ok(result.validation.errors.length > 0)
        assert.equal(result.projectId, result.validation.projectId)
        assert.equal(result.compositionId, result.validation.compositionId)
    })
})

test('falha nao retryable da Activity real encerra na primeira tentativa com failed sanitizado', async () => {
    let attempts = 0
    const spyActivities = {
        validateCompositionActivity: async () => {
            attempts += 1
            // Dispara o tratamento de erro inesperado da Activity real sem altera-la
            return validateCompositionActivity(null as unknown as CompositionValidationActivityInput)
        },
    }

    await withEphemeralWorker(spyActivities, async ({ runWorkflow }) => {
        const result = await runWorkflow(makeWorkflowInput('req-non-retryable'))

        assert.equal(attempts, 1)
        assert.deepEqual(result, {
            schemaVersion: 1,
            requestId: 'req-non-retryable',
            projectId: null,
            compositionId: null,
            status: 'failed',
            validation: null,
            completedSteps: [],
            failureCode: COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
        })
    })
})

test('falha transitoria simulada em Activity de teste recupera na segunda tentativa', async () => {
    let attempts = 0
    const transientThenSuccessActivities = {
        validateCompositionActivity: async (input: CompositionValidationActivityInput) => {
            attempts += 1
            if (attempts === 1) {
                throw ApplicationFailure.create({
                    type: COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
                    message: 'simulated transient glitch on attempt 1',
                })
            }
            return validateCompositionActivity(input)
        },
    }

    await withEphemeralWorker(transientThenSuccessActivities, async ({ runWorkflow }) => {
        const result = await runWorkflow(makeWorkflowInput('req-transient-recover'))

        assert.equal(attempts, 2)
        assert.equal(result.status, 'valid')
        assert.equal(result.failureCode, null)
        assert.deepEqual(result.completedSteps, ['validate-composition'])
        assert.ok(result.validation)
        assert.equal(result.validation.valid, true)
    })
})

test('falha transitoria persistente respeita maximumAttempts=2 e devolve failed', async () => {
    let attempts = 0
    const alwaysTransientActivities = {
        validateCompositionActivity: async () => {
            attempts += 1
            throw ApplicationFailure.create({
                type: COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
                message: 'persistent transient glitch',
            })
        },
    }

    await withEphemeralWorker(alwaysTransientActivities, async ({ runWorkflow }) => {
        const result = await runWorkflow(makeWorkflowInput('req-transient-exhausted'))

        assert.equal(attempts, 2)
        assert.deepEqual(result, {
            schemaVersion: 1,
            requestId: 'req-transient-exhausted',
            projectId: null,
            compositionId: null,
            status: 'failed',
            validation: null,
            completedSteps: [],
            failureCode: COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
        })
    })
})

test('timeout de Activity (5s) esgota duas tentativas via time-skipping e devolve TEMPORAL_COMPOSITION_TIMEOUT', async () => {
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

    await withEphemeralWorker(
        hangingActivities,
        async ({ env, taskQueue }) => {
            const handle = await env.client.workflow.start('validateCompositionWorkflow', {
                args: [makeWorkflowInput('req-timeout-2-attempts')],
                taskQueue,
                workflowId: `test-wf-timeout-${randomUUID()}`,
            })

            // Avanca o relogio virtual alem das duas tentativas de 5s + backoff de 1s
            for (let i = 0; i < 3; i += 1) {
                await env.sleep('6 seconds')
            }

            const result = (await handle.result()) as CompositionValidationWorkflowResult

            assert.equal(attempts, 2)
            assert.deepEqual(result, {
                schemaVersion: 1,
                requestId: 'req-timeout-2-attempts',
                projectId: null,
                compositionId: null,
                status: 'failed',
                validation: null,
                completedSteps: [],
                failureCode: COMPOSITION_WORKFLOW_FAILURE_CODES.timeout,
            })
        },
        () => {
            for (const rejectPending of abandoned) {
                rejectPending()
            }
        },
    )
})

test('falha tecnica desconhecida e sanitizada para TEMPORAL_COMPOSITION_ACTIVITY_FAILED sem vazar detalhes', async () => {
    let attempts = 0
    const unknownErrorActivities = {
        validateCompositionActivity: async () => {
            attempts += 1
            throw new Error('unexpected internal failure C:\\Users\\admin\\secret.key sk-live-never-leak')
        },
    }

    await withEphemeralWorker(unknownErrorActivities, async ({ runWorkflow }) => {
        const result = await runWorkflow(makeWorkflowInput('req-unknown-error'))

        assert.equal(attempts, 2)
        assert.deepEqual(result, {
            schemaVersion: 1,
            requestId: 'req-unknown-error',
            projectId: null,
            compositionId: null,
            status: 'failed',
            validation: null,
            completedSteps: [],
            failureCode: COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
        })

        const serialized = JSON.stringify(result)
        assert.equal(serialized.includes('unexpected'), false)
        assert.equal(serialized.includes('secret.key'), false)
        assert.equal(serialized.includes('sk-live-never-leak'), false)
        assert.equal(serialized.includes('Users'), false)
    })
})