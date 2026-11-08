/**
 * Derivacao de plano e chave de idempotencia do piloto TEMPORAL-01.
 *
 * A idempotencia aqui e estrutural: cada valor sai apenas da entrada, sem
 * relogio, sem aleatoriedade, sem ambiente e sem disco. Rodar duas vezes a
 * mesma entrada tem de dar a mesma saida, byte por byte.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { PILOT_OPERATION, PILOT_SCHEMA_VERSION, type TemporalPilotInput } from '../../src/pilot-core/pilot-input.js'
import { PILOT_STEPS, buildPilotOutput, isPilotOutput, pilotExecutionKey, pilotWorkflowId } from '../../src/pilot-core/pilot-plan.js'

function input(overrides: Partial<TemporalPilotInput> = {}): TemporalPilotInput {
    return {
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId: 'req-0001',
        projectId: 'marcasalao',
        operation: PILOT_OPERATION,
        payload: {},
        ...overrides,
    }
}

test('a chave de execucao combina requestId e operation', () => {
    assert.equal(pilotExecutionKey(input()), 'req-0001::validate-pilot-request')
})

test('mudar o requestId muda a chave, mudar o payload nao', () => {
    const base = pilotExecutionKey(input({ payload: { label: 'a' } }))
    assert.equal(pilotExecutionKey(input({ payload: { label: 'b', count: 3 } })), base)
    assert.notEqual(pilotExecutionKey(input({ requestId: 'req-0002' })), base)
})

test('o workflowId deriva do requestId e nao do relogio', () => {
    assert.equal(pilotWorkflowId(input()), 'temporal-pilot-req-0001')
    assert.equal(pilotWorkflowId(input({ requestId: 'req-0002' })), 'temporal-pilot-req-0002')
})

test('as tres etapas canonicas do piloto tem ordem estavel', () => {
    assert.deepEqual(PILOT_STEPS, ['validate', 'prepare', 'finalize'])
})

test('a saida do plano traz os tres passos e os padroes do payload', () => {
    const output = buildPilotOutput(input())

    assert.equal(output.executionKey, 'req-0001::validate-pilot-request')
    assert.equal(output.workflowId, 'temporal-pilot-req-0001')
    assert.deepEqual(output.plannedSteps, ['validate', 'prepare', 'finalize'])
    assert.equal(output.label, '')
    assert.equal(output.count, 0)
    assert.equal(output.flag, false)
})

test('a saida do plano preserva os valores informados no payload', () => {
    const output = buildPilotOutput(input({ payload: { label: 'piloto', count: 7, flag: true } }))

    assert.equal(output.label, 'piloto')
    assert.equal(output.count, 7)
    assert.equal(output.flag, true)
})

test('a mesma entrada produz exatamente a mesma saida duas vezes', () => {
    assert.deepEqual(buildPilotOutput(input({ payload: { label: 'piloto' } })), buildPilotOutput(input({ payload: { label: 'piloto' } })))
})

test('a saida do plano sobrevive a uma rodada de JSON sem mudar', () => {
    const output = buildPilotOutput(input({ payload: { label: 'piloto', count: 2, flag: true } }))

    assert.deepEqual(JSON.parse(JSON.stringify(output)), output)
})

test('o plano devolvido nao e uma lista compartilhada entre chamadas', () => {
    const first = buildPilotOutput(input())
    const second = buildPilotOutput(input())

    assert.notEqual(first.plannedSteps, second.plannedSteps)
    first.plannedSteps.length = 0
    assert.deepEqual(second.plannedSteps, ['validate', 'prepare', 'finalize'])
})

test('uma saida real do plano passa pelo proprio contrato', () => {
    assert.equal(isPilotOutput(buildPilotOutput(input())), true)
})

test('valores que nao sao uma saida do plano sao recusados', () => {
    const cases: unknown[] = [
        undefined,
        null,
        'executionKey',
        7,
        [],
        {},
        { ...buildPilotOutput(input()), extra: 'sim' },
        { ...buildPilotOutput(input()), executionKey: undefined },
        { ...buildPilotOutput(input()), executionKey: 7 },
        { ...buildPilotOutput(input()), count: '2' },
        { ...buildPilotOutput(input()), flag: 'false' },
        { ...buildPilotOutput(input()), plannedSteps: [] },
        { ...buildPilotOutput(input()), plannedSteps: ['validate', 'prepare', 'finalize', 'extra'] },
        { ...buildPilotOutput(input()), plannedSteps: ['finalize', 'prepare', 'validate'] },
        { ...buildPilotOutput(input()), plannedSteps: 'validate' },
    ]

    for (const value of cases) {
        assert.equal(isPilotOutput(value), false)
    }
})

test('a checagem do contrato de saida nao aceita entrada invalida', () => {
    assert.equal(isPilotOutput(input()), false)
})
