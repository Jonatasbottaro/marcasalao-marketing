/**
 * Paridade das CLIs com o corpus: a saida do processo e exatamente o relatorio do
 * validador em memoria, e os exit codes 0 (valido), 1 (invalido) e 2 (uso, arquivo
 * ausente, JSON malformado) valem para amostras dos dois contratos.
 *
 * Tambem confere determinismo entre execucoes e ausencia de caminho absoluto,
 * timestamp ou stack trace na saida — os relatorios sao a interface publica.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, test } from 'node:test'

import type { CompositionValidationReport, ProjectValidationReport } from '../../src/validation-report.js'
import {
    compositionWith,
    compositionWithHref,
    moduleRoot,
    officialPairs,
    projectWith,
    readCompositionExample,
    readProjectExample,
    validateCompositionDocument,
    validateProjectDocument,
} from '../contract-harness.js'
import {
    atOutsideAuthorityHrefs,
    emptyAuthorityHrefs,
    semanticCases,
    structuralCompositionCases,
    structuralProjectCases,
} from '../contract-corpus.js'

const projectCli = path.join(moduleRoot, 'dist', 'src', 'validate-project-cli.js')
const compositionCli = path.join(moduleRoot, 'dist', 'src', 'validate-composition-cli.js')
const tempDir = mkdtempSync(path.join(os.tmpdir(), 'contratos-cli-'))

interface CliResult {
    status: number | null
    stdout: string
    stderr: string
}

function run(cli: string, args: string[]): CliResult {
    const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' })
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

/** Escreve o documento em arquivo temporario e devolve o caminho. */
function stage(name: string, document: unknown): string {
    const filePath = path.join(tempDir, `${name.replace(/[^A-Za-z0-9-]/g, '_')}.json`)
    writeFileSync(filePath, `${JSON.stringify(document, null, 2)}\n`, 'utf8')
    return filePath
}

function sample<T extends { name: string; document: Record<string, unknown>; valid: boolean }>(
    cases: readonly T[],
    valid: boolean,
    count: number,
): T[] {
    return cases.filter((caseItem) => caseItem.valid === valid).slice(0, count)
}

after(() => rmSync(tempDir, { recursive: true, force: true }))

test('exit 0: os exemplos oficiais validam nos dois contratos, em JSON e em texto', () => {
    for (const pair of officialPairs) {
        const projectPath = path.join(moduleRoot, 'examples', 'projects', pair.project)
        const compositionPath = path.join(moduleRoot, 'examples', 'compositions', pair.composition)

        const projectRun = run(projectCli, ['--project', projectPath, '--json'])
        assert.equal(projectRun.status, 0, `${pair.project}: ${projectRun.stderr}`)
        assert.deepEqual(
            JSON.parse(projectRun.stdout) as ProjectValidationReport,
            validateProjectDocument(readProjectExample(pair.project)),
            `${pair.project}: CLI divergiu do validador`,
        )

        const compositionRun = run(compositionCli, ['--project', projectPath, '--composition', compositionPath, '--json'])
        assert.equal(compositionRun.status, 0, `${pair.composition}: ${compositionRun.stderr}`)
        assert.deepEqual(
            JSON.parse(compositionRun.stdout) as CompositionValidationReport,
            validateCompositionDocument(readCompositionExample(pair.composition), readProjectExample(pair.project)),
            `${pair.composition}: CLI divergiu do validador`,
        )

        const humanRun = run(compositionCli, ['--project', projectPath, '--composition', compositionPath])
        assert.equal(humanRun.status, 0)
        assert.equal(humanRun.stdout.split('\n')[0], 'Composition is valid.')
        assert.match(humanRun.stdout, /COMPOSITION_RENDERER_UNDECIDED/, 'avisos precisam aparecer na saida em texto')
    }
})

