/**
 * Schema do BeatPlan: o espelho draft-07 executado em ajv, sobre os mesmos
 * objetos que o contrato TypeScript descreve.
 *
 * O corpus vive neste arquivo (como no espelho do OutputPlan): `contract-harness.ts`
 * compila apenas os schemas dos contratos que ja existiam e nao exporta o motor,
 * entao o BeatPlan traz o proprio compile para nao editar o compartilhado.
 *
 * Duas fronteiras registradas aqui, separadas de proposito:
 * - **estrutural**: a regra mora na forma do documento e o motor a executa;
 * - **entre documentos e da timeline**: igualdade de ids, existencia de cena,
 *   continuidade e duracao total nao sao expressaveis no espelho e pertencem ao
 *   core (`validate-beat-plan.ts`). Os casos da segunda lista afirmam apenas o
 *   que o **motor** aceita, para que a ausencia de regra fique registrada.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import {
    BEAT_FIELDS,
    BEAT_MOTION_INTENTS,
    BEAT_NARRATIVE_FUNCTIONS,
    BEAT_PLAN_MAX_TAGS,
    BEAT_PLAN_METADATA_STATUSES,
    BEAT_PLAN_SCHEMA_VERSION,
    BEAT_PLAN_TOP_LEVEL_FIELDS,
    BEAT_TRANSITIONS,
    BEAT_VALIDATION_STATUSES,
    KEBAB_CASE_PATTERN,
} from '../../src/beat-plan-contract.js'
import { moduleRoot, withoutFields } from '../contract-harness.js'

const schemaPath = path.join(moduleRoot, 'schemas', 'beat-plan.schema.json')
const schemaText = readFileSync(schemaPath, 'utf8')
const schema = JSON.parse(schemaText) as AnySchemaObject

// Mesmas opcoes do harness dos contratos antigos: allErrors para registrar todas
// as violacoes de um documento e strict desligado porque o espelho usa somente o
// vocabulario draft-07 (avisos de strict mode dependeriam da versao do motor).
const ajv = new AjvModule.default({ allErrors: true, strict: false })
const validate = ajv.compile(schema)

/** Veredito do motor sobre um documento, recriando o compilador a cada chamada. */
function check(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map(
        (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
    )
    return { valid, detail: failures.join(' | ') }
}

function accepted(document: unknown, why: string): void {
    const result = check(document)
    assert.equal(result.valid, true, `${why} — motor rejeitou: ${result.detail}`)
}

function rejected(document: unknown, why: string): void {
    const result = check(document)
    assert.equal(result.valid, false, `${why} — motor aceitou um documento que deveria recusar`)
}

function beatWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        id: 'beat-abertura',
        order: 1,
        sceneIds: ['cena-abertura'],
        narrativeFunction: 'hook',
        startMs: 0,
        durationMs: 3000,
        visualIntent: 'abertura com o painel do sistema em tela cheia',
        motionIntent: 'slow-zoom',
        transitionIn: 'none',
        transitionOut: 'cut',
        editorialEvidence: ['briefing-2026-10'],
        validationStatus: 'draft',
        ...overrides,
    }
}

function planWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: BEAT_PLAN_SCHEMA_VERSION,
        projectId: 'projeto-fixture',
        compositionId: 'composicao-piloto',
        id: 'beat-plan-piloto',
        locale: 'pt-BR',
        beats: [beatWith()],
        ...overrides,
    }
}

function planWithTwoBeats(): Record<string, unknown> {
    return planWith({
        beats: [
            beatWith(),
            beatWith({
                id: 'beat-demonstracao',
                order: 2,
                sceneIds: ['cena-demonstracao', 'cena-detalhe'],
                narrativeFunction: 'demonstration',
                startMs: 3000,
                durationMs: 6000,
                motionIntent: 'pan',
                transitionIn: 'cut',
                transitionOut: 'fade',
            }),
        ],
    })
}

