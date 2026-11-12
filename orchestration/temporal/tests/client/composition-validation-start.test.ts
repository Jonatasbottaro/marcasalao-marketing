/**
 * Testes unitarios do cliente de validacao de Composition (TEMPORAL-02).
 *
 * Cliente falso: nenhuma conexao, nenhum servidor. Cobre determinismo do
 * Workflow ID, opcoes de start, politicas, preflight obrigatorio, colisao,
 * erro de conexao e erro desconhecido sanitizado.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { WorkflowExecutionAlreadyStartedError } from '@temporalio/common'
import { WorkflowIdConflictPolicy, WorkflowIdReusePolicy, type Client } from '@temporalio/client'

import {
    COMPOSITION_VALIDATION_START_FAILURE_CODES,
    COMPOSITION_VALIDATION_TASK_QUEUE,
    COMPOSITION_VALIDATION_WORKFLOW_TYPE,
    classifyCompositionValidationStartFailure,
    compositionValidationStartOptions,
    compositionValidationWorkflowId,
    executeCompositionValidation,
    startCompositionValidation,
} from '../../src/client/composition-validation-start.js'
import type { CompositionValidationWorkflowInput } from '../../src/composition-validation/composition-validation-input.js'
import type { CompositionValidationWorkflowResult } from '../../src/workflows/composition-validation-result.js'

const project = {
    schemaVersion: 1,
    projectId: 'fixture-project',
    name: 'Projeto Fixture',
    defaultLocale: 'pt-BR',
    supportedFormatProfiles: ['vertical-short-v1'],
}

const composition = {
    schemaVersion: 1,
    compositionId: 'fixture-composition',
    projectId: 'fixture-project',
    title: 'Composicao Fixture',
    scenes: [],
}

function makeInput(requestId = 'req-unit-0001'): CompositionValidationWorkflowInput {
    return { schemaVersion: 1, requestId, project, composition } as unknown as CompositionValidationWorkflowInput
}

interface FakeStartCall {
    workflowType: string
    options: Record<string, unknown>
}

function fakeClient(behavior: 'ok' | 'conflict' | 'unknown' | 'connection' = 'ok') {
    const calls: FakeStartCall[] = []
    const handle = {
        firstExecutionRunId: '00000000-0000-0000-0000-000000000001',
        result: async (): Promise<CompositionValidationWorkflowResult> => ({
            schemaVersion: 1,
            requestId: 'req-unit-0001',
            projectId: 'fixture-project',
            compositionId: 'fixture-composition',
            status: 'valid',
            validation: null,
            completedSteps: ['validate-composition'],
            failureCode: null,
        }),
    }
    const client = {
        workflow: {
            start: async (workflowType: string, options: Record<string, unknown>) => {
                calls.push({ workflowType, options })
                if (behavior === 'conflict') {
                    throw new WorkflowExecutionAlreadyStartedError(
                        'already started',
                        String(options.workflowId),
                        workflowType,
                    )
                }
                if (behavior === 'unknown') {
                    throw new Error('transport detail C:\\Users\\admin\\secret.key must not leak')
                }
                if (behavior === 'connection') {
                    throw Object.assign(new Error('connect ECONNREFUSED 127.0.0.1:7233'), { code: 'ECONNREFUSED' })
                }
                return handle
            },
        },
    } as unknown as Client
    return { client, calls, handle }
}

test('Workflow ID e deterministico, sem data, aleatoriedade ou hash', () => {
    const first = compositionValidationWorkflowId('req-0001')
    const second = compositionValidationWorkflowId('req-0001')
    assert.equal(first, 'composition-validation-req-0001')
    assert.equal(first, second)
    assert.match(first, /^composition-validation-[a-z0-9][a-z0-9._-]{0,63}$/)
    assert.equal(compositionValidationWorkflowId('req-0002'), 'composition-validation-req-0002')
})

test('opcoes de start carregam Task Queue dedicada, Workflow Type, politicas e a mesma referencia validada', () => {
    const input = makeInput()
    const options = compositionValidationStartOptions(input)
    assert.equal(options.taskQueue, COMPOSITION_VALIDATION_TASK_QUEUE)
    assert.equal(options.taskQueue, 'composition-validation-v1')
    assert.equal(options.workflowId, 'composition-validation-req-unit-0001')
    assert.equal(options.workflowIdReusePolicy, WorkflowIdReusePolicy.REJECT_DUPLICATE)
    assert.equal(options.workflowIdConflictPolicy, WorkflowIdConflictPolicy.FAIL)
    assert.deepEqual(options.args, [input])
    assert.equal(options.args[0], input)
    assert.equal('namespace' in options, false)
})

test('preflight invalido nao chama start e devolve codigo da via A sem requestId', async () => {
    const { client, calls } = fakeClient()
    const result = await startCompositionValidation(client, { ...makeInput(), schemaVersion: 2 })
    assert.equal(calls.length, 0)
    assert.deepEqual(result, {
        ok: false,
        requestId: null,
        workflowId: null,
        failureCode: 'TEMPORAL_COMPOSITION_INPUT_INVALID',
    })
})

test('preflight sensivel nao chama start', async () => {
    const { client, calls } = fakeClient()
    const result = await startCompositionValidation(client, {
        ...makeInput(),
        project: { ...project, password: 'hunter2' },
    })
    assert.equal(calls.length, 0)
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.failureCode, 'TEMPORAL_COMPOSITION_SENSITIVE_INPUT')
})

test('preflight grande demais nao chama start', async () => {
    const { client, calls } = fakeClient()
    const result = await startCompositionValidation(client, {
        ...makeInput(),
        project: { ...project, name: 'x'.repeat(70_000) },
    })
    assert.equal(calls.length, 0)
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.failureCode, 'TEMPORAL_COMPOSITION_INPUT_TOO_LARGE')
})

test('input valido chama start exatamente uma vez com o Workflow Type e as opcoes corretas', async () => {
    const { client, calls } = fakeClient()
    const input = makeInput()
    const result = await startCompositionValidation(client, input)
    assert.equal(calls.length, 1)
    assert.equal(calls[0]?.workflowType, COMPOSITION_VALIDATION_WORKFLOW_TYPE)
    assert.equal(calls[0]?.options.workflowId, 'composition-validation-req-unit-0001')
    assert.equal((calls[0]?.options.args as unknown[] | undefined)?.[0], input)
    assert.equal(result.ok, true)
    if (result.ok) {
        assert.equal(result.requestId, 'req-unit-0001')
        assert.equal(result.workflowId, 'composition-validation-req-unit-0001')
        assert.equal(result.runId, '00000000-0000-0000-0000-000000000001')
        assert.ok(result.handle)
    }
})

test('colisao de Workflow ID devolve codigo proprio sem nova execucao e sem resultado de Workflow', async () => {
    const { client, calls } = fakeClient('conflict')
    const result = await startCompositionValidation(client, makeInput())
    assert.equal(calls.length, 1)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, COMPOSITION_VALIDATION_START_FAILURE_CODES.workflowIdConflict)
        assert.equal(result.failureCode, 'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT')
        assert.equal(result.requestId, 'req-unit-0001')
        assert.equal(result.workflowId, 'composition-validation-req-unit-0001')
    }
    assert.equal('result' in result, false)
})

test('erro de conexao e classificado sem vazar mensagem de transporte', async () => {
    const { client } = fakeClient('connection')
    const result = await startCompositionValidation(client, makeInput())
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, COMPOSITION_VALIDATION_START_FAILURE_CODES.connectionFailed)
    }
    assert.equal(JSON.stringify(result).includes('ECONNREFUSED'), false)
    assert.equal(classifyCompositionValidationStartFailure(Object.assign(new Error('x'), { code: 14 })), 'TEMPORAL_COMPOSITION_CONNECTION_FAILED')
})

test('erro desconhecido do cliente devolve codigo sanitizado fixo', async () => {
    const { client } = fakeClient('unknown')
    const result = await startCompositionValidation(client, makeInput())
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, COMPOSITION_VALIDATION_START_FAILURE_CODES.startFailed)
    }
    const serialized = JSON.stringify(result)
    assert.equal(serialized.includes('secret.key'), false)
    assert.equal(serialized.includes('transport detail'), false)
    assert.equal(serialized.includes('Users'), false)
})

test('executeCompositionValidation aguarda o resultado e preserva valid sem remapear', async () => {
    const { client } = fakeClient()
    const execution = await executeCompositionValidation(client, makeInput())
    assert.equal(execution.ok, true)
    if (execution.ok) {
        assert.equal(execution.result.status, 'valid')
        assert.deepEqual(execution.result.completedSteps, ['validate-composition'])
        assert.equal(execution.start.workflowId, 'composition-validation-req-unit-0001')
    }
})

test('executeCompositionValidation propaga colisao sem aguardar resultado', async () => {
    const { client } = fakeClient('conflict')
    const execution = await executeCompositionValidation(client, makeInput())
    assert.equal(execution.ok, false)
    if (!execution.ok) {
        assert.equal(execution.start.failureCode, 'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT')
    }
})