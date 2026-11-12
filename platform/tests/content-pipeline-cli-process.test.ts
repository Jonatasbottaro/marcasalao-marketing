/**
 * Testes de processo da CLI do pipeline criativo (`content:validate-pipeline`).
 *
 * Executa sobre o binario compilado em dist/src/content-pipeline-validation-cli.js:
 * testa conjunto valido, caminhos invalidos por estagio, arquivos inexistentes,
 * JSON malformado, erros de sintaxe de flags (desconhecida, duplicada, sem flag,
 * valor ausente), exit codes (0, 1, 2), isolamento de stdout e stderr e ausencia
 * de vazamento de stack trace ou caminhos absolutos em mensagens de erro.
 */

import assert from 'node:assert/strict'
import { spawnSync, type SpawnSyncReturns } from 'node:child_process'
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, before, test } from 'node:test'

import { moduleRoot } from './contract-harness.js'

const cliPath = path.join(moduleRoot, 'dist', 'src', 'content-pipeline-validation-cli.js')

function runCli(args: readonly string[]): SpawnSyncReturns<string> {
    return spawnSync(process.execPath, [cliPath, ...args], {
        cwd: moduleRoot,
        encoding: 'utf8',
    })
}

const validProject = 'examples/projects/marca-salao-social.project.json'
const validComposition = 'examples/compositions/marca-salao-social-reel.composition.json'
const validOutputPlan = 'examples/output-plans/instagram-reels-video.output-plan.json'
const validBeatPlan = 'examples/pipelines/marca-salao-social-reel.beat-plan.json'

let tempDir: string

before(() => {
    assert.ok(existsSync(cliPath), `CLI compilada nao encontrada em ${cliPath}; execute build`)
    tempDir = path.join(os.tmpdir(), `pipeline-cli-test-${Date.now()}-${Math.random().toString(36).slice(2)}`)
    mkdirSync(tempDir, { recursive: true })
})

after(() => {
    if (tempDir && existsSync(tempDir)) {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

test('CLI com conjunto valido: exit code 0 e saida humana no stdout', () => {
    const result = runCli([
        '--project', validProject,
        '--composition', validComposition,
        '--output-plan', validOutputPlan,
        '--beat-plan', validBeatPlan,
    ])

    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    assert.match(result.stdout, /Content pipeline is valid\./)
})

test('CLI com conjunto valido em modo --json: exit code 0 e JSON valido com valid: true', () => {
    const result = runCli([
        '--project', validProject,
        '--composition', validComposition,
        '--output-plan', validOutputPlan,
        '--beat-plan', validBeatPlan,
        '--json',
    ])

    assert.equal(result.status, 0)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; summary: string }
    assert.equal(parsed.valid, true)
    assert.equal(parsed.summary, 'Content pipeline is valid.')
})

test('CLI com Project invalido: exit code 1 e diagnostico no stdout', () => {
    const invalidProjectFile = path.join(tempDir, 'invalid-project.json')
    writeFileSync(invalidProjectFile, JSON.stringify({ invalid: true }), 'utf8')

    const result = runCli([
        '--project', invalidProjectFile,
        '--composition', validComposition,
        '--output-plan', validOutputPlan,
        '--beat-plan', validBeatPlan,
        '--json',
    ])

    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; errors: Array<{ stage: string }> }
    assert.equal(parsed.valid, false)
    assert.ok(parsed.errors.some((e) => e.stage === 'project'))
})

test('CLI com Composition invalida: exit code 1', () => {
    const invalidCompFile = path.join(tempDir, 'invalid-comp.json')
    writeFileSync(invalidCompFile, JSON.stringify({ invalid: true }), 'utf8')

    const result = runCli([
        '--project', validProject,
        '--composition', invalidCompFile,
        '--output-plan', validOutputPlan,
        '--beat-plan', validBeatPlan,
        '--json',
    ])

    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; errors: Array<{ stage: string }> }
    assert.equal(parsed.valid, false)
    assert.ok(parsed.errors.some((e) => e.stage === 'composition'))
})

test('CLI com OutputPlan invalido: exit code 1', () => {
    const invalidPlanFile = path.join(tempDir, 'invalid-plan.json')
    writeFileSync(invalidPlanFile, JSON.stringify({ invalid: true }), 'utf8')

    const result = runCli([
        '--project', validProject,
        '--composition', validComposition,
        '--output-plan', invalidPlanFile,
        '--beat-plan', validBeatPlan,
        '--json',
    ])

    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; errors: Array<{ stage: string }> }
    assert.equal(parsed.valid, false)
    assert.ok(parsed.errors.some((e) => e.stage === 'output-plan'))
})

test('CLI com BeatPlan invalido: exit code 1', () => {
    const invalidBeatFile = path.join(tempDir, 'invalid-beat.json')
    writeFileSync(invalidBeatFile, JSON.stringify({ invalid: true }), 'utf8')

    const result = runCli([
        '--project', validProject,
        '--composition', validComposition,
        '--output-plan', validOutputPlan,
        '--beat-plan', invalidBeatFile,
        '--json',
    ])

    assert.equal(result.status, 1)
    assert.equal(result.stderr, '')
    const parsed = JSON.parse(result.stdout) as { valid: boolean; errors: Array<{ stage: string }> }
    assert.equal(parsed.valid, false)
    assert.ok(parsed.errors.some((e) => e.stage === 'beat-plan'))
})

test('CLI com arquivo ausente: exit code 2 e stderr com stdout vazio', () => {
    const result = runCli([
        '--project', 'nao-existe.json',
        '--composition', validComposition,
        '--output-plan', validOutputPlan,
        '--beat-plan', validBeatPlan,
    ])

    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /Erro: arquivo nao encontrado ou ilegivel/)
    assert.doesNotMatch(result.stderr, /at Object\./)
})

test('CLI com JSON malformado: exit code 2 e stderr com stdout vazio', () => {
    const malformedFile = path.join(tempDir, 'malformed.json')
    writeFileSync(malformedFile, '{ not valid json', 'utf8')

    const result = runCli([
        '--project', malformedFile,
        '--composition', validComposition,
        '--output-plan', validOutputPlan,
        '--beat-plan', validBeatPlan,
    ])

    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /Erro: JSON malformado/)
    assert.doesNotMatch(result.stderr, /SyntaxError:/)
})

test('CLI com flag desconhecida: exit code 2', () => {
    const result = runCli([
        '--flag-estranha', 'valor',
        '--project', validProject,
    ])

    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /flag desconhecida: --flag-estranha/)
})

test('CLI com flag duplicada: exit code 2', () => {
    const result = runCli([
        '--project', validProject,
        '--project', validProject,
    ])

    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /flag duplicada: --project/)
})

test('CLI com argumento sem flag: exit code 2', () => {
    const result = runCli(['argumento-sem-flag'])

    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /argumento sem flag/)
})

test('CLI com valor ausente para a flag: exit code 2', () => {
    const result = runCli(['--project'])

    assert.equal(result.status, 2)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /valor ausente para a flag: --project/)
})
