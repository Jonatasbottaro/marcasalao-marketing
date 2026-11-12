/**
 * Testes unitarios do contrato de caso de pipeline, do resolvedor seguro,
 * da validacao de um caso e da agregacao multiprojeto.
 *
 * Cobre: estrutura do ContentPipelineCaseManifest, codigos estaveis,
 * resolucao lexica com confinamento, leitura segura sob raiz declarada
 * (incluindo symlink externo), descoberta deterministica de manifestos,
 * estados do caso (valid/invalid/manifest-invalid/unreadable), duplicidade
 * de ids, determinismo e imutabilidade.
 */

import assert from 'node:assert/strict'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, test } from 'node:test'

import {
    CASE_MANIFEST_VALID_SUMMARY,
    validateCaseManifest,
    type ContentPipelineCaseManifest,
} from '../src/content-pipeline-case-contract.js'
import {
    discoverCaseManifests,
    loadContentPipelineCase,
} from '../src/content-pipeline-case-loader.js'
import {
    resolveCaseDocumentPath,
    resolveContentPipelineCase,
} from '../src/resolve-content-pipeline-case.js'
import {
    CASE_VALID_SUMMARY,
    CASES_VALID_SUMMARY,
    aggregateContentPipelineCases,
    validateContentPipelineCase,
} from '../src/validate-content-pipeline-case.js'
import { moduleRoot } from './contract-harness.js'

const examplesRoot = path.join(moduleRoot, 'examples')

function manifestWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'caso-teste',
        project: '../projects/projeto.json',
        composition: '../compositions/composicao.json',
        outputPlan: '../output-plans/plano.json',
        beatPlan: './plano-beats.json',
        ...overrides,
    }
}

function codesOf(errors: readonly { code: string }[]): string[] {
    return errors.map((item) => item.code)
}

const tempRoots: string[] = []

function makeTempRoot(): string {
    const root = mkdtempSync(path.join(os.tmpdir(), 'pipeline-case-test-'))
    tempRoots.push(root)
    return root
}

after(() => {
    for (const root of tempRoots) {
        if (root) rmSync(root, { recursive: true, force: true })
    }
})

/** Cria um caso minimo em disco: manifesto em case/ e quatro documentos JSON. */
function stageCaseOnDisk(root: string, overrides: Record<string, unknown> = {}): string {
    const caseDir = path.join(root, 'case')
    mkdirSync(path.join(root, 'projects'), { recursive: true })
    mkdirSync(path.join(root, 'compositions'), { recursive: true })
    mkdirSync(path.join(root, 'output-plans'), { recursive: true })
    mkdirSync(caseDir, { recursive: true })
    writeFileSync(path.join(root, 'projects', 'projeto.json'), '{"kind":"project"}\n', 'utf8')
    writeFileSync(path.join(root, 'compositions', 'composicao.json'), '{"kind":"composition"}\n', 'utf8')
    writeFileSync(path.join(root, 'output-plans', 'plano.json'), '{"kind":"outputPlan"}\n', 'utf8')
    writeFileSync(path.join(caseDir, 'plano-beats.json'), '{"kind":"beatPlan"}\n', 'utf8')
    const manifestPath = path.join(caseDir, 'caso.pipeline.json')
    writeFileSync(manifestPath, `${JSON.stringify(manifestWith(overrides), null, 2)}\n`, 'utf8')
    return manifestPath
}

function readJsonExample(relativePath: string): unknown {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as unknown
}

function validCaseInput(): Record<string, unknown> {
    return {
        manifest: readJsonExample('examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json'),
        project: readJsonExample('examples/projects/multitrack-hub-social.project.json'),
        composition: readJsonExample('examples/compositions/multitrack-hub-social-reel.composition.json'),
        outputPlan: readJsonExample('examples/output-plans/multitrack-hub-instagram-reels-video.output-plan.json'),
        beatPlan: readJsonExample('examples/pipelines/multitrack-hub-social-reel.beat-plan.json'),
    }
}

/* ------------------------------------------------------------------ */
/* Contrato estrutural do manifesto de caso                            */
/* ------------------------------------------------------------------ */

