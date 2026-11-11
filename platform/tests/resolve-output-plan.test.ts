/**
 * Resolucao de OutputPlan a partir do catalogo (R001-03).
 *
 * Os valores esperados deste arquivo sao **independentes do resolvedor**: as
 * doze geometrias estao escritas aqui como dados, nao lidas de `OUTPUT_PROFILES`.
 * Se o catalogo mudar sem que a matriz de saida mude junto, esta suite quebra —
 * que e exatamente o efeito procurado.
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { test } from 'node:test'

import { resolveOutputPlan, projectAllowedProfiles, type OutputPlanResolutionOptions } from '../src/resolve-output-profile.js'
import { validateOutputPlan } from '../src/validate-output-plan.js'
import type { OutputPlan, OutputPlanOf, RequiresInspection } from '../src/output-plan-contract.js'
import type { OutputMediaKind, RuleContext } from '../src/output-profiles/types.js'
import { projectWith } from './contract-harness.js'

const CATALOG_PROFILE_IDS = [
    'instagram-feed-image-square',
    'instagram-feed-image-portrait',
    'instagram-stories-image',
    'facebook-feed-image-square',
    'facebook-feed-image-portrait',
    'facebook-stories-image',
    'instagram-stories-video',
    'instagram-reels-video',
    'facebook-stories-video',
    'facebook-reels-video',
    'youtube-video-horizontal',
    'youtube-shorts',
] as const

const IMAGE_INSPECTION: readonly RequiresInspection[] = ['media-file', 'image-format', 'bytes', 'publication']
const VIDEO_INSPECTION: readonly RequiresInspection[] = ['media-file', 'codec', 'bytes', 'audio-streams', 'publication']

interface ExpectedPlan {
    readonly profileId: string
    readonly revision: number
    readonly mediaKind: OutputMediaKind
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
    readonly fps: number | null
    readonly pendingRuleIds: readonly string[]
    readonly requiresInspection: readonly RequiresInspection[]
}

/** Matriz de saida da etapa: os doze perfis e o plano que cada um deve produzir. */
const EXPECTED_PLANS: readonly ExpectedPlan[] = [
    { profileId: 'instagram-feed-image-square', revision: 2, mediaKind: 'image', width: 1080, height: 1080, aspectRatio: '1:1', fps: null, pendingRuleIds: [], requiresInspection: IMAGE_INSPECTION },
    { profileId: 'instagram-feed-image-portrait', revision: 2, mediaKind: 'image', width: 1080, height: 1350, aspectRatio: '4:5', fps: null, pendingRuleIds: [], requiresInspection: IMAGE_INSPECTION },
    { profileId: 'instagram-stories-image', revision: 2, mediaKind: 'image', width: 1080, height: 1920, aspectRatio: '9:16', fps: null, pendingRuleIds: [], requiresInspection: IMAGE_INSPECTION },
    { profileId: 'facebook-feed-image-square', revision: 2, mediaKind: 'image', width: 1080, height: 1080, aspectRatio: '1:1', fps: null, pendingRuleIds: ['P-FB-01'], requiresInspection: IMAGE_INSPECTION },
    { profileId: 'facebook-feed-image-portrait', revision: 2, mediaKind: 'image', width: 1080, height: 1350, aspectRatio: '4:5', fps: null, pendingRuleIds: ['P-FB-01'], requiresInspection: IMAGE_INSPECTION },
    { profileId: 'facebook-stories-image', revision: 2, mediaKind: 'image', width: 1080, height: 1920, aspectRatio: '9:16', fps: null, pendingRuleIds: ['P-FB-01'], requiresInspection: IMAGE_INSPECTION },
    { profileId: 'instagram-stories-video', revision: 2, mediaKind: 'video', width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, pendingRuleIds: [], requiresInspection: VIDEO_INSPECTION },
    { profileId: 'instagram-reels-video', revision: 2, mediaKind: 'video', width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, pendingRuleIds: [], requiresInspection: VIDEO_INSPECTION },
    { profileId: 'facebook-stories-video', revision: 2, mediaKind: 'video', width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, pendingRuleIds: ['P-FB-03'], requiresInspection: VIDEO_INSPECTION },
    { profileId: 'facebook-reels-video', revision: 2, mediaKind: 'video', width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, pendingRuleIds: ['P-FB-03'], requiresInspection: VIDEO_INSPECTION },
    { profileId: 'youtube-video-horizontal', revision: 2, mediaKind: 'video', width: 1920, height: 1080, aspectRatio: '16:9', fps: 30, pendingRuleIds: [], requiresInspection: VIDEO_INSPECTION },
    { profileId: 'youtube-shorts', revision: 3, mediaKind: 'video', width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, pendingRuleIds: ['P-YT-03'], requiresInspection: VIDEO_INSPECTION },
]

