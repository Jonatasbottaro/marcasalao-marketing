/**
 * Activities do piloto TEMPORAL-01.
 *
 * As tres atividades sao puras: recebem valor, devolvem valor, nao leem relogio,
 * ambiente, disco, rede nem arquivos, nao escrevem no repositorio e nao produzem
 * efeito real de negocio. A recusa e sempre um ApplicationFailure nao retryable
 * com codigo estavel e mensagem sanitizada.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ApplicationFailure } from '@temporalio/common'

import { PILOT_FAILURE_CODES } from '../../src/pilot-core/failures.js'
import { PILOT_OPERATION, PILOT_SCHEMA_VERSION } from '../../src/pilot-core/pilot-input.js'
import { buildPilotOutput } from '../../src/pilot-core/pilot-plan.js'
import { finalizePilotExecution, preparePilotExecution, validatePilotRequest } from '../../src/activities/pilot-activities.js'

function validRaw(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId: 'req-0001',
        projectId: 'marcasalao',
        operation: PILOT_OPERATION,
        payload: { label: 'piloto', count: 2 },
        ...overrides,
    }
}

async function failureOf(run: () => Promise<unknown>): Promise<ApplicationFailure> {
    let caught: unknown
    try {
        await run()
        assert.fail('a atividade deveria ter recusado o valor recebido')
    } catch (error) {
        caught = error
    }
    assert.ok(caught instanceof ApplicationFailure, 'a recusa deveria ser um ApplicationFailure')
    return caught
}

test('validate devolve o contrato quando a entrada e valida', async () => {
    const input = await validatePilotRequest(validRaw())

    assert.equal(input.requestId, 'req-0001')
    assert.equal(input.operation, PILOT_OPERATION)
    assert.deepEqual(input.payload, { label: 'piloto', count: 2 })
})

test('validate recusa violacao de contrato como falha nao retryable com codigo estavel', async () => {
    const cases: Array<{ raw: Record<string, unknown>; code: string }> = [
        { raw: validRaw({ schemaVersion: 2 }), code: PILOT_FAILURE_CODES.schemaUnsupported },
        { raw: validRaw({ operation: 'gerar-campanha' }), code: PILOT_FAILURE_CODES.operationInvalid },
        { raw: validRaw({ requestId: '' }), code: PILOT_FAILURE_CODES.requestIdRequired },
        { raw: validRaw({ payload: { midia: 'png' } }), code: PILOT_FAILURE_CODES.payloadInvalid },
    ]

    for (const testCase of cases) {
        const failure = await failureOf(() => validatePilotRequest(testCase.raw))

        assert.equal(failure.type, testCase.code)
        assert.equal(failure.nonRetryable, true)
    }
})

test('a recusa nao repete o valor que chegou na entrada', async () => {
    const marca = 'nunca-imprimir-aqui'
    const failure = await failureOf(() => validatePilotRequest(validRaw({ requestId: `REQ ${marca}` })))

    assert.ok(!failure.message.includes(marca))
    assert.ok(!JSON.stringify({ message: failure.message, type: failure.type }).includes(marca))
})

test('prepare e idempotente: a mesma entrada produz saida identica duas vezes', async () => {
    const input = await validatePilotRequest(validRaw())

    assert.deepEqual(await preparePilotExecution(input), await preparePilotExecution(input))
})

test('prepare concorda com o plano puro do nucleo', async () => {
    const input = await validatePilotRequest(validRaw())

    assert.deepEqual(await preparePilotExecution(input), buildPilotOutput(input))
})

test('finalize e idempotente e devolve o resultado concluido', async () => {
    const input = await validatePilotRequest(validRaw())
    const output = await preparePilotExecution(input)
    const result = await finalizePilotExecution(input, output)

    assert.equal(result.status, 'completed')
    assert.equal(result.failureCode, null)
    assert.deepEqual(result.completedSteps, ['validate', 'prepare', 'finalize'])
    assert.deepEqual(await finalizePilotExecution(input, output), result)
})

test('as tres etapas aceitam e devolvem apenas valores serializaveis', async () => {
    const input = await validatePilotRequest(validRaw())
    const output = await preparePilotExecution(input)
    const result = await finalizePilotExecution(input, output)

    assert.deepEqual(JSON.parse(JSON.stringify(input)), input)
    assert.deepEqual(JSON.parse(JSON.stringify(output)), output)
    assert.deepEqual(JSON.parse(JSON.stringify(result)), result)
})

test('prepare revalida a entrada e recusa um valor adulterado', async () => {
    const tampered = { ...(await validatePilotRequest(validRaw())), requestId: 'REQ-ADULTERADO' }

    const failure = await failureOf(() => preparePilotExecution(tampered))
    assert.equal(failure.type, PILOT_FAILURE_CODES.inputInvalid)
    assert.equal(failure.nonRetryable, true)
})

test('finalize recusa uma saida adulterada em vez de montar um resultado inconsistente', async () => {
    const input = await validatePilotRequest(validRaw())
    const tampered = { ...(await preparePilotExecution(input)), executionKey: '' }

    const failure = await failureOf(() => finalizePilotExecution(input, tampered))
    assert.equal(failure.type, PILOT_FAILURE_CODES.nonRetryable)
    assert.equal(failure.nonRetryable, true)
    assert.ok(!failure.message.includes('executionKey'))
})
