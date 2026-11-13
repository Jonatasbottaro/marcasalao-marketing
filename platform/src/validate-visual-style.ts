/**
 * Validador puro do VisualStyle v1.
 *
 * Garante:
 * - Estrutura exata do estilo (schemaVersion === 1, id kebab-case, title objeto);
 * - Ausencia de campos desconhecidos no objeto raiz e na secao title;
 * - Cores hexadecimais validas (#RRGGBB);
 * - Fonte e margens inteiras dentro dos limites do quadro de referencia (1080x1920).
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    HEX_COLOR_PATTERN,
    VISUAL_STYLE_LIMITS,
    VISUAL_STYLE_SCHEMA_VERSION,
    VISUAL_STYLE_TITLE_FIELDS,
    VISUAL_STYLE_TOP_LEVEL_FIELDS,
    type VisualStyle,
    type VisualStyleFailureCode,
    type VisualStyleTitle,
    type VisualStyleValidationResult,
} from './visual-style-contract.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    const keys = Object.keys(value)
    return keys.length === allowed.length && allowed.every((field) => keys.includes(field))
}

function fail(failureCode: VisualStyleFailureCode, subject: string | null): VisualStyleValidationResult {
    return { ok: false, failureCode, subject }
}

export function validateVisualStyle(input: unknown): VisualStyleValidationResult {
    if (!isPlainObject(input)) {
        return fail('STYLE_INVALID', null)
    }

    if (!hasExactFields(input, VISUAL_STYLE_TOP_LEVEL_FIELDS)) {
        return fail('STYLE_INVALID', null)
    }

    if (input.schemaVersion !== VISUAL_STYLE_SCHEMA_VERSION) {
        return fail('STYLE_INVALID', 'schemaVersion')
    }

    if (typeof input.id !== 'string' || !KEBAB_CASE_PATTERN.test(input.id)) {
        return fail('STYLE_ID_INVALID', typeof input.id === 'string' ? input.id : null)
    }

    if (!isPlainObject(input.title) || !hasExactFields(input.title, VISUAL_STYLE_TITLE_FIELDS)) {
        return fail('STYLE_TITLE_INVALID', null)
    }

    const { textColor, outlineColor, fontSize, marginTop, marginHorizontal } = input.title

    if (typeof textColor !== 'string' || !HEX_COLOR_PATTERN.test(textColor)) {
        return fail('STYLE_COLOR_INVALID', 'title.textColor')
    }

    if (typeof outlineColor !== 'string' || !HEX_COLOR_PATTERN.test(outlineColor)) {
        return fail('STYLE_COLOR_INVALID', 'title.outlineColor')
    }

    if (
        typeof fontSize !== 'number'
        || !Number.isSafeInteger(fontSize)
        || fontSize < VISUAL_STYLE_LIMITS.fontSize.min
        || fontSize > VISUAL_STYLE_LIMITS.fontSize.max
    ) {
        return fail('STYLE_FONT_SIZE_INVALID', 'title.fontSize')
    }

    if (
        typeof marginTop !== 'number'
        || !Number.isSafeInteger(marginTop)
        || marginTop < VISUAL_STYLE_LIMITS.marginTop.min
        || marginTop > VISUAL_STYLE_LIMITS.marginTop.max
    ) {
        return fail('STYLE_MARGIN_INVALID', 'title.marginTop')
    }

    if (
        typeof marginHorizontal !== 'number'
        || !Number.isSafeInteger(marginHorizontal)
        || marginHorizontal < VISUAL_STYLE_LIMITS.marginHorizontal.min
        || marginHorizontal > VISUAL_STYLE_LIMITS.marginHorizontal.max
    ) {
        return fail('STYLE_MARGIN_INVALID', 'title.marginHorizontal')
    }

    const canonicalTitle: VisualStyleTitle = {
        textColor: textColor.toUpperCase(),
        outlineColor: outlineColor.toUpperCase(),
        fontSize,
        marginTop,
        marginHorizontal,
    }

    const canonicalStyle: VisualStyle = {
        schemaVersion: 1,
        id: input.id,
        title: canonicalTitle,
    }

    return {
        ok: true,
        style: canonicalStyle,
    }
}
