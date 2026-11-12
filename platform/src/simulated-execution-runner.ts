/**
 * Executor local simulado do SimulatedExecutionPlan v1.
 *
 * Percorre os steps em ordem, produz eventos deterministicos, materializa
 * artefatos TEXTUAIS simulados (nunca midia) e devolve relatorio imutavel.
 * O adaptador `simulation` e uma ferramenta de verificacao do contrato:
 * nao renderiza, nao gera video/imagem/audio, nao usa ferramenta de video, TTS, fornecedor,
 * rede, Temporal, timers, sleep, paralelismo ou processos filhos.
 *
 * Falha controlada (`failAtStepId`) e cancelamento (`cancelAfterSequence`)
 * sao opcoes explicitas de teste do executor simulado; nao pertencem a
 * contratos de producao futura. Nenhum estado global e mantido.
 *
 * Os artefatos logicos derivam exclusivamente do plano: o conteudo e sempre
 * o mesmo para o mesmo plano, independentemente do status. O que muda com
 * falha/cancelamento e quais artefatos foram criados (aque cuja primeira
 * etapa declarante foi concluida) e o conjunto de eventos/steps concluidos.
 */

import { createHash } from 'node:crypto'

import {
    type SimulatedExecutionPlan,
    type SimulatedExecutionStep,
} from './simulated-execution-plan-contract.js'
import {
    SIMULATED_EXECUTION_CANCELLED_SUMMARY,
    SIMULATED_EXECUTION_COMPLETED_SUMMARY,
    SIMULATED_EXECUTION_FAILED_SUMMARY,
    SIMULATED_STEP_FAILURE_CODE,
    type SimulatedArtifactReport,
    type SimulatedExecutionEvent,
    type SimulatedExecutionReport,
    type SimulatedExecutionStatus,
    type SimulatedResumeIncompatibilityCode,
} from './simulated-execution-report-contract.js'
import {
    serializeSimulatedPrimaryOutputManifest,
} from './serialize-simulated-execution.js'
import { validateSimulatedExecutionPlan } from './validate-simulated-execution-plan.js'
import { validateSimulatedExecutionReport } from './validate-simulated-execution-report.js'

export interface SimulatedExecutionOptions {
    readonly failAtStepId?: string
    readonly cancelAfterSequence?: number
}

export interface SimulatedArtifactFile {
    readonly id: string
    readonly relativePath: string
    readonly logicalName: string
    readonly contentType: string
    readonly content: string
}

export interface SimulatedExecutionRunResult {
    readonly report: SimulatedExecutionReport
    readonly artifacts: readonly SimulatedArtifactFile[]
}

export type SimulatedResumeCheck =
    | { readonly ok: true }
    | { readonly ok: false; readonly code: SimulatedResumeIncompatibilityCode }

function sha256(content: string): string {
    return createHash('sha256').update(content, 'utf8').digest('hex')
}

/** Agrupa os steps por beat, preservando a ordem da timeline. */
function beatWindows(plan: SimulatedExecutionPlan): Array<{ beatId: string; startMs: number; endMs: number; onScreenText?: string; narrationText?: string }> {
    const windows: Array<{ beatId: string; startMs: number; endMs: number; onScreenText?: string; narrationText?: string }> = []
    for (const step of plan.steps) {
        if (step.operation === 'prepare-scene') {
            windows.push({ beatId: step.beatId, startMs: step.startMs, endMs: step.endMs })
            continue
        }
        if (step.operation === 'apply-text') {
            const window = windows[windows.length - 1]
            if (window !== undefined) {
                if (step.inputs.onScreenText !== undefined) window.onScreenText = step.inputs.onScreenText
                if (step.inputs.narrationText !== undefined) window.narrationText = step.inputs.narrationText
            }
        }
    }
    return windows
}

