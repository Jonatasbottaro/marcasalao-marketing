/**
 * Validacao do OutputPlan (R001-03) na camada de **semantica**: relatorio ecoado,
 * origem de cada diagnostico (preset interno vs requisito oficial vs contexto),
 * estados de aplicacao de regra e ausencia de coercione.
 *
 * A paridade de forma com o schema draft-07 fica em
 * `tests/contracts/output-plan-schema.test.ts`; este arquivo exercita o que so o
 * nucleo decide, incluindo os tipos de regra que o catalogo v1 instancia com
 * estado `informational` (e por isso precisam de um estado sintetico para provar
 * o caminho de erro).
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { test } from 'node:test'

import {
    OUTPUT_PLAN_ASPECT_RATIO_PATTERN,
    OUTPUT_PLAN_FPS_MAX,
    OUTPUT_PLAN_FPS_MIN,
    type OutputPlan,
} from '../src/output-plan-contract.js'
import { findOutputProfile } from '../src/output-profiles/catalog.js'
import type { OutputProfile, ProfileRuleReference, RuleContext } from '../src/output-profiles/types.js'
import {
    assessProfileRules,
    catalogProfileEcho,
    readOutputPlan,
    requiresInspectionFor,
    validateOutputPlan,
} from '../src/validate-output-plan.js'
import {
    catalogProfileRevision,
    catalogProject,
    imagePlanWith,
    outputPlanCodes,
    outputPlanWarningCodes,
    validateOutputPlanDocument,
    videoPlanWith,
} from './contract-harness.js'

function shortsProfileWith(rules: readonly ProfileRuleReference[]): OutputProfile {
    const profile = findOutputProfile('youtube-shorts')
    assert.notEqual(profile, null)
    return { ...(profile as OutputProfile), rules }
}

const PLAN_YOUTUBE_SHORTS = 'youtube-shorts'

test('o relatorio de um plano valido ecoa o documento e o catalogo, sem inventar nada', () => {
    const report = validateOutputPlanDocument(videoPlanWith({ ruleContext: 'studio-upload' }), catalogProject())

    assert.equal(report.valid, true, report.errors.map((error) => error.message).join(' | '))
    assert.deepEqual(outputPlanCodes(report), [])
    assert.equal(report.summary, 'Output plan is valid.')
    assert.equal(report.projectId, 'projeto-teste')
    assert.equal(report.profileId, PLAN_YOUTUBE_SHORTS)
    assert.equal(report.catalogVersion, '1')
    assert.equal(report.profileRevision, 3, 'shorts subiu de revisao com o escopo novo (R001-04) e com a pendencia promovida (R001-05)')
    assert.equal(report.mediaKind, 'video')
    assert.equal(report.ruleContext, 'studio-upload')
    assert.deepEqual(report.geometry, { width: 1080, height: 1920, aspectRatio: '9:16' })
    assert.equal(report.fps, 30)
    assert.deepEqual([...report.pendingRuleIds], ['P-YT-03'])
    assert.deepEqual([...report.requiresInspection], ['media-file', 'codec', 'bytes', 'audio-streams', 'publication'])

    // Duracao nao existe no plano: a regra R-YT-01 e declarada para o contexto, mas o
    // documento nao carrega o dado. O relatorio avisa; jamais afirma que a duracao passou.
    assert.deepEqual(outputPlanWarningCodes(report), ['OUTPUT_PLAN_RULE_NOT_ASSESSABLE'])
    assert.match(report.warnings[0]?.message ?? '', /nothing was verified/)
})

test('plano de imagem nao fabrica fps no relatorio nem no artefato lido', () => {
    const document = imagePlanWith({ ruleContext: 'in-app' })
    const report = validateOutputPlanDocument(document, catalogProject())

    assert.equal(report.valid, true, report.errors.map((error) => error.message).join(' | '))
    assert.equal(report.mediaKind, 'image')
    assert.equal(report.fps, null, 'fps de plano de imagem continua null, nunca 0')
    assert.deepEqual([...report.requiresInspection], ['media-file', 'image-format', 'bytes', 'publication'])
    assert.deepEqual(readOutputPlan(document)?.mediaKind, 'image')
    assert.equal('video' in (readOutputPlan(document) as object), false)

    assert.deepEqual([...requiresInspectionFor('image')], ['media-file', 'image-format', 'bytes', 'publication'])
    assert.deepEqual([...requiresInspectionFor('video')], ['media-file', 'codec', 'bytes', 'audio-streams', 'publication'])
})

test('contexto ausente nao avalia regra oficial condicionada e avisa sobre o alcance', () => {
    const report = validateOutputPlanDocument(videoPlanWith(), catalogProject())

    assert.equal(report.valid, true)
    assert.deepEqual(outputPlanWarningCodes(report), ['OUTPUT_PLAN_CONTEXT_NOT_DECLARED', 'OUTPUT_PLAN_CONTEXT_NOT_DECLARED'])
    assert.deepEqual(report.warnings.map((warning) => warning.path), ['ruleContext', 'ruleContext'])
    assert.match(report.warnings[0]?.message ?? '', /R-YT-01.*cannot be assessed because the document declares no context/)
    assert.match(report.warnings[1]?.message ?? '', /R-YT-02/)
    assert.match(report.warnings[0]?.message ?? '', /structural validity does not confirm an official requirement/)
    assert.equal(report.ruleContext, null)
})

test('contexto declarado fora do escopo da regra nao a aplica', () => {
    const report = validateOutputPlanDocument(videoPlanWith({ ruleContext: 'api-publishing' }), catalogProject())

    assert.equal(report.valid, true)
    assert.deepEqual(outputPlanWarningCodes(report), ['OUTPUT_PLAN_RULE_NOT_APPLIED', 'OUTPUT_PLAN_RULE_NOT_APPLIED'])
    assert.deepEqual(report.warnings.map((warning) => warning.path), ['rules[0]', 'rules[1]'])
    assert.match(report.warnings[0]?.message ?? '', /stated for context @in-app, @studio-upload, not for the declared @api-publishing/)
})

test('in-app pertence ao escopo de R-YT-01: o contexto declarado cumpre a avaliacao', () => {
    const inApp = validateOutputPlanDocument(videoPlanWith({ ruleContext: 'in-app' }), catalogProject())
    const studio = validateOutputPlanDocument(videoPlanWith({ ruleContext: 'studio-upload' }), catalogProject())

    assert.equal(inApp.valid, true)
    assert.equal(inApp.ruleContext, 'in-app')
    // O plano nao carrega duracao: R-YT-01 fica nao-avaliavel na camada de plano, e a
    // orientacao de R-YT-02 e avaliada a partir da geometria. O resultado tem de ser o
    // mesmo dos dois contextos do escopo -- uma definicao, nao uma tabela por contexto.
    assert.deepEqual(outputPlanWarningCodes(inApp), outputPlanWarningCodes(studio))
    assert.deepEqual(inApp.warnings.map((warning) => warning.path), ['video'])
    assert.match(inApp.warnings[0]?.message ?? '', /R-YT-01/)
})

test('ruleContext null e entrada invalida, e a avaliacao continua tratando o contexto como nao informado', () => {
    const report = validateOutputPlanDocument(videoPlanWith({ ruleContext: null }), catalogProject())

    assert.equal(report.valid, false)
    assert.deepEqual(outputPlanCodes(report), ['OUTPUT_PLAN_RULE_CONTEXT_INVALID'])
    assert.deepEqual(outputPlanWarningCodes(report), ['OUTPUT_PLAN_CONTEXT_NOT_DECLARED', 'OUTPUT_PLAN_CONTEXT_NOT_DECLARED'])
    assert.equal(report.ruleContext, null)
    assert.match(report.errors[0]?.message ?? '', /absence is an omitted key, never null/)
})

test('regra de contexto igual sem dado avaliavel vira nao-avaliabilidade, nao aprovacao', () => {
    const jpeg = validateOutputPlanDocument(imagePlanWith({
        profileId: 'instagram-feed-image-square',
        profileRevision: catalogProfileRevision('instagram-feed-image-square'),
        image: { width: 1080, height: 1080, aspectRatio: '1:1' },
        ruleContext: 'api-publishing',
    }), catalogProject())
    assert.equal(jpeg.valid, true)
    // R-IG-01 (formato) e R-IG-06 (faixa de proporcao e largura) sao exigencias
    // certificadas para o contexto declarado, e o plano nao e um arquivo: as duas
    // viram aviso de nao-avaliabilidade. R-IG-10 e do app, donc informational.
    assert.deepEqual(outputPlanWarningCodes(jpeg), [
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
        'OUTPUT_PLAN_RULE_INFORMATIONAL',
    ])
    assert.deepEqual(jpeg.warnings.map((warning) => warning.path), ['image', 'image', 'rules[2]'])
    assert.match(jpeg.warnings[0]?.message ?? '', /R-IG-01/)
    assert.match(jpeg.warnings[1]?.message ?? '', /R-IG-06/)

    const container = validateOutputPlanDocument(videoPlanWith({
        profileId: 'youtube-video-horizontal',
        profileRevision: catalogProfileRevision('youtube-video-horizontal'),
        video: { width: 1920, height: 1080, aspectRatio: '16:9', fps: 30 },
        ruleContext: 'studio-upload',
    }), catalogProject())
    assert.equal(container.valid, true)
    // R-YT-04 (contêiner recomendado), R-YT-05 (15 minutos) e R-YT-06 (256 GB / 12 h)
    // sao do contexto declarado e nao tem dado no plano; R-YT-07 e da Data API, ou
    // seja, de outro caminho.
    assert.deepEqual(outputPlanWarningCodes(container), [
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
        'OUTPUT_PLAN_RULE_NOT_APPLIED',
    ])
    assert.match(container.warnings[0]?.message ?? '', /R-YT-04/)
    assert.match(container.warnings[3]?.message ?? '', /R-YT-07/)
})

test('informational e not-applied nunca viram erro de plano', () => {
    const report = validateOutputPlanDocument(imagePlanWith({ ruleContext: 'in-app' }), catalogProject())

    assert.equal(report.valid, true, report.errors.map((error) => error.message).join(' | '))
    assert.deepEqual(outputPlanCodes(report), [])
    assert.deepEqual(outputPlanWarningCodes(report), [
        'OUTPUT_PLAN_RULE_NOT_APPLIED',
        'OUTPUT_PLAN_RULE_INFORMATIONAL',
        'OUTPUT_PLAN_RULE_INFORMATIONAL',
    ])
    assert.deepEqual(report.warnings.map((warning) => warning.path), ['rules[0]', 'rules[1]', 'rules[2]'])
    assert.match(report.warnings[0]?.message ?? '', /R-IG-07.*not for the declared @in-app; it is not applied/)
    assert.match(report.warnings[1]?.message ?? '', /R-IG-04.*is never a plan error/)
})

test('not-evaluated continua sendo aviso nomeado, mesmo com o contexto declarado', () => {
    // Depois da R001-05 nenhum perfil do catalogo usa este estado -- as aplicacoes que
    // ele protegia foram certificadas. Ele continua no contrato, entao o caminho e
    // exercitado por um estado sintetico: a avaliacao nao existe, e isso nunca vira
    // nem erro nem aprovacao.
    const assessment = assessProfileRules({
        profile: shortsProfileWith([{ ruleId: 'R-YT-01', state: 'not-evaluated' }]),
        ruleContext: 'studio-upload',
        scope: 'output-plan',
        facts: { path: 'video', geometry: { width: 1080, height: 1920, aspectRatio: '9:16' }, durationMs: null },
    })
    assert.deepEqual(assessment.errors, [])
    assert.deepEqual(assessment.warnings.map((warning) => warning.code), ['OUTPUT_PLAN_RULE_NOT_EVALUATED'])
    assert.match(assessment.warnings[0]?.message ?? '', /R-YT-01.*application is not evaluated/)
})

test('o estado de aplicacao domina sobre o contexto declarado', () => {
    // R-IG-07 e a exigencia certificada desta publicacao e R-IG-04/R-IG-05 sao do app:
    // nenhum contexto faz dessas regras erro de plano. Com api-publishing declarado,
    // R-IG-07 ate entra em avaliacao, mas o plano nao carrega arquivo: aviso, nao "ok".
    const expected: Record<RuleContext, readonly string[]> = {
        'in-app': ['OUTPUT_PLAN_RULE_NOT_APPLIED', 'OUTPUT_PLAN_RULE_INFORMATIONAL', 'OUTPUT_PLAN_RULE_INFORMATIONAL'],
        'api-publishing': [
            'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
            'OUTPUT_PLAN_RULE_INFORMATIONAL',
            'OUTPUT_PLAN_RULE_INFORMATIONAL',
        ],
        ads: ['OUTPUT_PLAN_RULE_NOT_APPLIED', 'OUTPUT_PLAN_RULE_INFORMATIONAL', 'OUTPUT_PLAN_RULE_INFORMATIONAL'],
        'studio-upload': [
            'OUTPUT_PLAN_RULE_NOT_APPLIED',
            'OUTPUT_PLAN_RULE_INFORMATIONAL',
            'OUTPUT_PLAN_RULE_INFORMATIONAL',
        ],
    }
    for (const context of ['in-app', 'api-publishing', 'ads', 'studio-upload'] as const) {
        const report = validateOutputPlanDocument(imagePlanWith({ ruleContext: context }), catalogProject())
        assert.equal(report.valid, true, `${context}: ${report.errors.map((error) => error.code).join(', ')}`)
        assert.deepEqual(outputPlanCodes(report), [], context)
        assert.deepEqual(outputPlanWarningCodes(report), expected[context], context)
    }
})

test('preset interno e requisito oficial tem codigos e mensagens separados', () => {
    const report = validateOutputPlanDocument(videoPlanWith({
        ruleContext: 'studio-upload',
        video: { width: 1920, height: 1080, aspectRatio: '16:9', fps: 25 },
    }), catalogProject())

    assert.equal(report.valid, false)
    assert.deepEqual(outputPlanCodes(report), [
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_FPS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_OFFICIAL_REQUIREMENT_VIOLATED',
    ])
    assert.deepEqual(report.errors.map((error) => error.path), [
        'video.width',
        'video.height',
        'video.aspectRatio',
        'video.fps',
        'video',
    ])
    assert.equal(report.summary, 'Output plan is invalid: 5 error(s).')

    const presetMessages = report.errors.slice(0, 4).map((error) => error.message)
    for (const message of presetMessages) {
        assert.match(message, /internal default/, `preset descrito sem origem interna: ${message}`)
        assert.doesNotMatch(message, /official rule/, `preset escrito como exigencia da rede: ${message}`)
    }
    assert.match(presetMessages[0] ?? '', /D-LOCAL-03/)
    assert.match(presetMessages[3] ?? '', /D-LOCAL-05/)

    const official = report.errors[4]
    assert.match(official?.message ?? '', /official rule "R-YT-02" @in-app, @studio-upload/, 'requisito oficial sem nomear a regra e os contextos do escopo')
    assert.doesNotMatch(official?.message ?? '', /internal default/)
})

test('o avaliador de regras decide pelo tipo de valor, estado e escopo, nao pela rede', () => {
    // Proporcao quadrada: o preset do Shorts e 9:16, mas a regra oficial aceita
    // quadrada ou vertical. As duas camadas continuam separadas.
    const square = assessProfileRules({
        profile: findOutputProfile(PLAN_YOUTUBE_SHORTS) as OutputProfile,
        ruleContext: 'studio-upload',
        scope: 'output-plan',
        facts: { path: 'video', geometry: { width: 1080, height: 1080, aspectRatio: '1:1' }, durationMs: null },
    })
    assert.deepEqual(square.errors, [])
    assert.deepEqual(square.warnings.map((warning) => warning.code), ['OUTPUT_PLAN_RULE_NOT_ASSESSABLE'])
    assert.match(square.warnings[0]?.message ?? '', /R-YT-01/, 'so a duracao falta; a orientacao foi avaliada e aceita')

    // Recomendação `applies`: aviso, nunca erro (o catalogo v1 nao instancia este
    // estado para R-IG-05, entao ele e montado aqui para exercitar o caminho).
    const recommendation = assessProfileRules({
        profile: shortsProfileWith([{ ruleId: 'R-IG-05', state: 'applies' }]),
        ruleContext: 'in-app',
        scope: 'output-plan',
        facts: { path: 'video', geometry: { width: 1080, height: 1080, aspectRatio: '1:1' }, durationMs: null },
    })
    assert.deepEqual(recommendation.errors, [])
    assert.deepEqual(recommendation.warnings.map((warning) => warning.code), ['OUTPUT_PLAN_RECOMMENDATION_NOT_MET'])
    assert.match(recommendation.warnings[0]?.message ?? '', /recommendation "R-IG-05" @in-app/)

    // Requisito de dimensao minima `applies`: erro nomeando a regra e o contexto.
    const minimum = assessProfileRules({
        profile: shortsProfileWith([{ ruleId: 'R-IG-04', state: 'applies' }]),
        ruleContext: 'in-app',
        scope: 'output-plan',
        facts: { path: 'video', geometry: { width: 640, height: 1136, aspectRatio: '9:16' }, durationMs: null },
    })
    assert.deepEqual(minimum.errors.map((error) => error.code), ['OUTPUT_PLAN_OFFICIAL_REQUIREMENT_VIOLATED'])
    assert.match(minimum.errors[0]?.message ?? '', /below the minimum 720x1280/)
    assert.deepEqual(minimum.warnings, [])

    // Duracao: avaliavel so na camada que tem a soma das cenas.
    const noDuration = assessProfileRules({
        profile: findOutputProfile(PLAN_YOUTUBE_SHORTS) as OutputProfile,
        ruleContext: 'studio-upload',
        scope: 'output-plan',
        facts: { path: 'video', geometry: null, durationMs: null },
    })
    assert.deepEqual(noDuration.errors, [])
    assert.deepEqual(noDuration.warnings.map((warning) => warning.code), [
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
        'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
    ], 'sem geometria nem duracao, as duas regras aplicaveis ficam sem avaliacao')
    assert.match(noDuration.warnings[0]?.message ?? '', /R-YT-01/)
    assert.match(noDuration.warnings[1]?.message ?? '', /R-YT-02/)

    const overDuration = assessProfileRules({
        profile: findOutputProfile(PLAN_YOUTUBE_SHORTS) as OutputProfile,
        ruleContext: 'studio-upload',
        scope: 'composition-output',
        facts: { path: 'scenes', geometry: null, durationMs: 180001 },
    })
    assert.deepEqual(overDuration.errors.map((error) => `${error.code} @${error.path}`), ['OUTPUT_COMPAT_DURATION_EXCEEDED @scenes'])

    // Na camada de saida, o que o plano ja cobriu fica em silencio: sem
    // duplicar diagnostico entre relatorio embutido e relatorio de compatibilidade.
    const silent = assessProfileRules({
        profile: findOutputProfile(PLAN_YOUTUBE_SHORTS) as OutputProfile,
        ruleContext: 'studio-upload',
        scope: 'composition-output',
        facts: { path: 'scenes', geometry: { width: 1920, height: 1080, aspectRatio: '16:9' }, durationMs: 60000 },
    })
    assert.deepEqual(silent.errors, [], 'regra de geometria reavaliada na camada errada')
})

test('o validador nao coage tipos nem preenche defaults ausentes', () => {
    const hostile = videoPlanWith({
        schemaVersion: '1',
        projectId: 'Projeto Teste',
        profileRevision: 1.5,
        extra: true,
        video: { width: '1080', height: 1920, aspectRatio: 916, fps: 30 },
    })
    const report = validateOutputPlanDocument(hostile, catalogProject())

    assert.equal(report.valid, false)
    assert.deepEqual(outputPlanCodes(report), [
        'OUTPUT_PLAN_UNKNOWN_FIELD',
        'OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED',
        'OUTPUT_PLAN_PROJECT_ID_INVALID',
        'OUTPUT_PLAN_PROFILE_REVISION_INVALID',
        'OUTPUT_PLAN_DIMENSIONS_INVALID',
        'OUTPUT_PLAN_ASPECT_RATIO_INVALID',
    ])
    assert.deepEqual(report.geometry, null, 'geometria parcial nao e preenchida por coercione')
    assert.equal(report.fps, 30)
    assert.deepEqual(outputPlanWarningCodes(report), ['OUTPUT_PLAN_CONTEXT_NOT_DECLARED', 'OUTPUT_PLAN_CONTEXT_NOT_DECLARED'])

    for (const missing of [
        { name: 'schemaVersion ausente', document: videoPlanWith({ schemaVersion: undefined }), code: 'OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED' },
        { name: 'aspectRatio ausente', document: imagePlanWith({ image: { width: 1080, height: 1920 } }), code: 'OUTPUT_PLAN_ASPECT_RATIO_INVALID' },
        { name: 'fps ausente', document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16' } }), code: 'OUTPUT_PLAN_FPS_INVALID' },
        { name: 'payload ausente', document: videoPlanWith({ video: undefined }), code: 'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH' },
    ]) {
        const codes = outputPlanCodes(validateOutputPlanDocument(missing.document, catalogProject()))
        assert.ok(codes.includes(missing.code), `${missing.name}: esperado ${missing.code}, obtido ${codes.join(', ')}`)
    }

    assert.equal(OUTPUT_PLAN_FPS_MIN, 1)
    assert.equal(OUTPUT_PLAN_FPS_MAX, 120)
    assert.equal(OUTPUT_PLAN_ASPECT_RATIO_PATTERN.test('9:16'), true)
    assert.equal(OUTPUT_PLAN_ASPECT_RATIO_PATTERN.test('09:16'), true)
    assert.equal(OUTPUT_PLAN_ASPECT_RATIO_PATTERN.test('9:16:9'), false)
})

test('a relacao com projeto e catalogo tem ordem fixa e motivo proprio', () => {
    const report = validateOutputPlanDocument(videoPlanWith({
        projectId: 'outro-projeto',
        catalogVersion: '2',
        profileId: 'instagram-reels-video',
        profileRevision: catalogProfileRevision('instagram-reels-video'),
        video: { width: 1920, height: 1080, aspectRatio: '16:9', fps: 25 },
    }), catalogProject({ outputProfiles: ['youtube-video-horizontal'] }))

    assert.deepEqual(outputPlanCodes(report), [
        'OUTPUT_PLAN_CATALOG_VERSION_UNKNOWN',
        'OUTPUT_PROFILE_NOT_ALLOWED',
        'OUTPUT_PLAN_PROJECT_MISMATCH',
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        'OUTPUT_PLAN_FPS_NOT_IN_CATALOG',
    ])
    assert.equal(report.fps, 25, 'o relatorio ecoa o que o documento declara, nao o preset')
    assert.equal(report.profileId, 'instagram-reels-video')
})

test('manifesto invalido derruba a relacao sem reemitir os codigos do validador de projeto', () => {
    const brokenProject = catalogProject({ outputProfiles: 'youtube-shorts' })
    const report = validateOutputPlanDocument(videoPlanWith(), brokenProject)

    assert.equal(report.valid, false)
    assert.deepEqual(outputPlanCodes(report), ['OUTPUT_PROJECT_INVALID'])
    assert.match(report.errors[0]?.message ?? '', /invalid: \d+ error\(s\)/)
    for (const error of report.errors) {
        assert.doesNotMatch(error.code, /^PROJECT_/, `codigo do validador de projeto vazou: ${error.code}`)
    }
    assert.equal(report.projectId, null)
    assert.deepEqual([...report.pendingRuleIds], ['P-YT-03'], 'as pendencias do perfil continuam visiveis')
})

test('perfil inexistente no catalogo impede preset e regras', () => {
    const report = validateOutputPlanDocument(videoPlanWith({ profileId: 'twitter-spaces' }), catalogProject())
    assert.deepEqual(outputPlanCodes(report), ['OUTPUT_PROFILE_UNKNOWN'])
    assert.deepEqual([...report.pendingRuleIds], [])
    assert.deepEqual([...report.requiresInspection], [])
})

test('o eco do catalogo para um perfil resolvido e o mesmo do plano construido', () => {
    const echo = catalogProfileEcho(findOutputProfile(PLAN_YOUTUBE_SHORTS) as OutputProfile)
    assert.deepEqual(echo, {
        catalogVersion: '1',
        profileId: PLAN_YOUTUBE_SHORTS,
        profileRevision: 3,
        mediaKind: 'video',
        geometry: { width: 1080, height: 1920, aspectRatio: '9:16' },
        fps: 30,
        pendingRuleIds: ['P-YT-03'],
        requiresInspection: ['media-file', 'codec', 'bytes', 'audio-streams', 'publication'],
    })
})

test('readOutputPlan so devolve artefato bem formado', () => {
    assert.equal(readOutputPlan(null), null)
    assert.equal(readOutputPlan([]), null)
    assert.equal(readOutputPlan('plano'), null)
    assert.equal(readOutputPlan(videoPlanWith({ video: undefined })), null)
    assert.equal(readOutputPlan(videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, duration: 5 } })), null)
    assert.equal(readOutputPlan(videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: '30' } })), null)

    const artifact = readOutputPlan(videoPlanWith({ ruleContext: 'studio-upload' })) as OutputPlan
    assert.equal(artifact.mediaKind, 'video')
    assert.equal(artifact.video?.fps, 30)
    assert.equal('image' in artifact, false)
})

test('o validador nao muta a entrada e repete o mesmo JSON byte a byte', () => {
    const document = videoPlanWith({ ruleContext: 'studio-upload' })
    const project = catalogProject()
    const before = JSON.stringify([document, project])
    const digests = new Set<string>()

    for (let run = 0; run < 3; run += 1) {
        digests.add(createHash('sha256').update(JSON.stringify(validateOutputPlan(document, project))).digest('hex'))
    }

    assert.equal(digests.size, 1)
    assert.equal(JSON.stringify([document, project]), before, 'entrada mutada pela validacao')
})

test('uma rejeicao nao contamina a validacao seguinte', () => {
    const project = catalogProject()
    assert.equal(validateOutputPlan(videoPlanWith({ profileRevision: 7 }), project).valid, false)
    assert.equal(validateOutputPlan(videoPlanWith(), project).valid, true)
    assert.equal(validateOutputPlan(videoPlanWith({ mediaKind: 'image' }), project).valid, false)
    assert.equal(validateOutputPlan(videoPlanWith(), project).valid, true)
})

test('validateOutputPlan devolve relatorio, nao plano', () => {
    // @ts-expect-error o contrato devolve OutputPlanReport; pegar um plano daqui seria reinterpretar diagnostico em artefato
    const comoPlano: OutputPlan = validateOutputPlan(videoPlanWith(), catalogProject())
    assert.equal(typeof comoPlano, 'object')
})
