/**
 * Paridade estrutural do VisualStyle v1:
 * O espelho draft-07 executado via Ajv e o validador puro em TypeScript
 * avaliam os mesmos documentos estruturais e seus vereditos coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateVisualStyle } from '../../src/validate-visual-style.js'
import { moduleRoot } from '../contract-harness.js'

const schemaPath = path.join(moduleRoot, 'schemas', 'visual-style.schema.json')
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

test('paridade estrutural: estilos visuais validos sao aceitos pelo schema e pelo validador', () => {
    const validCases = [
        {
            schemaVersion: 1,
            id: 'marca-salao-primary',
            title: {
                textColor: '#FFFFFF',
                outlineColor: '#000000',
                fontSize: 42,
                marginTop: 160,
                marginHorizontal: 60,
            },
        },
        {
            schemaVersion: 1,
            id: 'multitrack-hub-accent',
            title: {
                textColor: '#FFD700',
                outlineColor: '#1A1A1A',
                fontSize: 48,
                marginTop: 180,
                marginHorizontal: 80,
            },
        },
        {
            schemaVersion: 1,
            id: 'minimal-edge-values',
            title: {
                textColor: '#000000',
                outlineColor: '#FFFFFF',
                fontSize: 16,
                marginTop: 0,
                marginHorizontal: 0,
            },
        },
        {
            schemaVersion: 1,
            id: 'maximal-edge-values',
            title: {
                textColor: '#AABBCC',
                outlineColor: '#112233',
                fontSize: 160,
                marginTop: 600,
                marginHorizontal: 400,
            },
        },
    ]

    for (const validStyle of validCases) {
        const schemaResult = checkSchema(validStyle)
        assert.ok(schemaResult.valid, `Schema rejeitou estilo valido: ${schemaResult.detail}`)

        const validatorResult = validateVisualStyle(validStyle)
        assert.ok(validatorResult.ok, `Validador puro rejeitou estilo valido: ${validatorResult.ok ? '' : validatorResult.failureCode}`)
    }
})

test('paridade estrutural: defeitos de formato sao rejeitados pelo schema e pelo validador', () => {
    const invalidCases: Array<{ name: string; document: unknown }> = [
        {
            name: 'nao e objeto',
            document: 'estilo-string',
        },
        {
            name: 'objeto nulo',
            document: null,
        },
        {
            name: 'schemaVersion ausente',
            document: {
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'schemaVersion invalida (2)',
            document: {
                schemaVersion: 2,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'id ausente',
            document: {
                schemaVersion: 1,
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'id invalido (CamelCase)',
            document: {
                schemaVersion: 1,
                id: 'MarcaSalaoPrimary',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'campo desconhecido no topo',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                autor: 'designer',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'secao title ausente',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
            },
        },
        {
            name: 'secao title nao e objeto',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: 'invalido',
            },
        },
        {
            name: 'campo desconhecido dentro de title',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                    shadowColor: '#000000',
                },
            },
        },
        {
            name: 'textColor invalido (nome de cor)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: 'white',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'textColor invalido (3 digitos hex)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'outlineColor invalido (sem hashtag)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'fontSize menor que o limite (10)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 10,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'fontSize maior que o limite (200)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 200,
                    marginTop: 160,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'marginTop negativo (-10)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: -10,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'marginTop acima do limite (700)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 700,
                    marginHorizontal: 60,
                },
            },
        },
        {
            name: 'marginHorizontal acima do limite (500)',
            document: {
                schemaVersion: 1,
                id: 'estilo-padrao',
                title: {
                    textColor: '#FFFFFF',
                    outlineColor: '#000000',
                    fontSize: 42,
                    marginTop: 160,
                    marginHorizontal: 500,
                },
            },
        },
    ]

    for (const testCase of invalidCases) {
        const schemaResult = checkSchema(testCase.document)
        assert.strictEqual(
            schemaResult.valid,
            false,
            `Schema deveria rejeitar caso '${testCase.name}', mas aceitou.`,
        )

        const validatorResult = validateVisualStyle(testCase.document)
        assert.strictEqual(
            validatorResult.ok,
            false,
            `Validador puro deveria rejeitar caso '${testCase.name}', mas aceitou.`,
        )
    }
})
