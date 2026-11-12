/**
 * Testes unitarios do executor local simulado: execucao completed, falha
 * controlada, cancelamento, retomada, artefatos textuais, hashes, writer
 * transacional e agregacao multicase.
 */

import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import {
    existsSync,
    mkdirSync,
    mkdtempSync,
    readFileSync,
    readdirSync,
    rmSync,
    symlinkSync,
    writeFileSync,
} from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, test } from 'node:test'

import type { CreativeExecutionPackage } from '../src/creative-execution-package-contract.js'
import { createSimulatedExecutionPlan } from '../src/create-simulated-execution-plan.js'
import {
    aggregateSimulatedExecutions,
    type SimulatedExecutionCaseResult,
} from '../src/simulated-execution-multicase.js'
import type { SimulatedExecutionPlan } from '../src/simulated-execution-plan-contract.js'
import type { SimulatedExecutionReport } from '../src/simulated-execution-report-contract.js'
import {
    buildSimulatedArtifacts,
    checkSimulatedResume,
    resumeSimulatedExecution,
    runSimulatedExecution,
} from '../src/simulated-execution-runner.js'
import {
    buildSimulatedExecutionFiles,
    confineSimulatedOutputDir,
    writeSimulatedExecution,
} from '../src/simulated-execution-writer.js'
import { validateSimulatedExecutionReport } from '../src/validate-simulated-execution-report.js'
import { moduleRoot } from './contract-harness.js'

function readFixturePackage(name: string): CreativeExecutionPackage {
    return JSON.parse(readFileSync(path.join(moduleRoot, 'examples', 'execution-packages', name), 'utf8')) as CreativeExecutionPackage
}

const marcaPackage = readFixturePackage('execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json')
const multitrackPackage = readFixturePackage('execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json')

function planOf(executionPackage: CreativeExecutionPackage): SimulatedExecutionPlan {
    const result = createSimulatedExecutionPlan(executionPackage)
    assert.equal(result.ok, true)
    if (!result.ok) throw new Error('unreachable')
    return result.plan
}

const tempRoots: string[] = []
function makeTempRoot(): string {
    const root = mkdtempSync(path.join(os.tmpdir(), 'simulated-execution-test-'))
    tempRoots.push(root)
    return root
}
after(() => {
    for (const root of tempRoots) {
        if (root) rmSync(root, { recursive: true, force: true })
    }
})

function sha256(content: string): string {
    return createHash('sha256').update(content, 'utf8').digest('hex')
}

/* ------------------------------------------------------------------ */
/* Execucao completed                                                  */
/* ------------------------------------------------------------------ */

test('execucao completed: todos os steps, eventos em ordem, artefatos e hashes', () => {
    for (const executionPackage of [marcaPackage, multitrackPackage]) {
        const plan = planOf(executionPackage)
        const { report, artifacts } = runSimulatedExecution(plan)
        assert.equal(report.status, 'completed')
        assert.equal(report.resumedFromStatus, null)
        assert.deepEqual(report.completedSteps, plan.steps.map((step) => step.stepId))
        assert.equal(report.failedStepId, null)
        assert.equal(report.failureCode, null)
        assert.equal(report.artifactCount, 4)
        assert.equal(artifacts.length, 4)
        assert.equal(report.summary, 'Simulated execution completed.')

        report.events.forEach((event, index) => {
            assert.equal(event.sequence, index + 1)
            assert.equal(event.executionId, plan.executionId)
        })
        assert.equal(report.events[0]?.type, 'execution-started')
        assert.equal(report.events[report.events.length - 1]?.type, 'execution-completed')
        const stepCompleted = report.events.filter((event) => event.type === 'step-completed')
        assert.equal(stepCompleted.length, plan.steps.length)
        const artifactCreated = report.events.filter((event) => event.type === 'artifact-created')
        assert.equal(artifactCreated.length, 4)

        for (const artifact of report.artifacts) {
            assert.match(artifact.sha256, /^[0-9a-f]{64}$/)
            const file = artifacts.find((item) => item.id === artifact.id)
            assert.ok(file !== undefined)
            assert.equal(artifact.sha256, sha256(file?.content ?? ''))
        }
        assert.equal(validateSimulatedExecutionReport(report).valid, true)
    }
})

