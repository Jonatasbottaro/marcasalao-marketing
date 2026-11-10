/**
 * Testes unitarios do contrato CompositionValidationWorkflowInput e do preflight
 * local do cliente antes de qualquer conexao ou start no Temporal (TEMPORAL-02-02).
 *
 * Cobre:
 * - envelope fechado (schemaVersion, requestId, project, composition);
 * - validacao de schemaVersion (1 inteiro) e requestId (padrao TEMPORAL-01, <= 64);
 * - compatibilidade JSON sem perda (rejeicao de ciclos, BigInt, funcao, Symbol,
 *   undefined, NaN, Infinity, -Infinity, Date, Map, Set, TypedArray, instancias de
 *   classe, arrays esparsos, propriedades nao enumeraveis e getters/setters);
 * - medicao exata em bytes UTF-8 de project (64 KiB = 65.536), composition
 *   (256 KiB = 262.144) e envelope completo (384 KiB = 393.216), incluindo
 *   caracteres multibyte e exemplos tecnicos reais integrados;
 * - politica estreita e testavel de conteudo sensivel (chaves proibidas, variacao
 *   de caixa/separadores, URLs com username/password, caminhos absolutos Windows,
 *   UNC, POSIX e file://, .env, .env.local, PEM, P12/PFX, chaves privadas e
 *   service-account JSON);
 * - falsos positivos obrigatorios (texto editorial com "token", "senha",
 *   "nao inclua credenciais", URL HTTPS sem credenciais, caminho relativo seguro,
 *   texto com "/" e nomes de campos legitimos com substrings semelhantes);
 * - ordem deterministica de precedencia das validacoes;
 * - pureza, imutabilidade (copia estrutural antes/depois e preservacao de referencia)
 *   e sanitizacao das mensagens (nenhum valor ecoado);
 * - prova de ausencia de start via startAfterCompositionPreflight(input, start).
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import {
    COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST,
    COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES,
    COMPOSITION_VALIDATION_PREFLIGHT_MESSAGES,
    isCompositionValidationPreflightFailureCode,
} from '../../src/composition-validation/composition-validation-failures.js'
import {
    COMPOSITION_VALIDATION_ENVELOPE_FIELDS,
    COMPOSITION_VALIDATION_LIMITS,
    COMPOSITION_VALIDATION_REQUEST_ID_PATTERN,
    COMPOSITION_VALIDATION_SCHEMA_VERSION,
    type CompositionValidationWorkflowInput,
    type JsonObject,
} from '../../src/composition-validation/composition-validation-input.js'
import {
    preflightCompositionValidationInput,
    startAfterCompositionPreflight,
} from '../../src/composition-validation/composition-validation-preflight.js'

const platformExamplesDir = fileURLToPath(new URL('../../../../../platform/examples', import.meta.url))

function readJsonExample(relativePath: string): JsonObject {
    const fullPath = path.join(platformExamplesDir, relativePath)
    return JSON.parse(readFileSync(fullPath, 'utf8')) as JsonObject
}

function makeSyntheticProject(overrides: Record<string, unknown> = {}): JsonObject {
    return {
        schemaVersion: 1,
        projectId: 'fixture-project',
        name: 'Projeto Tecnico Sintetico',
        defaultLocale: 'pt-BR',
        supportedFormatProfiles: ['vertical-short-v1', 'square-feed-v1'],
        assetRoot: 'assets/fixture',
        ...overrides,
    }
}

function makeSyntheticComposition(overrides: Record<string, unknown> = {}): JsonObject {
    return {
        schemaVersion: 1,
        compositionId: 'comp-sintetica-001',
        projectId: 'fixture-project',
        locale: 'pt-BR',
        format: {
            profile: 'vertical-short-v1',
            aspectRatio: '9:16',
            width: 1080,
            height: 1920,
        },
        scenes: [
            {
                sceneId: 'scene-01',
                Order: 1,
                durationMs: 3000,
                headline: 'Texto tecnico sintetico de teste',
            },
        ],
        ...overrides,
    }
}

function makeValidEnvelope(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: COMPOSITION_VALIDATION_SCHEMA_VERSION,
        requestId: 'req-preflight-0001',
        project: makeSyntheticProject(),
        composition: makeSyntheticComposition(),
        ...overrides,
    }
}

function assertSanitizedFailure(
    result: ReturnType<typeof preflightCompositionValidationInput>,
    expectedCode: (typeof COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST)[number],
    expectedPath: string,
    forbiddenSubstrings: readonly string[] = [],
): void {
    assert.equal(result.ok, false)
    if (result.ok) {
        assert.fail('Esperava falha no preflight, mas retornou ok: true')
    }
    assert.equal(result.code, expectedCode)
    assert.equal(result.path, expectedPath)
    assert.equal(result.message, COMPOSITION_VALIDATION_PREFLIGHT_MESSAGES[expectedCode])
    assert.ok(!result.message.includes('\n'), 'mensagem nao deve conter quebras de linha ou stack trace')

    const serialized = JSON.stringify(result)
    for (const forbidden of forbiddenSubstrings) {
        if (forbidden.length > 0) {
            assert.ok(
                !serialized.includes(forbidden),
                `resultado serializado nao pode ecoar valor rejeitado (${forbidden})`,
            )
        }
    }
}

test('contrato e codigos do preflight: constantes imutaveis e tres codigos da Via A', () => {
    assert.equal(COMPOSITION_VALIDATION_SCHEMA_VERSION, 1)
    assert.equal(COMPOSITION_VALIDATION_LIMITS.maxProjectBytes, 65_536)
    assert.equal(COMPOSITION_VALIDATION_LIMITS.maxCompositionBytes, 262_144)
    assert.equal(COMPOSITION_VALIDATION_LIMITS.maxEnvelopeBytes, 393_216)
    assert.deepEqual(COMPOSITION_VALIDATION_ENVELOPE_FIELDS, [
        'schemaVersion',
        'requestId',
        'project',
        'composition',
    ])
    assert.ok(Object.isFrozen(COMPOSITION_VALIDATION_LIMITS))
    assert.ok(Object.isFrozen(COMPOSITION_VALIDATION_ENVELOPE_FIELDS))
    assert.ok(Object.isFrozen(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES))
    assert.ok(Object.isFrozen(COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST))
    assert.ok(Object.isFrozen(COMPOSITION_VALIDATION_PREFLIGHT_MESSAGES))

    assert.deepEqual(COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST, [
        'TEMPORAL_COMPOSITION_INPUT_INVALID',
        'TEMPORAL_COMPOSITION_INPUT_TOO_LARGE',
        'TEMPORAL_COMPOSITION_SENSITIVE_INPUT',
    ])

    for (const code of COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST) {
        assert.equal(isCompositionValidationPreflightFailureCode(code), true)
    }
    assert.equal(isCompositionValidationPreflightFailureCode('TEMPORAL_COMPOSITION_TIMEOUT'), false)
    assert.equal(isCompositionValidationPreflightFailureCode('TEMPORAL_COMPOSITION_ACTIVITY_FAILED'), false)
    assert.equal(
        isCompositionValidationPreflightFailureCode('TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE'),
        false,
    )
    assert.equal(
        isCompositionValidationPreflightFailureCode('TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT'),
        false,
    )
    assert.equal(isCompositionValidationPreflightFailureCode(null), false)
})

test('envelope valido e exemplos reais integrados (marca-salao e fixture-project) sao aceitos com medicoes UTF-8 exatas', () => {
    const marcaSalaoProject = readJsonExample('projects/marca-salao.project.json')
    const marcaSalaoComposition = readJsonExample('compositions/marca-salao-pilot.composition.json')
    const marcaSalaoEnvelope = {
        schemaVersion: 1,
        requestId: 'req-marca-salao-001',
        project: marcaSalaoProject,
        composition: marcaSalaoComposition,
    }

    const resMarcaSalao = preflightCompositionValidationInput(marcaSalaoEnvelope)
    assert.equal(resMarcaSalao.ok, true)
    if (resMarcaSalao.ok) {
        assert.equal(resMarcaSalao.value, marcaSalaoEnvelope)
        assert.equal(resMarcaSalao.value.project, marcaSalaoProject)
        assert.equal(resMarcaSalao.value.composition, marcaSalaoComposition)
        assert.equal(
            resMarcaSalao.sizes.projectBytes,
            Buffer.byteLength(JSON.stringify(marcaSalaoProject), 'utf8'),
        )
        assert.equal(
            resMarcaSalao.sizes.compositionBytes,
            Buffer.byteLength(JSON.stringify(marcaSalaoComposition), 'utf8'),
        )
        assert.equal(
            resMarcaSalao.sizes.envelopeBytes,
            Buffer.byteLength(JSON.stringify(marcaSalaoEnvelope), 'utf8'),
        )
        assert.equal(resMarcaSalao.sizes.projectBytes, 355)
        assert.equal(resMarcaSalao.sizes.compositionBytes, 752)
        assert.equal(resMarcaSalao.sizes.envelopeBytes, 1186)
    }

    const fixtureProject = readJsonExample('projects/fixture-project.project.json')
    const fixtureComposition = readJsonExample('compositions/fixture-project-pilot.composition.json')
    const fixtureEnvelope = {
        schemaVersion: 1,
        requestId: 'req-fixture-001',
        project: fixtureProject,
        composition: fixtureComposition,
    }

    const resFixture = preflightCompositionValidationInput(fixtureEnvelope)
    assert.equal(resFixture.ok, true)
    if (resFixture.ok) {
        assert.equal(resFixture.sizes.projectBytes, 356)
        assert.equal(resFixture.sizes.compositionBytes, 491)
        assert.equal(resFixture.sizes.envelopeBytes, 922)
    }
})

test('envelope invalido: rejeita null, array, primitivos, instancia de classe, campo ausente e campo extra', () => {
    for (const invalidRoot of [null, undefined, [], ['a'], 'texto', 123, true, new Date(), new Map()]) {
        const res = preflightCompositionValidationInput(invalidRoot)
        assertSanitizedFailure(res, COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$', ['texto'])
    }

    // Campo extra no envelope fechado
    const withExtra = makeValidEnvelope({ extraField: 'valor-extra-nao-ecoado' })
    assertSanitizedFailure(
        preflightCompositionValidationInput(withExtra),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$',
        ['extraField', 'valor-extra-nao-ecoado'],
    )

    // Campos obrigatorios ausentes
    const withoutSchema = makeValidEnvelope()
    delete withoutSchema.schemaVersion
    assertSanitizedFailure(
        preflightCompositionValidationInput(withoutSchema),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.schemaVersion',
    )

    const withoutRequestId = makeValidEnvelope()
    delete withoutRequestId.requestId
    assertSanitizedFailure(
        preflightCompositionValidationInput(withoutRequestId),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.requestId',
    )

    const withoutProject = makeValidEnvelope()
    delete withoutProject.project
    assertSanitizedFailure(
        preflightCompositionValidationInput(withoutProject),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    const withoutComposition = makeValidEnvelope()
    delete withoutComposition.composition
    assertSanitizedFailure(
        preflightCompositionValidationInput(withoutComposition),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.composition',
    )

    // project ou composition nao sendo objeto simples
    for (const badDoc of [null, [], 'doc-invalido', 42, false]) {
        assertSanitizedFailure(
            preflightCompositionValidationInput(makeValidEnvelope({ project: badDoc })),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
            '$.project',
            ['doc-invalido'],
        )
        assertSanitizedFailure(
            preflightCompositionValidationInput(makeValidEnvelope({ composition: badDoc })),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
            '$.composition',
            ['doc-invalido'],
        )
    }
})

test('schemaVersion e requestId: valida inteiro 1 e padrao de identificador ate 64 caracteres', () => {
    for (const badVersion of [0, 2, -1, 1.5, '1', null, true, NaN, Infinity]) {
        assertSanitizedFailure(
            preflightCompositionValidationInput(makeValidEnvelope({ schemaVersion: badVersion })),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
            '$.schemaVersion',
        )
    }

    // requestId validos nos limites (1 caractere e 64 caracteres)
    const minId = 'a'
    const maxId = 'a' + '0123456789._-'.repeat(4) + 'bcdefghijkl'
    assert.equal(maxId.length, 64)
    assert.ok(COMPOSITION_VALIDATION_REQUEST_ID_PATTERN.test(minId))
    assert.ok(COMPOSITION_VALIDATION_REQUEST_ID_PATTERN.test(maxId))

    assert.equal(preflightCompositionValidationInput(makeValidEnvelope({ requestId: minId })).ok, true)
    assert.equal(preflightCompositionValidationInput(makeValidEnvelope({ requestId: maxId })).ok, true)

    // requestId invalidos: vazio, espacos, maiusculas, inicio invalido, > 64 chars, nao-string
    const over64 = 'a'.repeat(65)
    for (const badRequestId of [
        '',
        '   ',
        'req com espaco',
        'Req-Maiuscula',
        '-inicia-com-traco',
        '.inicia-com-ponto',
        '_inicia-com-underscore',
        'req/barra',
        'req:dois-pontos',
        over64,
        123,
        null,
    ]) {
        assertSanitizedFailure(
            preflightCompositionValidationInput(makeValidEnvelope({ requestId: badRequestId })),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
            '$.requestId',
            typeof badRequestId === 'string' && badRequestId.trim().length > 1 ? [badRequestId] : [],
        )
    }
})

test('serializacao JSON sem perda: rejeita ciclo, BigInt, funcao, Symbol, undefined, NaN, Infinity, Date, Map, Set, classe, symbol key, array com buraco/invalido e getter', () => {
    // 1. Referencia circular direta em project e em composition
    const cyclicProject: Record<string, unknown> = { projectId: 'cyc' }
    cyclicProject.self = cyclicProject
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ project: cyclicProject })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    const cyclicComposition: Record<string, unknown> = { compositionId: 'cyc-comp' }
    cyclicComposition.nested = { back: cyclicComposition }
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ composition: cyclicComposition })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.composition',
    )

    // 2. Ciclo apontando para o proprio envelope
    const cyclicEnvelope = makeValidEnvelope()
    ;(cyclicEnvelope.project as Record<string, unknown>).root = cyclicEnvelope
    assertSanitizedFailure(
        preflightCompositionValidationInput(cyclicEnvelope),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    // 3. Valores nao serializaveis ou com perda silenciosa em objetos e arrays
    class CustomClass {
        readonly x = 1
    }

    const nonSerializableValues: unknown[] = [
        BigInt(42),
        () => 'fn',
        Symbol('sym-test'),
        undefined,
        Number.NaN,
        Number.POSITIVE_INFINITY,
        Number.NEGATIVE_INFINITY,
        new Date('2026-01-01T00:00:00.000Z'),
        new Map([['a', 1]]),
        new Set([1, 2]),
        new Uint8Array([1, 2, 3]),
        new CustomClass(),
        /regex-pattern/,
        {
            toJSON() {
                return 'custom-to-json'
            },
        },
    ]

    for (const badVal of nonSerializableValues) {
        assertSanitizedFailure(
            preflightCompositionValidationInput(
                makeValidEnvelope({ project: makeSyntheticProject({ badField: badVal }) }),
            ),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
            '$.project',
        )

        assertSanitizedFailure(
            preflightCompositionValidationInput(
                makeValidEnvelope({
                    composition: makeSyntheticComposition({ arrayWithBadValue: ['ok', badVal] }),
                }),
            ),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
            '$.composition',
        )
    }

    // 4. Propriedade Symbol em objeto
    const withSymbolKey: Record<string | symbol, unknown> = { ...makeSyntheticProject() }
    withSymbolKey[Symbol('secretSymbol')] = 'valor'
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ project: withSymbolKey })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    // 5. Array esparso (buraco vira null silenciosamente em JSON.stringify)
    const sparseArray: unknown[] = []
    sparseArray[0] = 'primeiro'
    sparseArray[2] = 'terceiro'
    assertSanitizedFailure(
        preflightCompositionValidationInput(
            makeValidEnvelope({ composition: makeSyntheticComposition({ scenes: sparseArray }) }),
        ),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.composition',
    )

    // 6. Propriedade nao enumeravel (omitida silenciosamente por JSON.stringify)
    const withNonEnumerable = makeSyntheticProject()
    Object.defineProperty(withNonEnumerable, 'hiddenProp', {
        value: 'oculto',
        enumerable: false,
    })
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ project: withNonEnumerable })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    // 7. Getter/accessor nao deve ser invocado e deve ser rejeitado
    let getterInvocations = 0
    const withGetter = makeSyntheticComposition()
    Object.defineProperty(withGetter, 'computedTrap', {
        enumerable: true,
        get() {
            getterInvocations += 1
            throw new Error('getter nao deveria ter sido executado')
        },
    })
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ composition: withGetter })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.composition',
    )
    assert.equal(getterInvocations, 0, 'preflight nao deve executar getters arbitrarios')
})

test('limites exatos em bytes UTF-8: 65.536/65.537 (project), 262.144/262.145 (composition) e 393.216/393.217 (envelope), incluindo caracteres multibyte', () => {
    // 1. Limite exato de project: 65.536 bytes aceito, 65.537 bytes rejeitado
    // {"pad":"..."} possui 10 bytes de estrutura JSON {"pad":""}
    const projectStructureOverhead = Buffer.byteLength(JSON.stringify({ pad: '' }), 'utf8')
    assert.equal(projectStructureOverhead, 10)

    const projectExact64KiB = { pad: 'a'.repeat(65_536 - projectStructureOverhead) }
    assert.equal(Buffer.byteLength(JSON.stringify(projectExact64KiB), 'utf8'), 65_536)

    const resProjectExact = preflightCompositionValidationInput(
        makeValidEnvelope({ project: projectExact64KiB }),
    )
    assert.equal(resProjectExact.ok, true)
    if (resProjectExact.ok) {
        assert.equal(resProjectExact.sizes.projectBytes, 65_536)
    }

    const projectOver64KiB = { pad: 'a'.repeat(65_537 - projectStructureOverhead) }
    assert.equal(Buffer.byteLength(JSON.stringify(projectOver64KiB), 'utf8'), 65_537)
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ project: projectOver64KiB })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge,
        '$.project',
    )

    // 2. Caso multibyte em project: "ã" ocupa 2 bytes em UTF-8 (1 caractere != 1 byte)
    // 32.763 caracteres "ã" = 65.526 bytes UTF-8 + 10 bytes de {"pad":""} = 65.536 bytes exatos!
    const multibyteExactProject = { pad: 'ã'.repeat(32_763) }
    assert.equal(multibyteExactProject.pad.length, 32_763)
    assert.equal(Buffer.byteLength(JSON.stringify(multibyteExactProject), 'utf8'), 65_536)
    assert.equal(
        preflightCompositionValidationInput(makeValidEnvelope({ project: multibyteExactProject })).ok,
        true,
    )

    // Mais 1 caractere ASCII ('x') leva para 65.537 bytes UTF-8 (embora length seja apenas 32.764!)
    const multibyteOverProject = { pad: 'ã'.repeat(32_763) + 'x' }
    assert.equal(multibyteOverProject.pad.length, 32_764)
    assert.equal(Buffer.byteLength(JSON.stringify(multibyteOverProject), 'utf8'), 65_537)
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ project: multibyteOverProject })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge,
        '$.project',
    )

    // 3. Limite exato de composition: 262.144 bytes aceito, 262.145 bytes rejeitado
    const compExact256KiB = { pad: 'b'.repeat(262_144 - projectStructureOverhead) }
    assert.equal(Buffer.byteLength(JSON.stringify(compExact256KiB), 'utf8'), 262_144)

    const resCompExact = preflightCompositionValidationInput(
        makeValidEnvelope({ composition: compExact256KiB }),
    )
    assert.equal(resCompExact.ok, true)
    if (resCompExact.ok) {
        assert.equal(resCompExact.sizes.compositionBytes, 262_144)
    }

    const compOver256KiB = { pad: 'b'.repeat(262_145 - projectStructureOverhead) }
    assert.equal(Buffer.byteLength(JSON.stringify(compOver256KiB), 'utf8'), 262_145)
    assertSanitizedFailure(
        preflightCompositionValidationInput(makeValidEnvelope({ composition: compOver256KiB })),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge,
        '$.composition',
    )

    // 4. Limite exato do envelope completo: 393.216 bytes aceito, 393.217 bytes rejeitado
    // Para atingir 393.216 bytes no envelope sem esbarrar antes no sub-limite individual de 64 KiB
    // de project, elevamos apenas maxProjectBytes nas opcoes de teste mantendo maxEnvelopeBytes = 393.216.
    const baseEnvelope = {
        schemaVersion: 1,
        requestId: 'req-envelope-limit-01',
        project: { pad: '' },
        composition: compExact256KiB,
    }
    const baseEnvelopeBytes = Buffer.byteLength(JSON.stringify(baseEnvelope), 'utf8')
    const neededProjectChars = 393_216 - baseEnvelopeBytes

    const envelopeExact384KiB = {
        schemaVersion: 1,
        requestId: 'req-envelope-limit-01',
        project: { pad: 'c'.repeat(neededProjectChars) },
        composition: compExact256KiB,
    }
    assert.equal(Buffer.byteLength(JSON.stringify(envelopeExact384KiB), 'utf8'), 393_216)

    const resEnvelopeExact = preflightCompositionValidationInput(envelopeExact384KiB, {
        limits: { maxProjectBytes: 200_000 },
    })
    assert.equal(resEnvelopeExact.ok, true)
    if (resEnvelopeExact.ok) {
        assert.equal(resEnvelopeExact.sizes.envelopeBytes, 393_216)
    }

    const envelopeOver384KiB = {
        schemaVersion: 1,
        requestId: 'req-envelope-limit-01',
        project: { pad: 'c'.repeat(neededProjectChars + 1) },
        composition: compExact256KiB,
    }
    assert.equal(Buffer.byteLength(JSON.stringify(envelopeOver384KiB), 'utf8'), 393_217)

    assertSanitizedFailure(
        preflightCompositionValidationInput(envelopeOver384KiB, {
            limits: { maxProjectBytes: 200_000 },
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge,
        '$',
    )
})

test('politica de conteudo sensivel: rejeita todas as chaves proibidas e variacoes de caixa/separadores sem ecoar chave nem valor', () => {
    const prohibitedKeys = [
        'password',
        'passwd',
        'secret',
        'token',
        'accessToken',
        'refreshToken',
        'apiKey',
        'privateKey',
        'clientSecret',
        'authorization',
        'cookie',
        'serviceAccount',
        // Variacoes de caixa e separadores
        'PASSWORD',
        'PassWd',
        'SECRET',
        'TOKEN',
        'access_token',
        'ACCESS-TOKEN',
        'refresh_token',
        'api_key',
        'API-KEY',
        'private_key',
        'client_secret',
        'Authorization',
        'COOKIE',
        'service_account',
        'Service-Account',
    ]

    for (const key of prohibitedKeys) {
        const syntheticValue = `valor-sintetico-proibido-${key.toLowerCase()}`

        const inProject = makeValidEnvelope({
            project: makeSyntheticProject({
                nestedConfig: { [key]: syntheticValue },
            }),
        })
        assertSanitizedFailure(
            preflightCompositionValidationInput(inProject),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
            '$.project.<prohibited>',
            [key, syntheticValue],
        )

        const inComposition = makeValidEnvelope({
            composition: makeSyntheticComposition({
                scenes: [{ sceneId: 's1', meta: { [key]: syntheticValue } }],
            }),
        })
        assertSanitizedFailure(
            preflightCompositionValidationInput(inComposition),
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
            '$.composition.<prohibited>',
            [key, syntheticValue],
        )
    }
})

test('politica de conteudo sensivel: rejeita URLs com username/password, caminhos absolutos (Windows, UNC, POSIX, file://) e arquivos sensiveis (.env, PEM, P12/PFX, service-account)', () => {
    const prohibitedStringCases: Array<{ label: string; value: string; marker: string }> = [
        {
            label: 'URL com username',
            value: 'https://usuario-sintetico@example.com/recurso',
            marker: 'usuario-sintetico',
        },
        {
            label: 'URL com username e password',
            value: 'https://user-teste:senha-sintetica-123@example.com/api',
            marker: 'senha-sintetica-123',
        },
        {
            label: 'caminho absoluto Windows com barra invertida',
            value: 'C:\\Users\\Sintetico\\projeto\\arquivo.json',
            marker: 'Sintetico',
        },
        {
            label: 'caminho absoluto Windows com barra normal',
            value: 'D:/Dados/Sintetico/imagem.png',
            marker: 'Sintetico',
        },
        {
            label: 'caminho UNC com barras invertidas',
            value: '\\\\servidor-interno\\compartilhamento\\arquivo.txt',
            marker: 'servidor-interno',
        },
        {
            label: 'caminho UNC com barras normais',
            value: '//servidor-interno/compartilhamento/arquivo.txt',
            marker: 'servidor-interno',
        },
        {
            label: 'caminho absoluto POSIX',
            value: '/etc/config-sintetica/app.conf',
            marker: 'config-sintetica',
        },
        {
            label: 'caminho absoluto POSIX em home',
            value: '/home/operador-sintetico/projeto/asset.png',
            marker: 'operador-sintetico',
        },
        {
            label: 'URI file://',
            value: 'file:///caminho/local/sintetico/documento.json',
            marker: 'sintetico',
        },
        {
            label: 'arquivo .env direto',
            value: '.env',
            marker: '.env',
        },
        {
            label: 'arquivo .env.local em caminho relativo',
            value: 'config/.env.local',
            marker: '.env.local',
        },
        {
            label: 'arquivo PEM',
            value: 'certs/certificado-sintetico.pem',
            marker: 'certificado-sintetico.pem',
        },
        {
            label: 'cabecalho PEM de chave privada',
            value: '-----BEGIN PRIVATE KEY-----BLOCO_SINTETICO_TESTE-----END PRIVATE KEY-----',
            marker: 'BLOCO_SINTETICO_TESTE',
        },
        {
            label: 'arquivo P12',
            value: 'certs/identidade-sintetica.p12',
            marker: 'identidade-sintetica.p12',
        },
        {
            label: 'arquivo PFX',
            value: 'certs/identidade-sintetica.pfx',
            marker: 'identidade-sintetica.pfx',
        },
        {
            label: 'arquivo de chave privada id_rsa',
            value: 'keys/id_rsa',
            marker: 'id_rsa',
        },
        {
            label: 'arquivo de chave privada .key',
            value: 'keys/assinatura-sintetica.key',
            marker: 'assinatura-sintetica.key',
        },
        {
            label: 'arquivo service-account JSON',
            value: 'credentials/service-account.json',
            marker: 'service-account.json',
        },
        {
            label: 'arquivo service_account com sufixo JSON',
            value: 'config/service-account-test-fixture.json',
            marker: 'service-account-test-fixture.json',
        },
    ]

    for (const item of prohibitedStringCases) {
        const resProject = preflightCompositionValidationInput(
            makeValidEnvelope({
                project: makeSyntheticProject({ note: item.value }),
            }),
        )
        assertSanitizedFailure(
            resProject,
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
            '$.project.<prohibited>',
            [item.marker],
        )

        const resComposition = preflightCompositionValidationInput(
            makeValidEnvelope({
                composition: makeSyntheticComposition({
                    scenes: [{ sceneId: 'scene-01', text: item.value }],
                }),
            }),
        )
        assertSanitizedFailure(
            resComposition,
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
            '$.composition.<prohibited>',
            [item.marker],
        )
    }
})

test('falsos positivos obrigatorios (Secao 12): aceita texto editorial sobre token/senha/credenciais, URL HTTPS limpa, caminho relativo, texto com barra e chaves legitimas com substrings', () => {
    const editorialEnvelope = makeValidEnvelope({
        project: makeSyntheticProject({
            assetRoot: 'assets/images/hero.png',
            websiteUrl: 'https://marcasalao.com.br/sistema',
            secretaria: 'Recepcao Principal',
            cookiePolicy: 'estrita',
            passwordless: true,
        }),
        composition: makeSyntheticComposition({
            tokenCount: 128,
            maxTokens: 512,
            scenes: [
                {
                    sceneId: 'scene-token-concept',
                    headline:
                        'Esta cena explica o conceito de token de autenticacao em APIs modernas sem conter segredo.',
                    body: 'Instrucao editorial: escolha uma senha forte no cadastro do aplicativo.',
                    editorialNote: 'Descricao de seguranca: nao inclua credenciais nos textos de roteiro.',
                    ctaHref: 'https://marcasalao.com.br/agendamento',
                    assetPath: 'assets/images/hero.png',
                    categoryLabel: 'Agendamento 24/7 para salao / barbearia / estetica',
                },
            ],
        }),
    })

    const result = preflightCompositionValidationInput(editorialEnvelope)
    assert.equal(result.ok, true, 'textos editoriais legitimos nao devem acionar falso positivo')
})

test('ordem deterministica de validacao (Secao 13): retorna sempre o primeiro erro segundo a precedencia canonica', () => {
    // 1 vs 2..11: nao-objeto vence qualquer outro problema
    assertSanitizedFailure(
        preflightCompositionValidationInput('nao-objeto'),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$',
    )

    // 2 vs 3..11: chave extra no envelope ($) vence schemaVersion invalida ($.schemaVersion) e conteudo sensivel
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 99,
            requestId: 'INVALIDO!',
            project: { password: 'x' },
            composition: null,
            extraKey: true,
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$',
    )

    // 3 vs 4..11: schemaVersion invalida ($.schemaVersion) vence requestId invalido ($.requestId)
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 2,
            requestId: 'INVALIDO!',
            project: null,
            composition: null,
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.schemaVersion',
    )

    // 4 vs 5..11: requestId invalido ($.requestId) vence project ausente ($.project)
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 1,
            requestId: 'INVALIDO!',
            composition: null,
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.requestId',
    )

    // 5 vs 6..11: project ausente/invalido ($.project) vence composition ausente ($.composition)
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 1,
            requestId: 'req-ordem-01',
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    // 6 vs 7..11: composition ausente ($.composition) vence problemas internos de project
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 1,
            requestId: 'req-ordem-01',
            project: { badNumber: Number.NaN, password: 'x' },
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.composition',
    )

    // 7 vs 8..11: compatibilidade JSON sem perda (INPUT_INVALID) vence conteudo sensivel (SENSITIVE_INPUT) e tamanho (INPUT_TOO_LARGE)
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 1,
            requestId: 'req-ordem-01',
            project: {
                badNumber: Number.NaN,
                password: 'synthetic-flag',
                pad: 'a'.repeat(70_000),
            },
            composition: makeSyntheticComposition(),
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
        '$.project',
    )

    // 8 vs 9..11: conteudo sensivel (SENSITIVE_INPUT) vence excesso de tamanho (INPUT_TOO_LARGE)
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 1,
            requestId: 'req-ordem-01',
            project: {
                password: 'synthetic-flag',
                pad: 'a'.repeat(70_000),
            },
            composition: makeSyntheticComposition({
                pad: 'b'.repeat(270_000),
            }),
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
        '$.project.<prohibited>',
    )

    // 9 vs 10..11: tamanho de project ($.project) vence tamanho de composition ($.composition)
    assertSanitizedFailure(
        preflightCompositionValidationInput({
            schemaVersion: 1,
            requestId: 'req-ordem-01',
            project: { pad: 'a'.repeat(70_000) },
            composition: { pad: 'b'.repeat(270_000) },
        }),
        COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge,
        '$.project',
    )
})

test('pureza, determinismo e imutabilidade (Secao 14): nao altera o input e preserva a mesma referencia quando ok: true', () => {
    const validInput = makeValidEnvelope({
        project: makeSyntheticProject({ zKey: 'ultimo', aKey: 'primeiro' }),
        composition: makeSyntheticComposition({ bKey: [3, 2, 1], aKey: { y: 2, x: 1 } }),
    })
    const snapshotBefore = structuredClone(validInput)

    const firstRun = preflightCompositionValidationInput(validInput)
    const secondRun = preflightCompositionValidationInput(validInput)

    assert.deepEqual(validInput, snapshotBefore, 'preflight nao pode mutar o envelope valido')
    assert.deepEqual(
        Object.keys(validInput.project as Record<string, unknown>),
        Object.keys(snapshotBefore.project as Record<string, unknown>),
        'preflight nao pode reordenar chaves de project',
    )
    assert.deepEqual(firstRun, secondRun, 'preflight deve ser deterministico para a mesma entrada')
    assert.equal(firstRun.ok, true)
    if (firstRun.ok) {
        assert.equal(firstRun.value, validInput, 'deve devolver a mesma referencia de entrada quando ok: true')
        assert.equal(firstRun.value.project, validInput.project)
        assert.equal(firstRun.value.composition, validInput.composition)
    }

    // Tambem nao muta entrada invalida/sensivel
    const invalidInput = makeValidEnvelope({
        project: makeSyntheticProject({ apiKey: 'synthetic-test-only' }),
    })
    const invalidSnapshot = structuredClone(invalidInput)
    const failedFirst = preflightCompositionValidationInput(invalidInput)
    const failedSecond = preflightCompositionValidationInput(invalidInput)

    assert.deepEqual(invalidInput, invalidSnapshot, 'preflight nao pode mutar entrada rejeitada')
    assert.deepEqual(failedFirst, failedSecond)
})

test('prova de ausencia de start (Secao 15): startAfterCompositionPreflight chama callback 0 vezes nas rejeicoes, 1 vez no valido e propaga erro do callback', async () => {
    // 1. Input invalido -> callback 0 vezes
    let invalidCalls = 0
    const resInvalid = await startAfterCompositionPreflight(
        makeValidEnvelope({ schemaVersion: 2 }),
        () => {
            invalidCalls += 1
            return 'started'
        },
    )
    assert.equal(invalidCalls, 0)
    assert.equal(resInvalid.ok, false)
    if (!resInvalid.ok) {
        assert.equal(resInvalid.code, COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid)
    }

    // 2. Input grande -> callback 0 vezes
    let largeCalls = 0
    const resLarge = await startAfterCompositionPreflight(
        makeValidEnvelope({ project: { pad: 'a'.repeat(70_000) } }),
        () => {
            largeCalls += 1
            return 'started'
        },
    )
    assert.equal(largeCalls, 0)
    assert.equal(resLarge.ok, false)
    if (!resLarge.ok) {
        assert.equal(resLarge.code, COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge)
    }

    // 3. Conteudo sensivel -> callback 0 vezes
    let sensitiveCalls = 0
    const resSensitive = await startAfterCompositionPreflight(
        makeValidEnvelope({ composition: makeSyntheticComposition({ token: 'synthetic-test-val' }) }),
        () => {
            sensitiveCalls += 1
            return 'started'
        },
    )
    assert.equal(sensitiveCalls, 0)
    assert.equal(resSensitive.ok, false)
    if (!resSensitive.ok) {
        assert.equal(resSensitive.code, COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput)
    }

    // 4. Input valido -> callback chamado exatamente 1 vez com apenas o valor validado
    const validEnvelope = makeValidEnvelope()
    const receivedArgs: unknown[][] = []
    const resValid = await startAfterCompositionPreflight(
        validEnvelope,
        (...args: [CompositionValidationWorkflowInput]) => {
            receivedArgs.push(args)
            return { workflowId: `temporal-composition-${args[0].requestId}` }
        },
    )
    assert.equal(receivedArgs.length, 1)
    assert.equal(receivedArgs[0]?.length, 1)
    assert.equal(receivedArgs[0]?.[0], validEnvelope)
    assert.equal(resValid.ok, true)
    if (resValid.ok) {
        assert.equal(resValid.preflight.value, validEnvelope)
        assert.deepEqual(resValid.startResult, { workflowId: 'temporal-composition-req-preflight-0001' })
    }

    // 5. Falha do callback de start e propagada sem ser recategorizada como falha de preflight
    const startError = new Error('falha simulada no callback de start pos-preflight')
    await assert.rejects(
        async () => {
            await startAfterCompositionPreflight(validEnvelope, async () => {
                throw startError
            })
        },
        (thrown: unknown) => {
            assert.equal(thrown, startError)
            return true
        },
    )
})
