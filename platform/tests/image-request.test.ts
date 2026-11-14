/**
 * Testes do validador puro ImageRequest v1.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { validateImageRequest } from '../src/validate-image-request.js'

const SHA = 'b'.repeat(64)

function validRequest(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'img-cena-abertura',
        target: { kind: 'video_scene', id: 'cena-abertura' },
        profileId: 'instagram-reels-video',
        prompt: 'Ilustracao de abertura com agenda do dia em destaque, fundo neutro.',
        purpose: 'Abertura do video de demonstracao',
        framing: 'Plano medio, elemento centralizado',
        aspectRatio: '9:16',
        geometry: { width: 1080, height: 1920 },
        anchor: null,
        context: { descriptor: 'Tela de abertura com agenda', contextSha256: SHA },
    }
}

test('aceita pedido valido sem ancora', () => {
    const result = validateImageRequest(validRequest())
    assert.ok(result.ok)
    if (result.ok) {
        assert.equal(result.request.target.kind, 'video_scene')
        assert.equal(result.request.anchor, null)
        assert.equal(result.request.geometry.width, 1080)
    }
})

test('aceita pedido valido com ancora e envio ao provedor', () => {
    const doc = {
        ...validRequest(),
        anchor: { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: SHA, sendToProvider: true },
    }
    const result = validateImageRequest(doc)
    assert.ok(result.ok)
    if (result.ok) assert.equal(result.request.anchor?.sendToProvider, true)
})

test('aceita card de carrossel 1:1 e descritor vazio', () => {
    const doc = {
        ...validRequest(),
        target: { kind: 'carousel_card', id: 'capa' },
        profileId: 'instagram-feed-image-square',
        aspectRatio: '1:1',
        geometry: { width: 1080, height: 1080 },
        context: { descriptor: '', contextSha256: SHA },
    }
    assert.ok(validateImageRequest(doc).ok)
})

test('nao muta a entrada', () => {
    const doc = validRequest()
    const snapshot = JSON.stringify(doc)
    validateImageRequest(doc)
    assert.equal(JSON.stringify(doc), snapshot)
})

test('rejeita nao objeto e campo desconhecido', () => {
    assert.ok(!validateImageRequest('x').ok)
    const result = validateImageRequest({ ...validRequest(), provider: 'google-gemini' })
    assert.ok(!result.ok)
    if (!result.ok) {
        assert.equal(result.failureCode, 'IMAGE_REQUEST_UNKNOWN_FIELD')
        assert.equal(result.subject, 'provider')
    }
})

test('rejeita schemaVersion diferente de 1', () => {
    const result = validateImageRequest({ ...validRequest(), schemaVersion: 2 })
    assert.ok(!result.ok)
    if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_SCHEMA_VERSION_UNSUPPORTED')
})

test('rejeita alvo invalido', () => {
    const badTargets = [
        null,
        {},
        { kind: 'story', id: 'capa' },
        { kind: 'video_scene', id: 'Cena' },
        { kind: 'video_scene', id: 'cena', extra: 1 },
    ]
    for (const target of badTargets) {
        const result = validateImageRequest({ ...validRequest(), target })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_TARGET_INVALID')
    }
})

test('rejeita textos vazios ou acima dos limites', () => {
    const cases: Array<[string, string, string]> = [
        ['prompt', '', 'IMAGE_REQUEST_PROMPT_INVALID'],
        ['prompt', 'x'.repeat(4001), 'IMAGE_REQUEST_PROMPT_INVALID'],
        ['purpose', '', 'IMAGE_REQUEST_PURPOSE_INVALID'],
        ['purpose', 'x'.repeat(301), 'IMAGE_REQUEST_PURPOSE_INVALID'],
        ['framing', '', 'IMAGE_REQUEST_FRAMING_INVALID'],
        ['framing', 'x'.repeat(301), 'IMAGE_REQUEST_FRAMING_INVALID'],
    ]
    for (const [field, value, code] of cases) {
        const result = validateImageRequest({ ...validRequest(), [field]: value })
        assert.ok(!result.ok, `${field} deveria falhar`)
        if (!result.ok) assert.equal(result.failureCode, code)
    }
})

test('rejeita proporcao fora da lista', () => {
    const result = validateImageRequest({ ...validRequest(), aspectRatio: '2:3' })
    assert.ok(!result.ok)
    if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_ASPECT_INVALID')
})

test('rejeita geometria invalida', () => {
    const badGeometries = [
        null,
        {},
        { width: 0, height: 1920 },
        { width: 1080, height: 1920.5 },
        { width: 1080, height: 9000 },
        { width: 1080, height: 1920, extra: 1 },
    ]
    for (const geometry of badGeometries) {
        const result = validateImageRequest({ ...validRequest(), geometry })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_GEOMETRY_INVALID')
    }
})

test('rejeita geometria incoerente com a proporcao (semantico)', () => {
    const result = validateImageRequest({ ...validRequest(), geometry: { width: 1080, height: 1080 } })
    assert.ok(!result.ok)
    if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_GEOMETRY_MISMATCH')
})

test('aceita pequena tolerancia de geometria', () => {
    const doc = { ...validRequest(), geometry: { width: 1080, height: 1916 } }
    assert.ok(validateImageRequest(doc).ok)
})

test('rejeita ancora malformada', () => {
    const badAnchors = [
        {},
        { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: 'abc', sendToProvider: true },
        { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: SHA, sendToProvider: 'sim' },
        { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: SHA },
    ]
    for (const anchor of badAnchors) {
        const result = validateImageRequest({ ...validRequest(), anchor })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_ANCHOR_INVALID')
    }
})

test('rejeita contexto sem hash valido', () => {
    const badContexts = [
        null,
        {},
        { descriptor: 'x', contextSha256: 'abc' },
        { descriptor: 'x'.repeat(2001), contextSha256: SHA },
        { descriptor: 'x', contextSha256: SHA, extra: 1 },
    ]
    for (const context of badContexts) {
        const result = validateImageRequest({ ...validRequest(), context })
        assert.ok(!result.ok)
        if (!result.ok) assert.equal(result.failureCode, 'IMAGE_REQUEST_CONTEXT_INVALID')
    }
})