/** Coleta toda string `$ref` do documento, em ordem de aparecimento. */
function collectRefs(value: unknown, found: string[] = []): string[] {
    if (Array.isArray(value)) {
        for (const item of value) collectRefs(item, found)
        return found
    }
    if (value !== null && typeof value === 'object') {
        for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
            if (key === '$ref' && typeof item === 'string') found.push(item)
            else collectRefs(item, found)
        }
    }
    return found
}

const beatDefinition = requireObject((schema.definitions as AnySchemaObject).beat, 'definitions.beat')

function beatProperties(): Record<string, AnySchemaObject> {
    return requireObject(beatDefinition.properties, 'definitions.beat.properties') as Record<string, AnySchemaObject>
}

function topProperties(): Record<string, AnySchemaObject> {
    return requireObject(schema.properties, 'properties') as Record<string, AnySchemaObject>
}

function metadataProperties(): Record<string, AnySchemaObject> {
    return requireObject(topProperties().metadata?.properties, 'properties.metadata.properties') as Record<string, AnySchemaObject>
}

function beatRequired(): string[] {
    return requireArray(beatDefinition.required, 'definitions.beat.required') as string[]
}

/** Le uma propriedade declarada do espelho; ausente e falha, nao `undefined` silencioso. */
function property(table: Record<string, AnySchemaObject | undefined>, name: string): AnySchemaObject {
    return requireObject(table[name], `propriedade "${name}"`)
}

function enumOf(table: Record<string, AnySchemaObject | undefined>, name: string): readonly unknown[] {
    return requireArray(property(table, name).enum, `enum de "${name}"`)
}

function patternOf(table: Record<string, AnySchemaObject | undefined>, name: string): string {
    return String(property(table, name).pattern)
}

function requireObject(value: unknown, label: string): AnySchemaObject {
    assert.ok(value !== null && typeof value === 'object' && !Array.isArray(value), `espelho sem ${label}`)
    return value as AnySchemaObject
}

function requireArray(value: unknown, label: string): readonly unknown[] {
    assert.ok(Array.isArray(value), `espelho sem o array ${label}`)
    return value as readonly unknown[]
}

test('o espelho e draft-07 autoportante: nenhum $ref sai do proprio documento', () => {
    assert.equal(schema.$schema, 'http://json-schema.org/draft-07/schema#')
    assert.equal(schema.type, 'object')

    const refs = collectRefs(schema)
    assert.ok(refs.length > 0, 'o espelho deve exercitar $ref interno entre beat e definitions')
    for (const reference of refs) {
        assert.ok(
            reference.startsWith('#/'),
            `$ref externo exigiria resolucao de rede ou de arquivo: ${reference}`,
        )
    }
    assert.deepEqual([...new Set(refs)], ['#/definitions/beat'])
})

test('o motor compila o espelho sem advertencias e a fixture valida passa de forma deterministica', () => {
    const primeira = check(planWith())
    const segunda = check(planWith())
    assert.deepEqual(primeira, segunda, 'dois passes do mesmo documento precisam dar o mesmo veredito')
    assert.equal(primeira.valid, true, `fixture valida recusada: ${primeira.detail}`)
    assert.equal(primeira.detail, '')
    accepted(planWithTwoBeats(), 'um plano de dois beats com cena multipla')
})

test('paridade de estrutura: campos obrigatorios e conhecidos do topo batem com o contrato', () => {
    assert.deepEqual(Object.keys(topProperties()), [...BEAT_PLAN_TOP_LEVEL_FIELDS])
    assert.deepEqual(schema.required, [
        'schemaVersion',
        'projectId',
        'compositionId',
        'id',
        'locale',
        'beats',
    ])
    assert.equal((schema.required as string[]).includes('metadata'), false)
    assert.equal(schema.additionalProperties, false, 'topo precisa proibir campo desconhecido')
})

