/**
 * Executa os schemas JSON normativos (draft-07) em um motor real (ajv).
 * O validador TypeScript continua sendo a implementacao de referencia: estes
 * testes provam que o espelho em JSON Schema aceita exatamente o que o core
 * aceita e rejeita o que o core rejeita, inclusive a relacao tipo de cena x
 * forma de content.
 */
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateComposition } from '../src/validate-composition.js'

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

// strict desligado: o espelho normativo usa somente o vocabulario draft-07 e os
// avisos do strict mode dependeriam da versao do motor (saida nao estavel).
// O pacote e CommonJS: o construtor chega pela propriedade `default` do modulo.
const ajv = new AjvModule.default({ allErrors: true, strict: false })

interface SchemaCheck {
    valid: boolean
    detail: string
}

function compileSchema(file: string): (document: unknown) => SchemaCheck {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', file), 'utf8')) as AnySchemaObject
    const validate = ajv.compile(schema)
    return (document: unknown): SchemaCheck => {
        const valid = validate(document) === true
        const failures = (validate.errors ?? []).map(
            (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
        )
        return { valid, detail: failures.join(' | ') }
    }
}

const compositionSchemaCheck = compileSchema('composition.schema.json')
const projectSchemaCheck = compileSchema('project.schema.json')

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

const baseProject = projectWith({})

function scene(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        id: 'opening',
        type: 'text',
        durationMs: 3000,
        content: { text: 'Texto de teste.' },
        ...overrides,
    }
}

function withoutFields(value: Record<string, unknown>, keys: string[]): Record<string, unknown> {
    const copy = { ...value }
    for (const key of keys) delete copy[key]
    return copy
}

function compositionWith(scenes: Record<string, unknown>[], overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        id: 'comp-schema',
        title: 'Composicao Schema',
        locale: 'pt-BR',
        format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
        scenes,
        renderer: { adapter: 'undecided' },
        ...overrides,
    }
}

const safeAsset = { id: 'tela-01', path: 'projects/projeto-teste/assets/tela-01.png' }

interface ContractCase {
    name: string
    document: Record<string, unknown>
    valid: boolean
}

/**
 * Matriz obrigatoria de cena: o mesmo documento e avaliado pelo schema (ajv) e
 * pelo validador TypeScript, e ambos devem concordar com o resultado esperado.
 */
