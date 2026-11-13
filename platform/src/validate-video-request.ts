/**
 * Validador puro do VideoRequest v1.
 *
 * Garante a estrutura exata do pedido (schemaVersion === 1, id kebab-case,
 * project/title nao vazios, profiles nao vazios e sem duplicidade, cadastro de
 * midia e cenas ordenadas com referencias validas), rejeita campos desconhecidos
 * e devolve codigos de falha estaveis. A validacao profunda do VisualStyle e a
 * resolucao de perfis ficam no compilador; aqui o estilo e apenas um objeto.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    VIDEO_REQUEST_MEDIA_FIELDS,
    VIDEO_REQUEST_MEDIA_REQUIRED_FIELDS,
    VIDEO_REQUEST_MEDIA_TYPES,
    VIDEO_REQUEST_MOTION_INTENTS,
    VIDEO_REQUEST_NARRATIVE_FUNCTIONS,
    VIDEO_REQUEST_SCENE_FIELDS,
    VIDEO_REQUEST_SCENE_REQUIRED_FIELDS,
    VIDEO_REQUEST_SCHEMA_VERSION,
    VIDEO_REQUEST_TOP_LEVEL_FIELDS,
    type VideoRequest,
    type VideoRequestFailureCode,
    type VideoRequestMedia,
    type VideoRequestMediaType,
    type VideoRequestMotionIntent,
    type VideoRequestScene,
    type VideoRequestValidationResult,
} from './video-request-contract.js'
import type { BeatNarrativeFunction } from './beat-plan-contract.js'
import type { VisualStyle } from './visual-style-contract.js'

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

function fail(failureCode: VideoRequestFailureCode, subject: string | null): VideoRequestValidationResult {
    return { ok: false, failureCode, subject }
}

function readMedia(input: unknown, seenIds: Set<string>): { ok: true; media: VideoRequestMedia } | { ok: false; failureCode: VideoRequestFailureCode; subject: string | null } {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, VIDEO_REQUEST_MEDIA_FIELDS) || !hasRequiredFields(input, VIDEO_REQUEST_MEDIA_REQUIRED_FIELDS)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_INVALID', subject: null }
    }
    if (!isKebabCase(input.id)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_ID_INVALID', subject: typeof input.id === 'string' ? input.id : null }
    }
    if (seenIds.has(input.id)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_ID_DUPLICATE', subject: input.id }
    }
    if (!isNonEmptyString(input.path)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_PATH_INVALID', subject: input.id }
    }
    if (typeof input.type !== 'string' || !(VIDEO_REQUEST_MEDIA_TYPES as readonly string[]).includes(input.type)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_TYPE_INVALID', subject: input.id }
    }
    if (!isNonEmptyString(input.origin)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_ORIGIN_INVALID', subject: input.id }
    }
    if (input.license !== undefined && !isNonEmptyString(input.license)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_MEDIA_LICENSE_INVALID', subject: input.id }
    }
    seenIds.add(input.id)
    const media: VideoRequestMedia = {
        id: input.id,
        path: input.path,
        type: input.type as VideoRequestMediaType,
        origin: input.origin,
        ...(input.license !== undefined ? { license: input.license } : {}),
    }
    return { ok: true, media }
}

function readScene(input: unknown, mediaIds: Set<string>, seenIds: Set<string>): { ok: true; scene: VideoRequestScene } | { ok: false; failureCode: VideoRequestFailureCode; subject: string | null } {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, VIDEO_REQUEST_SCENE_FIELDS) || !hasRequiredFields(input, VIDEO_REQUEST_SCENE_REQUIRED_FIELDS)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENES_INVALID', subject: null }
    }
    if (!isKebabCase(input.id)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_ID_INVALID', subject: typeof input.id === 'string' ? input.id : null }
    }
    if (seenIds.has(input.id)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_ID_DUPLICATE', subject: input.id }
    }
    if (typeof input.durationMs !== 'number' || !Number.isSafeInteger(input.durationMs) || input.durationMs <= 0) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_DURATION_INVALID', subject: input.id }
    }
    if (typeof input.mediaId !== 'string' || !mediaIds.has(input.mediaId)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_MEDIA_REFERENCE_INVALID', subject: input.id }
    }
    if (!isNonEmptyString(input.caption)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_CAPTION_INVALID', subject: input.id }
    }
    if (!isNonEmptyString(input.narration)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_NARRATION_INVALID', subject: input.id }
    }
    if (input.title !== undefined && !isNonEmptyString(input.title)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_TITLE_INVALID', subject: input.id }
    }
    if (input.narrativeFunction !== undefined && (typeof input.narrativeFunction !== 'string' || !(VIDEO_REQUEST_NARRATIVE_FUNCTIONS as readonly string[]).includes(input.narrativeFunction))) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_NARRATIVE_FUNCTION_INVALID', subject: input.id }
    }
    if (input.motionIntent !== undefined && (typeof input.motionIntent !== 'string' || !(VIDEO_REQUEST_MOTION_INTENTS as readonly string[]).includes(input.motionIntent))) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_SCENE_MOTION_INTENT_INVALID', subject: input.id }
    }
    seenIds.add(input.id)
    const scene: VideoRequestScene = {
        id: input.id,
        durationMs: input.durationMs,
        mediaId: input.mediaId,
        caption: input.caption,
        narration: input.narration,
        ...(input.title !== undefined ? { title: input.title } : {}),
        ...(input.narrativeFunction !== undefined ? { narrativeFunction: input.narrativeFunction as BeatNarrativeFunction } : {}),
        ...(input.motionIntent !== undefined ? { motionIntent: input.motionIntent as VideoRequestMotionIntent } : {}),
    }
    return { ok: true, scene }
}

export function validateVideoRequest(input: unknown): VideoRequestValidationResult {
    if (!isPlainObject(input)) {
        return fail('VIDEO_REQUEST_INVALID', null)
    }
    if (!hasOnlyKnownFields(input, VIDEO_REQUEST_TOP_LEVEL_FIELDS)) {
        const unknown = Object.keys(input).find((key) => !(VIDEO_REQUEST_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) ?? null
        return fail('VIDEO_REQUEST_UNKNOWN_FIELD', unknown)
    }
    if (input.schemaVersion !== VIDEO_REQUEST_SCHEMA_VERSION) {
        return fail('VIDEO_REQUEST_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion')
    }
    if (!isKebabCase(input.id)) {
        return fail('VIDEO_REQUEST_ID_INVALID', typeof input.id === 'string' ? input.id : null)
    }
    if (!isNonEmptyString(input.project)) {
        return fail('VIDEO_REQUEST_PROJECT_INVALID', 'project')
    }
    if (!isNonEmptyString(input.title)) {
        return fail('VIDEO_REQUEST_TITLE_INVALID', 'title')
    }
    if (input.locale !== undefined && !isNonEmptyString(input.locale)) {
        return fail('VIDEO_REQUEST_LOCALE_INVALID', 'locale')
    }
    if (!Array.isArray(input.profiles) || input.profiles.length === 0) {
        return fail('VIDEO_REQUEST_PROFILES_INVALID', 'profiles')
    }
    const seenProfiles = new Set<string>()
    for (const profile of input.profiles) {
        if (!isKebabCase(profile)) {
            return fail('VIDEO_REQUEST_PROFILES_INVALID', typeof profile === 'string' ? profile : null)
        }
        if (seenProfiles.has(profile)) {
            return fail('VIDEO_REQUEST_PROFILE_DUPLICATE', profile)
        }
        seenProfiles.add(profile)
    }
    if (input.visualStyle !== undefined && !isPlainObject(input.visualStyle)) {
        return fail('VIDEO_REQUEST_VISUAL_STYLE_INVALID', 'visualStyle')
    }
    if (!Array.isArray(input.media) || input.media.length === 0) {
        return fail('VIDEO_REQUEST_MEDIA_INVALID', 'media')
    }
    const media: VideoRequestMedia[] = []
    const mediaIds = new Set<string>()
    const seenMediaIds = new Set<string>()
    for (const entry of input.media) {
        const read = readMedia(entry, seenMediaIds)
        if (!read.ok) {
            return fail(read.failureCode, read.subject)
        }
        media.push(read.media)
        mediaIds.add(read.media.id)
    }
    if (!Array.isArray(input.scenes) || input.scenes.length === 0) {
        return fail('VIDEO_REQUEST_SCENES_INVALID', 'scenes')
    }
    const scenes: VideoRequestScene[] = []
    const seenSceneIds = new Set<string>()
    for (const entry of input.scenes) {
        const read = readScene(entry, mediaIds, seenSceneIds)
        if (!read.ok) {
            return fail(read.failureCode, read.subject)
        }
        scenes.push(read.scene)
    }

    const request: VideoRequest = {
        schemaVersion: 1,
        id: input.id,
        project: input.project,
        title: input.title,
        ...(input.locale !== undefined ? { locale: input.locale } : {}),
        profiles: [...input.profiles] as string[],
        ...(input.visualStyle !== undefined ? { visualStyle: input.visualStyle as unknown as VisualStyle } : {}),
        media,
        scenes,
    }
    return { ok: true, request }
}