test('exit 1: cada caso invalido da amostra devolve o mesmo relatorio do validador', () => {
    const projectFile = stage('projeto-base', projectWith({}))

    for (const caseItem of sample(structuralProjectCases, false, 10)) {
        const filePath = stage(`projeto-${caseItem.name}`, caseItem.document)
        const jsonRun = run(projectCli, ['--project', filePath, '--json'])
        assert.equal(jsonRun.status, 1, `esperava exit 1 em "${caseItem.name}": ${jsonRun.stdout}`)

        const report = JSON.parse(jsonRun.stdout) as ProjectValidationReport
        assert.deepEqual(report, validateProjectDocument(caseItem.document), `CLI divergiu do validador em "${caseItem.name}"`)
        if (caseItem.codes) {
            assert.deepEqual(report.errors.map((error) => error.code), [...caseItem.codes])
        }
    }

    for (const caseItem of sample(structuralCompositionCases, false, 12)) {
        const filePath = stage(`composicao-${caseItem.name}`, caseItem.document)
        const jsonRun = run(compositionCli, ['--project', projectFile, '--composition', filePath, '--json'])
        assert.equal(jsonRun.status, 1, `esperava exit 1 em "${caseItem.name}": ${jsonRun.stdout}`)

        const report = JSON.parse(jsonRun.stdout) as CompositionValidationReport
        assert.deepEqual(
            report,
            validateCompositionDocument(caseItem.document),
            `CLI divergiu do validador em "${caseItem.name}"`,
        )
    }
})

test('a CLI acompanha os dois motores no limite da autoridade do href', () => {
    const projectPath = stage('projeto-autoridade', projectWith({}))

    for (const [index, href] of atOutsideAuthorityHrefs.entries()) {
        const compositionPath = stage(`href-fora-da-autoridade-${index}`, compositionWithHref(href))
        const result = run(compositionCli, ['--project', projectPath, '--composition', compositionPath, '--json'])
        assert.equal(result.status, 0, `a CLI recusou href valido ${JSON.stringify(href)}: ${result.stdout}`)
        assert.equal((JSON.parse(result.stdout) as CompositionValidationReport).valid, true)
    }

    for (const [index, href] of emptyAuthorityHrefs.entries()) {
        const compositionPath = stage(`href-autoridade-vazia-${index}`, compositionWithHref(href))
        const result = run(compositionCli, ['--project', projectPath, '--composition', compositionPath, '--json'])
        assert.equal(result.status, 1, `a CLI aceitou href sem host na autoridade ${JSON.stringify(href)}`)
        const report = JSON.parse(result.stdout) as CompositionValidationReport
        assert.deepEqual(report.errors.map((error) => error.code), ['COMPOSITION_CTA_HREF_INVALID'])
    }
})

test('exit 0 com warnings: heuristicas nao mudam o codigo de saida', () => {
    const warningCase = semanticCases.find((caseItem) => caseItem.reason === 'heuristica-de-warning')
    assert.ok(warningCase, 'o corpus semantico perdeu o caso de heuristicas')

    const projectPath = stage('projeto-warning', warningCase.project)
    const compositionPath = stage('composicao-warning', warningCase.document)
    const jsonRun = run(compositionCli, ['--project', projectPath, '--composition', compositionPath, '--json'])

    assert.equal(jsonRun.status, 0)
    const report = JSON.parse(jsonRun.stdout) as CompositionValidationReport
    assert.deepEqual(report.errors, [])
    assert.deepEqual(report.warnings.map((warning) => warning.code), [...(warningCase.warnings ?? [])])

    const humanRun = run(compositionCli, ['--project', projectPath, '--composition', compositionPath])
    assert.equal(humanRun.status, 0)
    assert.match(humanRun.stdout, /COMPOSITION_SCENE_TEXT_LONG/)
})

test('casos validos da amostra tambem saem 0 pela CLI', () => {
    const projectFile = stage('projeto-base-valido', projectWith({}))

    for (const caseItem of sample(structuralCompositionCases, true, 3)) {
        const filePath = stage(`composicao-ok-${caseItem.name}`, caseItem.document)
        const result = run(compositionCli, ['--project', projectFile, '--composition', filePath, '--json'])
        assert.equal(result.status, 0, `esperava exit 0 em "${caseItem.name}": ${result.stdout}`)
        assert.equal((JSON.parse(result.stdout) as CompositionValidationReport).valid, true)
    }

    for (const caseItem of sample(structuralProjectCases, true, 3)) {
        const filePath = stage(`projeto-ok-${caseItem.name}`, caseItem.document)
        const result = run(projectCli, ['--project', filePath, '--json'])
        assert.equal(result.status, 0, `esperava exit 0 em "${caseItem.name}": ${result.stdout}`)
    }
})

