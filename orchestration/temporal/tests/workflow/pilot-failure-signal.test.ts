/**
 * Traducao de erro da SDK para o sinal neutro do piloto.
 *
 * Esta e a unica camada que conhece as classes de falha do Temporal. O teste
 * constroi as falhas reais da propria SDK, inclusive o invovel de Activity que
 * o servidor devolve em volta da causa, e exige o sinal correspondente.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ActivityFailure, ApplicationFailure, RetryState, TimeoutFailure, TimeoutType } from '@temporalio/common'

import { PILOT_FAILURE_CODES } from '../../src/pilot-core/failures.js'
import { signalOf } from '../../src/workflows/pilot-failure-signal.js'

function wrappedInActivityFailure(cause: Error): ActivityFailure {
    return new ActivityFailure('activity invocado falhou', 'preparePilotExecution', '1', RetryState.RETRY_STATE_MAXIMUM_ATTEMPTS_REACHED, 'test-identity', cause)
}

test('uma recusa nao retryable da atividade vira sinal de aplicacao nao retryable', () => {
    const failure = ApplicationFailure.create({ type: PILOT_FAILURE_CODES.schemaUnsupported, message: 'x', nonRetryable: true })

    assert.deepEqual(signalOf(wrappedInActivityFailure(failure)), { kind: 'application', code: PILOT_FAILURE_CODES.schemaUnsupported, nonRetryable: true })
})

test('uma falha transienta da atividade vira sinal de aplicacao retryable', () => {
    const failure = ApplicationFailure.create({ type: PILOT_FAILURE_CODES.transientFailure, message: 'x' })

    assert.deepEqual(signalOf(wrappedInActivityFailure(failure)), { kind: 'application', code: PILOT_FAILURE_CODES.transientFailure, nonRetryable: false })
})

test('um timeout do servidor vira sinal de timeout, nao falha de aplicacao', () => {
    const timeout = new TimeoutFailure('start to close', undefined, TimeoutType.START_TO_CLOSE)

    assert.deepEqual(signalOf(wrappedInActivityFailure(timeout)), { kind: 'timeout' })
})

test('uma falha sem causa conhecida vira sinal desconhecido', () => {
    assert.deepEqual(signalOf(wrappedInActivityFailure(new Error('falha comum'))), { kind: 'unknown' })
    assert.deepEqual(signalOf(new Error('falha solta')), { kind: 'unknown' })
    assert.deepEqual(signalOf('texto solto'), { kind: 'unknown' })
    assert.deepEqual(signalOf(undefined), { kind: 'unknown' })
})

test('o sinal nunca carrega mensagem, detalhe ou causa do erro recebido', () => {
    const failure = ApplicationFailure.create({
        type: PILOT_FAILURE_CODES.payloadInvalid,
        message: 'detalhe que nao deve vazar',
        nonRetryable: true,
        details: ['C:\\Repos\\marcasalao'],
    })

    const signal = signalOf(wrappedInActivityFailure(failure))

    assert.equal(JSON.stringify(signal), '{"kind":"application","code":"TEMPORAL_PILOT_PAYLOAD_INVALID","nonRetryable":true}')
})
