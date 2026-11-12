/**
 * Validacao de um caso de pipeline e agregacao de multiplos casos.
 *
 * Um caso combina o manifesto estrutural (`ContentPipelineCaseManifest`) com a
 * validacao consolidada dos quatro documentos (`validateContentPipeline`).
 * Este modulo e puro: recebe documentos ja lidos, nunca abre arquivos, nunca
 * acessa rede e nunca muta as entradas. A leitura segura dos documentos vive
 * em `content-pipeline-case-loader.ts` e `resolve-content-pipeline-case.ts`.
 *
 * Estados do caso:
 * - `valid`: manifesto estruturalmente valido e pipeline consolidado valido;
 * - `invalid`: manifesto valido, pipeline consolidado invalido (relatorio preservado);
 * - `manifest-invalid`: o proprio manifesto de caso foi rejeitado;
 * - `unreadable`: manifesto ou documentos nao puderam ser lidos (camada de I/O).
 *
 * Determinismo: sem timestamp, sem IDs aleatorios, sem variaveis de ambiente,
 * ordem de emissao fixa e nenhuma regra de marca no nucleo.
 */

import {
    validateCaseManifest,
    type ContentPipelineCaseIssue,
    type ContentPipelineCaseManifestReport,
} from './content-pipeline-case-contract.js'
import type { ContentPipelineValidationReport } from './content-pipeline-validation-contract.js'
import { validateContentPipeline } from './validate-content-pipeline.js'

export type ContentPipelineCaseStatus = 'valid' | 'invalid' | 'manifest-invalid' | 'unreadable'

/** Entrada de um caso: o manifesto e os quatro documentos ja lidos. */
export interface ContentPipelineCaseInput {
    readonly manifest: unknown
    readonly project: unknown
    readonly composition: unknown
    readonly outputPlan: unknown
    readonly beatPlan: unknown
}

export interface ContentPipelineCaseValidationReport {
    readonly schemaVersion: 1
    readonly status: ContentPipelineCaseStatus
    readonly valid: boolean
    readonly summary: string
    readonly caseId: string | null
    readonly manifestReport: ContentPipelineCaseManifestReport
    /** Relatorio consolidado completo; null quando o caso nao chegou ao pipeline. */
    readonly pipeline: ContentPipelineValidationReport | null
    /** Diagnosticos sanitizados de leitura; vazio quando nao houve falha de I/O. */
    readonly readErrors: readonly string[]
}

export const CASE_VALID_SUMMARY = 'Pipeline case is valid.'
export const CASE_INVALID_SUMMARY = 'Pipeline case is invalid.'

export function caseUnreadableSummary(errorCount: number): string {
    return `Pipeline case is unreadable: ${errorCount} document read error(s).`
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Valida um caso completo em memoria. O manifesto e conferido primeiro: se ele
 * for rejeitado, o pipeline consolidado nao roda e o relatorio registra
 * `manifest-invalid` com os codigos do contrato de caso.
 */
export function validateContentPipelineCase(input: unknown): ContentPipelineCaseValidationReport {
    const envelope = isPlainObject(input) ? input : {}
    const manifestReport = validateCaseManifest(envelope.manifest)
    const caseId = manifestReport.caseId

    if (!manifestReport.valid) {
        return {
            schemaVersion: 1,
            status: 'manifest-invalid',
            valid: false,
            summary: manifestReport.summary,
            caseId,
            manifestReport,
            pipeline: null,
            readErrors: [],
        }
    }

    const pipeline = validateContentPipeline({
        project: envelope.project,
        composition: envelope.composition,
        outputPlan: envelope.outputPlan,
        beatPlan: envelope.beatPlan,
    })

    return {
        schemaVersion: 1,
        status: pipeline.valid ? 'valid' : 'invalid',
        valid: pipeline.valid,
        summary: pipeline.valid ? CASE_VALID_SUMMARY : CASE_INVALID_SUMMARY,
        caseId,
        manifestReport,
        pipeline,
        readErrors: [],
    }
}

/** Constroi o relatorio de caso para falhas de leitura/estrutura da camada de I/O. */
export function caseFailureReport(
    status: 'manifest-invalid' | 'unreadable',
    manifestReport: ContentPipelineCaseManifestReport,
    readErrors: readonly string[] = [],
): ContentPipelineCaseValidationReport {
    return {
        schemaVersion: 1,
        status,
        valid: false,
        summary: status === 'unreadable' ? caseUnreadableSummary(readErrors.length) : manifestReport.summary,
        caseId: manifestReport.caseId,
        manifestReport,
        pipeline: null,
        readErrors,
    }
}

export interface ContentPipelineCasesValidationReport {
    readonly schemaVersion: 1
    readonly valid: boolean
    readonly summary: string
    readonly caseCount: number
    readonly validCount: number
    readonly invalidCount: number
    /** Relatorios individuais preservados por inteiro, na ordem recebida. */
    readonly cases: readonly ContentPipelineCaseValidationReport[]
    /** Erros estruturais do conjunto (lista vazia, ids duplicados). */
    readonly errors: readonly ContentPipelineCaseIssue[]
}

export const CASES_VALID_SUMMARY = 'All pipeline cases are valid.'

export function casesInvalidSummary(invalidCount: number, structuralErrorCount: number): string {
    return `Pipeline cases are invalid: ${invalidCount} invalid case(s), ${structuralErrorCount} structural error(s).`
}

/**
 * Agrega relatorios de casos em um relatorio multiprojeto. A ordem dos casos e
 * preservada; ids duplicados (declarados e nao nulos) sao erro estrutural; uma
 * lista vazia nunca e considerada valida. Nenhum relatorio individual e alterado.
 */
export function aggregateContentPipelineCases(
    cases: readonly ContentPipelineCaseValidationReport[],
): ContentPipelineCasesValidationReport {
    const errors: ContentPipelineCaseIssue[] = []

    if (cases.length === 0) {
        errors.push({ code: 'CASES_EMPTY', path: 'cases', message: 'At least one pipeline case is required.' })
    }

    const seen = new Map<string, number>()
    cases.forEach((caseReport, index) => {
        const id = caseReport.caseId
        if (id === null) return
        const firstIndex = seen.get(id)
        if (firstIndex === undefined) {
            seen.set(id, index)
            return
        }
        errors.push({
            code: 'CASE_DUPLICATE_ID',
            path: `cases[${index}].id`,
            message: `Duplicate case id "${id}" (first declared at cases[${firstIndex}]).`,
        })
    })

    const validCount = cases.filter((caseReport) => caseReport.valid).length
    const invalidCount = cases.length - validCount
    const valid = cases.length > 0 && invalidCount === 0 && errors.length === 0

    return {
        schemaVersion: 1,
        valid,
        summary: valid ? CASES_VALID_SUMMARY : casesInvalidSummary(invalidCount, errors.length),
        caseCount: cases.length,
        validCount,
        invalidCount,
        cases,
        errors,
    }
}
