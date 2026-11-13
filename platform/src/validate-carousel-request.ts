/**
 * Validador puro do CarouselRequest v1.
 *
 * Garante a estrutura exata do pedido (schemaVersion === 1, id kebab-case,
 * project/title nao vazios, profile kebab-case, cadastro de midia de imagem e
 * cards ordenados com referencias validas), rejeita campos desconhecidos e
 * devolve codigos de falha estaveis. A resolucao do perfil pelo catalogo e pela
 * allowlist do projeto fica na camada de exportacao.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    CAROUSEL_CARD_FIELDS,
    CAROUSEL_CARD_REQUIRED_FIELDS,
    CAROUSEL_MEDIA_FIELDS,
    CAROUSEL_MEDIA_REQUIRED_FIELDS,
    CAROUSEL_MEDIA_TYPES,
    CAROUSEL_REQUEST_SCHEMA_VERSION,
    CAROUSEL_REQUEST_TOP_LEVEL_FIELDS,
    type CarouselCard,
    type CarouselMedia,
    type CarouselMediaType,
    type CarouselRequest,
    type CarouselRequestFailureCode,
    type CarouselRequestValidationResult,
} from './carousel-request-contract.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isKebabCase(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function hasOnlyKnownFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    return Object.keys(value).every((key) => (allowed as readonly string[]).includes(key))
}

function hasRequiredFields(value: Record<string, unknown>, required: readonly string[]): boolean {
    return required.every((field) => value[field] !== undefined)
}

function fail(failureCode: CarouselRequestFailureCode, subject: string | null): CarouselRequestValidationResult {
    return { ok: false, failureCode, subject }
}

function readMedia(input: unknown, seen: Set<string>): { ok: true; media: CarouselMedia } | { ok: false; failureCode: CarouselRequestFailureCode; subject: string | null } {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, CAROUSEL_MEDIA_FIELDS) || !hasRequiredFields(input, CAROUSEL_MEDIA_REQUIRED_FIELDS)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_INVALID', subject: null }
    }
    if (!isKebabCase(input.id)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_ID_INVALID', subject: typeof input.id === 'string' ? input.id : null }
    }
    if (seen.has(input.id)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_ID_DUPLICATE', subject: input.id }
    }
    if (!isNonEmptyString(input.path)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_PATH_INVALID', subject: input.id }
    }
    if (typeof input.type !== 'string' || !(CAROUSEL_MEDIA_TYPES as readonly string[]).includes(input.type)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_TYPE_INVALID', subject: input.id }
    }
    if (!isNonEmptyString(input.origin)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_ORIGIN_INVALID', subject: input.id }
    }
    if (input.license !== undefined && !isNonEmptyString(input.license)) {
        return { ok: false, failureCode: 'CAROUSEL_MEDIA_LICENSE_INVALID', subject: input.id }
    }
    seen.add(input.id)
    const media: CarouselMedia = {
        id: input.id,
        path: input.path,
        type: input.type as CarouselMediaType,
        origin: input.origin,
        ...(input.license !== undefined ? { license: input.license } : {}),
    }
    return { ok: true, media }
}

function readCard(input: unknown, mediaIds: Set<string>, seen: Set<string>): { ok: true; card: CarouselCard } | { ok: false; failureCode: CarouselRequestFailureCode; subject: string | null } {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, CAROUSEL_CARD_FIELDS) || !hasRequiredFields(input, CAROUSEL_CARD_REQUIRED_FIELDS)) {
        return { ok: false, failureCode: 'CAROUSEL_CARDS_INVALID', subject: null }
    }
    if (!isKebabCase(input.id)) {
        return { ok: false, failureCode: 'CAROUSEL_CARD_ID_INVALID', subject: typeof input.id === 'string' ? input.id : null }
    }
    if (seen.has(input.id)) {
        return { ok: false, failureCode: 'CAROUSEL_CARD_ID_DUPLICATE', subject: input.id }
    }
    if (!isNonEmptyString(input.title)) {
        return { ok: false, failureCode: 'CAROUSEL_CARD_TITLE_INVALID', subject: input.id }
    }
    if (input.body !== undefined && !isNonEmptyString(input.body)) {
        return { ok: false, failureCode: 'CAROUSEL_CARD_BODY_INVALID', subject: input.id }
    }
    if (input.mediaId !== undefined && (typeof input.mediaId !== 'string' || !mediaIds.has(input.mediaId))) {
        return { ok: false, failureCode: 'CAROUSEL_CARD_MEDIA_REFERENCE_INVALID', subject: input.id }
    }
    seen.add(input.id)
    const card: CarouselCard = {
        id: input.id,
        title: input.title,
        ...(input.body !== undefined ? { body: input.body } : {}),
        ...(input.mediaId !== undefined ? { mediaId: input.mediaId } : {}),
    }
    return { ok: true, card }
}

export function validateCarouselRequest(input: unknown): CarouselRequestValidationResult {
    if (!isPlainObject(input)) {
        return fail('CAROUSEL_REQUEST_INVALID', null)
    }
    if (!hasOnlyKnownFields(input, CAROUSEL_REQUEST_TOP_LEVEL_FIELDS)) {
        const unknown = Object.keys(input).find((key) => !(CAROUSEL_REQUEST_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) ?? null
        return fail('CAROUSEL_REQUEST_UNKNOWN_FIELD', unknown)
    }
    if (input.schemaVersion !== CAROUSEL_REQUEST_SCHEMA_VERSION) {
        return fail('CAROUSEL_REQUEST_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion')
    }
    if (!isKebabCase(input.id)) {
        return fail('CAROUSEL_REQUEST_ID_INVALID', typeof input.id === 'string' ? input.id : null)
    }
    if (!isNonEmptyString(input.project)) {
        return fail('CAROUSEL_REQUEST_PROJECT_INVALID', 'project')
    }
    if (!isNonEmptyString(input.title)) {
        return fail('CAROUSEL_REQUEST_TITLE_INVALID', 'title')
    }
    if (input.profile !== undefined && !isKebabCase(input.profile)) {
        return fail('CAROUSEL_REQUEST_PROFILE_INVALID', typeof input.profile === 'string' ? input.profile : null)
    }
    if (!Array.isArray(input.media)) {
        return fail('CAROUSEL_MEDIA_INVALID', 'media')
    }
    const media: CarouselMedia[] = []
    const mediaIds = new Set<string>()
    const seenMedia = new Set<string>()
    for (const entry of input.media) {
        const read = readMedia(entry, seenMedia)
        if (!read.ok) return fail(read.failureCode, read.subject)
        media.push(read.media)
        mediaIds.add(read.media.id)
    }
    if (!Array.isArray(input.cards) || input.cards.length === 0) {
        return fail('CAROUSEL_CARDS_INVALID', 'cards')
    }
    const cards: CarouselCard[] = []
    const seenCards = new Set<string>()
    for (const entry of input.cards) {
        const read = readCard(entry, mediaIds, seenCards)
        if (!read.ok) return fail(read.failureCode, read.subject)
        cards.push(read.card)
    }

    const request: CarouselRequest = {
        schemaVersion: 1,
        id: input.id,
        project: input.project,
        ...(input.profile !== undefined ? { profile: input.profile } : {}),
        title: input.title,
        media,
        cards,
    }
    return { ok: true, request }
}