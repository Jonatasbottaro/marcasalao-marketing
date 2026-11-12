/**
 * Contrato interno de caso do pipeline criativo (ContentPipelineCaseManifest).
 *
 * Um caso amarra os quatro documentos de um consumidor do pipeline consolidado
 * (ProjectManifest, Composition, OutputPlan e BeatPlan) por caminhos relativos
 * ao diretorio do proprio manifesto. O contrato e estrutural: nao le arquivos,
 * nao resolve caminhos e nao conhece nenhum projeto consumidor. Marca, tema,
 * dominio, CTA e politicas continuam sendo dados dos documentos referenciados.
 *
 * A resolucao segura dos caminhos (confinamento na raiz declarada, rejeicao de
 * absoluto, traversal e symlink externo) vive em `resolve-content-pipeline-case.ts`;
 * a validacao consolidada dos quatro documentos continua em `validate-content-pipeline.ts`.
 *
 * Nucleo estritamente puro e deterministico: sem timestamp, sem IDs aleatorios,
 * sem I/O de rede ou disco, sem variaveis de ambiente e sem dependencias do Temporal.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import { inspectRelativePath } from './relative-path.js'

/** Unica versao de schema suportada nesta fatia. */
export const CASE_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
export const CASE_MANIFEST_FIELDS = [
    'schemaVersion',
    'id',
    'project',
    'composition',
    'outputPlan',
    'beatPlan',
] as const

/** Campos que referenciam documentos, na ordem canonica de resolucao. */
export const CASE_DOCUMENT_FIELDS = ['project', 'composition', 'outputPlan', 'beatPlan'] as const

export type CaseDocumentField = (typeof CASE_DOCUMENT_FIELDS)[number]

/**
 * Manifesto declarativo de um caso de pipeline. Os quatro caminhos sao
 * relativos ao diretorio do manifesto; a existencia fisica e o confinamento
 * sao verificados pelo resolvedor, nunca por este contrato.
 */
export interface ContentPipelineCaseManifest {
    readonly schemaVersion: 1
    readonly id: string
    readonly project: string
    readonly composition: string
    readonly outputPlan: string
    readonly beatPlan: string
}

/** Issue do contrato de caso, com a mesma politica de determinismo dos demais relatorios. */
export interface ContentPipelineCaseIssue {
    readonly code: string
    readonly path: string
    readonly message: string
}

export interface ContentPipelineCaseManifestReport {
    readonly valid: boolean
    readonly errors: readonly ContentPipelineCaseIssue[]
    readonly summary: string
    /** id declarado no manifesto, quando disponivel como string. */
    readonly caseId: string | null
}

export const CASE_MANIFEST_VALID_SUMMARY = 'Pipeline case manifest is valid.'

export function caseManifestInvalidSummary(errorCount: number): string {
    return `Pipeline case manifest is invalid: ${errorCount} error(s).`
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function issue(code: string, path: string, message: string): ContentPipelineCaseIssue {
    return { code, path, message }
}

/**
 * Valida a estrutura de um manifesto de caso. Ordem de emissao fixa:
 * forma do documento -> schemaVersion -> id -> campos desconhecidos ->
 * cada campo de documento na ordem canonica (presenca, tipo, seguranca lexical).
 * A entrada nunca e mutada.
 */
export function validateCaseManifest(input: unknown): ContentPipelineCaseManifestReport {
    const errors: ContentPipelineCaseIssue[] = []

    if (!isPlainObject(input)) {
        errors.push(issue(
            'CASE_MANIFEST_INVALID',
            '',
            'Pipeline case manifest must be a JSON object with schemaVersion, id, project, composition, outputPlan and beatPlan.',
        ))
        return { valid: false, errors, summary: caseManifestInvalidSummary(errors.length), caseId: null }
    }

    const caseId = isNonEmptyString(input.id) ? input.id : null

    if (input.schemaVersion !== CASE_SCHEMA_VERSION) {
        errors.push(issue(
            'CASE_SCHEMA_VERSION_UNSUPPORTED',
            'schemaVersion',
            `schemaVersion must be the integer ${CASE_SCHEMA_VERSION}.`,
        ))
    }

    if (!isNonEmptyString(input.id)) {
        errors.push(issue('CASE_ID_REQUIRED', 'id', 'id is required and must be a non-empty string.'))
    } else if (!KEBAB_CASE_PATTERN.test(input.id)) {
        errors.push(issue('CASE_ID_INVALID', 'id', 'id must be kebab-case (lowercase letters, digits and single hyphens).'))
    }

    for (const field of Object.keys(input)) {
        if (!(CASE_MANIFEST_FIELDS as readonly string[]).includes(field)) {
            errors.push(issue('CASE_UNKNOWN_FIELD', field, `Unknown field "${field}" is not part of the case manifest contract.`))
        }
    }

    for (const field of CASE_DOCUMENT_FIELDS) {
        const value = input[field]
        if (value === undefined) {
            errors.push(issue('CASE_DOCUMENT_PATH_REQUIRED', field, `${field} is required and must be a relative path to a JSON document.`))
            continue
        }
        if (!isNonEmptyString(value)) {
            errors.push(issue('CASE_DOCUMENT_PATH_INVALID', field, `${field} must be a non-empty string.`))
            continue
        }
        for (const violation of inspectRelativePath(value)) {
            // TRAVERSAL nao e rejeitado aqui: `..` e legitimo para alcancar
            // diretorios irmaos dentro da raiz. O confinamento estrito, que
            // rejeita qualquer resolucao para fora da raiz declarada, e
            // aplicado pelo resolvedor (resolveCaseDocumentPath).
            if (violation === 'TRAVERSAL') continue
            errors.push(issue(
                `CASE_DOCUMENT_PATH_${violation}`,
                field,
                `${field} must be a safe relative path (${violation.toLowerCase()} is not allowed).`,
            ))
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        summary: errors.length === 0 ? CASE_MANIFEST_VALID_SUMMARY : caseManifestInvalidSummary(errors.length),
        caseId,
    }
}
