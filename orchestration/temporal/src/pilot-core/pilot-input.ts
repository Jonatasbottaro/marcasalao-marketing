/**
 * Contrato e parse da entrada do piloto TEMPORAL-01.
 *
 * Camada de nucleo: nao importa nada de @temporalio. As mensagens de falha sao
 * fixas por codigo e caminho; jamais repetem o valor recebido, para que o
 * registro de erro possa ser enviado sem levar payload ou credencial.
 */
import { PILOT_FAILURE_CODES, type PilotFailureCode } from './failures.js'

export const PILOT_SCHEMA_VERSION = 1
export const PILOT_OPERATION = 'validate-pilot-request'

export type PilotOperation = typeof PILOT_OPERATION

const IDENTIFIER_PATTERN = /^[a-z0-9][a-z0-9._-]{0,63}$/
const LABEL_PATTERN = /^[A-Za-z0-9 ._-]{1,40}$/
/** Guarda-chuva contra segredo colado em campo livre; nao e classificacao completa. */
const SECRET_SHAPED_PATTERN = /(sk-|pk-|token[=:]|bearer\s|api[_-]?key|secret|password)/i

export interface TemporalPilotPayload {
    label?: string
    count?: number
    flag?: boolean
}

export interface TemporalPilotInput {
    schemaVersion: typeof PILOT_SCHEMA_VERSION
    requestId: string
    projectId: string
    operation: PilotOperation
    payload: TemporalPilotPayload
}

export type PilotInputFailure = { ok: false; code: PilotFailureCode; path: string; message: string }

export type PilotInputParseResult = { ok: true; input: TemporalPilotInput } | PilotInputFailure

const TOP_LEVEL_FIELDS = new Set(['schemaVersion', 'requestId', 'projectId', 'operation', 'payload'])

function fail(code: PilotFailureCode, path: string, message: string): PilotInputFailure {
    return { ok: false, code, path, message }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isBlank(value: unknown): boolean {
    return typeof value !== 'string' || value.trim() === ''
}

function parseIdentifier(value: unknown, field: string, missingCode: PilotFailureCode): PilotInputFailure | string {
    if (isBlank(value)) return fail(missingCode, field, `O campo obrigatorio ${field} nao foi informado.`)
    const identifier = identifierOrNull(value)
    if (identifier === null) {
        return fail(PILOT_FAILURE_CODES.inputInvalid, field, `${field} deve usar letras minusculas, digitos, ponto, traco ou underline e nao pode ter aparencia de credencial.`)
    }
    return identifier
}

/**
 * Identificador aproveitavel: as mesmas regras do parse, incluindo a guarda de
 * credencial. Um valor recusado aqui nunca chega ao resultado nem ao registro.
 */
function identifierOrNull(value: unknown): string | null {
    if (typeof value !== 'string') return null
    if (!IDENTIFIER_PATTERN.test(value)) return null
    if (SECRET_SHAPED_PATTERN.test(value)) return null
    return value
}

/** Identificadores que podem ser impressos: os validos, um a um, ou nulo. */
export interface PilotIdentities {
    requestId: string | null
    projectId: string | null
}

/**
 * Eco de uma entrada que pode ser invalida. Nada aqui lancas: uma entrada
 * qualquer devolve no maximo os dois identificadores que passaram pelas regras.
 */
export function echoIdentities(value: unknown): PilotIdentities {
    const source = isPlainObject(value) ? value : {}
    return { requestId: identifierOrNull(source.requestId), projectId: identifierOrNull(source.projectId) }
}

function parsePayload(value: unknown): { ok: true; payload: TemporalPilotPayload } | PilotInputFailure {
    if (!isPlainObject(value)) {
        return fail(PILOT_FAILURE_CODES.payloadInvalid, 'payload', 'payload deve ser um objeto pequeno e plano.')
    }

    const payload: TemporalPilotPayload = {}
    for (const key of Object.keys(value).sort()) {
        const received = value[key]

        if (key !== 'label' && key !== 'count' && key !== 'flag') {
            return fail(PILOT_FAILURE_CODES.payloadInvalid, `payload.${key}`, 'Chave de payload fora do conjunto nomeado do piloto.')
        }
        if (key === 'label') {
            if (typeof received !== 'string' || !LABEL_PATTERN.test(received)) {
                return fail(PILOT_FAILURE_CODES.payloadInvalid, 'payload.label', 'label deve ser texto curto, sem caminho nem URL.')
            }
            if (SECRET_SHAPED_PATTERN.test(received)) {
                return fail(PILOT_FAILURE_CODES.payloadInvalid, 'payload.label', 'label nao pode conter valor com aparencia de credencial.')
            }
            payload.label = received
            continue
        }
        if (key === 'count') {
            if (typeof received !== 'number' || !Number.isInteger(received) || received < 0 || received > 1000) {
                return fail(PILOT_FAILURE_CODES.payloadInvalid, 'payload.count', 'count deve ser inteiro entre 0 e 1000.')
            }
            payload.count = received
            continue
        }
        if (typeof received !== 'boolean') {
            return fail(PILOT_FAILURE_CODES.payloadInvalid, 'payload.flag', 'flag deve ser booleano.')
        }
        payload.flag = received
    }

    return { ok: true, payload }
}

export function parsePilotInput(value: unknown): PilotInputParseResult {
    if (!isPlainObject(value)) {
        return fail(PILOT_FAILURE_CODES.inputInvalid, '$', 'A entrada do piloto deve ser um objeto com exatamente cinco campos.')
    }

    const extraneous = Object.keys(value).filter((key) => !TOP_LEVEL_FIELDS.has(key)).sort()
    const firstExtraneous = extraneous[0]
    if (firstExtraneous !== undefined) {
        return fail(PILOT_FAILURE_CODES.inputInvalid, `$.${firstExtraneous}`, 'Campo fora do contrato TemporalPilotInput v1.')
    }

    if (value.schemaVersion !== PILOT_SCHEMA_VERSION) {
        return fail(PILOT_FAILURE_CODES.schemaUnsupported, 'schemaVersion', `O piloto aceita exclusivamente schemaVersion ${PILOT_SCHEMA_VERSION}.`)
    }

    const requestId = parseIdentifier(value.requestId, 'requestId', PILOT_FAILURE_CODES.requestIdRequired)
    if (typeof requestId !== 'string') return requestId

    const projectId = parseIdentifier(value.projectId, 'projectId', PILOT_FAILURE_CODES.projectIdRequired)
    if (typeof projectId !== 'string') return projectId

    if (value.operation !== PILOT_OPERATION) {
        return fail(PILOT_FAILURE_CODES.operationInvalid, 'operation', `operation deve ser ${PILOT_OPERATION}.`)
    }

    const parsedPayload = parsePayload(value.payload)
    if (!parsedPayload.ok) return parsedPayload

    return {
        ok: true,
        input: { schemaVersion: PILOT_SCHEMA_VERSION, requestId, projectId, operation: PILOT_OPERATION, payload: parsedPayload.payload },
    }
}
