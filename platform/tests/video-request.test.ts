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

// ---- sourceStartMs: corte por cena na fonte de video ----

function requestWithVideo(): Record<string, unknown> {
    const request = validRequest()
    const media = request.media as Array<Record<string, unknown>>
    media.push({ id: 'gravacao-01', path: '.workspace/tmp/prova/gravacao-01.mp4', type: 'video', origin: 'synthetic' })
    return request
}

test('aceita inicio explicito em cena de video e ecoa o valor', () => {
    const request = requestWithVideo()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], mediaId: 'gravacao-01', sourceStartMs: 6200, durationMs: 2400 }
    const result = validateVideoRequest(request)
    assert.ok(result.ok, result.ok ? '' : result.failureCode)
    if (result.ok) {
        assert.equal(result.request.scenes[0]?.sourceStartMs, 6200)
        assert.equal(result.request.scenes[0]?.durationMs, 2400)
    }
})

test('aceita inicio zero explicito e pedido legado sem o campo', () => {
    const request = requestWithVideo()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], mediaId: 'gravacao-01', sourceStartMs: 0 }
    const zero = validateVideoRequest(request)
    assert.ok(zero.ok)
    const legacy = requestWithVideo()
    ;(legacy.scenes as Array<Record<string, unknown>>)[0] = { ...scenes[0], mediaId: 'gravacao-01' }
    delete (legacy.scenes as Array<Record<string, unknown>>)[0]!.sourceStartMs
    const omitted = validateVideoRequest(legacy)
    assert.ok(omitted.ok)
    if (zero.ok && omitted.ok) {
        assert.equal(zero.request.scenes[0]?.sourceStartMs, 0)
        assert.equal(omitted.request.scenes[0]?.sourceStartMs, undefined)
    }
})

test('rejeita inicio negativo, fracionario ou nao numerico', () => {
    for (const bad of [-1, 1.5, '6200', NaN]) {
        const request = requestWithVideo()
        const scenes = request.scenes as Array<Record<string, unknown>>
        scenes[0] = { ...scenes[0], mediaId: 'gravacao-01', sourceStartMs: bad }
        assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_SOURCE_START_INVALID', `valor ${String(bad)}`)
    }
})

test('rejeita soma de inicio e duracao nao representavel', () => {
    const request = requestWithVideo()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], mediaId: 'gravacao-01', sourceStartMs: Number.MAX_SAFE_INTEGER, durationMs: 2000 }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_SOURCE_START_INVALID')
})

test('rejeita inicio explicito em cena de imagem (regra cruzada com o cadastro)', () => {
    const request = validRequest()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = { ...scenes[0], sourceStartMs: 1000 }
    assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_SOURCE_START_NOT_ALLOWED')
    const zero = validRequest()
    ;(zero.scenes as Array<Record<string, unknown>>)[0] = { ...scenes[0], sourceStartMs: 0 }
    assert.equal(codes(zero), 'VIDEO_REQUEST_SCENE_SOURCE_START_NOT_ALLOWED')
})

test('cena de imagem sem inicio continua valida (pedido legado)', () => {
    const result = validateVideoRequest(validRequest())
    assert.ok(result.ok)
    if (result.ok) {
        assert.equal(result.request.scenes[0]?.sourceStartMs, undefined)
        assert.equal(result.request.scenes[0]?.framingByProfile, undefined)
    }
})

// ---- framingByProfile: enquadramento por cena e por perfil ----

test('aceita framingByProfile valido em cenas de imagem e video e preserva perfis fora da selecao atual', () => {
    const request = requestWithVideo()
    const scenes = request.scenes as Array<Record<string, unknown>>
    scenes[0] = {
        ...scenes[0],
        mediaId: 'gravacao-01',
        framingByProfile: {
            'instagram-reels-video': { centerX: 0.78, centerY: 0.45, zoomPercent: 180 },
            'youtube-video-horizontal': { centerX: 0.5, centerY: 0.5, zoomPercent: 100 },
        },
    }
    scenes[1] = {
        ...scenes[1],
        framingByProfile: {
            'youtube-shorts': { centerX: 0.2, centerY: 0.8, zoomPercent: 300 },
        },
    }
    const result = validateVideoRequest(request)
    assert.ok(result.ok, result.ok ? '' : `${result.failureCode}:${result.subject}`)
    if (result.ok) {
        assert.deepEqual(result.request.scenes[0]?.framingByProfile?.['instagram-reels-video'], {
            centerX: 0.78,
            centerY: 0.45,
            zoomPercent: 180,
        })
        assert.deepEqual(result.request.scenes[0]?.framingByProfile?.['youtube-video-horizontal'], {
            centerX: 0.5,
            centerY: 0.5,
            zoomPercent: 100,
        })
    }
})

test('rejeita framingByProfile nao objeto, campos faltando ou campos desconhecidos', () => {
    for (const bad of ['preencher', [], null, { 'instagram-reels-video': { centerX: 0.5, centerY: 0.5 } }, { 'instagram-reels-video': { centerX: 0.5, centerY: 0.5, zoomPercent: 120, extra: 1 } }]) {
        const request = validRequest()
        const scenes = request.scenes as Array<Record<string, unknown>>
        scenes[0] = { ...scenes[0], framingByProfile: bad }
        assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_FRAMING_INVALID', `framingByProfile=${JSON.stringify(bad)}`)
    }
})

test('rejeita perfil inexistente ou perfil de imagem em framingByProfile', () => {
    for (const badProfile of ['perfil-desconhecido', 'instagram-feed-image-square', 'facebook-stories-image']) {
        const request = validRequest()
        const scenes = request.scenes as Array<Record<string, unknown>>
        scenes[0] = {
            ...scenes[0],
            framingByProfile: { [badProfile]: { centerX: 0.5, centerY: 0.5, zoomPercent: 120 } },
        }
        assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_FRAMING_PROFILE_INVALID', badProfile)
    }
})

test('rejeita centerX e centerY fora de [0, 1] ou nao numericos', () => {
    for (const bad of [-0.01, 1.01, NaN, Infinity, '0.5']) {
        const r1 = validRequest()
        ;(r1.scenes as Array<Record<string, unknown>>)[0] = {
            ...(r1.scenes as Array<Record<string, unknown>>)[0],
            framingByProfile: { 'instagram-reels-video': { centerX: bad, centerY: 0.5, zoomPercent: 150 } },
        }
        assert.equal(codes(r1), 'VIDEO_REQUEST_SCENE_FRAMING_CENTER_INVALID', `centerX=${String(bad)}`)
        const r2 = validRequest()
        ;(r2.scenes as Array<Record<string, unknown>>)[0] = {
            ...(r2.scenes as Array<Record<string, unknown>>)[0],
            framingByProfile: { 'instagram-reels-video': { centerX: 0.5, centerY: bad, zoomPercent: 150 } },
        }
        assert.equal(codes(r2), 'VIDEO_REQUEST_SCENE_FRAMING_CENTER_INVALID', `centerY=${String(bad)}`)
    }
})

test('rejeita zoomPercent fora de [100, 300] ou nao inteiro', () => {
    for (const bad of [99, 301, 150.5, '150', NaN]) {
        const request = validRequest()
        ;(request.scenes as Array<Record<string, unknown>>)[0] = {
            ...(request.scenes as Array<Record<string, unknown>>)[0],
            framingByProfile: { 'instagram-reels-video': { centerX: 0.5, centerY: 0.5, zoomPercent: bad } },
        }
        assert.equal(codes(request), 'VIDEO_REQUEST_SCENE_FRAMING_ZOOM_INVALID', `zoomPercent=${String(bad)}`)
    }
})