/**
 * Testes unitarios do SimulatedExecutionPlan v1 e do
 * SimulatedExecutionReport v1: compilador puro, validadores puros,
 * executionId deterministico, serializacao canonica e schemas draft-07.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import {
    deriveExecutionPackageId,
    type CreativeExecutionPackage,
} from '../src/creative-execution-package-contract.js'
import { createSimulatedExecutionPlan } from '../src/create-simulated-execution-plan.js'
import {
    deriveSimulatedExecutionId,
    SIMULATED_EXECUTION_HASH_PREFIX,
    SIMULATED_EXECUTION_ID_MAX_LENGTH,
    SIMULATED_STEP_OPERATIONS,
    type SimulatedExecutionPlan,
} from '../src/simulated-execution-plan-contract.js'
import type { SimulatedExecutionReport } from '../src/simulated-execution-report-contract.js'
import {
    serializeSimulatedExecutionEvents,
    serializeSimulatedExecutionPlan,
    serializeSimulatedExecutionReport,
    serializeSimulatedHashes,
    serializeSimulatedPrimaryOutputManifest,
} from '../src/serialize-simulated-execution.js'
import { validateSimulatedExecutionPlan } from '../src/validate-simulated-execution-plan.js'
import { validateSimulatedExecutionReport } from '../src/validate-simulated-execution-report.js'
import { moduleRoot } from './contract-harness.js'

const ajv = new AjvModule.default({ allErrors: true, strict: false })

function compileSchema(file: string): (value: unknown) => boolean {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', file), 'utf8')) as AnySchemaObject
    const validate = ajv.compile(schema)
    return (value: unknown) => validate(value) === true
}

const planSchemaCheck = compileSchema('simulated-execution-plan.schema.json')
const reportSchemaCheck = compileSchema('simulated-execution-report.schema.json')

function readFixturePackage(name: string): CreativeExecutionPackage {
    const files = readFileSync(path.join(moduleRoot, 'examples', 'execution-packages', name), 'utf8')
    return JSON.parse(files) as CreativeExecutionPackage
}

const marcaPackage = readFixturePackage('execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json')
const multitrackPackage = readFixturePackage('execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json')

function compilePlan(executionPackage: CreativeExecutionPackage): SimulatedExecutionPlan {
    const result = createSimulatedExecutionPlan(executionPackage)
    assert.equal(result.ok, true, `compilacao falhou: ${result.ok ? '' : result.failureCode}`)
    if (!result.ok) throw new Error('unreachable')
    return result.plan
}

function codesOf(errors: readonly { code: string }[]): string[] {
    return errors.map((item) => item.code)
}

/** Relatorio minimo coerente para exercitar o validador sem o runner. */
function minimalReport(): SimulatedExecutionReport {
    return {
        schemaVersion: 1,
        executionId: 'simulation-pacote-teste',
        packageId: 'pacote-teste',
        status: 'completed',
        resumedFromStatus: null,
        completedSteps: ['beat-um-prepare-scene'],
        failedStepId: null,
        failureCode: null,
        artifactCount: 1,
        artifacts: [
            {
                id: 'primary-output',
                logicalName: 'pacote-teste-primary-output',
                contentType: 'video',
                sha256: 'a'.repeat(64),
            },
        ],
        events: [
            { sequence: 1, type: 'execution-started', executionId: 'simulation-pacote-teste' },
            { sequence: 2, type: 'execution-completed', executionId: 'simulation-pacote-teste' },
        ],
        summary: 'Simulated execution completed.',
    }
}

function shuffleKeys(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(shuffleKeys)
    if (typeof value === 'object' && value !== null) {
        const entries = Object.entries(value as Record<string, unknown>).reverse()
        const shuffled: Record<string, unknown> = {}
        for (const [key, item] of entries) shuffled[key] = shuffleKeys(item)
        return shuffled
    }
    return value
}

/* ------------------------------------------------------------------ */
/* Compilador do plano                                                 */
/* ------------------------------------------------------------------ */

