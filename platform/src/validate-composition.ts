/**
 * Validador de composicao (Composition v1).
 *
 * Valida a estrutura propria da composicao e o vinculo com um ProjectManifest
 * informado explicitamente: mesmo projeto, mesmo locale e profile presente em
 * outputProfiles. Nao le arquivos, nao acessa rede, nao verifica existencia
 * fisica de assets e nao conhece nenhum projeto especifico.
 *
 * Os erros sao coletados todos, em ordem de emissao fixa: primeiro o manifesto
 * do projeto, depois a estrutura da composicao, depois os vinculos entre eles.
 */

import {
    COMPOSITION_FPS_MAX,
    COMPOSITION_FPS_MIN,
    COMPOSITION_MAX_TAGS,
    COMPOSITION_METADATA_STATUSES,
    COMPOSITION_SCENE_TYPES,
    COMPOSITION_SCHEMA_VERSION,
    COMPOSITION_TOP_LEVEL_FIELDS,
    KEBAB_CASE_PATTERN,
    type CompositionSceneType,
} from './composition-contract.js'
import { validateProjectManifest } from './validate-project.js'
import {
    COMPOSITION_VALID_SUMMARY,
    compositionInvalidSummary,
    issue,
    type CompositionReportFormat,
    type CompositionValidationReport,
    type ValidationIssue,
} from './validation-report.js'

/** Segmentos/nomes sensiveis que um asset nao pode referenciar. */
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

/** Campos permitidos em content, por tipo de cena (forma fechada). */
const CONTENT_FIELDS_BY_SCENE_TYPE: Record<CompositionSceneType, readonly string[]> = {
    text: ['text', 'accessibilityLabel'],
    cta: ['text', 'href', 'accessibilityLabel'],
    image: ['asset', 'alt', 'accessibilityLabel'],
    video: ['asset', 'alt', 'accessibilityLabel'],
}

/** Campos permitidos em metadata (forma fechada). */
const METADATA_FIELDS = ['status', 'description', 'tags'] as const

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isPositiveInteger(value: unknown): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value > 0
}

/** Detecta caminhos absolutos POSIX, Windows (letra de unidade) e UNC. */
function isAbsoluteishPath(value: string): boolean {
    return value.startsWith('/') || value.startsWith('\\') || /^[A-Za-z]:[\\/]/.test(value)
}

function pathSegments(value: string): string[] {
    return value.split(/[\\/]/).filter((segment) => segment.length > 0)
}

/** Detecta URL/protocolo ou credenciais embutidas em um caminho ou href. */
function hasUrlScheme(value: string): boolean {
    return /^[A-Za-z][A-Za-z0-9+.-]*:/.test(value)
}

function hasEmbeddedCredentials(value: string): boolean {
    return /^https?:\/\/[^/@]*:[^/@]*@/.test(value)
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

function validateAssetReference(value: unknown, basePath: string, errors: ValidationIssue[]): void {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'COMPOSITION_SCENE_CONTENT_ASSET_REQUIRED',
            basePath,
            'asset must be an object with id and path.',
        ))
        return
    }

    for (const key of Object.keys(value)) {
        if (key !== 'id' && key !== 'path') {
            errors.push(issue(
                'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN',
                `${basePath}.${key}`,
                `Unknown asset field "${key}"; AssetReference v1 accepts only id and path.`,
            ))
        }
    }

    if (!isNonEmptyString(value.id) || !KEBAB_CASE_PATTERN.test(value.id)) {
        errors.push(issue(
            'COMPOSITION_ASSET_ID_INVALID',
            `${basePath}.id`,
            'asset.id must be a non-empty kebab-case string.',
        ))
    }

    if (!isNonEmptyString(value.path)) {
        errors.push(issue(
            'COMPOSITION_ASSET_PATH_INVALID',
            `${basePath}.path`,
            'asset.path is required and must be a non-empty relative path.',
        ))
    } else {
        const assetPath = value.path
        if (isAbsoluteishPath(assetPath) || hasUrlScheme(assetPath)) {
            errors.push(issue(
                'COMPOSITION_ASSET_PATH_INVALID',
                `${basePath}.path`,
                'asset.path must be a relative path without protocol or URL.',
            ))
        }
        if (pathSegments(assetPath).some((segment) => segment === '..')) {
            errors.push(issue(
                'COMPOSITION_ASSET_PATH_INVALID',
                `${basePath}.path`,
                'asset.path must not traverse outside the project (".." segments are not allowed).',
            ))
        }
        if (hasEmbeddedCredentials(assetPath)) {
            errors.push(issue(
                'COMPOSITION_ASSET_PATH_INVALID',
                `${basePath}.path`,
                'asset.path must not embed credentials.',
            ))
        }
        if (detectSensitiveAssetPath(assetPath)) {
            errors.push(issue(
                'COMPOSITION_ASSET_PATH_SENSITIVE',
                `${basePath}.path`,
                'asset.path must not point to sensitive files (.env, keys, credentials).',
            ))
        }
    }
}