test('artefatos textuais derivam somente do plano, sem midia nem ambiente', () => {
    const plan = planOf(multitrackPackage)
    const artifacts = buildSimulatedArtifacts(plan)
    const captions = artifacts.find((artifact) => artifact.id === 'captions')
    const narration = artifacts.find((artifact) => artifact.id === 'narration-script')
    const manifest = artifacts.find((artifact) => artifact.id === 'primary-output')
    const summary = artifacts.find((artifact) => artifact.id === 'execution-report')
    assert.ok(captions !== undefined && narration !== undefined && manifest !== undefined && summary !== undefined)

    assert.ok(captions.content.includes('Multitracks, playbacks e rateios em um so lugar.'))
    assert.ok(narration.content.includes('Chamada tecnica final para conhecer o sistema.'))
    assert.match(captions.content, /^\[0-3000\] /)

    const parsedManifest = JSON.parse(manifest.content) as { simulated: boolean; mediaKind: string; durationMs: number }
    assert.equal(parsedManifest.simulated, true)
    assert.equal(parsedManifest.mediaKind, 'video')
    assert.equal(parsedManifest.durationMs, 15000)

    for (const artifact of artifacts) {
        assert.ok(!artifact.content.includes(process.cwd()))
        assert.ok(!artifact.content.includes('C:\\'))
        assert.ok(!artifact.relativePath.startsWith('/'))
        assert.ok(!artifact.content.includes('\r'))
    }
})

test('execucao e deterministica e nao muta o plano', () => {
    const plan = planOf(marcaPackage)
    const snapshot = JSON.stringify(plan)
    const run1 = runSimulatedExecution(plan)
    const run2 = runSimulatedExecution(plan)
    assert.deepEqual(run1, run2)
    assert.equal(JSON.stringify(plan), snapshot)
})

/* ------------------------------------------------------------------ */
/* Falha controlada                                                    */
/* ------------------------------------------------------------------ */

test('falha controlada: steps anteriores concluidos, posteriores ausentes, sem artefato posterior', () => {
    const plan = planOf(marcaPackage)
    const failedStep = plan.steps[5]
    assert.ok(failedStep !== undefined)
    const { report, artifacts } = runSimulatedExecution(plan, { failAtStepId: failedStep.stepId })

    assert.equal(report.status, 'failed')
    assert.equal(report.failedStepId, failedStep.stepId)
    assert.equal(report.failureCode, 'SIMULATED_STEP_FAILURE')
    assert.deepEqual(report.completedSteps, plan.steps.slice(0, 5).map((step) => step.stepId))
    assert.ok(!report.completedSteps.includes(failedStep.stepId))
    assert.equal(report.events[report.events.length - 1]?.type, 'execution-failed')
    const stepFailed = report.events.find((event) => event.type === 'step-failed')
    assert.equal(stepFailed?.stepId, failedStep.stepId)
    assert.equal(stepFailed?.failureCode, 'SIMULATED_STEP_FAILURE')

    // Nenhum artefato cuja primeira declaracao esteja no step falho ou depois.
    for (const artifact of artifacts) {
        const firstDecl = plan.steps.findIndex((step) => step.expectedArtifactIds.includes(artifact.id))
        assert.ok(firstDecl < 5, `artefato ${artifact.id} declarado tardiamente presente`)
    }
    assert.equal(validateSimulatedExecutionReport(report).valid, true)
})

/* ------------------------------------------------------------------ */
/* Cancelamento                                                        */
/* ------------------------------------------------------------------ */

test('cancelamento deterministico: status cancelled sem failureCode tecnico', () => {
    const plan = planOf(marcaPackage)
    const { report } = runSimulatedExecution(plan, { cancelAfterSequence: 4 })
    assert.equal(report.status, 'cancelled')
    assert.equal(report.failureCode, null)
    assert.equal(report.failedStepId, null)
    assert.equal(report.events[report.events.length - 1]?.type, 'execution-cancelled')
    assert.equal(report.events.length, 5)
    assert.ok(report.completedSteps.length < plan.steps.length)
    assert.equal(report.summary, 'Simulated execution cancelled.')
    assert.equal(validateSimulatedExecutionReport(report).valid, true)

    const again = runSimulatedExecution(plan, { cancelAfterSequence: 4 })
    assert.deepEqual(again.report, report)
})