const sceneCases: readonly ContractCase[] = [
    // Aceitar
    { name: 'text com content.text', document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.' } })]), valid: true },
    {
        name: 'text com content.accessibilityLabel',
        document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.', accessibilityLabel: 'Rotulo de tela.' } })]),
        valid: true,
    },
    {
        name: 'cta com content.text e href https',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', href: 'https://example.com.br' } })]),
        valid: true,
    },
    {
        name: 'cta com content.text e href http',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', href: 'http://example.com.br' } })]),
        valid: true,
    },
    {
        name: 'cta com content.text sem href',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.' } })]),
        valid: true,
    },
    {
        name: 'cta com content.accessibilityLabel',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', accessibilityLabel: 'Chamada para o site.' } })]),
        valid: true,
    },
    {
        name: 'image com content.asset',
        document: compositionWith([scene({ type: 'image', content: { asset: safeAsset } })]),
        valid: true,
    },
    {
        name: 'image com content.asset, alt e accessibilityLabel',
        document: compositionWith([
            scene({ type: 'image', content: { asset: safeAsset, alt: 'Agenda do salao.', accessibilityLabel: 'Imagem da agenda.' } }),
        ]),
        valid: true,
    },
    {
        name: 'video com content.asset',
        document: compositionWith([scene({ type: 'video', content: { asset: safeAsset } })]),
        valid: true,
    },
    {
        name: 'video com content.asset e alt',
        document: compositionWith([scene({ type: 'video', content: { asset: safeAsset, alt: 'Demonstracao do agendamento.' } })]),
        valid: true,
    },
    // Rejeitar
    {
        name: 'text com content.href (proprio de cta)',
        document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.', href: 'https://example.com.br' } })]),
        valid: false,
    },
    {
        name: 'text com content.asset (proibido)',
        document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.', asset: safeAsset } })]),
        valid: false,
    },
    {
        name: 'text com content.alt (proibido)',
        document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.', alt: 'Alternativo.' } })]),
        valid: false,
    },
    {
        name: 'cta com content.asset (proibido)',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', asset: safeAsset } })]),
        valid: false,
    },
    {
        name: 'cta com content.alt (proibido)',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', alt: 'Alternativo.' } })]),
        valid: false,
    },
    {
        name: 'image sem content.asset (so text)',
        document: compositionWith([scene({ type: 'image', content: { text: 'Descricao.' } })]),
        valid: false,
    },
    {
        name: 'video sem content.asset (so text)',
        document: compositionWith([scene({ type: 'video', content: { text: 'Descricao.' } })]),
        valid: false,
    },
    {
        name: 'image com content.asset e text (incompativel)',
        document: compositionWith([scene({ type: 'image', content: { asset: safeAsset, text: 'Descricao.' } })]),
        valid: false,
    },
    {
        name: 'text sem content.text',
        document: compositionWith([scene({ type: 'text', content: { accessibilityLabel: 'Rotulo.' } })]),
        valid: false,
    },
    {
        name: 'text com content.text vazio',
        document: compositionWith([scene({ type: 'text', content: { text: '' } })]),
        valid: false,
    },
    {
        name: 'cta com href de protocolo nao http(s)',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', href: 'ftp://example.com.br' } })]),
        valid: false,
    },
    {
        name: 'cta com href relativo',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', href: '/agenda' } })]),
        valid: false,
    },
    {
        name: 'cta com href com credenciais',
        document: compositionWith([scene({ type: 'cta', content: { text: 'Conheca.', href: 'https://usuario:senha@example.com.br' } })]),
        valid: false,
    },
    {
        name: 'cena com campo desconhecido em content',
        document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.', estilo: 'neon' } })]),
        valid: false,
    },
    {
        name: 'cena com campo desconhecido na cena',
        document: compositionWith([scene({ type: 'text', content: { text: 'Abertura.' }, beat: 'abertura' })]),
        valid: false,
    },
    {
        name: 'cena com type desconhecido',
        document: compositionWith([scene({ type: 'audio', content: { text: 'Abertura.' } })]),
        valid: false,
    },
    {
        name: 'cena sem type',
        document: compositionWith([withoutFields(scene({ content: { text: 'Abertura.' } }), ['type'])]),
        valid: false,
    },
    { name: 'cena sem content', document: compositionWith([withoutFields(scene(), ['content'])]), valid: false },
    { name: 'cena sem durationMs', document: compositionWith([withoutFields(scene(), ['durationMs'])]), valid: false },
    { name: 'cena sem id', document: compositionWith([withoutFields(scene(), ['id'])]), valid: false },
    {
        name: 'cena com durationMs zero',
        document: compositionWith([scene({ durationMs: 0 })]),
        valid: false,
    },
    {
        name: 'asset com caminho absoluto POSIX',
        document: compositionWith([scene({ type: 'image', content: { asset: { id: 'tela-01', path: '/tmp/tela.png' } } })]),
        valid: false,
    },
    {
        name: 'asset com caminho absoluto Windows',
        document: compositionWith([scene({ type: 'image', content: { asset: { id: 'tela-01', path: 'C:\\dados\\tela.png' } } })]),
        valid: false,
    },
    {
        name: 'asset com traversal',
        document: compositionWith([scene({ type: 'image', content: { asset: { id: 'tela-01', path: '../tela.png' } } })]),
        valid: false,
    },
    {
        name: 'asset com URL',
        document: compositionWith([scene({ type: 'image', content: { asset: { id: 'tela-01', path: 'https://example.com/tela.png' } } })]),
        valid: false,
    },
    {
        name: 'asset sem path',
        document: compositionWith([scene({ type: 'video', content: { asset: withoutFields(safeAsset, ['path']) } })]),
        valid: false,
    },
    {
        name: 'asset com campo desconhecido',
        document: compositionWith([scene({ type: 'video', content: { asset: { ...safeAsset, hash: 'abc' } } })]),
        valid: false,
    },
]

/** Regressoes da superficie que nao e de cena: garantem que a correcao nao as alterou. */
const contractCases: readonly ContractCase[] = [
    {
        name: 'composicao com as quatro cenas validas',
        document: compositionWith([
            scene({ id: 'opening', type: 'text', content: { text: 'Abertura.' } }),
            scene({ id: 'tela', type: 'image', content: { asset: safeAsset, alt: 'Agenda.' } }),
            scene({ id: 'demo', type: 'video', content: { asset: safeAsset } }),
            scene({ id: 'chamada', type: 'cta', content: { text: 'Conheca.', href: 'https://example.com.br' } }),
        ]),
        valid: true,
    },
    {
        name: 'metadata tecnica com status approved',
        document: compositionWith([scene()], {
            metadata: { status: 'approved', description: 'Fixture.', tags: ['pilot'] },
        }),
        valid: true,
    },
    { name: 'schemaVersion diferente de 1', document: compositionWith([scene()], { schemaVersion: 2 }), valid: false },
    { name: 'campo desconhecido no topo', document: { ...compositionWith([scene()]), renderPlan: {} }, valid: false },
    {
        name: 'fps fora da faixa 1-120',
        document: compositionWith([scene()], { format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 0 } }),
        valid: false,
    },
    {
        name: 'renderer com options (nao suportado na v1)',
        document: compositionWith([scene()], { renderer: { adapter: 'undecided', options: { preset: 'x' } } }),
        valid: false,
    },
    {
        name: 'metadata com campo desconhecido',
        document: compositionWith([scene()], { metadata: { status: 'draft', owner: 'marketing' } }),
        valid: false,
    },
    {
        name: 'metadata com status desconhecido',
        document: compositionWith([scene()], { metadata: { status: 'publicado' } }),
        valid: false,
    },
    {
        name: 'metadata com mais de oito tags',
        document: compositionWith([scene()], { metadata: { tags: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'] } }),
        valid: false,
    },
]

function readExample(directory: string, file: string): Record<string, unknown> {
    return JSON.parse(readFileSync(path.join(directory, file), 'utf8')) as Record<string, unknown>
}

test('os dois exemplos oficiais de composicao passam no schema draft-07', () => {
    for (const name of ['marca-salao-pilot.composition.json', 'fixture-project-pilot.composition.json']) {
        const result = compositionSchemaCheck(readExample(compositionsDir, name))
        assert.equal(result.valid, true, `${name} rejeitado pelo schema: ${result.detail}`)
    }
})

test('os dois exemplos oficiais de projeto passam no schema draft-07', () => {
    for (const name of ['marca-salao.project.json', 'fixture-project.project.json']) {
        const result = projectSchemaCheck(readExample(projectsDir, name))
        assert.equal(result.valid, true, `${name} rejeitado pelo schema: ${result.detail}`)
    }
})

for (const caseItem of [...sceneCases, ...contractCases]) {
    test(`schema e core concordam: ${caseItem.name}`, () => {
        const schemaResult = compositionSchemaCheck(caseItem.document)
        assert.equal(
            schemaResult.valid,
            caseItem.valid,
            `schema esperava "${caseItem.valid ? 'valido' : 'invalido'}": ${schemaResult.detail}`,
        )

        const report = validateComposition(caseItem.document, baseProject)
        assert.equal(
            report.valid,
            caseItem.valid,
            `TypeScript esperava "${caseItem.valid ? 'valido' : 'invalido'}": ${JSON.stringify(report.errors)}`,
        )
    })
}

test('os exemplos oficiais passam no schema e no core com o mesmo projeto', () => {
    const pairs: ReadonlyArray<{ composition: string; project: string }> = [
        { composition: 'marca-salao-pilot.composition.json', project: 'marca-salao.project.json' },
        { composition: 'fixture-project-pilot.composition.json', project: 'fixture-project.project.json' },
    ]

    for (const pair of pairs) {
        const composition = readExample(compositionsDir, pair.composition)
        const project = readExample(projectsDir, pair.project)
        assert.equal(
            compositionSchemaCheck(composition).valid,
            true,
            `${pair.composition} rejeitado pelo schema: ${compositionSchemaCheck(composition).detail}`,
        )
        assert.equal(
            validateComposition(composition, project).valid,
            true,
            `${pair.composition} rejeitado pelo core`,
        )
    }
})
