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

function warningCodesOf(report: CompositionValidationReport): string[] {
    return report.warnings.map((item: ValidationIssue) => item.code)
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
    assert.deepEqual(warningCodesOf(report), ['COMPOSITION_RENDERER_UNDECIDED'])
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
    assert.deepEqual(warningCodesOf(report), ['COMPOSITION_RENDERER_UNDECIDED'])
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

test('os quatro tipos de cena e as formas de content sao aceitos', () => {
    const report = validateComposition(compositionWith({
        scenes: [
            sceneWith({ id: 'texto', type: 'text', content: { text: 'Texto.', accessibilityLabel: 'Texto.' } }),
            sceneWith({ id: 'imagem', type: 'image', durationMs: 2000, content: { asset: { id: 'a-1', path: 'assets/a.png' }, alt: 'Alt.' } }),
            sceneWith({ id: 'video', type: 'video', durationMs: 2000, content: { asset: { id: 'v-1', path: 'assets/v.mp4' } } }),
            sceneWith({ id: 'chamada', type: 'cta', durationMs: 2000, content: { text: 'Veja.', href: 'https://example.com' } }),
        ],
    }), baseProject)
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.sceneCount, 4)
    assert.equal(report.totalDurationMs, 9000)
})

test('relatorio e deterministico para a mesma entrada, com warnings estaveis', () => {
    const first = validateComposition(compositionWith({}), baseProject)
    const second = validateComposition(compositionWith({}), baseProject)
    assert.equal(JSON.stringify(first), JSON.stringify(second))
    assert.equal(first.warnings.length, 1)
})

test('inputs nao sao mutados pelo validador', () => {
    const composition = compositionWith({})
    const project = projectWith({})
    const compositionBefore = JSON.stringify(composition)
    const projectBefore = JSON.stringify(project)
    validateComposition(composition, project)
    assert.equal(JSON.stringify(composition), compositionBefore)
    assert.equal(JSON.stringify(project), projectBefore)
})

test('projeto invalido produz COMPOSITION_MANIFEST_INVALID', () => {
    const report = validateComposition(compositionWith({}), projectWith({ id: 'Invalid_Id' }))
    assert.deepEqual(codesOf(report), ['COMPOSITION_MANIFEST_INVALID'])
})

test('schemaVersion diferente de 1 e rejeitado', () => {
    const report = validateComposition(compositionWith({ schemaVersion: 2 }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_SCHEMA_VERSION_UNSUPPORTED'])
})

test('campo desconhecido no topo produz COMPOSITION_UNKNOWN_FIELD', () => {
    const report = validateComposition(compositionWith({ beats: [] }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_UNKNOWN_FIELD'])
})

test('projectId ausente, invalido e divergente do projeto', () => {
    const missing = compositionWith({})
    delete missing.projectId
    assert.deepEqual(codesOf(validateComposition(missing, baseProject)), ['COMPOSITION_PROJECT_ID_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ projectId: 'Projeto_Teste' }), baseProject)),
        ['COMPOSITION_PROJECT_ID_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ projectId: 'outro-projeto' }), baseProject)),
        ['COMPOSITION_PROJECT_ID_MISMATCH'],
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

test('title e locale obrigatorios; locale divergente do projeto', () => {
    assert.deepEqual(codesOf(validateComposition(compositionWith({ title: '  ' }), baseProject)), ['COMPOSITION_TITLE_REQUIRED'])
    const missingLocale = compositionWith({})
    delete missingLocale.locale
    assert.deepEqual(codesOf(validateComposition(missingLocale, baseProject)), ['COMPOSITION_LOCALE_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ locale: 'en-US' }), baseProject)),
        ['COMPOSITION_LOCALE_MISMATCH'],
    )
})

test('format ausente e campos de format invalidos', () => {
    assert.deepEqual(codesOf(validateComposition(compositionWith({ format: null }), baseProject)), ['COMPOSITION_FORMAT_REQUIRED'])
    const missingProfile = compositionWith({ format: { width: 1080, height: 1920, fps: 30 } })
    assert.deepEqual(codesOf(validateComposition(missingProfile, baseProject)), ['COMPOSITION_FORMAT_PROFILE_REQUIRED'])
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

test('profile fora de outputProfiles produz COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED', () => {
    const report = validateComposition(compositionWith({
        format: { profile: 'square-social', width: 1080, height: 1080, fps: 30 },
    }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED'])
})

test('scenes ausente e cena malformada', () => {
    assert.deepEqual(codesOf(validateComposition(compositionWith({ scenes: 'nenhuma' }), baseProject)), ['COMPOSITION_SCENE_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: ['texto'] }), baseProject)),
        ['COMPOSITION_SCENE_INVALID'],
    )
})

test('id de cena ausente, invalido e duplicado', () => {
    const missingId = sceneWith({})
    delete missingId.id
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ scenes: [missingId] }), baseProject)),
        ['COMPOSITION_SCENE_ID_REQUIRED'],
    )
    const duplicated = compositionWith({ scenes: [sceneWith({}), sceneWith({})] })
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

test('content obrigatorio, texto obrigatorio e forma fechada por tipo', () => {
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
        ['COMPOSITION_ASSET_NOT_ALLOWED'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'image', content: { text: 'Oi' } })],
        }), baseProject)),
        ['COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN', 'COMPOSITION_ASSET_REQUIRED'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ content: { text: '' } })],
        }), baseProject)),
        ['COMPOSITION_TEXT_REQUIRED'],
    )
})

