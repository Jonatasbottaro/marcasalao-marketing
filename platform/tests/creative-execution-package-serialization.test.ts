/**
 * Testes da serializacao canonica e da geracao multicase do
 * CreativeExecutionPackage v1.
 *
 * Serializacao: bytes estaveis, LF, uma newline final, zero BOM, ordem de
 * propriedades definida, round trip, independencia da ordem de chaves do
 * objeto original e ausencia de informacao de ambiente.
 *
 * Multicase: dois casos validos, um invalido e outro valido, ordem estavel,
 * falha isolada, lista vazia e summary correto.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import type { ContentPipelineValidationInput } from '../src/content-pipeline-validation-contract.js'
import {
    aggregateCreativeExecutionPackageResults,
    createCreativeExecutionPackageFromCase,
    createCreativeExecutionPackagesFromCases,
    EXECUTION_PACKAGES_VALID_SUMMARY,
} from '../src/creative-execution-packages.js'
import type { CreativeExecutionPackage } from '../src/creative-execution-package-contract.js'
import { createCreativeExecutionPackage } from '../src/create-creative-execution-package.js'
import { serializeCreativeExecutionPackage } from '../src/serialize-creative-execution-package.js'
import { validateContentPipeline } from '../src/validate-content-pipeline.js'
import { moduleRoot } from './contract-harness.js'

const examplesRoot = path.join(moduleRoot, 'examples')

function readJsonExample(relativePath: string): unknown {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as unknown
}

function generatedPackage(brand: 'marca-salao' | 'multitrack-hub'): CreativeExecutionPackage {
    const input: ContentPipelineValidationInput = brand === 'marca-salao'
        ? {
            project: readJsonExample('examples/projects/marca-salao-social.project.json'),
            composition: readJsonExample('examples/compositions/marca-salao-social-reel.composition.json'),
            outputPlan: readJsonExample('examples/output-plans/instagram-reels-video.output-plan.json'),
            beatPlan: readJsonExample('examples/pipelines/marca-salao-social-reel.beat-plan.json'),
        }
        : {
            project: readJsonExample('examples/projects/multitrack-hub-social.project.json'),
            composition: readJsonExample('examples/compositions/multitrack-hub-social-reel.composition.json'),
            outputPlan: readJsonExample('examples/output-plans/multitrack-hub-instagram-reels-video.output-plan.json'),
            beatPlan: readJsonExample('examples/pipelines/multitrack-hub-social-reel.beat-plan.json'),
        }
    const report = validateContentPipeline(input)
    assert.equal(report.valid, true)
    const result = createCreativeExecutionPackage(input, report)
    assert.equal(result.ok, true)
    if (!result.ok) throw new Error('unreachable')
    return result.package
}

/** Reordena chaves recursivamente para provar independencia da ordem original. */
function shuffleKeys(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(shuffleKeys)
    if (typeof value === 'object' && value !== null) {
        const entries = Object.entries(value as Record<string, unknown>).reverse()
        const shuffled: Record<string, unknown> = {}
        for (const [key, item] of entries) shuffled[key] = shuffleKeys(item)
        return shuffled
    }
    return value
}

/* ------------------------------------------------------------------ */
/* Serializacao canonica                                               */
/* ------------------------------------------------------------------ */

test('serializacao produz bytes estaveis em LF com uma newline final e zero BOM', () => {
    for (const brand of ['marca-salao', 'multitrack-hub'] as const) {
        const pkg = generatedPackage(brand)
        const bytes = serializeCreativeExecutionPackage(pkg)
        assert.equal(bytes, serializeCreativeExecutionPackage(pkg))
        assert.ok(!bytes.includes('\r'), 'serializacao deve ser LF puro')
        assert.ok(bytes.endsWith('\n'), 'serializacao deve terminar com newline')
        assert.ok(!bytes.endsWith('\n\n'), 'serializacao deve terminar com exatamente uma newline')
        assert.ok(!bytes.startsWith('\uFEFF'), 'serializacao nao pode conter BOM')
        assert.equal(Buffer.from(bytes, 'utf8').toString('utf8'), bytes)
    }
})

test('serializacao define a ordem das propriedades e e independente da ordem original', () => {
    const pkg = generatedPackage('marca-salao')
    const canonical = serializeCreativeExecutionPackage(pkg)
    const parsed = JSON.parse(canonical) as Record<string, unknown>
    assert.deepEqual(Object.keys(parsed), [
        'schemaVersion',
        'packageId',
        'projectId',
        'compositionId',
        'outputPlanId',
        'beatPlanId',
        'output',
        'timeline',
        'expectedArtifacts',
        'source',
    ])
    const shuffled = shuffleKeys(pkg) as CreativeExecutionPackage
    assert.equal(serializeCreativeExecutionPackage(shuffled), canonical)
})

