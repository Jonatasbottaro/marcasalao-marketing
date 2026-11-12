/**
 * Gerador puro do CreativeExecutionPackage v1.
 *
 * So gera pacote quando o ContentPipelineValidationReport informado declara
 * pipeline valido; nao revalida regras duplicadas, nao acessa filesystem,
 * rede, relogio, aleatoriedade ou variaveis de ambiente, nao executa
 * subprocesso, nao importa Temporal, nao renderiza e nao muta as entradas.
 * Todo conteudo vem dos documentos ja validados: nenhum texto e criado ou
 * alterado, nenhum asset, prompt ou midia e inferido.
 *
 * O resultado e discriminado por `ok` e usa codigos de falha estaveis do
 * contrato, sem mensagens tecnicas variaveis.
 */

import type { BeatPlan } from './beat-plan-contract.js'
import type { Composition } from './composition-contract.js'
import {
    deriveExecutionPackageId,
    EXPECTED_ARTIFACT_KINDS,
    type CreativeExecutionPackage,
    type CreativeExecutionPackageCreationResult,
    type CreativeExecutionStep,
    type ExpectedArtifact,
} from './creative-execution-package-contract.js'
import type {
    ContentPipelineValidationInput,
    ContentPipelineValidationReport,
} from './content-pipeline-validation-contract.js'
import { findOutputProfile } from './output-profiles/catalog.js'
import type { VideoOutputProfile } from './output-profiles/types.js'
import { readOutputPlan } from './validate-output-plan.js'
import type {
    BeatPlanValidationReport,
    CompositionValidationReport,
} from './validation-report.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stageReport<T>(report: ContentPipelineValidationReport, stage: string): T | null {
    const found = report.stages.find((item) => item.stage === stage)
    if (found === undefined || found.report === null) return null
    return found.report as T
}

/**
 * Cria o pacote de execucao a partir dos quatro documentos e do relatorio
 * consolidado ja emitido pelo pipeline. A ordem de verificacao e fixa:
 * validade do pipeline -> identificadores -> configuracao de saida ->
 * duracoes -> timeline -> perfil -> versoes de origem.
 */
