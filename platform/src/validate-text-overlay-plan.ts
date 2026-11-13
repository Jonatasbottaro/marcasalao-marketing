/**
 * Validador puro do TextOverlayPlan v1 contra o pacote canonico e o caso de pipeline.
 *
 * Garante:
 * - Pacote canonico valido (CreativeExecutionPackage v1);
 * - Estrutura exata do plano (schemaVersion === 1, caseId kebab-case, overlays array);
 * - Ausencia de campos desconhecidos no plano e em cada item de overlay;
 * - Correspondencia do caseId quando esperado;
 * - Itens de overlay validos (beatId kebab-case, text nao vazio);
 * - Unicidade de beatId (no maximo um titulo por beat);
 * - Existencia do beatId na timeline do pacote canonico;
 * - Resolucao dos intervalos startMs, endMs e durationMs a partir da timeline.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import {
    TEXT_OVERLAY_BINDING_FIELDS,
    TEXT_OVERLAY_PLAN_SCHEMA_VERSION,
    TEXT_OVERLAY_PLAN_TOP_LEVEL_FIELDS,
    type ResolvedTextOverlay,
    type TextOverlayBinding,
    type TextOverlayPlan,
    type TextOverlayPlanFailureCode,
    type TextOverlayPlanValidationResult,
} from './text-overlay-plan-contract.js'
import { validateCreativeExecutionPackage } from './validate-creative-execution-package.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    const keys = Object.keys(value)
    return keys.length === allowed.length && allowed.every((field) => keys.includes(field))
}

function fail(failureCode: TextOverlayPlanFailureCode, subject: string | null): TextOverlayPlanValidationResult {
    return { ok: false, failureCode, subject }
}

export function validateTextOverlayPlan(
    packageInput: unknown,
    expectedCaseId: string | null | undefined,
    planInput: unknown,
): TextOverlayPlanValidationResult {
    const packageReport = validateCreativeExecutionPackage(packageInput)
    if (!packageReport.valid) {
        return fail('PACKAGE_INVALID', null)
    }
    const pkg = packageInput as CreativeExecutionPackage

    if (
        !isPlainObject(planInput)
        || !hasExactFields(planInput, TEXT_OVERLAY_PLAN_TOP_LEVEL_FIELDS)
        || planInput.schemaVersion !== TEXT_OVERLAY_PLAN_SCHEMA_VERSION
        || typeof planInput.caseId !== 'string'
        || !KEBAB_CASE_PATTERN.test(planInput.caseId)
        || !Array.isArray(planInput.overlays)
    ) {
        return fail('OVERLAY_PLAN_INVALID', null)
    }

    if (expectedCaseId !== null && expectedCaseId !== undefined && planInput.caseId !== expectedCaseId) {
        return fail('CASE_ID_MISMATCH', planInput.caseId)
    }

    const timelineMap = new Map<string, { startMs: number; endMs: number; durationMs: number }>()
    for (const step of pkg.timeline) {
        timelineMap.set(step.beatId, {
            startMs: step.startMs,
            endMs: step.endMs,
            durationMs: step.durationMs,
        })
    }

    const seenBeatIds = new Set<string>()
    const canonicalOverlays: TextOverlayBinding[] = []
    const resolvedOverlays: ResolvedTextOverlay[] = []

    for (const item of planInput.overlays) {
        if (
            !isPlainObject(item)
            || !hasExactFields(item, TEXT_OVERLAY_BINDING_FIELDS)
            || typeof item.beatId !== 'string'
            || !KEBAB_CASE_PATTERN.test(item.beatId)
            || typeof item.text !== 'string'
        ) {
            return fail('OVERLAY_PLAN_INVALID', null)
        }

        if (item.text.trim().length === 0) {
            return fail('OVERLAY_TEXT_EMPTY', item.beatId)
        }

        if (seenBeatIds.has(item.beatId)) {
            return fail('OVERLAY_BEAT_DUPLICATE', item.beatId)
        }
        seenBeatIds.add(item.beatId)

        const timelineStep = timelineMap.get(item.beatId)
        if (!timelineStep) {
            return fail('UNKNOWN_BEAT_REFERENCE', item.beatId)
        }

        canonicalOverlays.push({
            beatId: item.beatId,
            text: item.text,
        })

        resolvedOverlays.push({
            beatId: item.beatId,
            text: item.text,
            startMs: timelineStep.startMs,
            endMs: timelineStep.endMs,
            durationMs: timelineStep.durationMs,
        })
    }

    const canonicalPlan: TextOverlayPlan = {
        schemaVersion: 1,
        caseId: planInput.caseId,
        overlays: canonicalOverlays,
    }

    return {
        ok: true,
        plan: canonicalPlan,
        resolvedOverlays,
    }
}
