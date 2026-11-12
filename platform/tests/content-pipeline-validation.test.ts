/**
 * Testes unitarios da validacao consolidada do pipeline criativo
 * (`validateContentPipeline`).
 *
 * Cobre: pipeline valido, matriz de bloqueio (DAG de dependencias), propagacao
 * de relatorios originais, agregacao ordenada de erros e warnings, determinismo,
 * imutabilidade e barreiras estaticas de pureza.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    PIPELINE_VALID_SUMMARY,
    type ContentPipelineValidationInput,
} from '../src/content-pipeline-validation-contract.js'
import { validateContentPipeline } from '../src/validate-content-pipeline.js'
import { moduleRoot } from './contract-harness.js'

function readJsonExample(relativePath: string): unknown {
    const fullPath = path.join(moduleRoot, relativePath)
    return JSON.parse(readFileSync(fullPath, 'utf8')) as unknown
}

function validPipelineInput(): ContentPipelineValidationInput {
    return {
        project: readJsonExample('examples/projects/marca-salao-social.project.json'),
        composition: readJsonExample('examples/compositions/marca-salao-social-reel.composition.json'),
        outputPlan: readJsonExample('examples/output-plans/instagram-reels-video.output-plan.json'),
        beatPlan: readJsonExample('examples/pipelines/marca-salao-social-reel.beat-plan.json'),
    }
}

test('pipeline valido: todos os estagios valid, relatorios preservados e zero erros', () => {
    const input = validPipelineInput()
    const report = validateContentPipeline(input)

    assert.equal(report.valid, true)
    assert.equal(report.summary, PIPELINE_VALID_SUMMARY)
    assert.equal(report.schemaVersion, 1)
    assert.equal(report.projectId, 'marca-salao')
    assert.equal(report.compositionId, 'social-reel-example')
    assert.equal(report.outputPlanId, 'instagram-reels-video')
    assert.equal(report.beatPlanId, 'social-reel-beat-plan')

    assert.equal(report.errors.length, 0)
    assert.deepEqual(report.blockedStages, [])
    assert.deepEqual(report.completedStages, [
        'project',
        'composition',
        'output-plan',
        'output-compatibility',
        'beat-plan',
    ])

    assert.equal(report.stages.length, 5)
    for (const stage of report.stages) {
        assert.equal(stage.status, 'valid')
        assert.equal(stage.blockedBy, null)
        assert.ok(stage.report !== null)
        assert.equal(stage.report.valid, true)
    }
})

test('project invalido: bloqueia todos os estagios dependentes com blockedBy project', () => {
    const base = validPipelineInput()
    const input = {
        ...base,
        project: { invalid: true },
    }

    const report = validateContentPipeline(input)

    assert.equal(report.valid, false)
    assert.ok(report.errors.length > 0)
    assert.equal(report.errors[0]?.stage, 'project')

    assert.deepEqual(report.completedStages, ['project'])
    assert.deepEqual(report.blockedStages, [
        'composition',
        'output-plan',
        'output-compatibility',
        'beat-plan',
    ])

    const projectStage = report.stages.find((s) => s.stage === 'project')
    assert.equal(projectStage?.status, 'invalid')
    assert.ok(projectStage?.report !== null)

    for (const stageName of ['composition', 'output-plan', 'output-compatibility', 'beat-plan'] as const) {
        const stage = report.stages.find((s) => s.stage === stageName)
        assert.equal(stage?.status, 'blocked')
        assert.equal(stage?.report, null)
        assert.equal(stage?.blockedBy, 'project')
    }

    // Erros devem vir exclusivamente de project, sem erros sinteticos duplicados
    for (const error of report.errors) {
        assert.equal(error.stage, 'project')
    }
})

test('composition invalida: compatibilidade e beat-plan bloqueados; output-plan validado', () => {
    const base = validPipelineInput()
    const input = {
        ...base,
        composition: { invalid: 'composition' },
    }

    const report = validateContentPipeline(input)

    assert.equal(report.valid, false)

    const projectStage = report.stages.find((s) => s.stage === 'project')
    assert.equal(projectStage?.status, 'valid')

    const compStage = report.stages.find((s) => s.stage === 'composition')
    assert.equal(compStage?.status, 'invalid')
    assert.ok(compStage?.report !== null)

    const outputPlanStage = report.stages.find((s) => s.stage === 'output-plan')
    assert.equal(outputPlanStage?.status, 'valid')
    assert.ok(outputPlanStage?.report !== null)

    const compatStage = report.stages.find((s) => s.stage === 'output-compatibility')
    assert.equal(compatStage?.status, 'blocked')
    assert.equal(compatStage?.report, null)
    assert.equal(compatStage?.blockedBy, 'composition')

    const beatPlanStage = report.stages.find((s) => s.stage === 'beat-plan')
    assert.equal(beatPlanStage?.status, 'blocked')
    assert.equal(beatPlanStage?.report, null)
    assert.equal(beatPlanStage?.blockedBy, 'composition')

    assert.deepEqual(report.completedStages, ['project', 'composition', 'output-plan'])
    assert.deepEqual(report.blockedStages, ['output-compatibility', 'beat-plan'])
})

test('output-plan invalido: compatibilidade bloqueada; beat-plan executado normalmente', () => {
    const base = validPipelineInput()
    const input = {
        ...base,
        outputPlan: { invalid: 'outputPlan' },
    }

    const report = validateContentPipeline(input)

    assert.equal(report.valid, false)

    const projectStage = report.stages.find((s) => s.stage === 'project')
    assert.equal(projectStage?.status, 'valid')

    const compStage = report.stages.find((s) => s.stage === 'composition')
    assert.equal(compStage?.status, 'valid')

    const outputPlanStage = report.stages.find((s) => s.stage === 'output-plan')
    assert.equal(outputPlanStage?.status, 'invalid')
    assert.ok(outputPlanStage?.report !== null)

    const compatStage = report.stages.find((s) => s.stage === 'output-compatibility')
    assert.equal(compatStage?.status, 'blocked')
    assert.equal(compatStage?.report, null)
    assert.equal(compatStage?.blockedBy, 'output-plan')

    // BeatPlan pode continuar se composition e project forem validos
    const beatPlanStage = report.stages.find((s) => s.stage === 'beat-plan')
    assert.equal(beatPlanStage?.status, 'valid')
    assert.ok(beatPlanStage?.report !== null)

    assert.deepEqual(report.completedStages, ['project', 'composition', 'output-plan', 'beat-plan'])
    assert.deepEqual(report.blockedStages, ['output-compatibility'])
})

test('compatibilidade invalida: compatibilidade invalid; beat-plan executado', () => {
    const base = validPipelineInput()
    // Plano de Facebook Reels e valido para o projeto marca-salao, mas incompativel com a composition de Instagram Reels
    const incompatiblePlan = readJsonExample('examples/output-plans/facebook-reels-video.output-plan.json')
    const input = {
        ...base,
        outputPlan: incompatiblePlan,
    }

    const report = validateContentPipeline(input)

    assert.equal(report.valid, false)

    // Project, composition e output-plan sao individualmente validos
    assert.equal(report.stages.find((s) => s.stage === 'project')?.status, 'valid')
    assert.equal(report.stages.find((s) => s.stage === 'composition')?.status, 'valid')
    assert.equal(report.stages.find((s) => s.stage === 'output-plan')?.status, 'valid')

    const compatStage = report.stages.find((s) => s.stage === 'output-compatibility')
    assert.equal(compatStage?.status, 'invalid')
    assert.ok(compatStage?.report !== null)
    assert.equal(compatStage?.report?.valid, false)
    assert.ok(report.errors.some((e) => e.stage === 'output-compatibility'))

    // BeatPlan continuou executado e valido
    const beatPlanStage = report.stages.find((s) => s.stage === 'beat-plan')
    assert.equal(beatPlanStage?.status, 'valid')
    assert.ok(beatPlanStage?.report !== null)

    assert.deepEqual(report.completedStages, [
        'project',
        'composition',
        'output-plan',
        'output-compatibility',
        'beat-plan',
    ])
    assert.deepEqual(report.blockedStages, [])
})

test('beat-plan invalido: estagios anteriores validos; beat-plan invalid', () => {
    const base = validPipelineInput()
    const input = {
        ...base,
        beatPlan: { invalid: 'beatPlan' },
    }

    const report = validateContentPipeline(input)

    assert.equal(report.valid, false)

    assert.equal(report.stages.find((s) => s.stage === 'project')?.status, 'valid')
    assert.equal(report.stages.find((s) => s.stage === 'composition')?.status, 'valid')
    assert.equal(report.stages.find((s) => s.stage === 'output-plan')?.status, 'valid')
    assert.equal(report.stages.find((s) => s.stage === 'output-compatibility')?.status, 'valid')

    const beatPlanStage = report.stages.find((s) => s.stage === 'beat-plan')
    assert.equal(beatPlanStage?.status, 'invalid')
    assert.ok(beatPlanStage?.report !== null)
    assert.equal(beatPlanStage?.report?.valid, false)

    assert.deepEqual(report.completedStages, [
        'project',
        'composition',
        'output-plan',
        'output-compatibility',
        'beat-plan',
    ])
    assert.deepEqual(report.blockedStages, [])
})

test('warnings: aviso de cena nao referenciada no BeatPlan preservado sem invalidar por si so', () => {
    const base = validPipelineInput()
    const rawBeatPlan = JSON.parse(JSON.stringify(base.beatPlan)) as {
        beats: Array<{ sceneIds: string[]; durationMs: number }>
    }
    // Ajusta os beats para cobrir o tempo total de 14000ms sem referenciar 'closing' nem 'demo-frame'
    rawBeatPlan.beats = [
        { ...rawBeatPlan.beats[0]!, sceneIds: ['opening'], durationMs: 4000 },
        { ...rawBeatPlan.beats[1]!, sceneIds: ['opening'], durationMs: 10000 },
    ]

    const report = validateContentPipeline({
        ...base,
        beatPlan: rawBeatPlan,
    })

    // Deve ser valido porque warning nao invalida pipeline
    assert.equal(report.valid, true)
    assert.equal(report.errors.length, 0)
    assert.ok(report.warnings.length > 0)
    assert.ok(report.warnings.some((w) => w.code === 'BEAT_PLAN_SCENE_UNREFERENCED'))
})

test('determinismo e imutabilidade: inputs nao sofrem mutacao e resultado e estavel', () => {
    const input = validPipelineInput()
    const inputSnapshot = JSON.stringify(input)

    const run1 = validateContentPipeline(input)
    const run2 = validateContentPipeline(input)

    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(input), inputSnapshot, 'o validador nao pode mutar as entradas')
})

test('input nao-objeto: reporta PIPELINE_INPUT_INVALID e bloqueia dependentes', () => {
    for (const invalid of [null, undefined, 'string', 123, true, []]) {
        const report = validateContentPipeline(invalid)
        assert.equal(report.valid, false)
        assert.equal(report.errors[0]?.code, 'PIPELINE_INPUT_INVALID')
        assert.deepEqual(report.blockedStages, [
            'composition',
            'output-plan',
            'output-compatibility',
            'beat-plan',
        ])
    }
})

test('pureza e barreiras estaticas: modulo consolidador e puro e sem dependencias proibidas', () => {
    const files = [
        'src/content-pipeline-validation-contract.ts',
        'src/validate-content-pipeline.ts',
        'src/content-pipeline-validation-cli.ts',
    ]

    const forbiddenTokens = [
        '@temporalio',
        'orchestration',
        'fetch(',
        'http.request',
        'https.request',
        'process.env',
        'Date.now',
        'Math.random',
    ]

    for (const rel of files) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        for (const token of forbiddenTokens) {
            assert.ok(!content.includes(token), `token proibido "${token}" encontrado em ${rel}`)
        }
    }

    // Somente a CLI pode usar console; as funcoes de contrato e agregador nao podem
    for (const rel of ['src/content-pipeline-validation-contract.ts', 'src/validate-content-pipeline.ts']) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        assert.ok(!content.includes('console.'), `console proibido no modulo de dominio: ${rel}`)
        assert.ok(!content.includes('readFileSync('), `readFileSync proibido no modulo de dominio: ${rel}`)
        assert.ok(!content.includes('writeFileSync('), `writeFileSync proibido no modulo de dominio: ${rel}`)
    }
})
