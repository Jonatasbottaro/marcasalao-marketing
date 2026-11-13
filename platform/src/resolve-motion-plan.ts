/**
 * Resolvedor puro do MotionPlan v1 contra a timeline canonica do
 * CreativeExecutionPackage.
 *
 * Resolve os tempos absolutos (sceneStartMs + intervalo relativo), valida a
 * referencia da cena, o intervalo dentro da cena e a compatibilidade com o
 * recorte local (cena sem zoom). Um efeito que exija acompanhar regiao em
 * movimento (cena com zoom) e reportado como incompativel.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import {
    MOTION_DEFAULT_FADE_MS,
    type MotionPlanFailureCode,
    type MotionPlanResolutionResult,
    type ResolvedMotionEffect,
} from './motion-plan-contract.js'
import { validateMotionPlan } from './validate-motion-plan.js'

function fail(failureCode: MotionPlanFailureCode, subject: string | null): MotionPlanResolutionResult {
    return { ok: false, failureCode, subject }
}

export function resolveMotionPlan(packageInput: unknown, planInput: unknown): MotionPlanResolutionResult {
    const validation = validateMotionPlan(planInput)
    if (!validation.ok) {
        return fail(validation.failureCode, validation.subject)
    }
    const plan = validation.plan
    const pkg = packageInput as CreativeExecutionPackage
    if (!pkg || !Array.isArray(pkg.timeline)) {
        return fail('MOTION_PLAN_INVALID', 'package')
    }
    const stepByScene = new Map(pkg.timeline.map((step) => [step.beatId, step]))

    const effects: ResolvedMotionEffect[] = []
    for (const effect of plan.effects) {
        const step = stepByScene.get(effect.sceneId)
        if (step === undefined) {
            return fail('MOTION_SCENE_UNKNOWN', effect.sceneId)
        }
        if (step.motionIntent !== 'none') {
            return fail('MOTION_SCENE_MOVING', effect.sceneId)
        }
        if (effect.endMs > step.durationMs) {
            return fail('MOTION_INTERVAL_OUT_OF_SCENE', effect.sceneId)
        }
        const windowMs = effect.endMs - effect.startMs
        const maxFade = Math.floor(windowMs / 2)
        const fadeIn = Math.min(effect.fadeInMs ?? MOTION_DEFAULT_FADE_MS, maxFade)
        const fadeOut = Math.min(effect.fadeOutMs ?? MOTION_DEFAULT_FADE_MS, maxFade)
        effects.push({
            ...effect,
            sceneStartMs: step.startMs,
            sceneDurationMs: step.durationMs,
            absoluteStartMs: step.startMs + effect.startMs,
            absoluteEndMs: step.startMs + effect.endMs,
            resolvedFadeInMs: fadeIn,
            resolvedFadeOutMs: fadeOut,
        })
    }
    return { ok: true, requestId: plan.requestId, effects }
}