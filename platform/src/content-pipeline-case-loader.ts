/**
 * Camada de I/O dos casos de pipeline: descoberta de manifestos e leitura dos
 * quatro documentos de cada caso.
 *
 * A descoberta varre a raiz informada em ordem deterministica, coleta arquivos
 * `*.pipeline.json` e ignora symlinks (de arquivo ou de diretorio), para que a
 * varredura nunca alcance conteudo fora da raiz. A leitura de cada caso passa
 * pelo resolvedor seguro (`resolve-content-pipeline-case.ts`) e pelo helper
 * compartilhado `cli-input.ts`; nada aqui escreve arquivos ou acessa rede.
 *
 * Mensagens de erro sao sanitizadas: nenhum caminho absoluto da maquina,
 * nenhum stack trace e nenhum conteudo de documento ecoado.
 */

import { readdirSync } from 'node:fs'
import path from 'node:path'

import { readJsonFile } from './cli-input.js'
import {
    CASE_DOCUMENT_FIELDS,
    type ContentPipelineCaseIssue,
    type ContentPipelineCaseManifestReport,
} from './content-pipeline-case-contract.js'
import { resolveContentPipelineCase } from './resolve-content-pipeline-case.js'
import {
    caseFailureReport,
    validateContentPipelineCase,
    type ContentPipelineCaseInput,
    type ContentPipelineCaseValidationReport,
} from './validate-content-pipeline-case.js'

/** Sufixo canonico dos manifestos de caso descobertos pela varredura. */
export const CASE_MANIFEST_SUFFIX = '.pipeline.json'

export type CaseManifestDiscovery =
    | { readonly ok: true; readonly paths: readonly string[] }
    | { readonly ok: false; readonly error: string }

/**
 * Varre a raiz e devolve os caminhos absolutos dos manifestos de caso, em
 * ordem deterministica (caminho relativo com barras, ordenado). Symlinks sao
 * ignorados; diretorios inacessiveis encerram a varredura com erro sanitizado.
 */
export function discoverCaseManifests(rootDir: string): CaseManifestDiscovery {
    const root = path.resolve(rootDir)
    const found: { readonly relative: string; readonly absolute: string }[] = []

    function walk(directory: string, prefix: string): void {
        const entries = readdirSync(directory, { withFileTypes: true })
            .slice()
            .sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0))
        for (const entry of entries) {
            if (entry.isSymbolicLink()) continue
            const relative = prefix ? `${prefix}/${entry.name}` : entry.name
            const absolute = path.join(directory, entry.name)
            if (entry.isDirectory()) {
                walk(absolute, relative)
            } else if (entry.isFile() && entry.name.endsWith(CASE_MANIFEST_SUFFIX)) {
                found.push({ relative, absolute })
            }
        }
    }

    try {
        walk(root, '')
    } catch {
        return { ok: false, error: 'The cases root does not exist or is not readable.' }
    }

    found.sort((left, right) => (left.relative < right.relative ? -1 : left.relative > right.relative ? 1 : 0))
    return { ok: true, paths: found.map((item) => item.absolute) }
}

/** Classifica a falha do resolvedor entre estrutura do manifesto e leitura. */
function resolutionStatus(errors: readonly ContentPipelineCaseIssue[]): 'manifest-invalid' | 'unreadable' {
    const structural = errors.every((item) =>
        item.code === 'CASE_MANIFEST_INVALID'
        || item.code === 'CASE_SCHEMA_VERSION_UNSUPPORTED'
        || item.code === 'CASE_ID_REQUIRED'
        || item.code === 'CASE_ID_INVALID'
        || item.code === 'CASE_UNKNOWN_FIELD'
        || item.code.startsWith('CASE_DOCUMENT_PATH_'),
    )
    return structural ? 'manifest-invalid' : 'unreadable'
}

export type CaseLoadResult =
    | { readonly ok: true; readonly manifestPath: string; readonly input: ContentPipelineCaseInput }
    | { readonly ok: false; readonly manifestPath: string; readonly report: ContentPipelineCaseValidationReport }

/**
 * Le um caso completo: resolve o manifesto sob a raiz de confinamento e le os
 * quatro documentos. Falhas de resolucao viram `manifest-invalid` ou
 * `unreadable`; falhas de leitura dos documentos viram `unreadable` com
 * diagnosticos sanitizados, um por documento, na ordem canonica.
 */
export function loadContentPipelineCase(manifestPath: string, rootDir: string): CaseLoadResult {
    const resolution = resolveContentPipelineCase(manifestPath, rootDir)
    if (!resolution.ok) {
        const status = resolutionStatus(resolution.report.errors)
        const readErrors = status === 'unreadable' ? resolution.report.errors.map((item) => item.message) : []
        return {
            ok: false,
            manifestPath,
            report: caseFailureReport(status, resolution.report, readErrors),
        }
    }

    const documents: Record<string, unknown> = {}
    const readErrors: string[] = []
    for (const field of CASE_DOCUMENT_FIELDS) {
        const file = readJsonFile(resolution.paths[field])
        if ('error' in file) {
            readErrors.push(`The ${field} document was not found, is not readable or is not valid JSON.`)
            continue
        }
        documents[field] = file.value
    }

    if (readErrors.length > 0) {
        const manifestReport: ContentPipelineCaseManifestReport = {
            valid: true,
            errors: [],
            summary: 'Pipeline case manifest is valid.',
            caseId: resolution.manifest.id,
        }
        return { ok: false, manifestPath, report: caseFailureReport('unreadable', manifestReport, readErrors) }
    }

    return {
        ok: true,
        manifestPath,
        input: {
            manifest: resolution.manifest,
            project: documents.project,
            composition: documents.composition,
            outputPlan: documents.outputPlan,
            beatPlan: documents.beatPlan,
        },
    }
}

/**
 * Carrega e valida um caso em um unico passo, devolvendo sempre um relatorio.
 * Usado pela CLI multiprojeto; a funcao pura continua sendo
 * `validateContentPipelineCase` sobre documentos ja lidos.
 */
export function validateContentPipelineCaseFromDisk(
    manifestPath: string,
    rootDir: string,
): ContentPipelineCaseValidationReport {
    const loaded = loadContentPipelineCase(manifestPath, rootDir)
    return loaded.ok ? validateContentPipelineCase(loaded.input) : loaded.report
}
