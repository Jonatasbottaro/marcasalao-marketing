/**
 * Contrato de solicitacao versionado para validacao de Composition v1 contra
 * ProjectManifest em TEMPORAL-02 (TEMPORAL-02-02).
 *
 * Modulo puro e independente de @temporalio/*, de rede, de disco e de platform/src.
 * Os documentos project e composition sao validados aqui apenas quanto ao envelope
 * e serializacao sem perda; a validacao semantica do dominio ocorrera na futura Activity.
 */

export const COMPOSITION_VALIDATION_SCHEMA_VERSION = 1 as const

export const COMPOSITION_VALIDATION_REQUEST_ID_PATTERN = /^[a-z0-9][a-z0-9._-]{0,63}$/

export const COMPOSITION_VALIDATION_ENVELOPE_FIELDS = Object.freeze([
    'schemaVersion',
    'requestId',
    'project',
    'composition',
] as const)

export const COMPOSITION_VALIDATION_LIMITS = Object.freeze({
    maxProjectBytes: 65_536,
    maxCompositionBytes: 262_144,
    maxEnvelopeBytes: 393_216,
} as const)

export type JsonPrimitive = string | number | boolean | null

export type JsonValue = JsonPrimitive | readonly JsonValue[] | JsonObject

export interface JsonObject {
    readonly [key: string]: JsonValue
}

export interface CompositionValidationWorkflowInput {
    readonly schemaVersion: typeof COMPOSITION_VALIDATION_SCHEMA_VERSION
    readonly requestId: string
    readonly project: JsonObject
    readonly composition: JsonObject
}

export interface CompositionValidationPayloadSizes {
    readonly projectBytes: number
    readonly compositionBytes: number
    readonly envelopeBytes: number
}

export interface CompositionValidationLimits {
    readonly maxProjectBytes: number
    readonly maxCompositionBytes: number
    readonly maxEnvelopeBytes: number
}
