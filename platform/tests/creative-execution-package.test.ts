/**
 * Testes unitarios do CreativeExecutionPackage v1: gerador puro, validador
 * puro e derivacao deterministica do packageId.
 *
 * Cobre: geracao valida para os dois consumidores reais (Marca Salao e
 * Multitrack Hub), codigos de falha estaveis, invariantes (duracao, ordem,
 * cena inexistente, ids ausentes), determinismo, imutabilidade, unicidade,
 * artefatos esperados, source references e barreiras estaticas de pureza.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    deriveExecutionPackageId,
    EXECUTION_PACKAGE_HASH_PREFIX,
    EXECUTION_PACKAGE_ID_MAX_LENGTH,
    EXPECTED_ARTIFACT_KINDS,
    type CreativeExecutionPackage,
} from '../src/creative-execution-package-contract.js'
import type { ContentPipelineValidationInput, ContentPipelineValidationReport } from '../src/content-pipeline-validation-contract.js'
import { createCreativeExecutionPackage } from '../src/create-creative-execution-package.js'
import { validateContentPipeline } from '../src/validate-content-pipeline.js'
import { validateCreativeExecutionPackage } from '../src/validate-creative-execution-package.js'
import { moduleRoot } from './contract-harness.js'

function readJsonExample(relativePath: string): unknown {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as unknown
}

interface CaseFixture {
    readonly name: string
    readonly input: ContentPipelineValidationInput
}

const cases: readonly CaseFixture[] = [
    {
        name: 'marca-salao',
        input: {
            project: readJsonExample('examples/projects/marca-salao-social.project.json'),
            composition: readJsonExample('examples/compositions/marca-salao-social-reel.composition.json'),
            outputPlan: readJsonExample('examples/output-plans/instagram-reels-video.output-plan.json'),
            beatPlan: readJsonExample('examples/pipelines/marca-salao-social-reel.beat-plan.json'),
        },
    },
    {
        name: 'multitrack-hub',
        input: {
            project: readJsonExample('examples/projects/multitrack-hub-social.project.json'),
            composition: readJsonExample('examples/compositions/multitrack-hub-social-reel.composition.json'),
            outputPlan: readJsonExample('examples/output-plans/multitrack-hub-instagram-reels-video.output-plan.json'),
            beatPlan: readJsonExample('examples/pipelines/multitrack-hub-social-reel.beat-plan.json'),
        },
    },
]

function validReport(input: ContentPipelineValidationInput): ContentPipelineValidationReport {
    const report = validateContentPipeline(input)
    assert.equal(report.valid, true, `fixture invalida: ${report.summary}`)
    return report
}

function generate(fixture: CaseFixture): CreativeExecutionPackage {
    const result = createCreativeExecutionPackage(fixture.input, validReport(fixture.input))
    assert.equal(result.ok, true, `geracao falhou para ${fixture.name}`)
    if (!result.ok) throw new Error('unreachable')
    return result.package
}

function codesOf(errors: readonly { code: string }[]): string[] {
    return errors.map((item) => item.code)
}

/* ------------------------------------------------------------------ */
/* Geracao valida para os dois consumidores                            */
/* ------------------------------------------------------------------ */