test('paridade de estrutura: campos do beat batem com a ordem fixa do contrato', () => {
    assert.deepEqual(Object.keys(beatProperties()), [...BEAT_FIELDS])
    assert.deepEqual(beatRequired(), [
        'id',
        'order',
        'sceneIds',
        'narrativeFunction',
        'startMs',
        'durationMs',
        'visualIntent',
        'motionIntent',
        'transitionIn',
        'transitionOut',
        'editorialEvidence',
        'validationStatus',
    ])
    const beat = beatDefinition
    assert.equal(beat.additionalProperties, false, 'beat precisa proibir campo desconhecido')
})

test('paridade de vocabulario: enums e constantes do espelho sao os arrays do contrato', () => {
    const properties = beatProperties()
    assert.deepEqual(enumOf(properties, 'narrativeFunction'), [...BEAT_NARRATIVE_FUNCTIONS])
    assert.deepEqual(enumOf(properties, 'motionIntent'), [...BEAT_MOTION_INTENTS])
    assert.deepEqual(enumOf(properties, 'transitionIn'), [...BEAT_TRANSITIONS])
    assert.deepEqual(enumOf(properties, 'transitionOut'), [...BEAT_TRANSITIONS])
    assert.deepEqual(enumOf(properties, 'validationStatus'), [...BEAT_VALIDATION_STATUSES])
    assert.deepEqual(enumOf(metadataProperties(), 'status'), [...BEAT_PLAN_METADATA_STATUSES])

    assert.equal(property(topProperties(), 'schemaVersion').const, BEAT_PLAN_SCHEMA_VERSION)
    assert.equal(property(topProperties(), 'schemaVersion').type, 'integer')

    // O teto de tags heuristico do core e o maxItems do espelho: um numero so.
    assert.equal(property(metadataProperties(), 'tags').maxItems, BEAT_PLAN_MAX_TAGS)

    // O padrao de id e o mesmo regex do contrato, escrito como pattern draft-07.
    for (const key of ['projectId', 'compositionId', 'id'] as const) {
        assert.equal(patternOf(topProperties(), key), KEBAB_CASE_PATTERN.source, `pattern de ${key}`)
    }
    assert.equal(patternOf(beatProperties(), 'id'), KEBAB_CASE_PATTERN.source)
    assert.equal(
        patternOf({ sceneIds: requireObject(property(beatProperties(), 'sceneIds').items, 'items de sceneIds') }, 'sceneIds'),
        KEBAB_CASE_PATTERN.source,
    )
})

test('campos obrigatorios do topo: cada ausencia individual e recusada pelo motor', () => {
    for (const field of schema.required as string[]) {
        rejected(withoutFields(planWith(), [field]), `plano sem o obrigatorio "${field}"`)
    }
    accepted(withoutFields(planWith(), ['metadata']), 'plano sem metadata (opcional)')
})

test('schemaVersion: apenas o inteiro 1 existe no espelho', () => {
    for (const value of [0, 2, 1.5, '1', true, null, {}, []]) {
        rejected(planWith({ schemaVersion: value }), `schemaVersion ${JSON.stringify(value)}`)
    }
    accepted(planWith({ schemaVersion: 1 }), 'schemaVersion 1')
})

test('additionalProperties false vale nos quatro niveis do espelho', () => {
    rejected(planWith({ exportReady: true }), 'campo desconhecido no topo do plano')
    rejected(planWith({ beats: [beatWith({ renderCommand: 'ffmpeg' })] }), 'campo desconhecido no beat')
    rejected(
        planWith({ beats: [beatWith({ narration: { text: 'ok', voice: 'pt-BR' } })] }),
        'campo de TTS dentro de narration',
    )
    rejected(planWith({ metadata: { status: 'draft', owner: 'time' } }), 'campo desconhecido em metadata')
    rejected(
        planWith({ beats: [beatWith({ narration: { text: 'ok', file: 'narracao.mp3' } })] }),
        'referencia a arquivo de audio dentro de narration',
    )
})

