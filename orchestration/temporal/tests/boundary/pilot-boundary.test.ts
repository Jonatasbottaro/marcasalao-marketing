/**
 * Fronteira e proibicoes do piloto TEMPORAL-01, medidas no codigo-fonte.
 *
 * Os gates de tempo de execucao nao conseguem ver uma importacao errada. Estas
 * leituras estaticas fixam as duas regras que a revisao humana mais quebra: o
 * nucleo nao conhece Temporal e o Workflow nao faz efeito colateral proprio.
 */
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const pilotRoot = fileURLToPath(new URL('../../../', import.meta.url))
const platformRoot = fileURLToPath(new URL('../../../../../platform/src', import.meta.url))

function sources(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const full = path.join(dir, entry.name)
        if (entry.isDirectory()) return sources(full)
        return entry.name.endsWith('.ts') ? [full] : []
    })
}

function read(file: string): string {
    return readFileSync(file, 'utf8')
}

/** So linhas de import/export: uma prosa que cite o pacote nao e uma dependencia. */
function temporalImports(file: string): string[] {
    return read(file)
        .split(/\r?\n/)
        .filter((line) => /^\s*(import|export)\b/.test(line) && /['"]@temporalio/.test(line))
}

function coreSources(): string[] {
    return sources(path.join(pilotRoot, 'src/pilot-core'))
}

function workflowSources(): string[] {
    return sources(path.join(pilotRoot, 'src/workflows'))
}

test('o nucleo do piloto nao importa nada de @temporalio', () => {
    const files = coreSources()

    assert.ok(files.length >= 5, 'espera ao menos os cinco modulos do nucleo')
    for (const file of files) {
        assert.deepEqual(temporalImports(file), [], `${path.basename(file)} importa Temporal`)
    }
})

test('o nucleo nao conhece Workflow, Activity, Task Queue nem camadas de execucao', () => {
    const forbidden = [/from '\.\.\/workflows/, /from '\.\.\/activities/, /from '\.\.\/client/, /from '\.\.\/worker/, /from '\.\.\/local/, /taskQueue/, /ActivityOptions/]

    for (const file of coreSources()) {
        const source = read(file)
        for (const pattern of forbidden) {
            assert.ok(!pattern.test(source), `${path.basename(file)} toca a camada de execucao por ${pattern}`)
        }
    }
})

test('a plataforma continua sem nenhuma dependencia de Temporal', () => {
    const files = sources(platformRoot)

    assert.ok(files.length > 0, 'a plataforma nao foi encontrada; o teste perderia o sentido')
    for (const file of files) {
        assert.deepEqual(temporalImports(file), [], `${file} importa Temporal`)
    }
})

test('o Workflow nao toca disco, rede, relogio, aleatoriedade, ambiente, console nem timer nativo', () => {
    const forbidden = ['node:fs', 'node:net', 'node:http', 'node:https', 'node:dns', 'node:tls', 'node:child_process', 'node:crypto', 'fetch(', 'XMLHttpRequest', 'Date.now', 'Math.random', 'process.env', 'process.cwd', 'console.', 'setTimeout', 'setInterval', 'require(', '__dirname', '.env']

    for (const file of workflowSources()) {
        const source = read(file)
        for (const token of forbidden) {
            assert.ok(!source.includes(token), `${path.basename(file)} usa ${token}`)
        }
    }
})

test('o Workflow obtem as Activities por proxy e nunca as chama como funcao local', () => {
    const source = read(path.join(pilotRoot, 'src/workflows/content-pilot-workflow.ts'))

    assert.match(source, /proxyActivities</)
    assert.match(source, /import type \* as pilotActivities/, 'a Activity precisa entrar como tipo, nao como valor')
    assert.ok(!/^import \* as pilotActivities/m.test(source), 'import de valor das Activities dentro do Workflow')
    assert.ok(!/pilotActivities\./.test(source), 'chamada direta de Activity dentro do Workflow')
})

test('o nome da Task Queue do piloto existe em um unico lugar do codigo-fonte', () => {
    const hits = sources(path.join(pilotRoot, 'src')).filter((file) => read(file).includes('marketing-temporal-pilot-v1'))

    assert.deepEqual(hits.map((file) => path.basename(file)), ['content-pilot-workflow.ts'])
})

test('nenhum caminho absoluto de maquina aparece no codigo do piloto', () => {
    for (const file of sources(path.join(pilotRoot, 'src'))) {
        const source = read(file)
        assert.ok(!/[A-Za-z]:[\\/]{2}Users/.test(source), `${path.basename(file)} carrega caminho de usuario`)
        assert.ok(!source.includes('/home/'), `${path.basename(file)} carrega caminho de usuario`)
    }
})