test('geracao Marca Salao: pacote valido com output, timeline e artefatos derivados', () => {
    const pkg = generate(cases[0] as CaseFixture)
    assert.equal(pkg.schemaVersion, 1)
    assert.equal(pkg.packageId, 'execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan')
    assert.equal(pkg.projectId, 'marca-salao')
    assert.equal(pkg.compositionId, 'social-reel-example')
    assert.equal(pkg.outputPlanId, 'instagram-reels-video')
    assert.equal(pkg.beatPlanId, 'social-reel-beat-plan')

    assert.deepEqual(pkg.output, {
        profileId: 'instagram-reels-video',
        mediaKind: 'video',
        width: 1080,
        height: 1920,
        aspectRatio: '9:16',
        fps: 30,
        rendererAdapter: 'undecided',
        durationMs: 14000,
    })

    assert.equal(pkg.timeline.length, 3)
    assert.deepEqual(pkg.timeline.map((step) => [step.order, step.beatId, step.startMs, step.durationMs, step.endMs]), [
        [1, 'opening-hook', 0, 4000, 4000],
        [2, 'demonstration-body', 4000, 6000, 10000],
        [3, 'closing-cta', 10000, 4000, 14000],
    ])
    assert.equal(pkg.timeline[0]?.onScreenText, 'Contrato de saida em tres cenas.')
    assert.equal(pkg.timeline[0]?.narrationText, 'Texto tecnico de abertura do reel.')

    assert.deepEqual(pkg.expectedArtifacts.map((artifact) => artifact.kind), [...EXPECTED_ARTIFACT_KINDS])
    for (const artifact of pkg.expectedArtifacts) {
        assert.equal(artifact.required, true)
        assert.ok(artifact.logicalName.startsWith(pkg.packageId))
        assert.ok(!artifact.logicalName.includes('/'))
    }

    assert.deepEqual(pkg.source, {
        projectId: 'marca-salao',
        compositionId: 'social-reel-example',
        outputPlanId: 'instagram-reels-video',
        beatPlanId: 'social-reel-beat-plan',
        projectSchemaVersion: 1,
        compositionSchemaVersion: 1,
        outputPlanSchemaVersion: 1,
        beatPlanSchemaVersion: 1,
    })

    const validation = validateCreativeExecutionPackage(pkg)
    assert.equal(validation.valid, true, validation.summary)
    assert.equal(validation.packageId, pkg.packageId)
})

test('geracao Multitrack Hub: pacote independente com IDs distintos e textos preservados', () => {
    const marca = generate(cases[0] as CaseFixture)
    const multitrack = generate(cases[1] as CaseFixture)
    assert.notEqual(multitrack.packageId, marca.packageId)
    assert.equal(multitrack.projectId, 'multitrack-hub')
    assert.equal(multitrack.output.durationMs, 15000)
    assert.equal(multitrack.timeline.length, 4)
    assert.equal(multitrack.timeline[3]?.endMs, 15000)
    assert.equal(multitrack.timeline[0]?.onScreenText, 'Multitracks, playbacks e rateios em um so lugar.')
    assert.equal(multitrack.timeline[3]?.narrationText, 'Chamada tecnica final para conhecer o sistema.')

    const validation = validateCreativeExecutionPackage(multitrack)
    assert.equal(validation.valid, true, validation.summary)
})

test('timeline preserva a ordem e os textos do BeatPlan sem criar conteudo', () => {
    const fixture = cases[1] as CaseFixture
    const pkg = generate(fixture)
    const beatPlan = fixture.input.beatPlan as { beats: Array<Record<string, unknown>> }
    assert.equal(pkg.timeline.length, beatPlan.beats.length)
    beatPlan.beats.forEach((beat, index) => {
        const step = pkg.timeline[index]
        assert.equal(step?.beatId, beat.id)
        assert.deepEqual(step?.sceneIds, beat.sceneIds)
        assert.equal(step?.narrativeFunction, beat.narrativeFunction)
        assert.equal(step?.motionIntent, beat.motionIntent)
        assert.equal(step?.transitionIn, beat.transitionIn)
        assert.equal(step?.transitionOut, beat.transitionOut)
        assert.equal(step?.onScreenText, beat.onScreenText)
        assert.equal(step?.narrationText, (beat.narration as { text: string } | undefined)?.text)
    })
})

test('geracao e deterministica e nao muta documentos nem relatorio', () => {
    const fixture = cases[0] as CaseFixture
    const report = validReport(fixture.input)
    const inputSnapshot = JSON.stringify(fixture.input)
    const reportSnapshot = JSON.stringify(report)
    const run1 = createCreativeExecutionPackage(fixture.input, report)
    const run2 = createCreativeExecutionPackage(fixture.input, report)
    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(fixture.input), inputSnapshot)
    assert.equal(JSON.stringify(report), reportSnapshot)
})

/* ------------------------------------------------------------------ */
/* Codigos de falha                                                    */
/* ------------------------------------------------------------------ */

test('pipeline invalido com estagios bloqueados: PIPELINE_STAGE_BLOCKED', () => {
    const fixture = cases[0] as CaseFixture
    const input = { ...fixture.input, project: { invalido: true } }
    const report = validateContentPipeline(input)
    assert.equal(report.valid, false)
    const result = createCreativeExecutionPackage(input, report)
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'PIPELINE_STAGE_BLOCKED')
})

