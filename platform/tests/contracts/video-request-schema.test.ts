/**
 * Paridade estrutural do VideoRequest v1: o espelho draft-07 executado via Ajv
 * e o validador puro em TypeScript avaliam os mesmos documentos e coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateVideoRequest } from '../../src/validate-video-request.js'
import { moduleRoot } from '../contract-harness.js'

const schemaPath = path.join(moduleRoot, 'schemas', 'video-request.schema.json')
const schema = JSON.parse(readFileSync(schemaPath, 'utf8')) as AnySchemaObject
const ajv = new AjvModule.default({ allErrors: true, strict: false })

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map(
        (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
    )
    return { valid, detail: failures.join(' | ') }
}

function validRequest(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'pedido-demo',
        project: 'platform/examples/projects/marca-salao-social.project.json',
        title: 'Video demo de prova',
        profiles: ['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts'],
        media: [
            { id: 'tela-01', path: '.workspace/tmp/prova/tela-01.png', type: 'image', origin: 'synthetic', license: 'owned-synthetic' },
        ],
        scenes: [
            { id: 'abertura', durationMs: 4000, mediaId: 'tela-01', caption: 'Legenda', narration: 'Narracao', title: 'Titulo', narrativeFunction: 'hook', motionIntent: 'none' },
        ],
    }
}

test('paridade estrutural: pedidos validos sao aceitos pelo schema e pelo validador', () => {
    const minimal = validRequest()
    const scenes = minimal.scenes as Array<Record<string, unknown>>
    scenes[0] = { id: 'abertura', durationMs: 4000, mediaId: 'tela-01', caption: 'Legenda', narration: 'Narracao' }
    const media = minimal.media as Array<Record<string, unknown>>
    media[0] = { id: 'tela-01', path: '.workspace/tmp/prova/tela-01.png', type: 'image', origin: 'synthetic' }

    const validCases = [
        validRequest(),
        minimal,
        { ...validRequest(), locale: 'pt-BR', visualStyle: { schemaVersion: 1, id: 'estilo-demo', title: { textColor: '#FFFFFF', outlineColor: '#000000', fontSize: 42, marginTop: 160, marginHorizontal: 60 } } },
    ]

    for (const document of validCases) {
        const schemaResult = checkSchema(document)
        assert.ok(schemaResult.valid, `Schema rejeitou pedido valido: ${schemaResult.detail}`)
        const validatorResult = validateVideoRequest(document)
        assert.ok(validatorResult.ok, `Validador puro rejeitou pedido valido: ${validatorResult.ok ? '' : validatorResult.failureCode}`)
    }
})

test('paridade estrutural: defeitos de formato sao rejeitados pelo schema e pelo validador', () => {
    const badMedia = validRequest()
    ;(badMedia.media as Array<Record<string, unknown>>)[0] = { id: 'tela-01', path: '.workspace/tmp/prova/tela-01.png', type: 'audio', origin: 'synthetic' }
    const badScene = validRequest()
    ;(badScene.scenes as Array<Record<string, unknown>>)[0] = { id: 'abertura', durationMs: 0, mediaId: 'tela-01', caption: 'Legenda', narration: 'Narracao' }
    const badMotion = validRequest()
    ;(badMotion.scenes as Array<Record<string, unknown>>)[0] = { id: 'abertura', durationMs: 4000, mediaId: 'tela-01', caption: 'Legenda', narration: 'Narracao', motionIntent: 'pan' }

    const invalidCases: Array<{ name: string; document: unknown }> = [
        { name: 'nao e objeto', document: 'pedido' },
        { name: 'objeto nulo', document: null },
        { name: 'schemaVersion ausente', document: (() => { const r = validRequest(); delete (r as Record<string, unknown>).schemaVersion; return r })() },
        { name: 'schemaVersion invalida', document: { ...validRequest(), schemaVersion: 2 } },
        { name: 'id invalido', document: { ...validRequest(), id: 'PedidoDemo' } },
        { name: 'project vazio', document: { ...validRequest(), project: '' } },
        { name: 'title vazio', document: { ...validRequest(), title: '' } },
        { name: 'profiles vazio', document: { ...validRequest(), profiles: [] } },
        { name: 'perfil duplicado', document: { ...validRequest(), profiles: ['youtube-shorts', 'youtube-shorts'] } },
        { name: 'campo desconhecido', document: { ...validRequest(), autor: 'designer' } },
        { name: 'visualStyle nao objeto', document: { ...validRequest(), visualStyle: 'estilo' } },
        { name: 'midia vazia', document: { ...validRequest(), media: [] } },
        { name: 'tipo de midia invalido', document: badMedia },
        { name: 'cenas vazia', document: { ...validRequest(), scenes: [] } },
        { name: 'duracao nao positiva', document: badScene },
        { name: 'motionIntent fora do recorte', document: badMotion },
    ]

    for (const testCase of invalidCases) {
        const schemaResult = checkSchema(testCase.document)
        assert.strictEqual(schemaResult.valid, false, `Schema deveria rejeitar '${testCase.name}', mas aceitou.`)
        const validatorResult = validateVideoRequest(testCase.document)
        assert.strictEqual(validatorResult.ok, false, `Validador puro deveria rejeitar '${testCase.name}', mas aceitou.`)
    }
})