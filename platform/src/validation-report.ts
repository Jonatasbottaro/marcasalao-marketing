/**
 * Relatorio estruturado de validacao de manifesto de projeto.
 *
 * Regras de determinismo: nenhuma marca de tempo, nenhum identificador
 * aleatorio, nenhum caminho absoluto da maquina e ordem de emissao fixa.
 * A automacao deve confiar nos codigos estaveis, nao nas mensagens livres.
 */

import type { RequiresInspection, OutputPlanGeometry } from './output-plan-contract.js'
import type { OutputMediaKind, RuleContext } from './output-profiles/types.js'

export interface ValidationIssue {
    /** Codigo estavel do erro ou aviso (ver README do modulo). */
    code: string
    /** Caminho logico do campo dentro do manifesto, ex.: "contentPolicies.requireApprovedBriefing". */
    path: string
    /** Mensagem legivel, estavel para a mesma entrada. */
    message: string
}

export interface ProjectValidationReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    /** id declarado no manifesto, quando disponivel como string. */
    projectId: string | null
    /** schemaVersion declarado, quando disponivel como numero. */
    schemaVersion: number | null
    /** Tamanho declarado de outputProfiles (0 quando ausente ou malformado). */
    outputProfileCount: number
}

export const VALID_SUMMARY = 'Project manifest is valid.'

export function invalidSummary(errorCount: number): string {
    return `Project manifest is invalid: ${errorCount} error(s).`
}

/** Formato ecoado no relatorio de composicao, quando bem formado. */
export interface CompositionReportFormat {
    profile: string
    width: number
    height: number
    fps: number
}

/**
 * Relatorio estruturado de validacao de composicao (estrutura propria e
 * vinculo com um ProjectManifest). Mesmas regras de determinismo do relatorio
 * de projeto: sem timestamp, sem caminho absoluto, sem ID aleatorio, ordem
 * estavel e codigos estaveis.
 */
export interface CompositionValidationReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    /** projectId declarado na composicao, quando disponivel como string. */
    projectId: string | null
    /** id declarado na composicao, quando disponivel como string. */
    compositionId: string | null
    /** schemaVersion declarado, quando disponivel como numero. */
    schemaVersion: number | null
    /** Quantidade de cenas declaradas (0 quando ausente ou malformado). */
    sceneCount: number
    /**
     * Soma dos durationMs inteiros positivos das cenas; null quando a soma
     * ultrapassa Number.MAX_SAFE_INTEGER (COMPOSITION_DURATION_OVERFLOW).
     */
    totalDurationMs: number | null
    /** Formato ecoado quando bem formado; null caso contrario. */
    format: CompositionReportFormat | null
    /** Adaptador de renderizacao declarado, quando disponivel como string. */
    rendererAdapter: string | null
}

export const COMPOSITION_VALID_SUMMARY = 'Composition is valid.'

export function compositionInvalidSummary(errorCount: number): string {
    return `Composition is invalid: ${errorCount} error(s).`
}

export function issue(code: string, path: string, message: string): ValidationIssue {
    return { code, path, message }
}

/**
 * Relatorio de resolucao e de validacao do OutputPlan (R001-03). Mesmas regras
 * de determinismo deste arquivo. Os campos ecoados vém do plano lido ou do
 * catalogo quando o plano nao existe; `pendingRuleIds` e `requiresInspection`
 * dizem o que **continua** por certificar, nunca o que foi certificado.
 */
export interface OutputPlanReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    projectId: string | null
    profileId: string | null
    catalogVersion: string | null
    profileRevision: number | null
    mediaKind: OutputMediaKind | null
    /** Contexto declarado; null quando nao informado. Nunca "sem contexto" como string. */
    ruleContext: RuleContext | null
    geometry: OutputPlanGeometry | null
    /** null em plano de imagem: fps nunca e 0 nem inventado. */
    fps: number | null
    /** Pendencias nominais do perfil (§2.2): ausencia de numero, nao zero. */
    pendingRuleIds: readonly string[]
    /** Necessidades de inspecao de arquivo, em ordem fixa (§6.2.1). */
    requiresInspection: readonly RequiresInspection[]
}

/**
 * Relatorio de compatibilidade Composition v1 x OutputPlan. Os relatorios das
 * duas camadas entram **por inteiro**, sem resumo, para preservar a causa da
 * falha; cada um e null quando aquela camada nao rodou. Avisos das camadas
 * embutidas nao sao copiados para este relatorio.
 */
export interface OutputCompatibilityReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    compositionId: string | null
    profileId: string | null
    ruleContext: RuleContext | null
    /** Soma declarada das cenas; null se ausente, malformada ou em overflow. Nao e duracao de arquivo. */
    totalDurationMs: number | null
    compositionReport: CompositionValidationReport | null
    planReport: OutputPlanReport | null
}

export const OUTPUT_PLAN_VALID_SUMMARY = 'Output plan is valid.'

export function outputPlanInvalidSummary(errorCount: number): string {
    return `Output plan is invalid: ${errorCount} error(s).`
}

export const OUTPUT_COMPAT_VALID_SUMMARY = 'Composition is compatible with the output plan.'

export function outputCompatInvalidSummary(errorCount: number): string {
    return `Composition is not compatible with the output plan: ${errorCount} error(s).`
}