test('href de cta: http e https validos; demais protocolos, relativa, credenciais e malformada rejeitados', () => {
    const http = validateComposition(compositionWith({
        scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'http://example.com' } })],
    }), baseProject)
    assert.equal(http.valid, true)
    const https = validateComposition(compositionWith({
        scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'https://example.com' } })],
    }), baseProject)
    assert.equal(https.valid, true)
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'ftp://example.com' } })],
        }), baseProject)),
        ['COMPOSITION_CTA_HREF_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: '/relativa' } })],
        }), baseProject)),
        ['COMPOSITION_CTA_HREF_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'https://user:pass@example.com' } })],
        }), baseProject)),
        ['COMPOSITION_CTA_HREF_CREDENTIALS'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'cta', content: { text: 'Veja', href: 'https://' } })],
        }), baseProject)),
        ['COMPOSITION_CTA_HREF_INVALID'],
    )
})

test('asset path: matriz de seguranca de caminhos', () => {
    const assetScene = (assetPath: string) => compositionWith({
        scenes: [sceneWith({ type: 'image', content: { asset: { id: 'screen-01', path: assetPath } } })],
    })
    const cases: Array<[string, string]> = [
        ['C:\\dados\\a.png', 'COMPOSITION_ASSET_PATH_ABSOLUTE'],
        ['/etc/passwd', 'COMPOSITION_ASSET_PATH_ABSOLUTE'],
        ['\\\\servidor\\share\\a.png', 'COMPOSITION_ASSET_PATH_ABSOLUTE'],
        ['../fora.png', 'COMPOSITION_ASSET_PATH_TRAVERSAL'],
        ['..\\fora.png', 'COMPOSITION_ASSET_PATH_TRAVERSAL'],
        ['config/.env', 'COMPOSITION_ASSET_PATH_SENSITIVE'],
        ['config/.env.local', 'COMPOSITION_ASSET_PATH_SENSITIVE'],
        ['certs/a.pem', 'COMPOSITION_ASSET_PATH_SENSITIVE'],
        ['certs/a.key', 'COMPOSITION_ASSET_PATH_SENSITIVE'],
        ['http://example.com/a.png', 'COMPOSITION_ASSET_PATH_URL'],
        ['https://example.com/a.png', 'COMPOSITION_ASSET_PATH_URL'],
        ['//example.com/a.png', 'COMPOSITION_ASSET_PATH_URL'],
        ['file:///tmp/a.png', 'COMPOSITION_ASSET_PATH_URL'],
        ['', 'COMPOSITION_ASSET_PATH_REQUIRED'],
    ]
    for (const [assetPath, expectedCode] of cases) {
        const report = validateComposition(assetScene(assetPath), baseProject)
        assert.deepEqual(codesOf(report), [expectedCode], `caminho ${assetPath || '(vazio)'}`)
    }
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({
            scenes: [sceneWith({ type: 'image', content: { asset: { id: 'Screen_01', path: 'assets/a.png' } } })],
        }), baseProject)),
        ['COMPOSITION_ASSET_ID_INVALID'],
    )
})

