/**
 * Validador puro de compatibilidade entre um CreativeExecutionPackage v1 e um
 * TenantPolicyContract v1.
 *
 * Liga o pacote de execucao (artefatos logicos esperados) as regras
 * multi-tenant: bloqueia faixa de audio em tenants de servico, permite audio
 * apenas onde a politica habilita e declara o codec em allowedCodecs
 * e exige que a politica declare todos os uiLabels obrigatorios. Sem I/O, sem
 * rede, sem relogio, sem aleatoriedade e sem mutar a entrada.
 */

import {
    AUDIO_PERMITTED_TENANTS,
    TENANT_COMPATIBILITY_VALID_SUMMARY,
    tenantCompatibilityInvalidSummary,
    type TenantCompatibilityReport,
    type TenantPolicyContract,
} from './tenant-policy-contract.js'
import { validateTenantPolicy } from './validate-tenant-policy.js'
import { issue, type ValidationIssue } from './validation-report.js'

const AUDIO_CONTENT_TYPE_PATTERN = /^audio\/?/i

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function audioCodecOf(contentType: string): string {
    const slash = contentType.indexOf('/')
    return slash >= 0 ? contentType.slice(slash + 1).toLowerCase() : ''
}

/**
 * Valida a compatibilidade pacote x politica. Quando a politica e invalida,
 * seus erros sao repassados (prefixados por `tenantPolicy.`) e a checagem de
 * audio nao prossegue (as regras dependem de uma politica confiavel).
 */
export function validateExecutionPackageTenantCompatibility(
    executionPackage: unknown,
    tenantPolicy: unknown,
): TenantCompatibilityReport {
    const errors: ValidationIssue[] = []
    const warnings: ValidationIssue[] = []

    const policyReport = validateTenantPolicy(tenantPolicy)
    if (!policyReport.valid) {
        for (const item of policyReport.errors) {
            errors.push(issue(item.code, `tenantPolicy.${item.path}`, item.message))
        }
        return {
            valid: false,
            errors,
            warnings,
            summary: tenantCompatibilityInvalidSummary(errors.length),
            tenantId: policyReport.tenantId,
            audioArtifactCount: 0,
        }
    }

    const policy = tenantPolicy as TenantPolicyContract
    const tenantId = policy.tenantId

    if (!isPlainObject(executionPackage)) {
        errors.push(issue('EXECUTION_PACKAGE_INVALID', 'executionPackage', 'Execution package must be a JSON object.'))
        return {
            valid: false,
            errors,
            warnings,
            summary: tenantCompatibilityInvalidSummary(errors.length),
            tenantId,
            audioArtifactCount: 0,
        }
    }

    if (executionPackage.schemaVersion !== undefined && executionPackage.schemaVersion !== 1) {
        errors.push(issue('EXECUTION_PACKAGE_SCHEMA_VERSION_INVALID', 'executionPackage.schemaVersion', 'schemaVersion, when present, must be the integer 1.'))
    }

    let audioArtifactCount = 0
    const artifacts = executionPackage.expectedArtifacts
    if (!Array.isArray(artifacts)) {
        warnings.push(issue('EXECUTION_PACKAGE_ARTIFACTS_MISSING', 'executionPackage.expectedArtifacts', 'expectedArtifacts is missing; audio compatibility is assumed empty.'))
    } else {
        artifacts.forEach((artifact, index) => {
            if (!isPlainObject(artifact)) {
                return
            }
            const contentType = artifact.contentType
            if (typeof contentType !== 'string' || !AUDIO_CONTENT_TYPE_PATTERN.test(contentType)) {
                return
            }
            audioArtifactCount += 1
            const path = `executionPackage.expectedArtifacts[${index}]`
            if (!policy.audioProfile.allowAudioTrack) {
                errors.push(issue('EXEC_AUDIO_TRACK_NOT_ALLOWED', path, `Tenant "${tenantId}" does not allow an audio track.`))
                return
            }
            const codec = audioCodecOf(contentType)
            if (codec !== '' && !(policy.audioProfile.allowedCodecs as readonly string[]).includes(codec)) {
                errors.push(issue('EXEC_AUDIO_CODEC_NOT_ALLOWED', path, `Audio codec "${codec}" is not allowed for tenant "${tenantId}".`))
                return
            }
            if (codec === 'aac' && !(AUDIO_PERMITTED_TENANTS as readonly string[]).includes(tenantId)) {
                errors.push(issue('EXEC_AUDIO_CODEC_RESTRICTED', path, 'AAC audio is restricted to the audio-permitted tenant.'))
            }
        })
    }

    const valid = errors.length === 0
    return {
        valid,
        errors,
        warnings,
        summary: valid ? TENANT_COMPATIBILITY_VALID_SUMMARY : tenantCompatibilityInvalidSummary(errors.length),
        tenantId,
        audioArtifactCount,
    }
}