test('pipeline invalido sem bloqueio: PIPELINE_INVALID', () => {
    const fixture = cases[0] as CaseFixture
    const input = { ...fixture.input, beatPlan: { invalido: true } }
    const report = validateContentPipeline(input)
    assert.equal(report.valid, false)
    assert.deepEqual(report.blockedStages, [])
    const result = createCreativeExecutionPackage(input, report)
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'PIPELINE_INVALID')
})

test('identificador ausente no relatorio: REQUIRED_ID_UNAVAILABLE', () => {
    const fixture = cases[0] as CaseFixture
    const report = { ...validReport(fixture.input), beatPlanId: null }
    const result = createCreativeExecutionPackage(fixture.input, report)
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'REQUIRED_ID_UNAVAILABLE')
})

test('plano de imagem na entrada: UNSUPPORTED_OUTPUT_CONFIGURATION', () => {
    const fixture = cases[0] as CaseFixture
    const imagePlan = {
        schemaVersion: 1,
        projectId: 'marca-salao',
        catalogVersion: '1',
        profileId: 'instagram-feed-image-square',
        profileRevision: 2,
        mediaKind: 'image',
        image: { width: 1080, height: 1080, aspectRatio: '1:1' },
    }
    const result = createCreativeExecutionPackage({ ...fixture.input, outputPlan: imagePlan }, validReport(fixture.input))
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'UNSUPPORTED_OUTPUT_CONFIGURATION')
})

test('duracao divergente entre composition e beat plan: DURATION_MISMATCH', () => {
    const fixture = cases[0] as CaseFixture
    const report = validReport(fixture.input)
    const stages = report.stages.map((stage) =>
        stage.stage === 'beat-plan' && stage.report !== null
            ? { ...stage, report: { ...stage.report, totalDurationMs: 99999 } }
            : stage,
    )
    const tampered = { ...report, stages } as ContentPipelineValidationReport
    const result = createCreativeExecutionPackage(fixture.input, tampered)
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'DURATION_MISMATCH')
})

test('beats vazios: DURATION_MISMATCH sem pacote parcial', () => {
    const fixture = cases[0] as CaseFixture
    const beatPlan = { ...(fixture.input.beatPlan as Record<string, unknown>), beats: [] }
    const result = createCreativeExecutionPackage({ ...fixture.input, beatPlan }, validReport(fixture.input))
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'DURATION_MISMATCH')
})

test('cena inexistente referenciada pelo beat: INTERNAL_INVARIANT_FAILED', () => {
    const fixture = cases[0] as CaseFixture
    const beatPlan = JSON.parse(JSON.stringify(fixture.input.beatPlan)) as { beats: Array<{ sceneIds: string[] }> }
    beatPlan.beats[0]!.sceneIds = ['cena-que-nao-existe']
    const result = createCreativeExecutionPackage({ ...fixture.input, beatPlan }, validReport(fixture.input))
    assert.equal(result.ok, false)
    if (result.ok) return
    assert.equal(result.failureCode, 'INTERNAL_INVARIANT_FAILED')
})

/* ------------------------------------------------------------------ */
/* packageId deterministico                                            */
/* ------------------------------------------------------------------ */

test('packageId legivel enquanto couber no limite; hash canonico acima dele', () => {
    const ids = {
        projectId: 'projeto-teste',
        compositionId: 'composicao-teste',
        outputPlanId: 'plano-teste',
        beatPlanId: 'beats-teste',
    }
    const readable = deriveExecutionPackageId(ids)
    assert.equal(readable, 'execution-projeto-teste-composicao-teste-plano-teste-beats-teste')
    assert.ok(readable.length <= EXECUTION_PACKAGE_ID_MAX_LENGTH)

    const longIds = {
        projectId: 'p'.repeat(40),
        compositionId: 'c'.repeat(40),
        outputPlanId: 'o'.repeat(40),
        beatPlanId: 'b'.repeat(40),
    }
    const hashed = deriveExecutionPackageId(longIds)
    assert.ok(hashed.startsWith(EXECUTION_PACKAGE_HASH_PREFIX))
    assert.match(hashed, /^execution-v1-[0-9a-f]{64}$/)
    assert.equal(hashed, deriveExecutionPackageId(longIds))
    // A canonicalizacao usa ordem fixa de chaves: a ordem do objeto original nao importa.
    const shuffled = {
        beatPlanId: longIds.beatPlanId,
        outputPlanId: longIds.outputPlanId,
        compositionId: longIds.compositionId,
        projectId: longIds.projectId,
    }
    assert.equal(deriveExecutionPackageId(shuffled), hashed)
    assert.notEqual(hashed, deriveExecutionPackageId({ ...longIds, projectId: 'outro' }))
})

