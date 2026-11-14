/**
 * Paridade estrutural do PlanningSuggestion v1: espelho draft-07 (Ajv) e
 * validador puro avaliam os mesmos documentos e coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { validatePlanningSuggestion } from '../../src/validate-planning-suggestion.js'
import { moduleRoot } from '../contract-harness.js'

const schema = JSON.parse(
    readFileSync(path.join(moduleRoot, 'schemas', 'planning-suggestion.schema.json'), 'utf8'),
) as AnySchemaObject
const ajv = new AjvModule.default({ allErrors: true, strict: false })

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map((e) => `${e.instancePath || '#'} ${e.keyword}: ${e.message ?? ''}`.trim())
    return { valid, detail: failures.join(' | ') }
}

function validBriefing(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        stage: 'briefing',
        product: 'Produto Demo',
        objective: 'Objetivo Demo',
        audience: 'Publico Demo',
        coreMessage: 'Mensagem Central',
        supportEvidence: '',
        cta: 'Saiba mais',
        tone: 'Claro',
        recommendedProfiles: ['instagram-reels-video', 'instagram-feed-image-square'],
        gaps: ['Falta evidencia'],
        questions: [
            { id: 'q-1', dimension: 'supportEvidence', question: 'Qual evidencia anexar?' },
        ],
        claims: [
            { id: 'c-1', statement: 'Fluxo demonstrado na tela', status: 'pending_validation', requiresConfirmation: true },
        ],
    }
}

function validCreative(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        stage: 'creative',
        hookOptions: [{ id: 'h-1', text: 'Gancho inicial direto' }],
        selectedHookId: 'h-1',
        scriptSummary: 'Abertura, demonstracao e fechamento.',
        videoScenes: [
            {
                id: 'cena-1',
                objective: 'Abrir o tema',
                narrativeFunction: 'hook',
                durationMs: 4000,
                titleOverlay: 'Titulo 1',
                caption: 'Legenda da cena 1',
                narration: 'Texto falado da cena 1',
                requiredMediaDescriptor: 'Imagem de abertura',
                motionIntent: 'none',
            },
        ],
        carouselCards: [
            { id: 'capa', role: 'cover', title: 'Capa' },
            { id: 'fechamento', role: 'cta', title: 'Fechamento', body: 'CTA final' },
        ],
        channelCopies: [
            {
                profileId: 'instagram-reels-video',
                title: 'Post IG',
                postText: 'Texto da legenda social',
                cta: 'Link na bio',
                destinationUrl: 'https://marcasalao.com.br',
                hashtags: '#demo',
            },
        ],
        motionSuggestions: [
            { sceneId: 'cena-1', targetElement: 'Painel principal', suggestedColor: '#FFD700', suggestedStartMs: 400, suggestedEndMs: 2500 },
        ],
    }
}

test('paridade: documentos validos de briefing e creative passam no schema e no validador', () => {
    for (const doc of [validBriefing(), validCreative()]) {
        const s = checkSchema(doc)
        assert.ok(s.valid, `Schema rejeitou valido: ${s.detail}`)
        const v = validatePlanningSuggestion(doc)
        assert.ok(v.ok, v.ok ? '' : v.message)
    }
})

test('paridade: defeitos estruturais rejeitados pelo schema e pelo validador', () => {
    const cases: Array<{ name: string; document: unknown }> = [
        { name: 'nulo', document: null },
        { name: 'schemaVersion 2', document: { ...validBriefing(), schemaVersion: 2 } },
        { name: 'stage invalido', document: { ...validBriefing(), stage: 'apply' } },
        { name: 'campo desconhecido briefing', document: { ...validBriefing(), extra: 1 } },
        { name: 'perfis recomendados vazios', document: { ...validBriefing(), recommendedProfiles: [] } },
        { name: 'status claim invalido', document: { ...validBriefing(), claims: [{ id: 'c-1', statement: 'x', status: 'inventado', requiresConfirmation: true }] } },
        { name: 'duracao cena baixa', document: { ...validCreative(), videoScenes: [{ ...(validCreative().videoScenes as Array<Record<string, unknown>>)[0], durationMs: 200 }] } },
        { name: 'carousel com apenas 1 card', document: { ...validCreative(), carouselCards: [{ id: 'capa', role: 'cover', title: 'Capa' }] } },
        { name: 'cor motion invalida', document: { ...validCreative(), motionSuggestions: [{ sceneId: 'cena-1', targetElement: 'x', suggestedColor: 'gold' }] } },
        { name: 'campo desconhecido creative', document: { ...validCreative(), extra: 'nope' } },
    ]
    for (const c of cases) {
        const s = checkSchema(c.document)
        assert.strictEqual(s.valid, false, `Schema deveria rejeitar '${c.name}'`)
        const v = validatePlanningSuggestion(c.document)
        assert.strictEqual(v.ok, false, `Validador deveria rejeitar '${c.name}'`)
    }
})
