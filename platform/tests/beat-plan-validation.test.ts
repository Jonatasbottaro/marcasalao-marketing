/**
 * Testes do validador BeatPlan v1: `validateBeatPlan(beatPlan, composition, project)`
 * sobre documentos sinteticos, a delegacao a `validateProjectManifest` e a
 * `validateComposition`, os codigos estaveis, a ordem de emissao e a pureza do
 * nucleo (sem rede, sem filesystem, sem marca, sem fornecedor).
 *
 * A paridade com o espelho draft-07 aparece aqui e em
 * `tests/contracts/beat-plan-schema.test.ts`, que executa o motor AJV. Os
 * exemplos oficiais entram no bloco final deste arquivo, junto com a CLI
 * (`tests/beat-plan-cli-process.test.ts`), porque dependem dos arquivos de
 * `examples/beat-plans/`.
 */
import assert from 'node:assert/strict'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

import {
    BEAT_MOTION_INTENTS,
    BEAT_NARRATIVE_FUNCTIONS,
    BEAT_PLAN_MAX_NARRATION_LENGTH,
    BEAT_PLAN_MAX_ON_SCREEN_TEXT_LENGTH,
    BEAT_PLAN_MAX_TAGS,
    BEAT_PLAN_METADATA_STATUSES,
    BEAT_TRANSITIONS,
    BEAT_VALIDATION_STATUSES,
} from '../src/beat-plan-contract.js'
import { validateBeatPlan } from '../src/validate-beat-plan.js'
import type { BeatPlanValidationReport, ValidationIssue } from '../src/validation-report.js'

/**
 * Os testes sempre executam sobre JavaScript compilado (dist/tests). O root do
 * modulo e localizado subindo ate o package.json, como nas suites anteriores.
 */
const testDir = path.dirname(fileURLToPath(import.meta.url))

function findModuleRoot(startDir: string): string {
    let current = path.resolve(startDir)
    for (;;) {
        if (existsSync(path.join(current, 'package.json'))) return current
        const parent = path.dirname(current)
        if (parent === current) {
            throw new Error(`package.json do modulo nao encontrado a partir de ${startDir}`)
        }
        current = parent
    }
}

const moduleRoot = findModuleRoot(testDir)
const coreScanDirectories = [
    path.join(moduleRoot, 'src'),
    path.join(moduleRoot, 'schemas'),
]

function codesOf(report: BeatPlanValidationReport): string[] {
    return report.errors.map((item: ValidationIssue) => item.code)
}

function warningCodesOf(report: BeatPlanValidationReport): string[] {
    return report.warnings.map((item: ValidationIssue) => item.code)
}

/** Projeto neutro de teste; o nucleo nao conhece nenhum projeto especifico. */
function projectWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'projeto-teste',
        name: 'Projeto Teste',
        locale: 'pt-BR',
        timezone: 'America/Sao_Paulo',
        brandTheme: 'tema-teste',
        assetRoot: 'projects/projeto-teste/assets',
        contentPolicies: {
            requireApprovedBriefing: true,
            requireApprovedScript: true,
            prohibitPersonalData: true,
            requireFunctionalEvidence: true,
        },
        outputProfiles: ['vertical-social'],
        ...overrides,
    }
}

/** Composition de teste com duas cenas e duracao total de 5000 ms. */
function compositionWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        id: 'comp-teste',
        title: 'Composicao Teste',
        locale: 'pt-BR',
        format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
        scenes: [
            { id: 'opening', type: 'text', durationMs: 3000, content: { text: 'Texto de teste.' } },
            { id: 'closing', type: 'cta', durationMs: 2000, content: { text: 'Chamada de teste.' } },
        ],
        renderer: { adapter: 'undecided' },
        ...overrides,
    }
}

/** Beat de teste que ocupa exatamente a primeira cena (0 a 3000 ms). */
function beatWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        id: 'abertura',
        order: 1,
        sceneIds: ['opening'],
        narrativeFunction: 'hook',
        startMs: 0,
        durationMs: 3000,
        narration: { text: 'Narracao tecnica de teste.' },
        onScreenText: 'Texto de teste.',
        visualIntent: 'Intencao visual tecnica de teste.',
        motionIntent: 'none',
        transitionIn: 'none',
        transitionOut: 'cut',
        editorialEvidence: ['technical-example'],
        validationStatus: 'draft',
        ...overrides,
    }
}

/** Beat de teste que ocupa exatamente a segunda cena (3000 a 5000 ms). */
function secondBeatWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return beatWith({
        id: 'encerramento',
        order: 2,
        sceneIds: ['closing'],
        narrativeFunction: 'cta',
        startMs: 3000,
        durationMs: 2000,
        ...overrides,
    })
}

function beatPlanWith(overrides: Record<string, unknown>): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        compositionId: 'comp-teste',
        id: 'plano-teste',
        locale: 'pt-BR',
        beats: [beatWith({}), secondBeatWith({})],
        ...overrides,
    }
}

/** Plano com apenas o primeiro beat alterado; timeline permanece valida. */
function planWithFirstBeat(overrides: Record<string, unknown>): Record<string, unknown> {
    return beatPlanWith({ beats: [beatWith(overrides), secondBeatWith({})] })
}

/** Plano com apenas o segundo beat alterado; timeline permanece valida. */
function planWithSecondBeat(overrides: Record<string, unknown>): Record<string, unknown> {
    return beatPlanWith({ beats: [beatWith({}), secondBeatWith(overrides)] })
}

const baseProject = projectWith({})
const baseComposition = compositionWith({})

function validate(input: unknown, composition: unknown = baseComposition, project: unknown = baseProject) {
    return validateBeatPlan(input, composition, project)
}

function words(count: number): string {
    return Array.from({ length: count }, (_unused, index) => `p${index + 1}`).join(' ')
}

/* ========================================================================== */
/* Requisitos 4 e 5: entradas invalidas                                        */
/* ========================================================================== */

