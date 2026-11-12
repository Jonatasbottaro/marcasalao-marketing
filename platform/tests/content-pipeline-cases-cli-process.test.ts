/**
 * Testes de processo da CLI multiprojeto de casos (`content:validate-cases`).
 *
 * Executa sobre o binario compilado em dist/src/content-pipeline-cases-cli.js:
 * modo --case (com e sem --root), modo --cases-root, paridade com a funcao em
 * memoria, exit codes (0, 1, 2), isolamento de stdout e stderr, erros de sintaxe
 * de flags, descoberta vazia, confinamento e ausencia de stack trace ou caminho
 * absoluto da maquina nas mensagens de erro.
 */

import assert from 'node:assert/strict'
import { spawnSync, type SpawnSyncReturns } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, before, test } from 'node:test'

import { moduleRoot } from './contract-harness.js'
import {
    discoverCaseManifests,
    validateContentPipelineCaseFromDisk,
} from '../src/content-pipeline-case-loader.js'
import { aggregateContentPipelineCases } from '../src/validate-content-pipeline-case.js'

const cliPath = path.join(moduleRoot, 'dist', 'src', 'content-pipeline-cases-cli.js')
const examplesRoot = path.join(moduleRoot, 'examples')
const multitrackManifest = 'examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json'
const marcaManifest = 'examples/pipelines/marca-salao-pipeline-pilot.pipeline.json'

function runCli(args: readonly string[]): SpawnSyncReturns<string> {
    return spawnSync(process.execPath, [cliPath, ...args], {
        cwd: moduleRoot,
        encoding: 'utf8',
    })
}

let tempDir: string

before(() => {
    assert.ok(existsSync(cliPath), `CLI compilada nao encontrada em ${cliPath}; execute build`)
    tempDir = mkdtempSync(path.join(os.tmpdir(), 'pipeline-cases-cli-test-'))
})

