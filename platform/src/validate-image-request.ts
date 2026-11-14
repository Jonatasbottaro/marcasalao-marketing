/**
 * Validador puro estrutural do ImageRequest v1 (paridade com o schema draft-07).
 *
 * Valida campos fechados, alvo (cena/card), perfil, textos editaveis com
 * limites, proporcao, geometria e o vinculo opcional de VisualAnchor. A
 * coerencia entre geometria e proporcao declarada e uma verificacao semantica
 * adicional (IMAGE_REQUEST_GEOMETRY_MISMATCH), alem da estrutura do schema.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    IMAGE_REQUEST_ANCHOR_FIELDS,
    IMAGE_REQUEST_ASPECT_RATIOS,
    IMAGE_REQUEST_ASPECT_TOLERANCE,
    IMAGE_REQUEST_CONTEXT_FIELDS,
    IMAGE_REQUEST_DESCRIPTOR_MAX,
    IMAGE_REQUEST_FRAMING_MAX,
    IMAGE_REQUEST_GEOMETRY_FIELDS,
    IMAGE_REQUEST_GEOMETRY_MAX,
    IMAGE_REQUEST_GEOMETRY_MIN,
    IMAGE_REQUEST_PROMPT_MAX,
    IMAGE_REQUEST_PURPOSE_MAX,
    IMAGE_REQUEST_SCHEMA_VERSION,
    IMAGE_REQUEST_TARGET_FIELDS,
    IMAGE_REQUEST_TARGET_KINDS,
    IMAGE_REQUEST_TOP_LEVEL_FIELDS,
    SHA256_HEX_PATTERN,
    type ImageRequest,
    type ImageRequestAnchor,
    type ImageRequestAspectRatio,
    type ImageRequestFailureCode,
    type ImageRequestGeometry,
    type ImageRequestTarget,
    type ImageRequestTargetKind,
    type ImageRequestValidationResult,
} from './image-request-contract.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isKebabCase(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function hasOnlyKnownFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    return Object.keys(value).every((key) => (allowed as readonly string[]).includes(key))
}

function isBoundedText(value: unknown, max: number, allowEmpty = false): value is string {
    if (typeof value !== 'string' || value.length > max) return false
    return allowEmpty ? true : value.trim().length > 0
}

function fail(failureCode: ImageRequestFailureCode, subject: string | null): ImageRequestValidationResult {
    return { ok: false, failureCode, subject }
}

function readTarget(input: unknown): ImageRequestTarget | null {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, IMAGE_REQUEST_TARGET_FIELDS)) return null
    const { kind, id } = input
    if (typeof kind !== 'string' || !(IMAGE_REQUEST_TARGET_KINDS as readonly string[]).includes(kind)) return null
    if (!isKebabCase(id)) return null
    return { kind: kind as ImageRequestTargetKind, id }
}

function readGeometry(input: unknown): ImageRequestGeometry | null {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, IMAGE_REQUEST_GEOMETRY_FIELDS)) return null
    const { width, height } = input
    for (const value of [width, height]) {
        if (typeof value !== 'number' || !Number.isSafeInteger(value)
            || value < IMAGE_REQUEST_GEOMETRY_MIN || value > IMAGE_REQUEST_GEOMETRY_MAX) return null
    }
    return { width: width as number, height: height as number }
}

function readAnchor(input: unknown): ImageRequestAnchor | null | undefined {
    if (input === null) return null
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, IMAGE_REQUEST_ANCHOR_FIELDS)) return undefined
    const { anchorId, versionId, sha256, sendToProvider } = input
    if (!isKebabCase(anchorId) || !isKebabCase(versionId)) return undefined
    if (typeof sha256 !== 'string' || !SHA256_HEX_PATTERN.test(sha256)) return undefined
    if (typeof sendToProvider !== 'boolean') return undefined
    return { anchorId, versionId, sha256, sendToProvider }
}

const ASPECT_VALUES: Record<ImageRequestAspectRatio, number> = {
    '9:16': 9 / 16,
    '1:1': 1,
    '16:9': 16 / 9,
    '4:5': 4 / 5,
}

function aspectValue(aspect: ImageRequestAspectRatio): number {
    return ASPECT_VALUES[aspect]
}

export function validateImageRequest(input: unknown): ImageRequestValidationResult {
    if (!isPlainObject(input)) {
        return fail('IMAGE_REQUEST_INVALID', null)
    }
    if (!hasOnlyKnownFields(input, IMAGE_REQUEST_TOP_LEVEL_FIELDS)) {
        const unknown = Object.keys(input).find((key) => !(IMAGE_REQUEST_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) ?? null
        return fail('IMAGE_REQUEST_UNKNOWN_FIELD', unknown)
    }
    if (input.schemaVersion !== IMAGE_REQUEST_SCHEMA_VERSION) {
        return fail('IMAGE_REQUEST_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion')
    }
    if (!isKebabCase(input.id)) {
        return fail('IMAGE_REQUEST_ID_INVALID', typeof input.id === 'string' ? input.id : null)
    }
    const target = readTarget(input.target)
    if (target === null) {
        return fail('IMAGE_REQUEST_TARGET_INVALID', 'target')
    }
    if (!isKebabCase(input.profileId)) {
        return fail('IMAGE_REQUEST_PROFILE_INVALID', typeof input.profileId === 'string' ? input.profileId : null)
    }
    if (!isBoundedText(input.prompt, IMAGE_REQUEST_PROMPT_MAX)) {
        return fail('IMAGE_REQUEST_PROMPT_INVALID', 'prompt')
    }
    if (!isBoundedText(input.purpose, IMAGE_REQUEST_PURPOSE_MAX)) {
        return fail('IMAGE_REQUEST_PURPOSE_INVALID', 'purpose')
    }
    if (!isBoundedText(input.framing, IMAGE_REQUEST_FRAMING_MAX)) {
        return fail('IMAGE_REQUEST_FRAMING_INVALID', 'framing')
    }
    if (typeof input.aspectRatio !== 'string' || !(IMAGE_REQUEST_ASPECT_RATIOS as readonly string[]).includes(input.aspectRatio)) {
        return fail('IMAGE_REQUEST_ASPECT_INVALID', 'aspectRatio')
    }
    const aspectRatio = input.aspectRatio as ImageRequestAspectRatio
    const geometry = readGeometry(input.geometry)
    if (geometry === null) {
        return fail('IMAGE_REQUEST_GEOMETRY_INVALID', 'geometry')
    }
    const expected = aspectValue(aspectRatio)
    const actual = geometry.width / geometry.height
    if (Math.abs(actual - expected) > expected * IMAGE_REQUEST_ASPECT_TOLERANCE) {
        return fail('IMAGE_REQUEST_GEOMETRY_MISMATCH', 'geometry')
    }
    const anchor = readAnchor(input.anchor)
    if (anchor === undefined) {
        return fail('IMAGE_REQUEST_ANCHOR_INVALID', 'anchor')
    }
    if (!isPlainObject(input.context) || !hasOnlyKnownFields(input.context, IMAGE_REQUEST_CONTEXT_FIELDS)) {
        return fail('IMAGE_REQUEST_CONTEXT_INVALID', 'context')
    }
    const { descriptor, contextSha256 } = input.context
    if (!isBoundedText(descriptor, IMAGE_REQUEST_DESCRIPTOR_MAX, true)) {
        return fail('IMAGE_REQUEST_CONTEXT_INVALID', 'context.descriptor')
    }
    if (typeof contextSha256 !== 'string' || !SHA256_HEX_PATTERN.test(contextSha256)) {
        return fail('IMAGE_REQUEST_CONTEXT_INVALID', 'context.contextSha256')
    }
    const request: ImageRequest = {
        schemaVersion: 1,
        id: input.id,
        target,
        profileId: input.profileId,
        prompt: input.prompt,
        purpose: input.purpose,
        framing: input.framing,
        aspectRatio,
        geometry,
        anchor,
        context: { descriptor, contextSha256 },
    }
    return { ok: true, request }
}