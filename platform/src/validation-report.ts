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

/**
 * Relatorio estruturado de validacao de BeatPlan (estrutura propria, vinculo
 * com ProjectManifest e Composition, relacao com cenas e timeline). Mesmas
 * regras de determinismo: sem timestamp, sem caminho absoluto da maquina, sem
 * ID aleatorio, sem stack trace, ordem estavel e codigos estaveis.
 */
export interface BeatPlanValidationReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    /** projectId declarado no plano, quando disponivel como string. */
    projectId: string | null
    /** compositionId declarado no plano, quando disponivel como string. */
    compositionId: string | null
    /** id declarado no plano, quando disponivel como string. */
    beatPlanId: string | null
    /** schemaVersion declarado, quando disponivel como numero. */
    schemaVersion: number | null
    /**
     * Quantidade de entradas de beats que sao objetos JSON (0 quando beats esta
     * ausente ou malformado). Contagem estrutural: nao implica beats validos.
     */
    beatCount: number
    /** Quantidade de cenas da Composition valida (0 quando nao confiavel). */
    compositionSceneCount: number
    /** Quantidade de sceneIds unicos e existentes referenciados pelos beats. */
    referencedSceneCount: number
    /**
     * Soma segura dos durationMs inteiros positivos dos beats; null quando nao
     * pode ser calculada com seguranca (BEAT_PLAN_DURATION_OVERFLOW).
     */
    totalDurationMs: number | null
    /** Duracao total calculada pela Composition; null quando nao confiavel. */
    compositionDurationMs: number | null
    /** Quantidade de beats com narration bem formada. */
    narrationBeatCount: number
    /** Quantidade de beats com onScreenText bem formado. */
    onScreenTextBeatCount: number
    /** metadata.status declarado e valido; null quando ausente ou invalido. */
    metadataStatus: string | null
}

export const BEAT_PLAN_VALID_SUMMARY = 'Beat plan is valid.'

export function beatPlanInvalidSummary(errorCount: number): string {
    return `Beat plan is invalid: ${errorCount} error(s).`
}

export function issue(code: string, path: string, message: string): ValidationIssue {
    return { code, path, message }
}