test('tipos primitivos: cada campo com tipo trocado e recusado', () => {
    const cases: Array<[string, unknown]> = [
        ['projectId', 42],
        ['projectId', null],
        ['compositionId', ['composicao']],
        ['id', { value: 'beat-plan' }],
        ['locale', 7],
        ['locale', null],
        ['beats', 'beat-abertura'],
        ['beats', { 0: beatWith() }],
        ['beats', null],
        ['metadata', []],
        ['metadata', 'rascunho'],
    ]
    for (const [field, value] of cases) {
        rejected(planWith({ [field]: value }), `"${field}" com tipo ${JSON.stringify(value)}`)
    }

    const beatFieldCases: Array<[string, unknown]> = [
        ['id', 1],
        ['order', '1'],
        ['order', 1.5],
        ['order', null],
        ['sceneIds', 'cena-abertura'],
        ['sceneIds', [1]],
        ['sceneIds', [null]],
        ['narrativeFunction', 'gancho'],
        ['visualIntent', 120],
        ['visualIntent', null],
        ['motionIntent', 'zoom'],
        ['transitionIn', 'Fade'],
        ['transitionOut', 0],
        ['validationStatus', 'aprovado'],
    ]
    for (const [field, value] of beatFieldCases) {
        rejected(planWith({ beats: [beatWith({ [field]: value })] }), `beat.${field} com tipo ${JSON.stringify(value)}`)
    }
})

test('arrays: item minimo, unicidade e teto de tags', () => {
    rejected(planWith({ beats: [] }), 'plano sem nenhum beat')
    accepted(
        planWith({ beats: [beatWith(), beatWith({ id: 'beat-2', order: 2 })] }),
        'dois beats na mesma cena (cena e beat nao sao um para um)',
    )
    rejected(
        planWith({ beats: [beatWith({ sceneIds: [] })] }),
        'beat sem nenhuma cena referenciada',
    )
    rejected(
        planWith({ beats: [beatWith({ sceneIds: ['cena-1', 'cena-1'] })] }),
        'sceneIds duplicado no mesmo beat',
    )
    rejected(
        planWith({ beats: [beatWith({ editorialEvidence: [] })] }),
        'editorialEvidence vazio',
    )
    rejected(
        planWith({ beats: [beatWith({ editorialEvidence: ['e-1', 'e-1'] })] }),
        'editorialEvidence duplicado',
    )
    rejected(
        planWith({ beats: [beatWith({ editorialEvidence: [''] })] }),
        'evidencia editorial em string vazia',
    )
    rejected(
        planWith({ metadata: { tags: Array.from({ length: BEAT_PLAN_MAX_TAGS + 1 }, (_, i) => `tag-${i}`) } }),
        `metadata.tags acima do teto de ${BEAT_PLAN_MAX_TAGS}`,
    )
    rejected(planWith({ metadata: { tags: ['mesma', 'mesma'] } }), 'metadata.tags duplicado')
    rejected(planWith({ metadata: { tags: ['ok', ''] } }), 'metadata.tags com string vazia')
    rejected(planWith({ metadata: { description: '' } }), 'metadata.description vazia')
    accepted(
        planWith({ metadata: { tags: ['piloto', 'demonstracao'] } }),
        `metadata.tags com ate ${BEAT_PLAN_MAX_TAGS} itens unicos`,
    )
})

