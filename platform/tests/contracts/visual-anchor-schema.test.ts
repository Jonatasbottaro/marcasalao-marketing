/**
 * Paridade estrutural do VisualAnchor v1: espelho draft-07 (Ajv) e validador
 * puro avaliam os mesmos documentos e coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateVisualAnchor } from '../../src/validate-visual-anchor.js'
import { moduleRoot } from '../contract-harness.js'

const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'visual-anchor.schema.json'), 'utf8')) as AnySchemaObject
const ajv = new AjvModule.default({ allErrors: true, strict: false })

const SHA = 'c'.repeat(64)

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map((e) => `${e.instancePath || '#'} ${e.keyword}: ${e.message ?? ''}`.trim())
    return { valid, detail: failures.join(' | ') }
}

function validAnchor(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'anchor-padrao',
        title: 'Referencia visual do trabalho',
        reference: { mediaId: 'abertura', versionId: 'v-0123456789', sha256: SHA },
        direction: 'Ilustracao clara com fundo neutro.',
        mustInclude: ['agenda do dia'],
        mustAvoid: ['dados pessoais'],
        origin: 'imported-manual',
        license: 'pending',
    }
}

test('paridade: ancoras validas aceitas pelo schema e pelo validador', () => {
    const emptyLists = { ...validAnchor(), mustInclude: [], mustAvoid: [] }
    for (const doc of [validAnchor(), emptyLists]) {
        const s = checkSchema(doc)
        assert.ok(s.valid, `Schema rejeitou valido: ${s.detail}`)
        const v = validateVisualAnchor(doc)
        assert.ok(v.ok, `Validador rejeitou valido: ${v.ok ? '' : v.failureCode}`)
    }
})

test('paridade: defeitos rejeitados pelo schema e pelo validador', () => {
    const cases: Array<{ name: string; document: unknown }> = [
        { name: 'nao objeto', document: 'x' },
        { name: 'schemaVersion 2', document: { ...validAnchor(), schemaVersion: 2 } },
        { name: 'id invalido', document: { ...validAnchor(), id: 'Anchor' } },
        { name: 'titulo vazio', document: { ...validAnchor(), title: '' } },
        { name: 'titulo longo', document: { ...validAnchor(), title: 'x'.repeat(121) } },
        { name: 'referencia sem hash', document: { ...validAnchor(), reference: { mediaId: 'abertura', versionId: 'v-0123456789' } } },
        { name: 'hash invalido', document: { ...validAnchor(), reference: { mediaId: 'abertura', versionId: 'v-0123456789', sha256: 'xyz' } } },
        { name: 'direction vazia', document: { ...validAnchor(), direction: '' } },
        { name: 'mustInclude nao lista', document: { ...validAnchor(), mustInclude: 'x' } },
        { name: 'item vazio', document: { ...validAnchor(), mustAvoid: [''] } },
        { name: 'lista acima do limite', document: { ...validAnchor(), mustInclude: Array.from({ length: 21 }, (_, i) => `item-${i + 1}`) } },
        { name: 'origin vazia', document: { ...validAnchor(), origin: '' } },
        { name: 'license vazia', document: { ...validAnchor(), license: '' } },
        { name: 'campo desconhecido', document: { ...validAnchor(), provider: 'x' } },
        { name: 'campo desconhecido na referencia', document: { ...validAnchor(), reference: { mediaId: 'abertura', versionId: 'v-0123456789', sha256: SHA, extra: 1 } } },
    ]
    for (const c of cases) {
        const s = checkSchema(c.document)
        assert.strictEqual(s.valid, false, `Schema deveria rejeitar '${c.name}'`)
        const v = validateVisualAnchor(c.document)
        assert.strictEqual(v.ok, false, `Validador deveria rejeitar '${c.name}'`)
    }
})