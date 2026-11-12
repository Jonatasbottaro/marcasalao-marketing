/**
 * Pontos de entrada da execucao local de TEMPORAL-02 como processos reais.
 *
 * Todas as recusas acontecem antes de qualquer conexao (offline). Comprova
 * exit codes, stdout/stderr separados, zero stack, zero payload e que importar
 * o modulo do worker nao deixa handle ativo. O comportamento de sinais e
 * exercitado em processo filho isolado (emit seguro, sem matar o runner).
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const builtSrc = fileURLToPath(new URL('../../../dist/src', import.meta.url))
const repositoryRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../..')

function run(entry: string, argv: readonly string[]) {
    const result = spawnSync(process.execPath, [path.join(builtSrc, entry), ...argv], { encoding: 'utf8', timeout: 30000 })
    assert.equal(result.error, undefined, `o processo ${entry} nao abriu: ${result.error?.message}`)
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

function assertCleanRefusal(outcome: { status: number | null; stdout: string; stderr: string }, status: number) {
    assert.equal(outcome.status, status)
    assert.equal(outcome.stdout, '')
    assert.ok(!outcome.stderr.includes('    at '), `a recusa virou stack trace: ${outcome.stderr}`)
}

const projectExample = path.join(repositoryRoot, 'platform/examples/projects/marca-salao.project.json')
const compositionExample = path.join(repositoryRoot, 'platform/examples/compositions/marca-salao-pilot.composition.json')

test('o worker de composition recusa flag desconhecida sem conectar nada', () => {
    const outcome = run('worker/composition-validation-main.js', ['--queue', 'x'])
    assertCleanRefusal(outcome, 2)
    assert.match(outcome.stderr, /--address/)
})

test('o worker de composition recusa endereco remoto antes de conectar', () => {
    const outcome = run('worker/composition-validation-main.js', ['--address', 'temporal.example.com:443'])
    assert.equal(outcome.status, 1)
    assert.equal(outcome.stdout, '')
    assert.match(outcome.stderr, /localhost/)
    assert.ok(!outcome.stderr.includes('    at '))
})

test('o cliente de composition exige as flags obrigatorias', () => {
    const outcome = run('client/composition-validation-main.js', ['--project', projectExample])
    assertCleanRefusal(outcome, 2)
    assert.match(outcome.stderr, /obrigatoria/)
})

test('o cliente de composition recusa arquivo ausente e JSON malformado', () => {
    const missing = run('client/composition-validation-main.js', [
        '--project', path.join(os.tmpdir(), 'nao-existe-project.json'),
        '--composition', compositionExample,
        '--request-id', 'req-proc-0001',
    ])
    assertCleanRefusal(missing, 2)
    assert.match(missing.stderr, /ler o arquivo/)

    const base = mkdtempSync(path.join(os.tmpdir(), 'comp-val-cli-'))
    try {
        const badJson = path.join(base, 'bad.json')
        writeFileSync(badJson, '{isto nao e json', 'utf8')
        const malformed = run('client/composition-validation-main.js', [
            '--project', badJson,
            '--composition', compositionExample,
            '--request-id', 'req-proc-0001',
        ])
        assertCleanRefusal(malformed, 2)
        assert.match(malformed.stderr, /JSON valido/)
    } finally {
        rmSync(base, { recursive: true, force: true })
    }
})

test('o cliente de composition recusa requestId invalido no preflight sem conectar', () => {
    const outcome = run('client/composition-validation-main.js', [
        '--project', projectExample,
        '--composition', compositionExample,
        '--request-id', 'REQ-INVALIDO',
    ])
    assertCleanRefusal(outcome, 2)
    assert.match(outcome.stderr, /TEMPORAL_COMPOSITION_INPUT_INVALID/)
})

test('o cliente de composition recusa endereco remoto antes de conectar', () => {
    const outcome = run('client/composition-validation-main.js', [
        '--project', projectExample,
        '--composition', compositionExample,
        '--request-id', 'req-proc-0001',
        '--address', 'nao-local.example:7233',
    ])
    assertCleanRefusal(outcome, 2)
    assert.match(outcome.stderr, /localhost/)
})

test('a execucao local recusa argumentos sem subir servidor efemero', () => {
    const outcome = run('local/composition-validation-main.js', ['--address', 'localhost:7233'])
    assertCleanRefusal(outcome, 2)
})

test('importar o modulo do worker de composition nao deixa handle ativo', () => {
    const workerUrl = pathToFileURL(path.join(builtSrc, 'worker/composition-validation-worker.js')).href
    const result = spawnSync(
        process.execPath,
        ['--input-type=module', '-e', `await import(${JSON.stringify(workerUrl)}); process.stdout.write('imported');`],
        { encoding: 'utf8', timeout: 30000 },
    )
    assert.equal(result.error, undefined)
    assert.equal(result.status, 0)
    assert.equal(result.stdout, 'imported')
})

test('handlers de SIGINT/SIGTERM pedem shutdown e dispose remove os listeners', () => {
    const lifecycleUrl = pathToFileURL(
        path.join(builtSrc, 'worker/composition-validation-worker-lifecycle.js'),
    ).href
    const script = `
import { attachWorkerShutdownSignals } from ${JSON.stringify(lifecycleUrl)};
let shutdowns = 0;
const fakeWorker = { shutdown: () => { shutdowns += 1; } };
const handle = attachWorkerShutdownSignals(fakeWorker);
process.emit('SIGINT');
process.emit('SIGTERM');
const during = shutdowns;
handle.dispose();
process.emit('SIGINT');
process.stdout.write(JSON.stringify({ during, after: shutdowns }));
`
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', script], { encoding: 'utf8', timeout: 30000 })
    assert.equal(result.error, undefined)
    assert.equal(result.status, 0)
    assert.deepEqual(JSON.parse(result.stdout), { during: 2, after: 2 })
})