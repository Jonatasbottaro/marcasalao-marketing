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
    assert.equal(pkg.dependencies, undefined, 'nenhuma dependencia de runtime e permitida')
    assert.deepEqual(Object.keys(pkg.devDependencies ?? {}).sort(), ['@types/node', 'ajv', 'typescript'])
})

test('os scripts das CLIs de saida rodam sobre o build silencioso', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        scripts?: Record<string, string>
    }

    const expectations: Record<string, string> = {
        'content:profiles': 'dist/src/output-profiles-cli.js',
        'content:plan-output': 'dist/src/output-plan-cli.js',
    }

    for (const [script, artifact] of Object.entries(expectations)) {
        const value = pkg.scripts?.[script] ?? ''
        assert.ok(value.includes(`node ${artifact}`), `${script} precisa executar ${artifact}`)
        // --silent no build interno: sem ele o npm imprime o header do script no
        // stdout, e o consumidor de JSON nao consegue parsear a saida.
        assert.match(value, /^npm run build --silent && /, `${script} precisa compilar antes de executar, em modo silencioso`)
        assert.ok(
            existsSync(path.join(moduleRoot, ...artifact.split('/'))),
            `${artifact} nao existe em dist/`,
        )
    }
})

test('o script content:validate-beat-plan roda sobre o build silencioso', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        scripts?: Record<string, string>
    }

    // Mesmo contrato dos scripts de saida: a CLI e JavaScript compilado em dist/
    // e o build interno precisa ser silencioso para nao sujar o stdout do relatorio.
    const value = pkg.scripts?.['content:validate-beat-plan'] ?? ''
    assert.ok(value.includes('node dist/src/validate-beat-plan-cli.js'), 'o script precisa executar a CLI do beat plan')
    assert.match(value, /^npm run build --silent && /, 'o script precisa compilar antes de executar, em modo silencioso')
    assert.ok(
        existsSync(path.join(moduleRoot, 'dist', 'src', 'validate-beat-plan-cli.js')),
        'dist/src/validate-beat-plan-cli.js nao existe em dist/',
    )
})

test('o script content:validate-pipeline roda sobre o build silencioso', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        scripts?: Record<string, string>
    }

    const value = pkg.scripts?.['content:validate-pipeline'] ?? ''
    assert.ok(value.includes('node dist/src/content-pipeline-validation-cli.js'), 'o script precisa executar a CLI do pipeline')
    assert.match(value, /^npm run build --silent && /, 'o script precisa compilar antes de executar, em modo silencioso')
    assert.ok(
        existsSync(path.join(moduleRoot, 'dist', 'src', 'content-pipeline-validation-cli.js')),
        'dist/src/content-pipeline-validation-cli.js nao existe em dist/',
    )
})

test('o script content:validate-cases roda sobre o build silencioso', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        scripts?: Record<string, string>
    }

    // Mesmo contrato dos scripts anteriores: CLI compilada em dist/ e build
    // interno silencioso para nao sujar o stdout do relatorio.
    const value = pkg.scripts?.['content:validate-cases'] ?? ''
    assert.ok(value.includes('node dist/src/content-pipeline-cases-cli.js'), 'o script precisa executar a CLI multiprojeto de casos')
    assert.match(value, /^npm run build --silent && /, 'o script precisa compilar antes de executar, em modo silencioso')
    assert.ok(
        existsSync(path.join(moduleRoot, 'dist', 'src', 'content-pipeline-cases-cli.js')),
        'dist/src/content-pipeline-cases-cli.js nao existe em dist/',
    )
})

test('o script content:build-execution-packages roda sobre o build silencioso', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        scripts?: Record<string, string>
    }

    const value = pkg.scripts?.['content:build-execution-packages'] ?? ''
    assert.ok(value.includes('node dist/src/creative-execution-package-cli.js'), 'o script precisa executar a CLI de pacotes de execucao')
    assert.match(value, /^npm run build --silent && /, 'o script precisa compilar antes de executar, em modo silencioso')
    assert.ok(
        existsSync(path.join(moduleRoot, 'dist', 'src', 'creative-execution-package-cli.js')),
        'dist/src/creative-execution-package-cli.js nao existe em dist/',
    )
})

test('o script content:simulate-execution roda sobre o build silencioso', () => {
    const pkg = JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as {
        scripts?: Record<string, string>
    }

    const value = pkg.scripts?.['content:simulate-execution'] ?? ''
    assert.ok(value.includes('node dist/src/simulated-execution-cli.js'), 'o script precisa executar a CLI do executor simulado')
    assert.match(value, /^npm run build --silent && /, 'o script precisa compilar antes de executar, em modo silencioso')
    assert.ok(
        existsSync(path.join(moduleRoot, 'dist', 'src', 'simulated-execution-cli.js')),
        'dist/src/simulated-execution-cli.js nao existe em dist/',
    )
})