test('manifesto de caso valido: relatorio valido com caseId e summary estavel', () => {
    const report = validateCaseManifest(manifestWith())
    assert.equal(report.valid, true)
    assert.deepEqual(report.errors, [])
    assert.equal(report.summary, CASE_MANIFEST_VALID_SUMMARY)
    assert.equal(report.caseId, 'caso-teste')
})

test('manifesto de caso nao-objeto: CASE_MANIFEST_INVALID', () => {
    for (const invalid of [null, undefined, 'texto', 42, true, []]) {
        const report = validateCaseManifest(invalid)
        assert.equal(report.valid, false)
        assert.deepEqual(codesOf(report.errors), ['CASE_MANIFEST_INVALID'])
        assert.equal(report.caseId, null)
    }
})

test('schemaVersion diferente de 1: CASE_SCHEMA_VERSION_UNSUPPORTED', () => {
    for (const version of [2, 0, '1', null]) {
        const report = validateCaseManifest(manifestWith({ schemaVersion: version }))
        assert.equal(report.valid, false)
        assert.ok(codesOf(report.errors).includes('CASE_SCHEMA_VERSION_UNSUPPORTED'))
    }
    const missing = manifestWith()
    delete missing.schemaVersion
    assert.ok(codesOf(validateCaseManifest(missing).errors).includes('CASE_SCHEMA_VERSION_UNSUPPORTED'))
})

test('id ausente, vazio ou fora do kebab-case: codigos proprios', () => {
    const missing = manifestWith()
    delete missing.id
    assert.ok(codesOf(validateCaseManifest(missing).errors).includes('CASE_ID_REQUIRED'))
    assert.ok(codesOf(validateCaseManifest(manifestWith({ id: '   ' })).errors).includes('CASE_ID_REQUIRED'))
    assert.ok(codesOf(validateCaseManifest(manifestWith({ id: 'Caso_Teste' })).errors).includes('CASE_ID_INVALID'))
    assert.ok(codesOf(validateCaseManifest(manifestWith({ id: 123 })).errors).includes('CASE_ID_REQUIRED'))
})

test('campo desconhecido: CASE_UNKNOWN_FIELD com o nome no caminho logico', () => {
    const report = validateCaseManifest(manifestWith({ extra: true }))
    assert.equal(report.valid, false)
    const unknown = report.errors.find((item) => item.code === 'CASE_UNKNOWN_FIELD')
    assert.equal(unknown?.path, 'extra')
})

test('campo de documento ausente ou malformado: codigos proprios por campo', () => {
    const missing = manifestWith()
    delete missing.project
    assert.ok(codesOf(validateCaseManifest(missing).errors).includes('CASE_DOCUMENT_PATH_REQUIRED'))
    assert.ok(codesOf(validateCaseManifest(manifestWith({ composition: 7 })).errors).includes('CASE_DOCUMENT_PATH_INVALID'))
    assert.ok(codesOf(validateCaseManifest(manifestWith({ outputPlan: '   ' })).errors).includes('CASE_DOCUMENT_PATH_INVALID'))
})

test('caminhos absolutos, URL, controle e sensiveis sao rejeitados pelo contrato', () => {
    const cases: Array<{ value: string; code: string }> = [
        { value: '/absoluto/projeto.json', code: 'CASE_DOCUMENT_PATH_ABSOLUTE' },
        { value: 'C:\\absoluto\\projeto.json', code: 'CASE_DOCUMENT_PATH_ABSOLUTE' },
        { value: 'https://exemplo.com/projeto.json', code: 'CASE_DOCUMENT_PATH_URL' },
        { value: 'projeto\u0000.json', code: 'CASE_DOCUMENT_PATH_CONTROL_CHARACTER' },
        { value: '../.env', code: 'CASE_DOCUMENT_PATH_SENSITIVE' },
    ]
    for (const item of cases) {
        const report = validateCaseManifest(manifestWith({ project: item.value }))
        assert.equal(report.valid, false, item.value)
        assert.ok(codesOf(report.errors).includes(item.code), `${item.value} -> ${codesOf(report.errors).join(',')}`)
    }
})

test('traversal lexical e aceito pelo contrato: o confinamento decide no resolvedor', () => {
    const report = validateCaseManifest(manifestWith({ project: '../projects/projeto.json' }))
    assert.equal(report.valid, true)
})