function validateSceneContent(
    value: unknown,
    sceneType: CompositionSceneType,
    basePath: string,
    errors: ValidationIssue[],
): void {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'COMPOSITION_SCENE_CONTENT_REQUIRED',
            basePath,
            'content is required and must be an object.',
        ))
        return
    }

    const allowedFields = CONTENT_FIELDS_BY_SCENE_TYPE[sceneType]

    for (const key of Object.keys(value)) {
        if (!allowedFields.includes(key)) {
            errors.push(issue(
                'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN',
                `${basePath}.${key}`,
                `Field "${key}" is not allowed in content of a "${sceneType}" scene.`,
            ))
        }
    }

    if (sceneType === 'text' || sceneType === 'cta') {
        if (!isNonEmptyString(value.text)) {
            errors.push(issue(
                'COMPOSITION_SCENE_CONTENT_TEXT_REQUIRED',
                `${basePath}.text`,
                `content.text is required and must be a non-empty string in a "${sceneType}" scene.`,
            ))
        }
        if (sceneType === 'cta' && value.href !== undefined) {
            const href = value.href
            if (!isNonEmptyString(href) || !/^https?:\/\//i.test(href) || hasEmbeddedCredentials(href)) {
                errors.push(issue(
                    'COMPOSITION_SCENE_CONTENT_HREF_INVALID',
                    `${basePath}.href`,
                    'content.href must be an http(s) URL without embedded credentials; it is never fetched.',
                ))
            }
        }
    }

    if (sceneType === 'image' || sceneType === 'video') {
        if (value.asset === undefined) {
            errors.push(issue(
                'COMPOSITION_SCENE_CONTENT_ASSET_REQUIRED',
                `${basePath}.asset`,
                `content.asset is required in a "${sceneType}" scene.`,
            ))
        } else {
            validateAssetReference(value.asset, `${basePath}.asset`, errors)
        }
    }

    if (value.accessibilityLabel !== undefined && !isNonEmptyString(value.accessibilityLabel)) {
        errors.push(issue(
            'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN',
            `${basePath}.accessibilityLabel`,
            'content.accessibilityLabel must be a non-empty string when present.',
        ))
    }

    if (value.alt !== undefined && !isNonEmptyString(value.alt)) {
        errors.push(issue(
            'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN',
            `${basePath}.alt`,
            'content.alt must be a non-empty string when present.',
        ))
    }
}

