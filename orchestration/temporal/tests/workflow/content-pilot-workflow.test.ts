/**
 * Integracao do Workflow do piloto TEMPORAL-01 com um servidor local efemero.
 *
 * Usa o Test Server de pular-tempo do proprio SDK: retry e timeout sao
 * verificados sem espera real, sem Docker e sem servidor remoto. Cada teste
 * cria e derruba o seu ambiente. A contagem de chamadas vem de wrappers de
 * teste sobre as atividades reais, entao "quantas tentativas houve" e evidencia
 * medida, nao presuncao.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { ApplicationFailure } from '@temporalio/common'
import { TestWorkflowEnvironment } from '@temporalio/testing'
import { Worker } from '@temporalio/worker'

import * as pilotActivities from '../../src/activities/pilot-activities.js'
import { PILOT_FAILURE_CODES } from '../../src/pilot-core/failures.js'
import { PILOT_OPERATION, PILOT_SCHEMA_VERSION, type TemporalPilotInput } from '../../src/pilot-core/pilot-input.js'
import type { TemporalPilotResult } from '../../src/pilot-core/pilot-result.js'
import { PILOT_TASK_QUEUE } from '../../src/workflows/content-pilot-workflow.js'

const workflowsPath = fileURLToPath(new URL('../../src/workflows/content-pilot-workflow.js', import.meta.url))

interface PilotRun {
    env: TestWorkflowEnvironment
    start: (raw: unknown, requestId: string) => Promise<TemporalPilotResult>
}

async function withPilotWorker(activities: Record<string, unknown>, run: (ctx: PilotRun) => Promise<void>): Promise<void> {
    const env = await TestWorkflowEnvironment.createTimeSkipping()
    try {
        const worker = await Worker.create({ connection: env.nativeConnection, taskQueue: PILOT_TASK_QUEUE, workflowsPath, activities })
        const start = async (raw: unknown, requestId: string) => {
            const handle = await env.client.workflow.start('contentPilotWorkflow', {
                args: [raw],
                taskQueue: PILOT_TASK_QUEUE,
                workflowId: `temporal-pilot-${requestId}`,
            })
            return await handle.result()
        }
        await worker.runUntil(() => run({ env, start }))
    } finally {
        await env.teardown()
    }
}

function validRaw(requestId: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return { schemaVersion: PILOT_SCHEMA_VERSION, requestId, projectId: 'marcasalao', operation: PILOT_OPERATION, payload: { label: 'piloto' }, ...overrides }
}

function realActivities() {
    return { ...pilotActivities }
}

function countingActivities(counts: { validate: number; prepare: number }) {
    return {
        ...pilotActivities,
        validatePilotRequest: async (raw: unknown) => {
            counts.validate += 1
            return pilotActivities.validatePilotRequest(raw)
        },
        preparePilotExecution: async (input: TemporalPilotInput) => {
            counts.prepare += 1
            return pilotActivities.preparePilotExecution(input)
        },
    }
}

function failingPrepare(counts: { prepare: number }, failure: () => Error, failures: number) {
    return {
        ...pilotActivities,
        preparePilotExecution: async (input: TemporalPilotInput) => {
            counts.prepare += 1
            if (counts.prepare <= failures) throw failure()
            return pilotActivities.preparePilotExecution(input)
        },
    }
}

test('o caminho feliz conclui as tres etapas e devolve a saida do plano', async () => {
    await withPilotWorker(realActivities(), async ({ start }) => {
        const result = await start(validRaw('req-feliz'), 'req-feliz')

        assert.equal(result.status, 'completed')
        assert.equal(result.failureCode, null)
        assert.equal(result.requestId, 'req-feliz')
        assert.deepEqual(result.completedSteps, ['validate', 'prepare', 'finalize'])
        assert.ok(result.output)
        assert.equal(result.output.executionKey, 'req-feliz::validate-pilot-request')
        assert.equal(result.output.workflowId, 'temporal-pilot-req-feliz')
    })
})

test('executar a mesma entrada duas vezes produz relatorios identicos', async () => {
    await withPilotWorker(realActivities(), async ({ start }) => {
        const first = await start(validRaw('req-igual'), 'req-igual')
        const second = await start(validRaw('req-igual'), 'req-igual')

        assert.equal(first.status, 'completed')
        assert.deepEqual(second, first)
    })
})

test('violacao de contrato e rejeitada na primeira tentativa, sem retry', async () => {
    const counts = { validate: 0, prepare: 0 }

    await withPilotWorker(countingActivities(counts), async ({ start }) => {
        const result = await start(validRaw('req-ruim', { schemaVersion: 2 }), 'req-ruim')

        assert.equal(result.status, 'rejected')
        assert.equal(result.failureCode, PILOT_FAILURE_CODES.schemaUnsupported)
        assert.equal(result.requestId, 'req-ruim')
        assert.deepEqual(result.completedSteps, [])
        assert.equal(result.output, null)
    })

    assert.equal(counts.validate, 1)
    assert.equal(counts.prepare, 0)
})

test('falha transienta e tentada ate o limite e depois conclui', async () => {
    const counts = { validate: 0, prepare: 0 }
    const transient = () => ApplicationFailure.create({ type: PILOT_FAILURE_CODES.transientFailure, message: 'falha transienta simulada' })

    await withPilotWorker(failingPrepare(counts, transient, 2), async ({ start }) => {
        const result = await start(validRaw('req-transienta'), 'req-transienta')

        assert.equal(result.status, 'completed')
        assert.deepEqual(result.completedSteps, ['validate', 'prepare', 'finalize'])
    })

    assert.equal(counts.prepare, 3)
})

test('falha transienta que nao cede devolve failed com o codigo estavel e para em tres tentativas', async () => {
    const counts = { validate: 0, prepare: 0 }
    const transient = () => ApplicationFailure.create({ type: PILOT_FAILURE_CODES.transientFailure, message: 'falha transienta simulada' })

    await withPilotWorker(failingPrepare(counts, transient, 99), async ({ start }) => {
        const result = await start(validRaw('req-esgotada'), 'req-esgotada')

        assert.equal(result.status, 'failed')
        assert.equal(result.failureCode, PILOT_FAILURE_CODES.transientFailure)
        assert.deepEqual(result.completedSteps, ['validate'])
        assert.equal(result.output, null)
    })

    assert.equal(counts.prepare, 3)
})

test('recusa nao retryable da etapa de preparacao nao consome tentativas', async () => {
    const counts = { validate: 0, prepare: 0 }
    const refusal = () => ApplicationFailure.create({ type: PILOT_FAILURE_CODES.nonRetryable, message: 'regra do piloto recusou a execucao', nonRetryable: true })

    await withPilotWorker(failingPrepare(counts, refusal, 99), async ({ start }) => {
        const result = await start(validRaw('req-recusada'), 'req-recusada')

        assert.equal(result.status, 'rejected')
        assert.equal(result.failureCode, PILOT_FAILURE_CODES.nonRetryable)
        assert.deepEqual(result.completedSteps, ['validate'])
    })

    assert.equal(counts.prepare, 1)
})

test('erro de vocabulario externo nao vira codigo inventado', async () => {
    const counts = { validate: 0, prepare: 0 }
    const external = () => ApplicationFailure.create({ type: 'Falha_De_Fornecedor_Externo', message: 'detalhe que nao pertence ao piloto' })

    await withPilotWorker(failingPrepare(counts, external, 99), async ({ start }) => {
        const result = await start(validRaw('req-externa'), 'req-externa')

        assert.equal(result.status, 'failed')
        assert.equal(result.failureCode, PILOT_FAILURE_CODES.workflowFailed)
    })

    assert.equal(counts.prepare, 3)
})

test('o relatorio de uma execucao rejeitada nao carrega o valor que violou o contrato', async () => {
    const marca = 'nunca-imprimir-aqui'

    await withPilotWorker(realActivities(), async ({ start }) => {
        const result = await start(validRaw('req-vazamento', { payload: { label: `sk-live-${marca}` } }), 'req-vazamento')

        assert.equal(result.status, 'rejected')
        assert.equal(result.failureCode, PILOT_FAILURE_CODES.payloadInvalid)
        assert.ok(!JSON.stringify(result).includes(marca), 'o relatorio ecou o valor recusado')
        assert.ok(!JSON.stringify(result).includes('sk-live'), 'o relatorio ecou uma aparencia de credencial')
    })
})

test('timeout de atividade e classificado como timeout depois de esgotar as tentativas', async () => {
    const env = await TestWorkflowEnvironment.createTimeSkipping()
    const counts = { prepare: 0 }
    const abandonadas: Array<() => void> = []
    // Cada tentativa fica pendurada de proposito: o servidor da o timeout, o
    // Workflow classifica e so depois o teste libera as pendencias para o Worker
    // conseguir encerrar. As tres liberam, senao o shutdown espera para sempre.
    const blockedPrepare = () => {
        counts.prepare += 1
        return new Promise<never>((_resolve, reject) => {
            abandonadas.push(() => reject(new Error('tentativa abandonada pelo teste')))
        })
    }
    const worker = await Worker.create({
        connection: env.nativeConnection,
        taskQueue: PILOT_TASK_QUEUE,
        workflowsPath,
        activities: { ...pilotActivities, preparePilotExecution: blockedPrepare },
    })
    const workerRun = worker.run()

    try {
        const handle = await env.client.workflow.start('contentPilotWorkflow', {
            args: [validRaw('req-timeout')],
            taskQueue: PILOT_TASK_QUEUE,
            workflowId: 'temporal-pilot-req-timeout',
        })
        for (let tentativa = 0; tentativa < 4; tentativa += 1) {
            await env.sleep('6 seconds')
        }
        const result = await handle.result()

        assert.equal(result.status, 'failed')
        assert.equal(result.failureCode, PILOT_FAILURE_CODES.timeout)
        assert.deepEqual(result.completedSteps, ['validate'])
        assert.equal(counts.prepare, 3)
    } finally {
        for (const abandonar of abandonadas) {
            abandonar()
        }
        await worker.shutdown()
        await workerRun
        await env.teardown()
    }
})

test('a historia gravada na execucao reproduz sem violacao de determinismo', async () => {
    await withPilotWorker(realActivities(), async ({ env, start }) => {
        const handle = await env.client.workflow.start('contentPilotWorkflow', {
            args: [validRaw('req-replay')],
            taskQueue: PILOT_TASK_QUEUE,
            workflowId: 'temporal-pilot-req-replay',
        })
        const result = await handle.result()
        assert.equal(result.status, 'completed')

        const history = await handle.fetchHistory()
        assert.ok(history)
        await Worker.runReplayHistory({ workflowsPath }, history, 'temporal-pilot-req-replay')
    })
})
