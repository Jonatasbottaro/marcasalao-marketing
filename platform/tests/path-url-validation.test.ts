/**
 * Etapa 2 da correcao dos contratos: validacao lexica compartilhada de caminhos
 * relativos, regras de href (parser de URL) e campos textuais.
 *
 * Cada caso roda nos dois motores: o validador TypeScript (implementacao de
 * referencia) e o schema JSON draft-07 espelho (ajv). Os grupos de concordancia
 * exigem o mesmo veredicto nos dois; os grupos finais registram, de forma
 * explicita e testada, as unicas divergencias conhecidas — regras semanticas que
 * so o core expressa e a sintaxe canonica que so o schema exige.
 */
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { containsControlCharacter, inspectRelativePath, pathSegments } from '../src/relative-path.js'
import type { RelativePathViolation } from '../src/relative-path.js'
import { validateComposition } from '../src/validate-composition.js'
import { validateProjectManifest } from '../src/validate-project.js'
import type { CompositionValidationReport, ProjectValidationReport } from '../src/validation-report.js'

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

// strict desligado: o espelho normativo usa somente o vocabulario draft-07 e os
// avisos do strict mode dependeriam da versao do motor (saida nao estavel).
const ajv = new AjvModule.default({ allErrors: true, strict: false })

function compileSchema(file: string): (document: unknown) => boolean {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', file), 'utf8')) as AnySchemaObject
    const validate = ajv.compile(schema)
    return (document: unknown): boolean => validate(document) === true
}

const projectSchemaCheck = compileSchema('project.schema.json')
const compositionSchemaCheck = compileSchema('composition.schema.json')

const B = '\\'
const NUL = String.fromCharCode(0)

function manifestWith(assetRoot: string): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'projeto-teste',
        name: 'Projeto Teste',
        locale: 'pt-BR',
        timezone: 'America/Sao_Paulo',
        brandTheme: 'tema-teste',
        assetRoot,
        contentPolicies: {
            requireApprovedBriefing: true,
            requireApprovedScript: true,
            prohibitPersonalData: true,
            requireFunctionalEvidence: true,
        },
        outputProfiles: ['vertical-social'],
    }
}

const baseManifest = manifestWith('projects/projeto-teste/assets')

/** Composicao valida de uma cena image cujo asset.path recebe o valor testado. */
function compositionWithAssetPath(assetPath: string): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        id: 'comp-caminhos',
        title: 'Composicao Caminhos',
        locale: 'pt-BR',
        format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
        scenes: [
            {
                id: 'imagem',
                type: 'image',
                durationMs: 3000,
                content: { asset: { id: 'tela-01', path: assetPath } },
            },
        ],
        renderer: { adapter: 'undecided' },
    }
}

/** Composicao valida de uma cena cta cujo content.href recebe o valor testado. */
function compositionWithHref(href: string): Record<string, unknown> {
    return {
        ...compositionWithAssetPath('assets/tela-01.png'),
        id: 'comp-href',
        scenes: [
            {
                id: 'chamada',
                type: 'cta',
                durationMs: 3000,
                content: { text: 'Conheca o sistema.', href },
            },
        ],
    }
}

/** Composicao com uma cena text, para os campos textuais obrigatorios. */
function compositionWithTextField(field: 'title' | 'locale' | 'text' | 'accessibilityLabel' | 'alt', value: unknown): Record<string, unknown> {
    const document = compositionWithAssetPath('assets/tela-01.png')
    if (field === 'title' || field === 'locale') {
        document[field] = value
        return document
    }
    const scenes = document.scenes as Record<string, unknown>[]
    if (field === 'alt') {
        scenes[0]!.content = { asset: { id: 'tela-01', path: 'assets/tela-01.png' }, alt: value }
    } else if (field === 'text') {
        scenes[0] = { id: 'abertura', type: 'text', durationMs: 3000, content: { text: value } }
    } else {
        scenes[0] = { id: 'abertura', type: 'text', durationMs: 3000, content: { text: 'Abertura.', accessibilityLabel: value } }
    }
    return document
}

function errorsOfProject(report: ProjectValidationReport): string[] {
    return report.errors.map((error) => error.code)
}

function errorsOfComposition(report: CompositionValidationReport): string[] {
    return report.errors.map((error) => error.code)
}

