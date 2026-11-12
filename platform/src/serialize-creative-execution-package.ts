/**
 * Serializacao canonica do CreativeExecutionPackage v1.
 *
 * JSON com indentacao estavel de dois espacos, ordem de propriedades definida
 * explicitamente pelo contrato (nunca pela ordem do objeto original), arrays
 * na ordem semantica, LF, uma newline final, UTF-8 sem BOM. O mesmo pacote
 * produz bytes identicos; parse seguido de serializacao produz os mesmos
 * bytes. Nenhuma dependencia externa de canonical JSON.
 *
 * Funcao pura: sem I/O, sem relogio, sem aleatoriedade, sem mutacao.
 */

import type {
    CreativeExecutionPackage,
    CreativeExecutionStep,
    ExpectedArtifact,
} from './creative-execution-package-contract.js'

function canonicalStep(step: CreativeExecutionStep): Record<string, unknown> {
    return {
        order: step.order,
        beatId: step.beatId,
        sceneIds: [...step.sceneIds],
        startMs: step.startMs,
        durationMs: step.durationMs,
        endMs: step.endMs,
        narrativeFunction: step.narrativeFunction,
        motionIntent: step.motionIntent,
        transitionIn: step.transitionIn,
        transitionOut: step.transitionOut,
        ...(step.onScreenText !== undefined ? { onScreenText: step.onScreenText } : {}),
        ...(step.narrationText !== undefined ? { narrationText: step.narrationText } : {}),
    }
}

function canonicalArtifact(artifact: ExpectedArtifact): Record<string, unknown> {
    return {
        id: artifact.id,
        kind: artifact.kind,
        required: artifact.required,
        logicalName: artifact.logicalName,
        contentType: artifact.contentType,
    }
}

/**
 * Serializa o pacote na forma canonica. A reconstrucao explicita campo a campo
 * garante que duas representacoes logicamente iguais com ordens de chaves
 * diferentes produzam exatamente os mesmos bytes.
 */
export function serializeCreativeExecutionPackage(executionPackage: CreativeExecutionPackage): string {
    const output = executionPackage.output
    const canonical = {
        schemaVersion: executionPackage.schemaVersion,
        packageId: executionPackage.packageId,
        projectId: executionPackage.projectId,
        compositionId: executionPackage.compositionId,
        outputPlanId: executionPackage.outputPlanId,
        beatPlanId: executionPackage.beatPlanId,
        output: {
            profileId: output.profileId,
            mediaKind: output.mediaKind,
            width: output.width,
            height: output.height,
            aspectRatio: output.aspectRatio,
            fps: output.fps,
            ...(output.plannedContainer !== undefined ? { plannedContainer: output.plannedContainer } : {}),
            rendererAdapter: output.rendererAdapter,
            durationMs: output.durationMs,
        },
        timeline: executionPackage.timeline.map(canonicalStep),
        expectedArtifacts: executionPackage.expectedArtifacts.map(canonicalArtifact),
        source: {
            projectId: executionPackage.source.projectId,
            compositionId: executionPackage.source.compositionId,
            outputPlanId: executionPackage.source.outputPlanId,
            beatPlanId: executionPackage.source.beatPlanId,
            projectSchemaVersion: executionPackage.source.projectSchemaVersion,
            compositionSchemaVersion: executionPackage.source.compositionSchemaVersion,
            outputPlanSchemaVersion: executionPackage.source.outputPlanSchemaVersion,
            beatPlanSchemaVersion: executionPackage.source.beatPlanSchemaVersion,
        },
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}
