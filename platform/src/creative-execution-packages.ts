/**
 * Camada de aplicacao interna do CreativeExecutionPackage: geracao por caso
 * e multicase sobre o loader de casos e o pipeline consolidado.
 *
 * Fluxo por caso: carrega o caso com confinamento -> executa a validacao
 * consolidada -> se valida, cria o pacote -> valida o pacote -> devolve
 * resultado sanitizado. Uma falha nao impede os demais casos; a ordem e
 * estavel; nenhum registry global mutavel; nenhuma regra por marca.
 *
 * I/O somente atraves do loader de casos; a geracao e a validacao do pacote
 * continuam nas funcoes puras.
 */

import { loadContentPipelineCase } from './content-pipeline-case-loader.js'
import {
    validateContentPipelineCase,
    type ContentPipelineCaseValidationReport,
} from './validate-content-pipeline-case.js'
import {
    createCreativeExecutionPackage,
} from './create-creative-execution-package.js'
import type {
    CreativeExecutionPackage,
    CreativeExecutionPackageFailureCode,
} from './creative-execution-package-contract.js'
import {
    validateCreativeExecutionPackage,
} from './validate-creative-execution-package.js'
import type { ValidationIssue } from './validation-report.js'

export type CreativeExecutionPackageResultStatus =
    | 'generated'
    | 'case-invalid'
    | 'generation-failed'
    | 'package-invalid'

export interface CreativeExecutionPackageResult {
    readonly caseId: string | null
    readonly status: CreativeExecutionPackageResultStatus
    readonly package: CreativeExecutionPackage | null
    readonly failureCode: CreativeExecutionPackageFailureCode | null
    readonly packageErrors: readonly ValidationIssue[]
    readonly summary: string
}

export interface CreativeExecutionPackagesReport {
    readonly schemaVersion: 1
    readonly valid: boolean
    readonly caseCount: number
    readonly packageCount: number
    readonly failedCaseCount: number
    readonly packages: readonly CreativeExecutionPackageResult[]
    readonly summary: string
}

export const EXECUTION_PACKAGES_VALID_SUMMARY = 'All execution packages were generated.'

export function executionPackagesInvalidSummary(failedCount: number, caseCount: number): string {
    return `Execution package generation failed: ${failedCount} of ${caseCount} case(s) failed.`
}

function caseInvalidResult(caseReport: ContentPipelineCaseValidationReport): CreativeExecutionPackageResult {
    return {
        caseId: caseReport.caseId,
        status: 'case-invalid',
        package: null,
        failureCode: null,
        packageErrors: [],
        summary: caseReport.summary,
    }
}

/**
 * Gera o pacote de um caso em disco. O caso precisa estar valido no pipeline
 * consolidado; o pacote gerado e validado antes de ser devolvido.
 */
export function createCreativeExecutionPackageFromCase(
    manifestPath: string,
    rootDir: string,
): CreativeExecutionPackageResult {
    const loaded = loadContentPipelineCase(manifestPath, rootDir)
    if (!loaded.ok) {
        return caseInvalidResult(loaded.report)
    }

    const caseReport = validateContentPipelineCase(loaded.input)
    if (!caseReport.valid || caseReport.pipeline === null) {
        return caseInvalidResult(caseReport)
    }

    const creation = createCreativeExecutionPackage(loaded.input, caseReport.pipeline)
    if (!creation.ok) {
        return {
            caseId: caseReport.caseId,
            status: 'generation-failed',
            package: null,
            failureCode: creation.failureCode,
            packageErrors: [],
            summary: `Execution package generation failed: ${creation.failureCode}.`,
        }
    }

    const validation = validateCreativeExecutionPackage(creation.package)
    if (!validation.valid) {
        return {
            caseId: caseReport.caseId,
            status: 'package-invalid',
            package: null,
            failureCode: null,
            packageErrors: validation.errors,
            summary: validation.summary,
        }
    }

    return {
        caseId: caseReport.caseId,
        status: 'generated',
        package: creation.package,
        failureCode: null,
        packageErrors: [],
        summary: `Execution package generated: ${creation.package.packageId}.`,
    }
}

/**
 * Agrega resultados de geracao em um relatorio multicase. Funcao pura: a
 * ordem recebida e preservada e nenhum resultado e alterado. Uma lista vazia
 * nunca e considerada valida.
 */
export function aggregateCreativeExecutionPackageResults(
    results: readonly CreativeExecutionPackageResult[],
): CreativeExecutionPackagesReport {
    const packageCount = results.filter((result) => result.status === 'generated').length
    const failedCaseCount = results.length - packageCount
    const valid = results.length > 0 && failedCaseCount === 0
    return {
        schemaVersion: 1,
        valid,
        caseCount: results.length,
        packageCount,
        failedCaseCount,
        packages: results,
        summary: valid ? EXECUTION_PACKAGES_VALID_SUMMARY : executionPackagesInvalidSummary(failedCaseCount, results.length),
    }
}

/**
 * Gera pacotes para multiplos casos em disco, na ordem informada. Cada caso e
 * independente: a falha de um nao interrompe os demais.
 */
export function createCreativeExecutionPackagesFromCases(
    manifestPaths: readonly string[],
    rootDir: string,
): CreativeExecutionPackagesReport {
    const results = manifestPaths.map((manifestPath) => createCreativeExecutionPackageFromCase(manifestPath, rootDir))
    return aggregateCreativeExecutionPackageResults(results)
}
