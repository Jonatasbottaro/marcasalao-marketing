/**
 * Paridade estrutural do CarouselRequest v1: espelho draft-07 (Ajv) e validador
 * puro avaliam os mesmos documentos e coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateCarouselRequest } from '../../src/validate-carousel-request.js'
import { moduleRoot } from '../contract-harness.js'

const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'carousel-request.schema.json'), 'utf8')) as AnySchemaObject
const ajv = new AjvModule.default({ allErrors: true, strict: false })

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map((e) => `${e.instancePath || '#'} ${e.keyword}: ${e.message ?? ''}`.trim())
    return { valid, detail: failures.join(' | ') }
}

function validRequest(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'carrossel-demo',
        project: 'platform/examples/projects/marca-salao-social.project.json',
        profile: 'instagram-feed-image-square',
        title: 'Carrossel demo',
        media: [{ id: 'fundo-01', path: '.workspace/tmp/prova/fundo-01.png', type: 'image', origin: 'synthetic' }],
        cards: [
            { id: 'capa', title: 'Conheca o Marca Salao', body: 'Gestao completa', mediaId: 'fundo-01' },
            { id: 'fechamento', title: 'Acesse o link da descricao' },
        ],
    }
}

test('paridade: pedidos validos aceitos pelo schema e pelo validador', () => {
    const minimal = validRequest()
    delete (minimal as Record<string, unknown>).profile
    const cases = [validRequest(), minimal, { ...validRequest(), media: [], cards: [{ id: 'capa', title: 'So texto' }] }]
    for (const doc of cases) {
        const s = checkSchema(doc)
        assert.ok(s.valid, `Schema rejeitou valido: ${s.detail}`)
        const v = validateCarouselRequest(doc)
        assert.ok(v.ok, `Validador rejeitou valido: ${v.ok ? '' : v.failureCode}`)
    }
})

test('paridade: defeitos rejeitados pelo schema e pelo validador', () => {
    const badType = validRequest()
    ;(badType.media as Array<Record<string, unknown>>)[0] = { id: 'fundo-01', path: '.workspace/tmp/x.png', type: 'video', origin: 'synthetic' }
    const badCard = validRequest()
    ;(badCard.cards as Array<Record<string, unknown>>)[0] = { id: 'capa', title: '' }
    const cases: Array<{ name: string; document: unknown }> = [
        { name: 'nao objeto', document: 'x' },
        { name: 'nulo', document: null },
        { name: 'schemaVersion 2', document: { ...validRequest(), schemaVersion: 2 } },
        { name: 'id invalido', document: { ...validRequest(), id: 'CarrosselDemo' } },
        { name: 'project vazio', document: { ...validRequest(), project: '' } },
        { name: 'title vazio', document: { ...validRequest(), title: '' } },
        { name: 'campo desconhecido', document: { ...validRequest(), autor: 'x' } },
        { name: 'cards vazio', document: { ...validRequest(), cards: [] } },
        { name: 'tipo midia video', document: badType },
        { name: 'card titulo vazio', document: badCard },
    ]
    for (const c of cases) {
        const s = checkSchema(c.document)
        assert.strictEqual(s.valid, false, `Schema deveria rejeitar '${c.name}'`)
        const v = validateCarouselRequest(c.document)
        assert.strictEqual(v.ok, false, `Validador deveria rejeitar '${c.name}'`)
    }
})