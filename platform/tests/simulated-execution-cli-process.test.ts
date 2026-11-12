/**
 * Testes de processo da CLI do executor local simulado
 * (`content:simulate-execution`) sobre o binario compilado em dist/.
 *
 * Cobre: pacote unico, multicase, falha controlada, cancelamento, retomada,
 * pacote invalido, paths externos/symlink, preservacao da saida anterior,
 * falha de promocao, exit codes 0-5, stdout/stderr, zero stack e zero
 * caminho absoluto da maquina.
 */

import assert from 'node:assert/strict'
import { spawnSync, type SpawnSyncReturns } from 'node:child_process'
import {
    cpSync,
    existsSync,
    mkdirSync,
    mkdtempSync,
    readFileSync,
    readdirSync,
    rmSync,
    symlinkSync,
    writeFileSync,
} from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, before, test } from 'node:test'

import { moduleRoot } from './contract-harness.js'

const cliPath = path.join(moduleRoot, 'dist', 'src', 'simulated-execution-cli.js')
const packagesFixtureDir = path.join(moduleRoot, 'examples', 'execution-packages')

const marcaFileName = 'execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json'
const multitrackFileName = 'execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json'
const marcaExecutionId = 'simulation-execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan'
const multitrackExecutionId = 'simulation-execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan'

function runCli(args: readonly string[], cwd: string, withRoot = true): SpawnSyncReturns<string> {
    const rootArgs = withRoot ? ['--root', cwd] : []
    return spawnSync(process.execPath, [cliPath, ...args, ...rootArgs], { cwd, encoding: 'utf8' })
}

let tempDir: string

before(() => {
    assert.ok(existsSync(cliPath), `CLI compilada nao encontrada em ${cliPath}; execute build`)
    tempDir = mkdtempSync(path.join(os.tmpdir(), 'simulated-execution-cli-test-'))
})

