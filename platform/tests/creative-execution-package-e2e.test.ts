/**
 * Teste ponta a ponta do CreativeExecutionPackage v1.
 *
 * Em diretorio temporario (os.tmpdir do processo; redirecionavel para dentro
 * da raiz via TMPDIR): executa a CLI com manifesto multicase, gera os dois
 * pacotes, valida schema draft-07 e semantica, compara byte a byte com as
 * fixtures versionadas, confirma nomes, hashes SHA-256 e independencia,
 * reexecuta e confirma zero diff. Exercita tambem a falha transacional:
 * saida valida anterior preservada quando um caso invalido entra.
 *
 * As fixtures versionadas em examples/execution-packages/ sao geradas pela
 * propria CLI e nunca editadas manualmente; nao constituem render nem job
 * executado.
 */

import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import {
    cpSync,
    existsSync,
    mkdirSync,
    mkdtempSync,
    readFileSync,
    readdirSync,
    rmSync,
    writeFileSync,
} from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import type { ContentPipelineValidationInput } from '../src/content-pipeline-validation-contract.js'
import type { CreativeExecutionPackage } from '../src/creative-execution-package-contract.js'
import { createCreativeExecutionPackage } from '../src/create-creative-execution-package.js'
import { serializeCreativeExecutionPackage } from '../src/serialize-creative-execution-package.js'
import { validateContentPipeline } from '../src/validate-content-pipeline.js'
import { validateCreativeExecutionPackage } from '../src/validate-creative-execution-package.js'
import { moduleRoot } from './contract-harness.js'

const examplesRoot = path.join(moduleRoot, 'examples')
const fixturesRoot = path.join(examplesRoot, 'execution-packages')
const cliPath = path.join(moduleRoot, 'dist', 'src', 'creative-execution-package-cli.js')

const fixtureFiles = [
    'execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json',
    'execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json',
] as const

const caseEntries = [
    'examples/pipelines/marca-salao-pipeline-pilot.pipeline.json',
    'examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json',
]

const ajv = new AjvModule.default({ allErrors: true, strict: false })
const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'creative-execution-package.schema.json'), 'utf8')) as AnySchemaObject
const schemaValidate = ajv.compile(schema)

const tempRoots: string[] = []

function makeTempRoot(): string {
    const root = mkdtempSync(path.join(os.tmpdir(), 'execution-package-e2e-'))
    tempRoots.push(root)
    return root
}

after(() => {
    for (const root of tempRoots) {
        if (root) rmSync(root, { recursive: true, force: true })
    }
})

function sha256(content: string): string {
    return createHash('sha256').update(content, 'utf8').digest('hex')
}

function stageCliRoot(): { root: string; manifestPath: string } {
    const root = makeTempRoot()
    cpSync(examplesRoot, path.join(root, 'examples'), { recursive: true })
    const manifestPath = path.join(root, 'cases.json')
    writeFileSync(manifestPath, `${JSON.stringify({ schemaVersion: 1, id: 'casos-e2e', cases: caseEntries }, null, 2)}\n`, 'utf8')
    return { root, manifestPath }
}

function runCli(root: string, manifestPath: string, outputDir: string): { status: number | null; stdout: string; stderr: string } {
    const result = spawnSync(process.execPath, [cliPath, '--manifest', manifestPath, '--output-dir', outputDir, '--json'], {
        cwd: root,
        encoding: 'utf8',
    })
    return { status: result.status, stdout: result.stdout, stderr: result.stderr }
}

function readJsonExample(relativePath: string): unknown {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as unknown
}