function catalogProject(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return projectWith({ outputProfiles: [...CATALOG_PROFILE_IDS], ...overrides })
}

function expectedPlanObject(expected: ExpectedPlan, ruleContext?: RuleContext): Record<string, unknown> {
    const payload: Record<string, unknown> = { width: expected.width, height: expected.height, aspectRatio: expected.aspectRatio }
    if (expected.mediaKind === 'video') payload.fps = expected.fps
    const head: Record<string, unknown> = {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        catalogVersion: '1',
        profileId: expected.profileId,
        profileRevision: expected.revision,
        mediaKind: expected.mediaKind,
    }
    if (ruleContext !== undefined) head.ruleContext = ruleContext
    head[expected.mediaKind] = payload
    return head
}

function expectedKeys(expected: ExpectedPlan, ruleContext?: RuleContext): string[] {
    const keys = ['schemaVersion', 'projectId', 'catalogVersion', 'profileId', 'profileRevision', 'mediaKind']
    if (ruleContext !== undefined) keys.push('ruleContext')
    keys.push(expected.mediaKind)
    return keys
}

test('o projeto tecnico que lista os doze perfis e aceito pelo validador de manifesto', () => {
    const { allowed, report } = projectAllowedProfiles(catalogProject())
    assert.equal(report.valid, true, report.errors.map((error) => error.code).join(', '))
    assert.deepEqual([...allowed], CATALOG_PROFILE_IDS)
})

for (const expected of EXPECTED_PLANS) {
    test(`resolve ${expected.profileId}`, () => {
        const project = catalogProject()
        const resolution = resolveOutputPlan(project, expected.profileId)

        assert.notEqual(resolution.plan, null, `plan nao produzido: ${resolution.report.errors.map((e) => `${e.code} @${e.path}`).join(', ')}`)
        assert.deepEqual(JSON.parse(JSON.stringify(resolution.plan)), expectedPlanObject(expected))
        assert.deepEqual(Object.keys(resolution.plan as object), expectedKeys(expected))

        const report = resolution.report
        assert.equal(report.valid, true, report.errors.map((error) => `${error.code} @${error.path}: ${error.message}`).join(' | '))
        assert.deepEqual(report.errors, [])
        assert.equal(report.summary, 'Output plan is valid.')
        assert.equal(report.projectId, 'projeto-teste')
        assert.equal(report.profileId, expected.profileId)
        assert.equal(report.catalogVersion, '1')
        assert.equal(report.profileRevision, expected.revision)
        assert.equal(report.mediaKind, expected.mediaKind)
        assert.equal(report.ruleContext, null, 'contexto nao informado e chave omitida, nunca string')
        assert.deepEqual(report.geometry, { width: expected.width, height: expected.height, aspectRatio: expected.aspectRatio })
        assert.deepEqual([...report.pendingRuleIds], expected.pendingRuleIds)
        assert.deepEqual([...report.requiresInspection], [...expected.requiresInspection])

        // fps so existe no ramo de video; em plano de imagem continua null, jamais 0.
        if (expected.mediaKind === 'video') {
            assert.equal(report.fps, expected.fps)
        } else {
            assert.equal(report.fps, null)
        }
    })
}