test('compilacao valida para os dois consumidores: executionId, steps e artefatos', () => {
    for (const executionPackage of [marcaPackage, multitrackPackage]) {
        const plan = compilePlan(executionPackage)
        assert.equal(plan.schemaVersion, 1)
        assert.equal(plan.executionId, `simulation-${executionPackage.packageId}`)
        assert.equal(plan.packageId, executionPackage.packageId)
        assert.equal(plan.caseId, null)
        assert.equal(plan.adapter, 'simulation')
        assert.equal(plan.steps.length, executionPackage.timeline.length * SIMULATED_STEP_OPERATIONS.length)
        assert.deepEqual(plan.output, {
            profileId: executionPackage.output.profileId,
            mediaKind: 'video',
            width: executionPackage.output.width,
            height: executionPackage.output.height,
            aspectRatio: executionPackage.output.aspectRatio,
            fps: executionPackage.output.fps,
            durationMs: executionPackage.output.durationMs,
        })
        assert.deepEqual(plan.expectedArtifacts, executionPackage.expectedArtifacts)

        plan.steps.forEach((step, index) => {
            assert.equal(step.order, index + 1)
            const entryIndex = Math.floor(index / SIMULATED_STEP_OPERATIONS.length)
            const entry = executionPackage.timeline[entryIndex]
            assert.ok(entry !== undefined)
            assert.equal(step.beatId, entry?.beatId)
            assert.equal(step.sceneId, entry?.sceneIds[0])
            assert.equal(step.startMs, entry?.startMs)
            assert.equal(step.endMs, entry?.endMs)
            assert.equal(step.operation, SIMULATED_STEP_OPERATIONS[index % SIMULATED_STEP_OPERATIONS.length])
        })

        const validation = validateSimulatedExecutionPlan(plan)
        assert.equal(validation.valid, true, validation.summary)
        assert.equal(planSchemaCheck(plan), true, 'schema draft-07 rejeitou o plano compilado')
    }
})

test('compilacao preserva textos e intencoes sem criar conteudo', () => {
    const plan = compilePlan(multitrackPackage)
    const textSteps = plan.steps.filter((step) => step.operation === 'apply-text')
    assert.equal(textSteps.length, multitrackPackage.timeline.length)
    multitrackPackage.timeline.forEach((entry, index) => {
        const step = textSteps[index]
        assert.equal(step?.inputs.onScreenText, entry.onScreenText)
        assert.equal(step?.inputs.narrationText, entry.narrationText)
    })
    const motionSteps = plan.steps.filter((step) => step.operation === 'apply-motion')
    multitrackPackage.timeline.forEach((entry, index) => {
        const step = motionSteps[index]
        assert.equal(step?.inputs.motionIntent, entry.motionIntent)
        assert.equal(step?.inputs.transitionIn, entry.transitionIn)
        assert.equal(step?.inputs.transitionOut, entry.transitionOut)
    })
})

test('compilacao e deterministica e nao muta o pacote', () => {
    const snapshot = JSON.stringify(marcaPackage)
    const run1 = createSimulatedExecutionPlan(marcaPackage)
    const run2 = createSimulatedExecutionPlan(marcaPackage)
    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(marcaPackage), snapshot)
    assert.equal(
        serializeSimulatedExecutionPlan(compilePlan(marcaPackage)),
        serializeSimulatedExecutionPlan(compilePlan(marcaPackage)),
    )
})

test('pacote invalido ou versao errada: codigos de falha proprios', () => {
    const invalid = createSimulatedExecutionPlan({ invalido: true })
    assert.equal(invalid.ok, false)
    if (!invalid.ok) assert.equal(invalid.failureCode, 'PACKAGE_INVALID')

    const wrongVersion = createSimulatedExecutionPlan({ ...marcaPackage, schemaVersion: 2 })
    assert.equal(wrongVersion.ok, false)
    if (!wrongVersion.ok) assert.equal(wrongVersion.failureCode, 'PACKAGE_VERSION_UNSUPPORTED')

    const notObject = createSimulatedExecutionPlan(null)
    assert.equal(notObject.ok, false)
    if (!notObject.ok) assert.equal(notObject.failureCode, 'PACKAGE_INVALID')
})

test('timeline adulterada: TIMELINE_INVALID', () => {
    const broken = {
        ...marcaPackage,
        timeline: marcaPackage.timeline.map((entry, index) => (index === 1 ? { ...entry, startMs: entry.startMs + 1 } : entry)),
    }
    const result = createSimulatedExecutionPlan(broken)
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.failureCode, 'TIMELINE_INVALID')
})

