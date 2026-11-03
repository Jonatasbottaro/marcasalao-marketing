/**
 * Validador do manifesto de projeto.
 *
 * Implementa as regras descritas em platform/schemas/project.schema.json e em
 * platform/README.md. Nao conhece nenhum projeto especifico: aceita qualquer
 * manifesto que satisfaça o contrato e rejeita o que o viole, coletando todos
 * os erros relevantes em ordem de emissao fixa (deterministica).
 */

import {
    CONTENT_POLICY_KEYS,
    KEBAB_CASE_PATTERN,
    PROJECT_SCHEMA_VERSION,
    type ProjectManifest,
} from './project-contract.js'
import {
    VALID_SUMMARY,
    invalidSummary,
    issue,
    type ProjectValidationReport,
    type ValidationIssue,
} from './validation-report.js'

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
const KNOWN_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'id',
    'name',
    'locale',
    'timezone',
    'brandTheme',
    'assetRoot',
    'contentPolicies',
    'outputProfiles',
] as const

/** Segmentos/nomes de arquivo sensiveis que o assetRoot nao pode referenciar. */
const SENSITIVE_ASSET_PATTERNS = [
    '.env',
    'private_key',
    'privatekey',
    'service_account',
    'serviceaccount',
    'credential',
    'credentials',
    'secret',
    'secrets',
    'password',
    '.git',
] as const

/** Extensoes de chave privada/certificado sensiveis. */
const SENSITIVE_EXTENSIONS = ['.pem', '.key', '.p12', '.pfx'] as const

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

/** Detecta caminhos absolutos POSIX, Windows (letra de unidade) e UNC. */
function isAbsoluteishPath(value: string): boolean {
    return value.startsWith('/') || value.startsWith('\\') || /^[A-Za-z]:[\\/]/.test(value)
}

function pathSegments(value: string): string[] {
    return value.split(/[\\/]/).filter((segment) => segment.length > 0)
}

function detectSensitiveAssetPath(value: string): boolean {
    const lowerSegments = pathSegments(value).map((segment) => segment.toLowerCase())
    const lowerValue = value.toLowerCase()

    for (const segment of lowerSegments) {
        if (SENSITIVE_ASSET_PATTERNS.some((pattern) => segment === pattern || segment.startsWith(`${pattern}.`))) {
            return true
        }
        if (SENSITIVE_EXTENSIONS.some((extension) => segment.endsWith(extension))) {
            return true
        }
        if (segment.startsWith('id_rsa') || segment.startsWith('id_ed25519') || segment.startsWith('id_ecdsa')) {
            return true
        }
    }

    return SENSITIVE_ASSET_PATTERNS.some((pattern) => lowerValue.includes(pattern))
}

function validateContentPolicies(
    value: unknown,
    errors: ValidationIssue[],
): void {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'PROJECT_CONTENT_POLICY_INVALID',
            'contentPolicies',
            'contentPolicies must be an object with explicit boolean policies.',
        ))
        return
    }

    for (const key of CONTENT_POLICY_KEYS) {
        const policyValue = value[key]
        if (typeof policyValue !== 'boolean') {
            errors.push(issue(
                'PROJECT_CONTENT_POLICY_INVALID',
                `contentPolicies.${key}`,
                `Policy "${key}" must be an explicit boolean.`,
            ))
        }
    }

    for (const key of Object.keys(value)) {
        if (!(CONTENT_POLICY_KEYS as readonly string[]).includes(key)) {
            errors.push(issue(
                'PROJECT_CONTENT_POLICY_INVALID',
                `contentPolicies.${key}`,
                `Unknown policy "${key}"; the schema defines exactly ${CONTENT_POLICY_KEYS.length} boolean policies.`,
            ))
        }
    }
}

function validateOutputProfiles(value: unknown, errors: ValidationIssue[]): void {
    if (!Array.isArray(value) || value.length === 0) {
        errors.push(issue(
            'PROJECT_OUTPUT_PROFILE_REQUIRED',
            'outputProfiles',
            'outputProfiles must be a non-empty array.',
        ))
        return
    }

    const seen = new Set<string>()
    value.forEach((profile, index) => {
        const path = `outputProfiles[${index}]`
        if (!isNonEmptyString(profile) || !KEBAB_CASE_PATTERN.test(profile)) {
            errors.push(issue(
                'PROJECT_OUTPUT_PROFILE_INVALID',
                path,
                'Output profile identifiers must be non-empty kebab-case strings.',
            ))
            return
        }
        if (seen.has(profile)) {
            errors.push(issue(
                'PROJECT_OUTPUT_PROFILE_DUPLICATE',
                path,
                `Output profile "${profile}" is duplicated.`,
            ))
            return
        }
        seen.add(profile)
    })
}

