/**
 * Compatibilidade Composition v1 x OutputPlan (R001-03).
 *
 * A camada nao reimplementa regra nenhuma: os dois relatorios embutidos tem de
 * ser **byte a byte** os mesmos que `validateComposition` e `validateOutputPlan`
 * produzem sozinhos, e os codigos proprios desta camada so existem quando as duas
 * camadas anteriores aceitaram os documentos.
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { test } from 'node:test'

import { resolveOutputPlan } from '../src/resolve-output-profile.js'
import { validateComposition } from '../src/validate-composition.js'
import { validateCompositionForOutputPlan } from '../src/validate-composition-output.js'
import { validateOutputPlan } from '../src/validate-output-plan.js'
import type { OutputCompatibilityReport } from '../src/validation-report.js'
import {
    catalogProject,
    compositionWithScenes,
    officialPairs,
    projectWith,
    readCompositionExample,
    readProjectExample,
    sceneWith,
    videoPlanWith,
} from './contract-harness.js'

const PROJECT = catalogProject()

function outputComposition(overrides: Record<string, unknown> = {}, durations: readonly number[] = [90000, 90000]): Record<string, unknown> {
    return compositionWithScenes(
        durations.map((durationMs, index) => sceneWith({ id: `cena-${index + 1}`, durationMs })),
        {
            projectId: 'projeto-teste',
            id: 'comp-output',
            title: 'Composicao Output',
            format: { profile: 'youtube-shorts', width: 1080, height: 1920, fps: 30 },
            ...overrides,
        },
    )
}

function shortsPlan(context?: 'in-app' | 'api-publishing' | 'ads' | 'studio-upload'): Record<string, unknown> {
    const resolution = resolveOutputPlan(PROJECT, 'youtube-shorts', context === undefined ? undefined : { ruleContext: context })
    assert.notEqual(resolution.plan, null, 'plano de teste nao resolveu')
    return resolution.plan as unknown as Record<string, unknown>
}

function codesOf(report: OutputCompatibilityReport): string[] {
    return report.errors.map((error) => error.code)
}

function pathsOf(report: OutputCompatibilityReport): string[] {
    return report.errors.map((error) => error.path)
}

test('composicao declarando 180000 ms no contexto certificado e compativel', () => {
    const composition = outputComposition({}, [90000, 90000])
    const plan = shortsPlan('studio-upload')
    const report = validateCompositionForOutputPlan(composition, PROJECT, plan)

    assert.equal(report.valid, true, report.errors.map((error) => `${error.code} @${error.path}: ${error.message}`).join(' | '))
    assert.deepEqual(report.errors, [])
    assert.deepEqual(report.warnings, [])
    assert.equal(report.summary, 'Composition is compatible with the output plan.')
    assert.equal(report.compositionId, 'comp-output')
    assert.equal(report.profileId, 'youtube-shorts')
    assert.equal(report.ruleContext, 'studio-upload')
    assert.equal(report.totalDurationMs, 180000)

    // Delegacao pura: os relatorios embutidos sao os das proprias funcoes.
    assert.deepEqual(report.compositionReport, validateComposition(composition, PROJECT))
    assert.deepEqual(report.planReport, validateOutputPlan(plan, PROJECT))
})

test('composicao declarando 180001 ms estoura a regra de duracao no contexto certificado', () => {
    const report = validateCompositionForOutputPlan(outputComposition({}, [90000, 90001]), PROJECT, shortsPlan('studio-upload'))

    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_DURATION_EXCEEDED'])
    assert.deepEqual(pathsOf(report), ['scenes'])
    assert.equal(report.totalDurationMs, 180001)
    assert.match(report.errors[0]?.message ?? '', /Declared scene total of 180001 ms exceeds 180 s/)
    assert.match(report.errors[0]?.message ?? '', /official rule "R-YT-01"/)
    // A mesma definicao e citada nos dois contextos do escopo; nao ha tabela por contexto.
    assert.match(report.errors[0]?.message ?? '', /@in-app, @studio-upload/)
    // A soma declarada nao e duracao de arquivo: a inspecao continua pendente.
    assert.deepEqual([...report.planReport?.requiresInspection ?? []], ['media-file', 'codec', 'bytes', 'audio-streams', 'publication'])
})

test('o contexto in-app esta no escopo de R-YT-01: 180000 ms e compativel sem aviso de contexto', () => {
    const report = validateCompositionForOutputPlan(outputComposition({}, [90000, 90000]), PROJECT, shortsPlan('in-app'))

    assert.equal(report.valid, true, report.errors.map((error) => `${error.code} @${error.path}: ${error.message}`).join(' | '))
    assert.deepEqual(report.errors, [])
    assert.deepEqual(report.warnings, [], 'in-app pertence ao escopo da regra: nada fica com aplicacao pendente de contexto')
    assert.equal(report.ruleContext, 'in-app')
    assert.equal(report.totalDurationMs, 180000)
})

test('180001 ms no contexto in-app estoura a mesma definicao de R-YT-01', () => {
    const report = validateCompositionForOutputPlan(outputComposition({}, [90000, 90001]), PROJECT, shortsPlan('in-app'))

    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_DURATION_EXCEEDED'])
    assert.deepEqual(pathsOf(report), ['scenes'])
    assert.equal(report.totalDurationMs, 180001)
    assert.match(report.errors[0]?.message ?? '', /Declared scene total of 180001 ms exceeds 180 s/)
    assert.match(report.errors[0]?.message ?? '', /official rule "R-YT-01"/)
    // Comparado com o mesmo documento em studio-upload, so o contexto na mensagem muda.
    const studio = validateCompositionForOutputPlan(outputComposition({}, [90000, 90001]), PROJECT, shortsPlan('studio-upload'))
    assert.equal(
        report.errors[0]?.message.replace('@in-app, @studio-upload', '@CONTEXT'),
        studio.errors[0]?.message.replace('@in-app, @studio-upload', '@CONTEXT'),
        'a regra aplicada em outro contexto nao pode ser outra definicao',
    )
})

test('sem contexto declarado a mesma composicao continua valida e o aviso diz o alcance', () => {
    const report = validateCompositionForOutputPlan(outputComposition({}, [90000, 90001]), PROJECT, shortsPlan())

    assert.equal(report.valid, true, 'regra oficial condicional nao se avalia sem contexto')
    assert.equal(report.ruleContext, null)
    assert.deepEqual(report.warnings.map((warning) => warning.code), ['OUTPUT_PLAN_CONTEXT_NOT_DECLARED'])
    assert.equal(report.warnings[0]?.path, 'ruleContext')
    assert.match(report.warnings[0]?.message ?? '', /R-YT-01/)
    // O plano embutido carrega os dois avisos; a camada de saida avalia so duracao.
    assert.deepEqual(report.planReport?.warnings.map((warning) => warning.code), [
        'OUTPUT_PLAN_CONTEXT_NOT_DECLARED',
        'OUTPUT_PLAN_CONTEXT_NOT_DECLARED',
    ])
    assert.deepEqual(codesOf(report), [])
})

test('contexto de fato fora do escopo da regra nao a aplica', () => {
    const report = validateCompositionForOutputPlan(outputComposition({}, [90000, 90001]), PROJECT, shortsPlan('api-publishing'))

    assert.equal(report.valid, true)
    assert.equal(report.ruleContext, 'api-publishing')
    assert.deepEqual(report.warnings.map((warning) => warning.code), ['OUTPUT_PLAN_RULE_NOT_APPLIED'])
    assert.match(report.warnings[0]?.message ?? '', /stated for context @in-app, @studio-upload, not for the declared @api-publishing/)
    assert.deepEqual(codesOf(report), [])
})

test('perfil, dimensoes e frame rate divergentes tem cada um o seu codigo', () => {
    const plan = shortsPlan('studio-upload')

    const profile = validateCompositionForOutputPlan(outputComposition({ format: { profile: 'facebook-reels-video', width: 1080, height: 1920, fps: 30 } }), PROJECT, plan)
    assert.deepEqual(codesOf(profile), ['OUTPUT_COMPAT_PROFILE_MISMATCH'])
    assert.deepEqual(pathsOf(profile), ['format.profile'])
    assert.match(profile.errors[0]?.message ?? '', /"facebook-reels-video" is not the plan profile "youtube-shorts"/)

    const dimensions = validateCompositionForOutputPlan(outputComposition({ format: { profile: 'youtube-shorts', width: 1920, height: 1080, fps: 30 } }), PROJECT, plan)
    assert.deepEqual(codesOf(dimensions), ['OUTPUT_COMPAT_DIMENSIONS_MISMATCH'])
    assert.deepEqual(pathsOf(dimensions), ['format.width'])
    assert.match(dimensions.errors[0]?.message ?? '', /composition\.format is 1920x1080, the plan preset is 1080x1920/)

    const fps = validateCompositionForOutputPlan(outputComposition({ format: { profile: 'youtube-shorts', width: 1080, height: 1920, fps: 25 } }), PROJECT, plan)
    assert.deepEqual(codesOf(fps), ['OUTPUT_COMPAT_FPS_MISMATCH'])
    assert.deepEqual(pathsOf(fps), ['format.fps'])
    assert.match(fps.errors[0]?.message ?? '', /composition\.format\.fps 25 is not the plan preset fps 30/)

    const allThree = validateCompositionForOutputPlan(
        outputComposition({ format: { profile: 'facebook-stories-video', width: 720, height: 1280, fps: 24 } }, [3000]),
        PROJECT,
        shortsPlan('studio-upload'),
    )
    assert.deepEqual(codesOf(allThree), [
        'OUTPUT_COMPAT_PROFILE_MISMATCH',
        'OUTPUT_COMPAT_DIMENSIONS_MISMATCH',
        'OUTPUT_COMPAT_FPS_MISMATCH',
    ])
    assert.equal(allThree.totalDurationMs, 3000)
})

test('plano de imagem e recusado sem fabricar frame rate', () => {
    const imagePlan = resolveOutputPlan(PROJECT, 'instagram-stories-image', { ruleContext: 'in-app' })
    assert.notEqual(imagePlan.plan, null)

    const report = validateCompositionForOutputPlan(outputComposition({}, [3000]), PROJECT, imagePlan.plan as unknown as Record<string, unknown>)
    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_IMAGE_NO_COMPOSITION'])
    assert.deepEqual(pathsOf(report), ['mediaKind'])
    assert.match(report.errors[0]?.message ?? '', /never fabricates fps/)
    assert.equal(report.planReport?.fps, null)
    assert.equal(report.totalDurationMs, 3000, 'a composicao e valida; o que nao existe e a comparacao')
    assert.deepEqual(report.warnings, [], 'as regras do plano de imagem ficam no relatorio embutido')
})

test('camada nenhuma reescreve a outra: composicao invalida interrompe a comparacao', () => {
    const composition = outputComposition({}, [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER])
    const report = validateCompositionForOutputPlan(composition, PROJECT, shortsPlan('studio-upload'))

    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_COMPOSITION_INVALID'])
    assert.equal(report.totalDurationMs, null, 'duracao em overflow nao vira numero no relatorio de compatibilidade')
    assert.deepEqual(report.planReport, validateOutputPlan(shortsPlan('studio-upload'), PROJECT), 'o plano continua reportado mesmo sem comparacao')
    assert.deepEqual(report.compositionReport?.errors.map((error) => error.code), ['COMPOSITION_DURATION_OVERFLOW'])
    assert.deepEqual(report.warnings, [], 'sem comparacao nao ha avaliacao de regra')
})

test('plano invalido tambem interrompe a comparacao, e as duas causas cabem no mesmo relatorio', () => {
    const brokenPlan = videoPlanWith({ profileRevision: 9 })
    const planReport = validateOutputPlan(brokenPlan, PROJECT)
    assert.equal(planReport.valid, false)

    const report = validateCompositionForOutputPlan(outputComposition({}, [3000]), PROJECT, brokenPlan)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_PLAN_INVALID'])
    assert.deepEqual(pathsOf(report), ['plan'])
    assert.match(report.errors[0]?.message ?? '', /rejected before comparison: 1 error\(s\)/)
    assert.deepEqual(report.planReport, planReport)
    assert.equal(report.profileId, 'youtube-shorts')

    const both = validateCompositionForOutputPlan(
        outputComposition({ format: { profile: 'perfil-desconhecido', width: 1080, height: 1920, fps: 30 } }, [3000]),
        PROJECT,
        videoPlanWith({ video: { width: 0, height: 0, aspectRatio: 'x', fps: 0 } }),
    )
    assert.deepEqual(codesOf(both), ['OUTPUT_COMPAT_COMPOSITION_INVALID', 'OUTPUT_COMPAT_PLAN_INVALID'])
    assert.equal(both.totalDurationMs, null)
    assert.deepEqual(both.warnings, [])
})

test('projeto que nao permite o perfil do plano rejeita so o plano', () => {
    const project = catalogProject({ outputProfiles: ['instagram-reels-video'] })
    const composition = outputComposition({
        format: { profile: 'instagram-reels-video', width: 1080, height: 1920, fps: 30 },
    }, [3000])
    const report = validateCompositionForOutputPlan(composition, project, shortsPlan('studio-upload'))

    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_PLAN_INVALID'])
    assert.equal(report.compositionReport?.valid, true, 'a composicao em si nao e o problema')
    assert.deepEqual(report.planReport?.errors.map((error) => error.code), ['OUTPUT_PROFILE_NOT_ALLOWED'])
})

test('os exemplos oficiais e o perfil generico legado continuam validos na v1', () => {
    const legacyProject = projectWith({ outputProfiles: ['vertical-social'] })
    const legacyComposition = compositionWithScenes([sceneWith()], {
        format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
    })
    assert.equal(validateComposition(legacyComposition, legacyProject).valid, true, 'o perfil generico legado continua aceito')

    const plan = shortsPlan('studio-upload')
    const report = validateCompositionForOutputPlan(legacyComposition, legacyProject, plan)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_PLAN_INVALID'])
    // Um unico motivo, e nenhum deles uma regra nova sobre a Composition: o perfil
    // do plano nao esta na allowlist daquele manifesto.
    assert.deepEqual(report.planReport?.errors.map((error) => error.code), ['OUTPUT_PROFILE_NOT_ALLOWED'])
    assert.equal(report.compositionReport?.valid, true)

    for (const pair of officialPairs) {
        const exampleComposition = readCompositionExample(pair.composition)
        const exampleProject = readProjectExample(pair.project)
        assert.equal(validateComposition(exampleComposition, exampleProject).valid, true, pair.composition)
        const exampleReport = validateCompositionForOutputPlan(exampleComposition, exampleProject, plan)
        assert.deepEqual(codesOf(exampleReport), ['OUTPUT_COMPAT_PLAN_INVALID'], pair.composition)
        assert.equal(exampleReport.compositionReport?.valid, true, pair.composition)
        // O plano de teste pertence a outro projeto: allowlist e vinculo, nada alem.
        assert.deepEqual(exampleReport.planReport?.errors.map((error) => error.code), [
            'OUTPUT_PROFILE_NOT_ALLOWED',
            'OUTPUT_PLAN_PROJECT_MISMATCH',
        ], pair.composition)
    }
})

test('manifesto invalido: as causas ficam nos relatorios embutidos, nao repetidas no topo', () => {
    const brokenProject = { ...PROJECT, outputProfiles: 'youtube-shorts' }
    const report = validateCompositionForOutputPlan(outputComposition({}, [3000]), brokenProject, shortsPlan('studio-upload'))

    assert.equal(report.valid, false)
    assert.deepEqual(codesOf(report), ['OUTPUT_COMPAT_COMPOSITION_INVALID', 'OUTPUT_COMPAT_PLAN_INVALID'])
    assert.match(report.errors[0]?.message ?? '', /1 error\(s\)/)
    assert.deepEqual(report.compositionReport?.errors.map((error) => error.code), ['COMPOSITION_MANIFEST_INVALID'])
    assert.deepEqual(report.planReport?.errors.map((error) => error.code), ['OUTPUT_PROJECT_INVALID'])
    assert.equal(report.totalDurationMs, null)
    for (const error of report.errors) {
        assert.doesNotMatch(error.code, /^PROJECT_/, `codigo do validador de projeto vazou: ${error.code}`)
    }
})

test('o veredicto nao depende do estado de chamadas anteriores', () => {
    const composition = outputComposition({}, [90000, 90001])
    const plan = shortsPlan('studio-upload')

    assert.equal(validateCompositionForOutputPlan('nada', PROJECT, plan).valid, false)
    assert.equal(validateCompositionForOutputPlan(composition, PROJECT, videoPlanWith({ profileId: 'inexistente' })).valid, false)
    assert.equal(validateCompositionForOutputPlan(composition, PROJECT, plan).valid, false, 'estouro de duracao continua estouro')
    assert.equal(validateCompositionForOutputPlan(outputComposition({}, [90000, 90000]), PROJECT, plan).valid, true)
    assert.equal(validateCompositionForOutputPlan(composition, PROJECT, plan).valid, false)
})

test('entrada imutavel e saida identica em cinco execucoes', () => {
    const composition = outputComposition({}, [90000, 90001])
    const plan = shortsPlan('studio-upload')
    const project = catalogProject()
    const before = JSON.stringify([composition, project, plan])
    const digests = new Set<string>()

    for (let run = 0; run < 5; run += 1) {
        digests.add(createHash('sha256').update(JSON.stringify(validateCompositionForOutputPlan(composition, project, plan))).digest('hex'))
    }

    assert.equal(digests.size, 1, 'relatorios de compatibilidade divergem entre execucoes identicas')
    assert.equal(JSON.stringify([composition, project, plan]), before)
})

test('o relatorio nao expoe campo alem do contratado', () => {
    const report = validateCompositionForOutputPlan(outputComposition({}, [3000]), PROJECT, shortsPlan('studio-upload'))
    assert.deepEqual(Object.keys(report), [
        'valid',
        'errors',
        'warnings',
        'summary',
        'compositionId',
        'profileId',
        'ruleContext',
        'totalDurationMs',
        'compositionReport',
        'planReport',
    ])
    assert.equal(report.planReport?.profileId, 'youtube-shorts')
    assert.equal(report.compositionReport?.compositionId, 'comp-output')
})
