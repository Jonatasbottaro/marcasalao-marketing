/**
 * Testes unitarios do validador e serializador canonico de AssetManifest v1.
 * Puro: sem I/O de render, sem rede, sem relogio.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    ASSET_LICENSE_PENDING,
    ASSET_MANIFEST_IMAGE_EXTENSIONS,
    ASSET_MANIFEST_SCHEMA_VERSION,
    ASSET_MANIFEST_VIDEO_EXTENSIONS,
    type AssetManifest,
} from '../src/asset-manifest-contract.js'
import type { CreativeExecutionPackage } from '../src/creative-execution-package-contract.js'
import { serializeAssetManifest } from '../src/serialize-asset-manifest.js'
import { validateAssetManifest } from '../src/validate-asset-manifest.js'
import { moduleRoot } from './contract-harness.js'

const PACKAGE_FIXTURES = [
    {
        caseId: 'marca-salao-social-reel-example',
        path: 'examples/execution-packages/execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json',
    },
    {
        caseId: 'multitrack-hub-multitrack-social-reel-example',
        path: 'examples/execution-packages/execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json',
    },
] as const

const SHA_A = 'a'.repeat(64)
const SHA_B = 'b'.repeat(64)

type Mutable<T> = { -readonly [K in keyof T]: Mutable<T[K]> }

function readPackage(relativePath: string): CreativeExecutionPackage {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as CreativeExecutionPackage
}

function buildValidManifest(pkg: CreativeExecutionPackage, caseId: string): Mutable<AssetManifest> {
    const firstBeat = pkg.timeline[0]
    assert.ok(firstBeat)
    const otherBeats = pkg.timeline.slice(1)
    const assets: Mutable<AssetManifest>['assets'] = [
        {
            id: 'asset-primary-image',
            type: 'image',
            path: '.workspace/tmp/assets/primary.png',
            bytes: 2048,
            sha256: SHA_A,
            origin: 'synthetic-proof-asset',
            license: ASSET_LICENSE_PENDING,
        },
        ...(otherBeats.length > 0
            ? [
                {
                    id: 'asset-secondary-video',
                    type: 'video' as const,
                    path: '.workspace/tmp/assets/secondary.mp4',
                    bytes: 4096,
                    sha256: SHA_B,
                    origin: 'synthetic-proof-clip',
                    license: 'internal-owned',
                },
            ]
            : []),
    ]

    return {
        schemaVersion: ASSET_MANIFEST_SCHEMA_VERSION,
        caseId,
        packageId: pkg.packageId,
        assets,
        bindings: [
            { beatId: firstBeat.beatId, assetId: 'asset-primary-image' },
            ...otherBeats.map((step) => ({
                beatId: step.beatId,
                assetId: 'asset-secondary-video',
            })),
        ],
    }
}

function clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T
}

for (const fixture of PACKAGE_FIXTURES) {
    test(`inventario valido e reutilizacao de asset para ${fixture.caseId}`, () => {
        const pkg = readPackage(fixture.path)
        const manifest = buildValidManifest(pkg, fixture.caseId)
        const result = validateAssetManifest(pkg, fixture.caseId, manifest)
        assert.equal(result.ok, true)
        if (result.ok) {
            assert.equal(result.package.packageId, pkg.packageId)
            assert.equal(result.manifest.caseId, fixture.caseId)
            assert.equal(result.resolvedBindings.length, pkg.timeline.length)
            assert.equal(result.association.assets.length, pkg.timeline.length)
            assert.deepEqual(
                result.resolvedBindings.map((item) => item.beatId),
                pkg.timeline.map((step) => step.beatId),
            )
            const firstAssoc = result.association.assets[0]
            assert.ok(firstAssoc)
            assert.equal(firstAssoc.path, '.workspace/tmp/assets/primary.png')
            if (pkg.timeline.length > 1) {
                const secondResolved = result.resolvedBindings[1]
                assert.ok(secondResolved)
                assert.equal(secondResolved.assetId, 'asset-secondary-video')
                assert.equal(secondResolved.type, 'video')
            }
        }
    })
}

test('vinculos fora de ordem sao canonizados na ordem da timeline sem mutar entrada', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    const reversed: AssetManifest = {
        ...clone(manifest),
        bindings: [...manifest.bindings].reverse(),
    }
    const pkgBefore = JSON.stringify(pkg)
    const inputBefore = JSON.stringify(reversed)

    const first = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, reversed)
    const second = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, reversed)

    assert.deepEqual(first, second)
    assert.equal(JSON.stringify(pkg), pkgBefore)
    assert.equal(JSON.stringify(reversed), inputBefore)
    assert.equal(first.ok, true)
    if (first.ok) {
        assert.deepEqual(
            first.manifest.bindings.map((b) => b.beatId),
            pkg.timeline.map((s) => s.beatId),
        )
        assert.deepEqual(
            first.resolvedBindings.map((b) => b.beatId),
            pkg.timeline.map((s) => s.beatId),
        )
        assert.deepEqual(
            first.association.assets.map((a) => a.beatId),
            pkg.timeline.map((s) => s.beatId),
        )
    }
})

test('pacote invalido falha com PACKAGE_INVALID', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    for (const bad of [null, 123, {}, { schemaVersion: 1 }]) {
        const result = validateAssetManifest(bad, PACKAGE_FIXTURES[0].caseId, manifest)
        assert.equal(result.ok, false)
        if (!result.ok) {
            assert.equal(result.failureCode, 'PACKAGE_INVALID')
        }
    }
})

test('estrutura invalida do inventario falha com ASSET_MANIFEST_INVALID', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const base = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    const firstAsset = base.assets[0]
    assert.ok(firstAsset)

    const invalidCases: unknown[] = [
        null,
        { ...clone(base), extra: true },
        { ...clone(base), schemaVersion: 2 },
        { ...clone(base), assets: [] },
        { ...clone(base), bindings: [] },
        {
            ...clone(base),
            assets: [{ ...firstAsset, origin: '  ', license: 'ok' }],
        },
        {
            ...clone(base),
            assets: [{ ...firstAsset, origin: 'line1\nline2' }],
        },
        {
            ...clone(base),
            assets: [{ ...firstAsset, sha256: 'A'.repeat(64) }],
        },
    ]

    for (const candidate of invalidCases) {
        const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, candidate)
        assert.equal(result.ok, false)
        if (!result.ok) {
            assert.equal(result.failureCode, 'ASSET_MANIFEST_INVALID')
        }
    }
})

test('caseId divergente falha com CASE_ID_MISMATCH', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = buildValidManifest(pkg, 'outro-caso')
    const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'CASE_ID_MISMATCH')
        assert.equal(result.subject, 'outro-caso')
    }
})

test('packageId divergente falha com PACKAGE_ID_MISMATCH', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = {
        ...buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId),
        packageId: 'outro-pacote',
    }
    const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'PACKAGE_ID_MISMATCH')
        assert.equal(result.subject, 'outro-pacote')
    }
})

test('id de asset duplicado falha com ASSET_ID_DUPLICATE', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    const firstAsset = manifest.assets[0]
    assert.ok(firstAsset)
    manifest.assets.push({
        ...firstAsset,
        path: '.workspace/tmp/assets/outro.png',
    })
    const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'ASSET_ID_DUPLICATE')
        assert.equal(result.subject, firstAsset.id)
    }
})

test('caminho absoluto, traversal, URL ou sensivel falha com ASSET_PATH_INVALID', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    for (const badPath of [
        '/abs/file.png',
        'C:/abs/file.png',
        '\\\\server\\share\\file.png',
        '../outside/file.png',
        'assets/../escape.png',
        'https://example.com/file.png',
        '.env',
        'assets/secrets.png',
    ]) {
        const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
        manifest.assets[0]!.path = badPath
        const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest)
        assert.equal(result.ok, false)
        if (!result.ok) {
            assert.equal(result.failureCode, 'ASSET_PATH_INVALID')
            assert.equal(result.subject, badPath)
        }
    }
})

test('extensao incompativel com tipo declarado falha com ASSET_EXTENSION_UNSUPPORTED', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    manifest.assets[0]!.type = 'image'
    manifest.assets[0]!.path = '.workspace/tmp/assets/video-como-imagem.mp4'
    const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'ASSET_EXTENSION_UNSUPPORTED')
    }

    const manifest2 = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    manifest2.assets[0]!.type = 'video'
    manifest2.assets[0]!.path = '.workspace/tmp/assets/imagem-como-video.png'
    const result2 = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest2)
    assert.equal(result2.ok, false)
    if (!result2.ok) {
        assert.equal(result2.failureCode, 'ASSET_EXTENSION_UNSUPPORTED')
    }
})

test('todas as extensoes permitidas de imagem e video sao aceitas', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    for (const ext of ASSET_MANIFEST_IMAGE_EXTENSIONS) {
        const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
        manifest.assets[0]!.type = 'image'
        manifest.assets[0]!.path = `.workspace/tmp/assets/item${ext}`
        assert.equal(validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest).ok, true)
    }
    for (const ext of ASSET_MANIFEST_VIDEO_EXTENSIONS) {
        const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
        manifest.assets[0]!.type = 'video'
        manifest.assets[0]!.path = `.workspace/tmp/assets/item${ext}`
        assert.equal(validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest).ok, true)
    }
})

test('regras de vinculos: beat desconhecido, duplicado, ausente e asset desconhecido', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const firstBeat = pkg.timeline[0]
    assert.ok(firstBeat)

    const unknownBeat = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    unknownBeat.bindings.push({ beatId: 'beat-inexistente', assetId: unknownBeat.assets[0]!.id })
    const r1 = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, unknownBeat)
    assert.equal(r1.ok, false)
    if (!r1.ok) assert.equal(r1.failureCode, 'UNKNOWN_BEAT_REFERENCE')

    const dupBeat = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    dupBeat.bindings.push({ beatId: firstBeat.beatId, assetId: dupBeat.assets[0]!.id })
    const r2 = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, dupBeat)
    assert.equal(r2.ok, false)
    if (!r2.ok) assert.equal(r2.failureCode, 'BEAT_ASSET_DUPLICATE')

    const missingBeat = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    missingBeat.bindings.pop()
    const r3 = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, missingBeat)
    assert.equal(r3.ok, false)
    if (!r3.ok) assert.equal(r3.failureCode, 'BEAT_ASSET_MISSING')

    const unknownAsset = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    unknownAsset.bindings[0]!.assetId = 'asset-inexistente'
    const r4 = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, unknownAsset)
    assert.equal(r4.ok, false)
    if (!r4.ok) assert.equal(r4.failureCode, 'UNKNOWN_ASSET_REFERENCE')
})

test('delegacao para recorte do adaptador local falha com RENDER_CONFIGURATION_UNSUPPORTED', () => {
    const pkg = clone(readPackage(PACKAGE_FIXTURES[0].path)) as Mutable<CreativeExecutionPackage>
    pkg.output.aspectRatio = '16:9'
    const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    const result = validateAssetManifest(pkg, PACKAGE_FIXTURES[0].caseId, manifest)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'RENDER_CONFIGURATION_UNSUPPORTED')
    }
})

test('serializeAssetManifest gera JSON canonico deterministico com nova linha final', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0].path)
    const manifest = buildValidManifest(pkg, PACKAGE_FIXTURES[0].caseId)
    const first = serializeAssetManifest(manifest)
    const second = serializeAssetManifest(manifest)
    assert.equal(first, second)
    assert.equal(first.endsWith('\n'), true)
    assert.equal(first.includes('\r\n'), false)
    assert.deepEqual(JSON.parse(first), manifest)
})
