/**
 * Agregador e validador consolidado do pipeline criativo de conteudo.
 *
 * Executa a validacao em ordem deterministica fixa:
 * 1. ProjectManifest
 * 2. Composition (contra ProjectManifest)
 * 3. OutputPlan (contra ProjectManifest)
 * 4. OutputCompatibility (Composition contra OutputPlan)
 * 5. BeatPlan (contra ProjectManifest e Composition)
 *
 * Regras de bloqueio (DAG de dependencias):
 * - Project invalido:
 *     project: invalid;
 *     composition: blocked (por 'project');
 *     output-plan: blocked (por 'project');
 *     output-compatibility: blocked (por 'project');
 *     beat-plan: blocked (por 'project').
 * - Composition invalida (com Project valido):
 *     project: valid;
 *     composition: invalid;
 *     output-plan: avaliado (depende apenas do Project valido);
 *     output-compatibility: blocked (por 'composition');
 *     beat-plan: blocked (por 'composition').
 * - OutputPlan invalido:
 *     project e composition preservados;
 *     output-plan: invalid;
 *     output-compatibility: blocked (por 'output-plan');
 *     beat-plan: avaliado (depende apenas de Project e Composition validos).
 * - OutputCompatibility invalida:
 *     output-compatibility: invalid;
 *     beat-plan: avaliado (depende apenas de Project e Composition validos).
 * - BeatPlan invalido:
 *     estagios anteriores preservados;
 *     beat-plan: invalid.
 *
 * Imutabilidade: os objetos recebidos em input nunca sao mutados.
 * Determinismo: sem I/O, sem Date, sem valores pseudoaleatorios, sem variaveis de ambiente.
 */

import { validateBeatPlan } from './validate-beat-plan.js'
import { validateCompositionForOutputPlan } from './validate-composition-output.js'
import { validateComposition } from './validate-composition.js'
import { validateOutputPlan } from './validate-output-plan.js'
import { validateProjectManifest } from './validate-project.js'
import {
    PIPELINE_VALID_SUMMARY,
    pipelineInvalidSummary,
    type BeatPlanStageResult,
    type CompositionStageResult,
    type ContentPipelineIssue,
    type ContentPipelineStage,
    type ContentPipelineStageResult,
    type ContentPipelineValidationInput,
    type ContentPipelineValidationReport,
    type OutputCompatibilityStageResult,
    type OutputPlanStageResult,
    type ProjectStageResult,
} from './content-pipeline-validation-contract.js'
import type {
    BeatPlanValidationReport,
    CompositionValidationReport,
    OutputCompatibilityReport,
    OutputPlanReport,
    ProjectValidationReport,
    ValidationIssue,
} from './validation-report.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function mapIssues(
    stage: ContentPipelineStage,
    severity: 'error' | 'warning',
    issues: readonly ValidationIssue[],
): ContentPipelineIssue[] {
    return issues.map((item) => ({
        stage,
        severity,
        code: item.code,
        path: item.path,
        message: item.message,
    }))
}