/* ------------------------------------------------------------------ */
/* Validador do pacote                                                 */
/* ------------------------------------------------------------------ */

test('validador aceita os pacotes gerados e rejeita nao-objetos', () => {
    for (const fixture of cases) {
        const validation = validateCreativeExecutionPackage(generate(fixture))
        assert.equal(validation.valid, true)
        assert.deepEqual(validation.errors, [])
    }
    for (const invalid of [null, undefined, 'texto', 42, []]) {
        const validation = validateCreativeExecutionPackage(invalid)
        assert.equal(validation.valid, false)
        assert.deepEqual(codesOf(validation.errors), ['EXECUTION_PACKAGE_INVALID'])
    }
})

test('validador rejeita versao errada, campos extras e packageId inconsistente', () => {
    const pkg = generate(cases[0] as CaseFixture)
    const wrongVersion = validateCreativeExecutionPackage({ ...pkg, schemaVersion: 2 })
    assert.ok(codesOf(wrongVersion.errors).includes('EXECUTION_PACKAGE_SCHEMA_VERSION_UNSUPPORTED'))

    const extraField = validateCreativeExecutionPackage({ ...pkg, campoExtra: true })
    assert.ok(codesOf(extraField.errors).includes('EXECUTION_PACKAGE_UNKNOWN_FIELD'))

    const wrongId = validateCreativeExecutionPackage({ ...pkg, packageId: 'execution-outro-projeto-x-y-z' })
    assert.ok(codesOf(wrongId.errors).includes('EXECUTION_PACKAGE_ID_MISMATCH'))

    const badFormat = validateCreativeExecutionPackage({ ...pkg, packageId: 'Pacote_Invalido' })
    assert.ok(codesOf(badFormat.errors).includes('EXECUTION_PACKAGE_ID_INVALID'))
})

test('validador rejeita timeline quebrada: ordem, contiguidade, endMs e duplicatas', () => {
    const pkg = generate(cases[0] as CaseFixture)

    const wrongOrder = validateCreativeExecutionPackage({
        ...pkg,
        timeline: pkg.timeline.map((step, index) => (index === 1 ? { ...step, order: 9 } : step)),
    })
    assert.ok(codesOf(wrongOrder.errors).includes('EXECUTION_PACKAGE_STEP_ORDER_INVALID'))

    const gap = validateCreativeExecutionPackage({
        ...pkg,
        timeline: pkg.timeline.map((step, index) => (index === 1 ? { ...step, startMs: step.startMs + 1, endMs: step.endMs + 1 } : step)),
    })
    assert.ok(codesOf(gap.errors).includes('EXECUTION_PACKAGE_STEP_START_INVALID'))

    const wrongEnd = validateCreativeExecutionPackage({
        ...pkg,
        timeline: pkg.timeline.map((step, index) => (index === 0 ? { ...step, endMs: step.endMs + 1 } : step)),
    })
    assert.ok(codesOf(wrongEnd.errors).includes('EXECUTION_PACKAGE_STEP_END_INVALID'))

    const duplicateBeat = validateCreativeExecutionPackage({
        ...pkg,
        timeline: pkg.timeline.map((step, index) => (index === 1 ? { ...step, beatId: pkg.timeline[0]!.beatId } : step)),
    })
    assert.ok(codesOf(duplicateBeat.errors).includes('EXECUTION_PACKAGE_STEP_BEAT_ID_DUPLICATE'))

    const emptyTimeline = validateCreativeExecutionPackage({ ...pkg, timeline: [] })
    assert.ok(codesOf(emptyTimeline.errors).includes('EXECUTION_PACKAGE_TIMELINE_INVALID'))
})

