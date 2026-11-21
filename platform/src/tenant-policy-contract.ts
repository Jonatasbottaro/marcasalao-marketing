/**
 * Contrato TenantPolicyContract v1 — camada tipada que conecta os contratos
 * puros da platform (ProjectManifest, Composition, OutputPlan, BeatPlan,
 * CreativeExecutionPackage) as regras multi-tenant declaradas no `brand-kit`
 * (paleta, uiLabels, rotas) e nos `guardrails` (audioPolicy, termos vetados).
 *
 * Espelha os campos relevantes de `schemas/brand-kit.schema.json` e
 * `schemas/guardrails.schema.json`, mas em forma estritamente tipada e pura:
 * sem I/O, sem rede, sem relogio, sem aleatoriedade. Nenhuma execucao ou
 * publicacao acontece aqui.
 */

/** Unica versao de schema do contrato de politica por tenant. */
export const TENANT_POLICY_SCHEMA_VERSION = 1

/** Rotulos de UI obrigatorios no contrato (espelham brand-kit.uiLabels). */
export const TENANT_POLICY_UI_LABEL_KEYS = [
    'teamSectionTitle',
    'catalogSectionTitle',
    'publicRouteFallback',
    'managerRouteFallback',
    'journeyBridgeCaption',
    'itemUnitLabel',
    'customerLabel',
] as const
export type TenantUiLabelKey = (typeof TENANT_POLICY_UI_LABEL_KEYS)[number]

export interface TenantUiLabels {
    readonly teamSectionTitle: string
    readonly catalogSectionTitle: string
    readonly publicRouteFallback: string
    readonly managerRouteFallback: string
    readonly journeyBridgeCaption: string
    readonly itemUnitLabel: string
    readonly customerLabel: string
}

/** Cores hexadecimais espelhando o topo de `brand-kit.palette`. */
export const TENANT_PALETTE_KEYS = [
    'primary',
    'secondary',
    'accent',
    'background',
    'surface',
    'textPrimary',
    'textMuted',
] as const

export interface TenantPalette {
    readonly primary: string
    readonly secondary: string
    readonly accent: string
    readonly background: string
    readonly surface: string
    readonly textPrimary: string
    readonly textMuted: string
}

/** Rotas publicas vs de gestao declaradas pelo tenant. */
export const TENANT_ROUTE_KEYS = ['public', 'management'] as const

export interface TenantRoutes {
    readonly public: string
    readonly management: string
}

/** Codecs de audio reconhecidos na v1. */
export const TENANT_AUDIO_CODECS = ['aac'] as const
export type TenantAudioCodec = (typeof TENANT_AUDIO_CODECS)[number]

/** Unico(s) tenant(s) autorizado(s) a veicular faixa de audio (AAC) na v1. */
export const AUDIO_PERMITTED_TENANTS = ['multitrack-hub'] as const
export type AudioPermittedTenant = (typeof AUDIO_PERMITTED_TENANTS)[number]

/** Superficies reservadas a rotas de gestao (nunca publicas). */
export const MANAGEMENT_ROUTE_PREFIXES = ['/gestor/'] as const
export const MANAGEMENT_ROUTE_EXACT = ['/rateios'] as const

/** True quando a rota pertence a superficie de gestao (gestor/* ou rateios). */
export function isManagementRoute(route: string): boolean {
    if ((MANAGEMENT_ROUTE_EXACT as readonly string[]).includes(route)) {
        return true
    }
    return MANAGEMENT_ROUTE_PREFIXES.some((prefix) => route.startsWith(prefix))
}

export const TENANT_AUDIO_PROFILE_KEYS = [
    'allowAudioTrack',
    'allowedCodecs',
    'requireSrt',
    'requireExternalNarration',
] as const

export interface TenantAudioCodecProfile {
    readonly allowAudioTrack: boolean
    readonly allowedCodecs: readonly TenantAudioCodec[]
    readonly requireSrt: boolean
    readonly requireExternalNarration: boolean
}

/** Guardrails essenciais espelhando `schemas/guardrails.schema.json`. */
export const TENANT_GUARDRAIL_KEYS = ['forbiddenClaims', 'forbiddenUiElements'] as const

export interface TenantGuardrails {
    readonly forbiddenClaims: readonly string[]
    readonly forbiddenUiElements: readonly string[]
}

export const TENANT_DEFAULT_PRESETS = ['saas-demo', 'shorts-completo'] as const
export type TenantDefaultPreset = (typeof TENANT_DEFAULT_PRESETS)[number]

export const TENANT_POLICY_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'tenantId',
    'brandName',
    'defaultPreset',
    'palette',
    'uiLabels',
    'routes',
    'audioProfile',
    'guardrails',
] as const

export interface TenantPolicyContract {
    readonly schemaVersion: 1
    readonly tenantId: string
    readonly brandName: string
    readonly defaultPreset: TenantDefaultPreset
    readonly palette: TenantPalette
    readonly uiLabels: TenantUiLabels
    readonly routes: TenantRoutes
    readonly audioProfile: TenantAudioCodecProfile
    readonly guardrails: TenantGuardrails
}

/** Relatorio puro de validacao do contrato de politica por tenant. */
export interface TenantPolicyValidationReport {
    readonly valid: boolean
    readonly errors: readonly import('./validation-report.js').ValidationIssue[]
    readonly warnings: readonly import('./validation-report.js').ValidationIssue[]
    readonly summary: string
    readonly tenantId: string | null
}

/**
 * Relatorio puro de compatibilidade entre um CreativeExecutionPackage v1 e um
 * TenantPolicyContract v1. `audioArtifactCount` conta os artefatos esperados com
 * `contentType` de audio declarados no pacote (0 quando nao ha faixa de audio).
 */
export interface TenantCompatibilityReport {
    readonly valid: boolean
    readonly errors: readonly import('./validation-report.js').ValidationIssue[]
    readonly warnings: readonly import('./validation-report.js').ValidationIssue[]
    readonly summary: string
    readonly tenantId: string | null
    readonly audioArtifactCount: number
}

export const TENANT_POLICY_VALID_SUMMARY = 'Tenant policy contract is valid.'

export function tenantPolicyInvalidSummary(errorCount: number): string {
    return `Tenant policy contract is invalid: ${errorCount} error(s).`
}

export const TENANT_COMPATIBILITY_VALID_SUMMARY =
    'Execution package is compatible with the tenant policy.'

export function tenantCompatibilityInvalidSummary(errorCount: number): string {
    return `Execution package is not compatible with the tenant policy: ${errorCount} error(s).`
}