test('round trip: parse seguido de serializacao produz os mesmos bytes', () => {
    for (const brand of ['marca-salao', 'multitrack-hub'] as const) {
        const pkg = generatedPackage(brand)
        const canonical = serializeCreativeExecutionPackage(pkg)
        const roundTripped = JSON.parse(canonical) as CreativeExecutionPackage
        assert.equal(serializeCreativeExecutionPackage(roundTripped), canonical)
    }
})

test('serializacao nao carrega informacao de ambiente', () => {
    const bytes = serializeCreativeExecutionPackage(generatedPackage('multitrack-hub'))
    for (const needle of [process.cwd(), moduleRoot, 'C:\\', 'C:/', '/tmp/', process.platform]) {
        assert.ok(!bytes.includes(needle), `informacao de ambiente encontrada: ${needle}`)
    }
})

/* ------------------------------------------------------------------ */
/* Geracao multicase                                                   */
/* ------------------------------------------------------------------ */

const marcaManifest = path.join(examplesRoot, 'pipelines', 'marca-salao-pipeline-pilot.pipeline.json')
const multitrackManifest = path.join(examplesRoot, 'pipelines', 'multitrack-hub-pipeline-pilot.pipeline.json')

test('multicase: dois casos validos geram pacotes independentes com IDs distintos', () => {
    const report = createCreativeExecutionPackagesFromCases([marcaManifest, multitrackManifest], examplesRoot)
    assert.equal(report.schemaVersion, 1)
    assert.equal(report.valid, true)
    assert.equal(report.summary, EXECUTION_PACKAGES_VALID_SUMMARY)
    assert.equal(report.caseCount, 2)
    assert.equal(report.packageCount, 2)
    assert.equal(report.failedCaseCount, 0)
    const ids = report.packages.map((result) => result.package?.packageId)
    assert.equal(new Set(ids).size, 2)
    assert.deepEqual(report.packages.map((result) => result.caseId), [
        'marca-salao-pipeline-pilot',
        'multitrack-hub-pipeline-pilot',
    ])
    for (const result of report.packages) {
        assert.equal(result.status, 'generated')
        assert.ok(result.package !== null)
    }
})

test('multicase: um caso invalido nao impede o outro; ordem e falha isolada preservadas', () => {
    const report = createCreativeExecutionPackagesFromCases([marcaManifest, multitrackManifest, marcaManifest], examplesRoot)
    // O terceiro caso repete o primeiro: o caso e valido, mas a agregacao
    // multicase nao deduplica; para falha isolada usamos um caso quebrado abaixo.
    assert.equal(report.caseCount, 3)

    const brokenManifest = path.join(examplesRoot, 'pipelines', 'nao-existe.pipeline.json')
    const mixed = createCreativeExecutionPackagesFromCases([brokenManifest, multitrackManifest], examplesRoot)
    assert.equal(mixed.valid, false)
    assert.equal(mixed.caseCount, 2)
    assert.equal(mixed.packageCount, 1)
    assert.equal(mixed.failedCaseCount, 1)
    assert.equal(mixed.packages[0]?.status, 'case-invalid')
    assert.equal(mixed.packages[0]?.package, null)
    assert.equal(mixed.packages[1]?.status, 'generated')
    assert.match(mixed.summary, /1 of 2 case\(s\) failed/)
})

test('multicase: lista vazia nunca e valida; agregacao pura preserva a ordem', () => {
    const empty = createCreativeExecutionPackagesFromCases([], examplesRoot)
    assert.equal(empty.valid, false)
    assert.equal(empty.caseCount, 0)

    const first = createCreativeExecutionPackageFromCase(marcaManifest, examplesRoot)
    const second = createCreativeExecutionPackageFromCase(multitrackManifest, examplesRoot)
    const aggregated = aggregateCreativeExecutionPackageResults([first, second])
    assert.deepEqual(aggregated.packages, [first, second])
    assert.equal(aggregated.valid, true)
})

test('geracao por caso e deterministica entre execucoes', () => {
    const run1 = createCreativeExecutionPackageFromCase(multitrackManifest, examplesRoot)
    const run2 = createCreativeExecutionPackageFromCase(multitrackManifest, examplesRoot)
    assert.deepEqual(run1, run2)
    assert.ok(run1.package !== null)
    assert.equal(
        serializeCreativeExecutionPackage(run1.package as CreativeExecutionPackage),
        serializeCreativeExecutionPackage(run2.package as CreativeExecutionPackage),
    )
})
