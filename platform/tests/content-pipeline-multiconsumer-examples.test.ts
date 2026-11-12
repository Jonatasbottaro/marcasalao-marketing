/**
 * Teste de integracao multiprojeto: os dois consumidores reais do pipeline
 * consolidado (Marca Salao e Multitrack Hub) sobre o mesmo nucleo.
 *
 * Prova: fixtures em LF puro com newline final; os dois casos validos pelo
 * mesmo agregador, sem condicional de marca; estrutura dos relatorios
 * comparada (mesmos estagios, mesmos codigos de warning, identificadores
 * distintos); paridade byte a byte do OutputPlan da Multitrack Hub com o
 * stdout do resolvedor; schemas draft-07 executados sobre as fixtures novas;
 * CLI multiprojeto identica a memoria; fronteira publica preservada.
 */

import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    compositionSchemaCheck,
    moduleRoot,
    outputPlanSchemaCheck,
    projectSchemaCheck,
} from './contract-harness.js'
import {
    discoverCaseManifests,
    loadContentPipelineCase,
    validateContentPipelineCaseFromDisk,
} from '../src/content-pipeline-case-loader.js'
import { aggregateContentPipelineCases, type ContentPipelineCaseValidationReport } from '../src/validate-content-pipeline-case.js'
import type { ContentPipelineValidationReport } from '../src/content-pipeline-validation-contract.js'

const examplesRoot = path.join(moduleRoot, 'examples')
const casesCliPath = path.join(moduleRoot, 'dist', 'src', 'content-pipeline-cases-cli.js')
const planCliPath = path.join(moduleRoot, 'dist', 'src', 'output-plan-cli.js')

const caseManifests = [
    {
        id: 'marca-salao-pipeline-pilot',
        manifest: 'pipelines/marca-salao-pipeline-pilot.pipeline.json',
        projectId: 'marca-salao',
        compositionId: 'social-reel-example',
        beatPlanId: 'social-reel-beat-plan',
    },
    {
        id: 'multitrack-hub-pipeline-pilot',
        manifest: 'pipelines/multitrack-hub-pipeline-pilot.pipeline.json',
        projectId: 'multitrack-hub',
        compositionId: 'multitrack-social-reel-example',
        beatPlanId: 'multitrack-social-reel-beat-plan',
    },
] as const

function readFixture(relativePath: string): { raw: string; value: unknown } {
    const raw = readFileSync(path.join(examplesRoot, relativePath), 'utf8')
    return { raw, value: JSON.parse(raw) as unknown }
}

/**
 * Conferencia de quebras de linha. Diretorios governados por `eol=lf` no
 * `.gitattributes` (pipelines, beat-plans, output-plans) precisam estar em LF
 * puro ate no working tree do Windows. Projetos e composicoes nao tem regra
 * `eol=lf`: o checkout Windows pode converter para CRLF, entao a verificacao
 * aceita CRLF uniforme e rejeita CR solto ou ausencia de newline final.
 */
function assertLfFixture(relativePath: string, governed: boolean, exactlyOneNewline = true): void {
    const raw = readFileSync(path.join(examplesRoot, relativePath), 'utf8')
    const normalized = raw.replace(/\r\n/g, '\n')
    if (governed) {
        assert.ok(!raw.includes('\r'), `fixture ${relativePath} contem CR; deve ser LF puro`)
    } else {
        assert.ok(!normalized.includes('\r'), `fixture ${relativePath} contem CR solto`)
    }
    assert.ok(normalized.endsWith('\n'), `fixture ${relativePath} deve terminar com newline`)
    if (exactlyOneNewline) {
        assert.ok(!normalized.endsWith('\n\n'), `fixture ${relativePath} deve terminar com exatamente uma newline`)
    }
}