test('artefato declarado sem etapa que o referencie: ARTIFACT_REFERENCE_INVALID', () => {
    const semTexto: CreativeExecutionPackage = {
        ...marcaPackage,
        timeline: marcaPackage.timeline.map((entry) => {
            const { onScreenText: _text, narrationText: _narration, ...rest } = entry
            return rest
        }),
    }
    const result = createSimulatedExecutionPlan(semTexto)
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.failureCode, 'ARTIFACT_REFERENCE_INVALID')
})

test('executionId legivel e forma canonica com hash acima do limite', () => {
    const readable = deriveSimulatedExecutionId('pacote-teste')
    assert.equal(readable, 'simulation-pacote-teste')
    assert.ok(readable.length <= SIMULATED_EXECUTION_ID_MAX_LENGTH)

    const longId = 'x'.repeat(140)
    const hashed = deriveSimulatedExecutionId(longId)
    assert.ok(hashed.startsWith(SIMULATED_EXECUTION_HASH_PREFIX))
    assert.match(hashed, /^simulation-v1-[0-9a-f]{64}$/)
    assert.equal(hashed, deriveSimulatedExecutionId(longId))

    // Pacote valido com packageId legivel longo força a forma com hash no plano.
    const ids = {
        projectId: 'a'.repeat(30),
        compositionId: 'b'.repeat(30),
        outputPlanId: 'c'.repeat(25),
        beatPlanId: 'd'.repeat(21),
    }
    const longPackageId = deriveExecutionPackageId(ids)
    assert.ok(longPackageId.length + 'simulation-'.length > SIMULATED_EXECUTION_ID_MAX_LENGTH)
    const longPackage: CreativeExecutionPackage = {
        ...marcaPackage,
        packageId: longPackageId,
        projectId: ids.projectId,
        compositionId: ids.compositionId,
        outputPlanId: ids.outputPlanId,
        beatPlanId: ids.beatPlanId,
        source: {
            ...marcaPackage.source,
            projectId: ids.projectId,
            compositionId: ids.compositionId,
            outputPlanId: ids.outputPlanId,
            beatPlanId: ids.beatPlanId,
        },
    }
    const plan = compilePlan(longPackage)
    assert.match(plan.executionId, /^simulation-v1-[0-9a-f]{64}$/)
    assert.equal(validateSimulatedExecutionPlan(plan).valid, true)
})

/* ------------------------------------------------------------------ */
/* Validador do plano                                                  */
/* ------------------------------------------------------------------ */

test('validador do plano rejeita estrutura, versao, campos extras e ids inconsistentes', () => {
    const plan = compilePlan(marcaPackage)
    for (const invalid of [null, undefined, 'texto', []]) {
        assert.deepEqual(codesOf(validateSimulatedExecutionPlan(invalid).errors), ['SIMULATED_PLAN_INVALID'])
    }
    assert.ok(codesOf(validateSimulatedExecutionPlan({ ...plan, schemaVersion: 9 }).errors).includes('SIMULATED_PLAN_SCHEMA_VERSION_UNSUPPORTED'))
    assert.ok(codesOf(validateSimulatedExecutionPlan({ ...plan, extra: true }).errors).includes('SIMULATED_PLAN_UNKNOWN_FIELD'))
    assert.ok(codesOf(validateSimulatedExecutionPlan({ ...plan, executionId: 'simulation-outro-pacote' }).errors).includes('SIMULATED_PLAN_EXECUTION_ID_MISMATCH'))
    assert.ok(codesOf(validateSimulatedExecutionPlan({ ...plan, adapter: 'ffmpeg' }).errors).includes('SIMULATED_PLAN_ADAPTER_INVALID'))
    assert.ok(codesOf(validateSimulatedExecutionPlan({ ...plan, caseId: 'Invalido' }).errors).includes('SIMULATED_PLAN_CASE_ID_INVALID'))
})