test('identificadores: somente kebab-case e aceito nos quatro ids', () => {
    const invalidIds = ['Projeto_Teste', 'com pos', 'com-pos-', '-com-pos', 'com--pos', 'COM-POS', '', 'com.pos', 'com/pos']
    for (const value of invalidIds) {
        rejected(planWith({ projectId: value }), `projectId ${JSON.stringify(value)}`)
        rejected(planWith({ compositionId: value }), `compositionId ${JSON.stringify(value)}`)
        rejected(planWith({ id: value }), `id do plano ${JSON.stringify(value)}`)
        rejected(planWith({ beats: [beatWith({ id: value })] }), `id do beat ${JSON.stringify(value)}`)
        rejected(planWith({ beats: [beatWith({ sceneIds: [value] })] }), `sceneIds ${JSON.stringify(value)}`)
    }
    for (const value of ['a', 'a1', 'ab-cd-ef', '1-2-3']) {
        accepted(planWith({ id: value }), `id kebab-case ${value}`)
    }
    // locale nao e id: aceita qualquer string nao vazia, inclusive com espaco.
    accepted(planWith({ locale: 'pt BR' }), 'locale nao vazio fora de kebab-case')
    rejected(planWith({ locale: '' }), 'locale vazio')
})

test('duracoes: startMs inteiro maior ou igual a zero e durationMs inteiro positivo', () => {
    for (const value of [-1, -3000, 0.5, -0.5]) {
        rejected(planWith({ beats: [beatWith({ startMs: value })] }), `startMs ${value}`)
    }
    for (const value of [0, -1, 1.5, 2.0001]) {
        rejected(planWith({ beats: [beatWith({ durationMs: value })] }), `durationMs ${value}`)
    }
    for (const value of [null, '3000', true, {}]) {
        rejected(planWith({ beats: [beatWith({ startMs: value })] }), `startMs ${JSON.stringify(value)}`)
        rejected(planWith({ beats: [beatWith({ durationMs: value })] }), `durationMs ${JSON.stringify(value)}`)
    }
    accepted(planWith({ beats: [beatWith({ startMs: 0, durationMs: 1 })] }), 'beat minimo de 1 ms')
    accepted(planWith({ beats: [beatWith({ startMs: 2, durationMs: 2 })] }), 'duracoes inteiras pequenas')
})

test('campos opcionais do beat: narration e onScreenText seguem o espelho quando presentes', () => {
    accepted(planWith({ beats: [beatWith({ narration: { text: 'Voce abre o painel e ve o agendamento' } })] }), 'narration com texto')
    accepted(planWith({ beats: [beatWith({ onScreenText: 'Agenda cheia, vista clara' })] }), 'onScreenText')
    accepted(
        planWith({ beats: [beatWith({ narration: { text: 'ok' }, onScreenText: 'ok' })] }),
        'beat com os dois campos opcionais',
    )
    rejected(planWith({ beats: [beatWith({ narration: {} })] }), 'narration sem text')
    rejected(planWith({ beats: [beatWith({ narration: { text: '' } })] }), 'narration.text vazio')
    rejected(planWith({ beats: [beatWith({ narration: { text: 1 } })] }), 'narration.text nao string')
    rejected(planWith({ beats: [beatWith({ narration: 'texto solto' })] }), 'narration como string')
    rejected(planWith({ beats: [beatWith({ narration: null })] }), 'narration null')
    rejected(planWith({ beats: [beatWith({ onScreenText: '' })] }), 'onScreenText vazio')
    rejected(planWith({ beats: [beatWith({ onScreenText: ['texto'] })] }), 'onScreenText como array')
})

test('definicao compartilhada: a $ref vale em qualquer posicao do array de beats', () => {
    const valido = beatWith()
    const primeiroRuim = planWith({ beats: [beatWith({ durationMs: 0 }), valido] })
    const ultimoRuim = planWith({ beats: [valido, beatWith({ id: 'beat-2', order: 2, durationMs: 0 })] })
    rejected(primeiroRuim, 'beat na posicao 0 com durationMs 0')
    rejected(ultimoRuim, 'beat na ultima posicao com durationMs 0')

    const doisRuins = planWith({
        beats: [
            beatWith({ narrativeFunction: 'gancho' }),
            beatWith({ id: 'beat-2', order: 2, motionIntent: 'zoom' }),
        ],
    })
    const resultado = check(doisRuins)
    assert.equal(resultado.valid, false)
    // allErrors: as duas violacoes aparecem no mesmo passe, com o index path da posicao.
    assert.ok(resultado.detail.includes('/beats/0'), `faltou a posicao 0 em: ${resultado.detail}`)
    assert.ok(resultado.detail.includes('/beats/1'), `faltou a posicao 1 em: ${resultado.detail}`)
})

