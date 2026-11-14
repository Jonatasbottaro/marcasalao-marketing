/**
 * Paridade estrutural do ImageRequest v1: espelho draft-07 (Ajv) e validador
 * puro avaliam os mesmos documentos e coincidem. A coerencia geometria x
 * proporcao e semantica do validador (IMAGE_REQUEST_GEOMETRY_MISMATCH) e nao
 * faz parte do corpus estrutural.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateImageRequest } from '../../src/validate-image-request.js'
import { moduleRoot } from '../contract-harness.js'

const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'image-request.schema.json'), 'utf8')) as AnySchemaObject
const ajv = new AjvModule.default({ allErrors: true, strict: false })

const SHA = 'd'.repeat(64)

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map((e) => `${e.instancePath || '#'} ${e.keyword}: ${e.message ?? ''}`.trim())
    return { valid, detail: failures.join(' | ') }
}

function validRequest(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'img-cena-abertura',
        target: { kind: 'video_scene', id: 'cena-abertura' },
        profileId: 'instagram-reels-video',
        prompt: 'Ilustracao de abertura com agenda do dia em destaque.',
        purpose: 'Abertura do video',
        framing: 'Plano medio centralizado',
        aspectRatio: '9:16',
        geometry: { width: 1080, height: 1920 },
        anchor: null,
        context: { descriptor: 'Tela de abertura com agenda', contextSha256: SHA },
    }
}

test('paridade: pedidos validos aceitos pelo schema e pelo validador', () => {
    const withAnchor = {
        ...validRequest(),
        anchor: { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: SHA, sendToProvider: false },
    }
    const squareCard = {
        ...validRequest(),
        target: { kind: 'carousel_card', id: 'capa' },
        profileId: 'instagram-feed-image-square',
        aspectRatio: '1:1',
        geometry: { width: 1080, height: 1080 },
        context: { descriptor: '', contextSha256: SHA },
    }
    for (const doc of [validRequest(), withAnchor, squareCard]) {
        const s = checkSchema(doc)
        assert.ok(s.valid, `Schema rejeitou valido: ${s.detail}`)
        const v = validateImageRequest(doc)
        assert.ok(v.ok, `Validador rejeitou valido: ${v.ok ? '' : v.failureCode}`)
    }
})

test('paridade: defeitos rejeitados pelo schema e pelo validador', () => {
    const cases: Array<{ name: string; document: unknown }> = [
        { name: 'nao objeto', document: 'x' },
        { name: 'schemaVersion 2', document: { ...validRequest(), schemaVersion: 2 } },
        { name: 'id invalido', document: { ...validRequest(), id: 'Img' } },
        { name: 'alvo kind invalido', document: { ...validRequest(), target: { kind: 'story', id: 'capa' } } },
        { name: 'alvo id invalido', document: { ...validRequest(), target: { kind: 'video_scene', id: 'Cena' } } },
        { name: 'profileId invalido', document: { ...validRequest(), profileId: 'Perfil' } },
        { name: 'prompt vazio', document: { ...validRequest(), prompt: '' } },
        { name: 'prompt longo', document: { ...validRequest(), prompt: 'x'.repeat(4001) } },
        { name: 'purpose vazia', document: { ...validRequest(), purpose: '' } },
        { name: 'framing vazia', document: { ...validRequest(), framing: '' } },
        { name: 'proporcao fora da lista', document: { ...validRequest(), aspectRatio: '2:3' } },
        { name: 'geometria zero', document: { ...validRequest(), geometry: { width: 0, height: 1920 } } },
        { name: 'geometria nao inteira', document: { ...validRequest(), geometry: { width: 1080, height: 1920.5 } } },
        { name: 'geometria acima do limite', document: { ...validRequest(), geometry: { width: 1080, height: 9000 } } },
        { name: 'ancora sem sendToProvider', document: { ...validRequest(), anchor: { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: SHA } } },
        { name: 'ancora hash invalido', document: { ...validRequest(), anchor: { anchorId: 'anchor-padrao', versionId: 'v-0123456789', sha256: 'abc', sendToProvider: true } } },
        { name: 'contexto sem hash', document: { ...validRequest(), context: { descriptor: 'x' } } },
        { name: 'contexto hash invalido', document: { ...validRequest(), context: { descriptor: 'x', contextSha256: 'abc' } } },
        { name: 'descritor longo', document: { ...validRequest(), context: { descriptor: 'x'.repeat(2001), contextSha256: SHA } } },
        { name: 'campo desconhecido', document: { ...validRequest(), provider: 'x' } },
        { name: 'campo desconhecido no alvo', document: { ...validRequest(), target: { kind: 'video_scene', id: 'cena', extra: 1 } } },
    ]
    for (const c of cases) {
        const s = checkSchema(c.document)
        assert.strictEqual(s.valid, false, `Schema deveria rejeitar '${c.name}'`)
        const v = validateImageRequest(c.document)
        assert.strictEqual(v.ok, false, `Validador deveria rejeitar '${c.name}'`)
    }
})