test('contrato de caso e deterministico e nao muta a entrada', () => {
    const input = manifestWith()
    const snapshot = JSON.stringify(input)
    const run1 = validateCaseManifest(input)
    const run2 = validateCaseManifest(input)
    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(input), snapshot)
})

/* ------------------------------------------------------------------ */
/* Resolucao lexica pura com confinamento                              */
/* ------------------------------------------------------------------ */

test('resolveCaseDocumentPath aceita irmaos dentro da raiz e rejeita escape', () => {
    const root = path.join('raiz', 'examples')
    const manifestDir = path.join(root, 'pipelines')

    const inside = resolveCaseDocumentPath(manifestDir, root, 'project', '../projects/projeto.json')
    assert.ok('path' in inside)
    assert.equal(inside.path, path.resolve(manifestDir, '../projects/projeto.json'))

    const outside = resolveCaseDocumentPath(manifestDir, root, 'project', '../../fora/projeto.json')
    assert.ok('error' in outside)
    assert.equal(outside.error.code, 'CASE_DOCUMENT_PATH_ESCAPE')

    const selfRoot = resolveCaseDocumentPath(manifestDir, root, 'project', '..')
    assert.ok('error' in selfRoot)
    assert.equal(selfRoot.error.code, 'CASE_DOCUMENT_PATH_ESCAPE')
})

test('resolveCaseDocumentPath rejeita absoluto e URL antes de resolver', () => {
    const absolute = resolveCaseDocumentPath('dir', 'dir', 'project', '/etc/projeto.json')
    assert.ok('error' in absolute)
    assert.equal(absolute.error.code, 'CASE_DOCUMENT_PATH_ABSOLUTE')

    const url = resolveCaseDocumentPath('dir', 'dir', 'project', 'https://exemplo.com/x.json')
    assert.ok('error' in url)
    assert.equal(url.error.code, 'CASE_DOCUMENT_PATH_URL')
})

/* ------------------------------------------------------------------ */
/* Resolvedor com I/O: leitura, existencia e confinamento real         */
/* ------------------------------------------------------------------ */

test('resolvedor le o manifesto e resolve os quatro documentos dentro da raiz', () => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root)
    const resolution = resolveContentPipelineCase(manifestPath, root)
    assert.equal(resolution.ok, true)
    if (!resolution.ok) return
    assert.equal(resolution.manifest.id, 'caso-teste')
    for (const field of ['project', 'composition', 'outputPlan', 'beatPlan'] as const) {
        assert.ok(path.isAbsolute(resolution.paths[field]))
        assert.ok(!path.relative(root, resolution.paths[field]).startsWith('..'))
    }
})

test('resolvedor rejeita documento ausente com CASE_DOCUMENT_MISSING', () => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root)
    rmSync(path.join(root, 'projects', 'projeto.json'))
    const resolution = resolveContentPipelineCase(manifestPath, root)
    assert.equal(resolution.ok, false)
    if (resolution.ok) return
    assert.deepEqual(codesOf(resolution.report.errors), ['CASE_DOCUMENT_MISSING'])
    assert.equal(resolution.report.errors[0]?.path, 'project')
    assert.equal(resolution.report.caseId, 'caso-teste')
})

test('resolvedor rejeita documento que escapa da raiz por symlink', (t) => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root)
    const outsideDir = makeTempRoot()
    const outsideFile = path.join(outsideDir, 'projeto.json')
    writeFileSync(outsideFile, '{"kind":"outside"}\n', 'utf8')
    const linkPath = path.join(root, 'projects', 'projeto.json')
    rmSync(linkPath)
    try {
        symlinkSync(outsideFile, linkPath)
    } catch {
        t.skip('symlink nao suportado neste ambiente Windows')
        return
    }
    const resolution = resolveContentPipelineCase(manifestPath, root)
    assert.equal(resolution.ok, false)
    if (resolution.ok) return
    assert.deepEqual(codesOf(resolution.report.errors), ['CASE_RESOLUTION_ESCAPE'])
})

test('resolvedor rejeita manifesto fora da raiz de confinamento', () => {
    const root = makeTempRoot()
    const outsideRoot = makeTempRoot()
    const manifestPath = stageCaseOnDisk(outsideRoot)
    const resolution = resolveContentPipelineCase(manifestPath, root)
    assert.equal(resolution.ok, false)
    if (resolution.ok) return
    assert.deepEqual(codesOf(resolution.report.errors), ['CASE_RESOLUTION_ESCAPE'])
})