function validateScenes(value: unknown, errors: ValidationIssue[]): number {
    if (!Array.isArray(value)) {
        errors.push(issue(
            'COMPOSITION_SCENES_REQUIRED',
            'scenes',
            'scenes is required and must be an array.',
        ))
        return 0
    }

    const seenIds = new Set<string>()

    value.forEach((scene, index) => {
        const basePath = `scenes[${index}]`

        if (!isPlainObject(scene)) {
            errors.push(issue(
                'COMPOSITION_SCENE_INVALID',
                basePath,
                'Each scene must be an object.',
            ))
            return
        }

        for (const key of Object.keys(scene)) {
            if (key !== 'id' && key !== 'type' && key !== 'durationMs' && key !== 'content') {
                errors.push(issue(
                    'COMPOSITION_SCENE_INVALID',
                    `${basePath}.${key}`,
                    `Unknown scene field "${key}"; the schema does not allow additional properties.`,
                ))
            }
        }

        if (!isNonEmptyString(scene.id) || !KEBAB_CASE_PATTERN.test(scene.id)) {
            errors.push(issue(
                'COMPOSITION_SCENE_ID_INVALID',
                `${basePath}.id`,
                'scene.id must be a non-empty kebab-case string.',
            ))
        } else if (seenIds.has(scene.id)) {
            errors.push(issue(
                'COMPOSITION_SCENE_ID_DUPLICATE',
                `${basePath}.id`,
                `Scene id "${scene.id}" is duplicated in the composition.`,
            ))
        } else {
            seenIds.add(scene.id)
        }

        const sceneType = scene.type
        if (typeof sceneType !== 'string' || !(COMPOSITION_SCENE_TYPES as readonly string[]).includes(sceneType)) {
            errors.push(issue(
                'COMPOSITION_SCENE_TYPE_INVALID',
                `${basePath}.type`,
                `scene.type must be one of: ${COMPOSITION_SCENE_TYPES.join(', ')}.`,
            ))
        }

        if (!isPositiveInteger(scene.durationMs)) {
            errors.push(issue(
                'COMPOSITION_SCENE_DURATION_INVALID',
                `${basePath}.durationMs`,
                'scene.durationMs must be an integer greater than zero.',
            ))
        }

        if (scene.content === undefined) {
            errors.push(issue(
                'COMPOSITION_SCENE_CONTENT_REQUIRED',
                `${basePath}.content`,
                'scene.content is required.',
            ))
        } else if (typeof sceneType === 'string' && (COMPOSITION_SCENE_TYPES as readonly string[]).includes(sceneType)) {
            validateSceneContent(scene.content, sceneType as CompositionSceneType, `${basePath}.content`, errors)
        }
    })

    return value.length
}

function validateFormat(value: unknown, errors: ValidationIssue[]): CompositionReportFormat | null {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'COMPOSITION_FORMAT_REQUIRED',
            'format',
            'format is required and must be an object.',
        ))
        return null
    }

    for (const key of Object.keys(value)) {
        if (key !== 'profile' && key !== 'width' && key !== 'height' && key !== 'fps') {
            errors.push(issue(
                'COMPOSITION_FORMAT_REQUIRED',
                `format.${key}`,
                `Unknown format field "${key}"; the schema does not allow additional properties.`,
            ))
        }
    }

    let profile: string | null = null
    if (!isNonEmptyString(value.profile) || !KEBAB_CASE_PATTERN.test(value.profile)) {
        errors.push(issue(
            'COMPOSITION_FORMAT_PROFILE_INVALID',
            'format.profile',
            'format.profile must be a non-empty kebab-case string.',
        ))
    } else {
        profile = value.profile
    }

    if (!isPositiveInteger(value.width)) {
        errors.push(issue(
            'COMPOSITION_FORMAT_WIDTH_INVALID',
            'format.width',
            'format.width must be an integer greater than zero.',
        ))
    }

    if (!isPositiveInteger(value.height)) {
        errors.push(issue(
            'COMPOSITION_FORMAT_HEIGHT_INVALID',
            'format.height',
            'format.height must be an integer greater than zero.',
        ))
    }

    if (
        typeof value.fps !== 'number' ||
        !Number.isInteger(value.fps) ||
        value.fps < COMPOSITION_FPS_MIN ||
        value.fps > COMPOSITION_FPS_MAX
    ) {
        errors.push(issue(
            'COMPOSITION_FORMAT_FPS_INVALID',
            'format.fps',
            `format.fps must be an integer between ${COMPOSITION_FPS_MIN} and ${COMPOSITION_FPS_MAX}.`,
        ))
    }

    if (
        profile === null ||
        !isPositiveInteger(value.width) ||
        !isPositiveInteger(value.height) ||
        typeof value.fps !== 'number' ||
        !Number.isInteger(value.fps)
    ) {
        return null
    }

    return { profile, width: value.width, height: value.height, fps: value.fps }
}

