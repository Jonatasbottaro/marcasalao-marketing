/**
 * Testes de portabilidade do build: garantem que a suite e a CLI executam sobre
 * JavaScript compilado (dist/), que o artefato nao entra no Git e que o
 * package.json sustenta Node >= 22 sem dependencias de runtime adicionais.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

const testDir = path.dirname(fileURLToPath(import.meta.url))

function findModuleRoot(startDir: string): string {
    let current = path.resolve(startDir)
    for (;;) {
        if (existsSync(path.join(current, 'package.json'))) return current
        const parent = path.dirname(current)
        if (parent === current) {
            throw new Error(`package.json do modulo nao encontrado a partir de ${startDir}`)
        }
        current = parent
    }
}

const moduleRoot = findModuleRoot(testDir)
const distDir = path.join(moduleRoot, 'dist')

test('a suite de testes executa sobre JavaScript compilado', () => {
    assert.ok(import.meta.url.endsWith('.test.js'), `esperado arquivo compilado em dist/, obtido ${import.meta.url}`)
    assert.ok(fileURLToPath(import.meta.url).includes(path.join('dist', 'tests')))
    assert.ok(existsSync(fileURLToPath(import.meta.url)))
})

test('dist e declarado como artefato ignorado pelo Git', () => {
    const gitignoreLines = readFileSync(path.join(moduleRoot, '.gitignore'), 'utf8').split(/\r?\n/)
    assert.ok(gitignoreLines.includes('dist/'), '.gitignore deve conter a linha "dist/"')
})

test('nenhum artefato compilado esta rastreado pelo Git', (t) => {
    const insideRepo = spawnSync('git', ['rev-parse', '--is-inside-work-tree'], {
        cwd: moduleRoot,
        encoding: 'utf8',
    })
    if (insideRepo.error || insideRepo.status !== 0 || insideRepo.stdout?.trim() !== 'true') {
        t.skip('fora de um repositorio Git; verificacao de rastreamento dispensada')
        return
    }

    const tracked = spawnSync('git', ['ls-files', 'dist'], { cwd: moduleRoot, encoding: 'utf8' })
    assert.equal(tracked.status, 0)
    assert.equal((tracked.stdout ?? '').trim(), '', 'dist/ nao pode conter arquivos rastreados pelo Git')
})

test('os arquivos compilados nao importam fontes TypeScript em runtime', () => {
    const importSpecifierPattern = /(?:from|import)\s*\(?\s*['"][^'"]+\.ts['"]/
    const compiledFiles = readdirSync(distDir, { recursive: true })
        .map((entry) => entry.toString())
        .filter((entry) => entry.endsWith('.js'))

    assert.ok(compiledFiles.length > 0, 'dist/ deve conter JavaScript compilado')
    for (const relativeFile of compiledFiles) {
        const content = readFileSync(path.join(distDir, relativeFile), 'utf8')
        assert.ok(
            !importSpecifierPattern.test(content),
            `import com extensao .ts encontrado em dist/${relativeFile}`,
        )
    }
})

test('package.json declara build compilado, engines Node >= 22 e zero dependencias de runtime', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        engines?: { node?: string }
        scripts?: Record<string, string>
        dependencies?: Record<string, string>
        devDependencies?: Record<string, string>
    }

    assert.match(pkg.engines?.node ?? '', />=22/)
    assert.match(pkg.scripts?.build ?? '', /\btsc\b/)
    assert.ok((pkg.scripts?.test ?? '').includes('node --test'))
    assert.ok((pkg.scripts?.test ?? '').includes('dist/tests'))
    // A suíte inteira precisa incluir tests/contracts/: o glob tem de ser recursivo.
    assert.match(pkg.scripts?.test ?? '', /dist\/tests\/\*\*\/\*\.test\.js/)
    assert.match(pkg.scripts?.['test:contracts'] ?? '', /--test-reporter=tap "dist\/tests\/contracts\/\*\.test\.js"/)
    assert.match(pkg.scripts?.['test:contracts'] ?? '', /^npm run build/, 'test:contracts roda sobre JavaScript compilado')

    // O reporter precisa vir ANTES dos padroes de arquivo: depois de um argumento
    // posicional o node --test o ignora e a saida volta a ser o reporter default
    // (que muda entre versoes do Node), perdendo o TAP integral dos logs do gate.
    for (const script of ['test', 'test:contracts'] as const) {
        const command = pkg.scripts?.[script] ?? ''
        assert.match(command, /--test --test-reporter=tap /, `${script} deve forcar TAP antes dos padroes`)
        assert.ok(
            command.indexOf('--test-reporter=tap') < command.indexOf('"dist/tests'),
            `${script}: --test-reporter=tap precisa preceder o padrao de arquivos`,
        )
    }
    assert.ok((pkg.scripts?.['content:validate-project'] ?? '').includes('node dist/src/validate-project-cli.js'))
    assert.ok((pkg.scripts?.['content:validate-composition'] ?? '').includes('node dist/src/validate-composition-cli.js'))
    assert.ok((pkg.scripts?.['content:validate-beat-plan'] ?? '').includes('node dist/src/validate-beat-plan-cli.js'))
    assert.equal(pkg.dependencies, undefined, 'nenhuma dependencia de runtime e permitida')
    assert.deepEqual(Object.keys(pkg.devDependencies ?? {}).sort(), ['@types/node', 'ajv', 'typescript'])
})