test('ProjectManifest invalido produz BEAT_PLAN_PROJECT_MANIFEST_INVALID', () => {
    const report = validate(beatPlanWith({}), baseComposition, projectWith({ id: 'Invalid_Id' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_PROJECT_MANIFEST_INVALID'])
    assert.equal(report.errors[0]?.path, 'project')
    assert.equal(report.compositionDurationMs, null)
    assert.equal(report.compositionSceneCount, 0)
})

test('Composition invalida produz BEAT_PLAN_COMPOSITION_INVALID', () => {
    const report = validate(beatPlanWith({}), compositionWith({ schemaVersion: 9 }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_COMPOSITION_INVALID'])
    assert.equal(report.errors[0]?.path, 'composition')
    assert.equal(report.compositionDurationMs, null)
})

test('com Composition invalida a timeline nao e comparada com duracao nao confiavel', () => {
    const report = validate(beatPlanWith({}), compositionWith({ scenes: 'nenhuma' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_COMPOSITION_INVALID'])
    assert.equal(report.compositionDurationMs, null)
    assert.equal(report.compositionSceneCount, 0)
    assert.equal(report.referencedSceneCount, 0)
    assert.deepEqual(warningCodesOf(report), [])
})

/* ========================================================================== */
/* Requisitos 6 a 11: vinculos e estrutura de topo                             */
/* ========================================================================== */

test('projectId divergente do projeto produz BEAT_PLAN_PROJECT_ID_MISMATCH', () => {
    const report = validate(beatPlanWith({ projectId: 'outro-projeto' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_PROJECT_ID_MISMATCH'])
})

test('compositionId divergente da composicao produz BEAT_PLAN_COMPOSITION_ID_MISMATCH', () => {
    const report = validate(beatPlanWith({ compositionId: 'outra-composicao' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_COMPOSITION_ID_MISMATCH'])
})

test('locale divergente produz BEAT_PLAN_LOCALE_MISMATCH uma unica vez', () => {
    const report = validate(beatPlanWith({ locale: 'en-US' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_LOCALE_MISMATCH'])
    assert.equal(report.errors[0]?.path, 'locale')
})

test('schemaVersion diferente de 1 e rejeitado', () => {
    assert.deepEqual(codesOf(validate(beatPlanWith({ schemaVersion: 2 }))), ['BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ schemaVersion: '1' }))), ['BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED'])
})

test('campo desconhecido no topo produz BEAT_PLAN_UNKNOWN_FIELD', () => {
    const report = validate(beatPlanWith({ audioPlan: {} }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_UNKNOWN_FIELD'])
    assert.equal(report.errors[0]?.path, 'audioPlan')
})

test('entrada que nao e objeto produz BEAT_PLAN_MANIFEST_INVALID', () => {
    const report = validate(['nao', 'sou', 'objeto'])
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_MANIFEST_INVALID'])
    assert.equal(report.beatPlanId, null)
    assert.equal(report.beatCount, 0)
    assert.equal(report.totalDurationMs, 0)
})

test('id ausente e id invalido', () => {
    const missing = beatPlanWith({})
    delete missing.id
    assert.deepEqual(codesOf(validate(missing)), ['BEAT_PLAN_ID_REQUIRED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ id: 'Plano Teste' }))), ['BEAT_PLAN_ID_INVALID'])
})

test('projectId e compositionId obrigatorios e em kebab-case', () => {
    const missingProjectId = beatPlanWith({})
    delete missingProjectId.projectId
    assert.deepEqual(codesOf(validate(missingProjectId)), ['BEAT_PLAN_PROJECT_ID_REQUIRED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ projectId: 'Projeto_Teste' }))), ['BEAT_PLAN_PROJECT_ID_INVALID'])

    const missingCompositionId = beatPlanWith({})
    delete missingCompositionId.compositionId
    assert.deepEqual(codesOf(validate(missingCompositionId)), ['BEAT_PLAN_COMPOSITION_ID_REQUIRED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ compositionId: 'Comp Teste' }))), ['BEAT_PLAN_COMPOSITION_ID_INVALID'])
})

test('locale obrigatorio', () => {
    const missing = beatPlanWith({})
    delete missing.locale
    assert.deepEqual(codesOf(validate(missing)), ['BEAT_PLAN_LOCALE_REQUIRED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ locale: '  ' }))), ['BEAT_PLAN_LOCALE_REQUIRED'])
})

/* ========================================================================== */
/* Requisitos 14 a 16: array de beats                                          */
/* ========================================================================== */

test('beats ausentes e beats vazios produzem BEAT_PLAN_BEATS_REQUIRED', () => {
    const missing = beatPlanWith({})
    delete missing.beats
    assert.deepEqual(codesOf(validate(missing)), ['BEAT_PLAN_BEATS_REQUIRED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ beats: [] }))), ['BEAT_PLAN_BEATS_REQUIRED'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ beats: 'nenhum' }))), ['BEAT_PLAN_BEATS_REQUIRED'])
})

test('beat que nao e objeto produz BEAT_PLAN_BEAT_INVALID', () => {
    const report = validate(beatPlanWith({ beats: ['texto'] }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_BEAT_INVALID'])
    assert.equal(report.beatCount, 0)
})

test('campo desconhecido no beat produz BEAT_PLAN_BEAT_INVALID', () => {
    const report = validate(planWithFirstBeat({ provider: 'algum' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_BEAT_INVALID'])
    assert.equal(report.errors[0]?.path, 'beats[0].provider')
})

/* ========================================================================== */
/* Requisitos 17 a 24: id e order                                              */
/* ========================================================================== */

test('id de beat ausente, invalido e duplicado', () => {
    const missing = beatWith({})
    delete missing.id
    assert.deepEqual(
        codesOf(validate(beatPlanWith({ beats: [missing, secondBeatWith({})] }))),
        ['BEAT_PLAN_BEAT_ID_REQUIRED'],
    )
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ id: 'Abertura' }))), ['BEAT_PLAN_BEAT_ID_INVALID'])
    assert.deepEqual(
        codesOf(validate(beatPlanWith({ beats: [beatWith({}), secondBeatWith({ id: 'abertura' })] }))),
        ['BEAT_PLAN_BEAT_ID_DUPLICATE'],
    )
})

test('order zero, negativo e nao inteiro produzem BEAT_PLAN_ORDER_INVALID', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ order: 0 }))), ['BEAT_PLAN_ORDER_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ order: -1 }))), ['BEAT_PLAN_ORDER_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ order: 1.5 }))), ['BEAT_PLAN_ORDER_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ order: '1' }))), ['BEAT_PLAN_ORDER_INVALID'])
})

test('order duplicado produz BEAT_PLAN_ORDER_DUPLICATE', () => {
    const report = validate(beatPlanWith({
        beats: [beatWith({}), secondBeatWith({ order: 1 })],
    }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_ORDER_DUPLICATE'])
    assert.equal(report.errors[0]?.path, 'beats[1].order')
})

test('sequencia com lacuna produz BEAT_PLAN_ORDER_SEQUENCE_INVALID', () => {
    const report = validate(beatPlanWith({
        beats: [beatWith({}), secondBeatWith({ order: 3 })],
    }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_ORDER_SEQUENCE_INVALID'])
    assert.equal(report.errors[0]?.path, 'beats[1].order')
})

test('ordem do array incompativel com order produz BEAT_PLAN_ARRAY_ORDER_MISMATCH', () => {
    const report = validate(beatPlanWith({
        beats: [
            beatWith({ id: 'segundo', order: 2, sceneIds: ['closing'], startMs: 3000, durationMs: 2000 }),
            secondBeatWith({ id: 'primeiro', order: 1, sceneIds: ['opening'], startMs: 0, durationMs: 3000 }),
        ],
    }))
    assert.ok(codesOf(report).includes('BEAT_PLAN_ARRAY_ORDER_MISMATCH'))
    assert.ok(!codesOf(report).includes('BEAT_PLAN_ORDER_SEQUENCE_INVALID'))
    assert.equal(
        report.errors.find((item) => item.code === 'BEAT_PLAN_ARRAY_ORDER_MISMATCH')?.path,
        'beats[1].order',
    )
})

/* ========================================================================== */
/* Requisitos 25 a 29: sceneIds                                                */
/* ========================================================================== */

test('sceneIds ausentes e vazios produzem BEAT_PLAN_SCENE_IDS_REQUIRED', () => {
    const missing = beatWith({})
    delete missing.sceneIds
    assert.deepEqual(
        codesOf(validate(beatPlanWith({ beats: [missing, secondBeatWith({})] }))),
        ['BEAT_PLAN_SCENE_IDS_REQUIRED'],
    )
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ sceneIds: [] }))), ['BEAT_PLAN_SCENE_IDS_REQUIRED'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ sceneIds: 'opening' }))), ['BEAT_PLAN_SCENE_IDS_REQUIRED'])
})

test('sceneId invalido e duplicado dentro do beat', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ sceneIds: ['Opening'] }))), ['BEAT_PLAN_SCENE_ID_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ sceneIds: [1] }))), ['BEAT_PLAN_SCENE_ID_INVALID'])
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ sceneIds: ['opening', 'opening'] }))),
        ['BEAT_PLAN_SCENE_ID_DUPLICATE'],
    )
})

test('sceneId inexistente na Composition produz BEAT_PLAN_SCENE_NOT_FOUND', () => {
    const report = validate(planWithFirstBeat({ sceneIds: ['nao-existe'] }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_SCENE_NOT_FOUND'])
    assert.equal(report.errors[0]?.path, 'beats[0].sceneIds[0]')
    assert.equal(report.referencedSceneCount, 1)
})

test('um beat pode referenciar mais de uma cena e uma cena pode servir a varios beats', () => {
    const report = validate(beatPlanWith({
        beats: [
            beatWith({ sceneIds: ['opening', 'closing'], durationMs: 3000 }),
            secondBeatWith({ sceneIds: ['closing'] }),
        ],
    }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.referencedSceneCount, 2)
    assert.deepEqual(report.warnings, [])
})

/* ========================================================================== */
/* Requisitos 30 a 36: campos enum e tempos individuais                        */
/* ========================================================================== */

test('narrativeFunction fora da lista e rejeitada', () => {
    const report = validate(planWithFirstBeat({ narrativeFunction: 'venda' }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_NARRATIVE_FUNCTION_INVALID'])
    for (const fn of BEAT_NARRATIVE_FUNCTIONS) {
        assert.equal(validate(planWithFirstBeat({ narrativeFunction: fn })).valid, true, `funcao ${fn}`)
    }
})

test('startMs negativo e nao inteiro produzem BEAT_PLAN_START_INVALID', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ startMs: -1 }))), ['BEAT_PLAN_START_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ startMs: 1.5 }))), ['BEAT_PLAN_START_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ startMs: '0' }))), ['BEAT_PLAN_START_INVALID'])
})

test('durationMs zero, negativa e nao inteira produzem BEAT_PLAN_DURATION_INVALID', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ durationMs: 0 }))), ['BEAT_PLAN_DURATION_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ durationMs: -100 }))), ['BEAT_PLAN_DURATION_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ durationMs: 1500.5 }))), ['BEAT_PLAN_DURATION_INVALID'])
})

