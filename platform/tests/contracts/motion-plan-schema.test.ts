/**
 * Paridade estrutural do MotionPlan v1: espelho draft-07 (Ajv) e validador puro
 * avaliam os mesmos documentos e coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validateMotionPlan } from '../../src/validate-motion-plan.js'
import { moduleRoot } from '../contract-harness.js'

const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'motion-plan.schema.json'), 'utf8')) as AnySchemaObject
const ajv = new AjvModule.default({ allErrors: true, strict: false })

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map((e) => `${e.instancePath || '#'} ${e.keyword}: ${e.message ?? ''}`.trim())
    return { valid, detail: failures.join(' | ') }
}

function validPlan(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        requestId: 'pedido-demo',
        effects: [
            { sceneId: 'abertura', region: { x: 0.1, y: 0.2, w: 0.8, h: 0.1 }, color: '#FFD700', thickness: 6, startMs: 500, endMs: 3000 },
        ],
    }
}

test('paridade: planos validos aceitos pelo schema e pelo validador', () => {
    const withFade = validPlan()
    ;(withFade.effects as Array<Record<string, unknown>>)[0] = { ...(withFade.effects as Array<Record<string, unknown>>)[0], fadeInMs: 150, fadeOutMs: 150 }
    for (const doc of [validPlan(), withFade]) {
        const s = checkSchema(doc)
        assert.ok(s.valid, `Schema rejeitou valido: ${s.detail}`)
        const v = validateMotionPlan(doc)
        assert.ok(v.ok, `Validador rejeitou valido: ${v.ok ? '' : v.failureCode}`)
    }
})

test('paridade: defeitos rejeitados pelo schema e pelo validador', () => {
    const mk = (patch: Record<string, unknown>) => {
        const p = validPlan()
        ;(p.effects as Array<Record<string, unknown>>)[0] = { ...(p.effects as Array<Record<string, unknown>>)[0], ...patch }
        return p
    }
    const cases: Array<{ name: string; document: unknown }> = [
        { name: 'nao objeto', document: 'x' },
        { name: 'schemaVersion 2', document: { ...validPlan(), schemaVersion: 2 } },
        { name: 'requestId invalido', document: { ...validPlan(), requestId: 'PedidoDemo' } },
        { name: 'effects vazio', document: { ...validPlan(), effects: [] } },
        { name: 'regiao negativa', document: mk({ region: { x: -0.1, y: 0.2, w: 0.8, h: 0.1 } }) },
        { name: 'regiao w zero', document: mk({ region: { x: 0.1, y: 0.2, w: 0, h: 0.1 } }) },
        { name: 'cor invalida', document: mk({ color: 'gold' }) },
        { name: 'espessura 0', document: mk({ thickness: 0 }) },
        { name: 'campo desconhecido', document: { ...validPlan(), autor: 'x' } },
    ]
    for (const c of cases) {
        const s = checkSchema(c.document)
        assert.strictEqual(s.valid, false, `Schema deveria rejeitar '${c.name}'`)
        const v = validateMotionPlan(c.document)
        assert.strictEqual(v.ok, false, `Validador deveria rejeitar '${c.name}'`)
    }
})