/* ------------------------------------------------------------------ */
/* Retomada                                                            */
/* ------------------------------------------------------------------ */

test('retomada failed -> completed: sem duplicacao de eventos ou artefatos', () => {
    const plan = planOf(multitrackPackage)
    const failedStep = plan.steps[6]
    assert.ok(failedStep !== undefined)
    const failed = runSimulatedExecution(plan, { failAtStepId: failedStep.stepId })
    assert.equal(failed.report.status, 'failed')

    const check = checkSimulatedResume(plan, failed.report)
    assert.equal(check.ok, true)
    const resumed = resumeSimulatedExecution(plan, failed.report)
    assert.equal(resumed.report.status, 'completed')
    assert.equal(resumed.report.resumedFromStatus, 'failed')
    assert.deepEqual(resumed.report.completedSteps, plan.steps.map((step) => step.stepId))

    // Eventos anteriores preservados como prefixo; sequencia contigua sem duplicacao.
    const priorCount = failed.report.events.length
    assert.deepEqual(resumed.report.events.slice(0, priorCount), failed.report.events)
    resumed.report.events.forEach((event, index) => assert.equal(event.sequence, index + 1))
    assert.equal(resumed.report.events.filter((event) => event.type === 'execution-started').length, 1)
    assert.equal(resumed.report.events.filter((event) => event.type === 'artifact-created').length, 4)

    // Hashes identicos aos de uma execucao nova completa.
    const fresh = runSimulatedExecution(plan)
    assert.deepEqual(resumed.report.artifacts, fresh.report.artifacts)
    assert.equal(validateSimulatedExecutionReport(resumed.report).valid, true)
})

test('retomada cancelled -> completed preserva o prefixo concluido', () => {
    const plan = planOf(marcaPackage)
    const cancelled = runSimulatedExecution(plan, { cancelAfterSequence: 6 })
    assert.equal(cancelled.report.status, 'cancelled')
    const check = checkSimulatedResume(plan, cancelled.report)
    assert.equal(check.ok, true)
    if (!check.ok) return
    const resumed = resumeSimulatedExecution(plan, cancelled.report)
    assert.equal(resumed.report.status, 'completed')
    assert.equal(resumed.report.resumedFromStatus, 'cancelled')
    assert.deepEqual(resumed.report.completedSteps, plan.steps.map((step) => step.stepId))
})

test('retomada rejeita: completed, ids divergentes, hash divergente, relatorio invalido', () => {
    const plan = planOf(marcaPackage)
    const completed = runSimulatedExecution(plan)
    const notResumable = checkSimulatedResume(plan, completed.report)
    assert.equal(notResumable.ok, false)
    if (!notResumable.ok) assert.equal(notResumable.code, 'STATUS_NOT_RESUMABLE')

    const failed = runSimulatedExecution(plan, { failAtStepId: plan.steps[4]?.stepId })
    const wrongExecution = checkSimulatedResume(plan, {
        ...failed.report,
        executionId: 'simulation-outro',
        events: failed.report.events.map((event) => ({ ...event, executionId: 'simulation-outro' })),
    })
    assert.equal(wrongExecution.ok, false)
    if (!wrongExecution.ok) assert.equal(wrongExecution.code, 'EXECUTION_ID_MISMATCH')

    const wrongPackage = checkSimulatedResume(plan, { ...failed.report, packageId: 'outro-pacote' })
    assert.equal(wrongPackage.ok, false)
    if (!wrongPackage.ok) assert.equal(wrongPackage.code, 'PACKAGE_ID_MISMATCH')

    const tamperedHash = {
        ...failed.report,
        artifacts: failed.report.artifacts.map((artifact, index) => (index === 0 ? { ...artifact, sha256: 'b'.repeat(64) } : artifact)),
    }
    const hashMismatch = checkSimulatedResume(plan, tamperedHash)
    assert.equal(hashMismatch.ok, false)
    if (!hashMismatch.ok) assert.equal(hashMismatch.code, 'ARTIFACT_HASH_MISMATCH')

    const invalidReport = checkSimulatedResume(plan, { invalido: true })
    assert.equal(invalidReport.ok, false)
    if (!invalidReport.ok) assert.equal(invalidReport.code, 'REPORT_INVALID')

    const badPrefix = checkSimulatedResume(plan, { ...failed.report, completedSteps: ['step-inexistente'] })
    assert.equal(badPrefix.ok, false)
    if (!badPrefix.ok) assert.equal(badPrefix.code, 'REPORT_INVALID')
})