test('resolvedor distingue manifesto ausente, malformado e estruturalmente invalido', () => {
    const root = makeTempRoot()
    stageCaseOnDisk(root)

    const missing = resolveContentPipelineCase(path.join(root, 'case', 'nao-existe.pipeline.json'), root)
    assert.equal(missing.ok, false)
    if (!missing.ok) assert.deepEqual(codesOf(missing.report.errors), ['CASE_MANIFEST_UNREADABLE'])

    const malformedPath = path.join(root, 'case', 'malformado.pipeline.json')
    writeFileSync(malformedPath, '{ nao e json', 'utf8')
    const malformed = resolveContentPipelineCase(malformedPath, root)
    assert.equal(malformed.ok, false)
    if (!malformed.ok) assert.deepEqual(codesOf(malformed.report.errors), ['CASE_MANIFEST_MALFORMED'])

    const invalidPath = path.join(root, 'case', 'invalido.pipeline.json')
    writeFileSync(invalidPath, `${JSON.stringify(manifestWith({ schemaVersion: 9 }))}\n`, 'utf8')
    const invalid = resolveContentPipelineCase(invalidPath, root)
    assert.equal(invalid.ok, false)
    if (!invalid.ok) assert.ok(codesOf(invalid.report.errors).includes('CASE_SCHEMA_VERSION_UNSUPPORTED'))
})

test('resolvedor rejeita raiz de confinamento inexistente', () => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root)
    const resolution = resolveContentPipelineCase(manifestPath, path.join(root, 'nao-existe'))
    assert.equal(resolution.ok, false)
    if (resolution.ok) return
    assert.deepEqual(codesOf(resolution.report.errors), ['CASE_RESOLUTION_ROOT_INVALID'])
})

test('resolvedor rejeita escape por traversal que sai da raiz', () => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root, { project: '../../fora/projeto.json' })
    const resolution = resolveContentPipelineCase(manifestPath, root)
    assert.equal(resolution.ok, false)
    if (resolution.ok) return
    assert.deepEqual(codesOf(resolution.report.errors), ['CASE_DOCUMENT_PATH_ESCAPE'])
})

/* ------------------------------------------------------------------ */
/* Validacao de um caso em memoria                                     */
/* ------------------------------------------------------------------ */

test('caso completo valido: status valid e pipeline consolidado preservado', () => {
    const report = validateContentPipelineCase(validCaseInput())
    assert.equal(report.status, 'valid')
    assert.equal(report.valid, true)
    assert.equal(report.summary, CASE_VALID_SUMMARY)
    assert.equal(report.caseId, 'multitrack-hub-pipeline-pilot')
    assert.equal(report.manifestReport.valid, true)
    assert.ok(report.pipeline !== null)
    assert.equal(report.pipeline?.valid, true)
    assert.equal(report.pipeline?.projectId, 'multitrack-hub')
    assert.deepEqual(report.readErrors, [])
})

test('manifesto invalido: status manifest-invalid sem executar o pipeline', () => {
    const input = { ...validCaseInput(), manifest: { schemaVersion: 9 } }
    const report = validateContentPipelineCase(input)
    assert.equal(report.status, 'manifest-invalid')
    assert.equal(report.valid, false)
    assert.equal(report.pipeline, null)
    assert.ok(report.manifestReport.errors.length > 0)
})

test('documentos invalidos com manifesto valido: status invalid com relatorio do pipeline', () => {
    const input = { ...validCaseInput(), composition: { invalido: true } }
    const report = validateContentPipelineCase(input)
    assert.equal(report.status, 'invalid')
    assert.equal(report.valid, false)
    assert.ok(report.pipeline !== null)
    assert.equal(report.pipeline?.valid, false)
    assert.ok(report.pipeline?.errors.some((item) => item.stage === 'composition'))
})

test('entrada nao-objeto: manifest-invalid sem excecao', () => {
    for (const invalid of [null, undefined, 'texto', []]) {
        const report = validateContentPipelineCase(invalid)
        assert.equal(report.status, 'manifest-invalid')
        assert.equal(report.valid, false)
    }
})

