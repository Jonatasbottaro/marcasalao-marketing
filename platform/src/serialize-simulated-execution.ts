/**
 * Serializacao canonica dos documentos da execucao simulada v1.
 *
 * Ordem de campos fixa e explicita, indentacao de dois espacos, LF, uma
 * newline final, UTF-8 sem BOM, round trip estavel e bytes identicos entre
 * execucoes. Nenhuma dependencia externa de canonical JSON. Funcoes puras:
 * sem I/O, sem relogio, sem aleatoriedade, sem mutacao.
 */

import type {
    SimulatedExecutionPlan,
    SimulatedExecutionStep,
    SimulatedExpectedArtifact,
} from './simulated-execution-plan-contract.js'
import type {
    SimulatedArtifactReport,
    SimulatedExecutionEvent,
    SimulatedExecutionReport,
} from './simulated-execution-report-contract.js'

/** Manifesto logico do artefato primario simulado: descreve, nao cria midia. */
export interface SimulatedPrimaryOutputManifest {
    readonly logicalName: string
    readonly mediaKind: 'video'
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
    readonly fps: number
    readonly durationMs: number
    readonly profileId: string
    readonly simulated: true
}

function canonicalInputs(inputs: SimulatedExecutionStep['inputs']): Record<string, unknown> {
    return {
        ...(inputs.sceneId !== undefined ? { sceneId: inputs.sceneId } : {}),
        ...(inputs.startMs !== undefined ? { startMs: inputs.startMs } : {}),
        ...(inputs.durationMs !== undefined ? { durationMs: inputs.durationMs } : {}),
        ...(inputs.endMs !== undefined ? { endMs: inputs.endMs } : {}),
        ...(inputs.onScreenText !== undefined ? { onScreenText: inputs.onScreenText } : {}),
        ...(inputs.narrationText !== undefined ? { narrationText: inputs.narrationText } : {}),
        ...(inputs.motionIntent !== undefined ? { motionIntent: inputs.motionIntent } : {}),
        ...(inputs.transitionIn !== undefined ? { transitionIn: inputs.transitionIn } : {}),
        ...(inputs.transitionOut !== undefined ? { transitionOut: inputs.transitionOut } : {}),
    }
}

function canonicalStep(step: SimulatedExecutionStep): Record<string, unknown> {
    return {
        stepId: step.stepId,
        order: step.order,
        beatId: step.beatId,
        sceneId: step.sceneId,
        startMs: step.startMs,
        durationMs: step.durationMs,
        endMs: step.endMs,
        operation: step.operation,
        inputs: canonicalInputs(step.inputs),
        expectedArtifactIds: [...step.expectedArtifactIds],
    }
}

function canonicalExpectedArtifact(artifact: SimulatedExpectedArtifact): Record<string, unknown> {
    return {
        id: artifact.id,
        kind: artifact.kind,
        required: artifact.required,
        logicalName: artifact.logicalName,
        contentType: artifact.contentType,
    }
}

export function serializeSimulatedExecutionPlan(plan: SimulatedExecutionPlan): string {
    const canonical = {
        schemaVersion: plan.schemaVersion,
        executionId: plan.executionId,
        packageId: plan.packageId,
        caseId: plan.caseId,
        adapter: plan.adapter,
        output: {
            profileId: plan.output.profileId,
            mediaKind: plan.output.mediaKind,
            width: plan.output.width,
            height: plan.output.height,
            aspectRatio: plan.output.aspectRatio,
            fps: plan.output.fps,
            durationMs: plan.output.durationMs,
        },
        steps: plan.steps.map(canonicalStep),
        expectedArtifacts: plan.expectedArtifacts.map(canonicalExpectedArtifact),
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}

function canonicalEvent(event: SimulatedExecutionEvent): Record<string, unknown> {
    return {
        sequence: event.sequence,
        type: event.type,
        executionId: event.executionId,
        ...(event.stepId !== undefined ? { stepId: event.stepId } : {}),
        ...(event.artifactId !== undefined ? { artifactId: event.artifactId } : {}),
        ...(event.failureCode !== undefined ? { failureCode: event.failureCode } : {}),
    }
}

export function serializeSimulatedExecutionEvents(events: readonly SimulatedExecutionEvent[]): string {
    return `${JSON.stringify(events.map(canonicalEvent), null, 2)}\n`
}

function canonicalArtifactReport(artifact: SimulatedArtifactReport): Record<string, unknown> {
    return {
        id: artifact.id,
        logicalName: artifact.logicalName,
        contentType: artifact.contentType,
        sha256: artifact.sha256,
    }
}

export function serializeSimulatedExecutionReport(report: SimulatedExecutionReport): string {
    const canonical = {
        schemaVersion: report.schemaVersion,
        executionId: report.executionId,
        packageId: report.packageId,
        status: report.status,
        resumedFromStatus: report.resumedFromStatus,
        completedSteps: [...report.completedSteps],
        failedStepId: report.failedStepId,
        failureCode: report.failureCode,
        artifactCount: report.artifactCount,
        artifacts: report.artifacts.map(canonicalArtifactReport),
        events: report.events.map(canonicalEvent),
        summary: report.summary,
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}

export function serializeSimulatedPrimaryOutputManifest(manifest: SimulatedPrimaryOutputManifest): string {
    const canonical = {
        logicalName: manifest.logicalName,
        mediaKind: manifest.mediaKind,
        width: manifest.width,
        height: manifest.height,
        aspectRatio: manifest.aspectRatio,
        fps: manifest.fps,
        durationMs: manifest.durationMs,
        profileId: manifest.profileId,
        simulated: manifest.simulated,
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}

/**
 * Manifesto de hashes: chaves sao caminhos relativos logicos (nunca absolutos),
 * ordenados lexicograficamente; valores sao SHA-256 em hex minusculo.
 */
export function serializeSimulatedHashes(hashes: Readonly<Record<string, string>>): string {
    const canonical: Record<string, string> = {}
    for (const key of Object.keys(hashes).sort()) {
        canonical[key] = hashes[key] as string
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}
