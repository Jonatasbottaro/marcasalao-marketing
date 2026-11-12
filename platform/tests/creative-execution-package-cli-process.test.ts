/**
 * Testes de processo da CLI de geracao de pacotes de execucao
 * (`content:build-execution-packages`).
 *
 * Cobre: geracao dos dois pacotes, caso invalido, manifesto invalido,
 * output-dir externo/absoluto/escape/symlink, falha de escrita, preservacao
 * da saida anterior, ausencia de arquivo parcial, stdout/stderr, exit codes
 * 0/1/2/3/4, zero stack trace e zero caminho absoluto da maquina.
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

const cliPath = path.join(moduleRoot, 'dist', 'src', 'creative-execution-package-cli.js')
const examplesRoot = path.join(moduleRoot, 'examples')

const marcaPackageId = 'execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan'
const multitrackPackageId = 'execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan'

function runCli(args: readonly string[], cwd: string): SpawnSyncReturns<string> {
    return spawnSync(process.execPath, [cliPath, ...args], { cwd, encoding: 'utf8' })
}

let tempDir: string

before(() => {
    assert.ok(existsSync(cliPath), `CLI compilada nao encontrada em ${cliPath}; execute build`)
    tempDir = mkdtempSync(path.join(os.tmpdir(), 'execution-package-cli-test-'))
})

after(() => {
    if (tempDir && existsSync(tempDir)) {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

/** Cria uma raiz autocontida com copia dos exemplos e um manifesto de casos. */
function stageRoot(name: string, caseEntries: readonly string[]): { root: string; manifestPath: string } {
    const root = path.join(tempDir, name)
    mkdirSync(root, { recursive: true })
    cpSync(examplesRoot, path.join(root, 'examples'), { recursive: true })
    const manifestPath = path.join(root, 'cases.json')
    writeFileSync(manifestPath, `${JSON.stringify({ schemaVersion: 1, id: `casos-${name}`, cases: caseEntries }, null, 2)}\n`, 'utf8')
    return { root, manifestPath }
}

const bothCases = [
    'examples/pipelines/marca-salao-pipeline-pilot.pipeline.json',
    'examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json',
]

test('CLI gera os dois pacotes: exit 0, arquivos canonicos, stdout somente relatorio', () => {
    const { root, manifestPath } = stageRoot('ok', bothCases)
    const result = runCli(['--manifest', manifestPath, '--output-dir', 'out', '--json'], root)
    assert.equal(result.status, 0, `stderr: ${result.stderr}`)
    assert.equal(result.stderr, '')
    const report = JSON.parse(result.stdout) as { valid: boolean; packageCount: number; packages: Array<{ status: string }> }
    assert.equal(report.valid, true)
    assert.equal(report.packageCount, 2)

    const outDir = path.join(root, 'out')
    assert.deepEqual(readdirSync(outDir).sort(), [
        `${marcaPackageId}.execution-package.json`,
        `${multitrackPackageId}.execution-package.json`,
    ].sort())
    for (const file of readdirSync(outDir)) {
        const content = readFileSync(path.join(outDir, file), 'utf8')
        assert.ok(!content.includes('\r'))
        assert.ok(content.endsWith('\n'))
        const parsed = JSON.parse(content) as { packageId: string }
        assert.equal(`${parsed.packageId}.execution-package.json`, file)
    }
    assert.ok(!existsSync(path.join(outDir, '.staging-execution-packages')), 'staging nao pode sobreviver ao sucesso')
})

test('CLI em modo humano lista os casos e pacotes gerados', () => {
    const { root, manifestPath } = stageRoot('humano', bothCases)
    const result = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    assert.match(result.stdout, /All execution packages were generated\./)
    assert.match(result.stdout, /marca-salao-pipeline-pilot: generated/)
    assert.match(result.stdout, /multitrack-hub-pipeline-pilot: generated/)
})

test('CLI com caso invalido: exit 1, relatorio no stdout e nenhum arquivo escrito', () => {
    const { root, manifestPath } = stageRoot('caso-invalido', [
        ...bothCases,
        'examples/pipelines/nao-existe.pipeline.json',
    ])
    const result = runCli(['--manifest', manifestPath, '--output-dir', 'out', '--json'], root)
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const report = JSON.parse(result.stdout) as { valid: boolean; failedCaseCount: number }
    assert.equal(report.valid, false)
    assert.equal(report.failedCaseCount, 1)
    assert.ok(!existsSync(path.join(root, 'out')), 'output-dir nao pode ser criado quando ha caso invalido')
})

test('CLI com manifesto malformado, incompleto ou com campo desconhecido: exit 2', () => {
    const { root } = stageRoot('manifesto-ruim', bothCases)
    const malformed = path.join(root, 'malformado.json')
    writeFileSync(malformed, '{ nao e json', 'utf8')
    const incomplete = path.join(root, 'incompleto.json')
    writeFileSync(incomplete, '{"schemaVersion":1}\n', 'utf8')
    const unknown = path.join(root, 'desconhecido.json')
    writeFileSync(unknown, '{"schemaVersion":1,"cases":["x"],"extra":true}\n', 'utf8')
    const absoluteCase = path.join(root, 'absoluto.json')
    writeFileSync(absoluteCase, `{"schemaVersion":1,"cases":["${path.join(root, 'x').replace(/\\/g, '/')}"]}\n`, 'utf8')

    for (const manifest of [malformed, incomplete, unknown, absoluteCase, path.join(root, 'nao-existe.json')]) {
        const result = runCli(['--manifest', manifest, '--output-dir', 'out'], root)
        assert.equal(result.status, 2, manifest)
        assert.equal(result.stdout, '', manifest)
        assert.ok(result.stderr.length > 0)
        assert.doesNotMatch(result.stderr, / at /)
        assert.doesNotMatch(result.stderr, /SyntaxError/)
    }
})