function validateRenderer(value: unknown, errors: ValidationIssue[]): string | null {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'COMPOSITION_RENDERER_REQUIRED',
            'renderer',
            'renderer is required and must be an object.',
        ))
        return null
    }

    for (const key of Object.keys(value)) {
        if (key === 'options') {
            errors.push(issue(
                'COMPOSITION_RENDERER_OPTIONS_UNSUPPORTED',
                'renderer.options',
                'renderer.options is not supported in Composition v1.',
            ))
        } else if (key !== 'adapter') {
            errors.push(issue(
                'COMPOSITION_RENDERER_REQUIRED',
                `renderer.${key}`,
                `Unknown renderer field "${key}"; the schema does not allow additional properties.`,
            ))
        }
    }

    if (!isNonEmptyString(value.adapter) || !KEBAB_CASE_PATTERN.test(value.adapter)) {
        errors.push(issue(
            'COMPOSITION_RENDERER_ADAPTER_INVALID',
            'renderer.adapter',
            'renderer.adapter must be a non-empty kebab-case string; "undecided" is accepted.',
        ))
        return null
    }

    return value.adapter
}

function validateMetadata(value: unknown, errors: ValidationIssue[]): void {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'COMPOSITION_METADATA_INVALID',
            'metadata',
            'metadata must be an object when present.',
        ))
        return
    }

    for (const key of Object.keys(value)) {
        if (!(METADATA_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'COMPOSITION_METADATA_INVALID',
                `metadata.${key}`,
                `Unknown metadata field "${key}"; only status, description and tags are allowed.`,
            ))
        }
    }

    if (value.status !== undefined) {
        const status = value.status
        if (typeof status !== 'string' || !(COMPOSITION_METADATA_STATUSES as readonly string[]).includes(status)) {
            errors.push(issue(
                'COMPOSITION_METADATA_STATUS_INVALID',
                'metadata.status',
                `metadata.status must be one of: ${COMPOSITION_METADATA_STATUSES.join(', ')}.`,
            ))
        }
    }

    if (value.description !== undefined && !isNonEmptyString(value.description)) {
        errors.push(issue(
            'COMPOSITION_METADATA_INVALID',
            'metadata.description',
            'metadata.description must be a non-empty string when present.',
        ))
    }

    if (value.tags !== undefined) {
        if (!Array.isArray(value.tags) || value.tags.length > COMPOSITION_MAX_TAGS) {
            errors.push(issue(
                'COMPOSITION_METADATA_TAGS_INVALID',
                'metadata.tags',
                `metadata.tags must be an array with at most ${COMPOSITION_MAX_TAGS} items.`,
            ))
            return
        }
        const seen = new Set<string>()
        value.tags.forEach((tag, index) => {
            if (!isNonEmptyString(tag)) {
                errors.push(issue(
                    'COMPOSITION_METADATA_TAGS_INVALID',
                    `metadata.tags[${index}]`,
                    'metadata.tags items must be non-empty strings.',
                ))
                return
            }
            if (seen.has(tag)) {
                errors.push(issue(
                    'COMPOSITION_METADATA_TAG_DUPLICATE',
                    `metadata.tags[${index}]`,
                    `Tag "${tag}" is duplicated.`,
                ))
                return
            }
            seen.add(tag)
        })
    }
}

function sumDurations(scenes: unknown): number {
    if (!Array.isArray(scenes)) return 0
    let total = 0
    for (const scene of scenes) {
        if (isPlainObject(scene) && isPositiveInteger(scene.durationMs)) {
            total += scene.durationMs
        }
    }
    return total
}

/**
 * Valida uma composicao contra um manifesto de projeto qualquer. Ambos sao
 * dados de entrada: o nucleo nao le arquivos e nao conhece projetos especificos.
 */
