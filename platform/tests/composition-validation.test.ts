import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

import { validateComposition } from '../src/validate-composition.js'
import type { CompositionValidationReport, ValidationIssue } from '../src/validation-report.js'

/**
 * Os testes sempre executam sobre JavaScript compilado (dist/tests). O root do
 * modulo e localizado subindo ate o package.json, como na suite de projeto.
 */
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
const projectsDir = path.join(moduleRoot, 'examples', 'projects')
const compositionsDir = path.join(moduleRoot, 'examples', 'compositions')
const cliPath = path.join(moduleRoot, 'dist', 'src', 'validate-composition-cli.js')
const coreScanDirectories = [
    path.join(moduleRoot, 'src'),
    path.join(moduleRoot, 'schemas'),
]

function readProjectExample(name: string): unknown {
    return JSON.parse(readFileSync(path.join(projectsDir, name), 'utf8'))
}

function readCompositionExample(name: string): unknown {
    return JSON.parse(readFileSync(path.join(compositionsDir, name), 'utf8'))
}

function codesOf(report: CompositionValidationReport): string[] {
    return report.errors.map((item: ValidationIssue) => item.code)
}

function projectWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'projeto-teste',
        name: 'Projeto Teste',
        locale: 'pt-BR',
        timezone: 'America/Sao_Paulo',
        brandTheme: 'tema-teste',
        assetRoot: 'projects/projeto-teste/assets',
        contentPolicies: {
            requireApprovedBriefing: true,
            requireApprovedScript: true,
            prohibitPersonalData: true,
            requireFunctionalEvidence: true,
        },
        outputProfiles: ['vertical-social'],
        ...overrides,
    }
}

function compositionWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        id: 'comp-teste',
        title: 'Composicao Teste',
        locale: 'pt-BR',
        format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
        scenes: [
            { id: 'opening', type: 'text', durationMs: 3000, content: { text: 'Texto de teste.' } },
        ],
        renderer: { adapter: 'undecided' },
        ...overrides,
    }
}

function sceneWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        id: 'opening',
        type: 'text',
        durationMs: 3000,
        content: { text: 'Texto de teste.' },
        ...overrides,
    }
}

const baseProject = projectWith({})

function runCli(args: string[]): { status: number | null; stdout: string; stderr: string } {
    const result = spawnSync(process.execPath, [cliPath, ...args], { encoding: 'utf8' })
    return {
        status: result.status,
        stdout: result.stdout ?? '',
        stderr: result.stderr ?? '',
    }
}

test('exemplo marca-salao-pilot passa contra o projeto marca-salao', () => {
    const report = validateComposition(
        readCompositionExample('marca-salao-pilot.composition.json'),
        readProjectExample('marca-salao.project.json'),
    )
    assert.equal(report.valid, true)
    assert.deepEqual(report.errors, [])
    assert.equal(report.projectId, 'marca-salao')
    assert.equal(report.compositionId, 'pilot-composition')
    assert.equal(report.sceneCount, 3)
    assert.equal(report.totalDurationMs, 10000)
    assert.deepEqual(report.format, { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 })
    assert.equal(report.rendererAdapter, 'undecided')
})

test('exemplo fixture-project-pilot passa contra o projeto fixture-project', () => {
    const report = validateComposition(
        readCompositionExample('fixture-project-pilot.composition.json'),
        readProjectExample('fixture-project.project.json'),
    )
    assert.equal(report.valid, true)
    assert.deepEqual(report.errors, [])
    assert.equal(report.projectId, 'fixture-project')
    assert.equal(report.sceneCount, 2)
    assert.equal(report.totalDurationMs, 5000)
    assert.deepEqual(report.format, { profile: 'square-social', width: 1080, height: 1080, fps: 24 })
})

test('o mesmo validador aceita composicoes dos dois projetos diferentes', () => {
    const marcaSalao = validateComposition(
        readCompositionExample('marca-salao-pilot.composition.json'),
        readProjectExample('marca-salao.project.json'),
    )
    const fixture = validateComposition(
        readCompositionExample('fixture-project-pilot.composition.json'),
        readProjectExample('fixture-project.project.json'),
    )

    assert.equal(marcaSalao.valid, true)
    assert.equal(fixture.valid, true)
    assert.notEqual(marcaSalao.projectId, fixture.projectId)
})

