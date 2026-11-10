/**
 * Preflight local do cliente para TEMPORAL-02 (TEMPORAL-02-02).
 *
 * Executa inteiramente antes de qualquer conexao ou start no Temporal:
 * 1. envelope e objeto simples;
 * 2. conjunto exato de chaves (contrato fechado no envelope);
 * 3. schemaVersion === 1 (inteiro);
 * 4. requestId valido (^[a-z0-9][a-z0-9._-]{0,63}$);
 * 5. presenca e forma de objeto simples de project;
 * 6. presenca e forma de objeto simples de composition;
 * 7. compatibilidade JSON sem perda estrutural (sem ciclos, BigInt, funcao,
 *    Symbol, undefined, NaN, Infinity, Date, Map, Set, TypedArray, instancias
 *    de classe, arrays esparsos, propriedades nao enumeraveis ou getters);
 * 8. politica estreita e testavel de conteudo sensivel em project e composition;
 * 9. medicao UTF-8 de project (<= 64 KiB = 65.536 bytes);
 * 10. medicao UTF-8 de composition (<= 256 KiB = 262.144 bytes);
 * 11. medicao UTF-8 do envelope completo (<= 384 KiB = 393.216 bytes).
 *
 * Pureza e imutabilidade: nao muta a entrada, nao ordena chaves, nao preenche
 * defaults, nao le relogio/ambiente/disco/rede e devolve a mesma referencia de
 * entrada quando ok: true.
 */
import {
    COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES,
    COMPOSITION_VALIDATION_PREFLIGHT_MESSAGES,
    type CompositionValidationPreflightFailureCode,
} from './composition-validation-failures.js'
import {
    COMPOSITION_VALIDATION_ENVELOPE_FIELDS,
    COMPOSITION_VALIDATION_LIMITS,
    COMPOSITION_VALIDATION_REQUEST_ID_PATTERN,
    COMPOSITION_VALIDATION_SCHEMA_VERSION,
    type CompositionValidationLimits,
    type CompositionValidationPayloadSizes,
    type CompositionValidationWorkflowInput,
} from './composition-validation-input.js'

export type CompositionValidationPreflightSuccess = {
    readonly ok: true
    readonly value: CompositionValidationWorkflowInput
    readonly sizes: CompositionValidationPayloadSizes
}

export type CompositionValidationPreflightFailure = {
    readonly ok: false
    readonly code: CompositionValidationPreflightFailureCode
    readonly message: string
    readonly path: string
}

export type CompositionValidationPreflightResult =
    | CompositionValidationPreflightSuccess
    | CompositionValidationPreflightFailure

export interface CompositionValidationPreflightOptions {
    readonly limits?: Partial<CompositionValidationLimits>
}

export type CompositionValidationStartCallback<TResult> = (
    validatedInput: CompositionValidationWorkflowInput,
) => TResult | Promise<TResult>

export type CompositionValidationStartGateResult<TResult> =
    | {
          readonly ok: true
          readonly preflight: CompositionValidationPreflightSuccess
          readonly startResult: TResult
      }
    | CompositionValidationPreflightFailure

const ENVELOPE_FIELD_SET: ReadonlySet<string> = new Set(COMPOSITION_VALIDATION_ENVELOPE_FIELDS)

const PROHIBITED_NORMALIZED_KEYS: ReadonlySet<string> = new Set([
    'password',
    'passwd',
    'secret',
    'token',
    'accesstoken',
    'refreshtoken',
    'apikey',
    'privatekey',
    'clientsecret',
    'authorization',
    'cookie',
    'serviceaccount',
])

const URL_SCHEME_PREFIX_PATTERN = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//
const URL_EMBEDDED_CREDENTIALS_PATTERN = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^/\s?#]+@/
const FILE_URI_PATTERN = /^file:\/\//i
const WINDOWS_ABSOLUTE_PATH_PATTERN = /^[A-Za-z]:[\\/]/
const UNC_PATH_PATTERN = /^(?:\\\\|\/\/)[^\\/\s]+[\\/][^\\/\s]+/
const POSIX_KNOWN_ROOT_PATTERN =
    /^\/(?:etc|home|Users|root|var|tmp|opt|usr|proc|sys|dev|mnt|srv|private|Volumes|dados)(?:\/|$)/