export function createCreativeExecutionPackage(
    input: ContentPipelineValidationInput,
    report: ContentPipelineValidationReport,
): CreativeExecutionPackageCreationResult {
    if (!report.valid) {
        return {
            ok: false,
            failureCode: report.blockedStages.length > 0 ? 'PIPELINE_STAGE_BLOCKED' : 'PIPELINE_INVALID',
        }
    }

    const projectId = report.projectId
    const compositionId = report.compositionId
    const outputPlanId = report.outputPlanId
    const beatPlanId = report.beatPlanId
    if (projectId === null || compositionId === null || outputPlanId === null || beatPlanId === null) {
        return { ok: false, failureCode: 'REQUIRED_ID_UNAVAILABLE' }
    }

    const plan = readOutputPlan(input.outputPlan)
    if (plan === null || plan.mediaKind !== 'video') {
        return { ok: false, failureCode: 'UNSUPPORTED_OUTPUT_CONFIGURATION' }
    }

    const compositionReport = stageReport<CompositionValidationReport>(report, 'composition')
    const beatPlanReport = stageReport<BeatPlanValidationReport>(report, 'beat-plan')
    if (compositionReport === null || beatPlanReport === null) {
        return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
    }
    const compositionDurationMs = compositionReport.totalDurationMs
    const beatDurationMs = beatPlanReport.totalDurationMs
    if (compositionDurationMs === null || beatDurationMs === null || compositionReport.rendererAdapter === null) {
        return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
    }
    if (compositionDurationMs !== beatDurationMs) {
        return { ok: false, failureCode: 'DURATION_MISMATCH' }
    }

    const beatPlan = input.beatPlan as BeatPlan
    const composition = input.composition as Composition
    if (!isPlainObject(beatPlan) || !Array.isArray(beatPlan.beats) || !isPlainObject(composition) || !Array.isArray(composition.scenes)) {
        return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
    }
    const sceneIds = new Set(composition.scenes.map((scene) => scene.id))

    const timeline: CreativeExecutionStep[] = []
    let expectedStartMs = 0
    for (const beat of beatPlan.beats) {
        if (
            !isPlainObject(beat)
            || typeof beat.id !== 'string'
            || typeof beat.order !== 'number'
            || typeof beat.startMs !== 'number'
            || typeof beat.durationMs !== 'number'
            || !Array.isArray(beat.sceneIds)
        ) {
            return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
        }
        if (beat.order !== timeline.length + 1 || beat.startMs !== expectedStartMs) {
            return { ok: false, failureCode: 'DURATION_MISMATCH' }
        }
        for (const sceneId of beat.sceneIds) {
            if (typeof sceneId !== 'string' || !sceneIds.has(sceneId)) {
                return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
            }
        }
        const endMs = beat.startMs + beat.durationMs
        if (!Number.isSafeInteger(endMs)) {
            return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
        }
        const step: CreativeExecutionStep = {
            order: beat.order,
            beatId: beat.id,
            sceneIds: [...beat.sceneIds],
            startMs: beat.startMs,
            durationMs: beat.durationMs,
            endMs,
            narrativeFunction: beat.narrativeFunction,
            motionIntent: beat.motionIntent,
            transitionIn: beat.transitionIn,
            transitionOut: beat.transitionOut,
            ...(beat.onScreenText !== undefined ? { onScreenText: beat.onScreenText } : {}),
            ...(beat.narration !== undefined ? { narrationText: beat.narration.text } : {}),
        }
        timeline.push(step)
        expectedStartMs = endMs
    }
    if (timeline.length === 0 || expectedStartMs !== compositionDurationMs) {
        return { ok: false, failureCode: 'DURATION_MISMATCH' }
    }

    const profile = findOutputProfile(plan.profileId)
    if (profile === null || profile.mediaKind !== 'video') {
        return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
    }
    const videoProfile = profile as VideoOutputProfile

    const schemaVersions = [
        (input.project as Record<string, unknown>).schemaVersion,
        (input.composition as Record<string, unknown>).schemaVersion,
        (input.outputPlan as Record<string, unknown>).schemaVersion,
        (input.beatPlan as Record<string, unknown>).schemaVersion,
    ]
    if (schemaVersions.some((version) => typeof version !== 'number')) {
        return { ok: false, failureCode: 'INTERNAL_INVARIANT_FAILED' }
    }

    const packageId = deriveExecutionPackageId({ projectId, compositionId, outputPlanId, beatPlanId })

    const output = {
        profileId: plan.profileId,
        mediaKind: 'video' as const,
        width: plan.video.width,
        height: plan.video.height,
        aspectRatio: plan.video.aspectRatio,
        fps: plan.video.fps,
        ...(videoProfile.plannedContainer !== undefined ? { plannedContainer: videoProfile.plannedContainer } : {}),
        rendererAdapter: compositionReport.rendererAdapter,
        durationMs: compositionDurationMs,
    }

    const expectedArtifacts: ExpectedArtifact[] = EXPECTED_ARTIFACT_KINDS.map((kind) => {
        if (kind === 'primary-output') {
            const extension = videoProfile.plannedContainer !== undefined ? `.${videoProfile.plannedContainer}` : ''
            return {
                id: kind,
                kind,
                required: true,
                logicalName: `${packageId}-primary-output${extension}`,
                contentType: plan.mediaKind,
            }
        }
        if (kind === 'captions') {
            return { id: kind, kind, required: true, logicalName: `${packageId}-captions.srt`, contentType: 'text/srt' }
        }
        if (kind === 'narration-script') {
            return { id: kind, kind, required: true, logicalName: `${packageId}-narration-script.txt`, contentType: 'text/plain' }
        }
        return { id: kind, kind, required: true, logicalName: `${packageId}-execution-report.json`, contentType: 'application/json' }
    })

    const executionPackage: CreativeExecutionPackage = {
        schemaVersion: 1,
        packageId,
        projectId,
        compositionId,
        outputPlanId,
        beatPlanId,
        output,
        timeline,
        expectedArtifacts,
        source: {
            projectId,
            compositionId,
            outputPlanId,
            beatPlanId,
            projectSchemaVersion: schemaVersions[0] as number,
            compositionSchemaVersion: schemaVersions[1] as number,
            outputPlanSchemaVersion: schemaVersions[2] as number,
            beatPlanSchemaVersion: schemaVersions[3] as number,
        },
    }

    return { ok: true, package: executionPackage }
}