function memoryPackage(brand: 'marca-salao' | 'multitrack-hub'): CreativeExecutionPackage {
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

test('fixtures versionadas existem em LF puro com uma newline final', () => {
    assert.deepEqual(readdirSync(fixturesRoot).sort(), [...fixtureFiles].sort())
    for (const file of fixtureFiles) {
        const raw = readFileSync(path.join(fixturesRoot, file), 'utf8')
        assert.ok(!raw.includes('\r'), `${file} deve ser LF puro`)
        assert.ok(raw.endsWith('\n'), `${file} deve terminar com newline`)
        assert.ok(!raw.endsWith('\n\n'), `${file} deve terminar com exatamente uma newline`)
    }
})

test('paridade byte a byte: gerador em memoria, serializacao, fixture e CLI', () => {
    const { root, manifestPath } = stageCliRoot()
    const run = runCli(root, manifestPath, 'out')
    assert.equal(run.status, 0, `CLI falhou: ${run.stderr}`)
    assert.equal(run.stderr, '')

    const brands = ['marca-salao', 'multitrack-hub'] as const
    brands.forEach((brand, index) => {
        const fixtureBytes = readFileSync(path.join(fixturesRoot, fixtureFiles[index] as string), 'utf8')
        const memoryBytes = serializeCreativeExecutionPackage(memoryPackage(brand))
        const cliBytes = readFileSync(path.join(root, 'out', fixtureFiles[index] as string), 'utf8')
        assert.equal(memoryBytes, fixtureBytes, `gerador em memoria difere da fixture ${brand}`)
        assert.equal(cliBytes, fixtureBytes, `CLI difere da fixture ${brand}`)
        assert.equal(sha256(cliBytes), sha256(fixtureBytes), `hash SHA-256 difere para ${brand}`)
    })
})

test('fixtures passam pelo schema draft-07 executado e pela validacao semantica', () => {
    for (const file of fixtureFiles) {
        const value = JSON.parse(readFileSync(path.join(fixturesRoot, file), 'utf8')) as unknown
        const schemaOk = schemaValidate(value) === true
        assert.equal(schemaOk, true, `schema rejeitou ${file}: ${JSON.stringify(schemaValidate.errors)}`)
        const semantic = validateCreativeExecutionPackage(value)
        assert.equal(semantic.valid, true, `validador semantico rejeitou ${file}: ${semantic.summary}`)
    }
})

test('pacotes sao independentes: nomes, packageIds e projetos distintos', () => {
    const parsed = fixtureFiles.map((file) => JSON.parse(readFileSync(path.join(fixturesRoot, file), 'utf8')) as CreativeExecutionPackage)
    const [marca, multitrack] = parsed as [CreativeExecutionPackage, CreativeExecutionPackage]
    assert.notEqual(marca.packageId, multitrack.packageId)
    assert.notEqual(marca.projectId, multitrack.projectId)
    assert.equal(marca.projectId, 'marca-salao')
    assert.equal(multitrack.projectId, 'multitrack-hub')
    for (const pkg of parsed) {
        assert.ok(pkg.packageId.length <= 128)
        assert.equal(pkg.output.durationMs, pkg.timeline[pkg.timeline.length - 1]?.endMs)
    }
})

test('reexecucao da CLI produz zero diff nos bytes', () => {
    const { root, manifestPath } = stageCliRoot()
    const first = runCli(root, manifestPath, 'out')
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const snapshot = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))
    const second = runCli(root, manifestPath, 'out')
    assert.equal(second.status, 0)
    const again = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))
    assert.deepEqual([...again.entries()], [...snapshot.entries()])
    assert.equal(first.stdout, second.stdout)
})

test('falha transacional: caso invalido posterior preserva hashes da saida anterior', () => {
    const { root, manifestPath } = stageCliRoot()
    const first = runCli(root, manifestPath, 'out')
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const hashesBefore = new Map(readdirSync(outDir).map((file) => [file, sha256(readFileSync(path.join(outDir, file), 'utf8'))]))

    writeFileSync(manifestPath, `${JSON.stringify({ schemaVersion: 1, cases: [...caseEntries, 'examples/pipelines/nao-existe.pipeline.json'] }, null, 2)}\n`, 'utf8')
    const second = runCli(root, manifestPath, 'out')
    assert.notEqual(second.status, 0)

    const hashesAfter = new Map(readdirSync(outDir).map((file) => [file, sha256(readFileSync(path.join(outDir, file), 'utf8'))]))
    assert.deepEqual([...hashesAfter.entries()], [...hashesBefore.entries()], 'hashes da saida anterior devem permanecer identicos')
    assert.ok(!existsSync(path.join(outDir, '.staging-execution-packages')), 'nenhum staging ou arquivo parcial pode permanecer')
    assert.equal(readdirSync(outDir).length, fixtureFiles.length, 'nenhum arquivo parcial promovido')
})