test('validador do plano rejeita steps quebrados: ordem, agrupamento, janela e referencias', () => {
    const plan = compilePlan(marcaPackage)
    const wrongOrder = { ...plan, steps: plan.steps.map((step, index) => (index === 2 ? { ...step, order: 99 } : step)) }
    assert.ok(codesOf(validateSimulatedExecutionPlan(wrongOrder).errors).includes('SIMULATED_PLAN_STEP_ORDER_INVALID'))

    const wrongOperation = { ...plan, steps: plan.steps.map((step, index) => (index === 1 ? { ...step, operation: 'finalize-scene' } : step)) }
    assert.ok(codesOf(validateSimulatedExecutionPlan(wrongOperation).errors).includes('SIMULATED_PLAN_STEP_SEQUENCE_INVALID'))

    const brokenWindow = { ...plan, steps: plan.steps.map((step, index) => (index === 0 ? { ...step, endMs: step.endMs + 1 } : step)) }
    assert.ok(codesOf(validateSimulatedExecutionPlan(brokenWindow).errors).includes('SIMULATED_PLAN_STEP_WINDOW_INVALID'))

    const unknownArtifact = { ...plan, steps: plan.steps.map((step, index) => (index === 0 ? { ...step, expectedArtifactIds: ['artefato-fantasma'] } : step)) }
    assert.ok(codesOf(validateSimulatedExecutionPlan(unknownArtifact).errors).includes('SIMULATED_PLAN_ARTIFACT_REFERENCE_INVALID'))

    const emptySteps = { ...plan, steps: [] }
    assert.ok(codesOf(validateSimulatedExecutionPlan(emptySteps).errors).includes('SIMULATED_PLAN_STEPS_INVALID'))
})

test('validador do plano exige duracao consolidada igual ao fim da timeline', () => {
    const plan = compilePlan(marcaPackage)
    const mismatch = { ...plan, output: { ...plan.output, durationMs: plan.output.durationMs + 1 } }
    assert.ok(codesOf(validateSimulatedExecutionPlan(mismatch).errors).includes('SIMULATED_PLAN_DURATION_MISMATCH'))
})

/* ------------------------------------------------------------------ */
/* Validador do relatorio                                              */
/* ------------------------------------------------------------------ */

test('validador do relatorio aceita relatorio coerente e o schema draft-07 tambem', () => {
    const report = minimalReport()
    const validation = validateSimulatedExecutionReport(report)
    assert.equal(validation.valid, true, validation.summary)
    assert.equal(reportSchemaCheck(report), true)
})

test('validador do relatorio rejeita incoerencia de status, eventos e hashes', () => {
    const report = minimalReport()
    assert.deepEqual(codesOf(validateSimulatedExecutionReport(null).errors), ['SIMULATED_REPORT_INVALID'])
    assert.ok(codesOf(validateSimulatedExecutionReport({ ...report, schemaVersion: 2 }).errors).includes('SIMULATED_REPORT_SCHEMA_VERSION_UNSUPPORTED'))
    assert.ok(codesOf(validateSimulatedExecutionReport({ ...report, extra: 1 }).errors).includes('SIMULATED_REPORT_UNKNOWN_FIELD'))

    const completedWithFailure = { ...report, failureCode: 'X', failedStepId: 'beat-um-prepare-scene' }
    assert.ok(codesOf(validateSimulatedExecutionReport(completedWithFailure).errors).includes('SIMULATED_REPORT_STATUS_INCOHERENT'))

    const failedWithoutCode = { ...report, status: 'failed', failedStepId: 'beat-um-apply-text' }
    assert.ok(codesOf(validateSimulatedExecutionReport(failedWithoutCode).errors).includes('SIMULATED_REPORT_STATUS_INCOHERENT'))

    const cancelledWithCode = { ...report, status: 'cancelled', failureCode: 'X' }
    assert.ok(codesOf(validateSimulatedExecutionReport(cancelledWithCode).errors).includes('SIMULATED_REPORT_STATUS_INCOHERENT'))

    const badSequence = { ...report, events: report.events.map((event, index) => (index === 1 ? { ...event, sequence: 9 } : event)) }
    assert.ok(codesOf(validateSimulatedExecutionReport(badSequence).errors).includes('SIMULATED_REPORT_EVENT_SEQUENCE_INVALID'))

    const badLast = { ...report, events: [report.events[0] as SimulatedExecutionReport['events'][number]] }
    assert.ok(codesOf(validateSimulatedExecutionReport(badLast).errors).includes('SIMULATED_REPORT_EVENT_ORDER_INVALID'))

    const badHash = { ...report, artifacts: [{ ...report.artifacts[0]!, sha256: 'xyz' }] }
    assert.ok(codesOf(validateSimulatedExecutionReport(badHash).errors).includes('SIMULATED_REPORT_ARTIFACT_HASH_INVALID'))

    const badCount = { ...report, artifactCount: 5 }
    assert.ok(codesOf(validateSimulatedExecutionReport(badCount).errors).includes('SIMULATED_REPORT_ARTIFACT_COUNT_INVALID'))

    const badResume = { ...report, resumedFromStatus: 'completed' }
    assert.ok(codesOf(validateSimulatedExecutionReport(badResume).errors).includes('SIMULATED_REPORT_RESUME_INVALID'))
})