const PEM_PRIVATE_KEY_HEADER_PATTERN = /-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----/
const PATH_LIKE_SEGMENT_PATTERN = /^[A-Za-z0-9._ -]+$/
const SERVICE_ACCOUNT_JSON_SEGMENT_PATTERN = /^service[-_]?account(?:[-_.][a-z0-9._-]+)?\.json$/i

const SENSITIVE_KEY_FILE_NAMES: ReadonlySet<string> = new Set([
    'id_rsa',
    'id_dsa',
    'id_ecdsa',
    'id_ed25519',
    'private-key',
    'private_key',
])

const SENSITIVE_FILE_EXTENSIONS = ['.pem', '.p12', '.pfx', '.key'] as const

function fail(
    code: CompositionValidationPreflightFailureCode,
    path: string,
): CompositionValidationPreflightFailure {
    return {
        ok: false,
        code,
        message: COMPOSITION_VALIDATION_PREFLIGHT_MESSAGES[code],
        path,
    }
}

function hasPlainObjectPrototype(value: object): boolean {
    const proto: unknown = Object.getPrototypeOf(value)
    if (proto !== null && proto !== Object.prototype) {
        return false
    }
    return Object.prototype.toString.call(value) === '[object Object]'
}

function isPlainObjectRootShell(value: unknown): value is Record<string, unknown> {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return false
    }
    return hasPlainObjectPrototype(value)
}

function isLosslessPlainObjectShell(value: unknown): value is Record<string, unknown> {
    if (!isPlainObjectRootShell(value)) {
        return false
    }
    if (Object.getOwnPropertySymbols(value).length > 0) {
        return false
    }
    const descriptors = Object.getOwnPropertyDescriptors(value)
    for (const key of Object.keys(descriptors)) {
        const desc = descriptors[key]
        if (desc === undefined) {
            return false
        }
        if ('get' in desc && desc.get !== undefined) {
            return false
        }
        if ('set' in desc && desc.set !== undefined) {
            return false
        }
        if (!desc.enumerable) {
            return false
        }
    }
    return true
}

function inspectLosslessJsonValue(value: unknown, activeAncestors: Set<object>): boolean {
    if (value === null || typeof value === 'boolean' || typeof value === 'string') {
        return true
    }
    if (typeof value === 'number') {
        return Number.isFinite(value)
    }
    if (typeof value !== 'object') {
        return false
    }

    if (activeAncestors.has(value)) {
        return false
    }

    if (Array.isArray(value)) {
        if (Object.getPrototypeOf(value) !== Array.prototype) {
            return false
        }
        if (Object.getOwnPropertySymbols(value).length > 0) {
            return false
        }
        const descriptors = Object.getOwnPropertyDescriptors(value)
        const ownKeys = Object.keys(descriptors)
        if (ownKeys.length !== value.length + 1) {
            return false
        }

        activeAncestors.add(value)
        for (let index = 0; index < value.length; index += 1) {
            const desc = descriptors[String(index)]
            if (
                desc === undefined ||
                !desc.enumerable ||
                ('get' in desc && desc.get !== undefined) ||
                ('set' in desc && desc.set !== undefined)
            ) {
                activeAncestors.delete(value)
                return false
            }
            if (!inspectLosslessJsonValue(desc.value, activeAncestors)) {
                activeAncestors.delete(value)
                return false
            }
        }
        activeAncestors.delete(value)
        return true
    }

    if (!isLosslessPlainObjectShell(value)) {
        return false
    }

    const descriptors = Object.getOwnPropertyDescriptors(value)
    activeAncestors.add(value)
    for (const key of Object.keys(descriptors)) {
        const desc = descriptors[key]
        if (desc === undefined) {
            activeAncestors.delete(value)
            return false
        }
        if (!inspectLosslessJsonValue(desc.value, activeAncestors)) {
            activeAncestors.delete(value)
            return false
        }
    }
    activeAncestors.delete(value)
    return true
}

