/**
 * Matriz de exportabilidade local por modulo (fonte compartilhada).
 *
 * Cobre os doze perfis do catalogo: video vertical e horizontal, carrossel
 * quadrado e 4:5, motion restrito ao vertical, e os motivos estaveis para
 * perfis conhecidos sem render local.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { listOutputProfiles } from '../src/output-profiles/catalog.js'
import {
    LOCAL_EXPORT_REASON_LABELS,
    localExportCapabilities,
} from '../src/output-profiles/local-export.js'

function caps(id: string) {
    const profile = listOutputProfiles().find((p) => p.id === id)
    assert.ok(profile, `perfil ausente do catalogo: ${id}`)
    return localExportCapabilities(profile)
}

test('video vertical 9:16@30: video e motion suportados, carrossel nao', () => {
    for (const id of ['instagram-reels-video', 'facebook-reels-video', 'youtube-shorts', 'instagram-stories-video', 'facebook-stories-video']) {
        const c = caps(id)
        assert.ok(c.video.supported, id)
        assert.ok(c.motion.supported, id)
        assert.ok(!c.carousel.supported, id)
        assert.equal(c.carousel.reason, 'MEDIA_KIND_MISMATCH')
    }
})

test('video horizontal 16:9@30: video suportado, motion restrito ao vertical', () => {
    const c = caps('youtube-video-horizontal')
    assert.ok(c.video.supported)
    assert.equal(c.video.reason, null)
    assert.ok(!c.motion.supported)
    assert.equal(c.motion.reason, 'MOTION_VERTICAL_ONLY')
    assert.ok(LOCAL_EXPORT_REASON_LABELS.MOTION_VERTICAL_ONLY.includes('9:16'))
})

test('carrossel quadrado e 4:5 suportados; imagem 9:16 sem render local', () => {
    for (const id of ['instagram-feed-image-square', 'facebook-feed-image-square']) {
        const c = caps(id)
        assert.ok(c.carousel.supported, id)
        assert.ok(!c.video.supported, id)
        assert.equal(c.video.reason, 'MEDIA_KIND_MISMATCH')
    }
    for (const id of ['instagram-feed-image-portrait', 'facebook-feed-image-portrait']) {
        const c = caps(id)
        assert.ok(c.carousel.supported, id)
        assert.equal(c.carousel.reason, null)
    }
    for (const id of ['instagram-stories-image', 'facebook-stories-image']) {
        const c = caps(id)
        assert.ok(!c.carousel.supported, id)
        assert.equal(c.carousel.reason, 'GEOMETRY_UNSUPPORTED')
    }
})

test('matriz completa: todo perfil do catalogo tem resposta por modulo', () => {
    const profiles = listOutputProfiles()
    assert.equal(profiles.length, 12)
    for (const profile of profiles) {
        const c = localExportCapabilities(profile)
        for (const mod of ['video', 'carousel', 'motion'] as const) {
            assert.equal(typeof c[mod].supported, 'boolean', `${profile.id}/${mod}`)
            if (c[mod].supported) {
                assert.equal(c[mod].reason, null, `${profile.id}/${mod}`)
            } else {
                assert.ok(c[mod].reason, `${profile.id}/${mod}`)
                assert.ok(LOCAL_EXPORT_REASON_LABELS[c[mod].reason!], `${profile.id}/${mod}`)
            }
        }
    }
})

test('geometrias suportadas batem com os presets do catalogo', () => {
    const horiz = listOutputProfiles().find((p) => p.id === 'youtube-video-horizontal')!
    assert.equal(horiz.geometry.width, 1920)
    assert.equal(horiz.geometry.height, 1080)
    assert.equal(horiz.geometry.aspectRatio, '16:9')
    const portrait = listOutputProfiles().find((p) => p.id === 'instagram-feed-image-portrait')!
    assert.equal(portrait.geometry.width, 1080)
    assert.equal(portrait.geometry.height, 1350)
    assert.equal(portrait.geometry.aspectRatio, '4:5')
})