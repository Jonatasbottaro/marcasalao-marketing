/**
 * Testes do validador estrutural e do resolvedor do MotionPlan v1.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { validateMotionPlan } from '../src/validate-motion-plan.js'
import { resolveMotionPlan } from '../src/resolve-motion-plan.js'
import type { MotionPlanFailureCode } from '../src/motion-plan-contract.js'

function validPlan(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        requestId: 'pedido-demo',
        effects: [
            { sceneId: 'abertura', region: { x: 0.1, y: 0.2, w: 0.8, h: 0.1 }, color: '#FFD700', thickness: 6, startMs: 500, endMs: 3000 },
        ],
    }
}

function pkg(): Record<string, unknown> {
    return {
        timeline: [
            { beatId: 'abertura', startMs: 0, durationMs: 4000, motionIntent: 'none' },
            { beatId: 'meio', startMs: 4000, durationMs: 6000, motionIntent: 'slow-zoom' },
        ],
    }
}

function code(input: unknown): MotionPlanFailureCode | null {
    const r = validateMotionPlan(input)
    return r.ok ? null : r.failureCode
}

test('aceita plano valido', () => {
    const r = validateMotionPlan(validPlan())
    assert.ok(r.ok, r.ok ? '' : r.failureCode)
})

test('rejeita nao objeto / schemaVersion / requestId', () => {
    assert.equal(code(null), 'MOTION_PLAN_INVALID')
    assert.equal(code({ ...validPlan(), schemaVersion: 2 }), 'MOTION_PLAN_SCHEMA_VERSION_UNSUPPORTED')
    assert.equal(code({ ...validPlan(), requestId: 'PedidoDemo' }), 'MOTION_PLAN_REQUEST_ID_INVALID')
})

test('rejeita efeitos vazios e cena duplicada', () => {
    assert.equal(code({ ...validPlan(), effects: [] }), 'MOTION_PLAN_EFFECTS_INVALID')
    const p = validPlan()
    const effects = p.effects as Array<Record<string, unknown>>
    effects.push({ ...effects[0] })
    assert.equal(code(p), 'MOTION_EFFECT_SCENE_DUPLICATE')
})

test('rejeita regiao invalida (fora de 0..1, w/h zero, soma > 1)', () => {
    const mk = (region: unknown) => {
        const p = validPlan()
        ;(p.effects as Array<Record<string, unknown>>)[0] = { ...(p.effects as Array<Record<string, unknown>>)[0], region }
        return code(p)
    }
    assert.equal(mk({ x: -0.1, y: 0.2, w: 0.8, h: 0.1 }), 'MOTION_EFFECT_REGION_INVALID')
    assert.equal(mk({ x: 0.1, y: 0.2, w: 0, h: 0.1 }), 'MOTION_EFFECT_REGION_INVALID')
    assert.equal(mk({ x: 0.5, y: 0.2, w: 0.8, h: 0.1 }), 'MOTION_EFFECT_REGION_INVALID')
})

test('rejeita cor / espessura / intervalo invalidos', () => {
    const mk = (patch: Record<string, unknown>) => {
        const p = validPlan()
        ;(p.effects as Array<Record<string, unknown>>)[0] = { ...(p.effects as Array<Record<string, unknown>>)[0], ...patch }
        return code(p)
    }
    assert.equal(mk({ color: 'gold' }), 'MOTION_EFFECT_COLOR_INVALID')
    assert.equal(mk({ thickness: 0 }), 'MOTION_EFFECT_THICKNESS_INVALID')
    assert.equal(mk({ thickness: 41 }), 'MOTION_EFFECT_THICKNESS_INVALID')
    assert.equal(mk({ startMs: 3000, endMs: 3000 }), 'MOTION_EFFECT_INTERVAL_INVALID')
    assert.equal(mk({ startMs: -1 }), 'MOTION_EFFECT_INTERVAL_INVALID')
})

test('resolvedor resolve tempos absolutos e fades', () => {
    const r = resolveMotionPlan(pkg(), validPlan())
    assert.ok(r.ok, r.ok ? '' : r.failureCode)
    if (r.ok) {
        const e = r.effects[0]!
        assert.equal(e.absoluteStartMs, 500)
        assert.equal(e.absoluteEndMs, 3000)
        assert.equal(e.sceneStartMs, 0)
        assert.equal(e.resolvedFadeInMs, 200)
        assert.equal(e.resolvedFadeOutMs, 200)
    }
})

test('resolvedor rejeita cena desconhecida / intervalo fora / cena com zoom', () => {
    const unknown = validPlan()
    ;(unknown.effects as Array<Record<string, unknown>>)[0] = { ...(unknown.effects as Array<Record<string, unknown>>)[0], sceneId: 'inexistente' }
    const r1 = resolveMotionPlan(pkg(), unknown)
    assert.equal(r1.ok ? null : r1.failureCode, 'MOTION_SCENE_UNKNOWN')

    const out = validPlan()
    ;(out.effects as Array<Record<string, unknown>>)[0] = { ...(out.effects as Array<Record<string, unknown>>)[0], endMs: 5000 }
    const r2 = resolveMotionPlan(pkg(), out)
    assert.equal(r2.ok ? null : r2.failureCode, 'MOTION_INTERVAL_OUT_OF_SCENE')

    const moving = validPlan()
    ;(moving.effects as Array<Record<string, unknown>>)[0] = { ...(moving.effects as Array<Record<string, unknown>>)[0], sceneId: 'meio', startMs: 0, endMs: 3000 }
    const r3 = resolveMotionPlan(pkg(), moving)
    assert.equal(r3.ok ? null : r3.failureCode, 'MOTION_SCENE_MOVING')
})