test('duracao individual insegura e rejeitada como invalida', () => {
    const report = validate(planWithFirstBeat({ durationMs: Number.MAX_SAFE_INTEGER * 2 }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_DURATION_INVALID'])
    const startReport = validate(planWithFirstBeat({ startMs: Number.MAX_SAFE_INTEGER * 2 }))
    assert.deepEqual(codesOf(startReport), ['BEAT_PLAN_START_INVALID'])
})

/* ========================================================================== */
/* Requisitos 37 a 42: timeline e overflow                                     */
/* ========================================================================== */

test('soma temporal acima de MAX_SAFE_INTEGER produz BEAT_PLAN_DURATION_OVERFLOW', () => {
    const report = validate(beatPlanWith({
        beats: [
            beatWith({ durationMs: Number.MAX_SAFE_INTEGER }),
            secondBeatWith({ startMs: Number.MAX_SAFE_INTEGER, durationMs: 1 }),
        ],
    }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_DURATION_OVERFLOW'])
    assert.equal(report.valid, false)
    assert.equal(report.totalDurationMs, null)
})

test('primeiro beat fora do zero produz BEAT_PLAN_TIMELINE_START_INVALID', () => {
    const report = validate(beatPlanWith({
        beats: [beatWith({ startMs: 1000, durationMs: 5000 }), secondBeatWith({ sceneIds: ['closing'] })],
    }))
    assert.ok(codesOf(report).includes('BEAT_PLAN_TIMELINE_START_INVALID'))
    assert.equal(report.errors[0]?.path, 'beats[0].startMs')
})

test('timeline com um unico beat deve comecar em zero', () => {
    const report = validate(beatPlanWith({ beats: [beatWith({ startMs: 500, durationMs: 4500 })] }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_TIMELINE_START_INVALID'])
})

test('lacuna temporal produz BEAT_PLAN_TIMELINE_GAP', () => {
    const report = validate(planWithSecondBeat({ startMs: 3500, durationMs: 1500 }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_TIMELINE_GAP'])
    assert.equal(report.errors[0]?.path, 'beats[1].startMs')
})

test('sobreposicao produz BEAT_PLAN_TIMELINE_OVERLAP', () => {
    const report = validate(planWithSecondBeat({ startMs: 2500, durationMs: 2500 }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_TIMELINE_OVERLAP'])
    assert.equal(report.errors[0]?.path, 'beats[1].startMs')
})

test('termino antes e depois da Composition produz BEAT_PLAN_TIMELINE_END_MISMATCH', () => {
    const before = validate(planWithSecondBeat({ durationMs: 1000 }))
    assert.deepEqual(codesOf(before), ['BEAT_PLAN_TIMELINE_END_MISMATCH'])
    assert.equal(before.totalDurationMs, 4000)

    const after = validate(planWithSecondBeat({ durationMs: 3000 }))
    assert.deepEqual(codesOf(after), ['BEAT_PLAN_TIMELINE_END_MISMATCH'])
    assert.equal(after.totalDurationMs, 6000)
})

test('timeline contigua que termina exatamente na Composition e aceita', () => {
    const report = validate(beatPlanWith({
        beats: [
            beatWith({ durationMs: 1000 }),
            secondBeatWith({ id: 'meio', order: 2, sceneIds: ['opening'], startMs: 1000, durationMs: 2000 }),
            beatWith({ id: 'fim', order: 3, sceneIds: ['closing'], startMs: 3000, durationMs: 2000 }),
        ],
    }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.totalDurationMs, 5000)
    assert.equal(report.beatCount, 3)
})

/* ========================================================================== */
/* Requisitos 43 a 49: narration e onScreenText                                */
/* ========================================================================== */

test('narration ausente e valida e nao gera erro', () => {
    const report = validate(planWithFirstBeat({ narration: undefined }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.narrationBeatCount, 1)
})

test('narration malformada produz BEAT_PLAN_NARRATION_INVALID', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ narration: 'texto' }))), ['BEAT_PLAN_NARRATION_INVALID'])
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ narration: { text: 'Texto.', voice: 'neutra' } }))),
        ['BEAT_PLAN_NARRATION_INVALID'],
    )
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ narration: { text: 'Texto.', provider: 'algum' } }))),
        ['BEAT_PLAN_NARRATION_INVALID'],
    )
})