test('relatorio e deterministico para a mesma entrada', () => {
    const first = validateComposition(compositionWith({}), baseProject)
    const second = validateComposition(compositionWith({}), baseProject)
    assert.equal(JSON.stringify(first), JSON.stringify(second))
    assert.equal(first.warnings.length, 0)
})

test('projeto invalido produz COMPOSITION_PROJECT_MANIFEST_INVALID', () => {
    const report = validateComposition(compositionWith({}), projectWith({ id: 'Invalid_Id' }))
    assert.deepEqual(codesOf(report), ['COMPOSITION_PROJECT_MANIFEST_INVALID'])
})

test('schemaVersion diferente de 1 e rejeitado', () => {
    const report = validateComposition(compositionWith({ schemaVersion: 2 }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_SCHEMA_VERSION_UNSUPPORTED'])
})

test('campo desconhecido no topo produz COMPOSITION_UNKNOWN_FIELD', () => {
    const report = validateComposition(compositionWith({ beats: [] }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_UNKNOWN_FIELD'])
})

test('projectId ausente e projectId fora de kebab-case', () => {
    const missing = compositionWith({})
    delete missing.projectId
    assert.deepEqual(codesOf(validateComposition(missing, baseProject)), ['COMPOSITION_PROJECT_ID_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ projectId: 'Projeto_Teste' }), baseProject)),
        ['COMPOSITION_PROJECT_ID_INVALID'],
    )
})

test('id ausente e id invalido', () => {
    const missing = compositionWith({})
    delete missing.id
    assert.deepEqual(codesOf(validateComposition(missing, baseProject)), ['COMPOSITION_ID_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ id: 'Comp Teste' }), baseProject)),
        ['COMPOSITION_ID_INVALID'],
    )
})

test('title e locale obrigatorios', () => {
    assert.deepEqual(codesOf(validateComposition(compositionWith({ title: '  ' }), baseProject)), ['COMPOSITION_TITLE_REQUIRED'])
    const missingLocale = compositionWith({})
    delete missingLocale.locale
    assert.deepEqual(codesOf(validateComposition(missingLocale, baseProject)), ['COMPOSITION_LOCALE_REQUIRED'])
})

test('format ausente e campos de format invalidos', () => {
    assert.deepEqual(codesOf(validateComposition(compositionWith({ format: null }), baseProject)), ['COMPOSITION_FORMAT_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ format: { profile: 'Vertical_Social', width: 1080, height: 1920, fps: 30 } }), baseProject)),
        ['COMPOSITION_FORMAT_PROFILE_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ format: { profile: 'vertical-social', width: 0, height: 1920, fps: 30 } }), baseProject)),
        ['COMPOSITION_FORMAT_WIDTH_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ format: { profile: 'vertical-social', width: 1080, height: -1, fps: 30 } }), baseProject)),
        ['COMPOSITION_FORMAT_HEIGHT_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 0 } }), baseProject)),
        ['COMPOSITION_FORMAT_FPS_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 121 } }), baseProject)),
        ['COMPOSITION_FORMAT_FPS_INVALID'],
    )
    const highFps = validateComposition(
        compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 120 } }),
        baseProject,
    )
    assert.equal(highFps.valid, true, 'fps 120 deve ser aceito')
})

test('scenes ausente e cena malformada', () => {
    assert.deepEqual(codesOf(validateComposition(compositionWith({ scenes: 'nenhuma' }), baseProject)), ['COMPOSITION_SCENES_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: ['texto'] }), baseProject)),
        ['COMPOSITION_SCENE_INVALID'],
    )
})

test('id de cena duplicado e id de cena invalido', () => {
    const duplicated = compositionWith({
        scenes: [sceneWith({}), sceneWith({})],
    })
    assert.deepEqual(codesOf(validateComposition(duplicated, baseProject)), ['COMPOSITION_SCENE_ID_DUPLICATE'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: [sceneWith({ id: 'Abertura' })] }), baseProject)),
        ['COMPOSITION_SCENE_ID_INVALID'],
    )
})

test('type fora da lista e durationMs invalido', () => {
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: [sceneWith({ type: 'audio' })] }), baseProject)),
        ['COMPOSITION_SCENE_TYPE_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: [sceneWith({ durationMs: 0 })] }), baseProject)),
        ['COMPOSITION_SCENE_DURATION_INVALID'],
    )
})

test('content obrigatorio e forma fechada por tipo', () => {
    const missingContent = sceneWith({})
    delete missingContent.content
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: [missingContent] }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_REQUIRED'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ content: { text: 'Oi', asset: { id: 'a-1', path: 'assets/a.png' } } })],
        }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'image', content: { text: 'Oi' } })],
        }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN', 'COMPOSITION_SCENE_CONTENT_ASSET_REQUIRED'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ content: { text: '' } })],
        }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_TEXT_REQUIRED'],
    )
})

