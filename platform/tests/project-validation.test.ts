import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

import { validateProjectManifest } from '../src/validate-project.js'
import type { ProjectValidationReport, ValidationIssue } from '../src/validation-report.js'

/**
 * Os testes sempre executam sobre JavaScript compilado (dist/tests). O root do
 * modulo e localizado subindo ate o package.json, o que funciona tanto com os
 * testes compilados (dist/tests -> ../..) quanto na arvore-fonte (tests -> ..).
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
const examplesDir = path.join(moduleRoot, 'examples', 'projects')
const cliPath = path.join(moduleRoot, 'dist', 'src', 'validate-project-cli.js')
const coreScanDirectories = [
    path.join(moduleRoot, 'src'),
    path.join(moduleRoot, 'schemas'),
]

function readExample(name: string): unknown {
    return JSON.parse(readFileSync(path.join(examplesDir, name), 'utf8'))
}

function codesOf(report: ProjectValidationReport): string[] {
    return report.errors.map((item: ValidationIssue) => item.code)
}

function manifestWith(overrides: Record<string, unknown>): Record<string, unknown> {
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

function runCli(args: string[]): { status: number | null; stdout: string; stderr: string } {
    const result = spawnSync(process.execPath, [cliPath, ...args], { encoding: 'utf8' })
    return {
        status: result.status,
        stdout: result.stdout ?? '',
        stderr: result.stderr ?? '',
    }
}

test('exemplo marca-salao passa no validador', () => {
    const report = validateProjectManifest(readExample('marca-salao.project.json'))
    assert.equal(report.valid, true)
    assert.equal(report.projectId, 'marca-salao')
    assert.deepEqual(report.errors, [])
    assert.equal(report.outputProfileCount, 1)
})

test('exemplo fixture-project passa no mesmo validador', () => {
    const report = validateProjectManifest(readExample('fixture-project.project.json'))
    assert.equal(report.valid, true)
    assert.equal(report.projectId, 'fixture-project')
    assert.deepEqual(report.errors, [])
    assert.equal(report.outputProfileCount, 1)
})

test('o mesmo validador aceita os dois projetos diferentes', () => {
    const marcaSalao = validateProjectManifest(readExample('marca-salao.project.json'))
    const fixture = validateProjectManifest(readExample('fixture-project.project.json'))

    assert.equal(marcaSalao.valid, true)
    assert.equal(fixture.valid, true)
    assert.notEqual(marcaSalao.projectId, fixture.projectId)
    assert.notEqual(marcaSalao.schemaVersion, null)
})

test('schemaVersion diferente de 1 e rejeitado', () => {
    const report = validateProjectManifest(manifestWith({ schemaVersion: 2 }))
    assert.deepEqual(codesOf(report), ['PROJECT_SCHEMA_VERSION_UNSUPPORTED'])
})

test('id ausente produz PROJECT_ID_REQUIRED', () => {
    const manifest = manifestWith({})
    delete (manifest as Record<string, unknown>).id
    const report = validateProjectManifest(manifest)
    assert.deepEqual(codesOf(report), ['PROJECT_ID_REQUIRED'])
})

test('id fora de kebab-case produz PROJECT_ID_INVALID', () => {
    const report = validateProjectManifest(manifestWith({ id: 'Marca_Salao' }))
    assert.deepEqual(codesOf(report), ['PROJECT_ID_INVALID'])
})

test('name ausente produz PROJECT_NAME_REQUIRED', () => {
    const manifest = manifestWith({})
    delete (manifest as Record<string, unknown>).name
    const report = validateProjectManifest(manifest)
    assert.deepEqual(codesOf(report), ['PROJECT_NAME_REQUIRED'])
})

test('locale ausente produz PROJECT_LOCALE_REQUIRED', () => {
    const manifest = manifestWith({})
    delete (manifest as Record<string, unknown>).locale
    const report = validateProjectManifest(manifest)
    assert.deepEqual(codesOf(report), ['PROJECT_LOCALE_REQUIRED'])
})

test('timezone ausente produz PROJECT_TIMEZONE_REQUIRED', () => {
    const manifest = manifestWith({})
    delete (manifest as Record<string, unknown>).timezone
    const report = validateProjectManifest(manifest)
    assert.deepEqual(codesOf(report), ['PROJECT_TIMEZONE_REQUIRED'])
})

test('brandTheme ausente produz PROJECT_BRAND_THEME_REQUIRED', () => {
    const manifest = manifestWith({})
    delete (manifest as Record<string, unknown>).brandTheme
    const report = validateProjectManifest(manifest)
    assert.deepEqual(codesOf(report), ['PROJECT_BRAND_THEME_REQUIRED'])
})

test('assetRoot absoluto Windows produz PROJECT_ASSET_ROOT_ABSOLUTE', () => {
    const report = validateProjectManifest(manifestWith({ assetRoot: 'C:\\projetos\\assets' }))
    assert.deepEqual(codesOf(report), ['PROJECT_ASSET_ROOT_ABSOLUTE'])
})

test('assetRoot absoluto POSIX produz PROJECT_ASSET_ROOT_ABSOLUTE', () => {
    const report = validateProjectManifest(manifestWith({ assetRoot: '/var/assets' }))
    assert.deepEqual(codesOf(report), ['PROJECT_ASSET_ROOT_ABSOLUTE'])
})

test('path traversal no assetRoot produz PROJECT_ASSET_ROOT_TRAVERSAL', () => {
    const report = validateProjectManifest(manifestWith({ assetRoot: 'projects/../fora/assets' }))
    assert.deepEqual(codesOf(report), ['PROJECT_ASSET_ROOT_TRAVERSAL'])
})

test('assetRoot apontando para .env produz PROJECT_ASSET_ROOT_SENSITIVE', () => {
    const report = validateProjectManifest(manifestWith({ assetRoot: 'projects/x/.env' }))
    assert.deepEqual(codesOf(report), ['PROJECT_ASSET_ROOT_SENSITIVE'])
})

test('assetRoot apontando para chave privada produz PROJECT_ASSET_ROOT_SENSITIVE', () => {
    const report = validateProjectManifest(manifestWith({ assetRoot: 'projects/x/keys/service_account.json' }))
    assert.deepEqual(codesOf(report), ['PROJECT_ASSET_ROOT_SENSITIVE'])
})

test('politica ausente produz PROJECT_CONTENT_POLICY_INVALID', () => {
    const policies = manifestWith({}).contentPolicies as Record<string, unknown>
    delete policies.requireApprovedBriefing
    const report = validateProjectManifest(manifestWith({ contentPolicies: policies }))
    assert.deepEqual(codesOf(report), ['PROJECT_CONTENT_POLICY_INVALID'])
    assert.equal(report.errors[0]?.path, 'contentPolicies.requireApprovedBriefing')
})

test('politica nao booleana produz PROJECT_CONTENT_POLICY_INVALID', () => {
    const policies = {
        requireApprovedBriefing: 'true',
        requireApprovedScript: true,
        prohibitPersonalData: true,
        requireFunctionalEvidence: true,
    }
    const report = validateProjectManifest(manifestWith({ contentPolicies: policies }))
    assert.deepEqual(codesOf(report), ['PROJECT_CONTENT_POLICY_INVALID'])
    assert.equal(report.errors[0]?.path, 'contentPolicies.requireApprovedBriefing')
})

test('outputProfiles vazio produz PROJECT_OUTPUT_PROFILE_REQUIRED', () => {
    const report = validateProjectManifest(manifestWith({ outputProfiles: [] }))
    assert.deepEqual(codesOf(report), ['PROJECT_OUTPUT_PROFILE_REQUIRED'])
})

test('profile invalido produz PROJECT_OUTPUT_PROFILE_INVALID', () => {
    const report = validateProjectManifest(manifestWith({ outputProfiles: ['Vertical Social'] }))
    assert.deepEqual(codesOf(report), ['PROJECT_OUTPUT_PROFILE_INVALID'])
})

test('profiles duplicados produzem PROJECT_OUTPUT_PROFILE_DUPLICATE', () => {
    const report = validateProjectManifest(manifestWith({ outputProfiles: ['vertical-social', 'vertical-social'] }))
    assert.deepEqual(codesOf(report), ['PROJECT_OUTPUT_PROFILE_DUPLICATE'])
    assert.equal(report.errors[0]?.path, 'outputProfiles[1]')
})

test('campo de topo desconhecido produz PROJECT_UNKNOWN_FIELD', () => {
    const report = validateProjectManifest(manifestWith({ camposSecreto: 'valor' }))
    assert.deepEqual(codesOf(report), ['PROJECT_UNKNOWN_FIELD'])
})

test('entrada que nao e objeto produz PROJECT_MANIFEST_INVALID', () => {
    const report = validateProjectManifest(['nao', 'sou', 'objeto'])
    assert.deepEqual(codesOf(report), ['PROJECT_MANIFEST_INVALID'])
    assert.equal(report.projectId, null)
    assert.equal(report.schemaVersion, null)
    assert.equal(report.outputProfileCount, 0)
})

test('o relatorio e deterministico para a mesma entrada', () => {
    const input = manifestWith({ id: 'ID Invalido', locale: undefined })
    const first = validateProjectManifest(input)
    const second = validateProjectManifest(structuredClone(input))

    assert.deepEqual(JSON.parse(JSON.stringify(second)), JSON.parse(JSON.stringify(first)))
})

test('a ordem dos erros e estavel e fixa', () => {
    const input = manifestWith({
        id: 'ID Invalido',
        name: '',
        locale: undefined,
        timezone: undefined,
        brandTheme: undefined,
        assetRoot: '/absoluto',
        outputProfiles: [],
    })

    const firstRun = codesOf(validateProjectManifest(input))
    const secondRun = codesOf(validateProjectManifest(structuredClone(input)))

    assert.deepEqual(secondRun, firstRun)
    assert.deepEqual(firstRun, [
        'PROJECT_ID_INVALID',
        'PROJECT_NAME_REQUIRED',
        'PROJECT_LOCALE_REQUIRED',
        'PROJECT_TIMEZONE_REQUIRED',
        'PROJECT_BRAND_THEME_REQUIRED',
        'PROJECT_ASSET_ROOT_ABSOLUTE',
        'PROJECT_OUTPUT_PROFILE_REQUIRED',
    ])
})

test('CLI retorna exit 0 e JSON valido para o exemplo marca-salao', () => {
    const result = runCli([
        '--project',
        path.join(examplesDir, 'marca-salao.project.json'),
        '--json',
    ])

    assert.equal(result.status, 0)
    const report = JSON.parse(result.stdout) as ProjectValidationReport
    assert.equal(report.valid, true)
    assert.equal(report.projectId, 'marca-salao')
    assert.equal(report.summary, 'Project manifest is valid.')
})

test('CLI retorna exit 0 para o fixture-project', () => {
    const result = runCli([
        '--project',
        path.join(examplesDir, 'fixture-project.project.json'),
        '--json',
    ])

    assert.equal(result.status, 0)
    const report = JSON.parse(result.stdout) as ProjectValidationReport
    assert.equal(report.valid, true)
    assert.equal(report.projectId, 'fixture-project')
})

test('CLI retorna exit diferente de zero para manifesto invalido', () => {
    const tempDir = mkdtempSync(path.join(tmpdir(), 'platform-cli-'))
    try {
        const invalidPath = path.join(tempDir, 'invalido.project.json')
        writeFileSync(invalidPath, JSON.stringify({ schemaVersion: 9 }), 'utf8')

        const result = runCli(['--project', invalidPath, '--json'])
        assert.equal(result.status, 1)
        const report = JSON.parse(result.stdout) as ProjectValidationReport
        assert.equal(report.valid, false)
        assert.ok(codesOf(report).includes('PROJECT_SCHEMA_VERSION_UNSUPPORTED'))
    } finally {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

test('CLI produz erro sanitizado para arquivo inexistente', () => {
    const result = runCli(['--project', path.join(tmpdir(), 'nao-existe.project.json'), '--json'])

    assert.equal(result.status, 2)
    assert.match(result.stderr, /arquivo nao encontrado/)
    assert.equal(result.stdout, '')
})

test('CLI produz erro sanitizado para JSON malformado', () => {
    const tempDir = mkdtempSync(path.join(tmpdir(), 'platform-cli-'))
    try {
        const malformedPath = path.join(tempDir, 'malformado.project.json')
        writeFileSync(malformedPath, '{ schemaVersion: sem aspas }', 'utf8')

        const result = runCli(['--project', malformedPath])
        assert.equal(result.status, 2)
        assert.match(result.stderr, /JSON malformado/)
        assert.equal(result.stdout, '')
    } finally {
        rmSync(tempDir, { recursive: true, force: true })
    }
})

test('CLI sem --project retorna erro de uso', () => {
    const result = runCli([])
    assert.equal(result.status, 2)
    assert.match(result.stderr, /Uso:/)
})

test('o nucleo nao contem condicional nem referencia a projetos especificos', () => {
    const forbidden = [
        'marca salão',
        'marca-salao',
        'ns-001',
        'marcasalao.com.br',
        'hyperframes',
    ]

    for (const directory of coreScanDirectories) {
        for (const file of coreSourceFiles(directory)) {
            const content = readFileSync(file, 'utf8').toLowerCase()
            for (const needle of forbidden) {
                assert.ok(
                    !content.includes(needle),
                    `Referencia proibida "${needle}" encontrada em ${file}`,
                )
            }
        }
    }
})

/**
 * Varredura recursiva: o nucleo passou a ter subpastas (`src/output-profiles/`),
 * e um readdirSync raso deixaria de ler esses arquivos sem avisar.
 */
function coreSourceFiles(directory: string): string[] {
    return readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
        entry.isDirectory() ? coreSourceFiles(path.join(directory, entry.name)) : [path.join(directory, entry.name)],
    )
}

test('o schema declara a mesma superficie do contrato', () => {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'project.schema.json'), 'utf8')) as {
        additionalProperties?: boolean
        required?: string[]
        properties?: Record<string, unknown>
    }

    assert.equal(schema.additionalProperties, false)
    assert.deepEqual(schema.required, [
        'schemaVersion',
        'id',
        'name',
        'locale',
        'timezone',
        'brandTheme',
        'assetRoot',
        'contentPolicies',
        'outputProfiles',
    ])
    assert.ok(schema.properties?.contentPolicies)
})
