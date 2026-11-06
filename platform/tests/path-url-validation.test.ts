/**
 * Regressoes da etapa 2 — caminhos, URLs e campos textuais.
 *
 * A classificacao lexica e uma funcao pura compartilhada (`src/relative-path.ts`);
 * os codigos e caminhos de erro permanecem proprios de cada contrato. Este arquivo
 * roda as tabelas do corpus compartilhado (paths, hrefs, textos em branco) contra
 * os dois motores e fixa as tres diferencas registradas de proposito entre o
 * espelho draft-07 e o validador TypeScript. A paridade caso a caso dos demais
 * contratos esta em tests/contracts/.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
    containsControlCharacter,
    inspectRelativePath,
    pathSegments,
} from '../src/relative-path.js'
import {
    B,
    NUL,
    compositionCodes,
    compositionSchemaCheck,
    compositionWith,
    compositionWithAssetPath,
    compositionWithHref,
    compositionWithScenes,
    compositionWithTextField,
    manifestWithAssetRoot,
    officialPairs,
    projectCodes,
    projectSchemaCheck,
    readCompositionExample,
    readProjectExample,
    sceneWith,
    validateCompositionDocument,
    validateProjectDocument,
} from './contract-harness.js'
import {
    acceptedHrefs,
    acceptedPaths,
    blankProjectFields,
    blankStringFields,
    blankValues,
    lexicalPathCases,
    rejectedHrefs,
    tokenSensitivePaths,
    urlParserOnlyHrefs,
} from './contract-corpus.js'

test('a violacao lexica compartilhada produz os codigos proprios de cada contrato', () => {
    for (const caseItem of lexicalPathCases) {
        assert.deepEqual(
            inspectRelativePath(caseItem.value),
            [caseItem.violation],
            `violacao esperada para ${JSON.stringify(caseItem.value)}`,
        )

        const manifest = manifestWithAssetRoot(caseItem.value)
        assert.deepEqual(projectCodes(validateProjectDocument(manifest)), [caseItem.projectCode])
        assert.equal(projectSchemaCheck(manifest).valid, false, `schema aceitou assetRoot ${caseItem.value}`)

        const composition = compositionWithAssetPath(caseItem.value)
        assert.deepEqual(compositionCodes(validateCompositionDocument(composition)), [caseItem.compositionCode])
        assert.equal(compositionSchemaCheck(composition).valid, false, `schema aceitou asset.path ${caseItem.value}`)
    }
})

test('caminhos comuns sao aceitos pelos dois contratos nos dois motores', () => {
    for (const value of acceptedPaths) {
        assert.deepEqual(inspectRelativePath(value), [])

        const manifest = manifestWithAssetRoot(value)
        assert.equal(validateProjectDocument(manifest).valid, true, `core rejeitou assetRoot ${JSON.stringify(value)}`)
        assert.equal(projectSchemaCheck(manifest).valid, true, `schema rejeitou assetRoot ${JSON.stringify(value)}`)

        const composition = compositionWithAssetPath(value)
        assert.equal(validateCompositionDocument(composition).valid, true, `core rejeitou asset.path ${JSON.stringify(value)}`)
        assert.equal(compositionSchemaCheck(composition).valid, true, `schema rejeitou asset.path ${JSON.stringify(value)}`)
    }
})

test('assetRoot com protocolo e rejeitado (regressao: antes passava)', () => {
    const manifest = manifestWithAssetRoot('https://example.com/assets')
    assert.deepEqual(projectCodes(validateProjectDocument(manifest)), ['PROJECT_ASSET_ROOT_URL'])
    assert.equal(projectSchemaCheck(manifest).valid, false)
})

test('asset secretaria e aceito (regressao: o bloqueio por substring rejeitava)', () => {
    for (const value of ['assets/secretaria', 'assets/secretaria.png']) {
        const manifest = manifestWithAssetRoot(`projects/projeto-teste/${value}`)
        assert.equal(validateProjectDocument(manifest).valid, true)
        assert.equal(projectSchemaCheck(manifest).valid, true)

        const composition = compositionWithAssetPath(`projects/projeto-teste/${value}`)
        assert.equal(validateCompositionDocument(composition).valid, true)
        assert.equal(compositionSchemaCheck(composition).valid, true)
    }
})

test('href aceita http(s) absoluto sem credenciais, em qualquer caixa', () => {
    for (const href of acceptedHrefs) {
        const composition = compositionWithHref(href)
        const report = validateCompositionDocument(composition)
        assert.equal(
            report.valid,
            true,
            `core rejeitou href ${JSON.stringify(href)}: ${compositionCodes(report).join(', ')}`,
        )
        assert.equal(compositionSchemaCheck(composition).valid, true, `schema rejeitou href ${JSON.stringify(href)}`)
    }
})

test('href rejeita usuario ou senha e qualquer outra sintaxe', () => {
    for (const caseItem of rejectedHrefs) {
        const composition = compositionWithHref(caseItem.href)
        assert.deepEqual(
            compositionCodes(validateCompositionDocument(composition)),
            [caseItem.code],
            `core produziu outro codigo para href ${JSON.stringify(caseItem.href)}`,
        )
        assert.equal(compositionSchemaCheck(composition).valid, false, `schema aceitou href ${JSON.stringify(caseItem.href)}`)
    }
})

test('href com apenas usuario e credencial (regressao: antes passava)', () => {
    const composition = compositionWithHref('https://usuario@example.com')
    assert.deepEqual(compositionCodes(validateCompositionDocument(composition)), ['COMPOSITION_CTA_HREF_CREDENTIALS'])
    assert.equal(compositionSchemaCheck(composition).valid, false)
})

test('strings obrigatorias compostas apenas por espacos sao rejeitadas nos dois contratos', () => {
    for (const caseItem of blankStringFields) {
        for (const value of blankValues) {
            const composition = compositionWithTextField(caseItem.field, value)
            assert.deepEqual(
                compositionCodes(validateCompositionDocument(composition)),
                [caseItem.code],
                `core aceitou ${caseItem.field} em branco`,
            )
            assert.equal(compositionSchemaCheck(composition).valid, false, `schema aceitou ${caseItem.field} em branco`)
        }
    }

    for (const field of blankProjectFields) {
        const manifest = manifestWithAssetRoot('projects/projeto-teste/assets')
        const document = { ...manifest, [field]: '   ' }
        const report = validateProjectDocument(document)
        assert.equal(report.valid, false, `core aceitou project.${field} em branco`)
        assert.equal(report.errors.length, 1)
        assert.match(report.errors[0]!.code, /^PROJECT_[A-Z_]+_REQUIRED$/)
        assert.equal(projectSchemaCheck(document).valid, false, `schema aceitou project.${field} em branco`)
    }

    const withBlankMetadata = compositionWith({ metadata: { description: '  ' } })
    assert.deepEqual(compositionCodes(validateCompositionDocument(withBlankMetadata)), ['COMPOSITION_METADATA_INVALID'])
    assert.equal(compositionSchemaCheck(withBlankMetadata).valid, false)

    const withBlankTag = compositionWith({ metadata: { tags: ['campanha', '   '] } })
    assert.deepEqual(compositionCodes(validateCompositionDocument(withBlankTag)), ['COMPOSITION_METADATA_INVALID'])
    assert.equal(compositionSchemaCheck(withBlankTag).valid, false)
})

test('durationMs respeita o inteiro seguro tambien no schema', () => {
    const maximum = compositionWithScenes([sceneWith({ durationMs: Number.MAX_SAFE_INTEGER })])
    assert.equal(validateCompositionDocument(maximum).valid, true)
    assert.equal(compositionSchemaCheck(maximum).valid, true)

    for (const invalid of [Number.MAX_SAFE_INTEGER + 1, 1.5, 0, -1]) {
        const document = compositionWithScenes([sceneWith({ durationMs: invalid })])
        assert.deepEqual(compositionCodes(validateCompositionDocument(document)), ['COMPOSITION_SCENE_DURATION_INVALID'])
        assert.equal(compositionSchemaCheck(document).valid, false, `schema aceitou durationMs ${invalid}`)
    }
})

test('a classificacao lexica e pura, com ordem fixa e sem efeitos colaterais', () => {
    const hostile = `/assets${NUL}/../.env`
    const frozen = hostile
    const first = inspectRelativePath(hostile)
    const second = inspectRelativePath(hostile)

    assert.deepEqual(first, ['CONTROL_CHARACTER', 'ABSOLUTE', 'TRAVERSAL', 'SENSITIVE'])
    assert.deepEqual(second, first)
    assert.notEqual(first, second)
    assert.equal(hostile, frozen)

    // A ordem de emissao e a da classificacao compartilhada, nos dois contratos.
    assert.deepEqual(projectCodes(validateProjectDocument(manifestWithAssetRoot(hostile))), [
        'PROJECT_ASSET_ROOT_CONTROL_CHARACTER',
        'PROJECT_ASSET_ROOT_ABSOLUTE',
        'PROJECT_ASSET_ROOT_TRAVERSAL',
        'PROJECT_ASSET_ROOT_SENSITIVE',
    ])
    assert.deepEqual(compositionCodes(validateCompositionDocument(compositionWithAssetPath(hostile))), [
        'COMPOSITION_ASSET_PATH_CONTROL_CHARACTER',
        'COMPOSITION_ASSET_PATH_ABSOLUTE',
        'COMPOSITION_ASSET_PATH_TRAVERSAL',
        'COMPOSITION_ASSET_PATH_SENSITIVE',
    ])

    assert.deepEqual(inspectRelativePath('assets/secretaria.png'), [])
    assert.deepEqual(pathSegments(`a${B}b/c`), ['a', 'b', 'c'])
    assert.equal(containsControlCharacter('assets/ok.png'), false)
    assert.equal(containsControlCharacter(`assets${String.fromCharCode(31)}.png`), true)
    assert.deepEqual(inspectRelativePath(''), [])
    assert.deepEqual(inspectRelativePath('//example.com/x/../.env'), ['URL', 'TRAVERSAL', 'SENSITIVE'])
})

/**
 * Divergencias registradas de proposito (README, secao "Regras do schema x regras
 * do core"): aqui o teste nao exige concordancia, exige a diferenca conhecida, para
 * que uma mudanca futura em qualquer lado seja percebida.
 */
