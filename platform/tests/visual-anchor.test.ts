/**
 * Testes do validador puro VisualAnchor v1.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { validateVisualAnchor } from '../src/validate-visual-anchor.js'

const SHA = 'a'.repeat(64)

function validAnchor(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'anchor-padrao',
        title: 'Referencia visual do trabalho',
        reference: { mediaId: 'abertura', versionId: 'v-0123456789', sha256: SHA },
        direction: 'Ilustracao clara com fundo neutro e destaque no produto.',
        mustInclude: ['agenda do dia', 'cores da marca'],
        mustAvoid: ['dados pessoais de clientes'],
        origin: 'imported-manual',
        license: 'pending',
    }
}

test('aceita ancora valida e preserva os campos', () => {
    const result = validateVisualAnchor(validAnchor())
    assert.ok(result.ok)
    if (result.ok) {
        assert.equal(result.anchor.id, 'anchor-padrao')
        assert.equal(result.anchor.reference.sha256, SHA)
        assert.deepEqual(result.anchor.mustInclude, ['agenda do dia', 'cores da marca'])
    }
})

test('aceita listas vazias de elementos', () => {
    const doc = { ...validAnchor(), mustInclude: [], mustAvoid: [] }
    assert.ok(validateVisualAnchor(doc).ok)
})

test('nao muta a entrada', () => {
    const doc = validAnchor()
    const snapshot = JSON.stringify(doc)
    validateVisualAnchor(doc)
    assert.equal(JSON.stringify(doc), snapshot)
})

test('rejeita nao objeto', () => {
    for (const bad of [null, undefined, 'x', 42, []]) {
        const result = validateVisualAnchor(bad)
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'VISUAL_ANCHOR_INVALID')
    }
})

test('rejeita campo desconhecido', () => {
    const result = validateVisualAnchor({ ...validAnchor(), provider: 'x' })
    assert.ok(!result.ok)
    if (!result.ok) {
        assert.equal(result.failureCode, 'VISUAL_ANCHOR_UNKNOWN_FIELD')
        assert.equal(result.subject, 'provider')
    }
})

test('rejeita schemaVersion diferente de 1', () => {
    const result = validateVisualAnchor({ ...validAnchor(), schemaVersion: 2 })
    assert.ok(!result.ok)
    if (!result.ok) assert.equal(result.failureCode, 'VISUAL_ANCHOR_SCHEMA_VERSION_UNSUPPORTED')
})

test('rejeita id fora de kebab-case', () => {
    for (const id of ['Anchor', 'anchor_padrao', '-anchor', 'anchor-', '']) {
        const result = validateVisualAnchor({ ...validAnchor(), id })
        assert.ok(!result.ok, `id '${id}' deveria falhar`)
        if (!result.ok) assert.equal(result.failureCode, 'VISUAL_ANCHOR_ID_INVALID')
    }
})

test('rejeita titulo vazio ou acima do limite', () => {
    for (const title of ['', '   ', 'x'.repeat(121)]) {
        const result = validateVisualAnchor({ ...validAnchor(), title })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'VISUAL_ANCHOR_TITLE_INVALID')
    }
})

test('rejeita referencia sem versao ou hash valido', () => {
    const badRefs = [
        null,
        {},
        { mediaId: 'abertura', versionId: 'v-0123456789' },
        { mediaId: 'abertura', versionId: 'v-0123456789', sha256: 'abc' },
        { mediaId: 'Abertura', versionId: 'v-0123456789', sha256: SHA },
        { mediaId: 'abertura', versionId: 'v-0123456789', sha256: SHA, extra: 1 },
    ]
    for (const reference of badRefs) {
        const result = validateVisualAnchor({ ...validAnchor(), reference })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'VISUAL_ANCHOR_REFERENCE_INVALID')
    }
})

test('rejeita direction vazia ou acima do limite', () => {
    for (const direction of ['', 'x'.repeat(2001)]) {
        const result = validateVisualAnchor({ ...validAnchor(), direction })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'VISUAL_ANCHOR_DIRECTION_INVALID')
    }
})

test('rejeita listas de elementos invalidas', () => {
    const badLists = [
        'x',
        [1],
        [''],
        ['x'.repeat(201)],
        Array.from({ length: 21 }, (_, i) => `item-${i + 1}`),
    ]
    for (const field of ['mustInclude', 'mustAvoid'] as const) {
        for (const list of badLists) {
            const result = validateVisualAnchor({ ...validAnchor(), [field]: list })
            assert.ok(!result.ok, `${field} deveria falhar`)
            if (!result.ok) {
                assert.equal(result.failureCode, 'VISUAL_ANCHOR_ELEMENTS_INVALID')
                assert.equal(result.subject, field)
            }
        }
    }
})

test('rejeita origin e license vazios', () => {
    for (const field of ['origin', 'license'] as const) {
        const result = validateVisualAnchor({ ...validAnchor(), [field]: '' })
        assert.ok(!result.ok)
        if (!result.ok) {
            assert.equal(result.failureCode, field === 'origin' ? 'VISUAL_ANCHOR_ORIGIN_INVALID' : 'VISUAL_ANCHOR_LICENSE_INVALID')
        }
    }
})