test('renderer obrigatorio, adapter kebab-case, undecided aceito e options rejeitado', () => {
    const missingRenderer = compositionWith({})
    delete missingRenderer.renderer
    assert.deepEqual(codesOf(validateComposition(missingRenderer, baseProject)), ['COMPOSITION_RENDERER_REQUIRED'])
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ renderer: {} }), baseProject)),
        ['COMPOSITION_RENDERER_ADAPTER_REQUIRED'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ renderer: { adapter: 'HTML_CSS' } }), baseProject)),
        ['COMPOSITION_RENDERER_ADAPTER_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ renderer: { adapter: 'undecided', options: { token: 'x' } } }), baseProject)),
        ['COMPOSITION_RENDERER_OPTIONS_UNSUPPORTED'],
    )
    const decided = validateComposition(compositionWith({ renderer: { adapter: 'html-css-ffmpeg' } }), baseProject)
    assert.equal(decided.valid, true)
    assert.deepEqual(warningCodesOf(decided), [])
})

test('metadata: ausencia valida, status validos, tags limitadas e campos fechados', () => {
    const withoutMetadata = compositionWith({})
    delete withoutMetadata.metadata
    assert.equal(validateComposition(withoutMetadata, baseProject).valid, true)

    for (const status of ['draft', 'review', 'approved', 'archived']) {
        const report = validateComposition(compositionWith({ metadata: { status } }), baseProject)
        assert.equal(report.valid, true, `status ${status} deve ser tecnicamente valido`)
    }

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
        ['COMPOSITION_METADATA_INVALID'],
    )
    assert.deepEqual(
        codesOf(validateComposition(compositionWith({ metadata: { tags: [''] } }), baseProject)),
        ['COMPOSITION_METADATA_INVALID'],
    )
})

test('warnings heuristicos: texto longo e cena curta com texto, em ordem estavel', () => {
    const longText = 'x'.repeat(161)
    const report = validateComposition(compositionWith({
        renderer: { adapter: 'html-css-ffmpeg' },
        scenes: [
            sceneWith({ id: 'curta', durationMs: 500, content: { text: longText } }),
            sceneWith({ id: 'longa', durationMs: 2000, content: { text: longText } }),
        ],
    }), baseProject)
    assert.equal(report.valid, true, 'warnings nao invalidam a composicao')
    assert.deepEqual(warningCodesOf(report), [
        'COMPOSITION_SCENE_TEXT_LONG',
        'COMPOSITION_SCENE_DURATION_SHORT',
        'COMPOSITION_SCENE_TEXT_LONG',
    ])
    const again = validateComposition(compositionWith({
        renderer: { adapter: 'html-css-ffmpeg' },
        scenes: [
            sceneWith({ id: 'curta', durationMs: 500, content: { text: longText } }),
            sceneWith({ id: 'longa', durationMs: 2000, content: { text: longText } }),
        ],
    }), baseProject)
    assert.equal(JSON.stringify(report.warnings), JSON.stringify(again.warnings))
})