interface PathCase {
    value: string
    violation: RelativePathViolation
    projectCode: string
    compositionCode: string
}

/**
 * Cada linha e a mesma violacao lexica vista pelos dois contratos: a deteccao e
 * compartilhada, os codigos e caminhos de erro permanecem proprios de cada um.
 */
const pathCases: readonly PathCase[] = [
    {
        value: `/var/assets`,
        violation: 'ABSOLUTE',
        projectCode: 'PROJECT_ASSET_ROOT_ABSOLUTE',
        compositionCode: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
    },
    {
        value: `C:${B}assets${B}x`,
        violation: 'ABSOLUTE',
        projectCode: 'PROJECT_ASSET_ROOT_ABSOLUTE',
        compositionCode: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
    },
    {
        value: `${B}${B}servidor${B}share${B}a.png`,
        violation: 'ABSOLUTE',
        projectCode: 'PROJECT_ASSET_ROOT_ABSOLUTE',
        compositionCode: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
    },
    {
        value: 'https://example.com/assets',
        violation: 'URL',
        projectCode: 'PROJECT_ASSET_ROOT_URL',
        compositionCode: 'COMPOSITION_ASSET_PATH_URL',
    },
    {
        value: 'file:///c:/assets/a.png',
        violation: 'URL',
        projectCode: 'PROJECT_ASSET_ROOT_URL',
        compositionCode: 'COMPOSITION_ASSET_PATH_URL',
    },
    {
        value: '//example.com/a.png',
        violation: 'URL',
        projectCode: 'PROJECT_ASSET_ROOT_URL',
        compositionCode: 'COMPOSITION_ASSET_PATH_URL',
    },
    {
        value: '../assets',
        violation: 'TRAVERSAL',
        projectCode: 'PROJECT_ASSET_ROOT_TRAVERSAL',
        compositionCode: 'COMPOSITION_ASSET_PATH_TRAVERSAL',
    },
    {
        value: `assets${B}..${B}fora.png`,
        violation: 'TRAVERSAL',
        projectCode: 'PROJECT_ASSET_ROOT_TRAVERSAL',
        compositionCode: 'COMPOSITION_ASSET_PATH_TRAVERSAL',
    },
    {
        value: 'projects/x/.env',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'assets/.env.local',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'assets/.git/config',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/server.pem',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/service.key',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/legacy.p12',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/legacy.pfx',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/id_rsa',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/id_ed25519.pub',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: `assets${NUL}b.png`,
        violation: 'CONTROL_CHARACTER',
        projectCode: 'PROJECT_ASSET_ROOT_CONTROL_CHARACTER',
        compositionCode: 'COMPOSITION_ASSET_PATH_CONTROL_CHARACTER',
    },
]

/** Caminhos que devem ser ACEITOS pelos dois contratos e pelos dois motores. */
const acceptedPaths: readonly string[] = [
    'assets/secretaria',
    'assets/secretaria.png',
    'assets/cenas/01.png',
    'projects/projeto-teste/assets',
    'assets/keys/x.png',
    'assets/.gitignore',
    'assets/env/.gitmodules',
    'assets/passphrase.txt',
    'assets/./ok.png',
]

/** URL que devem ser ACEITAS no href (http(s) absoluto, com hostname, sem credenciais). */
const acceptedHrefs: readonly string[] = [
    'http://example.com',
    'https://example.com',
    'https://example.com.br/roda-pe',
    'HTTPS://EXAMPLE.COM',
    'HtTpS://example.com/a?b=1#c',
    'https://example.com:8443/rota',
    'https://example.com/@mencao',
    'https://[::1]:8080/',
]

