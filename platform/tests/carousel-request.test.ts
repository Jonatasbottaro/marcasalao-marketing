/**
 * Testes do validador puro CarouselRequest v1.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { validateCarouselRequest } from '../src/validate-carousel-request.js'
import type { CarouselRequestFailureCode } from '../src/carousel-request-contract.js'

function validRequest(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'carrossel-demo',
        project: 'platform/examples/projects/marca-salao-social.project.json',
        profile: 'instagram-feed-image-square',
        title: 'Carrossel demo',
        media: [
            { id: 'fundo-01', path: '.workspace/tmp/prova/fundo-01.png', type: 'image', origin: 'synthetic', license: 'owned-synthetic' },
        ],
        cards: [
            { id: 'capa', title: 'Conheca o Marca Salao', body: 'Gestao completa do salao', mediaId: 'fundo-01' },
            { id: 'conteudo', title: 'Agenda e clientes', body: 'Organize o dia a dia' },
            { id: 'fechamento', title: 'Acesse o link da descricao', body: 'Conheca o sistema' },
        ],
    }
}

function code(input: unknown): CarouselRequestFailureCode | null {
    const r = validateCarouselRequest(input)
    return r.ok ? null : r.failureCode
}

test('aceita pedido valido e ecoa id e ordem dos cards', () => {
    const r = validateCarouselRequest(validRequest())
    assert.ok(r.ok, r.ok ? '' : r.failureCode)
    if (r.ok) {
        assert.equal(r.request.id, 'carrossel-demo')
        assert.deepEqual(r.request.cards.map((c) => c.id), ['capa', 'conteudo', 'fechamento'])
    }
})

test('nao muta a entrada', () => {
    const req = validRequest()
    const before = JSON.stringify(req)
    validateCarouselRequest(req)
    assert.equal(JSON.stringify(req), before)
})

test('rejeita nao objeto', () => {
    assert.equal(code('x'), 'CAROUSEL_REQUEST_INVALID')
    assert.equal(code(null), 'CAROUSEL_REQUEST_INVALID')
})

test('rejeita schemaVersion diferente de 1', () => {
    assert.equal(code({ ...validRequest(), schemaVersion: 2 }), 'CAROUSEL_REQUEST_SCHEMA_VERSION_UNSUPPORTED')
})

test('rejeita id fora de kebab-case', () => {
    assert.equal(code({ ...validRequest(), id: 'CarrosselDemo' }), 'CAROUSEL_REQUEST_ID_INVALID')
})

test('rejeita project vazio', () => {
    assert.equal(code({ ...validRequest(), project: '' }), 'CAROUSEL_REQUEST_PROJECT_INVALID')
})

test('rejeita title vazio', () => {
    assert.equal(code({ ...validRequest(), title: '  ' }), 'CAROUSEL_REQUEST_TITLE_INVALID')
})

test('rejeita profile fora de kebab-case', () => {
    assert.equal(code({ ...validRequest(), profile: 'InstagramFeed' }), 'CAROUSEL_REQUEST_PROFILE_INVALID')
})

test('rejeita campo desconhecido no topo', () => {
    assert.equal(code({ ...validRequest(), autor: 'x' }), 'CAROUSEL_REQUEST_UNKNOWN_FIELD')
})

test('rejeita id de midia duplicado', () => {
    const req = validRequest()
    const media = req.media as Array<Record<string, unknown>>
    media.push({ ...media[0] })
    assert.equal(code(req), 'CAROUSEL_MEDIA_ID_DUPLICATE')
})

test('rejeita tipo de midia nao imagem', () => {
    const req = validRequest()
    ;(req.media as Array<Record<string, unknown>>)[0] = { ...(req.media as Array<Record<string, unknown>>)[0], type: 'video' }
    assert.equal(code(req), 'CAROUSEL_MEDIA_TYPE_INVALID')
})

test('rejeita origem de midia vazia', () => {
    const req = validRequest()
    ;(req.media as Array<Record<string, unknown>>)[0] = { ...(req.media as Array<Record<string, unknown>>)[0], origin: '' }
    assert.equal(code(req), 'CAROUSEL_MEDIA_ORIGIN_INVALID')
})

test('rejeita lista de cards vazia', () => {
    assert.equal(code({ ...validRequest(), cards: [] }), 'CAROUSEL_CARDS_INVALID')
})

test('rejeita id de card duplicado', () => {
    const req = validRequest()
    const cards = req.cards as Array<Record<string, unknown>>
    cards[1] = { ...cards[1], id: 'capa' }
    assert.equal(code(req), 'CAROUSEL_CARD_ID_DUPLICATE')
})

test('rejeita titulo de card vazio', () => {
    const req = validRequest()
    ;(req.cards as Array<Record<string, unknown>>)[0] = { ...(req.cards as Array<Record<string, unknown>>)[0], title: '' }
    assert.equal(code(req), 'CAROUSEL_CARD_TITLE_INVALID')
})

test('rejeita corpo vazio quando presente', () => {
    const req = validRequest()
    ;(req.cards as Array<Record<string, unknown>>)[0] = { ...(req.cards as Array<Record<string, unknown>>)[0], body: '' }
    assert.equal(code(req), 'CAROUSEL_CARD_BODY_INVALID')
})

test('rejeita referencia de midia desconhecida no card', () => {
    const req = validRequest()
    ;(req.cards as Array<Record<string, unknown>>)[0] = { ...(req.cards as Array<Record<string, unknown>>)[0], mediaId: 'inexistente' }
    assert.equal(code(req), 'CAROUSEL_CARD_MEDIA_REFERENCE_INVALID')
})

test('aceita cards sem midia e cadastro vazio', () => {
    const req = validRequest()
    req.media = []
    req.cards = [{ id: 'capa', title: 'So texto' }]
    const r = validateCarouselRequest(req)
    assert.ok(r.ok, r.ok ? '' : r.failureCode)
})