export function validateComposition(compositionInput: unknown, projectInput: unknown): CompositionValidationReport {
    const errors: ValidationIssue[] = []

    const projectReport = validateProjectManifest(projectInput)
    if (!projectReport.valid) {
        errors.push(issue(
            'COMPOSITION_PROJECT_MANIFEST_INVALID',
            'project',
            `The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`,
        ))
    }

    let compositionId: string | null = null
    let projectId: string | null = null
    let schemaVersion: number | null = null
    let sceneCount = 0
    let format: CompositionReportFormat | null = null
    let rendererAdapter: string | null = null

    if (!isPlainObject(compositionInput)) {
        errors.push(issue(
            'COMPOSITION_INVALID',
            '',
            'Composition must be a JSON object.',
        ))
    } else {
        const record = compositionInput

        for (const key of Object.keys(record)) {
            if (!(COMPOSITION_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) {
                errors.push(issue(
                    'COMPOSITION_UNKNOWN_FIELD',
                    key,
                    `Unknown top-level field "${key}"; the schema does not allow additional properties.`,
                ))
            }
        }

        if (record.schemaVersion !== COMPOSITION_SCHEMA_VERSION) {
            errors.push(issue(
                'COMPOSITION_SCHEMA_VERSION_UNSUPPORTED',
                'schemaVersion',
                `schemaVersion must be ${COMPOSITION_SCHEMA_VERSION}.`,
            ))
        }

        if (!isNonEmptyString(record.projectId)) {
            errors.push(issue(
                'COMPOSITION_PROJECT_ID_REQUIRED',
                'projectId',
                'projectId is required and must be a non-empty string.',
            ))
        } else if (!KEBAB_CASE_PATTERN.test(record.projectId)) {
            errors.push(issue(
                'COMPOSITION_PROJECT_ID_INVALID',
                'projectId',
                'projectId must be kebab-case (lowercase letters, digits and dashes).',
            ))
        } else {
            projectId = record.projectId
        }

        if (!isNonEmptyString(record.id)) {
            errors.push(issue(
                'COMPOSITION_ID_REQUIRED',
                'id',
                'id is required and must be a non-empty string.',
            ))
        } else if (!KEBAB_CASE_PATTERN.test(record.id)) {
            errors.push(issue(
                'COMPOSITION_ID_INVALID',
                'id',
                'id must be kebab-case (lowercase letters, digits and dashes).',
            ))
        } else {
            compositionId = record.id
        }

        if (!isNonEmptyString(record.title)) {
            errors.push(issue(
                'COMPOSITION_TITLE_REQUIRED',
                'title',
                'title is required and must be a non-empty string.',
            ))
        }

        if (!isNonEmptyString(record.locale)) {
            errors.push(issue(
                'COMPOSITION_LOCALE_REQUIRED',
                'locale',
                'locale is required and must be a non-empty string.',
            ))
        }

        format = validateFormat(record.format, errors)
        sceneCount = validateScenes(record.scenes, errors)
        rendererAdapter = validateRenderer(record.renderer, errors)

        if (record.metadata !== undefined) {
            validateMetadata(record.metadata, errors)
        }
    }

    if (typeof compositionInput === 'object' && compositionInput !== null) {
        schemaVersion = isPlainObject(compositionInput) && typeof compositionInput.schemaVersion === 'number'
            ? compositionInput.schemaVersion
            : null
    }

    if (projectReport.valid && isPlainObject(compositionInput)) {
        const project = projectInput as Record<string, unknown>

        if (projectId !== null && projectId !== project.id) {
            errors.push(issue(
                'COMPOSITION_PROJECT_ID_MISMATCH',
                'projectId',
                `composition.projectId "${projectId}" does not match project.id "${String(project.id)}".`,
            ))
        }

        if (isNonEmptyString(compositionInput.locale) && compositionInput.locale !== project.locale) {
            errors.push(issue(
                'COMPOSITION_LOCALE_MISMATCH',
                'locale',
                `composition.locale "${compositionInput.locale}" does not match project.locale "${String(project.locale)}".`,
            ))
        }

        if (format !== null) {
            const profiles = Array.isArray(project.outputProfiles) ? project.outputProfiles : []
            if (!profiles.includes(format.profile)) {
                errors.push(issue(
                    'COMPOSITION_PROFILE_NOT_IN_PROJECT',
                    'format.profile',
                    `format.profile "${format.profile}" is not declared in project.outputProfiles.`,
                ))
            }
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings: [],
        summary: errors.length === 0 ? COMPOSITION_VALID_SUMMARY : compositionInvalidSummary(errors.length),
        projectId,
        compositionId,
        schemaVersion,
        sceneCount,
        totalDurationMs: sumDurations(isPlainObject(compositionInput) ? compositionInput.scenes : undefined),
        format,
        rendererAdapter,
    }
}