test('CLI com output-dir externo, escape por .. ou absoluto: exit 2 sem escrita', () => {
    const { root, manifestPath } = stageRoot('escape', bothCases)
    for (const outputDir of ['../fora', 'out/../../fora', path.join(tempDir, 'absoluto-fora')]) {
        const result = runCli(['--manifest', manifestPath, '--output-dir', outputDir], root)
        assert.equal(result.status, 2, outputDir)
        assert.equal(result.stdout, '')
        assert.match(result.stderr, /output-dir/)
    }
    assert.ok(!existsSync(path.join(tempDir, 'fora')))
    assert.ok(!existsSync(path.join(tempDir, 'absoluto-fora')))
})

test('CLI com output-dir symlink externo: exit 2', (t) => {
    const { root, manifestPath } = stageRoot('symlink', bothCases)
    const outside = path.join(tempDir, 'symlink-alvo')
    mkdirSync(outside, { recursive: true })
    try {
        symlinkSync(outside, path.join(root, 'out-link'), 'dir')
    } catch {
        t.skip('symlink nao suportado neste ambiente Windows')
        return
    }
    const result = runCli(['--manifest', manifestPath, '--output-dir', 'out-link'], root)
    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.deepEqual(readdirSync(outside), [])
})

test('CLI preserva a saida anterior quando um caso invalido entra no manifesto', () => {
    const { root, manifestPath } = stageRoot('preserva', bothCases)
    const first = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const before = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))

    writeFileSync(manifestPath, `${JSON.stringify({ schemaVersion: 1, cases: [...bothCases, 'examples/pipelines/nao-existe.pipeline.json'] }, null, 2)}\n`, 'utf8')
    const second = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(second.status, 1)
    const after = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))
    assert.deepEqual([...after.entries()], [...before.entries()], 'bytes da saida anterior devem permanecer identicos')
    assert.ok(!existsSync(path.join(outDir, '.staging-execution-packages')))
})

test('CLI com falha de promocao: exit 4, saida anterior preservada, sem arquivo parcial', () => {
    const { root, manifestPath } = stageRoot('falha-escrita', bothCases)
    const first = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const before = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))

    // Transforma um dos alvos em diretorio: o rename do staging falha e a
    // transacao precisa reverter os arquivos ja promovidos.
    const victim = `${multitrackPackageId}.execution-package.json`
    rmSync(path.join(outDir, victim))
    mkdirSync(path.join(outDir, victim))

    const second = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(second.status, 4)
    assert.equal(second.stdout, '')
    assert.match(second.stderr, /saida anterior preservada/)
    assert.doesNotMatch(second.stderr, / at /)

    // O alvo-diretorio continua diretorio (estado anterior a falha era o arquivo;
    // a garantia exercitada e: nenhum pacote parcial promovido e o outro arquivo intacto).
    const intact = `${marcaPackageId}.execution-package.json`
    assert.equal(readFileSync(path.join(outDir, intact), 'utf8'), before.get(intact))
    assert.ok(!existsSync(path.join(outDir, '.staging-execution-packages')), 'staging removido apos a falha')
})

test('CLI com flags ausentes, desconhecidas, duplicadas ou sem valor: exit 2', () => {
    const { root, manifestPath } = stageRoot('flags', bothCases)
    const cases: string[][] = [
        [],
        ['--manifest', manifestPath],
        ['--output-dir', 'out'],
        ['--manifest', manifestPath, '--output-dir', 'out', '--flag-estranha', 'x'],
        ['--manifest', manifestPath, '--manifest', manifestPath, '--output-dir', 'out'],
        ['--manifest'],
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

test('CLI e deterministica: duas execucoes produzem bytes identicos', () => {
    const { root, manifestPath } = stageRoot('determinismo', bothCases)
    const first = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(first.status, 0)
    const outDir = path.join(root, 'out')
    const snapshot = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))
    const second = runCli(['--manifest', manifestPath, '--output-dir', 'out'], root)
    assert.equal(second.status, 0)
    const again = new Map(readdirSync(outDir).map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))
    assert.deepEqual([...again.entries()], [...snapshot.entries()])
    assert.equal(first.stdout, second.stdout)
})

test('CLI nao vaza caminho absoluto da maquina em stderr', () => {
    const { root, manifestPath } = stageRoot('sem-vazamento', bothCases)
    const result = runCli(['--manifest', manifestPath, '--output-dir', '../fora'], root)
    assert.equal(result.status, 2)
    assert.ok(!result.stderr.includes(root), 'stderr nao pode conter o caminho absoluto da raiz temporaria')
    assert.ok(!result.stderr.includes(tempDir))
})