test('regras semanticas de nomes permanecem apenas no core', () => {
    for (const value of tokenSensitivePaths) {
        assert.deepEqual(inspectRelativePath(value), ['SENSITIVE'])

        const manifest = manifestWithAssetRoot(value)
        assert.deepEqual(projectCodes(validateProjectDocument(manifest)), ['PROJECT_ASSET_ROOT_SENSITIVE'])
        assert.equal(projectSchemaCheck(manifest).valid, true, `o schema deveria aceitar (regra de tokens e do core): ${value}`)

        const composition = compositionWithAssetPath(value)
        assert.deepEqual(compositionCodes(validateCompositionDocument(composition)), ['COMPOSITION_ASSET_PATH_SENSITIVE'])
        assert.equal(compositionSchemaCheck(composition).valid, true, `o schema deveria aceitar (regra de tokens e do core): ${value}`)
    }
})

test('regras do parser de URL permanecem apenas no core', () => {
    for (const href of urlParserOnlyHrefs) {
        const composition = compositionWithHref(href)
        assert.deepEqual(compositionCodes(validateCompositionDocument(composition)), ['COMPOSITION_CTA_HREF_INVALID'])
        assert.equal(compositionSchemaCheck(composition).valid, true, `o schema deveria aceitar: ${href}`)
    }
})