test('href de cta aceita somente http(s) sem credenciais', () => {
    const valid = validateComposition(compositionWith({
        scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'https://example.com' } })],
    }), baseProject)
    assert.equal(valid.valid, true)
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'ftp://example.com' } })],
        }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_HREF_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'https://user:pass@example.com' } })],
        }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_HREF_INVALID'],
    )
})

test('asset path rejeita absoluto, traversal, url e sensiveis', () => {
    const assetScene = (assetPath: string) => compositionWith({
        scenes: [sceneWith({ type: 'image', content: { asset: { id: 'screen-01', path: assetPath } } })],
    })
    assert.deepEqual(codesOf(validateComposition(assetScene('/etc/passwd'), baseProject)), ['COMPOSITION_ASSET_PATH_INVALID'])
    assert.deepEqual(codesOf(validateComposition(assetScene('../fora.png'), baseProject)), ['COMPOSITION_ASSET_PATH_INVALID'])
    assert.deepEqual(codesOf(validateComposition(assetScene('https://example.com/a.png'), baseProject)), ['COMPOSITION_ASSET_PATH_INVALID'])
    assert.deepEqual(codesOf(validateComposition(assetScene('secrets/.env'), baseProject)), ['COMPOSITION_ASSET_PATH_SENSITIVE'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'image', content: { asset: { id: 'Screen_01', path: 'assets/a.png' } } })],
        }), baseProject)),
        ['COMPOSITION_ASSET_ID_INVALID'],
    )
})

test('renderer obrigatorio, adapter kebab-case e options nao suportado', () => {
    const missingRenderer = compositionWith({})
    delete missingRenderer.renderer
    assert.deepEqual(codesOf(validateComposition(missingRenderer, baseProject)), ['COMPOSITION_RENDERER_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ renderer: { adapter: 'HTML_CSS' } }), baseProject)),
        ['COMPOSITION_RENDERER_ADAPTER_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ renderer: { adapter: 'undecided', options: { token: 'x' } } }), baseProject)),
        ['COMPOSITION_RENDERER_OPTIONS_UNSUPPORTED'],
    )
})

test('metadata fechada: status, description e tags', () => {
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ metadata: { status: 'published' } }), baseProject)),
        ['COMPOSITION_METADATA_STATUS_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ metadata: { extra: 1 } }), baseProject)),
        ['COMPOSITION_METADATA_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ metadata: { tags: ['a', 'a'] } }), baseProject)),
        ['COMPOSITION_METADATA_TAG_DUPLICATE'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ metadata: { tags: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'] } }), baseProject)),
        ['COMPOSITION_METADATA_TAGS_INVALID'],
    )
    const approved = validateComposition(compositionWith({ metadata: { status: 'approved' } }), baseProject)
    assert.equal(approved.valid, true, 'approved e um status tecnico valido, sem efeito editorial')
})

test('vinculos com o projeto: projectId, locale e profile', () => {
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ projectId: 'outro-projeto' }), baseProject)),
        ['COMPOSITION_PROJECT_ID_MISMATCH'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ locale: 'en-US' }), baseProject)),
        ['COMPOSITION_LOCALE_MISMATCH'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            format: { profile: 'square-social', width: 1080, height: 1080, fps: 30 },
        }), baseProject)),
        ['COMPOSITION_PROFILE_NOT_IN_PROJECT'],
    )
})

