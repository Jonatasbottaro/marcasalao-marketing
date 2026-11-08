/**
 * Relatorio estruturado do piloto TEMPORAL-01.
 *
 * O resultado e a unica saida publica de uma execucao: campos pequenos, ordem
 * estavel, codigo estavel presente em toda falha e nenhum valor de entrada
 * ecoado alem dos identificadores que passaram pelas mesmas regras do parse.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { PILOT_FAILURE_CODES } from '../../src/pilot-core/failures.js'
import { PILOT_OPERATION, PILOT_SCHEMA_VERSION, echoIdentities, type TemporalPilotInput } from '../../src/pilot-core/pilot-input.js'
import { buildPilotOutput } from '../../src/pilot-core/pilot-plan.js'
import { completedPilotResult, failedPilotResult, rejectedPilotResult } from '../../src/pilot-core/pilot-result.js'

function input(overrides: Partial<TemporalPilotInput> = {}): TemporalPilotInput {
    return {
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId: 'req-0001',
        projectId: 'marcasalao',
        operation: PILOT_OPERATION,
        payload: { label: 'piloto' },
        ...overrides,
    }
}

test('o resultado concluido traz as tres etapas, codigo nulo e saida presente', () => {
    const pilotInput = input()
    const result = completedPilotResult(pilotInput, buildPilotOutput(pilotInput))

    assert.equal(result.schemaVersion, 1)
    assert.equal(result.status, 'completed')
    assert.equal(result.failureCode, null)
    assert.equal(result.requestId, 'req-0001')
    assert.equal(result.projectId, 'marcasalao')
    assert.deepEqual(result.completedSteps, ['validate', 'prepare', 'finalize'])
    assert.ok(result.output)
    assert.equal(result.output.executionKey, 'req-0001::validate-pilot-request')
})

test('o resultado rejeitado nao tem saida e nao tem etapa concluida', () => {
    const result = rejectedPilotResult({ requestId: 'req-0001', projectId: 'marcasalao' }, PILOT_FAILURE_CODES.operationInvalid, [])

    assert.equal(result.status, 'rejected')
    assert.equal(result.failureCode, 'TEMPORAL_PILOT_OPERATION_INVALID')
    assert.equal(result.output, null)
    assert.deepEqual(result.completedSteps, [])
})

test('uma rejeicao posterior conserva as etapas ja concluidas', () => {
    const result = rejectedPilotResult({ requestId: 'req-0001', projectId: null }, PILOT_FAILURE_CODES.nonRetryable, ['validate'])

    assert.deepEqual(result.completedSteps, ['validate'])
})

test('o resultado falho conserva a ordem exata das etapas concluidas', () => {
    const result = failedPilotResult({ requestId: 'req-0001', projectId: 'marcasalao' }, PILOT_FAILURE_CODES.timeout, ['validate', 'prepare'])

    assert.equal(result.status, 'failed')
    assert.equal(result.failureCode, 'TEMPORAL_PILOT_TIMEOUT')
    assert.equal(result.output, null)
    assert.deepEqual(result.completedSteps, ['validate', 'prepare'])
})

test('todo resultado com falha tem codigo, sem excecao', () => {
    const rejected = rejectedPilotResult({ requestId: null, projectId: null }, PILOT_FAILURE_CODES.inputInvalid, [])
    const failed = failedPilotResult({ requestId: null, projectId: null }, PILOT_FAILURE_CODES.workflowFailed, [])

    assert.ok(rejected.failureCode)
    assert.ok(failed.failureCode)
    assert.equal(rejected.requestId, null)
})

test('os identificadores sao ecoados quando validos', () => {
    assert.deepEqual(echoIdentities({ requestId: 'req-0001', projectId: 'marcasalao', operation: 'x' }), {
        requestId: 'req-0001',
        projectId: 'marcasalao',
    })
})

test('os identificadores viram nulos quando ausentes, errados ou de tipo errado', () => {
    const cases: unknown[] = [undefined, null, 'req-0001', [], 7, {}, { requestId: 'REQ-0001' }, { projectId: 'marca salao' }, { requestId: 7 }]

    for (const value of cases) {
        assert.deepEqual(echoIdentities(value), { requestId: null, projectId: null })
    }
})

test('um identificador com aparencia de credencial nao e ecoado', () => {
    assert.deepEqual(echoIdentities({ requestId: 'sk-live-nunca-imprimir', projectId: 'marcasalao' }), {
        requestId: null,
        projectId: 'marcasalao',
    })
})

test('o mesmo par de argumentos produz exatamente o mesmo resultado duas vezes', () => {
    const pilotInput = input()
    const output = buildPilotOutput(pilotInput)

    assert.deepEqual(completedPilotResult(pilotInput, output), completedPilotResult(pilotInput, output))
})

test('o resultado sobrevive a uma rodada de JSON sem mudar', () => {
    const pilotInput = input()
    const result = completedPilotResult(pilotInput, buildPilotOutput(pilotInput))

    assert.deepEqual(JSON.parse(JSON.stringify(result)), result)
})

test('mudar o resultado devolvido nao muda o resultado da proxima chamada', () => {
    const pilotInput = input()
    const first = completedPilotResult(pilotInput, buildPilotOutput(pilotInput))
    first.completedSteps.push('finalize')

    const second = completedPilotResult(pilotInput, buildPilotOutput(pilotInput))
    assert.deepEqual(second.completedSteps, ['validate', 'prepare', 'finalize'])
})