/** URL que devem ser REJEITADAS, com o codigo esperado do core. */
const rejectedHrefs: readonly { value: string; code: string }[] = [
    { value: 'https://usuario@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { value: 'https://user:pass@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { value: 'HTTPS://usuario:senha@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { value: 'https://@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { value: 'ftp://example.com', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: 'file:///c:/assets/a.png', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: 'data:text/plain,oi', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: '//example.com/a.png', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: '/rota/relativa', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: 'example.com/a', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: 'https://', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { value: `https://example.com${NUL}`, code: 'COMPOSITION_CTA_HREF_INVALID' },
]

test('a violacao lexica compartilhada produz os codigos proprios de cada contrato', () => {
    for (const testCase of pathCases) {
        assert.deepEqual(
            inspectRelativePath(testCase.value),
            [testCase.violation],
            `violacao esperada para ${JSON.stringify(testCase.value)}`,
        )

        const manifest = manifestWith(testCase.value)
        assert.deepEqual(errorsOfProject(validateProjectManifest(manifest)), [testCase.projectCode])
        assert.equal(projectSchemaCheck(manifest), false)

        const composition = compositionWithAssetPath(testCase.value)
        assert.deepEqual(errorsOfComposition(validateComposition(composition, baseManifest)), [testCase.compositionCode])
        assert.equal(compositionSchemaCheck(composition), false)
    }
})

test('caminhos comuns sao aceitos pelos dois contratos nos dois motores', () => {
    for (const value of acceptedPaths) {
        assert.deepEqual(inspectRelativePath(value), [])

        const manifest = manifestWith(value)
        assert.equal(validateProjectManifest(manifest).valid, true, `core rejeitou assetRoot ${JSON.stringify(value)}`)
        assert.equal(projectSchemaCheck(manifest), true, `schema rejeitou assetRoot ${JSON.stringify(value)}`)

        const composition = compositionWithAssetPath(value)
        assert.equal(validateComposition(composition, baseManifest).valid, true, `core rejeitou asset.path ${JSON.stringify(value)}`)
        assert.equal(compositionSchemaCheck(composition), true, `schema rejeitou asset.path ${JSON.stringify(value)}`)
    }
})

test('assetRoot com protocolo e rejeitado (regressao: antes passava)', () => {
    const manifest = manifestWith('https://example.com/assets')
    assert.deepEqual(errorsOfProject(validateProjectManifest(manifest)), ['PROJECT_ASSET_ROOT_URL'])
    assert.equal(projectSchemaCheck(manifest), false)
})

test('asset secretaria e aceito (regressao: o bloqueio por substring rejeitava)', () => {
    for (const value of ['assets/secretaria', 'assets/secretaria.png']) {
        const manifest = manifestWith(`projects/projeto-teste/${value}`)
        assert.equal(validateProjectManifest(manifest).valid, true)
        assert.equal(projectSchemaCheck(manifest), true)

        const composition = compositionWithAssetPath(`projects/projeto-teste/${value}`)
        assert.equal(validateComposition(composition, baseManifest).valid, true)
        assert.equal(compositionSchemaCheck(composition), true)
    }
})

test('href aceita http(s) absoluto sem credenciais, em qualquer caixa', () => {
    for (const href of acceptedHrefs) {
        const composition = compositionWithHref(href)
        assert.equal(
            validateComposition(composition, baseManifest).valid,
            true,
            `core rejeitou href ${JSON.stringify(href)}: ${errorsOfComposition(validateComposition(composition, baseManifest)).join(', ')}`,
        )
        assert.equal(compositionSchemaCheck(composition), true, `schema rejeitou href ${JSON.stringify(href)}`)
    }
})

test('href rejeita usuario ou senha e qualquer outra sintaxe', () => {
    for (const { value, code } of rejectedHrefs) {
        const composition = compositionWithHref(value)
        const errors = errorsOfComposition(validateComposition(composition, baseManifest))
        assert.deepEqual(errors, [code], `core produziu outro codigo para href ${JSON.stringify(value)}`)
        assert.equal(compositionSchemaCheck(composition), false, `schema aceitou href ${JSON.stringify(value)}`)
    }
})

test('href com apenas usuario e credencial (regressao: antes passava)', () => {
    const composition = compositionWithHref('https://usuario@example.com')
    assert.deepEqual(errorsOfComposition(validateComposition(composition, baseManifest)), ['COMPOSITION_CTA_HREF_CREDENTIALS'])
    assert.equal(compositionSchemaCheck(composition), false)
})

test('strings obrigatorias compostas apenas por espacos sao rejeitadas nos dois contratos', () => {
    const blankCases: readonly { field: 'title' | 'locale' | 'text' | 'accessibilityLabel' | 'alt'; code: string }[] = [
        { field: 'title', code: 'COMPOSITION_TITLE_REQUIRED' },
        { field: 'locale', code: 'COMPOSITION_LOCALE_REQUIRED' },
        { field: 'text', code: 'COMPOSITION_TEXT_REQUIRED' },
        { field: 'accessibilityLabel', code: 'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN' },
        { field: 'alt', code: 'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN' },
    ]

    for (const { field, code } of blankCases) {
        for (const value of ['   ', '\t\n ']) {
            const composition = compositionWithTextField(field, value)
            assert.deepEqual(errorsOfComposition(validateComposition(composition, baseManifest)), [code], `core aceitou ${field} em branco`)
            assert.equal(compositionSchemaCheck(composition), false, `schema aceitou ${field} em branco`)
        }
    }

    for (const field of ['name', 'locale', 'timezone', 'brandTheme'] as const) {
        const manifest = { ...baseManifest, [field]: '   ' }
        const report = validateProjectManifest(manifest)
        assert.equal(report.valid, false, `core aceitou project.${field} em branco`)
        assert.equal(report.errors.length, 1)
        assert.match(report.errors[0]!.code, /^PROJECT_[A-Z_]+_REQUIRED$/)
        assert.equal(projectSchemaCheck(manifest), false, `schema aceitou project.${field} em branco`)
    }

    const withBlankMetadata = {
        ...compositionWithAssetPath('assets/tela-01.png'),
        metadata: { description: '  ' },
    }
    assert.deepEqual(errorsOfComposition(validateComposition(withBlankMetadata, baseManifest)), ['COMPOSITION_METADATA_INVALID'])
    assert.equal(compositionSchemaCheck(withBlankMetadata), false)

    const withBlankTag = {
        ...compositionWithAssetPath('assets/tela-01.png'),
        metadata: { tags: ['campanha', '   '] },
    }
    assert.deepEqual(errorsOfComposition(validateComposition(withBlankTag, baseManifest)), ['COMPOSITION_METADATA_INVALID'])
    assert.equal(compositionSchemaCheck(withBlankTag), false)
})

test('durationMs respeita o inteiro seguro tambien no schema', () => {
    const document = compositionWithAssetPath('assets/tela-01.png')
    const scenes = document.scenes as Record<string, unknown>[]

    scenes[0]!.durationMs = Number.MAX_SAFE_INTEGER
    assert.equal(validateComposition(document, baseManifest).valid, true)
    assert.equal(compositionSchemaCheck(document), true)

    for (const invalid of [Number.MAX_SAFE_INTEGER + 1, 1.5, 0, -1]) {
        scenes[0]!.durationMs = invalid
        assert.deepEqual(errorsOfComposition(validateComposition(document, baseManifest)), ['COMPOSITION_SCENE_DURATION_INVALID'])
        assert.equal(compositionSchemaCheck(document), false, `schema aceitou durationMs ${invalid}`)
    }
})

test('a classificacao lexica e pura, com ordem fixa e sem efeitos colaterais', () => {
    const hostile = `/assets${NUL}/../.env`
    const frozen = hostile
    const first = inspectRelativePath(hostile)
    const second = inspectRelativePath(hostile)

    assert.deepEqual(first, ['CONTROL_CHARACTER', 'ABSOLUTE', 'TRAVERSAL', 'SENSITIVE'])
    assert.deepEqual(second, first)
    assert.notEqual(first, second)
    assert.equal(hostile, frozen)

    // A ordem de emissao e a da classificacao compartilhada, nos dois contratos.
    assert.deepEqual(errorsOfProject(validateProjectManifest(manifestWith(hostile))), [
        'PROJECT_ASSET_ROOT_CONTROL_CHARACTER',
        'PROJECT_ASSET_ROOT_ABSOLUTE',
        'PROJECT_ASSET_ROOT_TRAVERSAL',
        'PROJECT_ASSET_ROOT_SENSITIVE',
    ])
    assert.deepEqual(errorsOfComposition(validateComposition(compositionWithAssetPath(hostile), baseManifest)), [
        'COMPOSITION_ASSET_PATH_CONTROL_CHARACTER',
        'COMPOSITION_ASSET_PATH_ABSOLUTE',
        'COMPOSITION_ASSET_PATH_TRAVERSAL',
        'COMPOSITION_ASSET_PATH_SENSITIVE',
    ])

    assert.deepEqual(inspectRelativePath('assets/secretaria.png'), [])
    assert.deepEqual(pathSegments(`a${B}b/c`), ['a', 'b', 'c'])
    assert.equal(containsControlCharacter('assets/ok.png'), false)
    assert.equal(containsControlCharacter(`assets${String.fromCharCode(31)}.png`), true)
    assert.deepEqual(inspectRelativePath(''), [])
    assert.deepEqual(inspectRelativePath(`//example.com/x/../.env`), ['URL', 'TRAVERSAL', 'SENSITIVE'])
})

/**
 * Divergencias registradas de proposito (documentadas em platform/README.md na
 * secao "Schema x core"): aqui o teste nao exige concordancia, exige a diferenca
 * conhecida, para que uma mudanca futura em qualquer lado seja percebida.
 */
test('regras semanticas de nomes permanecem apenas no core', () => {
    const coreOnlyPaths: readonly string[] = [
        'assets/secret.txt',
        'assets/secrets',
        'assets/secret/README.md',
        'assets/api-secrets.yaml',
        'assets/service_account.json',
        'assets/private_key.txt',
    ]

    for (const value of coreOnlyPaths) {
        assert.deepEqual(inspectRelativePath(value), ['SENSITIVE'])

        const manifest = manifestWith(value)
        assert.deepEqual(errorsOfProject(validateProjectManifest(manifest)), ['PROJECT_ASSET_ROOT_SENSITIVE'])
        assert.equal(projectSchemaCheck(manifest), true, `o schema deveria aceitar (regra de tokens e do core): ${value}`)

        const composition = compositionWithAssetPath(value)
        assert.deepEqual(errorsOfComposition(validateComposition(composition, baseManifest)), ['COMPOSITION_ASSET_PATH_SENSITIVE'])
        assert.equal(compositionSchemaCheck(composition), true, `o schema deveria aceitar (regra de tokens e do core): ${value}`)
    }
})

test('regras do parser de URL permanecem apenas no core', () => {
    for (const href of ['https://:8443', 'https://exa mple.com']) {
        const composition = compositionWithHref(href)
        assert.deepEqual(errorsOfComposition(validateComposition(composition, baseManifest)), ['COMPOSITION_CTA_HREF_INVALID'])
        assert.equal(compositionSchemaCheck(composition), true, `o schema deveria aceitar: ${href}`)
    }
})

test('o schema exige a forma canonica scheme://host; o core usa o parser de URL', () => {
    for (const href of ['http:/example.com', `https:${B}${B}example.com`]) {
        const composition = compositionWithHref(href)
        assert.equal(validateComposition(composition, baseManifest).valid, true, `o core deveria aceitar: ${href}`)
        assert.equal(compositionSchemaCheck(composition), false, `o schema exige // depois do protocolo: ${href}`)
    }
})

test('os exemplos oficiais continuam validos depois do endurecimento', () => {
    const fixture = JSON.parse(readFileSync(path.join(moduleRoot, 'examples', 'projects', 'fixture-project.project.json'), 'utf8')) as Record<string, unknown>
    const marcaSalao = JSON.parse(readFileSync(path.join(moduleRoot, 'examples', 'projects', 'marca-salao.project.json'), 'utf8')) as Record<string, unknown>

    assert.equal(validateProjectManifest(fixture).valid, true)
    assert.equal(projectSchemaCheck(fixture), true)
    assert.equal(validateProjectManifest(marcaSalao).valid, true)
    assert.equal(projectSchemaCheck(marcaSalao), true)

    const officialExamples: readonly { composition: string; project: string }[] = [
        { composition: 'fixture-project-pilot.composition.json', project: 'fixture-project.project.json' },
        { composition: 'marca-salao-pilot.composition.json', project: 'marca-salao.project.json' },
    ]

    for (const { composition: compositionFile, project: projectFile } of officialExamples) {
        const composition = JSON.parse(readFileSync(path.join(moduleRoot, 'examples', 'compositions', compositionFile), 'utf8')) as Record<string, unknown>
        const project = JSON.parse(readFileSync(path.join(moduleRoot, 'examples', 'projects', projectFile), 'utf8')) as Record<string, unknown>

        assert.equal(validateComposition(composition, project).valid, true, `core rejeitou ${compositionFile}`)
        assert.equal(compositionSchemaCheck(composition), true, `schema rejeitou ${compositionFile}`)
    }
})