function isProhibitedKeyName(key: string): boolean {
    const trimmed = key.trim().toLowerCase()
    if (trimmed === '.env' || trimmed.startsWith('.env.')) {
        return true
    }
    const normalized = key.replace(/[^a-zA-Z0-9]/g, '').toLowerCase()
    return PROHIBITED_NORMALIZED_KEYS.has(normalized)
}

function isUrlWithEmbeddedCredentials(trimmed: string): boolean {
    if (!URL_SCHEME_PREFIX_PATTERN.test(trimmed)) {
        return false
    }
    if (URL_EMBEDDED_CREDENTIALS_PATTERN.test(trimmed)) {
        return true
    }
    try {
        const parsed = new URL(trimmed)
        return parsed.username.length > 0 || parsed.password.length > 0
    } catch {
        return false
    }
}

function isAbsolutePathOrFileUri(trimmed: string): boolean {
    if (FILE_URI_PATTERN.test(trimmed)) {
        return true
    }
    if (WINDOWS_ABSOLUTE_PATH_PATTERN.test(trimmed)) {
        return true
    }
    if (UNC_PATH_PATTERN.test(trimmed)) {
        return true
    }
    if (trimmed.startsWith('/') && !trimmed.startsWith('//')) {
        if (POSIX_KNOWN_ROOT_PATTERN.test(trimmed)) {
            return true
        }
        if (trimmed.length > 1 && !/\s/.test(trimmed)) {
            return true
        }
    }
    return false
}

function isSensitivePathSegment(segment: string): boolean {
    const lower = segment.trim().toLowerCase()
    if (lower.length === 0) {
        return false
    }
    if (lower === '.env' || lower.startsWith('.env.')) {
        return true
    }
    if (SENSITIVE_FILE_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
        return true
    }
    if (SERVICE_ACCOUNT_JSON_SEGMENT_PATTERN.test(lower)) {
        return true
    }
    if (SENSITIVE_KEY_FILE_NAMES.has(lower)) {
        return true
    }
    for (const keyPrefix of SENSITIVE_KEY_FILE_NAMES) {
        if (lower.startsWith(`${keyPrefix}.`)) {
            return true
        }
    }
    return false
}

function isKnownSensitiveFileReference(trimmed: string): boolean {
    if (PEM_PRIVATE_KEY_HEADER_PATTERN.test(trimmed)) {
        return true
    }
    if (URL_SCHEME_PREFIX_PATTERN.test(trimmed)) {
        return false
    }

    const segments = trimmed.split(/[\\/]/).filter((part) => part.length > 0)
    if (segments.length === 0) {
        return false
    }

    const isSingleTokenWithoutWhitespace = segments.length === 1 && !/\s/.test(trimmed)
    const isMultiSegmentPathLike =
        segments.length > 1 && segments.every((seg) => PATH_LIKE_SEGMENT_PATTERN.test(seg))

    if (!isSingleTokenWithoutWhitespace && !isMultiSegmentPathLike) {
        return false
    }

    return segments.some((segment) => isSensitivePathSegment(segment))
}

function isProhibitedStringValue(value: string): boolean {
    const trimmed = value.trim()
    if (trimmed.length === 0) {
        return false
    }
    if (isUrlWithEmbeddedCredentials(trimmed)) {
        return true
    }
    if (isAbsolutePathOrFileUri(trimmed)) {
        return true
    }
    if (isKnownSensitiveFileReference(trimmed)) {
        return true
    }
    return false
}

function containsSensitiveContent(value: unknown): boolean {
    if (typeof value === 'string') {
        return isProhibitedStringValue(value)
    }
    if (typeof value !== 'object' || value === null) {
        return false
    }
    if (Array.isArray(value)) {
        for (let index = 0; index < value.length; index += 1) {
            if (containsSensitiveContent(value[index])) {
                return true
            }
        }
        return false
    }

    const record = value as Record<string, unknown>
    for (const key of Object.keys(record)) {
        if (isProhibitedKeyName(key)) {
            return true
        }
        if (containsSensitiveContent(record[key])) {
            return true
        }
    }
    return false
}

