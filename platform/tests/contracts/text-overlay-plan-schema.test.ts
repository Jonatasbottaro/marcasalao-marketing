/**
 * Paridade estrutural do TextOverlayPlan v1:
 * O espelho draft-07 executado via Ajv e o validador puro em TypeScript
 * avaliam os mesmos documentos estruturais e seus vereditos coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { createCreativeExecutionPackageFromCase } from '../../src/creative-execution-packages.js'
import { validateTextOverlayPlan } from '../../src/validate-text-overlay-plan.js'
import { moduleRoot } from '../contract-harness.js'

const schemaPath = path.join(moduleRoot, 'schemas', 'text-overlay-plan.schema.json')
const schemaText = readFileSync(schemaPath, 'utf8')
const schema = JSON.parse(schemaText) as AnySchemaObject

const ajv = new AjvModule.default({ allErrors: true, strict: false })

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map(
        (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
    )
    return { valid, detail: failures.join(' | ') }
}

const examplesRoot = path.join(moduleRoot, 'examples')
const marcaManifest = path.join(examplesRoot, 'pipelines', 'marca-salao-pipeline-pilot.pipeline.json')
const creation = createCreativeExecutionPackageFromCase(marcaManifest, examplesRoot)
if (creation.status !== 'generated' || creation.package === null) {
    throw new Error(`Falha ao preparar pacote para teste de schema: ${creation.summary}`)
}
const validPackage = creation.package
const validCaseId = creation.caseId as string

test('paridade estrutural: casos validos sao aceitos pelo schema e pelo validador', () => {
    const validCases = [
        {
            schemaVersion: 1,
            caseId: validCaseId,
            overlays: [
                {
                    beatId: 'demonstration-body',
                    text: 'Agendamento online facil e rapido',
                },
            ],
        },
        {
            schemaVersion: 1,
            caseId: validCaseId,
            overlays: [],
        },
        {
            schemaVersion: 1,
            caseId: validCaseId,
            overlays: [
                {
                    beatId: 'opening-hook',
                    text: 'Atencao para esta novidade!',
                },
                {
                    beatId: 'demonstration-body',
                    text: 'Demonstracao pratica em tempo real',
                },
            ],
        },
    ]

    for (const doc of validCases) {
        const schemaRes = checkSchema(doc)
        assert.equal(schemaRes.valid, true, `Schema rejeitou caso valido: ${schemaRes.detail}`)

        const validatorRes = validateTextOverlayPlan(validPackage, doc.caseId, doc)
        assert.equal(validatorRes.ok, true, `Validador rejeitou caso valido: ${!validatorRes.ok ? validatorRes.failureCode : ''}`)
    }
})

test('paridade estrutural: defeitos de formato sao rejeitados pelo schema e pelo validador', () => {
    const invalidStructuralCases = [
        {
            name: 'schemaVersion ausente',
            doc: {
                caseId: 'test-case',
                overlays: [],
            },
        },
        {
            name: 'schemaVersion diferente de 1',
            doc: {
                schemaVersion: 2,
                caseId: 'test-case',
                overlays: [],
            },
        },
        {
            name: 'caseId ausente',
            doc: {
                schemaVersion: 1,
                overlays: [],
            },
        },
        {
            name: 'caseId com maiusculas (invalido para kebab-case)',
            doc: {
                schemaVersion: 1,
                caseId: 'Invalid_Case',
                overlays: [],
            },
        },
        {
            name: 'caseId com espacos',
            doc: {
                schemaVersion: 1,
                caseId: 'invalid case',
                overlays: [],
            },
        },
        {
            name: 'overlays ausente',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
            },
        },
        {
            name: 'overlays nao e array',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: 'nao-array',
            },
        },
        {
            name: 'propriedade extra de topo',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: [],
                extraField: 'proibido',
            },
        },
        {
            name: 'overlay sem beatId',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: [{ text: 'Titulo sem beat' }],
            },
        },
        {
            name: 'overlay com beatId fora do padrao kebab-case',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: [{ beatId: 'Beat_Invalido', text: 'Titulo' }],
            },
        },
        {
            name: 'overlay sem text',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: [{ beatId: 'demonstration-body' }],
            },
        },
        {
            name: 'overlay com text vazio',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: [{ beatId: 'demonstration-body', text: '' }],
            },
        },
        {
            name: 'overlay com propriedade extra',
            doc: {
                schemaVersion: 1,
                caseId: 'test-case',
                overlays: [
                    {
                        beatId: 'demonstration-body',
                        text: 'Titulo valido',
                        extraField: 'proibido',
                    },
                ],
            },
        },
    ]

    for (const { name, doc } of invalidStructuralCases) {
        const schemaRes = checkSchema(doc)
        assert.equal(schemaRes.valid, false, `Schema deveria rejeitar: ${name}`)

        const validatorRes = validateTextOverlayPlan(validPackage, 'test-case', doc)
        assert.equal(validatorRes.ok, false, `Validador deveria rejeitar: ${name}`)
    }
})
