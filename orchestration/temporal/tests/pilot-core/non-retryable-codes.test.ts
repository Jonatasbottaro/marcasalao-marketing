/**
 * A lista canonica dos codigos nao retryable do piloto TEMPORAL-01.
 *
 * A Retry Policy do Workflow e a classificacao de resultado do nucleo descrevem
 * o mesmo conjunto. Enquanto foram duas listas copiadas a mao, uma revisao podia
 * troca-las sem que nada reclamasse. Este arquivo nao deixa: a fonte e unica e
 * qualquer diferenca entre as representacoes cai aqui.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { NON_RETRYABLE_PILOT_CODES, PILOT_FAILURE_CODES } from '../../src/pilot-core/failures.js'
import { outcomeFor } from '../../src/pilot-core/pilot-outcome.js'

const pilotRoot = fileURLToPath(new URL('../../../', import.meta.url))
const workflowSource = readFileSync(path.join(pilotRoot, 'src/workflows/content-pilot-workflow.ts'), 'utf8')
const outcomeSource = readFileSync(path.join(pilotRoot, 'src/pilot-core/pilot-outcome.ts'), 'utf8')

const CANONICAL = [
    PILOT_FAILURE_CODES.schemaUnsupported,
    PILOT_FAILURE_CODES.requestIdRequired,
    PILOT_FAILURE_CODES.projectIdRequired,
    PILOT_FAILURE_CODES.operationInvalid,
    PILOT_FAILURE_CODES.payloadInvalid,
    PILOT_FAILURE_CODES.inputInvalid,
    PILOT_FAILURE_CODES.nonRetryable,
]

const APPLICATION_FAILURE = (code: string): { kind: 'application'; code: string; nonRetryable: boolean } => ({ kind: 'application', code, nonRetryable: true })

/** Vista larga da lista: as verificacoes abaixo perguntam por codigos que NAO devem estar nela. */
const LISTED: readonly string[] = NON_RETRYABLE_PILOT_CODES

test('a lista canonica tem exatamente os seis codigos de entrada mais a recusa nao retryable', () => {
    assert.deepEqual(new Set(NON_RETRYABLE_PILOT_CODES), new Set(CANONICAL))
    assert.equal(NON_RETRYABLE_PILOT_CODES.length, CANONICAL.length)
})

test('a lista canonica nao duplica e nao carrega codigo de fora do catalogo', () => {
    const catalog = new Set(Object.values(PILOT_FAILURE_CODES))

    assert.equal(new Set(NON_RETRYABLE_PILOT_CODES).size, NON_RETRYABLE_PILOT_CODES.length)
    for (const code of NON_RETRYABLE_PILOT_CODES) {
        assert.equal(catalog.has(code), true, `${code} nao e um codigo do piloto`)
    }
})

test('nenhuma falha tecnica retryable aparece na lista nao retryable', () => {
    for (const code of [PILOT_FAILURE_CODES.transientFailure, PILOT_FAILURE_CODES.timeout, PILOT_FAILURE_CODES.workflowFailed]) {
        assert.equal(LISTED.includes(code), false, `${code} e retryable ou tecnico e nao pode estar na lista`)
    }
})

test('a colisao de workflowId nao e tratada como erro de Activity', () => {
    const conflict = PILOT_FAILURE_CODES.workflowIdConflict

    assert.equal(LISTED.includes(conflict), false)
    assert.equal(outcomeFor(APPLICATION_FAILURE(conflict)).status, 'failed')
})

test('a classificacao do nucleo recusa justamente os codigos da lista canonica', () => {
    for (const code of NON_RETRYABLE_PILOT_CODES) {
        const outcome = outcomeFor(APPLICATION_FAILURE(code))

        assert.equal(outcome.status, 'rejected', `${code} deveria ser recusa`)
        assert.equal(outcome.failureCode, code)
    }

    for (const code of Object.values(PILOT_FAILURE_CODES)) {
        if (LISTED.includes(code)) continue
        assert.equal(outcomeFor(APPLICATION_FAILURE(code)).status, 'failed', `${code} nao deveria ser recusa`)
    }
})

test('o Workflow nao redeclara codigo nenhum: ele importa a lista canonica', () => {
    assert.equal(/TEMPORAL_PILOT_[A-Z0-9_]+/.test(workflowSource), false, 'o Workflow carrega um codigo literal em vez da fonte unica')
    assert.match(workflowSource, /import \{[^}]*NON_RETRYABLE_PILOT_CODES[^}]*\} from '\.\.\/pilot-core\/failures\.js'/)
    assert.match(workflowSource, /nonRetryableErrorTypes:\s*(?:\[\s*\.\.\.NON_RETRYABLE_PILOT_CODES\s*\]|NON_RETRYABLE_PILOT_CODES)/)
})

test('o nucleo deriva o conjunto de recusa da mesma lista, sem segunda copia', () => {
    assert.equal(/TEMPORAL_PILOT_[A-Z0-9_]+/.test(outcomeSource), false, 'a classificacao carrega um codigo literal em vez da fonte unica')
    assert.match(outcomeSource, /new Set\(NON_RETRYABLE_PILOT_CODES\)/)
    assert.match(outcomeSource, /import \{[^}]*NON_RETRYABLE_PILOT_CODES[^}]*\} from '\.\/failures\.js'/)
})
