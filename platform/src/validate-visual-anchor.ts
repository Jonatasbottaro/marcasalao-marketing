/**
 * Validador puro estrutural do VisualAnchor v1 (paridade com o schema draft-07).
 *
 * Valida campos fechados, identificadores kebab-case, vinculo de referencia
 * (mediaId + versionId + SHA-256) e limites de texto. A existencia fisica do
 * arquivo e a conferencia do hash ficam na camada de ferramentas.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    SHA256_HEX_PATTERN,
    VISUAL_ANCHOR_DIRECTION_MAX,
    VISUAL_ANCHOR_ELEMENT_MAX,
    VISUAL_ANCHOR_ELEMENTS_MAX,
    VISUAL_ANCHOR_LICENSE_MAX,
    VISUAL_ANCHOR_ORIGIN_MAX,
    VISUAL_ANCHOR_REFERENCE_FIELDS,
    VISUAL_ANCHOR_SCHEMA_VERSION,
    VISUAL_ANCHOR_TITLE_MAX,
    VISUAL_ANCHOR_TOP_LEVEL_FIELDS,
    type VisualAnchor,
    type VisualAnchorFailureCode,
    type VisualAnchorReference,
    type VisualAnchorValidationResult,
} from './visual-anchor-contract.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isKebabCase(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function hasOnlyKnownFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    return Object.keys(value).every((key) => (allowed as readonly string[]).includes(key))
}

function isBoundedText(value: unknown, max: number): value is string {
    return typeof value === 'string' && value.trim().length > 0 && value.length <= max
}

function fail(failureCode: VisualAnchorFailureCode, subject: string | null): VisualAnchorValidationResult {
    return { ok: false, failureCode, subject }
}

function readReference(input: unknown): VisualAnchorReference | null {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, VISUAL_ANCHOR_REFERENCE_FIELDS)) return null
    const { mediaId, versionId, sha256 } = input
    if (!isKebabCase(mediaId) || !isKebabCase(versionId)) return null
    if (typeof sha256 !== 'string' || !SHA256_HEX_PATTERN.test(sha256)) return null
    return { mediaId, versionId, sha256 }
}

function readElements(input: unknown): string[] | null {
    if (!Array.isArray(input) || input.length > VISUAL_ANCHOR_ELEMENTS_MAX) return null
    const out: string[] = []
    for (const entry of input) {
        if (!isBoundedText(entry, VISUAL_ANCHOR_ELEMENT_MAX)) return null
        out.push(entry)
    }
    return out
}

export function validateVisualAnchor(input: unknown): VisualAnchorValidationResult {
    if (!isPlainObject(input)) {
        return fail('VISUAL_ANCHOR_INVALID', null)
    }
    if (!hasOnlyKnownFields(input, VISUAL_ANCHOR_TOP_LEVEL_FIELDS)) {
        const unknown = Object.keys(input).find((key) => !(VISUAL_ANCHOR_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) ?? null
        return fail('VISUAL_ANCHOR_UNKNOWN_FIELD', unknown)
    }
    if (input.schemaVersion !== VISUAL_ANCHOR_SCHEMA_VERSION) {
        return fail('VISUAL_ANCHOR_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion')
    }
    if (!isKebabCase(input.id)) {
        return fail('VISUAL_ANCHOR_ID_INVALID', typeof input.id === 'string' ? input.id : null)
    }
    if (!isBoundedText(input.title, VISUAL_ANCHOR_TITLE_MAX)) {
        return fail('VISUAL_ANCHOR_TITLE_INVALID', 'title')
    }
    const reference = readReference(input.reference)
    if (reference === null) {
        return fail('VISUAL_ANCHOR_REFERENCE_INVALID', 'reference')
    }
    if (!isBoundedText(input.direction, VISUAL_ANCHOR_DIRECTION_MAX)) {
        return fail('VISUAL_ANCHOR_DIRECTION_INVALID', 'direction')
    }
    const mustInclude = readElements(input.mustInclude)
    if (mustInclude === null) {
        return fail('VISUAL_ANCHOR_ELEMENTS_INVALID', 'mustInclude')
    }
    const mustAvoid = readElements(input.mustAvoid)
    if (mustAvoid === null) {
        return fail('VISUAL_ANCHOR_ELEMENTS_INVALID', 'mustAvoid')
    }
    if (!isBoundedText(input.origin, VISUAL_ANCHOR_ORIGIN_MAX)) {
        return fail('VISUAL_ANCHOR_ORIGIN_INVALID', 'origin')
    }
    if (!isBoundedText(input.license, VISUAL_ANCHOR_LICENSE_MAX)) {
        return fail('VISUAL_ANCHOR_LICENSE_INVALID', 'license')
    }
    const anchor: VisualAnchor = {
        schemaVersion: 1,
        id: input.id,
        title: input.title,
        reference,
        direction: input.direction,
        mustInclude,
        mustAvoid,
        origin: input.origin,
        license: input.license,
    }
    return { ok: true, anchor }
}