test('narration.text ausente e vazio produzem BEAT_PLAN_NARRATION_TEXT_REQUIRED', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ narration: {} }))), ['BEAT_PLAN_NARRATION_TEXT_REQUIRED'])
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ narration: { text: '   ' } }))),
        ['BEAT_PLAN_NARRATION_TEXT_REQUIRED'],
    )
})

test('onScreenText ausente e valido; nao string e vazio sao invalidos', () => {
    const absent = validate(planWithFirstBeat({ onScreenText: undefined }))
    assert.equal(absent.valid, true, JSON.stringify(absent.errors))
    assert.equal(absent.onScreenTextBeatCount, 1)

    assert.deepEqual(codesOf(validate(planWithFirstBeat({ onScreenText: 42 }))), ['BEAT_PLAN_ON_SCREEN_TEXT_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ onScreenText: '  ' }))), ['BEAT_PLAN_ON_SCREEN_TEXT_INVALID'])
})

/* ========================================================================== */
/* Requisitos 50 a 54: intencoes visuais, de movimento e transicao             */
/* ========================================================================== */

test('visualIntent ausente e vazia produzem BEAT_PLAN_VISUAL_INTENT_REQUIRED', () => {
    const missing = beatWith({})
    delete missing.visualIntent
    assert.deepEqual(
        codesOf(validate(beatPlanWith({ beats: [missing, secondBeatWith({})] }))),
        ['BEAT_PLAN_VISUAL_INTENT_REQUIRED'],
    )
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ visualIntent: '   ' }))), ['BEAT_PLAN_VISUAL_INTENT_REQUIRED'])
})

test('motionIntent fora da lista e rejeitada; todas as neutras sao aceitas', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ motionIntent: 'zoom-in-fast' }))), ['BEAT_PLAN_MOTION_INTENT_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ motionIntent: undefined }))), ['BEAT_PLAN_MOTION_INTENT_INVALID'])
    for (const motion of BEAT_MOTION_INTENTS) {
        assert.equal(validate(planWithFirstBeat({ motionIntent: motion })).valid, true, `motion ${motion}`)
    }
})

test('transitionIn e transitionOut fora da lista sao rejeitadas', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ transitionIn: 'wipe' }))), ['BEAT_PLAN_TRANSITION_IN_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ transitionOut: 'wipe' }))), ['BEAT_PLAN_TRANSITION_OUT_INVALID'])
    for (const transition of BEAT_TRANSITIONS) {
        assert.equal(validate(planWithFirstBeat({ transitionIn: transition, transitionOut: transition })).valid, true, `transicao ${transition}`)
    }
})

/* ========================================================================== */
/* Requisitos 55 a 60: evidencia editorial e validationStatus                  */
/* ========================================================================== */

test('editorialEvidence ausente e vazia produzem BEAT_PLAN_EDITORIAL_EVIDENCE_REQUIRED', () => {
    const missing = beatWith({})
    delete missing.editorialEvidence
    assert.deepEqual(
        codesOf(validate(beatPlanWith({ beats: [missing, secondBeatWith({})] }))),
        ['BEAT_PLAN_EDITORIAL_EVIDENCE_REQUIRED'],
    )
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ editorialEvidence: [] }))), ['BEAT_PLAN_EDITORIAL_EVIDENCE_REQUIRED'])
})

test('itens de editorialEvidence invalidos e caminhos absolutos', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ editorialEvidence: [1] }))), ['BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID'])
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ editorialEvidence: ['  '] }))), ['BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID'])
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ editorialEvidence: ['C:\\dados\\evidencia'] }))),
        ['BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID'],
    )
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ editorialEvidence: ['/etc/evidencia'] }))),
        ['BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID'],
    )
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ editorialEvidence: ['https://example.com/evidencia'] }))),
        ['BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID'],
    )
    assert.deepEqual(
        codesOf(validate(planWithFirstBeat({ editorialEvidence: ['../fora'] }))),
        ['BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID'],
    )
})

