/**
 * Validador puro estrutural do MotionPlan v1 (paridade com o schema draft-07).
 *
 * Valida requestId, um efeito por cena, regiao relativa ao quadro final (0..1),
 * cor hexadecimal, espessura e intervalo (startMs >= 0, endMs > startMs). A
 * compatibilidade com a timeline (cena existente, intervalo dentro da cena,
 * cena sem zoom) fica em resolve-motion-plan.ts.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    MOTION_COLOR_PATTERN,
    MOTION_EFFECT_FIELDS,
    MOTION_EFFECT_REQUIRED_FIELDS,
    MOTION_PLAN_SCHEMA_VERSION,
    MOTION_PLAN_TOP_LEVEL_FIELDS,
    MOTION_REGION_FIELDS,
    MOTION_THICKNESS_MAX,
    MOTION_THICKNESS_MIN,
    type MotionEffect,
    type MotionPlan,
    type MotionPlanFailureCode,
    type MotionPlanValidationResult,
    type MotionRegion,
} from './motion-plan-contract.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
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

function isUnitNumber(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
}

function fail(failureCode: MotionPlanFailureCode, subject: string | null): MotionPlanValidationResult {
    return { ok: false, failureCode, subject }
}

function readRegion(input: unknown): MotionRegion | null {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, MOTION_REGION_FIELDS) || !hasRequiredFields(input, MOTION_REGION_FIELDS)) {
        return null
    }
    const { x, y, w, h } = input
    if (!isUnitNumber(x) || !isUnitNumber(y) || !isUnitNumber(w) || !isUnitNumber(h)) return null
    if (w <= 0 || h <= 0) return null
    if (x + w > 1 || y + h > 1) return null
    return { x, y, w, h }
}

function readEffect(input: unknown, seenScenes: Set<string>): { ok: true; effect: MotionEffect } | { ok: false; failureCode: MotionPlanFailureCode; subject: string | null } {
    if (!isPlainObject(input) || !hasOnlyKnownFields(input, MOTION_EFFECT_FIELDS) || !hasRequiredFields(input, MOTION_EFFECT_REQUIRED_FIELDS)) {
        return { ok: false, failureCode: 'MOTION_PLAN_EFFECTS_INVALID', subject: null }
    }
    if (!isKebabCase(input.sceneId)) {
        return { ok: false, failureCode: 'MOTION_EFFECT_SCENE_ID_INVALID', subject: typeof input.sceneId === 'string' ? input.sceneId : null }
    }
    if (seenScenes.has(input.sceneId)) {
        return { ok: false, failureCode: 'MOTION_EFFECT_SCENE_DUPLICATE', subject: input.sceneId }
    }
    const region = readRegion(input.region)
    if (region === null) {
        return { ok: false, failureCode: 'MOTION_EFFECT_REGION_INVALID', subject: input.sceneId }
    }
    if (typeof input.color !== 'string' || !MOTION_COLOR_PATTERN.test(input.color)) {
        return { ok: false, failureCode: 'MOTION_EFFECT_COLOR_INVALID', subject: input.sceneId }
    }
    if (typeof input.thickness !== 'number' || !Number.isSafeInteger(input.thickness) || input.thickness < MOTION_THICKNESS_MIN || input.thickness > MOTION_THICKNESS_MAX) {
        return { ok: false, failureCode: 'MOTION_EFFECT_THICKNESS_INVALID', subject: input.sceneId }
    }
    if (typeof input.startMs !== 'number' || !Number.isSafeInteger(input.startMs) || input.startMs < 0
        || typeof input.endMs !== 'number' || !Number.isSafeInteger(input.endMs) || input.endMs <= input.startMs) {
        return { ok: false, failureCode: 'MOTION_EFFECT_INTERVAL_INVALID', subject: input.sceneId }
    }
    for (const fadeField of ['fadeInMs', 'fadeOutMs'] as const) {
        const value = input[fadeField]
        if (value !== undefined && (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0)) {
            return { ok: false, failureCode: 'MOTION_EFFECT_FADE_INVALID', subject: input.sceneId }
        }
    }
    seenScenes.add(input.sceneId)
    const effect: MotionEffect = {
        sceneId: input.sceneId,
        region,
        color: input.color,
        thickness: input.thickness,
        startMs: input.startMs,
        endMs: input.endMs,
        ...(input.fadeInMs !== undefined ? { fadeInMs: input.fadeInMs as number } : {}),
        ...(input.fadeOutMs !== undefined ? { fadeOutMs: input.fadeOutMs as number } : {}),
    }
    return { ok: true, effect }
}

export function validateMotionPlan(input: unknown): MotionPlanValidationResult {
    if (!isPlainObject(input)) {
        return fail('MOTION_PLAN_INVALID', null)
    }
    if (!hasOnlyKnownFields(input, MOTION_PLAN_TOP_LEVEL_FIELDS)) {
        const unknown = Object.keys(input).find((key) => !(MOTION_PLAN_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) ?? null
        return fail('MOTION_PLAN_UNKNOWN_FIELD', unknown)
    }
    if (input.schemaVersion !== MOTION_PLAN_SCHEMA_VERSION) {
        return fail('MOTION_PLAN_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion')
    }
    if (!isKebabCase(input.requestId)) {
        return fail('MOTION_PLAN_REQUEST_ID_INVALID', typeof input.requestId === 'string' ? input.requestId : null)
    }
    if (!Array.isArray(input.effects) || input.effects.length === 0) {
        return fail('MOTION_PLAN_EFFECTS_INVALID', 'effects')
    }
    const effects: MotionEffect[] = []
    const seenScenes = new Set<string>()
    for (const entry of input.effects) {
        const read = readEffect(entry, seenScenes)
        if (!read.ok) return fail(read.failureCode, read.subject)
        effects.push(read.effect)
    }
    const plan: MotionPlan = { schemaVersion: 1, requestId: input.requestId, effects }
    return { ok: true, plan }
}