function resolveLimits(options?: CompositionValidationPreflightOptions): CompositionValidationLimits {
    return {
        maxProjectBytes: options?.limits?.maxProjectBytes ?? COMPOSITION_VALIDATION_LIMITS.maxProjectBytes,
        maxCompositionBytes:
            options?.limits?.maxCompositionBytes ?? COMPOSITION_VALIDATION_LIMITS.maxCompositionBytes,
        maxEnvelopeBytes:
            options?.limits?.maxEnvelopeBytes ?? COMPOSITION_VALIDATION_LIMITS.maxEnvelopeBytes,
    }
}

export function preflightCompositionValidationInput(
    input: unknown,
    options?: CompositionValidationPreflightOptions,
): CompositionValidationPreflightResult {
    // 1. Envelope e objeto simples (sem getters, symbols ou propriedades nao enumeraveis)
    if (!isLosslessPlainObjectShell(input)) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$')
    }

    // 2. Conjunto exato de chaves (rejeita chaves extras no envelope fechado)
    for (const key of Object.keys(input)) {
        if (!ENVELOPE_FIELD_SET.has(key)) {
            return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$')
        }
    }

    // 3. schemaVersion
    const schemaVersion = input.schemaVersion
    if (
        typeof schemaVersion !== 'number' ||
        !Number.isInteger(schemaVersion) ||
        schemaVersion !== COMPOSITION_VALIDATION_SCHEMA_VERSION
    ) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$.schemaVersion')
    }

    // 4. requestId
    const requestId = input.requestId
    if (typeof requestId !== 'string' || !COMPOSITION_VALIDATION_REQUEST_ID_PATTERN.test(requestId)) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$.requestId')
    }

    // 5. Presenca e objeto simples de project
    const project = input.project
    if (!isPlainObjectRootShell(project)) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$.project')
    }

    // 6. Presenca e objeto simples de composition
    const composition = input.composition
    if (!isPlainObjectRootShell(composition)) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$.composition')
    }

    // 7. Compatibilidade JSON sem perda
    const projectAncestors = new Set<object>([input])
    if (!inspectLosslessJsonValue(project, projectAncestors)) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$.project')
    }

    const compositionAncestors = new Set<object>([input])
    if (!inspectLosslessJsonValue(composition, compositionAncestors)) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid, '$.composition')
    }

    // 8. Conteudo sensivel
    if (containsSensitiveContent(project)) {
        return fail(
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
            '$.project.<prohibited>',
        )
    }

    if (containsSensitiveContent(composition)) {
        return fail(
            COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
            '$.composition.<prohibited>',
        )
    }

    const limits = resolveLimits(options)

    // 9. Medicao UTF-8 de project
    const projectBytes = Buffer.byteLength(JSON.stringify(project), 'utf8')
    if (projectBytes > limits.maxProjectBytes) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge, '$.project')
    }

    // 10. Medicao UTF-8 de composition
    const compositionBytes = Buffer.byteLength(JSON.stringify(composition), 'utf8')
    if (compositionBytes > limits.maxCompositionBytes) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge, '$.composition')
    }

    // 11. Medicao UTF-8 do envelope completo
    const envelopeBytes = Buffer.byteLength(JSON.stringify(input), 'utf8')
    if (envelopeBytes > limits.maxEnvelopeBytes) {
        return fail(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge, '$')
    }

    // Devolve a mesma referencia de entrada comprovada pelo type guard estrutural
    return {
        ok: true,
        value: input as unknown as CompositionValidationWorkflowInput,
        sizes: {
            projectBytes,
            compositionBytes,
            envelopeBytes,
        },
    }
}

export async function startAfterCompositionPreflight<TResult>(
    input: unknown,
    start: CompositionValidationStartCallback<TResult>,
    options?: CompositionValidationPreflightOptions,
): Promise<CompositionValidationStartGateResult<TResult>> {
    const preflight = preflightCompositionValidationInput(input, options)
    if (!preflight.ok) {
        return preflight
    }
    const startResult = await start(preflight.value)
    return {
        ok: true,
        preflight,
        startResult,
    }
}