after(() => {
    if (tempDir && existsSync(tempDir)) {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

/** Raiz autocontida com copia dos pacotes canonicos. */
function stageRoot(name: string): { root: string; packagesDir: string; marcaPath: string } {
    const root = path.join(tempDir, name)
    const packagesDir = path.join(root, 'packages')
    mkdirSync(packagesDir, { recursive: true })
    cpSync(packagesFixtureDir, packagesDir, { recursive: true })
    return { root, packagesDir, marcaPath: path.join(packagesDir, marcaFileName) }
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

test('CLI pacote unico: exit 0, arquivos completos, stdout somente relatorio', () => {
    const { root, marcaPath } = stageRoot('unico')
    const result = runCli(['--package', marcaPath, '--output-dir', 'out', '--json'], root)
    assert.equal(result.status, 0, `stderr: ${result.stderr}`)
    assert.equal(result.stderr, '')
    const report = JSON.parse(result.stdout) as { valid: boolean; completedCount: number; executions: Array<{ status: string; executionId: string }> }
    assert.equal(report.valid, true)
    assert.equal(report.completedCount, 1)
    assert.equal(report.executions[0]?.executionId, marcaExecutionId)

    const outDir = path.join(root, 'out')
    assert.deepEqual(listFilesRecursive(outDir), [
        'artifacts/captions.txt',
        'artifacts/execution-summary.txt',
        'artifacts/narration-script.txt',
        'artifacts/primary-output.manifest.json',
        'events.json',
        'execution-plan.json',
        'execution-report.json',
        'hashes.json',
    ])
    const executionReport = JSON.parse(readFileSync(path.join(outDir, 'execution-report.json'), 'utf8')) as { status: string }
    assert.equal(executionReport.status, 'completed')
})

test('CLI multicase: dois pacotes em diretorios separados por executionId', () => {
    const { root, packagesDir } = stageRoot('multi')
    const result = runCli(['--packages-dir', packagesDir, '--output-dir', 'out', '--json'], root)
    assert.equal(result.status, 0, `stderr: ${result.stderr}`)
    assert.equal(result.stderr, '')
    const report = JSON.parse(result.stdout) as { valid: boolean; packageCount: number; completedCount: number; executions: Array<{ executionId: string }> }
    assert.equal(report.valid, true)
    assert.equal(report.packageCount, 2)
    assert.equal(report.completedCount, 2)
    assert.deepEqual(report.executions.map((execution) => execution.executionId), [marcaExecutionId, multitrackExecutionId])
    assert.ok(existsSync(path.join(root, 'out', marcaExecutionId, 'execution-report.json')))
    assert.ok(existsSync(path.join(root, 'out', multitrackExecutionId, 'execution-report.json')))
})

test('CLI falha controlada: exit 1 com status failed e failureCode', () => {
    const { root, marcaPath } = stageRoot('falha')
    const result = runCli(['--package', marcaPath, '--output-dir', 'out', '--fail-step', 'demonstration-body-apply-text', '--json'], root)
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const report = JSON.parse(result.stdout) as { valid: boolean; failedCount: number; executions: Array<{ status: string; failureCode: string | null }> }
    assert.equal(report.valid, false)
    assert.equal(report.failedCount, 1)
    assert.equal(report.executions[0]?.status, 'failed')
    assert.equal(report.executions[0]?.failureCode, 'SIMULATED_STEP_FAILURE')
    const executionReport = JSON.parse(readFileSync(path.join(root, 'out', 'execution-report.json'), 'utf8')) as { failedStepId: string }
    assert.equal(executionReport.failedStepId, 'demonstration-body-apply-text')
})

test('CLI cancelamento: exit 1 com status cancelled sem failureCode', () => {
    const { root, marcaPath } = stageRoot('cancela')
    const result = runCli(['--package', marcaPath, '--output-dir', 'out', '--cancel-after', '4', '--json'], root)
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const report = JSON.parse(result.stdout) as { executions: Array<{ status: string; failureCode: string | null }> }
    assert.equal(report.executions[0]?.status, 'cancelled')
    assert.equal(report.executions[0]?.failureCode, null)
})

test('CLI retomada: failed -> completed com resumedFromStatus e hashes preservados', () => {
    const { root, marcaPath } = stageRoot('retoma')
    const failedStep = 'demonstration-body-apply-text'
    const first = runCli(['--package', marcaPath, '--output-dir', 'out', '--fail-step', failedStep, '--json'], root)
    assert.equal(first.status, 1)
    const outDir = path.join(root, 'out')
    const priorReportPath = path.join(outDir, 'execution-report.json')
    const priorHashes = readFileSync(path.join(outDir, 'hashes.json'), 'utf8')

    const second = runCli(['--package', marcaPath, '--output-dir', 'out', '--resume-from', priorReportPath, '--json'], root)
    assert.equal(second.status, 0, `stderr: ${second.stderr}`)
    const report = JSON.parse(second.stdout) as { valid: boolean; executions: Array<{ status: string; report: { resumedFromStatus: string } }> }
    assert.equal(report.valid, true)
    assert.equal(report.executions[0]?.report.resumedFromStatus, 'failed')

    const finalReport = JSON.parse(readFileSync(priorReportPath, 'utf8')) as { status: string; completedSteps: string[] }
    assert.equal(finalReport.status, 'completed')
    assert.equal(finalReport.completedSteps.length, 12)
    // Artefatos concluidos anteriormente mantem os mesmos hashes.
    const priorHashEntries = Object.entries(JSON.parse(priorHashes) as Record<string, string>)
    const newHashes = JSON.parse(readFileSync(path.join(outDir, 'hashes.json'), 'utf8')) as Record<string, string>
    for (const [file, digest] of priorHashEntries) {
        if (file === 'execution-report.json' || file === 'events.json' || file === 'hashes.json') continue
        assert.equal(newHashes[file], digest, `hash divergente apos retomada: ${file}`)
    }
})

test('CLI retomada incompativel: exit 5 a partir de relatorio completed', () => {
    const { root, marcaPath } = stageRoot('retoma-completed')
    const first = runCli(['--package', marcaPath, '--output-dir', 'out'], root)
    assert.equal(first.status, 0)
    const second = runCli(['--package', marcaPath, '--output-dir', 'out', '--resume-from', path.join(root, 'out', 'execution-report.json')], root)
    assert.equal(second.status, 5)
    assert.equal(second.stdout, '')
    assert.match(second.stderr, /retomada incompativel: STATUS_NOT_RESUMABLE/)
})

test('CLI pacote invalido: exit 3 sem escrita; JSON malformado: exit 2', () => {
    const { root, packagesDir } = stageRoot('invalido')
    const badPackage = path.join(packagesDir, 'ruim.execution-package.json')
    writeFileSync(badPackage, '{"invalido":true}\n', 'utf8')
    const result = runCli(['--package', badPackage, '--output-dir', 'out', '--json'], root)
    assert.equal(result.status, 3)
    assert.ok(!existsSync(path.join(root, 'out')))

    const malformed = path.join(packagesDir, 'malformado.execution-package.json')
    writeFileSync(malformed, '{ nao e json', 'utf8')
    const result2 = runCli(['--package', malformed, '--output-dir', 'out'], root)
    assert.equal(result2.status, 2)
    assert.equal(result2.stdout, '')
})

test('CLI output-dir externo, absoluto ou escape: exit 2 sem escrita', () => {
    const { root, marcaPath } = stageRoot('escape')
    for (const outputDir of ['../fora', 'out/../../fora', path.join(tempDir, 'absoluto')]) {
        const result = runCli(['--package', marcaPath, '--output-dir', outputDir], root)
        assert.equal(result.status, 2, outputDir)
        assert.equal(result.stdout, '')
    }
    assert.ok(!existsSync(path.join(tempDir, 'fora')))
    assert.ok(!existsSync(path.join(tempDir, 'absoluto')))
})

test('CLI output-dir symlink externo: exit 2', (t) => {
    const { root, marcaPath } = stageRoot('symlink')
    const outside = path.join(tempDir, 'symlink-alvo-exec')
    mkdirSync(outside, { recursive: true })
    try {
        symlinkSync(outside, path.join(root, 'out-link'), 'dir')
    } catch {
        t.skip('symlink nao suportado neste ambiente Windows')
        return
    }
    const result = runCli(['--package', marcaPath, '--output-dir', 'out-link'], root)
    assert.equal(result.status, 2)
    assert.deepEqual(readdirSync(outside), [])
})

test('CLI preserva a saida anterior quando o pacote se torna invalido', () => {
    const { root, marcaPath } = stageRoot('preserva')
    const first = runCli(['--package', marcaPath, '--output-dir', 'out'], root)
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const before = listFilesRecursive(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')] as const)

    writeFileSync(marcaPath, '{"invalido":true}\n', 'utf8')
    const second = runCli(['--package', marcaPath, '--output-dir', 'out'], root)
    assert.equal(second.status, 3)
    const after = listFilesRecursive(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')] as const)
    assert.deepEqual(after, before, 'saida anterior deve permanecer byte a byte identica')
})

test('CLI falha de promocao: exit 4 com saida anterior preservada', () => {
    const { root, marcaPath } = stageRoot('falha-escrita')
    const first = runCli(['--package', marcaPath, '--output-dir', 'out'], root)
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const reportBefore = readFileSync(path.join(outDir, 'execution-report.json'), 'utf8')

    rmSync(path.join(outDir, 'events.json'))
    mkdirSync(path.join(outDir, 'events.json'))
    const second = runCli(['--package', marcaPath, '--output-dir', 'out'], root)
    assert.equal(second.status, 4)
    assert.equal(second.stdout, '')
    assert.match(second.stderr, /saida anterior preservada/)
    assert.doesNotMatch(second.stderr, / at /)
    assert.equal(readFileSync(path.join(outDir, 'execution-report.json'), 'utf8'), reportBefore)
    assert.ok(!existsSync(path.join(outDir, '.staging-simulated-execution')))
})

test('CLI flags invalidas: exit 2 com stdout vazio', () => {
    const { root, marcaPath, packagesDir } = stageRoot('flags')
    const cases: string[][] = [
        [],
        ['--package', marcaPath],
        ['--output-dir', 'out'],
        ['--package', marcaPath, '--packages-dir', packagesDir, '--output-dir', 'out'],
        ['--package', marcaPath, '--output-dir', 'out', '--cancel-after', '0'],
        ['--package', marcaPath, '--output-dir', 'out', '--cancel-after', 'abc'],
        ['--packages-dir', packagesDir, '--output-dir', 'out', '--resume-from', 'x.json'],
        ['--package', marcaPath, '--output-dir', 'out', '--flag-estranha', 'x'],
        ['argumento-sem-flag'],
    ]
    for (const args of cases) {
        const result = runCli(args, root)
        assert.equal(result.status, 2, JSON.stringify(args))
        assert.equal(result.stdout, '')
        assert.ok(result.stderr.length > 0)
        assert.doesNotMatch(result.stderr, / at /)
    }
})

test('CLI deterministica: duas execucoes produzem bytes identicos', () => {
    const { root, marcaPath } = stageRoot('determinismo')
    const first = runCli(['--package', marcaPath, '--output-dir', 'out', '--json'], root)
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const snapshot = listFilesRecursive(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')] as const)
    const second = runCli(['--package', marcaPath, '--output-dir', 'out', '--json'], root)
    assert.equal(second.status, 0)
    const again = listFilesRecursive(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')] as const)
    assert.deepEqual(again, snapshot)
    assert.equal(first.stdout, second.stdout)
})

test('CLI sem --root usa o diretorio do pacote como raiz de confinamento', () => {
    const { root, packagesDir, marcaPath } = stageRoot('raiz-padrao')
    // cwd = diretorio do pacote: 'out' resolve dentro da raiz padrao.
    const result = runCli(['--package', marcaPath, '--output-dir', 'out'], packagesDir, false)
    assert.equal(result.status, 0, `stderr: ${result.stderr}`)
    assert.ok(existsSync(path.join(packagesDir, 'out', 'execution-report.json')))
    // cwd fora do diretorio do pacote: 'out' escapa da raiz padrao e e rejeitado.
    const rejected = runCli(['--package', marcaPath, '--output-dir', 'out'], root, false)
    assert.equal(rejected.status, 2)
})

test('CLI nao vaza caminho absoluto da maquina em stderr', () => {
    const { root, marcaPath } = stageRoot('sem-vazamento')
    const result = runCli(['--package', marcaPath, '--output-dir', '../fora'], root)
    assert.equal(result.status, 2)
    assert.ok(!result.stderr.includes(root))
    assert.ok(!result.stderr.includes(tempDir))
})
