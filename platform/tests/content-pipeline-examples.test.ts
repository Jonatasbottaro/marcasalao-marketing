/**
 * Teste de ponta a ponta dos exemplos do pipeline criativo e integridade de fixtures.
 *
 * Carrega o manifesto de pipeline `platform/examples/pipelines/marca-salao-pipeline-pilot.pipeline.json`,
 * valida confinamento estrito dos caminhos relativos sob `platform/examples/`,
 * valida que todas as fixtures usam quebras LF puras (zero CR) e newline final,
 * executa `validateContentPipeline` e a CLI em modo `--json`,
 * compara o resultado em memoria com a saida da CLI e assegura valid: true.
 */

import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import type { ContentPipelineValidationReport } from '../src/content-pipeline-validation-contract.js'
import { validateContentPipeline } from '../src/validate-content-pipeline.js'
import { moduleRoot } from './contract-harness.js'

const examplesRoot = path.join(moduleRoot, 'examples')
const pipelineManifestPath = path.join(examplesRoot, 'pipelines', 'marca-salao-pipeline-pilot.pipeline.json')
const cliPath = path.join(moduleRoot, 'dist', 'src', 'content-pipeline-validation-cli.js')

interface PipelineManifest {
    readonly schemaVersion: number
    readonly id: string
    readonly project: string
    readonly composition: string
    readonly outputPlan: string
    readonly beatPlan: string
}

test('manifesto integrado de pipeline e confinamento no diretorio examples/', () => {
    assert.ok(existsSync(pipelineManifestPath), 'o manifesto de pipeline deve existir em examples/pipelines/')

    const rawManifest = readFileSync(pipelineManifestPath, 'utf8')
    assert.ok(!rawManifest.includes('\r'), 'o manifesto de pipeline deve usar LF puro (zero CR)')
    assert.ok(rawManifest.endsWith('\n'), 'o manifesto deve terminar com exatamente uma quebra de linha')

    const manifest = JSON.parse(rawManifest) as PipelineManifest
    assert.equal(manifest.schemaVersion, 1)
    assert.equal(manifest.id, 'marca-salao-pipeline-pilot')

    const pipelineDir = path.dirname(pipelineManifestPath)
    const referencedFiles: Record<string, string> = {
        project: path.resolve(pipelineDir, manifest.project),
        composition: path.resolve(pipelineDir, manifest.composition),
        outputPlan: path.resolve(pipelineDir, manifest.outputPlan),
        beatPlan: path.resolve(pipelineDir, manifest.beatPlan),
    }

    const examplesRootNormalized = path.resolve(examplesRoot)

    for (const [key, absPath] of Object.entries(referencedFiles)) {
        assert.ok(existsSync(absPath), `arquivo referenciado por ${key} nao existe: ${absPath}`)
        assert.ok(!path.isAbsolute(manifest[key as keyof PipelineManifest] as string), `${key} nao pode ser caminho absoluto`)

        // Garante que o caminho resolve estritamente dentro de platform/examples/
        const relativeToExamples = path.relative(examplesRootNormalized, absPath)
        assert.ok(
            !relativeToExamples.startsWith('..') && !path.isAbsolute(relativeToExamples),
            `arquivo ${key} escapa da raiz de examples: ${relativeToExamples}`,
        )

        // Confirma que a fixture termina com newline
        const content = readFileSync(absPath, 'utf8')
        assert.ok(content.endsWith('\n'), `fixture ${key} deve terminar com newline: ${absPath}`)

        // Para fixtures sob governanca LF estrita (pipelines e beat-plans)
        if (key === 'beatPlan') {
            assert.ok(!content.includes('\r'), `fixture ${key} contem CR; deve ser LF puro: ${absPath}`)
        }
    }
})

test('execucao ponta a ponta: validador em memoria e CLI produzem resultado identico e valido', () => {
    const rawManifest = readFileSync(pipelineManifestPath, 'utf8')
    const manifest = JSON.parse(rawManifest) as PipelineManifest
    const pipelineDir = path.dirname(pipelineManifestPath)

    const projectPath = path.resolve(pipelineDir, manifest.project)
    const compositionPath = path.resolve(pipelineDir, manifest.composition)
    const outputPlanPath = path.resolve(pipelineDir, manifest.outputPlan)
    const beatPlanPath = path.resolve(pipelineDir, manifest.beatPlan)

    const project = JSON.parse(readFileSync(projectPath, 'utf8')) as unknown
    const composition = JSON.parse(readFileSync(compositionPath, 'utf8')) as unknown
    const outputPlan = JSON.parse(readFileSync(outputPlanPath, 'utf8')) as unknown
    const beatPlan = JSON.parse(readFileSync(beatPlanPath, 'utf8')) as unknown

    // Execucao direta em memoria
    const memoryReport = validateContentPipeline({
        project,
        composition,
        outputPlan,
        beatPlan,
    })

    assert.equal(memoryReport.valid, true)
    assert.equal(memoryReport.errors.length, 0)
    assert.equal(memoryReport.summary, 'Content pipeline is valid.')
    assert.equal(memoryReport.projectId, 'marca-salao')
    assert.equal(memoryReport.compositionId, 'social-reel-example')
    assert.equal(memoryReport.outputPlanId, 'instagram-reels-video')
    assert.equal(memoryReport.beatPlanId, 'social-reel-beat-plan')

    // Execucao via CLI compilada
    const cliResult = spawnSync(
        process.execPath,
        [
            cliPath,
            '--project', projectPath,
            '--composition', compositionPath,
            '--output-plan', outputPlanPath,
            '--beat-plan', beatPlanPath,
            '--json',
        ],
        {
            cwd: moduleRoot,
            encoding: 'utf8',
        },
    )

    assert.equal(cliResult.status, 0, `CLI falhou:\nstderr: ${cliResult.stderr}`)
    assert.equal(cliResult.stderr, '')

    const cliReport = JSON.parse(cliResult.stdout) as ContentPipelineValidationReport
    assert.deepEqual(cliReport, memoryReport)
})