after(() => {
    if (tempDir && existsSync(tempDir)) {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

/** Cria um caso minimo em disco sob tempDir e devolve manifesto e raiz. */
function stageCase(name: string, manifestOverrides: Record<string, unknown> = {}): { manifestPath: string; root: string } {
    const root = path.join(tempDir, name)
    const caseDir = path.join(root, 'case')
    mkdirSync(path.join(root, 'projects'), { recursive: true })
    mkdirSync(path.join(root, 'compositions'), { recursive: true })
    mkdirSync(path.join(root, 'output-plans'), { recursive: true })
    mkdirSync(caseDir, { recursive: true })
    writeFileSync(path.join(root, 'projects', 'projeto.json'), '{"kind":"project"}\n', 'utf8')
    writeFileSync(path.join(root, 'compositions', 'composicao.json'), '{"kind":"composition"}\n', 'utf8')
    writeFileSync(path.join(root, 'output-plans', 'plano.json'), '{"kind":"outputPlan"}\n', 'utf8')
    writeFileSync(path.join(caseDir, 'plano-beats.json'), '{"kind":"beatPlan"}\n', 'utf8')
    const manifest = {
        schemaVersion: 1,
        id: `caso-${name}`,
        project: '../projects/projeto.json',
        composition: '../compositions/composicao.json',
        outputPlan: '../output-plans/plano.json',
        beatPlan: './plano-beats.json',
        ...manifestOverrides,
    }
    const manifestPath = path.join(caseDir, 'caso.pipeline.json')
    writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
    return { manifestPath, root }
}

test('CLI --case valido com --root: exit 0 e saida humana no stdout', () => {
    const result = runCli(['--case', multitrackManifest, '--root', 'examples'])
    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    assert.match(result.stdout, /Pipeline case is valid\./)
})

test('CLI --case --json: paridade exata com a funcao em memoria', () => {
    const result = runCli(['--case', multitrackManifest, '--root', 'examples', '--json'])
    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; caseId: string }
    assert.equal(parsed.valid, true)
    assert.equal(parsed.caseId, 'multitrack-hub-pipeline-pilot')

    const memory = validateContentPipelineCaseFromDisk(path.join(moduleRoot, multitrackManifest), examplesRoot)
    assert.deepEqual(parsed, memory)
})

test('CLI --case sem --root usa o diretorio do manifesto e confine estrito', () => {
    // O manifesto referencia ../projects: sem --root, a raiz padrao e o proprio
    // diretorio do manifesto e o escape para o diretorio pai deve ser rejeitado.
    const result = runCli(['--case', multitrackManifest, '--json'])
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { status: string; manifestReport: { errors: Array<{ code: string }> } }
    assert.equal(parsed.status, 'manifest-invalid')
    assert.ok(parsed.manifestReport.errors.some((item) => item.code === 'CASE_DOCUMENT_PATH_ESCAPE'))
})

test('CLI --cases-root examples: dois consumidores validos, paridade com a memoria', () => {
    const result = runCli(['--cases-root', 'examples', '--json'])
    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as {
        valid: boolean
        caseCount: number
        validCount: number
        cases: Array<{ caseId: string; status: string }>
    }
    assert.equal(parsed.valid, true)
    assert.equal(parsed.caseCount, 2)
    assert.equal(parsed.validCount, 2)
    assert.deepEqual(parsed.cases.map((item) => item.caseId), [
        'marca-salao-pipeline-pilot',
        'multitrack-hub-pipeline-pilot',
    ])

    const discovery = discoverCaseManifests(examplesRoot)
    assert.equal(discovery.ok, true)
    if (!discovery.ok) return
    const memory = aggregateContentPipelineCases(
        discovery.paths.map((manifestPath) => validateContentPipelineCaseFromDisk(manifestPath, examplesRoot)),
    )
    assert.deepEqual(parsed, memory)
})

test('CLI --cases-root em modo humano lista os dois casos pelo id', () => {
    const result = runCli(['--cases-root', 'examples'])
    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    assert.match(result.stdout, /All pipeline cases are valid\./)
    assert.match(result.stdout, /marca-salao-pipeline-pilot: valid/)
    assert.match(result.stdout, /multitrack-hub-pipeline-pilot: valid/)
})

test('CLI --case com documento invalido de dominio: exit 1 com relatorio no stdout', () => {
    const { manifestPath, root } = stageCase('dominio')
    writeFileSync(path.join(root, 'projects', 'projeto.json'), '{"invalido":true}\n', 'utf8')
    const result = runCli(['--case', manifestPath, '--root', root, '--json'])
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { status: string; pipeline: { valid: boolean } | null }
    assert.equal(parsed.status, 'invalid')
    assert.equal(parsed.pipeline?.valid, false)
})

test('CLI --case com manifesto estruturalmente invalido: exit 1 manifest-invalid', () => {
    const { manifestPath, root } = stageCase('estrutura', { schemaVersion: 9 })
    const result = runCli(['--case', manifestPath, '--root', root, '--json'])
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { status: string }
    assert.equal(parsed.status, 'manifest-invalid')
})

test('CLI --case com manifesto ausente: exit 2, stdout vazio, stderr sanitizado', () => {
    const result = runCli(['--case', 'nao-existe.pipeline.json'])
    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /manifest/)
    assert.doesNotMatch(result.stderr, /at Object\./)
    assert.doesNotMatch(result.stderr, /Error:/)
})

test('CLI --case com manifesto malformado: exit 2, stdout vazio', () => {
    const malformedPath = path.join(tempDir, 'malformado.pipeline.json')
    writeFileSync(malformedPath, '{ nao e json', 'utf8')
    const result = runCli(['--case', malformedPath, '--json'])
    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.doesNotMatch(result.stderr, /SyntaxError:/)
})

test('CLI --case com documento ilegivel: exit 2, stdout vazio, stderr sanitizado', () => {
    const { manifestPath, root } = stageCase('ilegivel')
    rmSync(path.join(root, 'projects', 'projeto.json'))
    const result = runCli(['--case', manifestPath, '--root', root, '--json'])
    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /ilegivel/)
    assert.match(result.stderr, /project document/)
    assert.doesNotMatch(result.stderr, / at /)
})