test('metadata opcional: status e descricao respeitam o espelho quando o objeto existe', () => {
    accepted(planWith({ metadata: {} }), 'metadata objeto vazio')
    accepted(planWith({ metadata: { status: 'draft' } }), 'metadata.status draft')
    for (const status of ['rascunho', 'approved', 'published', '']) {
        rejected(planWith({ metadata: { status } }), `metadata.status ${JSON.stringify(status)}`)
    }
    rejected(planWith({ metadata: { description: 12 } }), 'metadata.description numerica')
    rejected(planWith({ metadata: { tags: 'piloto' } }), 'metadata.tags como string')
})

test('fronteira do espelho: regras entre documentos e da timeline ficam fora do schema', () => {
    // O motor decide apenas a forma. Estes casos violam uma regra do core e, por
    // isso mesmo, o espelho os aceita — a ausencia de regra fica registrada aqui.
    accepted(
        planWith({
            beats: [
                beatWith({ order: 1 }),
                beatWith({ id: 'beat-2', order: 1, sceneIds: ['cena-abertura'] }),
            ],
        }),
        'dois beats com o mesmo order e a mesma cena',
    )
    accepted(
        planWith({
            beats: [beatWith({ order: 2 }), beatWith({ id: 'beat-2', order: 5 })],
        }),
        'ordem com lacuna (2 e 5)',
    )
    accepted(
        planWith({
            beats: [
                beatWith({ startMs: 0, durationMs: 3000 }),
                beatWith({ id: 'beat-2', order: 2, startMs: 1000, durationMs: 3000 }),
            ],
        }),
        'beats sobrepostos na timeline',
    )
    accepted(
        planWith({ projectId: 'outro-projeto', compositionId: 'outra-composicao' }),
        'plano que aponta para projeto e composicao diferentes dos ids do beat',
    )
    const acimaDoInteiroSeguro = 9007199254740992
    assert.ok(acimaDoInteiroSeguro > Number.MAX_SAFE_INTEGER)
    accepted(
        planWith({ beats: [beatWith({ startMs: acimaDoInteiroSeguro, durationMs: acimaDoInteiroSeguro })] }),
        'duracao acima de Number.MAX_SAFE_INTEGER (o core recusa; o espelho nao expressa)',
    )
})

test('o espelho nao contem chave de fornecedor, caminho absoluto nem prompt executavel', () => {
    // Regra de pureza do nucleo: o schema e texto declarativo. Qualquer chave que
    // nomeie fornecedor, arquivo ou comando seria um contrato de execucao.
    const forbiddenKeys = ['provider', 'command', 'cmd', 'script', 'path', 'filePath', 'url', 'href', 'model', 'apiKey']
    const lowerSchema = JSON.stringify(schema).toLowerCase()
    for (const key of forbiddenKeys) {
        const properties = [
            Object.keys(topProperties()),
            Object.keys(beatProperties()),
            Object.keys(requireObject(property(beatProperties(), 'narration').properties, 'narration.properties')),
            Object.keys(metadataProperties()),
        ].flat()
        assert.equal(
            properties.some((property) => property.toLowerCase() === key),
            false,
            `propriedade de execucao ou arquivo nao pertence ao espelho: ${key}`,
        )
    }
    assert.equal(lowerSchema.includes('http://json-schema.org/draft-07/schema#'), true)
    assert.equal(/(s3|ffmpeg|gemini|openai|replicate|\.mp3|\.mp4)/i.test(schemaText), false)
})