test('o contexto declarado entra no plano canonico, entre mediaKind e o payload', () => {
    const project = catalogProject()
    for (const context of ['in-app', 'api-publishing', 'ads', 'studio-upload'] as const) {
        const expected = EXPECTED_PLANS.find((item) => item.profileId === 'youtube-shorts') as ExpectedPlan
        const resolution = resolveOutputPlan(project, 'youtube-shorts', { ruleContext: context })
        assert.deepEqual(Object.keys(resolution.plan as object), expectedKeys(expected, context))
        assert.deepEqual(JSON.parse(JSON.stringify(resolution.plan)), expectedPlanObject(expected, context))
        assert.equal(resolution.report.ruleContext, context)
    }
})

test('o round-trip serializado revalida com o mesmo relatorio, com e sem contexto', () => {
    const project = catalogProject()
    for (const expected of EXPECTED_PLANS) {
        for (const context of [undefined, 'studio-upload', 'in-app'] as const) {
            const resolution = resolveOutputPlan(project, expected.profileId, context === undefined ? undefined : { ruleContext: context })
            const parsed = JSON.parse(JSON.stringify(resolution.plan)) as unknown
            const rerun = validateOutputPlan(parsed, project)

            assert.equal(rerun.valid, true, `${expected.profileId}/${String(context)}: ${rerun.errors.map((e) => e.code).join(', ')}`)
            assert.deepEqual(rerun, resolution.report, `round-trip divergiu da resolucao em ${expected.profileId}/${String(context)}`)
            assert.deepEqual(Object.keys(parsed as object), expectedKeys(expected, context))
        }
    }
})

test('um pedido resolve um plano, nunca uma lista de variacoes', () => {
    const resolution = resolveOutputPlan(catalogProject(), 'youtube-shorts', { network: 'youtube', publication: 'shorts', mediaKind: 'video' })
    assert.equal(typeof resolution.plan, 'object')
    assert.ok(!Array.isArray(resolution.plan))
    assert.deepEqual(JSON.parse(JSON.stringify(resolution.plan)), JSON.parse(JSON.stringify(resolveOutputPlan(catalogProject(), 'youtube-shorts').plan)))
})

test('filtros coerentes com o perfil nao mudam o plano', () => {
    const project = catalogProject()
    const plain = resolveOutputPlan(project, 'instagram-reels-video')
    const filtered = resolveOutputPlan(project, 'instagram-reels-video', { network: 'instagram', publication: 'reels', mediaKind: 'video' })
    assert.deepEqual(JSON.parse(JSON.stringify(filtered.plan)), JSON.parse(JSON.stringify(plain.plan)))
    assert.deepEqual(filtered.report, plain.report)
})

test('manifesto invalido bloqueia a resolucao sem derivar allowlist de documento rejeitado', () => {
    const resolution = resolveOutputPlan({ schemaVersion: 1 }, 'youtube-shorts')
    assert.equal(resolution.plan, null)
    assert.deepEqual(resolution.report.errors.map((error) => error.code), ['OUTPUT_PROJECT_INVALID'])
    assert.equal(resolution.report.errors[0]?.path, 'project')
    // O nome do perfil existe no catalogo, mas comparar allowlist contra manifesto
    // rejeitado criaria regra a partir de entrada malformada.
    assert.equal(resolution.report.profileId, 'youtube-shorts')
    assert.equal(resolution.report.projectId, null)
})