/* ------------------------------------------------------------------ */
/* Multicase                                                           */
/* ------------------------------------------------------------------ */

test('agregacao multicase: contagens, ordem estavel e isolamento de falha', () => {
    const marcaPlan = planOf(marcaPackage)
    const multitrackPlan = planOf(multitrackPackage)
    const ok1 = runSimulatedExecution(marcaPlan)
    const ok2 = runSimulatedExecution(multitrackPlan)
    const toResult = (sourceName: string, report: SimulatedExecutionReport): SimulatedExecutionCaseResult => ({
        sourceName,
        packageId: report.packageId,
        executionId: report.executionId,
        status: report.status,
        report,
        failureCode: report.failureCode,
        summary: report.summary,
    })

    const both = aggregateSimulatedExecutions([toResult('a.json', ok1.report), toResult('b.json', ok2.report)])
    assert.equal(both.valid, true)
    assert.equal(both.completedCount, 2)
    assert.equal(both.packageCount, 2)
    assert.deepEqual(both.executions.map((execution) => execution.sourceName), ['a.json', 'b.json'])

    const failed = runSimulatedExecution(multitrackPlan, { failAtStepId: multitrackPlan.steps[3]?.stepId })
    const mixed = aggregateSimulatedExecutions([toResult('a.json', failed.report), toResult('b.json', ok1.report)])
    assert.equal(mixed.valid, false)
    assert.equal(mixed.failedCount, 1)
    assert.equal(mixed.completedCount, 1)
    assert.match(mixed.summary, /1 completed, 1 failed/)

    const empty = aggregateSimulatedExecutions([])
    assert.equal(empty.valid, false)
    assert.equal(empty.packageCount, 0)
})

/* ------------------------------------------------------------------ */
/* Writer transacional                                                 */
/* ------------------------------------------------------------------ */

test('writer produz todos os arquivos com hashes verificaveis e bytes estaveis', () => {
    const root = makeTempRoot()
    const plan = planOf(marcaPackage)
    const run = runSimulatedExecution(plan)
    const outDir = path.join(root, 'out')
    const result = writeSimulatedExecution(outDir, { plan, report: run.report, artifacts: run.artifacts })
    assert.equal(result.ok, true)

    const expectedFiles = [
        'execution-plan.json',
        'execution-report.json',
        'events.json',
        'hashes.json',
        'artifacts/primary-output.manifest.json',
        'artifacts/captions.txt',
        'artifacts/narration-script.txt',
        'artifacts/execution-summary.txt',
    ]
    for (const file of expectedFiles) {
        assert.ok(existsSync(path.join(outDir, file)), `arquivo ausente: ${file}`)
    }
    assert.ok(!existsSync(path.join(outDir, '.staging-simulated-execution')))

    const hashes = JSON.parse(readFileSync(path.join(outDir, 'hashes.json'), 'utf8')) as Record<string, string>
    for (const [relativePath, digest] of Object.entries(hashes)) {
        const content = readFileSync(path.join(outDir, relativePath), 'utf8')
        assert.equal(sha256(content), digest, `hash divergente: ${relativePath}`)
    }
    assert.ok(!('hashes.json' in hashes), 'hashes.json nao pode conter o proprio hash')

    const before = new Map(expectedFiles.map((file) => [file, readFileSync(path.join(outDir, file), 'utf8')]))
    const again = writeSimulatedExecution(outDir, { plan, report: run.report, artifacts: run.artifacts })
    assert.equal(again.ok, true)
    for (const file of expectedFiles) {
        assert.equal(readFileSync(path.join(outDir, file), 'utf8'), before.get(file))
    }
})