/* ------------------------------------------------------------------ */
/* Serializacao canonica                                               */
/* ------------------------------------------------------------------ */

test('serializadores produzem bytes estaveis em LF com uma newline e zero BOM', () => {
    const plan = compilePlan(marcaPackage)
    const report = minimalReport()
    const serializers: Array<() => string> = [
        () => serializeSimulatedExecutionPlan(plan),
        () => serializeSimulatedExecutionReport(report),
        () => serializeSimulatedExecutionEvents(report.events),
        () => serializeSimulatedPrimaryOutputManifest({
            logicalName: 'pacote-teste-primary-output',
            mediaKind: 'video',
            width: 1080,
            height: 1920,
            aspectRatio: '9:16',
            fps: 30,
            durationMs: 14000,
            profileId: 'instagram-reels-video',
            simulated: true,
        }),
        () => serializeSimulatedHashes({ 'b.json': 'b'.repeat(64), 'a.json': 'a'.repeat(64) }),
    ]
    for (const serialize of serializers) {
        const bytes = serialize()
        assert.equal(bytes, serialize())
        assert.ok(!bytes.includes('\r'))
        assert.ok(bytes.endsWith('\n'))
        assert.ok(!bytes.endsWith('\n\n'))
        assert.ok(!bytes.startsWith('\uFEFF'))
    }
})

test('round trip e independencia da ordem de chaves original', () => {
    const plan = compilePlan(multitrackPackage)
    const canonicalPlan = serializeSimulatedExecutionPlan(plan)
    assert.equal(serializeSimulatedExecutionPlan(shuffleKeys(plan) as SimulatedExecutionPlan), canonicalPlan)
    assert.equal(serializeSimulatedExecutionPlan(JSON.parse(canonicalPlan) as SimulatedExecutionPlan), canonicalPlan)

    const report = minimalReport()
    const canonicalReport = serializeSimulatedExecutionReport(report)
    assert.equal(serializeSimulatedExecutionReport(shuffleKeys(report) as SimulatedExecutionReport), canonicalReport)
    assert.equal(serializeSimulatedExecutionReport(JSON.parse(canonicalReport) as SimulatedExecutionReport), canonicalReport)

    const hashes = serializeSimulatedHashes({ 'z.json': 'z'.repeat(64), 'a.json': 'a'.repeat(64) })
    assert.deepEqual(Object.keys(JSON.parse(hashes) as Record<string, string>), ['a.json', 'z.json'])
})

test('serializacao nao carrega informacao de ambiente', () => {
    const bytes = serializeSimulatedExecutionPlan(compilePlan(multitrackPackage))
    for (const needle of [process.cwd(), moduleRoot, 'C:\\', 'C:/', process.platform]) {
        assert.ok(!bytes.includes(needle), `informacao de ambiente encontrada: ${needle}`)
    }
})

/* ------------------------------------------------------------------ */
/* Barreiras estaticas de pureza                                       */
/* ------------------------------------------------------------------ */

test('modulos da execucao simulada nao usam rede, relogio, aleatoriedade, Temporal nem filesystem', () => {
    const domainFiles = [
        'src/simulated-execution-plan-contract.ts',
        'src/simulated-execution-report-contract.ts',
        'src/create-simulated-execution-plan.ts',
        'src/validate-simulated-execution-plan.ts',
        'src/validate-simulated-execution-report.ts',
        'src/serialize-simulated-execution.ts',
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
        'node:fs',
        'readFileSync(',
        'writeFileSync(',
        'child_process',
        'ffmpeg',
        'console.',
        'setTimeout',
        'setInterval',
    ]
    for (const rel of domainFiles) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        for (const token of forbiddenTokens) {
            assert.ok(!content.includes(token), `token proibido "${token}" encontrado em ${rel}`)
        }
    }
    for (const rel of domainFiles.filter((file) => !file.includes('plan-contract'))) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        assert.ok(!content.includes('node:crypto'), `node:crypto fora do contrato de plano: ${rel}`)
    }
})