test('caso em memoria e deterministico e nao muta as entradas', () => {
    const input = validCaseInput()
    const snapshot = JSON.stringify(input)
    const run1 = validateContentPipelineCase(input)
    const run2 = validateContentPipelineCase(input)
    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(input), snapshot)
})

/* ------------------------------------------------------------------ */
/* Agregacao multiprojeto                                              */
/* ------------------------------------------------------------------ */

test('agregacao de dois casos validos: valid, contagens e ordem preservadas', () => {
    const marca = validateContentPipelineCase({
        manifest: readJsonExample('examples/pipelines/marca-salao-pipeline-pilot.pipeline.json'),
        project: readJsonExample('examples/projects/marca-salao-social.project.json'),
        composition: readJsonExample('examples/compositions/marca-salao-social-reel.composition.json'),
        outputPlan: readJsonExample('examples/output-plans/instagram-reels-video.output-plan.json'),
        beatPlan: readJsonExample('examples/pipelines/marca-salao-social-reel.beat-plan.json'),
    })
    const multitrack = validateContentPipelineCase(validCaseInput())
    const report = aggregateContentPipelineCases([marca, multitrack])
    assert.equal(report.valid, true)
    assert.equal(report.summary, CASES_VALID_SUMMARY)
    assert.equal(report.caseCount, 2)
    assert.equal(report.validCount, 2)
    assert.equal(report.invalidCount, 0)
    assert.deepEqual(report.errors, [])
    assert.deepEqual(report.cases.map((item) => item.caseId), ['marca-salao-pipeline-pilot', 'multitrack-hub-pipeline-pilot'])
})

test('agregacao com um caso invalido: invalid com contagem exata', () => {
    const valid = validateContentPipelineCase(validCaseInput())
    const invalid = validateContentPipelineCase({ ...validCaseInput(), beatPlan: { invalido: true } })
    const report = aggregateContentPipelineCases([valid, invalid])
    assert.equal(report.valid, false)
    assert.equal(report.validCount, 1)
    assert.equal(report.invalidCount, 1)
    assert.match(report.summary, /1 invalid case\(s\)/)
})

test('agregacao rejeita ids duplicados com CASE_DUPLICATE_ID', () => {
    const first = validateContentPipelineCase(validCaseInput())
    const second = validateContentPipelineCase(validCaseInput())
    const report = aggregateContentPipelineCases([first, second])
    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report.errors), ['CASE_DUPLICATE_ID'])
    assert.equal(report.errors[0]?.path, 'cases[1].id')
})

test('agregacao vazia nunca e valida: CASES_EMPTY', () => {
    const report = aggregateContentPipelineCases([])
    assert.equal(report.valid, false)
    assert.equal(report.caseCount, 0)
    assert.deepEqual(codesOf(report.errors), ['CASES_EMPTY'])
})

/* ------------------------------------------------------------------ */
/* Descoberta e carga em disco                                         */
/* ------------------------------------------------------------------ */

test('descoberta encontra manifestos em ordem deterministica e ignora outros arquivos', () => {
    const root = makeTempRoot()
    mkdirSync(path.join(root, 'a'), { recursive: true })
    mkdirSync(path.join(root, 'b'), { recursive: true })
    writeFileSync(path.join(root, 'b', 'segundo.pipeline.json'), '{}\n', 'utf8')
    writeFileSync(path.join(root, 'a', 'primeiro.pipeline.json'), '{}\n', 'utf8')
    writeFileSync(path.join(root, 'a', 'outro.json'), '{}\n', 'utf8')

    const discovery = discoverCaseManifests(root)
    assert.equal(discovery.ok, true)
    if (!discovery.ok) return
    assert.deepEqual(discovery.paths, [
        path.join(root, 'a', 'primeiro.pipeline.json'),
        path.join(root, 'b', 'segundo.pipeline.json'),
    ])
    const again = discoverCaseManifests(root)
    assert.deepEqual(again, discovery)
})