/**
 * Valida um manifesto de projeto qualquer. Nao le arquivos, nao acessa rede e
 * nao depende de nenhum projeto especifico.
 */
export function validateProjectManifest(input: unknown): ProjectValidationReport {
    const errors: ValidationIssue[] = []

    if (!isPlainObject(input)) {
        errors.push(issue(
            'PROJECT_MANIFEST_INVALID',
            '',
            'Project manifest must be a JSON object.',
        ))
        return finalizeReport(errors, null, null, 0)
    }

    const record = input as Record<string, unknown>

    // Campos desconhecidos: politica do schema e additionalProperties=false.
    for (const key of Object.keys(record)) {
        if (!(KNOWN_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'PROJECT_UNKNOWN_FIELD',
                key,
                `Unknown top-level field "${key}"; the schema does not allow additional properties.`,
            ))
        }
    }

    if (record.schemaVersion !== PROJECT_SCHEMA_VERSION) {
        errors.push(issue(
            'PROJECT_SCHEMA_VERSION_UNSUPPORTED',
            'schemaVersion',
            `schemaVersion must be ${PROJECT_SCHEMA_VERSION}.`,
        ))
    }

    if (!isNonEmptyString(record.id)) {
        errors.push(issue('PROJECT_ID_REQUIRED', 'id', 'id is required and must be a non-empty string.'))
    } else if (!KEBAB_CASE_PATTERN.test(record.id)) {
        errors.push(issue('PROJECT_ID_INVALID', 'id', 'id must be kebab-case (lowercase letters, digits and dashes).'))
    }

    if (!isNonEmptyString(record.name)) {
        errors.push(issue('PROJECT_NAME_REQUIRED', 'name', 'name is required and must be a non-empty string.'))
    }

    if (!isNonEmptyString(record.locale)) {
        errors.push(issue('PROJECT_LOCALE_REQUIRED', 'locale', 'locale is required.'))
    }

    if (!isNonEmptyString(record.timezone)) {
        errors.push(issue('PROJECT_TIMEZONE_REQUIRED', 'timezone', 'timezone is required.'))
    }

    // brandTheme e opaco: apenas exige presenca e formato de string.
    if (!isNonEmptyString(record.brandTheme)) {
        errors.push(issue('PROJECT_BRAND_THEME_REQUIRED', 'brandTheme', 'brandTheme is required.'))
    }

    if (!isNonEmptyString(record.assetRoot)) {
        errors.push(issue('PROJECT_ASSET_ROOT_REQUIRED', 'assetRoot', 'assetRoot is required.'))
    } else {
        if (isAbsoluteishPath(record.assetRoot)) {
            errors.push(issue(
                'PROJECT_ASSET_ROOT_ABSOLUTE',
                'assetRoot',
                'assetRoot must be a relative path.',
            ))
        }
        if (pathSegments(record.assetRoot).some((segment) => segment === '..')) {
            errors.push(issue(
                'PROJECT_ASSET_ROOT_TRAVERSAL',
                'assetRoot',
                'assetRoot must not traverse outside the allowed root (".." segments are not allowed).',
            ))
        }
        if (detectSensitiveAssetPath(record.assetRoot)) {
            errors.push(issue(
                'PROJECT_ASSET_ROOT_SENSITIVE',
                'assetRoot',
                'assetRoot must not point to sensitive files (.env, keys, credentials).',
            ))
        }
    }

    validateContentPolicies(record.contentPolicies, errors)
    validateOutputProfiles(record.outputProfiles, errors)

    return finalizeReport(
        errors,
        typeof record.id === 'string' ? record.id : null,
        typeof record.schemaVersion === 'number' ? record.schemaVersion : null,
        Array.isArray(record.outputProfiles) ? record.outputProfiles.length : 0,
    )
}

function finalizeReport(
    errors: ValidationIssue[],
    projectId: string | null,
    schemaVersion: number | null,
    outputProfileCount: number,
): ProjectValidationReport {
    return {
        valid: errors.length === 0,
        errors,
        warnings: [],
        summary: errors.length === 0 ? VALID_SUMMARY : invalidSummary(errors.length),
        projectId,
        schemaVersion,
        outputProfileCount,
    }
}

export type { ProjectManifest }
