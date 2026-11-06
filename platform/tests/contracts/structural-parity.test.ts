/**
 * Paridade estrutural do corpus: o MESMO documento e avaliado pelo motor JSON Schema
 * draft-07 (ajv) e pelo validador TypeScript, e os dois veredictos precisam coincidir.
 *
 * Este grupo so cobre regras que vivem na forma do proprio documento. O que depende de
 * outro documento, de aritmetica de duracoes, de unicidade de ids ou de comparacao por
 * tokens esta em semantic-rules.test.ts.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
    compositionSchemaCheck,
    officialPairs,
    projectSchemaCheck,
    readCompositionExample,
    readProjectExample,
    validateCompositionDocument,
    validateProjectDocument,
} from '../contract-harness.js'
import { structuralCompositionCases, structuralProjectCases } from '../contract-corpus.js'

test('o corpus estrutural tem casos positivos e negativos nos dois contratos', () => {
    const projectPositives = structuralProjectCases.filter((caseItem) => caseItem.valid).length
    const compositionPositives = structuralCompositionCases.filter((caseItem) => caseItem.valid).length

    assert.ok(projectPositives >= 10, `esperados ao menos 10 casos validos de manifesto, obtidos ${projectPositives}`)
    assert.ok(structuralProjectCases.length - projectPositives >= 20, 'o corpus de manifesto precisa de casos negativos')
    assert.ok(compositionPositives >= 15, `esperados ao menos 15 casos validos de composicao, obtidos ${compositionPositives}`)
    assert.ok(structuralCompositionCases.length - compositionPositives >= 60, 'o corpus de composicao precisa de casos negativos')

    for (const cases of [structuralProjectCases, structuralCompositionCases]) {
        assert.equal(
            new Set(cases.map((caseItem) => caseItem.name)).size,
            cases.length,
            'nomes de caso duplicados dentro do mesmo contrato',
        )
    }
})

for (const caseItem of structuralProjectCases) {
    test(`ProjectManifest estrutural: ${caseItem.name}`, () => {
        const report = validateProjectDocument(caseItem.document)
        assert.equal(
            report.valid,
            caseItem.valid,
            `TypeScript esperava valid=${caseItem.valid}, obtido valid=${report.valid} (${report.errors.map((error) => error.code).join(', ')})`,
        )
        if (!caseItem.valid && caseItem.codes) {
            assert.deepEqual(report.errors.map((error) => error.code), caseItem.codes)
        }

        const schema = projectSchemaCheck(caseItem.document)
        assert.equal(
            schema.valid,
            caseItem.valid,
            `schema esperava valid=${caseItem.valid}, obtido valid=${schema.valid} (${schema.detail})`,
        )
    })
}

for (const caseItem of structuralCompositionCases) {
    test(`Composition estrutural: ${caseItem.name}`, () => {
        const report = validateCompositionDocument(caseItem.document)
        assert.equal(
            report.valid,
            caseItem.valid,
            `TypeScript esperava valid=${caseItem.valid}, obtido valid=${report.valid} (${report.errors.map((error) => error.code).join(', ')})`,
        )
        if (!caseItem.valid && caseItem.codes) {
            assert.deepEqual(report.errors.map((error) => error.code), caseItem.codes)
        }

        const schema = compositionSchemaCheck(caseItem.document)
        assert.equal(
            schema.valid,
            caseItem.valid,
            `schema esperava valid=${caseItem.valid}, obtido valid=${schema.valid} (${schema.detail})`,
        )
    })
}

test('os exemplos oficiais passam nos dois motores, com o projeto correspondente', () => {
    for (const pair of officialPairs) {
        const composition = readCompositionExample(pair.composition)
        const project = readProjectExample(pair.project)

        assert.equal(projectSchemaCheck(project).valid, true, `${pair.project} rejeitado pelo schema de projeto`)
        assert.equal(validateProjectDocument(project).valid, true, `${pair.project} rejeitado pelo TypeScript`)
        assert.equal(compositionSchemaCheck(composition).valid, true, `${pair.composition} rejeitado pelo schema: ${compositionSchemaCheck(composition).detail}`)
        assert.equal(validateCompositionDocument(composition, project).valid, true, `${pair.composition} rejeitado pelo TypeScript`)
    }
})