test('exit 2: uso incorreto, arquivo ausente e JSON malformado nos dois contratos', () => {
    const goodProject = stage('projeto-uso', projectWith({}))
    const malformed = path.join(tempDir, 'malformado.json')
    writeFileSync(malformed, '{ nao e json', 'utf8')
    const missing = path.join(tempDir, 'nao-existe.json')

    assert.equal(run(projectCli, []).status, 2)
    assert.match(run(projectCli, []).stderr, /^Uso: /)
    assert.equal(run(projectCli, ['--project']).status, 2)
    assert.equal(run(projectCli, ['--project', missing]).status, 2)
    assert.equal(run(projectCli, ['--project', malformed]).status, 2)
    assert.equal(run(projectCli, ['--projeto', goodProject]).status, 2)
    assert.equal(run(projectCli, ['--project', goodProject, '--extra']).status, 2)

    assert.equal(run(compositionCli, []).status, 2)
    assert.match(run(compositionCli, []).stderr, /^Uso: /)
    assert.equal(run(compositionCli, ['--project', goodProject]).status, 2)
    assert.equal(run(compositionCli, ['--project', goodProject, '--composition', missing]).status, 2)
    assert.equal(run(compositionCli, ['--project', goodProject, '--composition', malformed]).status, 2)
    assert.equal(run(compositionCli, ['--project', malformed, '--composition', goodProject]).status, 2)

    for (const result of [
        run(projectCli, ['--project', malformed]),
        run(compositionCli, ['--project', goodProject, '--composition', malformed]),
    ]) {
        assert.equal(result.stdout, '', 'erro de uso nao imprime relatorio em stdout')
        assert.ok(!result.stderr.includes(' at '), 'sem stack trace')
        assert.match(result.stderr, /^Erro: /)
    }
})

test('a saida das CLIs e deterministica e nao expoe caminhos da maquina', () => {
    const invalidCase = sample(structuralCompositionCases, false, 1)[0]
    assert.ok(invalidCase, 'o corpus nao tem caso invalido para a checagem de determinismo')

    const projectPath = stage('projeto-det', projectWith({}))
    const compositionPath = stage('composicao-det', invalidCase.document)
    const args = ['--project', projectPath, '--composition', compositionPath, '--json']

    const first = run(compositionCli, args)
    const second = run(compositionCli, args)
    assert.equal(first.stdout, second.stdout, 'duas execucoes produziram JSON diferente')
    assert.equal(first.status, second.status)

    for (const output of [first.stdout, first.stderr]) {
        assert.ok(!output.includes(moduleRoot), 'a saida contem o caminho absoluto do modulo')
        assert.ok(!output.includes(tempDir), 'a saida contem o caminho absoluto do arquivo temporario')
        assert.ok(!/\d{4}-\d{2}-\d{2}T[\d:.]+Z/.test(output), 'a saida contem um timestamp ISO')
    }

    const report = JSON.parse(first.stdout) as CompositionValidationReport
    assert.deepEqual(Object.keys(report).sort(), [
        'compositionId',
        'errors',
        'format',
        'projectId',
        'rendererAdapter',
        'sceneCount',
        'schemaVersion',
        'summary',
        'totalDurationMs',
        'valid',
        'warnings',
    ])
    assert.ok(report.errors.length > 0)
    for (const error of report.errors) {
        assert.deepEqual(Object.keys(error).sort(), ['code', 'message', 'path'])
        assert.ok(!error.path.includes(path.sep), `caminho logico com separador de sistema: ${error.path}`)
    }
})

test('a CLI nao muta os arquivos validados', () => {
    const projectPath = stage('projeto-imutavel', projectWith({}))
    const compositionPath = stage('composicao-imutavel', compositionWith({}))
    const beforeProject = readFileSync(projectPath, 'utf8')
    const beforeComposition = readFileSync(compositionPath, 'utf8')

    const result = run(compositionCli, ['--project', projectPath, '--composition', compositionPath, '--json'])

    assert.equal(result.status, 0)
    assert.equal(readFileSync(projectPath, 'utf8'), beforeProject)
    assert.equal(readFileSync(compositionPath, 'utf8'), beforeComposition)
})