test('fixtures dos dois consumidores existem e usam LF puro com newline final', () => {
    const fixtures: Array<{ file: string; governed: boolean; exactlyOneNewline?: boolean }> = [
        { file: 'pipelines/marca-salao-pipeline-pilot.pipeline.json', governed: true },
        // O beat plan integrado da Marca Salao termina com duas newlines na main;
        // o fixture historico nao e alterado por esta fatia, apenas conferido em LF.
        { file: 'pipelines/marca-salao-social-reel.beat-plan.json', governed: true, exactlyOneNewline: false },
        { file: 'projects/marca-salao-social.project.json', governed: false },
        { file: 'compositions/marca-salao-social-reel.composition.json', governed: false },
        { file: 'output-plans/instagram-reels-video.output-plan.json', governed: true },
        { file: 'pipelines/multitrack-hub-pipeline-pilot.pipeline.json', governed: true },
        { file: 'pipelines/multitrack-hub-social-reel.beat-plan.json', governed: true },
        { file: 'projects/multitrack-hub-social.project.json', governed: false },
        { file: 'compositions/multitrack-hub-social-reel.composition.json', governed: false },
        { file: 'output-plans/multitrack-hub-instagram-reels-video.output-plan.json', governed: true },
    ]
    for (const fixture of fixtures) {
        assert.ok(existsSync(path.join(examplesRoot, fixture.file)), `fixture ausente: ${fixture.file}`)
        assertLfFixture(fixture.file, fixture.governed, fixture.exactlyOneNewline ?? true)
    }
})

test('os dois consumidores sao validados pelo mesmo nucleo com estrutura identica', () => {
    const reports: ContentPipelineCaseValidationReport[] = []
    for (const item of caseManifests) {
        const manifestPath = path.join(examplesRoot, item.manifest)
        const loaded = loadContentPipelineCase(manifestPath, examplesRoot)
        assert.equal(loaded.ok, true, `caso ${item.id} nao carregou`)
        if (!loaded.ok) continue
        const report = validateContentPipelineCaseFromDisk(manifestPath, examplesRoot)
        assert.equal(report.valid, true, `caso ${item.id} invalido: ${report.summary}`)
        assert.equal(report.caseId, item.id)
        const pipeline = report.pipeline as ContentPipelineValidationReport
        assert.equal(pipeline.projectId, item.projectId)
        assert.equal(pipeline.compositionId, item.compositionId)
        assert.equal(pipeline.beatPlanId, item.beatPlanId)
        assert.equal(pipeline.outputPlanId, 'instagram-reels-video')
        assert.equal(pipeline.errors.length, 0)
        reports.push(report)
    }

    assert.equal(reports.length, 2)
    const [marca, multitrack] = reports as [ContentPipelineCaseValidationReport, ContentPipelineCaseValidationReport]
    const marcaPipeline = marca.pipeline as ContentPipelineValidationReport
    const multitrackPipeline = multitrack.pipeline as ContentPipelineValidationReport

    // Comparacao estrutural: mesmos estagios, mesma ordem, mesmos status,
    // mesmos codigos de warning; identificadores de projeto distintos.
    assert.deepEqual(marcaPipeline.completedStages, multitrackPipeline.completedStages)
    assert.deepEqual(marcaPipeline.blockedStages, multitrackPipeline.blockedStages)
    assert.deepEqual(
        marcaPipeline.stages.map((stage) => [stage.stage, stage.status, stage.blockedBy]),
        multitrackPipeline.stages.map((stage) => [stage.stage, stage.status, stage.blockedBy]),
    )
    assert.deepEqual(
        [...marcaPipeline.warnings.map((item) => item.code)].sort(),
        [...multitrackPipeline.warnings.map((item) => item.code)].sort(),
    )
    assert.notEqual(marcaPipeline.projectId, multitrackPipeline.projectId)
    assert.notEqual(marcaPipeline.compositionId, multitrackPipeline.compositionId)
    assert.notEqual(marcaPipeline.beatPlanId, multitrackPipeline.beatPlanId)
    assert.deepEqual(Object.keys(marcaPipeline).sort(), Object.keys(multitrackPipeline).sort())

    const aggregate = aggregateContentPipelineCases(reports)
    assert.equal(aggregate.valid, true)
    assert.equal(aggregate.caseCount, 2)
    assert.equal(aggregate.validCount, 2)
})