test('evidencia duplicada produz BEAT_PLAN_EDITORIAL_EVIDENCE_DUPLICATE', () => {
    const report = validate(planWithFirstBeat({ editorialEvidence: ['technical-example', 'technical-example'] }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_EDITORIAL_EVIDENCE_DUPLICATE'])
    assert.equal(report.errors[0]?.path, 'beats[0].editorialEvidence[1]')
})

test('validationStatus fora da lista e rejeitado; todos os estados sao aceitos', () => {
    assert.deepEqual(codesOf(validate(planWithFirstBeat({ validationStatus: 'published' }))), ['BEAT_PLAN_VALIDATION_STATUS_INVALID'])
    for (const status of BEAT_VALIDATION_STATUSES) {
        const report = validate(planWithFirstBeat({ validationStatus: status }))
        assert.equal(report.valid, true, `status ${status}`)
    }
})

test('validationStatus validated nao altera o resultado tecnico do relatorio', () => {
    const report = validate(planWithFirstBeat({ validationStatus: 'validated' }))
    assert.equal(report.valid, true)
    assert.equal(report.summary, 'Beat plan is valid.')
})

/* ========================================================================== */
/* Requisitos 61 a 68: metadata                                                */
/* ========================================================================== */

test('metadata ausente e valida e metadataStatus fica null', () => {
    const report = validate(beatPlanWith({}))
    assert.equal(report.valid, true)
    assert.equal(report.metadataStatus, null)
})

test('metadata valida com status, description e tags', () => {
    const report = validate(beatPlanWith({
        metadata: { status: 'review', description: 'Descricao tecnica.', tags: ['exemplo', 'contrato'] },
    }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.metadataStatus, 'review')
    for (const status of BEAT_PLAN_METADATA_STATUSES) {
        assert.equal(validate(beatPlanWith({ metadata: { status } })).valid, true, `status ${status}`)
    }
})

test('metadata com status invalido produz BEAT_PLAN_METADATA_STATUS_INVALID', () => {
    const report = validate(beatPlanWith({ metadata: { status: 'published' } }))
    assert.deepEqual(codesOf(report), ['BEAT_PLAN_METADATA_STATUS_INVALID'])
    assert.equal(report.metadataStatus, null)
})

test('metadata com description vazia produz BEAT_PLAN_METADATA_DESCRIPTION_INVALID', () => {
    assert.deepEqual(codesOf(validate(beatPlanWith({ metadata: { description: '  ' } }))), ['BEAT_PLAN_METADATA_DESCRIPTION_INVALID'])
})

test('tags invalidas, duplicadas, acima do limite e campo desconhecido', () => {
    assert.deepEqual(codesOf(validate(beatPlanWith({ metadata: { tags: [''] } }))), ['BEAT_PLAN_METADATA_TAG_INVALID'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ metadata: { tags: 'exemplo' } }))), ['BEAT_PLAN_METADATA_TAG_INVALID'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ metadata: { tags: ['a', 'a'] } }))), ['BEAT_PLAN_METADATA_TAG_DUPLICATE'])
    assert.deepEqual(
        codesOf(validate(beatPlanWith({ metadata: { tags: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'] } }))),
        ['BEAT_PLAN_METADATA_TAG_LIMIT'],
    )
    assert.equal(BEAT_PLAN_MAX_TAGS, 8)
    assert.deepEqual(codesOf(validate(beatPlanWith({ metadata: { extra: 1 } }))), ['BEAT_PLAN_METADATA_INVALID'])
    assert.deepEqual(codesOf(validate(beatPlanWith({ metadata: 'rascunho' }))), ['BEAT_PLAN_METADATA_INVALID'])
})

/* ========================================================================== */
/* Requisitos 69 a 75: warnings                                                */
/* ========================================================================== */

test('cena nao referenciada gera BEAT_PLAN_SCENE_UNREFERENCED sem invalidar', () => {
    const report = validate(beatPlanWith({ beats: [beatWith({ durationMs: 5000 })] }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.deepEqual(warningCodesOf(report), ['BEAT_PLAN_SCENE_UNREFERENCED'])
    assert.equal(report.warnings[0]?.path, 'composition.scenes[1].id')
    assert.match(report.warnings[0]?.message ?? '', /closing/)
    assert.equal(report.referencedSceneCount, 1)
    assert.equal(report.compositionSceneCount, 2)
})

test('nenhuma narration gera warning global unico', () => {
    const report = validate(beatPlanWith({
        beats: [beatWith({ narration: undefined }), secondBeatWith({ narration: undefined })],
    }))
    assert.equal(report.valid, true)
    assert.deepEqual(warningCodesOf(report), ['BEAT_PLAN_NARRATION_MISSING'])
    assert.equal(report.narrationBeatCount, 0)
})

test('nenhum onScreenText gera warning global unico', () => {
    const report = validate(beatPlanWith({
        beats: [beatWith({ onScreenText: undefined }), secondBeatWith({ onScreenText: undefined })],
    }))
    assert.equal(report.valid, true)
    assert.deepEqual(warningCodesOf(report), ['BEAT_PLAN_ON_SCREEN_TEXT_MISSING'])
    assert.equal(report.onScreenTextBeatCount, 0)
})

test('narration longa gera BEAT_PLAN_NARRATION_TEXT_LONG', () => {
    const longText = 'x'.repeat(BEAT_PLAN_MAX_NARRATION_LENGTH + 1)
    const report = validate(planWithFirstBeat({ narration: { text: longText } }))
    assert.equal(report.valid, true)
    assert.deepEqual(warningCodesOf(report), ['BEAT_PLAN_NARRATION_TEXT_LONG'])
    assert.equal(report.warnings[0]?.path, 'beats[0].narration.text')
})

test('onScreenText longo gera BEAT_PLAN_ON_SCREEN_TEXT_LONG', () => {
    const longText = 'x'.repeat(BEAT_PLAN_MAX_ON_SCREEN_TEXT_LENGTH + 1)
    const report = validate(planWithFirstBeat({ onScreenText: longText }))
    assert.equal(report.valid, true)
    assert.deepEqual(warningCodesOf(report), ['BEAT_PLAN_ON_SCREEN_TEXT_LONG'])
    assert.equal(report.warnings[0]?.path, 'beats[0].onScreenText')
})

test('risco de leitura usa max(1000, palavras*300) e informa as duracoes', () => {
    const report = validate(planWithSecondBeat({ onScreenText: words(10) }))
    assert.equal(report.valid, true)
    assert.deepEqual(warningCodesOf(report), ['BEAT_PLAN_READING_TIME_RISK'])
    assert.equal(report.warnings[0]?.path, 'beats[1].durationMs')
    assert.match(report.warnings[0]?.message ?? '', /2000 ms/)
    assert.match(report.warnings[0]?.message ?? '', /3000 ms/)
})

test('heuristica de leitura tem piso de 1000 ms e escala por palavra', () => {
    const atFloor = validate(beatPlanWith({
        beats: [beatWith({ onScreenText: words(2), durationMs: 1000 }), secondBeatWith({ startMs: 1000, durationMs: 4000 })],
    }))
    assert.equal(atFloor.valid, true, JSON.stringify(atFloor.errors))
    assert.deepEqual(warningCodesOf(atFloor), [])

    const belowFloor = validate(beatPlanWith({
        beats: [beatWith({ onScreenText: words(1), durationMs: 999 }), secondBeatWith({ startMs: 999, durationMs: 4001 })],
    }))
    assert.equal(belowFloor.valid, true, JSON.stringify(belowFloor.errors))
    assert.deepEqual(warningCodesOf(belowFloor), ['BEAT_PLAN_READING_TIME_RISK'])
    assert.match(belowFloor.warnings[0]?.message ?? '', /999 ms/)
    assert.match(belowFloor.warnings[0]?.message ?? '', /1000 ms/)

    const fourWords = validate(beatPlanWith({
        beats: [beatWith({ onScreenText: words(4), durationMs: 1000 }), secondBeatWith({ startMs: 1000, durationMs: 4000 })],
    }))
    assert.deepEqual(warningCodesOf(fourWords), ['BEAT_PLAN_READING_TIME_RISK'])
    assert.match(fourWords.warnings[0]?.message ?? '', /1200 ms/)
})

test('espacos repetidos nao contam como palavras extras', () => {
    const padded = validate(planWithSecondBeat({ onScreenText: `${words(10)}     ` }))
    assert.deepEqual(warningCodesOf(padded), ['BEAT_PLAN_READING_TIME_RISK'])
    assert.match(padded.warnings[0]?.message ?? '', /3000 ms/)
})

test('warnings nao invalidam e a ordem e global, por beat e por cena', () => {
    const report = validate(beatPlanWith({
        beats: [beatWith({ narration: undefined, onScreenText: words(20), durationMs: 5000 })],
    }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.deepEqual(warningCodesOf(report), [
        'BEAT_PLAN_NARRATION_MISSING',
        'BEAT_PLAN_READING_TIME_RISK',
        'BEAT_PLAN_SCENE_UNREFERENCED',
    ])
})

/* ========================================================================== */
/* Requisitos 76 a 86: relatorio e determinismo                                */
/* ========================================================================== */

test('campos derivados do relatorio sao calculados corretamente', () => {
    const report = validate(beatPlanWith({
        metadata: { status: 'review' },
        beats: [beatWith({}), secondBeatWith({ narration: undefined, onScreenText: undefined })],
    }))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.beatCount, 2)
    assert.equal(report.compositionSceneCount, 2)
    assert.equal(report.referencedSceneCount, 2)
    assert.equal(report.totalDurationMs, 5000)
    assert.equal(report.compositionDurationMs, 5000)
    assert.equal(report.narrationBeatCount, 1)
    assert.equal(report.onScreenTextBeatCount, 1)
    assert.equal(report.metadataStatus, 'review')
    assert.equal(report.schemaVersion, 1)
    assert.equal(report.beatPlanId, 'plano-teste')
    assert.deepEqual(warningCodesOf(report), [])
})

test('beatCount conta somente entradas que sao objetos', () => {
    const report = validate(beatPlanWith({ beats: [beatWith({}), 'texto', secondBeatWith({})] }))
    assert.equal(report.beatCount, 2)
    assert.ok(codesOf(report).includes('BEAT_PLAN_BEAT_INVALID'))
})

test('relatorio e deterministico para a mesma entrada', () => {
    const first = validate(beatPlanWith({}))
    const second = validate(structuredClone(beatPlanWith({})))
    assert.equal(JSON.stringify(first), JSON.stringify(second))
})

test('a ordem dos errors e estavel e fixa', () => {
    const input = beatPlanWith({
        schemaVersion: 2,
        projectId: 'Projeto_Teste',
        id: 'Plano Teste',
        locale: 'en-US',
        beats: [
            beatWith({ id: 'Abertura', order: 0, sceneIds: ['Opening'], narrativeFunction: 'venda', startMs: -1, durationMs: 0 }),
            secondBeatWith({ motionIntent: 'zoom', transitionIn: 'wipe', validationStatus: 'published' }),
        ],
    })
    const firstRun = codesOf(validate(structuredClone(input)))
    const secondRun = codesOf(validate(structuredClone(input)))
    assert.deepEqual(secondRun, firstRun)
    assert.deepEqual(firstRun, [
        'BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED',
        'BEAT_PLAN_PROJECT_ID_INVALID',
        'BEAT_PLAN_ID_INVALID',
        'BEAT_PLAN_BEAT_ID_INVALID',
        'BEAT_PLAN_ORDER_INVALID',
        'BEAT_PLAN_SCENE_ID_INVALID',
        'BEAT_PLAN_NARRATIVE_FUNCTION_INVALID',
        'BEAT_PLAN_START_INVALID',
        'BEAT_PLAN_DURATION_INVALID',
        'BEAT_PLAN_MOTION_INTENT_INVALID',
        'BEAT_PLAN_TRANSITION_IN_INVALID',
        'BEAT_PLAN_VALIDATION_STATUS_INVALID',
        'BEAT_PLAN_LOCALE_MISMATCH',
    ])
})

test('a ordem dos warnings e estavel', () => {
    const build = () => validate(beatPlanWith({
        beats: [beatWith({ narration: undefined, onScreenText: words(20), durationMs: 5000 })],
    }))
    assert.equal(JSON.stringify(build().warnings), JSON.stringify(build().warnings))
})

test('summary usa texto estavel e warnings nao contam como errors', () => {
    const valid = validate(beatPlanWith({}))
    assert.equal(valid.summary, 'Beat plan is valid.')

    const invalid = validate(beatPlanWith({ schemaVersion: 3 }))
    assert.equal(invalid.summary, 'Beat plan is invalid: 1 error(s).')

    const withWarnings = validate(beatPlanWith({ beats: [beatWith({ durationMs: 5000 })] }))
    assert.equal(withWarnings.valid, true)
    assert.equal(withWarnings.summary, 'Beat plan is valid.')
    assert.equal(withWarnings.warnings.length, 1)
})

test('inputs nao sao mutados pelo validador', () => {
    const beatPlan = beatPlanWith({})
    const composition = compositionWith({})
    const project = projectWith({})
    const beforePlan = JSON.stringify(beatPlan)
    const beforeComposition = JSON.stringify(composition)
    const beforeProject = JSON.stringify(project)
    validate(beatPlan, composition, project)
    assert.equal(JSON.stringify(beatPlan), beforePlan)
    assert.equal(JSON.stringify(composition), beforeComposition)
    assert.equal(JSON.stringify(project), beforeProject)
})


/* ========================================================================== */
/* Requisitos 100 a 104: seguranca, independencia e coerencia                  */
/* ========================================================================== */

test('validador, contrato e CLI nao usam rede nem abrem arquivos alem dos informados', () => {
    const forbiddenCalls = ['fetch(', 'http.request', 'https.request', 'XMLHttpRequest', 'net.connect', 'process.env', 'dotenv', 'axios', 'undici']
    for (const relative of ['src/validate-beat-plan.ts', 'src/validate-beat-plan-cli.ts', 'src/beat-plan-contract.ts']) {
        const content = readFileSync(path.join(moduleRoot, relative), 'utf8')
        for (const needle of forbiddenCalls) {
            assert.ok(!content.includes(needle), `chamada proibida "${needle}" em ${relative}`)
        }
    }
    const validator = readFileSync(path.join(moduleRoot, 'src', 'validate-beat-plan.ts'), 'utf8')
    assert.ok(!validator.includes('readFileSync('), 'somente a CLI pode ler arquivos; o validador nao')
    assert.ok(!validator.includes('writeFileSync('), 'o validador nao cria arquivos')

    // A leitura de JSON da CLI vem do helper compartilhado: ela nao abre o
    // filesystem por conta propria nem escreve em lugar nenhum.
    const cli = readFileSync(path.join(moduleRoot, 'src', 'validate-beat-plan-cli.ts'), 'utf8')
    assert.ok(!cli.includes('node:fs'), 'a CLI so le arquivos atraves de cli-input.ts')
    assert.ok(!cli.includes('writeFileSync('), 'a CLI nao cria nem altera arquivos')
})

/**
 * Varre `src/` e `schemas/` em ordem deterministica e devolve caminhos relativos
 * com barra. A lista e fechada: um arquivo novo so passa pelo teste se entrar
 * explicitamente numa das expectativas abaixo.
 */
function listModuleFiles(relativeRoot: string): string[] {
    const root = path.join(moduleRoot, relativeRoot)
    const found: string[] = []

    function walk(directory: string, prefix: string): void {
        const entries = readdirSync(directory, { withFileTypes: true })
            .slice()
            .sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0))
        for (const entry of entries) {
            const relative = prefix ? `${prefix}/${entry.name}` : entry.name
            if (entry.isDirectory()) walk(path.join(directory, entry.name), relative)
            else found.push(relative)
        }
    }

    walk(root, '')
    return found.sort()
}

/** Arquivos que esta fatia adiciona ao nucleo. Nada alem deles e autorizado. */
const BEAT_PLAN_SOURCE_FILES = ['beat-plan-contract.ts', 'validate-beat-plan.ts', 'validate-beat-plan-cli.ts']
const BEAT_PLAN_SCHEMA_FILES = ['beat-plan.schema.json']

/** Arquivos da validacao consolidada do pipeline. */
const PIPELINE_SOURCE_FILES = [
    'content-pipeline-validation-cli.ts',
    'content-pipeline-validation-contract.ts',
    'validate-content-pipeline.ts',
]

/** Arquivos do contrato de caso e da CLI multiprojeto (segundo consumidor). */
const CASE_SOURCE_FILES = [
    'content-pipeline-case-contract.ts',
    'content-pipeline-case-loader.ts',
    'content-pipeline-cases-cli.ts',
    'resolve-content-pipeline-case.ts',
    'validate-content-pipeline-case.ts',
]

/** Arquivos do CreativeExecutionPackage v1 (pacote tecnico de execucao). */
const EXECUTION_PACKAGE_SOURCE_FILES = [
    'creative-execution-package-cli.ts',
    'creative-execution-package-contract.ts',
    'creative-execution-packages.ts',
    'create-creative-execution-package.ts',
    'serialize-creative-execution-package.ts',
    'validate-creative-execution-package.ts',
]
const EXECUTION_PACKAGE_SCHEMA_FILES = ['creative-execution-package.schema.json']

/** Arquivos do executor local simulado v1 (verificacao de contrato, nao renderer). */
const SIMULATED_EXECUTION_SOURCE_FILES = [
    'create-simulated-execution-plan.ts',
    'serialize-simulated-execution.ts',
    'simulated-execution-cli.ts',
    'simulated-execution-multicase.ts',
    'simulated-execution-plan-contract.ts',
    'simulated-execution-report-contract.ts',
    'simulated-execution-runner.ts',
    'simulated-execution-writer.ts',
    'validate-simulated-execution-plan.ts',
    'validate-simulated-execution-report.ts',
]
const SIMULATED_EXECUTION_SCHEMA_FILES = [
    'simulated-execution-plan.schema.json',
    'simulated-execution-report.schema.json',
]

/** Ponte interna de entrada do adaptador de render local de prova (tools/). */
const LOCAL_RENDER_INPUT_SOURCE_FILES = [
    'local-render-input-contract.ts',
    'validate-local-render-input.ts',
]

/** Plano de sobreposicao textual editavel v1 (piloto de composicao e render local). */
const TEXT_OVERLAY_PLAN_SOURCE_FILES = [
    'serialize-text-overlay-plan.ts',
    'text-overlay-plan-contract.ts',
    'validate-text-overlay-plan.ts',
]
const TEXT_OVERLAY_PLAN_SCHEMA_FILES = [
    'text-overlay-plan.schema.json',
]

/** Direcao visual compartilhada VisualStyle v1 (piloto de composicao e render local). */
const VISUAL_STYLE_SOURCE_FILES = [
    'serialize-visual-style.ts',
    'validate-visual-style.ts',
    'visual-style-contract.ts',
]
const VISUAL_STYLE_SCHEMA_FILES = [
    'visual-style.schema.json',
]

/** Inventario versionado de midia AssetManifest v1 (render local e pipeline). */
const ASSET_MANIFEST_SOURCE_FILES = [
    'asset-manifest-contract.ts',
    'serialize-asset-manifest.ts',
    'validate-asset-manifest.ts',
]
const ASSET_MANIFEST_SCHEMA_FILES = [
    'asset-manifest.schema.json',
]

/** Entrada unica de producao de video VideoRequest v1 (compilador puro). */
const VIDEO_REQUEST_SOURCE_FILES = [
    'compile-video-request.ts',
    'validate-video-request.ts',
    'video-request-contract.ts',
]
const VIDEO_REQUEST_SCHEMA_FILES = [
    'video-request.schema.json',
]

/** Entrada unica de carrossel de imagens CarouselRequest v1 (R003). */
const CAROUSEL_REQUEST_SOURCE_FILES = [
    'carousel-request-contract.ts',
    'validate-carousel-request.ts',
]
const CAROUSEL_REQUEST_SCHEMA_FILES = [
    'carousel-request.schema.json',
]

/** Arquivos que ja existiam na main apos o R001 e seguem intactos. */
const PREEXISTING_SOURCE_FILES = [
    'cli-input.ts',
    'composition-contract.ts',
    'composition-validation-api.ts',
    'output-plan-cli.ts',
    'output-plan-contract.ts',
    'output-profiles-cli.ts',
    'output-profiles/catalog.ts',
    'output-profiles/geometry.ts',
    'output-profiles/rules.ts',
    'output-profiles/types.ts',
    'project-contract.ts',
    'relative-path.ts',
    'resolve-output-profile.ts',
    'validate-composition-cli.ts',
    'validate-composition-output.ts',
    'validate-composition.ts',
    'validate-output-plan.ts',
    'validate-project-cli.ts',
    'validate-project.ts',
    'validation-report.ts',
]
const PREEXISTING_SCHEMA_FILES = [
    'composition.schema.json',
    'output-plan.schema.json',
    'project.schema.json',
]

test('o nucleo de beat plan nao contem referencia a projetos nem a fornecedores', () => {
    const forbidden = [
        'marca salão',
        'marca-salao',
        'ns-001',
        'marcasalao.com.br',
        'salao02',
        'multitrack',
        'multitrackhub.com.br',
        'google flow',
        'hyperframes',
        'elevenlabs',
        'ffmpeg',
        'capcut',
    ]

    // Varredura recursiva: `src/output-profiles/` existe na main e um readdirSync
    // raso tentaria ler diretorio como arquivo (e deixaria de ler os catalogs).
    const scanned = coreScanDirectories.flatMap((directory) =>
        listModuleFiles(path.relative(moduleRoot, directory)).map((relative) => path.join(directory, relative)),
    )
    assert.ok(scanned.length >= 2, 'a varredura do nucleo nao encontrou arquivos')
    for (const filePath of scanned) {
        const content = readFileSync(filePath, 'utf8').toLowerCase()
        for (const needle of forbidden) {
            assert.ok(
                !content.includes(needle),
                `Referencia proibida "${needle}" encontrada em ${filePath}`,
            )
        }
    }
})

test('o schema de beat plan declara a mesma superficie do contrato', () => {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', 'beat-plan.schema.json'), 'utf8')) as {
        additionalProperties?: boolean
        required?: string[]
        properties?: Record<string, unknown>
        definitions?: {
            beat?: {
                additionalProperties?: boolean
                required?: string[]
                properties?: Record<string, { enum?: string[] }>
            }
        }
    }

    assert.equal(schema.additionalProperties, false)
    assert.deepEqual(schema.required, ['schemaVersion', 'projectId', 'compositionId', 'id', 'locale', 'beats'])
    assert.deepEqual(Object.keys(schema.properties ?? {}).sort(), [
        'beats',
        'compositionId',
        'id',
        'locale',
        'metadata',
        'projectId',
        'schemaVersion',
    ])

    const beat = schema.definitions?.beat
    assert.equal(beat?.additionalProperties, false)
    assert.deepEqual(beat?.required, [
        'id',
        'order',
        'sceneIds',
        'narrativeFunction',
        'startMs',
        'durationMs',
        'visualIntent',
        'motionIntent',
        'transitionIn',
        'transitionOut',
        'editorialEvidence',
        'validationStatus',
    ])
    assert.deepEqual(beat?.properties?.narrativeFunction?.enum, [...BEAT_NARRATIVE_FUNCTIONS])
    assert.deepEqual(beat?.properties?.motionIntent?.enum, [...BEAT_MOTION_INTENTS])
    assert.deepEqual(beat?.properties?.transitionIn?.enum, [...BEAT_TRANSITIONS])
    assert.deepEqual(beat?.properties?.transitionOut?.enum, [...BEAT_TRANSITIONS])
    assert.deepEqual(beat?.properties?.validationStatus?.enum, [...BEAT_VALIDATION_STATUSES])
})

/**
 * Inventario fechado da arvore real pos-R001. As tres expectativas sao
 * separadas de proposito: o que a main ja tinha, o que o BeatPlan acrescenta e
 * a uniao conferida contra o disco. Nenhum contrato existente sai da lista.
 */
test('nenhum contrato fora do escopo desta fatia foi criado', () => {
    const sourceFiles = listModuleFiles('src')
    const schemaFiles = listModuleFiles('schemas')

    for (const [root, relative] of [
        ['src', BEAT_PLAN_SOURCE_FILES],
        ['schemas', BEAT_PLAN_SCHEMA_FILES],
        ['src', PREEXISTING_SOURCE_FILES],
        ['schemas', PREEXISTING_SCHEMA_FILES],
        ['src', PIPELINE_SOURCE_FILES],
        ['src', CASE_SOURCE_FILES],
        ['src', EXECUTION_PACKAGE_SOURCE_FILES],
        ['schemas', EXECUTION_PACKAGE_SCHEMA_FILES],
        ['src', SIMULATED_EXECUTION_SOURCE_FILES],
        ['schemas', SIMULATED_EXECUTION_SCHEMA_FILES],
        ['src', LOCAL_RENDER_INPUT_SOURCE_FILES],
        ['src', TEXT_OVERLAY_PLAN_SOURCE_FILES],
        ['schemas', TEXT_OVERLAY_PLAN_SCHEMA_FILES],
        ['src', VISUAL_STYLE_SOURCE_FILES],
        ['schemas', VISUAL_STYLE_SCHEMA_FILES],
        ['src', ASSET_MANIFEST_SOURCE_FILES],
        ['schemas', ASSET_MANIFEST_SCHEMA_FILES],
        ['src', VIDEO_REQUEST_SOURCE_FILES],
        ['schemas', VIDEO_REQUEST_SCHEMA_FILES],
        ['src', CAROUSEL_REQUEST_SOURCE_FILES],
        ['schemas', CAROUSEL_REQUEST_SCHEMA_FILES],
    ] as const) {
        for (const file of relative) {
            assert.ok(
                existsSync(path.join(moduleRoot, root, file)),
                `arquivo esperado ausente em ${root}/: ${file}`,
            )
        }
    }

    assert.deepEqual(
        sourceFiles,
        [...PREEXISTING_SOURCE_FILES, ...BEAT_PLAN_SOURCE_FILES, ...PIPELINE_SOURCE_FILES, ...CASE_SOURCE_FILES, ...EXECUTION_PACKAGE_SOURCE_FILES, ...SIMULATED_EXECUTION_SOURCE_FILES, ...LOCAL_RENDER_INPUT_SOURCE_FILES, ...TEXT_OVERLAY_PLAN_SOURCE_FILES, ...VISUAL_STYLE_SOURCE_FILES, ...ASSET_MANIFEST_SOURCE_FILES, ...VIDEO_REQUEST_SOURCE_FILES, ...CAROUSEL_REQUEST_SOURCE_FILES].sort(),
        'src/ so pode conter os contratos da main mais os arquivos desta fatia',
    )
    assert.deepEqual(
        schemaFiles,
        [...PREEXISTING_SCHEMA_FILES, ...BEAT_PLAN_SCHEMA_FILES, ...EXECUTION_PACKAGE_SCHEMA_FILES, ...SIMULATED_EXECUTION_SCHEMA_FILES, ...TEXT_OVERLAY_PLAN_SCHEMA_FILES, ...VISUAL_STYLE_SCHEMA_FILES, ...ASSET_MANIFEST_SCHEMA_FILES, ...VIDEO_REQUEST_SCHEMA_FILES, ...CAROUSEL_REQUEST_SCHEMA_FILES].sort(),
        'schemas/ so pode conter os espelhos da main mais o do BeatPlan',
    )

    const beatPlanEntries = [...sourceFiles, ...schemaFiles].filter((relative) => relative.includes('beat-plan'))
    assert.deepEqual(
        beatPlanEntries.sort(),
        [...BEAT_PLAN_SOURCE_FILES, ...BEAT_PLAN_SCHEMA_FILES].sort(),
        'nenhum arquivo de VisualAnchor, AssetManifest, AudioPlan ou RenderPlan foi criado',
    )

    for (const forbidden of ['adapters', 'outputs', 'previews', 'assets', 'audio-plans', 'render-plans', 'visual-styles', 'visual-anchors', 'asset-manifests']) {
        assert.ok(!existsSync(path.join(moduleRoot, forbidden)), `diretorio fora de escopo: ${forbidden}`)
    }
})