function textLines(windows: ReturnType<typeof beatWindows>, field: 'onScreenText' | 'narrationText'): string {
    const lines: string[] = []
    for (const window of windows) {
        const text = window[field]
        if (text !== undefined) {
            lines.push(`[${window.startMs}-${window.endMs}] ${text}`)
        }
    }
    return lines.length === 0 ? '' : `${lines.join('\n')}\n`
}

/**
 * Materializa os artefatos textuais simulados a partir do plano. Conteudo
 * deterministico, sem data, hostname, usuario ou caminho absoluto. Nenhum
 * arquivo fisico e criado aqui; a escrita vive no writer transacional.
 */
export function buildSimulatedArtifacts(plan: SimulatedExecutionPlan): readonly SimulatedArtifactFile[] {
    const windows = beatWindows(plan)
    const files: SimulatedArtifactFile[] = []
    for (const artifact of plan.expectedArtifacts) {
        if (artifact.kind === 'primary-output') {
            files.push({
                id: artifact.id,
                relativePath: 'artifacts/primary-output.manifest.json',
                logicalName: artifact.logicalName,
                contentType: artifact.contentType,
                content: serializeSimulatedPrimaryOutputManifest({
                    logicalName: artifact.logicalName,
                    mediaKind: plan.output.mediaKind,
                    width: plan.output.width,
                    height: plan.output.height,
                    aspectRatio: plan.output.aspectRatio,
                    fps: plan.output.fps,
                    durationMs: plan.output.durationMs,
                    profileId: plan.output.profileId,
                    simulated: true,
                }),
            })
            continue
        }
        if (artifact.kind === 'captions') {
            files.push({
                id: artifact.id,
                relativePath: 'artifacts/captions.txt',
                logicalName: artifact.logicalName,
                contentType: artifact.contentType,
                content: textLines(windows, 'onScreenText'),
            })
            continue
        }
        if (artifact.kind === 'narration-script') {
            files.push({
                id: artifact.id,
                relativePath: 'artifacts/narration-script.txt',
                logicalName: artifact.logicalName,
                contentType: artifact.contentType,
                content: textLines(windows, 'narrationText'),
            })
            continue
        }
        const summaryLines = [
            `executionId: ${plan.executionId}`,
            `packageId: ${plan.packageId}`,
            'adapter: simulation',
            `profile: ${plan.output.profileId}`,
            `mediaKind: ${plan.output.mediaKind}`,
            `geometry: ${plan.output.width}x${plan.output.height} ${plan.output.aspectRatio} fps ${plan.output.fps}`,
            `durationMs: ${plan.output.durationMs}`,
            `steps: ${plan.steps.length}`,
            `beats: ${windows.length}`,
            'simulated: true',
        ]
        files.push({
            id: artifact.id,
            relativePath: 'artifacts/execution-summary.txt',
            logicalName: artifact.logicalName,
            contentType: artifact.contentType,
            content: `${summaryLines.join('\n')}\n`,
        })
    }
    return files
}

/** Indice da primeira etapa que declara cada artefato. */
function firstDeclarationIndex(plan: SimulatedExecutionPlan): Map<string, number> {
    const first = new Map<string, number>()
    plan.steps.forEach((step, index) => {
        for (const artifactId of step.expectedArtifactIds) {
            if (!first.has(artifactId)) first.set(artifactId, index)
        }
    })
    return first
}

interface LoopState {
    readonly events: SimulatedExecutionEvent[]
    readonly completedSteps: string[]
    readonly createdArtifactIds: Set<string>
    status: SimulatedExecutionStatus
    failedStepId: string | null
    failureCode: string | null
    stopped: boolean
}

function emit(state: LoopState, plan: SimulatedExecutionPlan, event: Omit<SimulatedExecutionEvent, 'sequence' | 'executionId'>): void {
    state.events.push({
        sequence: state.events.length + 1,
        executionId: plan.executionId,
        ...event,
    })
}

/**
 * Cancelamento deterministico: quando o numero de eventos emitidos alcanca
 * `cancelAfterSequence`, o proximo evento e execution-cancelled e a execucao
 * para. O evento execution-started sempre existe (primeiro evento).
 */
