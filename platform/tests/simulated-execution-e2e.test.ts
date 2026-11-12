/**
 * Teste ponta a ponta do executor local simulado v1.
 *
 * Em diretorio temporario (os.tmpdir do processo; redirecionavel para dentro
 * da raiz via TMPDIR): executa a CLI multicase, valida schemas e semantica,
 * compara byte a byte com as fixtures versionadas (memoria == serializacao
 * == CLI == fixture), confirma hashes SHA-256, reexecuta com zero diff e
 * exercita a prova transacional (pacote invalido e falha de promocao
 * preservam a saida anterior).
 *
 * As fixtures em examples/simulated-executions/ sao produzidas pelo proprio
 * executor e nunca editadas manualmente; nao constituem render nem midia.
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

import type { CreativeExecutionPackage } from '../src/creative-execution-package-contract.js'
import { createSimulatedExecutionPlan } from '../src/create-simulated-execution-plan.js'
import type { SimulatedExecutionPlan } from '../src/simulated-execution-plan-contract.js'
import { runSimulatedExecution } from '../src/simulated-execution-runner.js'
import {
    serializeSimulatedExecutionEvents,
    serializeSimulatedExecutionPlan,
    serializeSimulatedExecutionReport,
} from '../src/serialize-simulated-execution.js'
import { buildSimulatedExecutionFiles } from '../src/simulated-execution-writer.js'
import { validateSimulatedExecutionReport } from '../src/validate-simulated-execution-report.js'
import { moduleRoot } from './contract-harness.js'

const examplesRoot = path.join(moduleRoot, 'examples')
const packagesDir = path.join(examplesRoot, 'execution-packages')
const fixturesRoot = path.join(examplesRoot, 'simulated-executions')
const cliPath = path.join(moduleRoot, 'dist', 'src', 'simulated-execution-cli.js')

const brands = [
    {
        dir: 'marca-salao',
        packageFile: 'execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json',
        executionId: 'simulation-execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan',
    },
    {
        dir: 'multitrackhub',
        packageFile: 'execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json',
        executionId: 'simulation-execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan',
    },
] as const

const executionFiles = [
    'execution-plan.json',
    'execution-report.json',
    'events.json',
    'hashes.json',
    'artifacts/primary-output.manifest.json',
    'artifacts/captions.txt',
    'artifacts/narration-script.txt',
    'artifacts/execution-summary.txt',
] as const

const ajv = new AjvModule.default({ allErrors: true, strict: false })
function compileSchema(file: string): (value: unknown) => boolean {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', file), 'utf8')) as AnySchemaObject
    const validate = ajv.compile(schema)
    return (value: unknown) => validate(value) === true
}
const planSchemaCheck = compileSchema('simulated-execution-plan.schema.json')
const reportSchemaCheck = compileSchema('simulated-execution-report.schema.json')

const tempRoots: string[] = []
function makeTempRoot(): string {
    const root = mkdtempSync(path.join(os.tmpdir(), 'simulated-execution-e2e-'))
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

function readPackage(file: string): CreativeExecutionPackage {
    return JSON.parse(readFileSync(path.join(packagesDir, file), 'utf8')) as CreativeExecutionPackage
}

function planOf(executionPackage: CreativeExecutionPackage): SimulatedExecutionPlan {
    const result = createSimulatedExecutionPlan(executionPackage)
    assert.equal(result.ok, true)
    if (!result.ok) throw new Error('unreachable')
    return result.plan
}

function listFilesRecursive(dir: string): string[] {
    const found: string[] = []
    function walk(current: string, prefix: string): void {
        for (const entry of readdirSync(current, { withFileTypes: true })) {
            const relative = prefix ? `${prefix}/${entry.name}` : entry.name
            if (entry.isDirectory()) walk(path.join(current, entry.name), relative)
            else found.push(relative)
        }
    }
    walk(dir, '')
    return found.sort()
}

function stageCliRoot(): { root: string; packages: string } {
    const root = makeTempRoot()
    const packages = path.join(root, 'packages')
    mkdirSync(packages, { recursive: true })
    cpSync(packagesDir, packages, { recursive: true })
    return { root, packages }
}

function runCli(root: string, args: readonly string[]): { status: number | null; stdout: string; stderr: string } {
    const result = spawnSync(process.execPath, [cliPath, ...args, '--root', root], { cwd: root, encoding: 'utf8' })
    return { status: result.status, stdout: result.stdout, stderr: result.stderr }
}

test('fixtures versionadas existem em LF puro com uma newline final', () => {
    for (const brand of brands) {
        const dir = path.join(fixturesRoot, brand.dir)
        assert.deepEqual(listFilesRecursive(dir), [...executionFiles].sort())
        for (const file of executionFiles) {
            const raw = readFileSync(path.join(dir, file), 'utf8')
            assert.ok(!raw.includes('\r'), `${brand.dir}/${file} deve ser LF puro`)
            assert.ok(raw.endsWith('\n'), `${brand.dir}/${file} deve terminar com newline`)
            assert.ok(!raw.endsWith('\n\n'), `${brand.dir}/${file} deve terminar com exatamente uma newline`)
        }
    }
})

test('paridade byte a byte: memoria, serializacao, fixtures e CLI', () => {
    const { root, packages } = stageCliRoot()
    const run = runCli(root, ['--packages-dir', packages, '--output-dir', 'out', '--json'])
    assert.equal(run.status, 0, `CLI falhou: ${run.stderr}`)
    assert.equal(run.stderr, '')

    for (const brand of brands) {
        const executionPackage = readPackage(brand.packageFile)
        const plan = planOf(executionPackage)
        const memory = runSimulatedExecution(plan)
        const files = buildSimulatedExecutionFiles({ plan, report: memory.report, artifacts: memory.artifacts })
        const fixtureDir = path.join(fixturesRoot, brand.dir)
        const cliDir = path.join(root, 'out', brand.executionId)

        for (const file of executionFiles) {
            const fixtureBytes = readFileSync(path.join(fixtureDir, file), 'utf8')
            const memoryBytes = files.get(file)
            assert.ok(memoryBytes !== undefined, `arquivo ausente na memoria: ${file}`)
            assert.equal(memoryBytes, fixtureBytes, `memoria difere da fixture: ${brand.dir}/${file}`)
            const cliBytes = readFileSync(path.join(cliDir, file), 'utf8')
            assert.equal(cliBytes, fixtureBytes, `CLI difere da fixture: ${brand.dir}/${file}`)
            assert.equal(sha256(cliBytes), sha256(fixtureBytes))
        }

        assert.equal(serializeSimulatedExecutionPlan(plan), files.get('execution-plan.json'))
        assert.equal(serializeSimulatedExecutionReport(memory.report), files.get('execution-report.json'))
        assert.equal(serializeSimulatedExecutionEvents(memory.report.events), files.get('events.json'))
    }
})

test('fixtures passam pelos schemas draft-07 e pela validacao semantica', () => {
    for (const brand of brands) {
        const dir = path.join(fixturesRoot, brand.dir)
        const plan = JSON.parse(readFileSync(path.join(dir, 'execution-plan.json'), 'utf8')) as unknown
        const report = JSON.parse(readFileSync(path.join(dir, 'execution-report.json'), 'utf8')) as unknown
        assert.equal(planSchemaCheck(plan), true, `schema rejeitou plano ${brand.dir}`)
        assert.equal(reportSchemaCheck(report), true, `schema rejeitou relatorio ${brand.dir}`)
        assert.equal(validateSimulatedExecutionReport(report).valid, true)

        const hashes = JSON.parse(readFileSync(path.join(dir, 'hashes.json'), 'utf8')) as Record<string, string>
        for (const [relativePath, digest] of Object.entries(hashes)) {
            assert.equal(sha256(readFileSync(path.join(dir, relativePath), 'utf8')), digest)
        }
    }
})

test('reexecucao da CLI multicase produz zero diff nos bytes', () => {
    const { root, packages } = stageCliRoot()
    const first = runCli(root, ['--packages-dir', packages, '--output-dir', 'out', '--json'])
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const snapshot = listFilesRecursive(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')] as const)
    const second = runCli(root, ['--packages-dir', packages, '--output-dir', 'out', '--json'])
    assert.equal(second.status, 0)
    const again = listFilesRecursive(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')] as const)
    assert.deepEqual(again, snapshot)
    assert.equal(first.stdout, second.stdout)
})

test('retomada ponta a ponta: falha, retomada e artefatos identicos aos da fixture', () => {
    const { root, packages } = stageCliRoot()
    const brand = brands[0]
    const packagePath = path.join(packages, brand.packageFile)
    const failed = runCli(root, ['--package', packagePath, '--output-dir', 'out', '--fail-step', 'demonstration-body-apply-text', '--json'])
    assert.equal(failed.status, 1)
    const outDir = path.join(root, 'out')
    const resumed = runCli(root, ['--package', packagePath, '--output-dir', 'out', '--resume-from', path.join(outDir, 'execution-report.json'), '--json'])
    assert.equal(resumed.status, 0, `retomada falhou: ${resumed.stderr}`)

    const report = JSON.parse(readFileSync(path.join(outDir, 'execution-report.json'), 'utf8')) as { status: string; resumedFromStatus: string }
    assert.equal(report.status, 'completed')
    assert.equal(report.resumedFromStatus, 'failed')

    for (const file of executionFiles) {
        if (file === 'execution-report.json' || file === 'events.json' || file === 'hashes.json') continue
        assert.equal(
            readFileSync(path.join(outDir, file), 'utf8'),
            readFileSync(path.join(fixturesRoot, brand.dir, file), 'utf8'),
            `artefato/plano diverge da fixture apos retomada: ${file}`,
        )
    }
})

test('prova transacional: pacote invalido e falha de promocao preservam a saida anterior', () => {
    const { root, packages } = stageCliRoot()
    const brand = brands[1]
    const packagePath = path.join(packages, brand.packageFile)
    const first = runCli(root, ['--package', packagePath, '--output-dir', 'out'])
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const hashesBefore = listFilesRecursive(outDir).map((file) => [file, sha256(readFileSync(path.join(outDir, file), 'utf8'))] as const)

    // Pacote invalido: exit 3, nenhum byte alterado.
    writeFileSync(packagePath, '{"invalido":true}\n', 'utf8')
    const invalid = runCli(root, ['--package', packagePath, '--output-dir', 'out'])
    assert.equal(invalid.status, 3)
    const afterInvalid = listFilesRecursive(outDir).map((file) => [file, sha256(readFileSync(path.join(outDir, file), 'utf8'))] as const)
    assert.deepEqual(afterInvalid, hashesBefore)

    // Falha de promocao: alvo vira diretorio; exit 4, saida anterior preservada.
    cpSync(path.join(packagesDir, brand.packageFile), packagePath)
    rmSync(path.join(outDir, 'events.json'))
    mkdirSync(path.join(outDir, 'events.json'))
    const promoteFail = runCli(root, ['--package', packagePath, '--output-dir', 'out'])
    assert.equal(promoteFail.status, 4)
    assert.ok(!existsSync(path.join(outDir, '.staging-simulated-execution')))
    for (const [file, digest] of hashesBefore) {
        if (file === 'events.json') continue
        assert.equal(sha256(readFileSync(path.join(outDir, file), 'utf8')), digest, `hash alterado: ${file}`)
    }
})
