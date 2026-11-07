/**
 * Regras semanticas do corpus: aqui o veredicto depende de algo que o vocabulario
 * draft-07 nao expressa — vinculo com o ProjectManifest, unicidade de ids de cena,
 * soma de duracoes, nomes sensiveis comparados por token e sintaxe de URL pelo parser.
 *
 * O que se testou e o codigo emitido pelo validador TypeScript. O veredicto do schema
 * sobre o MESMO documento fica registrado em `schemaAccepts` como diferenca conhecida:
 * nao se exige que o schema resolva vinculo entre documentos.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
    compositionCodes,
    compositionSchemaCheck,
    compositionWith,
    projectSchemaCheck,
    projectWith,
    validateCompositionDocument,
    validateProjectDocument,
} from '../contract-harness.js'
import type { SemanticReason } from '../contract-corpus.js'
import { semanticCases } from '../contract-corpus.js'

interface Outcome {
    readonly valid: boolean
    readonly codes: readonly string[]
    readonly warningCodes: readonly string[]
    readonly totalDurationMs: number | null | undefined
}

function evaluate(contract: 'project' | 'composition', document: Record<string, unknown>, project: Record<string, unknown>): Outcome {
    if (contract === 'project') {
        const report = validateProjectDocument(document)
        return {
            valid: report.valid,
            codes: report.errors.map((error) => error.code),
            warningCodes: report.warnings.map((warning) => warning.code),
            totalDurationMs: undefined,
        }
    }
    const report = validateCompositionDocument(document, project)
    return {
        valid: report.valid,
        codes: compositionCodes(report),
        warningCodes: report.warnings.map((warning) => warning.code),
        totalDurationMs: report.totalDurationMs,
    }
}

const reasonLabels: readonly SemanticReason[] = [
    'vinculo-com-o-projectmanifest',
    'manifesto-invalido',
    'unicidade-de-id-de-cena',
    'soma-de-duracoes',
    'nomes-sensiveis-por-token',
    'sintaxe-de-url-no-parser',
    'heuristica-de-warning',
]

test('o corpus semantico cobre todas as razoes documentadas e os dois contratos', () => {
    const covered = new Set(semanticCases.map((caseItem) => caseItem.reason))
    assert.deepEqual(
        reasonLabels.filter((reason) => !covered.has(reason)),
        [],
        'motivos semanticos sem caso no corpus',
    )
    assert.ok(semanticCases.some((caseItem) => caseItem.contract === 'project'), 'faltam casos semanticos de ProjectManifest')
    assert.ok(semanticCases.some((caseItem) => caseItem.contract === 'composition'), 'faltam casos semanticos de Composition')
})

for (const caseItem of semanticCases) {
    test(`Semantico (${caseItem.contract}): ${caseItem.name}`, () => {
        const before = JSON.stringify({ document: caseItem.document, project: caseItem.project })
        const outcome = evaluate(caseItem.contract, caseItem.document, caseItem.project)

        assert.equal(outcome.valid, caseItem.codes.length === 0, `veredito divergente dos codigos esperados: ${outcome.codes.join(', ')}`)
        assert.deepEqual([...outcome.codes], [...caseItem.codes])
        // Os builders declaram renderer "undecided", que produz um aviso em toda composicao.
        const expectedWarnings = caseItem.warnings ?? (caseItem.contract === 'composition' ? ['COMPOSITION_RENDERER_UNDECIDED'] : [])
        assert.deepEqual([...outcome.warningCodes], [...expectedWarnings])
        if (caseItem.totalDurationMs !== undefined) {
            assert.equal(outcome.totalDurationMs, caseItem.totalDurationMs)
        }

        const schema =
            caseItem.contract === 'project' ? projectSchemaCheck(caseItem.document) : compositionSchemaCheck(caseItem.document)
        assert.equal(
            schema.valid,
            caseItem.schemaAccepts,
            `schema decidiu "${caseItem.reason}" (valid=${schema.valid}): ${schema.detail}`,
        )

        assert.equal(JSON.stringify({ document: caseItem.document, project: caseItem.project }), before, 'o validador mutou a entrada')
    })
}

test('o schema nao decide vinculo: a mesma composicao vale para dois projetos opostos', () => {
    const composition = compositionWith({})
    const ownProject = projectWith({})
    const otherProject = projectWith({ id: 'outro-projeto', locale: 'en-US', outputProfiles: ['quadrado-social'] })

    assert.equal(compositionSchemaCheck(composition).valid, true)
    assert.equal(validateCompositionDocument(composition, ownProject).valid, true)

    const report = validateCompositionDocument(composition, otherProject)
    assert.equal(report.valid, false)
    assert.deepEqual(compositionCodes(report), [
        'COMPOSITION_PROJECT_ID_MISMATCH',
        'COMPOSITION_LOCALE_MISMATCH',
        'COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED',
    ])
    assert.equal(compositionSchemaCheck(composition).valid, true, 'o schema mudou de veredicto ao trocar apenas o projeto')
})

test('um manifesto invalido bloqueia a composicao sem alterar o veredicto do schema', () => {
    const composition = compositionWith({})
    const brokenProject = projectWith({ assetRoot: '/var/assets' })

    assert.equal(projectSchemaCheck(brokenProject).valid, false)
    assert.equal(compositionSchemaCheck(composition).valid, true)

    const report = validateCompositionDocument(composition, brokenProject)
    assert.deepEqual(compositionCodes(report), ['COMPOSITION_MANIFEST_INVALID'])
})

test('os relatorios semanticos sao deterministicos e separam warnings de erros', () => {
    for (const caseItem of semanticCases) {
        const first = evaluate(caseItem.contract, caseItem.document, caseItem.project)
        const second = evaluate(caseItem.contract, caseItem.document, caseItem.project)

        assert.deepEqual(second, first, `relatorio nao deterministico em "${caseItem.name}"`)
        assert.ok(
            first.valid || first.codes.length > 0,
            `relatorio invalido sem nenhum codigo em "${caseItem.name}"`,
        )
        assert.ok(
            first.valid === (first.codes.length === 0),
            `veredito e lista de erros incoerentes em "${caseItem.name}"`,
        )
        for (const code of first.warningCodes) {
            assert.ok(
                code === 'COMPOSITION_SCENE_TEXT_LONG'
                    || code === 'COMPOSITION_SCENE_DURATION_SHORT'
                    || code === 'COMPOSITION_RENDERER_UNDECIDED',
                `codigo inesperado na lista de warnings: ${code}`,
            )
        }
        for (const code of first.codes) {
            assert.ok(
                code.startsWith('PROJECT_') || code.startsWith('COMPOSITION_'),
                `codigo de erro fora do espaco publico documentado: ${code}`,
            )
        }
    }
})