test('CLI multiprojeto sobre examples/ produz o mesmo relatorio da memoria', () => {
    const result = spawnSync(process.execPath, [casesCliPath, '--cases-root', 'examples', '--json'], {
        cwd: moduleRoot,
        encoding: 'utf8',
    })
    assert.equal(result.status, 0, `CLI falhou:\nstderr: ${result.stderr}`)
    assert.equal(result.stderr, '')

    const discovery = discoverCaseManifests(examplesRoot)
    assert.equal(discovery.ok, true)
    if (!discovery.ok) return
    const memory = aggregateContentPipelineCases(
        discovery.paths.map((manifestPath) => validateContentPipelineCaseFromDisk(manifestPath, examplesRoot)),
    )
    assert.deepEqual(JSON.parse(result.stdout), memory)
})

test('OutputPlan da Multitrack Hub e byte a byte igual ao stdout do resolvedor', () => {
    const fixturePath = path.join(examplesRoot, 'output-plans', 'multitrack-hub-instagram-reels-video.output-plan.json')
    const result = spawnSync(
        process.execPath,
        [
            planCliPath,
            '--project', 'examples/projects/multitrack-hub-social.project.json',
            '--profile', 'instagram-reels-video',
            '--json',
        ],
        { cwd: moduleRoot, encoding: 'utf8' },
    )
    assert.equal(result.status, 0, `resolvedor falhou:\nstderr: ${result.stderr}`)
    assert.equal(result.stdout, readFileSync(fixturePath, 'utf8'), 'stdout do resolvedor difere do fixture versionado')
})

test('fixtures novas da Multitrack Hub passam pelos schemas draft-07 executados', () => {
    const project = readFixture('projects/multitrack-hub-social.project.json')
    const composition = readFixture('compositions/multitrack-hub-social-reel.composition.json')
    const outputPlan = readFixture('output-plans/multitrack-hub-instagram-reels-video.output-plan.json')

    const projectCheck = projectSchemaCheck(project.value)
    assert.equal(projectCheck.valid, true, projectCheck.detail)
    const compositionCheck = compositionSchemaCheck(composition.value)
    assert.equal(compositionCheck.valid, true, compositionCheck.detail)
    const planCheck = outputPlanSchemaCheck(outputPlan.value)
    assert.equal(planCheck.valid, true, planCheck.detail)
})

test('a fronteira publica permanece minima: somente validateComposition no entrypoint', async () => {
    const api = await import('../src/composition-validation-api.js')
    assert.deepEqual(Object.keys(api).sort(), ['validateComposition'])

    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        exports: Record<string, unknown>
        files: string[]
    }
    assert.deepEqual(Object.keys(pkg.exports), ['.'])
    assert.deepEqual(pkg.files, ['dist/src', '!dist/src/*-cli.*'])
})

test('o manifesto de caso da Multitrack Hub referencia apenas caminhos dentro de examples/', () => {
    const { value } = readFixture('pipelines/multitrack-hub-pipeline-pilot.pipeline.json')
    const manifest = value as { project: string; composition: string; outputPlan: string; beatPlan: string }
    const manifestDir = path.join(examplesRoot, 'pipelines')
    for (const field of ['project', 'composition', 'outputPlan', 'beatPlan'] as const) {
        const reference = manifest[field]
        assert.ok(!path.isAbsolute(reference), `${field} nao pode ser absoluto`)
        const resolved = path.resolve(manifestDir, reference)
        const relative = path.relative(examplesRoot, resolved)
        assert.ok(!relative.startsWith('..') && !path.isAbsolute(relative), `${field} escapa de examples/: ${relative}`)
        assert.ok(existsSync(resolved), `${field} nao existe: ${reference}`)
    }
})
