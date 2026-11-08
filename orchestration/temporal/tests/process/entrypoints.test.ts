/**
 * Pontos de entrada do piloto como processos reais.
 *
 * O que importa aqui e o comportamento observavel de fora: uma recusa de
 * argumento sai antes de qualquer conexao, o codigo de saida distingue sucesso
 * de falha e importar o modulo do worker nao liga um poller. Nada neste arquivo
 * fala com servidor: todas as execucoes sao recusadas na parse.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const builtSrc = fileURLToPath(new URL('../../../dist/src', import.meta.url))

function run(entry: string, argv: readonly string[]) {
    const result = spawnSync(process.execPath, [path.join(builtSrc, entry), ...argv], { encoding: 'utf8', timeout: 30000 })

    assert.equal(result.error, undefined, `o processo ${entry} nao abriu: ${result.error?.message}`)
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

function assertCleanRefusal(outcome: { status: number | null; stdout: string; stderr: string }) {
    assert.equal(outcome.status, 1)
    assert.equal(outcome.stdout, '')
    assert.ok(!outcome.stderr.includes('    at '), `a recusa virou stack trace: ${outcome.stderr}`)
}

test('o worker recusa flag desconhecida sem conectar nada', () => {
    const outcome = run('worker/main.js', ['--namespace', 'default'])

    assertCleanRefusal(outcome)
    assert.match(outcome.stderr, /--address/)
})

test('o worker recusa endereco que nao e localhost', () => {
    for (const argv of [['--address', 'temporal.example.com:443'], ['--address', '10.0.0.5:7233'], ['--address', 'localhost'], ['--address', 'localhost:0']]) {
        const outcome = run('worker/main.js', argv)

        assertCleanRefusal(outcome)
        assert.match(outcome.stderr, /localhost|porta|forma/)
    }
})

test('o cliente recusa endereco remoto e entrada fora do contrato antes de conectar', () => {
    const remoto = run('client/main.js', ['--address', 'nao-local.example:7233'])
    assertCleanRefusal(remoto)
    assert.match(remoto.stderr, /localhost/)

    const contrato = run('client/main.js', ['--request-id', 'REQ-1'])
    assertCleanRefusal(contrato)
    assert.match(contrato.stderr, /contrato/)
    assert.match(contrato.stderr, /TEMPORAL_PILOT_INPUT_INVALID/)
})

test('a execucao local recusa --address sem subir servidor efemero', () => {
    const outcome = run('local/main.js', ['--address', 'localhost:7233'])

    assertCleanRefusal(outcome)
    assert.match(outcome.stderr, /--address/)
})

test('a execucao local recusa flag desconhecida e valor invalido', () => {
    for (const argv of [['--namespace', 'default'], ['--request-id'], ['--label', 'x'.repeat(60)]]) {
        const outcome = run('local/main.js', argv)

        assertCleanRefusal(outcome)
    }
})

test('importar o modulo do worker nao inicia poller nem conexao', () => {
    const moduleUrl = pathToFileURL(path.join(builtSrc, 'worker/main.js')).href
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', `await import(${JSON.stringify(moduleUrl)})`], { encoding: 'utf8', timeout: 30000 })

    assert.equal(result.error, undefined, `o import nao terminou sozinho: ${result.error?.message}`)
    assert.equal(result.status, 0)
    assert.equal(result.stdout, '')
    assert.equal(result.stderr, '')
})

test('importar o modulo do cliente nao inicia nada', () => {
    const moduleUrl = pathToFileURL(path.join(builtSrc, 'client/main.js')).href
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', `await import(${JSON.stringify(moduleUrl)})`], { encoding: 'utf8', timeout: 30000 })

    assert.equal(result.error, undefined, `o import nao terminou sozinho: ${result.error?.message}`)
    assert.equal(result.status, 0)
})