test('profileId que nao e kebab-case e erro de entrada, nao de catalogo', () => {
    const project = catalogProject()
    for (const profileId of ['YouTube Shorts', 'youtube_shorts', '-youtube', 'youtube-', '', 'youtube-SHORTS']) {
        const resolution = resolveOutputPlan(project, profileId)
        assert.equal(resolution.plan, null)
        assert.deepEqual(resolution.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_ID_INVALID'], `profileId ${JSON.stringify(profileId)}`)
    }
    for (const profileId of [42, null, undefined, ['youtube-shorts'], { id: 'youtube-shorts' }]) {
        const resolution = resolveOutputPlan(project, profileId)
        assert.deepEqual(resolution.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_ID_INVALID'], `profileId ${JSON.stringify(profileId)}`)
    }
})

test('profileId valido mas ausente do catalogo', () => {
    const resolution = resolveOutputPlan(catalogProject(), 'tiktok-videos')
    assert.equal(resolution.plan, null)
    assert.deepEqual(resolution.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_UNKNOWN'])
    assert.match(resolution.report.errors[0]?.message ?? '', /does not exist in catalog version "1"/)
})

test('perfil do catalogo fora da allowlist do projeto', () => {
    const project = catalogProject({ outputProfiles: ['youtube-video-horizontal'] })
    const resolution = resolveOutputPlan(project, 'youtube-shorts')
    assert.equal(resolution.plan, null)
    assert.deepEqual(resolution.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_NOT_ALLOWED'])
    assert.match(resolution.report.errors[0]?.message ?? '', /not listed in project "projeto-teste" outputProfiles/)
})

test('filtro que contradiz o perfil escolhido e selecao ambigua', () => {
    const project = catalogProject()
    const wrongKind = resolveOutputPlan(project, 'youtube-shorts', { mediaKind: 'image' })
    assert.deepEqual(wrongKind.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_AMBIGUOUS_SELECTION'])
    assert.equal(wrongKind.report.errors[0]?.path, 'options.mediaKind')
    assert.match(wrongKind.report.errors[0]?.message ?? '', /6 catalog profile\(s\) match the declared filters/)

    const wrongNetwork = resolveOutputPlan(project, 'youtube-shorts', { network: 'instagram' })
    assert.deepEqual(wrongNetwork.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_AMBIGUOUS_SELECTION'])
    assert.equal(wrongNetwork.report.errors[0]?.path, 'options.network')
    assert.match(wrongNetwork.report.errors[0]?.message ?? '', /5 catalog profile\(s\) match the declared filters/)

    const twoContradictions = resolveOutputPlan(project, 'youtube-shorts', { network: 'facebook', publication: 'feed' })
    assert.deepEqual(twoContradictions.report.errors.map((error) => error.code), [
        'OUTPUT_PROFILE_AMBIGUOUS_SELECTION',
        'OUTPUT_PROFILE_AMBIGUOUS_SELECTION',
    ])
})

test('filtro fora do enum, opcao desconhecida e options malformadas sao erros, nunca filtro silencioso', () => {
    const project = catalogProject()

    const outOfEnum = resolveOutputPlan(project, 'youtube-shorts', { network: 'tiktok', publication: 'lives' } as unknown as OutputPlanResolutionOptions)
    assert.deepEqual(outOfEnum.report.errors.map((error) => error.code), [
        'OUTPUT_PROFILE_FILTER_INVALID',
        'OUTPUT_PROFILE_FILTER_INVALID',
    ])
    assert.deepEqual(outOfEnum.report.errors.map((error) => error.path), ['options.network', 'options.publication'])

    const unknownOption = resolveOutputPlan(project, 'youtube-shorts', { brand: 'qualquer-coisa' } as unknown as OutputPlanResolutionOptions)
    assert.deepEqual(unknownOption.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_FILTER_INVALID'])
    assert.equal(unknownOption.report.errors[0]?.path, 'options.brand')

    const notObject = resolveOutputPlan(project, 'youtube-shorts', 'youtube' as unknown as OutputPlanResolutionOptions)
    assert.deepEqual(notObject.report.errors.map((error) => error.code), ['OUTPUT_PROFILE_FILTER_INVALID'])
    assert.equal(notObject.report.errors[0]?.path, 'options')
})

test('ruleContext null ou fora do enum invalida a opcao; ausencia nao invalida', () => {
    const project = catalogProject()
    const nullContext = resolveOutputPlan(project, 'youtube-shorts', { ruleContext: null } as unknown as OutputPlanResolutionOptions)
    assert.equal(nullContext.plan, null)
    assert.deepEqual(nullContext.report.errors.map((error) => error.code), ['OUTPUT_PLAN_RULE_CONTEXT_INVALID'])
    assert.match(nullContext.report.errors[0]?.message ?? '', /absence is an omitted key, never null/)

    const wrongContext = resolveOutputPlan(project, 'youtube-shorts', { ruleContext: 'web' } as unknown as OutputPlanResolutionOptions)
    assert.deepEqual(wrongContext.report.errors.map((error) => error.code), ['OUTPUT_PLAN_RULE_CONTEXT_INVALID'])

    const emptyOptions = resolveOutputPlan(project, 'youtube-shorts', {})
    assert.equal(emptyOptions.report.valid, true)
    assert.equal('ruleContext' in (emptyOptions.plan as object), false)
})

test('as causas se somam na ordem topo, perfil, opcoes', () => {
    const resolution = resolveOutputPlan({ schemaVersion: 2 }, 'INSTAGRAM', { network: 'tiktok' } as unknown as OutputPlanResolutionOptions)
    assert.deepEqual(resolution.report.errors.map((error) => error.code), [
        'OUTPUT_PROJECT_INVALID',
        'OUTPUT_PROFILE_ID_INVALID',
        'OUTPUT_PROFILE_FILTER_INVALID',
    ])
})

test('o resolvedor nao muta as entradas e e identico entre execucoes', () => {
    const project = catalogProject()
    const options: OutputPlanResolutionOptions = { ruleContext: 'studio-upload' }
    const before = JSON.stringify([project, 'youtube-shorts', options])
    const digests = new Set<string>()

    for (let run = 0; run < 5; run += 1) {
        const resolution = resolveOutputPlan(project, 'youtube-shorts', options)
        digests.add(createHash('sha256').update(JSON.stringify({ plan: resolution.plan, report: resolution.report })).digest('hex'))
    }

    assert.equal(digests.size, 1, 'dois runs produziram JSON diferente para a mesma entrada')
    assert.equal(JSON.stringify([project, 'youtube-shorts', options]), before, 'entrada mutada pela resolucao')
})

test('uma falha nao contamina a resolucao seguinte', () => {
    const project = catalogProject()
    assert.equal(resolveOutputPlan(project, 'perfil-inexistente').plan, null)
    assert.equal(resolveOutputPlan(project, 'youtube-shorts').report.valid, true)
    assert.equal(resolveOutputPlan({ schemaVersion: 1 }, 'youtube-shorts').plan, null)
    assert.equal(resolveOutputPlan(project, 'youtube-shorts').report.valid, true)
})

test('a uniao do plano restringe o ramo conforme mediaKind', () => {
    const project = catalogProject()
    const imagePlan = resolveOutputPlan(project, 'instagram-stories-image', { ruleContext: 'in-app' }).plan as OutputPlanOf<'image'>
    const videoPlan = resolveOutputPlan(project, 'youtube-shorts', { ruleContext: 'studio-upload' }).plan as OutputPlanOf<'video'>

    assert.equal(imagePlan.image.aspectRatio, '9:16')
    assert.equal(videoPlan.video.fps, 30)

    // @ts-expect-error o ramo de imagem nao aceita payload com fps
    const imagePlanWithFps: OutputPlanOf<'image'> = { ...imagePlan, image: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30 } }
    assert.equal(imagePlanWithFps.mediaKind, 'image')

    // @ts-expect-error um plano de video nao pode carregar tambem o payload de imagem
    const crossedPlan: OutputPlanOf<'video'> = { ...videoPlan, image: { width: 1080, height: 1080, aspectRatio: '1:1' } }
    assert.equal(crossedPlan.profileId, 'youtube-shorts')

    // @ts-expect-error ruleContext so aceita os quatro contextos do catalogo
    const hostileOptions: OutputPlanResolutionOptions = { ruleContext: null }
    assert.equal(hostileOptions.ruleContext, null)

    // @ts-expect-error a resolucao nao aceita um quinto tipo de midia
    const hostileFilter: OutputPlanResolutionOptions = { mediaKind: 'audio' }
    assert.equal(hostileFilter.mediaKind, 'audio')

    // @ts-expect-error OutputPlan e uniao fechada; um ramo de audio nao existe
    const audioPlan: OutputPlan = { schemaVersion: 1, projectId: 'p', catalogVersion: '1', profileId: 'p', profileRevision: 1, mediaKind: 'audio' }
    assert.equal(audioPlan.mediaKind, 'audio')
})
