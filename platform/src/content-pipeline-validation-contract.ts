/**
 * Contrato de validacao consolidada do pipeline criativo de conteudo
 * (ProjectManifest -> Composition -> OutputPlan -> Compatibility -> BeatPlan).
 *
 * Nucleo estritamente puro e deterministico: sem timestamp, sem IDs aleatorios,
 * sem I/O de rede ou disco, sem variaveis de ambiente e sem dependencias do Temporal.
 */

import type { TenantCompatibilityReport } from './tenant-policy-contract.js'
import type {
    BeatPlanValidationReport,
    CompositionValidationReport,
    OutputCompatibilityReport,
    OutputPlanReport,
    ProjectValidationReport,
} from './validation-report.js'

export type ContentPipelineStage =
    | 'project'
    | 'composition'
    | 'output-plan'
    | 'output-compatibility'
    | 'beat-plan'
    // Etapa 6: rotulo para issues da checagem ExecutionPackage x TenantPolicy,
    // que e aditiva e NAO entra no DAG de 5 estagios (CONTENT_PIPELINE_STAGES).
    | 'tenant-policy'
    // Etapa 8: rotulo para a invariante global `autoPublish: false` (aditiva).
    | 'autopublish'

export const CONTENT_PIPELINE_STAGES: readonly ContentPipelineStage[] = Object.freeze([
    'project',
    'composition',
    'output-plan',
    'output-compatibility',
    'beat-plan',
] as const)

export type ContentPipelineStageStatus = 'valid' | 'invalid' | 'blocked'

export interface ContentPipelineIssue {
    readonly stage: ContentPipelineStage
    readonly severity: 'error' | 'warning'
    readonly code: string
    readonly path: string
    readonly message: string
}

export interface ProjectStageResult {
    readonly stage: 'project'
    readonly status: 'valid' | 'invalid'
    readonly report: ProjectValidationReport
    readonly blockedBy: null
}

export interface CompositionStageResult {
    readonly stage: 'composition'
    readonly status: ContentPipelineStageStatus
    readonly report: CompositionValidationReport | null
    readonly blockedBy: ContentPipelineStage | null
}

export interface OutputPlanStageResult {
    readonly stage: 'output-plan'
    readonly status: ContentPipelineStageStatus
    readonly report: OutputPlanReport | null
    readonly blockedBy: ContentPipelineStage | null
}

export interface OutputCompatibilityStageResult {
    readonly stage: 'output-compatibility'
    readonly status: ContentPipelineStageStatus
    readonly report: OutputCompatibilityReport | null
    readonly blockedBy: ContentPipelineStage | null
}

export interface BeatPlanStageResult {
    readonly stage: 'beat-plan'
    readonly status: ContentPipelineStageStatus
    readonly report: BeatPlanValidationReport | null
    readonly blockedBy: ContentPipelineStage | null
}

export type ContentPipelineStageResult =
    | ProjectStageResult
    | CompositionStageResult
    | OutputPlanStageResult
    | OutputCompatibilityStageResult
    | BeatPlanStageResult

export interface ContentPipelineValidationReport {
    readonly schemaVersion: 1
    readonly valid: boolean
    readonly summary: string
    readonly projectId: string | null
    readonly compositionId: string | null
    readonly outputPlanId: string | null
    readonly beatPlanId: string | null
    readonly stages: readonly ContentPipelineStageResult[]
    readonly errors: readonly ContentPipelineIssue[]
    readonly warnings: readonly ContentPipelineIssue[]
    readonly completedStages: readonly ContentPipelineStage[]
    readonly blockedStages: readonly ContentPipelineStage[]
    /**
     * Resultado da checagem opcional ExecutionPackage x TenantPolicy. Presente
     * somente quando o input traz `executionPackage` e `tenantPolicy`; ausente
     * para o pipeline classico de 5 estagios (retrocompativel).
     */
    readonly tenantCompatibility?: TenantCompatibilityReport
}

export interface ContentPipelineValidationInput {
    readonly project: unknown
    readonly composition: unknown
    readonly outputPlan: unknown
    readonly beatPlan: unknown
    /**
     * Entradas opcionais da Etapa 6: quando ambas informadas, dispara a checagem
     * de compatibilidade ExecutionPackage v1 x TenantPolicyContract v1 (aditiva,
     * fora do DAG de 5 estagios). Ausentes mantem o comportamento historico.
     */
    readonly executionPackage?: unknown
    readonly tenantPolicy?: unknown
}

export const PIPELINE_VALID_SUMMARY = 'Content pipeline is valid.'

export function pipelineInvalidSummary(
    errorCount: number,
    warningCount: number,
    blockedCount: number,
): string {
    return `Content pipeline is invalid: ${errorCount} error(s), ${warningCount} warning(s), ${blockedCount} blocked stage(s).`
}