export function validateContentPipeline(
    input: unknown,
): ContentPipelineValidationReport {
    const errors: ContentPipelineIssue[] = []
    const warnings: ContentPipelineIssue[] = []

    if (!isPlainObject(input)) {
        const rootError: ContentPipelineIssue = {
            stage: 'project',
            severity: 'error',
            code: 'PIPELINE_INPUT_INVALID',
            path: '',
            message: 'Input must be a JSON object containing project, composition, outputPlan and beatPlan.',
        }
        const emptyProjectReport: ProjectValidationReport = {
            valid: false,
            errors: [{ code: 'PIPELINE_INPUT_INVALID', path: '', message: rootError.message }],
            warnings: [],
            summary: 'Project manifest is invalid: 1 error(s).',
            projectId: null,
            schemaVersion: null,
            outputProfileCount: 0,
        }
        const stages: readonly ContentPipelineStageResult[] = [
            { stage: 'project', status: 'invalid', report: emptyProjectReport, blockedBy: null },
            { stage: 'composition', status: 'blocked', report: null, blockedBy: 'project' },
            { stage: 'output-plan', status: 'blocked', report: null, blockedBy: 'project' },
            { stage: 'output-compatibility', status: 'blocked', report: null, blockedBy: 'project' },
            { stage: 'beat-plan', status: 'blocked', report: null, blockedBy: 'project' },
        ]
        return {
            schemaVersion: 1,
            valid: false,
            summary: pipelineInvalidSummary(1, 0, 4),
            projectId: null,
            compositionId: null,
            outputPlanId: null,
            beatPlanId: null,
            stages,
            errors: [rootError],
            warnings: [],
            completedStages: ['project'],
            blockedStages: ['composition', 'output-plan', 'output-compatibility', 'beat-plan'],
        }
    }

    const typedInput = input as Partial<ContentPipelineValidationInput>
    const projectInput = typedInput.project
    const compositionInput = typedInput.composition
    const outputPlanInput = typedInput.outputPlan
    const beatPlanInput = typedInput.beatPlan

    // 1. ProjectManifest
    const projectReport = validateProjectManifest(projectInput)
    const projectStage: ProjectStageResult = {
        stage: 'project',
        status: projectReport.valid ? 'valid' : 'invalid',
        report: projectReport,
        blockedBy: null,
    }
    errors.push(...mapIssues('project', 'error', projectReport.errors))
    warnings.push(...mapIssues('project', 'warning', projectReport.warnings))

    let compositionStage: CompositionStageResult
    let outputPlanStage: OutputPlanStageResult
    let outputCompatStage: OutputCompatibilityStageResult
    let beatPlanStage: BeatPlanStageResult

    let compositionReport: CompositionValidationReport | null = null
    let outputPlanReport: OutputPlanReport | null = null
    let outputCompatReport: OutputCompatibilityReport | null = null
    let beatPlanReport: BeatPlanValidationReport | null = null

    if (!projectReport.valid) {
        // Project invalido bloqueia todos os estagios dependentes
        compositionStage = { stage: 'composition', status: 'blocked', report: null, blockedBy: 'project' }
        outputPlanStage = { stage: 'output-plan', status: 'blocked', report: null, blockedBy: 'project' }
        outputCompatStage = { stage: 'output-compatibility', status: 'blocked', report: null, blockedBy: 'project' }
        beatPlanStage = { stage: 'beat-plan', status: 'blocked', report: null, blockedBy: 'project' }
    } else {
        // 2. Composition (Project e valido)
        compositionReport = validateComposition(compositionInput, projectInput)
        compositionStage = {
            stage: 'composition',
            status: compositionReport.valid ? 'valid' : 'invalid',
            report: compositionReport,
            blockedBy: null,
        }
        errors.push(...mapIssues('composition', 'error', compositionReport.errors))
        warnings.push(...mapIssues('composition', 'warning', compositionReport.warnings))

        // 3. OutputPlan (Project e valido)
        outputPlanReport = validateOutputPlan(outputPlanInput, projectInput)
        outputPlanStage = {
            stage: 'output-plan',
            status: outputPlanReport.valid ? 'valid' : 'invalid',
            report: outputPlanReport,
            blockedBy: null,
        }
        errors.push(...mapIssues('output-plan', 'error', outputPlanReport.errors))
        warnings.push(...mapIssues('output-plan', 'warning', outputPlanReport.warnings))

        // 4. OutputCompatibility (requer Composition e OutputPlan validos)
        if (!compositionReport.valid) {
            outputCompatStage = {
                stage: 'output-compatibility',
                status: 'blocked',
                report: null,
                blockedBy: 'composition',
            }
        } else if (!outputPlanReport.valid) {
            outputCompatStage = {
                stage: 'output-compatibility',
                status: 'blocked',
                report: null,
                blockedBy: 'output-plan',
            }
        } else {
            outputCompatReport = validateCompositionForOutputPlan(
                compositionInput,
                projectInput,
                outputPlanInput,
            )
            outputCompatStage = {
                stage: 'output-compatibility',
                status: outputCompatReport.valid ? 'valid' : 'invalid',
                report: outputCompatReport,
                blockedBy: null,
            }
            errors.push(...mapIssues('output-compatibility', 'error', outputCompatReport.errors))
            warnings.push(...mapIssues('output-compatibility', 'warning', outputCompatReport.warnings))
        }

        // 5. BeatPlan (requer Project e Composition validos)
        if (!compositionReport.valid) {
            beatPlanStage = {
                stage: 'beat-plan',
                status: 'blocked',
                report: null,
                blockedBy: 'composition',
            }
        } else {
            beatPlanReport = validateBeatPlan(beatPlanInput, compositionInput, projectInput)
            beatPlanStage = {
                stage: 'beat-plan',
                status: beatPlanReport.valid ? 'valid' : 'invalid',
                report: beatPlanReport,
                blockedBy: null,
            }
            errors.push(...mapIssues('beat-plan', 'error', beatPlanReport.errors))
            warnings.push(...mapIssues('beat-plan', 'warning', beatPlanReport.warnings))
        }
    }

    const stages: readonly ContentPipelineStageResult[] = [
        projectStage,
        compositionStage,
        outputPlanStage,
        outputCompatStage,
        beatPlanStage,
    ]

    const completedStages: ContentPipelineStage[] = []
    const blockedStages: ContentPipelineStage[] = []
    for (const stage of stages) {
        if (stage.status === 'blocked') {
            blockedStages.push(stage.stage)
        } else {
            completedStages.push(stage.stage)
        }
    }

    const allValid = stages.every((s) => s.status === 'valid')
    const valid = allValid && errors.length === 0

    const summary = valid
        ? PIPELINE_VALID_SUMMARY
        : pipelineInvalidSummary(errors.length, warnings.length, blockedStages.length)

    const projectId =
        projectReport.projectId ??
        compositionReport?.projectId ??
        outputPlanReport?.projectId ??
        beatPlanReport?.projectId ??
        null

    const compositionId =
        compositionReport?.compositionId ??
        beatPlanReport?.compositionId ??
        null

    const outputPlanId = outputPlanReport?.profileId ?? null

    const beatPlanId = beatPlanReport?.beatPlanId ?? null

    return {
        schemaVersion: 1,
        valid,
        summary,
        projectId,
        compositionId,
        outputPlanId,
        beatPlanId,
        stages,
        errors,
        warnings,
        completedStages,
        blockedStages,
    }
}
