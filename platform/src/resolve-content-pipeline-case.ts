/**
 * Resolucao segura dos quatro documentos de um caso de pipeline.
 *
 * Recebe o caminho do manifesto e uma raiz de confinamento declarada, le o
 * manifesto, valida a estrutura pelo contrato e resolve cada caminho relativo
 * ao diretorio do manifesto. Todo documento precisa existir e permanecer
 * estritamente dentro da raiz, inclusive depois de resolver symlinks: um
 * caminho lexicalmente interno que aponta para fora via symlink e rejeitado.
 *
 * Camada de I/O controlado: le apenas o manifesto e os documentos referenciados,
 * nunca escreve, nunca acessa rede e nunca ecoa caminho absoluto da maquina em
 * mensagens de erro. A classificacao lexical dos caminhos vem da funcao pura
 * compartilhada `relative-path.ts`; nenhuma regra de marca vive aqui.
 */

import { realpathSync } from 'node:fs'
import path from 'node:path'

import { readJsonFile } from './cli-input.js'
import {
    CASE_DOCUMENT_FIELDS,
    validateCaseManifest,
    type CaseDocumentField,
    type ContentPipelineCaseIssue,
    type ContentPipelineCaseManifest,
    type ContentPipelineCaseManifestReport,
} from './content-pipeline-case-contract.js'
import { inspectRelativePath } from './relative-path.js'

export interface ResolvedCasePaths {
    readonly project: string
    readonly composition: string
    readonly outputPlan: string
    readonly beatPlan: string
}

export type ContentPipelineCaseResolution =
    | {
        readonly ok: true
        readonly manifest: ContentPipelineCaseManifest
        readonly paths: ResolvedCasePaths
    }
    | {
        readonly ok: false
        readonly report: ContentPipelineCaseManifestReport
    }

function issue(code: string, field: string, message: string): ContentPipelineCaseIssue {
    return { code, path: field, message }
}

function failure(caseId: string | null, errors: readonly ContentPipelineCaseIssue[]): ContentPipelineCaseResolution {
    return {
        ok: false,
        report: {
            valid: false,
            errors,
            summary: `Pipeline case manifest is invalid: ${errors.length} error(s).`,
            caseId,
        },
    }
}

/** Contenção estrita: o candidato precisa estar dentro da raiz, nunca ser a propria raiz. */
function isWithinRoot(rootReal: string, candidateReal: string): boolean {
    const relative = path.relative(rootReal, candidateReal)
    return relative !== '' && !relative.startsWith('..') && !path.isAbsolute(relative)
}

/**
 * Resolucao lexica pura de um campo de documento: rejeita violacoes de caminho
 * relativo e qualquer resolucao que escape da raiz declarada (inclusive `..`
 * que o sistema operacional normalizaria para fora). Nao le o filesystem.
 */
export function resolveCaseDocumentPath(
    manifestDir: string,
    rootDir: string,
    field: CaseDocumentField,
    value: string,
): { readonly path: string } | { readonly error: ContentPipelineCaseIssue } {
    for (const violation of inspectRelativePath(value)) {
        // `..` e permitido lexicalmente: o que decide e o confinamento abaixo,
        // que rejeita qualquer resolucao para fora da raiz declarada.
        if (violation === 'TRAVERSAL') continue
        return {
            error: issue(
                `CASE_DOCUMENT_PATH_${violation}`,
                field,
                `${field} must be a safe relative path (${violation.toLowerCase()} is not allowed).`,
            ),
        }
    }

    const root = path.resolve(rootDir)
    const resolved = path.resolve(manifestDir, value)
    if (!isWithinRoot(root, resolved)) {
        return {
            error: issue('CASE_DOCUMENT_PATH_ESCAPE', field, `${field} resolves outside the declared containment root.`),
        }
    }

    return { path: resolved }
}

/**
 * Le e valida o manifesto informado e resolve os quatro documentos sob a raiz
 * de confinamento. Falhas de leitura, estrutura, confinamento ou existencia
 * viram relatorio com codigos estaveis; nenhum caminho absoluto da maquina
 * aparece nas mensagens.
 */
export function resolveContentPipelineCase(
    manifestPath: string,
    rootDir: string,
): ContentPipelineCaseResolution {
    const root = path.resolve(rootDir)

    let rootReal: string
    try {
        rootReal = realpathSync(root)
    } catch {
        return failure(null, [issue('CASE_RESOLUTION_ROOT_INVALID', '', 'The declared containment root does not exist or is not readable.')])
    }

    const manifestFile = readJsonFile(manifestPath)
    if ('error' in manifestFile) {
        const code = manifestFile.error.includes('JSON malformado') ? 'CASE_MANIFEST_MALFORMED' : 'CASE_MANIFEST_UNREADABLE'
        return failure(null, [issue(code, '', 'The pipeline case manifest was not found, is not readable or is not valid JSON.')])
    }

    const manifestReport = validateCaseManifest(manifestFile.value)
    if (!manifestReport.valid) {
        return { ok: false, report: manifestReport }
    }

    const manifest = manifestFile.value as ContentPipelineCaseManifest

    let manifestReal: string
    try {
        manifestReal = realpathSync(path.resolve(manifestPath))
    } catch {
        return failure(manifest.id, [issue('CASE_MANIFEST_UNREADABLE', '', 'The pipeline case manifest was not found or is not readable.')])
    }
    if (!isWithinRoot(rootReal, manifestReal)) {
        return failure(manifest.id, [issue('CASE_RESOLUTION_ESCAPE', '', 'The pipeline case manifest is outside the declared containment root.')])
    }

    const manifestDir = path.dirname(path.resolve(manifestPath))
    const resolved: Record<CaseDocumentField, string> = {
        project: '',
        composition: '',
        outputPlan: '',
        beatPlan: '',
    }

    for (const field of CASE_DOCUMENT_FIELDS) {
        const value = manifest[field]
        const lexical = resolveCaseDocumentPath(manifestDir, root, field, value)
        if ('error' in lexical) {
            return failure(manifest.id, [lexical.error])
        }

        let documentReal: string
        try {
            documentReal = realpathSync(lexical.path)
        } catch {
            return failure(manifest.id, [issue('CASE_DOCUMENT_MISSING', field, `The ${field} document was not found or is not readable.`)])
        }
        if (!isWithinRoot(rootReal, documentReal)) {
            return failure(manifest.id, [issue('CASE_RESOLUTION_ESCAPE', field, `The ${field} document resolves outside the declared containment root.`)])
        }

        resolved[field] = lexical.path
    }

    return { ok: true, manifest, paths: resolved }
}