test('totalDurationMs soma somente duracoes inteiras positivas', () => {
    const report = validateComposition(compositionWith({
        scenes: [
            sceneWith({ id: 'a', durationMs: 1500 }),
            sceneWith({ id: 'b', durationMs: 2500 }),
            sceneWith({ id: 'c', durationMs: -5 }),
        ],
    }), baseProject)
    assert.equal(report.totalDurationMs, 4000)
    assert.equal(report.sceneCount, 3)
})

test('CLI retorna exit 0 e JSON valido para o exemplo marca-salao', () => {
    const result = runCli([
        '--project',
        path.join(projectsDir, 'marca-salao.project.json'),
        '--composition',
        path.join(compositionsDir, 'marca-salao-pilot.composition.json'),
        '--json',
    ])
    assert.equal(result.status, 0)
    const report = JSON.parse(result.stdout) as CompositionValidationReport
    assert.equal(report.valid, true)
    assert.equal(report.projectId, 'marca-salao')
})

test('CLI retorna exit 1 para composicao invalida e exit 2 para uso incorreto', () => {
    const tempDir = mkdtempSync(path.join(tmpdir(), 'composition-cli-'))
    try {
        const badPath = path.join(tempDir, 'bad.composition.json')
        writeFileSync(badPath, JSON.stringify(compositionWith({ schemaVersion: 9 })), 'utf8')
        const invalid = runCli([
            '--project',
            path.join(projectsDir, 'marca-salao.project.json'),
            '--composition',
            badPath,
        ])
        assert.equal(invalid.status, 1)
        assert.match(invalid.stdout, /COMPOSITION_SCHEMA_VERSION_UNSUPPORTED/)

        assert.equal(runCli([]).status, 2)
        assert.match(runCli([]).stderr, /Uso:/)
        assert.equal(runCli([
            '--project',
            path.join(projectsDir, 'nao-existe.json'),
            '--composition',
            badPath,
        ]).status, 2)

        const malformed = path.join(tempDir, 'malformed.json')
        writeFileSync(malformed, '{ nao e json', 'utf8')
        assert.equal(runCli([
            '--project',
            path.join(projectsDir, 'marca-salao.project.json'),
            '--composition',
            malformed,
        ]).status, 2)
    } finally {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

test('o nucleo de composicao nao contem referencia a projetos ou fornecedores', () => {
    const forbidden = [
        'marca salão',
        'marca-salao',
        'ns-001',
        'marcasalao.com.br',
        'hyperframes',
    ]

    for (const directory of coreScanDirectories) {
        for (const entry of readdirSync(directory)) {
            const content = readFileSync(path.join(directory, entry), 'utf8').toLowerCase()
            for (const needle of forbidden) {
                assert.ok(
                    !content.includes(needle),
                    `Referencia proibida "${needle}" encontrada em ${path.join(directory, entry)}`,
                )
            }
        }
    }
})

test('o schema de composicao declara a mesma superficie do contrato', () => {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'composition.schema.json'), 'utf8')) as {
        additionalProperties?: boolean
        required?: string[]
        properties?: Record<string, unknown>
    }

    assert.equal(schema.additionalProperties, false)
    assert.deepEqual(schema.required, [
        'schemaVersion',
        'projectId',
        'id',
        'title',
        'locale',
        'format',
        'scenes',
        'renderer',
    ])
    assert.deepEqual(Object.keys(schema.properties ?? {}).sort(), [
        'format',
        'id',
        'locale',
        'metadata',
        'projectId',
        'renderer',
        'scenes',
        'schemaVersion',
        'title',
    ])
})