test('descoberta ignora symlink de arquivo e de diretorio', (t) => {
    const root = makeTempRoot()
    const outside = makeTempRoot()
    writeFileSync(path.join(outside, 'externo.pipeline.json'), '{}\n', 'utf8')
    mkdirSync(path.join(root, 'real'), { recursive: true })
    writeFileSync(path.join(root, 'real', 'interno.pipeline.json'), '{}\n', 'utf8')
    try {
        symlinkSync(path.join(outside, 'externo.pipeline.json'), path.join(root, 'link.pipeline.json'))
        symlinkSync(outside, path.join(root, 'dir-link'))
    } catch {
        t.skip('symlink nao suportado neste ambiente Windows')
        return
    }
    const discovery = discoverCaseManifests(root)
    assert.equal(discovery.ok, true)
    if (!discovery.ok) return
    assert.deepEqual(discovery.paths, [path.join(root, 'real', 'interno.pipeline.json')])
})

test('descoberta em raiz inexistente devolve erro sanitizado', () => {
    const discovery = discoverCaseManifests(path.join(makeTempRoot(), 'nao-existe'))
    assert.equal(discovery.ok, false)
    if (discovery.ok) return
    assert.equal(discovery.error, 'The cases root does not exist or is not readable.')
})

test('carga em disco dos exemplos reais devolve os quatro documentos lidos', () => {
    const manifestPath = path.join(examplesRoot, 'pipelines', 'multitrack-hub-pipeline-pilot.pipeline.json')
    const loaded = loadContentPipelineCase(manifestPath, examplesRoot)
    assert.equal(loaded.ok, true)
    if (!loaded.ok) return
    assert.deepEqual(loaded.input.project, readJsonExample('examples/projects/multitrack-hub-social.project.json'))
    assert.deepEqual(loaded.input.beatPlan, readJsonExample('examples/pipelines/multitrack-hub-social-reel.beat-plan.json'))
    const report = validateContentPipelineCase(loaded.input)
    assert.equal(report.valid, true)
})

test('carga com documento malformado: status unreadable com diagnostico por campo', () => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root)
    writeFileSync(path.join(root, 'projects', 'projeto.json'), '{ nao e json', 'utf8')
    const loaded = loadContentPipelineCase(manifestPath, root)
    assert.equal(loaded.ok, false)
    if (loaded.ok) return
    assert.equal(loaded.report.status, 'unreadable')
    assert.equal(loaded.report.valid, false)
    assert.equal(loaded.report.readErrors.length, 1)
    assert.match(loaded.report.readErrors[0] ?? '', /project document/)
    assert.equal(loaded.report.pipeline, null)
})

test('carga com manifesto estruturalmente invalido: status manifest-invalid', () => {
    const root = makeTempRoot()
    const manifestPath = stageCaseOnDisk(root, { id: 'Invalido' })
    const loaded = loadContentPipelineCase(manifestPath, root)
    assert.equal(loaded.ok, false)
    if (loaded.ok) return
    assert.equal(loaded.report.status, 'manifest-invalid')
    assert.ok(loaded.report.manifestReport.errors.some((item) => item.code === 'CASE_ID_INVALID'))
})

/* ------------------------------------------------------------------ */
/* Pureza estatica dos modulos novos                                   */
/* ------------------------------------------------------------------ */

test('modulos de caso nao usam rede, relogio, aleatoriedade nem Temporal', () => {
    const files = [
        'src/content-pipeline-case-contract.ts',
        'src/validate-content-pipeline-case.ts',
        'src/resolve-content-pipeline-case.ts',
        'src/content-pipeline-case-loader.ts',
        'src/content-pipeline-cases-cli.ts',
    ]
    const forbiddenTokens = [
        '@temporalio',
        'orchestration',
        'fetch(',
        'http.request',
        'https.request',
        'process.env',
        'Date.now',
        'Math.random',
    ]
    for (const rel of files) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        for (const token of forbiddenTokens) {
            assert.ok(!content.includes(token), `token proibido "${token}" encontrado em ${rel}`)
        }
    }
    for (const rel of ['src/content-pipeline-case-contract.ts', 'src/validate-content-pipeline-case.ts']) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        assert.ok(!content.includes('console.'), `console proibido no modulo de dominio: ${rel}`)
        assert.ok(!content.includes('readFileSync('), `readFileSync proibido no modulo de dominio: ${rel}`)
        assert.ok(!content.includes('node:fs'), `I/O direto proibido no modulo de dominio: ${rel}`)
    }
})
