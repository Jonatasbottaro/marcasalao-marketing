/**
 * O espelho normativo em JSON Schema: os dois arquivos sao documentos draft-07
 * reais, compilados por um motor ajv — nao por um simulacro em teste.
 *
 * A regressao da etapa 1 (a cena era discriminada pelas formas de content, o que
 * aceitava text+asset) e verificada aqui na estrutura do schema: `scenes.items`
 * discrimina por `type` e cada definicao fecha propriedades. A paridade caso a
 * caso entre schema e validador TypeScript esta em
 * tests/contracts/structural-parity.test.ts, dirigida pelo corpus compartilhado.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    compositionSchemaCheck,
    moduleRoot,
    officialPairs,
    projectSchemaCheck,
    readCompositionExample,
    readProjectExample,
} from './contract-harness.js'
import { sceneShapeCases, surfaceCases } from './contract-corpus.js'

interface SchemaFile {
    $schema?: string
    type?: string
    required?: string[]
    additionalProperties?: unknown
    properties?: Record<string, { items?: { oneOf?: { $ref?: string }[] } }>
    definitions?: Record<string, {
        properties?: Record<string, { const?: unknown; $ref?: string }>
        required?: string[]
        additionalProperties?: unknown
    }>
}

function readSchema(file: string): SchemaFile {
    return JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', file), 'utf8')) as SchemaFile
}

const compositionSchema = readSchema('composition.schema.json')
const projectSchema = readSchema('project.schema.json')

test('os dois schemas sao documentos draft-07 compilaveis pelo motor', () => {
    for (const schema of [compositionSchema, projectSchema]) {
        assert.equal(schema.$schema, 'http://json-schema.org/draft-07/schema#')
        assert.equal(schema.type, 'object')
        assert.equal(schema.additionalProperties, false)
    }
    assert.ok(Array.isArray(projectSchema.required) && projectSchema.required.length > 0)
    assert.deepEqual(compositionSchema.required, [
        'schemaVersion',
        'projectId',
        'id',
        'title',
        'locale',
        'format',
        'scenes',
        'renderer',
    ])
})

test('a cena e discriminada por type, nao pela forma de content (regressao da etapa 1)', () => {
    const refs = compositionSchema.properties?.scenes?.items?.oneOf?.map((entry) => entry.$ref ?? '') ?? []
    assert.deepEqual(refs, ['#/definitions/textScene', '#/definitions/imageScene', '#/definitions/videoScene', '#/definitions/ctaScene'])

    const contentRefByScene: Record<string, string> = {
        textScene: '#/definitions/textContent',
        imageScene: '#/definitions/mediaContent',
        videoScene: '#/definitions/mediaContent',
        ctaScene: '#/definitions/ctaContent',
    }
    for (const [definitionName, contentRef] of Object.entries(contentRefByScene)) {
        const definition = compositionSchema.definitions?.[definitionName]
        assert.ok(definition, `definicao "${definitionName}" ausente`)
        assert.equal(definition.properties?.type?.const, definitionName.replace(/Scene$/, ''))
        assert.equal(definition.properties?.content?.$ref, contentRef)
        assert.deepEqual(definition.required, ['id', 'type', 'durationMs', 'content'])
        assert.equal(definition.additionalProperties, false)
    }

    // Uma cena text com asset satisfaz a definicao de content isolada; apenas a
    // discriminacao por type fecha essa porta.
    const textWithAsset = sceneShapeCases.find((caseItem) => caseItem.name === 'text com asset')
    assert.ok(textWithAsset, 'o corpus perdeu o caso text+asset')
    assert.equal(compositionSchemaCheck(textWithAsset.document).valid, false)
})

test('todo par type x forma invalido do corpus segue rejeitado pelo schema', () => {
    const rejected = sceneShapeCases.filter((caseItem) => !caseItem.valid)
    assert.ok(rejected.length >= 18, `esperados ao menos 18 casos de cena invalidos, obtidos ${rejected.length}`)
    for (const caseItem of rejected) {
        assert.equal(
            compositionSchemaCheck(caseItem.document).valid,
            false,
            `schema aceitou "${caseItem.name}": ${compositionSchemaCheck(caseItem.document).detail}`,
        )
    }
})

test('superficie fora de cena continua fechada no schema', () => {
    for (const label of ['campo desconhecido no topo', 'renderer.options nao suportado na v1', 'metadata com campo desconhecido']) {
        const caseItem = surfaceCases.find((item) => item.name === label)
        assert.ok(caseItem, `o corpus perdeu o caso "${label}"`)
        assert.equal(compositionSchemaCheck(caseItem.document).valid, false, `schema aceitou "${label}"`)
    }

    for (const definitionName of ['textContent', 'ctaContent', 'mediaContent', 'assetReference']) {
        assert.equal(
            compositionSchema.definitions?.[definitionName]?.additionalProperties,
            false,
            `${definitionName} nao fecha propriedades`,
        )
    }
})

test('os exemplos oficiais passam no schema draft-07 nos dois contratos', () => {
    for (const pair of officialPairs) {
        const compositionCheck = compositionSchemaCheck(readCompositionExample(pair.composition))
        assert.equal(compositionCheck.valid, true, `${pair.composition} rejeitado: ${compositionCheck.detail}`)

        const projectCheck = projectSchemaCheck(readProjectExample(pair.project))
        assert.equal(projectCheck.valid, true, `${pair.project} rejeitado: ${projectCheck.detail}`)
    }
})
