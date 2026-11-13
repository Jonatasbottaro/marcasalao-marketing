/**
 * Testes do compilador puro VideoRequest v1: deriva os documentos existentes
 * por perfil, valida pelo pipeline canonico, respeita a allowlist e o recorte
 * local, e mantem determinismo e imutabilidade.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { compileVideoRequest } from '../src/compile-video-request.js'
import { projectWith } from './contract-harness.js'

function project(): Record<string, unknown> {
    return projectWith({ outputProfiles: ['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts'] })
}

function request(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'pedido-demo',
        project: 'platform/examples/projects/marca-salao-social.project.json',
        title: 'Video demo de prova',
        profiles: ['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts'],
        visualStyle: { schemaVersion: 1, id: 'estilo-demo', title: { textColor: '#FFFFFF', outlineColor: '#000000', fontSize: 42, marginTop: 160, marginHorizontal: 60 } },
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

test('compila os tres perfis a partir de um unico pedido', () => {
    const result = compileVideoRequest(request(), project())
    assert.ok(result.ok, result.ok ? '' : `${result.failureCode}: ${result.subject}`)
    if (!result.ok) return
    assert.equal(result.requestId, 'pedido-demo')
    assert.equal(result.profiles.length, 3)
    for (const profile of result.profiles) {
        assert.equal(profile.status, 'compiled', `${profile.profileId}: ${profile.failureCode}`)
        assert.ok(profile.package)
        assert.ok(profile.composition)
        assert.ok(profile.beatPlan)
        assert.ok(profile.outputPlan)
        assert.equal(profile.composition?.format.profile, profile.profileId)
        assert.equal(profile.composition?.format.width, 1080)
        assert.equal(profile.composition?.format.height, 1920)
        assert.equal(profile.composition?.format.fps, 30)
        assert.equal(profile.composition?.metadata?.status, 'draft')
        assert.equal(profile.package?.output.durationMs, 14000)
        assert.equal(profile.plan?.supported, true)
    }
})

test('deriva tempos cumulativos e fade apenas no ultimo beat', () => {
    const result = compileVideoRequest(request(), project())
    assert.ok(result.ok)
    if (!result.ok) return
    const profile = result.profiles[0]!
    const beats = profile.beatPlan?.beats ?? []
    assert.deepEqual(beats.map((b) => b.startMs), [0, 4000, 10000])
    assert.deepEqual(beats.map((b) => b.durationMs), [4000, 6000, 4000])
    assert.deepEqual(beats.map((b) => b.transitionOut), ['cut', 'cut', 'fade'])
    assert.deepEqual(beats.map((b) => b.transitionIn), ['none', 'cut', 'cut'])
    assert.deepEqual(beats.map((b) => b.validationStatus), ['draft', 'draft', 'draft'])
})

test('reutiliza a mesma midia em varias cenas sem duplicar cadastro', () => {
    const result = compileVideoRequest(request(), project())
    assert.ok(result.ok)
    if (!result.ok) return
    const profile = result.profiles[0]!
    const association = profile.association
    assert.ok(association)
    assert.equal(association?.assets.length, 3)
    assert.equal(association?.assets[0]?.path, '.workspace/tmp/prova/tela-01.png')
    assert.equal(association?.assets[2]?.path, '.workspace/tmp/prova/tela-01.png')
    assert.equal(profile.package?.packageId, association?.packageId)
})

test('projeta titulos sobrepostos apenas das cenas que declaram title', () => {
    const result = compileVideoRequest(request(), project())
    assert.ok(result.ok)
    if (!result.ok) return
    const overlays = result.profiles[0]!.textOverlayPlan?.overlays ?? []
    assert.equal(overlays.length, 1)
    assert.equal(overlays[0]?.beatId, 'abertura')
    assert.equal(overlays[0]?.text, 'Titulo abertura')
})

test('profileFilter restringe a um unico perfil pedido', () => {
    const result = compileVideoRequest(request(), project(), { profileFilter: 'youtube-shorts' })
    assert.ok(result.ok)
    if (!result.ok) return
    assert.equal(result.profiles.length, 1)
    assert.equal(result.profiles[0]?.profileId, 'youtube-shorts')
})

test('perfil fora da allowlist falha isoladamente sem derrubar os demais', () => {
    const restricted = projectWith({ outputProfiles: ['instagram-reels-video', 'youtube-shorts'] })
    const result = compileVideoRequest(request(), restricted)
    assert.ok(result.ok)
    if (!result.ok) return
    const facebook = result.profiles.find((p) => p.profileId === 'facebook-reels-video')
    assert.equal(facebook?.status, 'failed')
    assert.ok(facebook?.errors.some((e) => e.code === 'OUTPUT_PROFILE_NOT_ALLOWED'))
    const instagram = result.profiles.find((p) => p.profileId === 'instagram-reels-video')
    assert.equal(instagram?.status, 'compiled')
})

test('pedido estruturalmente invalido devolve ok:false', () => {
    const result = compileVideoRequest({ ...request(), id: 'PedidoDemo' }, project())
    assert.equal(result.ok, false)
})

test('projeto invalido devolve ok:false', () => {
    const result = compileVideoRequest(request(), { ...project(), id: 'ProjetoInvalido' })
    assert.equal(result.ok, false)
})

test('visualStyle invalido devolve ok:false', () => {
    const result = compileVideoRequest({ ...request(), visualStyle: { schemaVersion: 1, id: 'x', title: { textColor: 'white' } } }, project())
    assert.equal(result.ok, false)
})

test('e deterministico e nao muta a entrada', () => {
    const req = request()
    const proj = project()
    const beforeReq = JSON.stringify(req)
    const beforeProj = JSON.stringify(proj)
    const first = compileVideoRequest(req, proj)
    const second = compileVideoRequest(req, proj)
    assert.equal(JSON.stringify(first), JSON.stringify(second))
    assert.equal(JSON.stringify(req), beforeReq)
    assert.equal(JSON.stringify(proj), beforeProj)
})