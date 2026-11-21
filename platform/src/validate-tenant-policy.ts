/**
 * Validador puro do TenantPolicyContract v1.
 *
 * Verifica estrutura, ids, paleta hex, uiLabels obrigatorios, rotas publicas
 * vs. de gestao e o perfil de audio (audio so onde declarado habilitado;
 * tenants de servico sem faixa de audio; codecs restritos aos declarados). Sem I/O, sem
 * rede, sem relogio, sem aleatoriedade e sem mutar a entrada. Codigos estaveis
 * e ordem de emissao fixa.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    TENANT_AUDIO_CODECS,
    TENANT_AUDIO_PROFILE_KEYS,
    TENANT_DEFAULT_PRESETS,
    TENANT_GUARDRAIL_KEYS,
    TENANT_PALETTE_KEYS,
    TENANT_POLICY_SCHEMA_VERSION,
    TENANT_POLICY_TOP_LEVEL_FIELDS,
    TENANT_POLICY_UI_LABEL_KEYS,
    TENANT_POLICY_VALID_SUMMARY,
    TENANT_ROUTE_KEYS,
    tenantPolicyInvalidSummary,
    type TenantPolicyValidationReport,
} from './tenant-policy-contract.js'
import { issue, type ValidationIssue } from './validation-report.js'

const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isHexColor(value: unknown): value is string {
    return typeof value === 'string' && HEX_COLOR_PATTERN.test(value)
}

function isStringArray(value: unknown): value is readonly string[] {
    return Array.isArray(value) && value.every((item) => isNonEmptyString(item))
}

function unknownFields(
    value: Record<string, unknown>,
    allowed: readonly string[],
    prefix: string,
    errors: ValidationIssue[],
): void {
    const allowedSet = new Set(allowed)
    for (const field of Object.keys(value)) {
        if (!allowedSet.has(field)) {
            errors.push(issue(
                'TENANT_POLICY_UNKNOWN_FIELD',
                `${prefix}${field}`,
                `Unknown field "${field}" is not part of the tenant policy contract.`,
            ))
        }
    }
}

/** Valida um contrato de politica por tenant. A entrada nunca e mutada. */
export function validateTenantPolicy(input: unknown): TenantPolicyValidationReport {
    const errors: ValidationIssue[] = []

    if (!isPlainObject(input)) {
        errors.push(issue('TENANT_POLICY_INVALID', '', 'Tenant policy must be a JSON object.'))
        return {
            valid: false,
            errors,
            warnings: [],
            summary: tenantPolicyInvalidSummary(errors.length),
            tenantId: null,
        }
    }

    const tenantId = isNonEmptyString(input.tenantId) ? input.tenantId : null
    const tenantIdValid = typeof input.tenantId === 'string' && KEBAB_CASE_PATTERN.test(input.tenantId)

    if (input.schemaVersion !== TENANT_POLICY_SCHEMA_VERSION) {
        errors.push(issue(
            'TENANT_POLICY_SCHEMA_VERSION_UNSUPPORTED',
            'schemaVersion',
            `schemaVersion must be the integer ${TENANT_POLICY_SCHEMA_VERSION}.`,
        ))
    }
    unknownFields(input, TENANT_POLICY_TOP_LEVEL_FIELDS, '', errors)

    if (!tenantIdValid) {
        errors.push(issue('TENANT_POLICY_TENANT_ID_INVALID', 'tenantId', 'tenantId is required and must be kebab-case.'))
    }
    if (!isNonEmptyString(input.brandName)) {
        errors.push(issue('TENANT_POLICY_BRAND_NAME_INVALID', 'brandName', 'brandName is required and must be a non-empty string.'))
    }
    if (!(TENANT_DEFAULT_PRESETS as readonly string[]).includes(input.defaultPreset as string)) {
        errors.push(issue('TENANT_POLICY_DEFAULT_PRESET_INVALID', 'defaultPreset', 'defaultPreset must be one of the supported presets.'))
    }

    // palette (hex)
    const palette = input.palette
    if (!isPlainObject(palette)) {
        errors.push(issue('TENANT_POLICY_PALETTE_INVALID', 'palette', 'palette is required and must be an object.'))
    } else {
        unknownFields(palette, TENANT_PALETTE_KEYS, 'palette.', errors)
        for (const key of TENANT_PALETTE_KEYS) {
            if (!isHexColor(palette[key])) {
                errors.push(issue('TENANT_POLICY_PALETTE_INVALID', `palette.${key}`, `palette.${key} must be a #RRGGBB color.`))
            }
        }
    }

    // uiLabels (todos obrigatorios; chaves desconhecidas proibidas)
    const uiLabels = input.uiLabels
    if (!isPlainObject(uiLabels)) {
        errors.push(issue('TENANT_POLICY_UI_LABELS_INVALID', 'uiLabels', 'uiLabels is required for the tenant policy contract.'))
    } else {
        unknownFields(uiLabels, TENANT_POLICY_UI_LABEL_KEYS, 'uiLabels.', errors)
        for (const key of TENANT_POLICY_UI_LABEL_KEYS) {
            if (!isNonEmptyString(uiLabels[key])) {
                errors.push(issue('TENANT_POLICY_UI_LABEL_MISSING', `uiLabels.${key}`, `uiLabels.${key} is required and must be a non-empty string.`))
            }
        }
    }

    // routes (publicas vs. gestao, distintas)
    const routes = input.routes
    if (!isPlainObject(routes)) {
        errors.push(issue('TENANT_POLICY_ROUTES_INVALID', 'routes', 'routes is required and must be an object.'))
    } else {
        unknownFields(routes, TENANT_ROUTE_KEYS, 'routes.', errors)
        const hasPublic = isNonEmptyString(routes.public)
        const hasManagement = isNonEmptyString(routes.management)
        if (!hasPublic) {
            errors.push(issue('TENANT_POLICY_ROUTE_MISSING', 'routes.public', 'routes.public is required and must be a non-empty string.'))
        }
        if (!hasManagement) {
            errors.push(issue('TENANT_POLICY_ROUTE_MISSING', 'routes.management', 'routes.management is required and must be a non-empty string.'))
        }
        if (hasPublic && hasManagement && routes.public === routes.management) {
            errors.push(issue('TENANT_POLICY_ROUTE_NOT_DISTINCT', 'routes', 'routes.public and routes.management must differ.'))
        }
    }

    // audioProfile
    const audio = input.audioProfile
    if (!isPlainObject(audio)) {
        errors.push(issue('TENANT_POLICY_AUDIO_PROFILE_INVALID', 'audioProfile', 'audioProfile is required and must be an object.'))
    } else {
        unknownFields(audio, TENANT_AUDIO_PROFILE_KEYS, 'audioProfile.', errors)
        const allowAudio = typeof audio.allowAudioTrack === 'boolean' ? audio.allowAudioTrack : null
        if (allowAudio === null) {
            errors.push(issue('TENANT_POLICY_AUDIO_FLAG_INVALID', 'audioProfile.allowAudioTrack', 'audioProfile.allowAudioTrack must be boolean.'))
        }
        if (typeof audio.requireSrt !== 'boolean') {
            errors.push(issue('TENANT_POLICY_AUDIO_FLAG_INVALID', 'audioProfile.requireSrt', 'audioProfile.requireSrt must be boolean.'))
        }
        if (typeof audio.requireExternalNarration !== 'boolean') {
            errors.push(issue('TENANT_POLICY_AUDIO_FLAG_INVALID', 'audioProfile.requireExternalNarration', 'audioProfile.requireExternalNarration must be boolean.'))
        }

        let codecs: readonly string[] = []
        if (!Array.isArray(audio.allowedCodecs)) {
            errors.push(issue('TENANT_POLICY_AUDIO_CODECS_INVALID', 'audioProfile.allowedCodecs', 'audioProfile.allowedCodecs must be an array.'))
        } else {
            codecs = audio.allowedCodecs.filter((codec): codec is string => typeof codec === 'string')
            if (codecs.length !== audio.allowedCodecs.length) {
                errors.push(issue('TENANT_POLICY_AUDIO_CODECS_INVALID', 'audioProfile.allowedCodecs', 'audioProfile.allowedCodecs must contain only strings.'))
            }
            for (const codec of codecs) {
                if (!(TENANT_AUDIO_CODECS as readonly string[]).includes(codec)) {
                    errors.push(issue('TENANT_POLICY_AUDIO_CODEC_UNKNOWN', 'audioProfile.allowedCodecs', `Unknown audio codec "${codec}".`))
                }
            }
        }

        if (allowAudio === false && codecs.length > 0) {
            errors.push(issue('TENANT_POLICY_AUDIO_CODEC_WITH_AUDIO_DISABLED', 'audioProfile.allowedCodecs', 'allowedCodecs must be empty when allowAudioTrack is false.'))
        }
        if (allowAudio === true && codecs.length === 0) {
            errors.push(issue('TENANT_POLICY_AUDIO_ENABLED_WITHOUT_CODEC', 'audioProfile.allowedCodecs', 'allowedCodecs must be non-empty when allowAudioTrack is true.'))
        }
            }

    // guardrails
    const guardrails = input.guardrails
    if (!isPlainObject(guardrails)) {
        errors.push(issue('TENANT_POLICY_GUARDRAILS_INVALID', 'guardrails', 'guardrails is required and must be an object.'))
    } else {
        unknownFields(guardrails, TENANT_GUARDRAIL_KEYS, 'guardrails.', errors)
        for (const key of TENANT_GUARDRAIL_KEYS) {
            const value = guardrails[key]
            if (!isStringArray(value) || value.length === 0) {
                errors.push(issue('TENANT_POLICY_GUARDRAILS_INVALID', `guardrails.${key}`, `guardrails.${key} must be a non-empty array of strings.`))
            }
        }
    }

    const valid = errors.length === 0
    return {
        valid,
        errors,
        warnings: [],
        summary: valid ? TENANT_POLICY_VALID_SUMMARY : tenantPolicyInvalidSummary(errors.length),
        tenantId,
    }
}