test('a forma canonica scheme://host e exigida pelos dois motores (etapa 5)', () => {
    for (const href of ['http:/example.com', `https:${B}${B}example.com`, 'http:/example.com/agenda', 'https:\\example.com']) {
        const composition = compositionWithHref(href)
        const report = validateCompositionDocument(composition)
        assert.deepEqual(compositionCodes(report), ['COMPOSITION_CTA_HREF_INVALID'], `o core aceitou href ${JSON.stringify(href)}`)
        assert.equal(compositionSchemaCheck(composition).valid, false, `o schema aceitou href ${JSON.stringify(href)}`)
    }
})

test('os exemplos oficiais continuam validos depois do endurecimento', () => {
    for (const pair of officialPairs) {
        const project = readProjectExample(pair.project)
        assert.equal(validateProjectDocument(project).valid, true, `core rejeitou ${pair.project}`)
        assert.equal(projectSchemaCheck(project).valid, true, `schema rejeitou ${pair.project}`)

        const composition = readCompositionExample(pair.composition)
        assert.equal(validateCompositionDocument(composition, project).valid, true, `core rejeitou ${pair.composition}`)
        assert.equal(compositionSchemaCheck(composition).valid, true, `schema rejeitou ${pair.composition}`)
    }

    // As artes oficiais seguem referenciando caminhos relativos simples.
    const composition = readCompositionExample(officialPairs[0]!.composition)
    const scenes = composition.scenes as { content: Record<string, unknown> }[]
    const assetPaths = scenes.map((scene) => (scene.content.asset as { path?: string } | undefined)?.path).filter((p) => typeof p === 'string')
    assert.ok(assetPaths.length > 0, 'a composicao oficial precisa de ao menos um asset.path para a regressao')
    for (const assetPath of assetPaths) {
        assert.deepEqual(inspectRelativePath(assetPath), [])
    }
})