function shouldCancel(state: LoopState, options: SimulatedExecutionOptions): boolean {
    return options.cancelAfterSequence !== undefined
        && state.events.length >= options.cancelAfterSequence
}

function runSteps(
    plan: SimulatedExecutionPlan,
    options: SimulatedExecutionOptions,
    state: LoopState,
    steps: readonly SimulatedExecutionStep[],
): void {
    for (const step of steps) {
        if (shouldCancel(state, options)) {
            emit(state, plan, { type: 'execution-cancelled' })
            state.status = 'cancelled'
            state.stopped = true
            return
        }
        emit(state, plan, { type: 'step-started', stepId: step.stepId })

        if (options.failAtStepId !== undefined && step.stepId === options.failAtStepId) {
            emit(state, plan, { type: 'step-failed', stepId: step.stepId, failureCode: SIMULATED_STEP_FAILURE_CODE })
            emit(state, plan, { type: 'execution-failed', failureCode: SIMULATED_STEP_FAILURE_CODE })
            state.status = 'failed'
            state.failedStepId = step.stepId
            state.failureCode = SIMULATED_STEP_FAILURE_CODE
            state.stopped = true
            return
        }

        for (const artifactId of step.expectedArtifactIds) {
            if (!state.createdArtifactIds.has(artifactId)) {
                if (shouldCancel(state, options)) {
                    emit(state, plan, { type: 'execution-cancelled' })
                    state.status = 'cancelled'
                    state.stopped = true
                    return
                }
                emit(state, plan, { type: 'artifact-created', stepId: step.stepId, artifactId })
                state.createdArtifactIds.add(artifactId)
            }
        }
        if (shouldCancel(state, options)) {
            emit(state, plan, { type: 'execution-cancelled' })
            state.status = 'cancelled'
            state.stopped = true
            return
        }
        emit(state, plan, { type: 'step-completed', stepId: step.stepId })
        state.completedSteps.push(step.stepId)
    }
}

function finalizeReport(
    plan: SimulatedExecutionPlan,
    state: LoopState,
    artifacts: readonly SimulatedArtifactFile[],
    resumedFromStatus: SimulatedExecutionStatus | null,
): SimulatedExecutionRunResult {
    if (!state.stopped) {
        emit(state, plan, { type: 'execution-completed' })
        state.status = 'completed'
    }
    const completedCount = state.completedSteps.length
    const firstDecl = firstDeclarationIndex(plan)
    const createdArtifacts = artifacts.filter((artifact) => {
        const index = firstDecl.get(artifact.id)
        return index !== undefined && index < completedCount
    })
    const artifactReports: SimulatedArtifactReport[] = createdArtifacts.map((artifact) => ({
        id: artifact.id,
        logicalName: artifact.logicalName,
        contentType: artifact.contentType,
        sha256: sha256(artifact.content),
    }))
    const summary = state.status === 'completed'
        ? SIMULATED_EXECUTION_COMPLETED_SUMMARY
        : state.status === 'failed'
            ? SIMULATED_EXECUTION_FAILED_SUMMARY
            : SIMULATED_EXECUTION_CANCELLED_SUMMARY
    const report: SimulatedExecutionReport = {
        schemaVersion: 1,
        executionId: plan.executionId,
        packageId: plan.packageId,
        status: state.status,
        resumedFromStatus,
        completedSteps: [...state.completedSteps],
        failedStepId: state.failedStepId,
        failureCode: state.failureCode,
        artifactCount: artifactReports.length,
        artifacts: artifactReports,
        events: [...state.events],
        summary,
    }
    return { report, artifacts: createdArtifacts }
}

/**
 * Executa o plano simulado do inicio. O plano e validado antes da execucao;
 * um plano invalido produz relatorio failed com codigo fixo, sem excecao.
 */