test('CLI --cases-root com diretorio vazio: exit 2 e diagnostico em stderr', () => {
    const emptyDir = path.join(tempDir, 'vazio')
    mkdirSync(emptyDir, { recursive: true })
    const result = runCli(['--cases-root', emptyDir])
    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /nenhum manifesto \*\.pipeline\.json/)
})

test('CLI --cases-root inexistente: exit 2 e diagnostico em stderr', () => {
    const result = runCli(['--cases-root', path.join(tempDir, 'nao-existe')])
    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /cases root/)
})

test('CLI --cases-root com casos rejeitados: exit 1 com contagens e sem excecao', () => {
    const root = path.join(tempDir, 'misto')
    // Dois casos autocontidos: um com documentos invalidos de dominio e outro
    // com manifesto estruturalmente invalido. Ambos sao rejeitados sem excecao.
    for (const [name, overrides] of [['bom', {}], ['ruim', { schemaVersion: 9 }]] as const) {
        const caseDir = path.join(root, name)
        mkdirSync(caseDir, { recursive: true })
        writeFileSync(path.join(caseDir, 'projeto.json'), '{"invalido":true}\n', 'utf8')
        writeFileSync(path.join(caseDir, 'composicao.json'), '{"invalido":true}\n', 'utf8')
        writeFileSync(path.join(caseDir, 'plano.json'), '{"invalido":true}\n', 'utf8')
        writeFileSync(path.join(caseDir, 'plano-beats.json'), '{"invalido":true}\n', 'utf8')
        const manifest = {
            schemaVersion: 1,
            id: `caso-misto-${name}`,
            project: './projeto.json',
            composition: './composicao.json',
            outputPlan: './plano.json',
            beatPlan: './plano-beats.json',
            ...overrides,
        }
        writeFileSync(path.join(caseDir, 'caso.pipeline.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
    }
    const result = runCli(['--cases-root', root, '--json'])
    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; caseCount: number; invalidCount: number; cases: Array<{ status: string }> }
    assert.equal(parsed.valid, false)
    assert.equal(parsed.caseCount, 2)
    assert.equal(parsed.invalidCount, 2)
    assert.deepEqual(parsed.cases.map((item) => item.status), ['invalid', 'manifest-invalid'])
})

test('CLI com os dois modos, nenhum modo ou --root solto: exit 2', () => {
    for (const args of [
        ['--case', multitrackManifest, '--cases-root', 'examples'],
        [],
        ['--root', 'examples'],
    ]) {
        const result = runCli(args)
        assert.equal(result.status, 2, JSON.stringify(args))
        assert.equal(result.stdout, '')
        assert.match(result.stderr, /Erro de uso/)
    }
})

test('CLI com flag desconhecida, duplicada, sem flag ou sem valor: exit 2', () => {
    const cases: string[][] = [
        ['--flag-estranha', 'valor'],
        ['--case', multitrackManifest, '--case', marcaManifest],
        ['argumento-sem-flag'],
        ['--case'],
        ['--cases-root'],
    ]
    for (const args of cases) {
        const result = runCli(args)
        assert.equal(result.status, 2, JSON.stringify(args))
        assert.equal(result.stdout, '')
        assert.ok(result.stderr.length > 0)
        assert.doesNotMatch(result.stderr, / at /)
    }
})

test('CLI e deterministica: duas execucoes produzem stdout byte a byte igual', () => {
    const first = runCli(['--cases-root', 'examples', '--json'])
    const second = runCli(['--cases-root', 'examples', '--json'])
    assert.equal(first.status, 0)
    assert.equal(second.status, 0)
    assert.equal(first.stdout, second.stdout)
})
