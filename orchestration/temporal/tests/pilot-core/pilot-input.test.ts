/**
 * Contratos do piloto TEMPORAL-01: parse da entrada e relatorio estruturado.
 *
 * Regras de determinismo herdadas do nucleo da platform: nenhuma marca de tempo,
 * nenhum identificador aleatorio, nenhum caminho absoluto, ordem de emissao fixa
 * e codigo estavel como fonte de verdade (a mensagem livre e secundaria).
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { PILOT_SCHEMA_VERSION, parsePilotInput } from '../../src/pilot-core/pilot-input.js'

function validInput(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId: 'req-0001',
        projectId: 'marcasalao',
        operation: 'validate-pilot-request',
        payload: { label: 'piloto' },
        ...overrides,
    }
}

test('a entrada minima valida e aceita e ecoa os identificadores', () => {
    const parsed = parsePilotInput(validInput())

    assert.equal(parsed.ok, true)
    assert.ok(parsed.ok)
    assert.equal(parsed.input.requestId, 'req-0001')
    assert.equal(parsed.input.projectId, 'marcasalao')
    assert.equal(parsed.input.operation, 'validate-pilot-request')
    assert.equal(parsed.input.schemaVersion, 1)
})

test('o payload e conservado integralmente quando bem formado', () => {
    const parsed = parsePilotInput(validInput({ payload: { label: 'piloto', count: 7, flag: true } }))

    assert.ok(parsed.ok)
    assert.deepEqual(parsed.input.payload, { label: 'piloto', count: 7, flag: true })
})

test('uma entrada que nao e objeto e recusada com codigo de contrato', () => {
    for (const input of [null, undefined, 'req-0001', 42, []]) {
        const parsed = parsePilotInput(input)

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_INPUT_INVALID')
        assert.equal(parsed.path, '$')
    }
})

test('um schemaVersion diferente de 1 e recusado como incompativel', () => {
    for (const schemaVersion of [0, 2, '1', null, undefined]) {
        const parsed = parsePilotInput(validInput({ schemaVersion }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_SCHEMA_UNSUPPORTED')
        assert.equal(parsed.path, 'schemaVersion')
    }
})

test('requestId ausente ou em branco e recusado com codigo proprio', () => {
    for (const requestId of [undefined, '', '   ', null]) {
        const parsed = parsePilotInput(validInput({ requestId }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_REQUEST_ID_REQUIRED')
        assert.equal(parsed.path, 'requestId')
    }
})

test('projectId ausente ou em branco e recusado com codigo proprio', () => {
    for (const projectId of [undefined, '', '   ', null]) {
        const parsed = parsePilotInput(validInput({ projectId }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_PROJECT_ID_REQUIRED')
        assert.equal(parsed.path, 'projectId')
    }
})

test('identificador fora do formato permitido e recusado como violacao de contrato', () => {
    for (const requestId of ['REQ-0001', 'req 0001', 'req/0001', 'req-0001\nsegredo', '-req', 'x'.repeat(65)]) {
        const parsed = parsePilotInput(validInput({ requestId }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_INPUT_INVALID')
        assert.equal(parsed.path, 'requestId')
    }
})

test('operation diferentes da unica operacao do piloto e recusada', () => {
    for (const operation of ['generate-campaign', 'export-preview', 'publish-post', '', undefined, 7]) {
        const parsed = parsePilotInput(validInput({ operation }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_OPERATION_INVALID')
        assert.equal(parsed.path, 'operation')
    }
})

test('payload ausente ou que nao e objeto simples e recusado', () => {
    for (const payload of [undefined, null, 'piloto', 42, [], ['label']]) {
        const parsed = parsePilotInput(validInput({ payload }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_PAYLOAD_INVALID')
        assert.equal(parsed.path, 'payload')
    }
})

test('payload com chave fora do conjunto nomeado e recusado', () => {
    const parsed = parsePilotInput(validInput({ payload: { segredo: 'abc' } }))

    assert.equal(parsed.ok, false)
    assert.ok(!parsed.ok)
    assert.equal(parsed.code, 'TEMPORAL_PILOT_PAYLOAD_INVALID')
    assert.equal(parsed.path, 'payload.segredo')
})

test('payload com valor aninhado ou em array e recusado', () => {
    for (const [path, payload] of [
        ['payload.label', { label: { interno: 1 } }],
        ['payload.label', { label: ['a'] }],
        ['payload.count', { count: 1.5 }],
        ['payload.count', { count: -1 }],
        ['payload.count', { count: 1001 }],
        ['payload.flag', { flag: 'true' }],
    ] as const) {
        const parsed = parsePilotInput(validInput({ payload }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_PAYLOAD_INVALID')
        assert.equal(parsed.path, path)
    }
})

test('label acima de quarenta caracteres e recusado', () => {
    const parsed = parsePilotInput(validInput({ payload: { label: 'x'.repeat(41) } }))

    assert.equal(parsed.ok, false)
    assert.ok(!parsed.ok)
    assert.equal(parsed.code, 'TEMPORAL_PILOT_PAYLOAD_INVALID')
    assert.equal(parsed.path, 'payload.label')
})

test('valor de payload que parece caminho absoluto ou segredo e recusado', () => {
    for (const payload of [
        { label: 'C:\\Repos\\marcasalao' },
        { label: '/home/swn/secret' },
        { label: 'https://exemplo.internal/token' },
        { label: 'sk-live-1234567890' },
    ]) {
        const parsed = parsePilotInput(validInput({ payload }))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_PAYLOAD_INVALID')
    }
})

test('a mensagem de falha nunca repete o valor que chegou na entrada', () => {
    const segredo = 'nunca-imprimir-aqui'
    const casos = [
        validInput({ requestId: `REQ ${segredo}` }),
        validInput({ projectId: `proj/${segredo}` }),
        validInput({ payload: { label: `/tmp/${segredo}` } }),
        validInput({ payload: { label: `sk-live-${segredo}` } }),
    ]

    for (const input of casos) {
        const parsed = parsePilotInput(input)

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.ok(!parsed.message.includes(segredo), `mensagem vazou o valor recebido: ${parsed.message}`)
        assert.ok(!JSON.stringify(parsed).includes(segredo), 'o registro serializado vazou o valor recebido')
    }
})

test('um identificador com aparencia de credencial e recusado e nao ecoado', () => {
    const marca = 'marca-agua'
    const casos = [{ requestId: `sk-live-${marca}` }, { projectId: `secret-${marca}` }, { requestId: `password-${marca}` }]

    for (const override of casos) {
        const parsed = parsePilotInput(validInput(override))

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.equal(parsed.code, 'TEMPORAL_PILOT_INPUT_INVALID')
        assert.ok(!JSON.stringify(parsed).includes(marca), 'a falha ecoou o identificador recebido')
    }
})

test('a mesma entrada produz exatamente o mesmo resultado duas vezes', () => {
    const entrada = validInput({ payload: { label: 'piloto', count: 3 } })

    assert.deepEqual(parsePilotInput(entrada), parsePilotInput(entrada))
    assert.deepEqual(parsePilotInput(validInput({ operation: 'gerar-campanha' })), parsePilotInput(validInput({ operation: 'gerar-campanha' })))
})

test('campos alem dos cinco contractuais sao recusados', () => {
    const parsed = parsePilotInput(validInput({ mídia: 'png' }))

    assert.equal(parsed.ok, false)
    assert.ok(!parsed.ok)
    assert.equal(parsed.code, 'TEMPORAL_PILOT_INPUT_INVALID')
    assert.equal(parsed.path, '$.mídia')
})