test('validador rejeita divergencia entre output.durationMs e o fim da timeline', () => {
    const pkg = generate(cases[0] as CaseFixture)
    const validation = validateCreativeExecutionPackage({
        ...pkg,
        output: { ...pkg.output, durationMs: pkg.output.durationMs + 1 },
    })
    assert.ok(codesOf(validation.errors).includes('EXECUTION_PACKAGE_DURATION_MISMATCH'))
})

test('validador rejeita artefatos duplicados, ausentes ou com nome inseguro', () => {
    const pkg = generate(cases[0] as CaseFixture)

    const duplicateId = validateCreativeExecutionPackage({
        ...pkg,
        expectedArtifacts: pkg.expectedArtifacts.map((artifact, index) => (index === 1 ? { ...artifact, id: pkg.expectedArtifacts[0]!.id } : artifact)),
    })
    assert.ok(codesOf(duplicateId.errors).includes('EXECUTION_PACKAGE_ARTIFACT_ID_DUPLICATE'))

    const missingKind = validateCreativeExecutionPackage({
        ...pkg,
        expectedArtifacts: pkg.expectedArtifacts.filter((artifact) => artifact.kind !== 'captions'),
    })
    assert.ok(codesOf(missingKind.errors).includes('EXECUTION_PACKAGE_ARTIFACT_KIND_MISSING'))

    const duplicateKind = validateCreativeExecutionPackage({
        ...pkg,
        expectedArtifacts: [...pkg.expectedArtifacts, { ...pkg.expectedArtifacts[0]!, id: 'primary-output-extra' }],
    })
    assert.ok(codesOf(duplicateKind.errors).includes('EXECUTION_PACKAGE_ARTIFACT_KIND_DUPLICATE'))

    const unsafeName = validateCreativeExecutionPackage({
        ...pkg,
        expectedArtifacts: pkg.expectedArtifacts.map((artifact, index) => (index === 0 ? { ...artifact, logicalName: '../fora.bin' } : artifact)),
    })
    assert.ok(codesOf(unsafeName.errors).includes('EXECUTION_PACKAGE_ARTIFACT_NAME_INVALID'))
})

test('validador rejeita source references inconsistentes', () => {
    const pkg = generate(cases[0] as CaseFixture)
    const mismatch = validateCreativeExecutionPackage({
        ...pkg,
        source: { ...pkg.source, compositionId: 'outra-composicao' },
    })
    assert.ok(codesOf(mismatch.errors).includes('EXECUTION_PACKAGE_SOURCE_MISMATCH'))

    const badVersion = validateCreativeExecutionPackage({
        ...pkg,
        source: { ...pkg.source, beatPlanSchemaVersion: 0 },
    })
    assert.ok(codesOf(badVersion.errors).includes('EXECUTION_PACKAGE_SOURCE_VERSION_INVALID'))
})

test('validador e deterministico e nao muta a entrada', () => {
    const pkg = generate(cases[1] as CaseFixture)
    const snapshot = JSON.stringify(pkg)
    const run1 = validateCreativeExecutionPackage(pkg)
    const run2 = validateCreativeExecutionPackage(pkg)
    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(pkg), snapshot)
})

/* ------------------------------------------------------------------ */
/* Barreiras estaticas de pureza                                       */
/* ------------------------------------------------------------------ */

test('modulos do pacote nao usam rede, relogio, aleatoriedade, Temporal nem filesystem', () => {
    const domainFiles = [
        'src/creative-execution-package-contract.ts',
        'src/create-creative-execution-package.ts',
        'src/validate-creative-execution-package.ts',
    ]
    const forbiddenTokens = [
        '@temporalio',
        'orchestration',
        'fetch(',
        'http.request',
        'https.request',
        'process.env',
        'Date.now',
        'Math.random',
        'node:fs',
        'readFileSync(',
        'writeFileSync(',
        'child_process',
        'ffmpeg',
        'console.',
    ]
    for (const rel of domainFiles) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        for (const token of forbiddenTokens) {
            assert.ok(!content.includes(token), `token proibido "${token}" encontrado em ${rel}`)
        }
    }
    // node:crypto e permitido somente no contrato, para o fallback SHA-256 do packageId.
    for (const rel of ['src/create-creative-execution-package.ts', 'src/validate-creative-execution-package.ts']) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        assert.ok(!content.includes('node:crypto'), `node:crypto fora do contrato: ${rel}`)
    }
})