test('writer preserva o destino anterior em falha de promocao', () => {
    const root = makeTempRoot()
    const plan = planOf(marcaPackage)
    const run = runSimulatedExecution(plan)
    const outDir = path.join(root, 'out')
    assert.equal(writeSimulatedExecution(outDir, { plan, report: run.report, artifacts: run.artifacts }).ok, true)
    const before = new Map(
        readdirSync(outDir, { withFileTypes: true })
            .filter((entry) => entry.isFile())
            .map((entry) => [entry.name, readFileSync(path.join(outDir, entry.name), 'utf8')]),
    )

    // Transforma um alvo em diretorio: o rename falha e a transacao reverte.
    rmSync(path.join(outDir, 'events.json'))
    mkdirSync(path.join(outDir, 'events.json'))
    const failed = writeSimulatedExecution(outDir, { plan, report: run.report, artifacts: run.artifacts })
    assert.equal(failed.ok, false)
    if (!failed.ok) assert.equal(failed.stage, 'promote')

    assert.equal(readFileSync(path.join(outDir, 'execution-report.json'), 'utf8'), before.get('execution-report.json'))
    assert.equal(readFileSync(path.join(outDir, 'hashes.json'), 'utf8'), before.get('hashes.json'))
})

test('confinamento rejeita absoluto, escape, symlink externo e arquivo no lugar de diretorio', (t) => {
    const root = makeTempRoot()
    const previousCwd = process.cwd()
    process.chdir(root)
    try {
        assert.equal(confineSimulatedOutputDir(path.join(root, 'out'), root).ok, false)
        assert.equal(confineSimulatedOutputDir('../fora', root).ok, false)
        assert.equal(confineSimulatedOutputDir('out/../../fora', root).ok, false)
        assert.equal(confineSimulatedOutputDir('out', root).ok, true)

        const filePath = path.join(root, 'arquivo')
        writeFileSync(filePath, 'x', 'utf8')
        assert.equal(confineSimulatedOutputDir('arquivo', root).ok, false)

        const outside = makeTempRoot()
        try {
            symlinkSync(outside, path.join(root, 'link'), 'dir')
        } catch {
            t.skip('symlink nao suportado neste ambiente Windows')
            return
        }
        assert.equal(confineSimulatedOutputDir('link', root).ok, false)
    } finally {
        process.chdir(previousCwd)
    }
})

test('mapa de arquivos do writer e deterministico e sem caminhos absolutos', () => {
    const plan = planOf(multitrackPackage)
    const run = runSimulatedExecution(plan)
    const files = buildSimulatedExecutionFiles({ plan, report: run.report, artifacts: run.artifacts })
    for (const [relativePath, content] of files) {
        assert.ok(!path.isAbsolute(relativePath))
        assert.ok(!relativePath.includes('..'))
        assert.ok(!content.includes(process.cwd()))
        assert.ok(content.endsWith('\n'))
        assert.ok(!content.includes('\r'))
    }
})

/* ------------------------------------------------------------------ */
/* Barreiras estaticas                                                 */
/* ------------------------------------------------------------------ */

test('runner e writer nao usam timers, rede, Temporal ou processos filhos', () => {
    const files = [
        'src/simulated-execution-runner.ts',
        'src/simulated-execution-writer.ts',
        'src/simulated-execution-multicase.ts',
        'src/simulated-execution-cli.ts',
    ]
    const forbidden = [
        '@temporalio',
        'orchestration',
        'fetch(',
        'http.request',
        'https.request',
        'Date.now',
        'Math.random',
        'setTimeout',
        'setInterval',
        'child_process',
        'ffmpeg',
    ]
    for (const rel of files) {
        const content = readFileSync(path.join(moduleRoot, rel), 'utf8')
        for (const token of forbidden) {
            assert.ok(!content.includes(token), `token proibido "${token}" encontrado em ${rel}`)
        }
    }
    const runner = readFileSync(path.join(moduleRoot, 'src/simulated-execution-runner.ts'), 'utf8')
    assert.ok(!runner.includes('node:fs'), 'runner nao acessa filesystem; somente writer/CLI')
    const multicase = readFileSync(path.join(moduleRoot, 'src/simulated-execution-multicase.ts'), 'utf8')
    assert.ok(!multicase.includes('node:fs'), 'agregacao multicase e pura')
})
