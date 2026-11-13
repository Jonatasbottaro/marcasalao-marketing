/**
 * Testes do validador puro VideoRequest v1: estrutura exata, campos opcionais,
 * codigos de falha estaveis e imutabilidade da entrada.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { validateVideoRequest } from '../src/validate-video-request.js'
import type { VideoRequestFailureCode } from '../src/video-request-contract.js'

function validRequest(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'pedido-demo',
        project: 'platform/examples/projects/marca-salao-social.project.json',
        title: 'Video demo de prova',
        profiles: ['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts'],
        media: [
            { id: 'tela-01', path: '.workspace/tmp/prova/tela-01.png', type: 'image', origin: 'synthetic', license: 'owned-synthetic' },
            { id: 'tela-02', path: '.workspace/tmp/prova/tela-02.png', type: 'image', origin: 'synthetic' },
        ],
        scenes: [
            { id: 'abertura', durationMs: 4000, mediaId: 'tela-01', caption: 'Legenda abertura', narration: 'Narracao abertura', title: 'Titulo abertura', narrativeFunction: 'hook', motionIntent: 'none' },
            { id: 'meio', durationMs: 6000, mediaId: 'tela-02', caption: 'Legenda meio', narration: 'Narracao meio', motionIntent: 'slow-zoom' },
            { id: 'fecho', durationMs: 4000, mediaId: 'tela-01', caption: 'Legenda fecho', narration: 'Narracao fecho', narrativeFunction: 'cta' },
        ],
    }
}

function codes(input: unknown): VideoRequestFailureCode | null {
    const result = validateVideoRequest(input)
    return result.ok ? null : result.failureCode
}

test('aceita um pedido valido e ecoa o identificador', () => {
    const result = validateVideoRequest(validRequest())
    assert.ok(result.ok, result.ok ? '' : result.failureCode)
    if (result.ok) {
        assert.equal(result.request.id, 'pedido-demo')
        assert.deepEqual([...result.request.profiles], ['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts'])
        assert.equal(result.request.scenes.length, 3)
    }
})

test('preserva campos opcionais ausentes sem inventar valores', () => {
    const request = validRequest()
    const result = validateVideoRequest(request)
    assert.ok(result.ok)
    if (result.ok) {
        assert.equal(result.request.locale, undefined)
        assert.equal(result.request.visualStyle, undefined)
        assert.equal(result.request.media[1]?.license, undefined)
    }
})

test('nao muta a entrada', () => {
    const request = validRequest()
    const before = JSON.stringify(request)
    validateVideoRequest(request)
    assert.equal(JSON.stringify(request), before)
})

test('rejeita entrada que nao e objeto', () => {
    assert.equal(codes('pedido'), 'VIDEO_REQUEST_INVALID')
    assert.equal(codes(null), 'VIDEO_REQUEST_INVALID')
})

test('rejeita schemaVersion diferente de 1', () => {
    assert.equal(codes({ ...validRequest(), schemaVersion: 2 }), 'VIDEO_REQUEST_SCHEMA_VERSION_UNSUPPORTED')
})

test('rejeita id fora de kebab-case', () => {
    assert.equal(codes({ ...validRequest(), id: 'PedidoDemo' }), 'VIDEO_REQUEST_ID_INVALID')
})

test('rejeita project vazio', () => {
    assert.equal(codes({ ...validRequest(), project: '' }), 'VIDEO_REQUEST_PROJECT_INVALID')
})

test('rejeita title vazio', () => {
    assert.equal(codes({ ...validRequest(), title: '   ' }), 'VIDEO_REQUEST_TITLE_INVALID')
})

test('rejeita locale invalido quando presente', () => {
    assert.equal(codes({ ...validRequest(), locale: '' }), 'VIDEO_REQUEST_LOCALE_INVALID')
})

test('rejeita profiles vazio', () => {
    assert.equal(codes({ ...validRequest(), profiles: [] }), 'VIDEO_REQUEST_PROFILES_INVALID')
})

test('rejeita perfil fora de kebab-case', () => {
    assert.equal(codes({ ...validRequest(), profiles: ['Instagram-Reels'] }), 'VIDEO_REQUEST_PROFILES_INVALID')
})

test('rejeita perfil duplicado', () => {
    assert.equal(codes({ ...validRequest(), profiles: ['youtube-shorts', 'youtube-shorts'] }), 'VIDEO_REQUEST_PROFILE_DUPLICATE')
})

test('rejeita campo desconhecido no topo', () => {
    assert.equal(codes({ ...validRequest(), autor: 'designer' }), 'VIDEO_REQUEST_UNKNOWN_FIELD')
})

test('rejeita visualStyle que nao e objeto', () => {
    assert.equal(codes({ ...validRequest(), visualStyle: 'estilo' }), 'VIDEO_REQUEST_VISUAL_STYLE_INVALID')
})

test('rejeita cadastro de midia vazio', () => {
    assert.equal(codes({ ...validRequest(), media: [] }), 'VIDEO_REQUEST_MEDIA_INVALID')
})

test('rejeita id de midia duplicado', () => {
    const request = validRequest()
    const media = request.media as Array<Record<string, unknown>>
    media[1] = { ...media[1], id: 'tela-01' }
    assert.equal(codes(request), 'VIDEO_REQUEST_MEDIA_ID_DUPLICATE')
})

test('rejeita tipo de midia invalido', () => {
    const request = validRequest()
    const media = request.media as Array<Record<string, unknown>>
    media[0] = { ...media[0], type: 'audio' }
    assert.equal(codes(request), 'VIDEO_REQUEST_MEDIA_TYPE_INVALID')
})

test('rejeita origem de midia vazia', () => {
    const request = validRequest()
    const media = request.media as Array<Record<string, unknown>>
    media[0] = { ...media[0], origin: '' }
    assert.equal(codes(request), 'VIDEO_REQUEST_MEDIA_ORIGIN_INVALID')
})

test('rejeita licenca de midia vazia quando presente', () => {
    const request = validRequest()
    const media = request.media as Array<Record<string, unknown>>
    media[0] = { ...media[0], license: '' }
    assert.equal(codes(request), 'VIDEO_REQUEST_MEDIA_LICENSE_INVALID')
})

test('rejeita lista de cenas vazia', () => {
    assert.equal(codes({ ...validRequest(), scenes: [] }), 'VIDEO_REQUEST_SCENES_INVALID')
})

test('rejeita id de cena duplicado', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[1] = { ...scenes[1], id: 'abertura' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_ID_DUPLICATE')
})

test('rejeita duracao de cena nao positiva', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], durationMs: 0 }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_DURATION_INVALID')
})

test('rejeita referencia de midia desconhecida na cena', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], mediaId: 'inexistente' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_MEDIA_REFERENCE_INVALID')
})

test('rejeita legenda vazia', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], caption: '' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_CAPTION_INVALID')
})

test('rejeita narracao vazia', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], narration: '' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_NARRATION_INVALID')
})

test('rejeita titulo sobreposto vazio quando presente', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], title: '' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_TITLE_INVALID')
})

test('rejeita motionIntent fora do recorte', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], motionIntent: 'pan' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_MOTION_INTENT_INVALID')
})

test('rejeita narrativeFunction invalida', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], narrativeFunction: 'invalida' }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_NARRATIVE_FUNCTION_INVALID')
})