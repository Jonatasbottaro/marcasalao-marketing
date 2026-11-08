/**
 * Os codigos estaveis do piloto e o reconhecimento deles.
 *
 * `isPilotFailureCode` decide se um erro de fora pertence ao vocabulario do
 * piloto, entao ele tem de reconhecer os valores publicados, nunca as chaves
 * locais do catalogo.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { PILOT_FAILURE_CODES, isPilotFailureCode } from '../../src/pilot-core/failures.js'

test('todo codigo publicado e reconhecido', () => {
    for (const code of Object.values(PILOT_FAILURE_CODES)) {
        assert.equal(isPilotFailureCode(code), true, `${code} deveria ser um codigo do piloto`)
    }
})

test('nenhuma chave do catalogo e um codigo', () => {
    for (const key of Object.keys(PILOT_FAILURE_CODES)) {
        assert.equal(isPilotFailureCode(key), false)
    }
})

test('valores fora do vocabulario e de tipo errado nao sao codigos', () => {
    for (const value of ['TEMPORAL_PILOT_INVENTADO', '', undefined, null, 7, {}, ['TEMPORAL_PILOT_TIMEOUT']]) {
        assert.equal(isPilotFailureCode(value), false)
    }
})

test('os codigos tem prefixo e idioma estaveis, sem duplicata', () => {
    const codes = Object.values(PILOT_FAILURE_CODES)

    assert.equal(new Set(codes).size, codes.length)
    for (const code of codes) {
        assert.match(code, /^TEMPORAL_PILOT_[A-Z0-9_]+$/)
    }
})
