/**
 * Serializacao canonica do TextOverlayPlan v1.
 *
 * JSON com indentacao estavel de dois espacos, ordem de propriedades definida
 * explicitamente pelo contrato (nunca pela ordem do objeto original), arrays
 * na ordem semantica, LF, uma newline final, UTF-8 sem BOM. O mesmo plano
 * produz bytes identicos; parse seguido de serializacao produz os mesmos
 * bytes. Nenhuma dependencia externa de canonical JSON.
 *
 * Funcao pura: sem I/O, sem relogio, sem aleatoriedade, sem mutacao.
 */

import type { TextOverlayBinding, TextOverlayPlan } from './text-overlay-plan-contract.js'

function canonicalOverlay(binding: TextOverlayBinding): Record<string, unknown> {
    return {
        beatId: binding.beatId,
        text: binding.text,
    }
}

/**
 * Serializa o plano de sobreposicao textual na forma canonica.
 */
export function serializeTextOverlayPlan(plan: TextOverlayPlan): string {
    const canonical = {
        schemaVersion: plan.schemaVersion,
        caseId: plan.caseId,
        overlays: plan.overlays.map(canonicalOverlay),
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}
