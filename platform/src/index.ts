/**
 * Superficie publica tipada da platform (Etapa 8): conecta os contratos puros
 * (ProjectManifest, Composition, OutputPlan, BeatPlan, CreativeExecutionPackage)
 * as politicas multi-tenant (TenantPolicyContract v1). Estritamente puro: sem
 * I/O, sem rede, sem publicacao automatica e sem efeitos colaterais.
 *
 * A fronteira minima `validateComposition(composition, project)` permanece pura
 * e e reexportada aqui.
 */

export { validateComposition } from './validate-composition.js'
export { validateContentPipeline } from './validate-content-pipeline.js'
export { validateTenantPolicy } from './validate-tenant-policy.js'
export { validateExecutionPackageTenantCompatibility } from './validate-execution-tenant-compatibility.js'
export { validateCreativeExecutionPackage } from './validate-creative-execution-package.js'

export {
    AUDIO_PERMITTED_TENANTS,
    MANAGEMENT_ROUTE_EXACT,
    MANAGEMENT_ROUTE_PREFIXES,
    TENANT_AUDIO_CODECS,
    TENANT_DEFAULT_PRESETS,
    TENANT_PALETTE_KEYS,
    TENANT_POLICY_SCHEMA_VERSION,
    TENANT_POLICY_UI_LABEL_KEYS,
    TENANT_ROUTE_KEYS,
    isManagementRoute,
} from './tenant-policy-contract.js'

export type {
    AudioPermittedTenant,
    TenantAudioCodec,
    TenantAudioCodecProfile,
    TenantCompatibilityReport,
    TenantDefaultPreset,
    TenantGuardrails,
    TenantPalette,
    TenantPolicyContract,
    TenantPolicyValidationReport,
    TenantRoutes,
    TenantUiLabelKey,
    TenantUiLabels,
} from './tenant-policy-contract.js'

export type { ProjectManifest } from './project-contract.js'
export type { Composition } from './composition-contract.js'
export type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
export type {
    ContentPipelineIssue,
    ContentPipelineStage,
    ContentPipelineValidationInput,
    ContentPipelineValidationReport,
} from './content-pipeline-validation-contract.js'
export type { CompositionValidationReport, ValidationIssue } from './validation-report.js'