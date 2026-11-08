/**
 * Classificacao de falha do piloto TEMPORAL-01.
 *
 * O mapeamento e uma funcao pura de nucleo sobre um sinal neutro: nem nucleo nem
 * teste precisam de @temporalio para provar que violacao de contrato encorre
 * rejected e que falha tecnica encorre failed. A camada de orquestracao so
 * traduz o erro da SDK para esse sinal.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { PILOT_FAILURE_CODES, isPilotFailureCode } from '../../src/pilot-core/failures.js'
import { outcomeFor } from '../../src/pilot-core/pilot-outcome.js'

test('violacao de contrato encorre rejected, com ou sem a flag de nao retry', () => {
    for (const failureCode of [
        PILOT_FAILURE_CODES.schemaUnsupported,
        PILOT_FAILURE_CODES.requestIdRequired,
        PILOT_FAILURE_CODES.projectIdRequired,
        PILOT_FAILURE_CODES.operationInvalid,
        PILOT_FAILURE_CODES.payloadInvalid,
        PILOT_FAILURE_CODES.inputInvalid,
    ]) {
        for (const nonRetryable of [true, false]) {
            assert.deepEqual(outcomeFor({ kind: 'application', code: failureCode, nonRetryable }), { status: 'rejected', failureCode })
        }
    }
})

test('falha tecnica retryable esgotada encorre failed com o proprio codigo', () => {
    assert.deepEqual(outcomeFor({ kind: 'application', code: PILOT_FAILURE_CODES.transientFailure, nonRetryable: false }), {
        status: 'failed',
        failureCode: 'TEMPORAL_PILOT_ACTIVITY_TRANSIENT_FAILURE',
    })
})

test('recusa nao retryable de activity encorre rejected', () => {
    assert.deepEqual(outcomeFor({ kind: 'application', code: PILOT_FAILURE_CODES.nonRetryable, nonRetryable: true }), {
        status: 'rejected',
        failureCode: 'TEMPORAL_PILOT_ACTIVITY_NON_RETRYABLE',
    })
})

test('timeout encorre failed com codigo de timeout', () => {
    assert.deepEqual(outcomeFor({ kind: 'timeout' }), { status: 'failed', failureCode: 'TEMPORAL_PILOT_TIMEOUT' })
})

test('codigo desconhecido nao retryable vira recusa generica, nao um codigo inventado', () => {
    assert.deepEqual(outcomeFor({ kind: 'application', code: 'Qualquer_Coisa_Externa', nonRetryable: true }), {
        status: 'rejected',
        failureCode: PILOT_FAILURE_CODES.nonRetryable,
    })
})

test('codigo desconhecido retryable e sinal desconhecido viram falha do workflow', () => {
    assert.deepEqual(outcomeFor({ kind: 'application', code: 'Qualquer_Coisa_Externa', nonRetryable: false }), {
        status: 'failed',
        failureCode: 'TEMPORAL_PILOT_WORKFLOW_FAILED',
    })
    assert.deepEqual(outcomeFor({ kind: 'unknown' }), { status: 'failed', failureCode: 'TEMPORAL_PILOT_WORKFLOW_FAILED' })
})

test('nenhum sinal produz status completed', () => {
    const signals = [
        { kind: 'timeout' as const },
        { kind: 'unknown' as const },
        ...Object.values(PILOT_FAILURE_CODES).flatMap((code) => [
            { kind: 'application' as const, code, nonRetryable: true },
            { kind: 'application' as const, code, nonRetryable: false },
        ]),
    ]

    for (const signal of signals) {
        const outcome = outcomeFor(signal)
        assert.notEqual(outcome.status, 'completed')
        assert.ok(isPilotFailureCode(outcome.failureCode), `codigo instavel esperado, recebido ${outcome.failureCode}`)
    }
})

test('o mesmo sinal produz exatamente o mesmo desfecho duas vezes', () => {
    const signal = { kind: 'application' as const, code: PILOT_FAILURE_CODES.payloadInvalid, nonRetryable: true }

    assert.deepEqual(outcomeFor(signal), outcomeFor(signal))
})