export function runSimulatedExecution(
    plan: SimulatedExecutionPlan,
    options: SimulatedExecutionOptions = {},
): SimulatedExecutionRunResult {
    const artifacts = buildSimulatedArtifacts(plan)
    const state: LoopState = {
        events: [],
        completedSteps: [],
        createdArtifactIds: new Set(),
        status: 'running',
        failedStepId: null,
        failureCode: null,
        stopped: false,
    }

    const planReport = validateSimulatedExecutionPlan(plan)
    if (!planReport.valid) {
        emit(state, plan, { type: 'execution-started' })
        emit(state, plan, { type: 'execution-failed', failureCode: 'SIMULATED_PLAN_INVALID' })
        state.status = 'failed'
        state.failureCode = 'SIMULATED_PLAN_INVALID'
        state.stopped = true
        return finalizeReport(plan, state, artifacts, null)
    }

    emit(state, plan, { type: 'execution-started' })
    runSteps(plan, options, state, plan.steps)
    return finalizeReport(plan, state, artifacts, null)
}

/**
 * Verifica se a retomada e compativel: relatorio anterior valido, mesmos
 * executionId/packageId, status failed ou cancelled, steps concluidos como
 * prefixo do plano e hashes dos artefatos conferidos contra o conteudo
 * deterministico do plano.
 */
export function checkSimulatedResume(
    plan: SimulatedExecutionPlan,
    priorReport: unknown,
): SimulatedResumeCheck {
    const validation = validateSimulatedExecutionReport(priorReport)
    if (!validation.valid) {
        return { ok: false, code: 'REPORT_INVALID' }
    }
    const prior = priorReport as SimulatedExecutionReport
    if (prior.executionId !== plan.executionId) {
        return { ok: false, code: 'EXECUTION_ID_MISMATCH' }
    }
    if (prior.packageId !== plan.packageId) {
        return { ok: false, code: 'PACKAGE_ID_MISMATCH' }
    }
    if (prior.status !== 'failed' && prior.status !== 'cancelled') {
        return { ok: false, code: 'STATUS_NOT_RESUMABLE' }
    }
    const completedCount = prior.completedSteps.length
    const prefix = plan.steps.slice(0, completedCount)
    if (
        prefix.length !== completedCount
        || prefix.some((step, index) => step.stepId !== prior.completedSteps[index])
    ) {
        return { ok: false, code: 'REPORT_INVALID' }
    }
    const artifacts = buildSimulatedArtifacts(plan)
    const byId = new Map(artifacts.map((artifact) => [artifact.id, artifact]))
    for (const priorArtifact of prior.artifacts) {
        const current = byId.get(priorArtifact.id)
        if (current === undefined || sha256(current.content) !== priorArtifact.sha256) {
            return { ok: false, code: 'ARTIFACT_HASH_MISMATCH' }
        }
    }
    return { ok: true }
}

/**
 * Retoma a execucao a partir de um relatorio anterior failed/cancelled:
 * preserva steps concluidos e eventos anteriores (sem duplicacao), executa
 * apenas os steps restantes e continua a sequencia de eventos. O novo
 * relatorio indica `resumedFromStatus`.
 */
export function resumeSimulatedExecution(
    plan: SimulatedExecutionPlan,
    priorReport: SimulatedExecutionReport,
    options: SimulatedExecutionOptions = {},
): SimulatedExecutionRunResult {
    const artifacts = buildSimulatedArtifacts(plan)
    const state: LoopState = {
        events: [...priorReport.events],
        completedSteps: [...priorReport.completedSteps],
        createdArtifactIds: new Set(priorReport.artifacts.map((artifact) => artifact.id)),
        status: 'running',
        failedStepId: null,
        failureCode: null,
        stopped: false,
    }
    const remaining = plan.steps.slice(priorReport.completedSteps.length)
    runSteps(plan, options, state, remaining)
    return finalizeReport(plan, state, artifacts, priorReport.status)
}

/** Valida o relatorio produzido (barreira defensiva antes da escrita). */
export function validateRunResult(result: SimulatedExecutionRunResult): boolean {
    return validateSimulatedExecutionReport(result.report).valid
}
