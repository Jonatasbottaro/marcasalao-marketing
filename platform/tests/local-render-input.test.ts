/**
 * Testes unitarios da ponte interna de entrada do render local de prova:
 * contrato de associacao de assets, reuso do validador do pacote e recorte
 * inicial de configuracao. Puro: sem I/O de render, sem rede, sem relogio.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import type { CreativeExecutionPackage } from '../src/creative-execution-package-contract.js'
import {
    LOCAL_RENDER_ASSET_EXTENSIONS,
    LOCAL_RENDER_INPUT_SCHEMA_VERSION,
    type LocalRenderAssetAssociation,
} from '../src/local-render-input-contract.js'
import {
    checkLocalRenderConfiguration,
    validateLocalRenderInput,
} from '../src/validate-local-render-input.js'
import { moduleRoot } from './contract-harness.js'

const PACKAGE_FIXTURES = [
    'examples/execution-packages/execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json',
    'examples/execution-packages/execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json',
] as const

function readPackage(relativePath: string): CreativeExecutionPackage {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as CreativeExecutionPackage
}

function associationFor(pkg: CreativeExecutionPackage): LocalRenderAssetAssociation {
    return {
        schemaVersion: LOCAL_RENDER_INPUT_SCHEMA_VERSION,
        packageId: pkg.packageId,
        assets: pkg.timeline.map((step) => ({
            beatId: step.beatId,
            path: `.workspace/tmp/local-render/assets/${step.beatId}.png`,
        })),
    }
}

function clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T
}

type Mutable<T> = { -readonly [K in keyof T]: Mutable<T[K]> }

for (const fixture of PACKAGE_FIXTURES) {
    test(`entrada valida para a fixture ${path.basename(fixture)}`, () => {
        const pkg = readPackage(fixture)
        const association = associationFor(pkg)
        const result = validateLocalRenderInput(pkg, association)
        assert.equal(result.ok, true)
        if (result.ok) {
            assert.equal(result.package.packageId, pkg.packageId)
            assert.deepEqual(result.association, association)
        }
    })
}

test('resultado e deterministico e nao muta as entradas', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const association = associationFor(pkg)
    const pkgBefore = JSON.stringify(pkg)
    const associationBefore = JSON.stringify(association)
    const first = validateLocalRenderInput(pkg, association)
    const second = validateLocalRenderInput(pkg, association)
    assert.deepEqual(first, second)
    assert.equal(JSON.stringify(pkg), pkgBefore)
    assert.equal(JSON.stringify(association), associationBefore)
})

test('pacote invalido reprova antes da associacao', () => {
    const association = associationFor(readPackage(PACKAGE_FIXTURES[0]))
    for (const bad of [null, 42, {}, { schemaVersion: 1 }]) {
        const result = validateLocalRenderInput(bad, association)
        assert.equal(result.ok, false)
        if (!result.ok) {
            assert.equal(result.failureCode, 'PACKAGE_INVALID')
            assert.equal(result.subject, null)
        }
    }
    const tampered = clone(readPackage(PACKAGE_FIXTURES[0])) as Mutable<CreativeExecutionPackage>
    tampered.timeline[0]!.endMs += 1
    const result = validateLocalRenderInput(tampered, association)
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.failureCode, 'PACKAGE_INVALID')
})

test('estrutura da associacao e verificada com codigos estaveis', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const base = associationFor(pkg)
    const invalidAssociations: readonly unknown[] = [
        null,
        [],
        { ...base, extra: true },
        { ...base, schemaVersion: 2 },
        { ...base, packageId: '' },
        { ...base, assets: 'nao-e-lista' },
        { ...base, assets: [{ beatId: 'opening-hook' }] },
        { ...base, assets: [{ beatId: '', path: 'a.png' }] },
        { ...base, assets: [{ beatId: 'opening-hook', path: 'a.png', extra: 1 }] },
    ]
    for (const association of invalidAssociations) {
        const result = validateLocalRenderInput(pkg, association)
        assert.equal(result.ok, false)
        if (!result.ok) assert.equal(result.failureCode, 'ASSOCIATION_INVALID')
    }
})

test('packageId divergente e recusado', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const association = { ...associationFor(pkg), packageId: 'execution-outro-pacote' }
    const result = validateLocalRenderInput(pkg, association)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'PACKAGE_ID_MISMATCH')
        assert.equal(result.subject, 'execution-outro-pacote')
    }
})

test('beat sem asset, duplicado ou desconhecido e recusado', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const base = associationFor(pkg)

    const missing = { ...base, assets: base.assets.slice(1) }
    const missingResult = validateLocalRenderInput(pkg, missing)
    assert.equal(missingResult.ok, false)
    if (!missingResult.ok) {
        assert.equal(missingResult.failureCode, 'BEAT_ASSET_MISSING')
        assert.equal(missingResult.subject, pkg.timeline[0]!.beatId)
    }

    const duplicated = { ...base, assets: [...base.assets, base.assets[0]] }
    const duplicateResult = validateLocalRenderInput(pkg, duplicated)
    assert.equal(duplicateResult.ok, false)
    if (!duplicateResult.ok) {
        assert.equal(duplicateResult.failureCode, 'BEAT_ASSET_DUPLICATE')
        assert.equal(duplicateResult.subject, pkg.timeline[0]!.beatId)
    }

    const unknown = { ...base, assets: [...base.assets, { beatId: 'beat-fantasma', path: 'a.png' }] }
    const unknownResult = validateLocalRenderInput(pkg, unknown)
    assert.equal(unknownResult.ok, false)
    if (!unknownResult.ok) {
        assert.equal(unknownResult.failureCode, 'UNKNOWN_BEAT_REFERENCE')
        assert.equal(unknownResult.subject, 'beat-fantasma')
    }
})

test('caminhos absolutos, traversal e controle sao recusados', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const base = associationFor(pkg)
    const badPaths = [
        '/absoluto/a.png',
        'C:/absoluto/a.png',
        '\\\\servidor\\a.png',
        '../fora/a.png',
        'assets/../fora/a.png',
        'https://exemplo.invalid/a.png',
        'assets/a\u0000.png',
    ]
    for (const badPath of badPaths) {
        const association = {
            ...base,
            assets: base.assets.map((binding, index) => index === 0 ? { ...binding, path: badPath } : binding),
        }
        const result = validateLocalRenderInput(pkg, association)
        assert.equal(result.ok, false, `caminho deveria falhar: ${badPath}`)
        if (!result.ok) {
            assert.equal(result.failureCode, 'ASSET_PATH_INVALID')
            assert.equal(result.subject, badPath)
        }
    }
})

test('extensao fora do recorte e recusada', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const base = associationFor(pkg)
    const association = {
        ...base,
        assets: base.assets.map((binding, index) => index === 0 ? { ...binding, path: 'assets/a.gif' } : binding),
    }
    const result = validateLocalRenderInput(pkg, association)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'ASSET_EXTENSION_UNSUPPORTED')
        assert.equal(result.subject, 'assets/a.gif')
    }
    assert.ok(LOCAL_RENDER_ASSET_EXTENSIONS.includes('.png'))
})

test('configuracao fora do recorte inicial recebe diagnostico claro', () => {
    const base = readPackage(PACKAGE_FIXTURES[0])
    const firstBeatId = base.timeline[0]?.beatId
    const secondBeatId = base.timeline[1]?.beatId
    assert.ok(firstBeatId)
    assert.ok(secondBeatId)
    const scenarios: readonly { mutate: (pkg: Mutable<CreativeExecutionPackage>) => void; subject: string }[] = [
        { mutate: (pkg) => { pkg.output.fps = 25 }, subject: 'output.fps' },
        { mutate: (pkg) => { pkg.output.aspectRatio = '16:9' }, subject: 'output.aspectRatio' },
        { mutate: (pkg) => { pkg.output.width = 1081 }, subject: 'output.width' },
        { mutate: (pkg) => { pkg.output.plannedContainer = 'webm' }, subject: 'output.plannedContainer' },
        { mutate: (pkg) => { pkg.timeline[1]!.motionIntent = 'parallax-depth' }, subject: `${secondBeatId}.motionIntent` },
        { mutate: (pkg) => { pkg.timeline[1]!.transitionIn = 'fade' }, subject: `${secondBeatId}.transitionIn` },
        { mutate: (pkg) => { pkg.timeline[0]!.transitionOut = 'fade' }, subject: `${firstBeatId}.transitionOut` },
    ]
    for (const scenario of scenarios) {
        const pkg = clone(base) as Mutable<CreativeExecutionPackage>
        scenario.mutate(pkg)
        const result = validateLocalRenderInput(pkg, associationFor(base))
        assert.equal(result.ok, false, `cenario deveria falhar: ${scenario.subject}`)
        if (!result.ok) {
            assert.equal(result.failureCode, 'RENDER_CONFIGURATION_UNSUPPORTED')
            assert.equal(result.subject, scenario.subject)
        }
    }
})

test('fade final e slow-zoom continuam dentro do recorte', () => {
    for (const fixture of PACKAGE_FIXTURES) {
        const pkg = readPackage(fixture)
        const last = pkg.timeline[pkg.timeline.length - 1]
        assert.ok(last)
        assert.equal(last.transitionOut, 'fade')
        assert.ok(pkg.timeline.some((step) => step.motionIntent === 'slow-zoom'))
        const result = validateLocalRenderInput(pkg, associationFor(pkg))
        assert.equal(result.ok, true)
    }
})

test('checkLocalRenderConfiguration indica suporte e razao quando fora do recorte', () => {
    const pkg = readPackage(PACKAGE_FIXTURES[0])
    const valid = checkLocalRenderConfiguration(pkg)
    assert.equal(valid.supported, true)
    assert.equal(valid.unsupportedReason, null)

    const invalidPkg = clone(pkg) as Mutable<CreativeExecutionPackage>
    invalidPkg.output.aspectRatio = '16:9'
    const invalid = checkLocalRenderConfiguration(invalidPkg)
    assert.equal(invalid.supported, false)
    assert.equal(invalid.unsupportedReason, 'output.aspectRatio')
})
