/**
 * Relatorio estruturado de validacao de manifesto de projeto.
 *
 * Regras de determinismo: nenhuma marca de tempo, nenhum identificador
 * aleatorio, nenhum caminho absoluto da maquina e ordem de emissao fixa.
 * A automacao deve confiar nos codigos estaveis, nao nas mensagens livres.
 */

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

export function issue(code: string, path: string, message: string): ValidationIssue {
    return { code, path, message }
}
