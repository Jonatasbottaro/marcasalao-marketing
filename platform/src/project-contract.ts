/**
 * Contrato ProjectManifest — primeira fatia do nucleo modular da Content Factory.
 *
 * Este nucleo NAO conhece nenhum projeto especifico: marca, tema, cores, dominio,
 * CTA e politicas editoriais valem como dados declarados no manifesto. Qualquer
 * projeto que satisfaça este contrato deve ser aceito pelo mesmo validador.
 *
 * Ver docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md.
 */

/** Unica versao de schema suportada nesta fatia. */
export const PROJECT_SCHEMA_VERSION = 1

/** Formato de identificadores (id do projeto e output profiles). */
export const KEBAB_CASE_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*$/

/**
 * Politicas editoriais explicitas do projeto. Cada chave deve estar presente e
 * ser booleana: ausencia e tratada como erro, nao como valor padrao implicito.
 */
export interface ProjectContentPolicies {
    requireApprovedBriefing: boolean
    requireApprovedScript: boolean
    prohibitPersonalData: boolean
    requireFunctionalEvidence: boolean
}

/** Chaves obrigatorias de contentPolicies, em ordem fixa de verificacao. */
export const CONTENT_POLICY_KEYS = [
    'requireApprovedBriefing',
    'requireApprovedScript',
    'prohibitPersonalData',
    'requireFunctionalEvidence',
] as const

/**
 * Manifesto declarativo de um projeto consumidor da plataforma.
 * Campos sao dados, nunca regras: o nucleo nao interpreta brandTheme,
 * outputProfiles ou politicas — apenas exige que estejam bem formados.
 */
export interface ProjectManifest {
    schemaVersion: number
    id: string
    name: string
    locale: string
    timezone: string
    /** Opaco para o nucleo: identificacao do tema visual no projeto consumidor. */
    brandTheme: string
    /** Caminho relativo seguro para a raiz de assets do projeto. */
    assetRoot: string
    contentPolicies: ProjectContentPolicies
    /** Pelo menos um profile, em kebab-case, sem duplicacoes. */
    outputProfiles: string[]
}