test('soma de duracoes acima de MAX_SAFE_INTEGER produz COMPOSITION_DURATION_OVERFLOW', () => {
    const report = validateComposition(compositionWith({
        scenes: [
            sceneWith({ id: 'a', durationMs: Number.MAX_SAFE_INTEGER }),
            sceneWith({ id: 'b', durationMs: 1 }),
        ],
    }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_DURATION_OVERFLOW'])
    assert.equal(report.valid, false)
    assert.equal(report.totalDurationMs, null)
})

test('durationMs individual acima de MAX_SAFE_INTEGER e rejeitado como invalido', () => {
    const report = validateComposition(compositionWith({
        scenes: [sceneWith({ durationMs: Number.MAX_SAFE_INTEGER * 2 })],
    }), baseProject)
    assert.deepEqual(codesOf(report), ['COMPOSITION_SCENE_DURATION_INVALID'])
    assert.equal(report.totalDurationMs, 0)
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
    assert.ok(!result.stdout.includes('\\\\'), 'relatorio JSON nao pode conter caminho absoluto')
})

test('CLI retorna exit 1 para composicao ou projeto semanticamente invalidos', () => {
    const tempDir = mkdtempSync(path.join(tmpdir(), 'composition-cli-'))
    try {
        const badComposition = path.join(tempDir, 'bad.composition.json')
        writeFileSync(badComposition, JSON.stringify(compositionWith({ schemaVersion: 9 })), 'utf8')
        const invalidComposition = runCli([
            '--project',
            path.join(projectsDir, 'marca-salao.project.json'),
            '--composition',
            badComposition,
        ])
        assert.equal(invalidComposition.status, 1)
        assert.match(invalidComposition.stdout, /COMPOSITION_SCHEMA_VERSION_UNSUPPORTED/)
        assert.ok(!invalidComposition.stdout.includes('at '), 'sem stack trace')

        const badProject = path.join(tempDir, 'bad.project.json')
        writeFileSync(badProject, JSON.stringify(projectWith({ id: 'Invalid_Id' })), 'utf8')
        const invalidProject = runCli([
            '--project',
            badProject,
            '--composition',
            path.join(compositionsDir, 'marca-salao-pilot.composition.json'),
        ])
        assert.equal(invalidProject.status, 1)
        assert.match(invalidProject.stdout, /COMPOSITION_MANIFEST_INVALID/)
    } finally {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

test('CLI retorna exit 2 para uso incorreto, arquivos inexistentes e JSON malformado', () => {
    const tempDir = mkdtempSync(path.join(tmpdir(), 'composition-cli-'))
    try {
        assert.equal(runCli([]).status, 2)
        assert.match(runCli([]).stderr, /Uso:/)
        assert.equal(runCli([
            '--project',
            path.join(projectsDir, 'nao-existe.json'),
            '--composition',
            path.join(compositionsDir, 'marca-salao-pilot.composition.json'),
        ]).status, 2)
        assert.equal(runCli([
            '--project',
            path.join(projectsDir, 'marca-salao.project.json'),
            '--composition',
            path.join(compositionsDir, 'nao-existe.json'),
        ]).status, 2)

        const malformed = path.join(tempDir, 'malformed.json')
        writeFileSync(malformed, '{ nao e json', 'utf8')
        assert.equal(runCli([
            '--project',
            path.join(projectsDir, 'marca-salao.project.json'),
            '--composition',
            malformed,
        ]).status, 2)
        assert.equal(runCli([
            '--project',
            malformed,
            '--composition',
            path.join(compositionsDir, 'marca-salao-pilot.composition.json'),
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
        'google flow',
        'elevenlabs',
        'ffmpeg',
        'capcut',
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

test('validador e CLI nao usam rede nem abrem assets', () => {
    const forbiddenCalls = ['fetch(', 'http.request', 'https.request', 'XMLHttpRequest', 'net.connect', 'readFile']
    for (const relative of ['src/validate-composition.ts', 'src/validate-composition-cli.ts']) {
        const content = readFileSync(path.join(moduleRoot, relative), 'utf8')
        for (const needle of forbiddenCalls) {
            if (needle === 'readFile') {
                assert.ok(
                    !content.includes('readFileSync(') || relative.endsWith('cli.ts'),
                    'somente a CLI pode ler arquivos; o validador nao',
                )
                continue
            }
            assert.ok(!content.includes(needle), `chamada proibida "${needle}" em ${relative}`)
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
