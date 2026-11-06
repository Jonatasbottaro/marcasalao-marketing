/**
 * Validador de composicao (Composition v1).
 *
 * Valida a estrutura propria da composicao e o vinculo com um ProjectManifest
 * informado explicitamente: mesmo projeto, mesmo locale e profile presente em
 * outputProfiles. Nao le arquivos, nao acessa rede, nao abre assets, nao
 * verifica existencia fisica e nao conhece nenhum projeto especifico.
 *
 * Os erros sao coletados todos, em ordem de emissao fixa: primeiro o manifesto
 * do projeto, depois a estrutura da composicao, depois os vinculos entre eles.
 * Warnings sao heuristicas tecnicas (texto longo, cena curta, renderer
 * undecided): nao tornam a composicao invalida e nao substituem aprovacao
 * editorial.
 */

import {
    COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE,
    COMPOSITION_FPS_MAX,
    COMPOSITION_FPS_MIN,
    COMPOSITION_MAX_TAGS,
    COMPOSITION_MAX_TEXT_LENGTH,
    COMPOSITION_METADATA_STATUSES,
    COMPOSITION_MIN_TEXT_DURATION_MS,
    COMPOSITION_SCENE_TYPES,
    COMPOSITION_SCHEMA_VERSION,
    COMPOSITION_TOP_LEVEL_FIELDS,
    KEBAB_CASE_PATTERN,
    type CompositionSceneType,
} from './composition-contract.js'
import { containsControlCharacter, inspectRelativePath, type RelativePathViolation } from './relative-path.js'
import { validateProjectManifest } from './validate-project.js'
import {
    COMPOSITION_VALID_SUMMARY,
    compositionInvalidSummary,
    issue,
    type CompositionReportFormat,
    type CompositionValidationReport,
    type ValidationIssue,
} from './validation-report.js'

/**
 * Cada violacao lexica de caminho e traduzida para o codigo e o caminho de erro
 * proprios da Composition; a deteccao em si e compartilhada com o ProjectManifest.
 */
const ASSET_PATH_VIOLATIONS: Record<RelativePathViolation, { code: string; message: string }> = {
    CONTROL_CHARACTER: {
        code: 'COMPOSITION_ASSET_PATH_CONTROL_CHARACTER',
        message: 'asset.path must not contain control characters.',
    },
    ABSOLUTE: {
        code: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
        message: 'asset.path must be a relative path (POSIX absolute, drive letter and UNC are rejected).',
    },
    URL: {
        code: 'COMPOSITION_ASSET_PATH_URL',
        message: 'asset.path must not be a URL or use any protocol (http, https, file).',
    },
    TRAVERSAL: {
        code: 'COMPOSITION_ASSET_PATH_TRAVERSAL',
        message: 'asset.path must not traverse outside the project (".." segments are not allowed).',
    },
    SENSITIVE: {
        code: 'COMPOSITION_ASSET_PATH_SENSITIVE',
        message: 'asset.path must not point to sensitive files (.env, keys, credentials).',
    },
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

/**
 * Forma canonica exigida pelo espelho normativo (`^[hH][tT][tT][pP][sS]?://`): o prefixo
 * precisa estar literalmente na string. Sem essa checagem, o parser de URL normalizaria
 * `http:/example.com` e `https:\\example.com` em URLs validas, e o core aceitaria como
 * `valid: true` uma estrutura que o schema draft-07 declara invalida.
 */
const CANONICAL_HTTP_HREF = /^https?:\/\//i

/**
 * href e tratado somente como dado: o parser de URL do Node nao resolve DNS, nao abre
 * conexao e nao faz nenhuma requisicao. Aceita http(s) absoluto na forma canonica
 * scheme://host, com hostname e sem credenciais (username ou password), em qualquer
 * caixa do protocolo.
 */
type HrefViolation = 'INVALID' | 'CREDENTIALS'

function inspectHttpHref(value: string): HrefViolation | null {
    if (containsControlCharacter(value)) return 'INVALID'
    if (!CANONICAL_HTTP_HREF.test(value)) return 'INVALID'

    let parsed: URL
    try {
        parsed = new URL(value)
    } catch {
        return 'INVALID'
    }

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return 'INVALID'
    if (parsed.hostname.length === 0) return 'INVALID'
    if (parsed.username.length > 0 || parsed.password.length > 0) return 'CREDENTIALS'

    const authority = value.slice(value.indexOf('://') + 3).split(/[/?#]/)[0] ?? ''
    return authority.includes('@') ? 'CREDENTIALS' : null
}

function validateAssetReference(value: unknown, basePath: string, errors: ValidationIssue[]): void {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'COMPOSITION_ASSET_REQUIRED',
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

    if (value.id === undefined || !isNonEmptyString(value.id)) {
        errors.push(issue(
            'COMPOSITION_ASSET_ID_INVALID',
            `${basePath}.id`,
            'asset.id is required and must be a non-empty kebab-case string.',
        ))
    } else if (!KEBAB_CASE_PATTERN.test(value.id)) {
        errors.push(issue(
            'COMPOSITION_ASSET_ID_INVALID',
            `${basePath}.id`,
            'asset.id must be kebab-case (lowercase letters, digits and dashes).',
        ))
    }

    if (value.path === undefined || !isNonEmptyString(value.path)) {
        errors.push(issue(
            'COMPOSITION_ASSET_PATH_REQUIRED',
            `${basePath}.path`,
            'asset.path is required and must be a non-empty relative path.',
        ))
        return
    }

    const assetPath = value.path
    for (const violation of inspectRelativePath(assetPath)) {
        const rule = ASSET_PATH_VIOLATIONS[violation]
        const message = violation === 'URL' && assetPath.startsWith('//')
            ? 'asset.path must not be a protocol-relative URL.'
            : rule.message
        errors.push(issue(rule.code, `${basePath}.path`, message))
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

    const allowedFields: readonly string[] = COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE[sceneType]

    for (const key of Object.keys(value)) {
        if (!allowedFields.includes(key)) {
            if (key === 'asset' && (sceneType === 'text' || sceneType === 'cta')) {
                errors.push(issue(
                    'COMPOSITION_ASSET_NOT_ALLOWED',
                    `${basePath}.asset`,
                    `asset is not allowed in content of a "${sceneType}" scene.`,
                ))
            } else {
                errors.push(issue(
                    'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN',
                    `${basePath}.${key}`,
                    `Field "${key}" is not allowed in content of a "${sceneType}" scene.`,
                ))
            }
        }
    }

    if (sceneType === 'text' || sceneType === 'cta') {
        if (!isNonEmptyString(value.text)) {
            errors.push(issue(
                'COMPOSITION_TEXT_REQUIRED',
                `${basePath}.text`,
                `content.text is required and must be a non-empty string in a "${sceneType}" scene.`,
            ))
        }
        if (sceneType === 'cta' && value.href !== undefined) {
            const href = value.href
            if (!isNonEmptyString(href)) {
                errors.push(issue(
                    'COMPOSITION_CTA_HREF_INVALID',
                    `${basePath}.href`,
                    'content.href must be a non-empty http(s) URL when present; it is never fetched.',
                ))
            } else {
                const violation = inspectHttpHref(href)
                if (violation === 'CREDENTIALS') {
                    errors.push(issue(
                        'COMPOSITION_CTA_HREF_CREDENTIALS',
                        `${basePath}.href`,
                        'content.href must not embed a user or a password.',
                    ))
                } else if (violation === 'INVALID') {
                    errors.push(issue(
                        'COMPOSITION_CTA_HREF_INVALID',
                        `${basePath}.href`,
                        'content.href must be a well-formed absolute http(s) URL with a hostname; relative URLs, other protocols and control characters are rejected in v1.',
                    ))
                }
            }
        }
    }

    if (sceneType === 'image' || sceneType === 'video') {
        if (value.asset === undefined) {
            errors.push(issue(
                'COMPOSITION_ASSET_REQUIRED',
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

interface SceneScanResult {
    sceneCount: number
    totalDurationMs: number | null
    warnings: ValidationIssue[]
}

function validateScenes(value: unknown, errors: ValidationIssue[], warnings: ValidationIssue[]): SceneScanResult {
    if (!Array.isArray(value)) {
        errors.push(issue(
            'COMPOSITION_SCENE_REQUIRED',
            'scenes',
            'scenes is required and must be an array.',
        ))
        return { sceneCount: 0, totalDurationMs: 0, warnings }
    }

    const seenIds = new Set<string>()
    let totalDurationMs = 0
    let overflow = false

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

        if (scene.id === undefined || !isNonEmptyString(scene.id)) {
            errors.push(issue(
                'COMPOSITION_SCENE_ID_REQUIRED',
                `${basePath}.id`,
                'scene.id is required and must be a non-empty string.',
            ))
        } else if (!KEBAB_CASE_PATTERN.test(scene.id)) {
            errors.push(issue(
                'COMPOSITION_SCENE_ID_INVALID',
                `${basePath}.id`,
                'scene.id must be kebab-case (lowercase letters, digits and dashes).',
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
        const typeIsValid =
            typeof sceneType === 'string' && (COMPOSITION_SCENE_TYPES as readonly string[]).includes(sceneType)
        if (!typeIsValid) {
            errors.push(issue(
                'COMPOSITION_SCENE_TYPE_INVALID',
                `${basePath}.type`,
                `scene.type must be one of: ${COMPOSITION_SCENE_TYPES.join(', ')}.`,
            ))
        }

        let durationIsValid = false
        let validDuration: number | null = null
        if (scene.durationMs === undefined) {
            errors.push(issue(
                'COMPOSITION_SCENE_DURATION_INVALID',
                `${basePath}.durationMs`,
                'scene.durationMs is required and must be an integer greater than zero.',
            ))
        } else if (
            typeof scene.durationMs !== 'number' ||
            !Number.isInteger(scene.durationMs) ||
            scene.durationMs <= 0 ||
            scene.durationMs > Number.MAX_SAFE_INTEGER
        ) {
            errors.push(issue(
                'COMPOSITION_SCENE_DURATION_INVALID',
                `${basePath}.durationMs`,
                'scene.durationMs must be a safe integer greater than zero.',
            ))
        } else {
            durationIsValid = true
            validDuration = scene.durationMs
            if (totalDurationMs + validDuration > Number.MAX_SAFE_INTEGER) {
                overflow = true
            } else {
                totalDurationMs += validDuration
            }
        }

        if (scene.content === undefined) {
            errors.push(issue(
                'COMPOSITION_SCENE_CONTENT_REQUIRED',
                `${basePath}.content`,
                'scene.content is required.',
            ))
        } else if (typeIsValid) {
            validateSceneContent(scene.content, sceneType as CompositionSceneType, `${basePath}.content`, errors)
        }

        // Warnings heuristicos, em ordem estavel de cena.
        const sceneText = isPlainObject(scene.content) && isNonEmptyString(scene.content.text)
            ? scene.content.text
            : null
        if (typeIsValid && (sceneType === 'text' || sceneType === 'cta') && sceneText !== null) {
            if (sceneText.length > COMPOSITION_MAX_TEXT_LENGTH) {
                warnings.push(issue(
                    'COMPOSITION_SCENE_TEXT_LONG',
                    `${basePath}.content.text`,
                    `Scene text has ${sceneText.length} characters; more than ${COMPOSITION_MAX_TEXT_LENGTH} is a technical heuristic, not editorial approval.`,
                ))
            }
            if (durationIsValid && validDuration !== null && validDuration < COMPOSITION_MIN_TEXT_DURATION_MS) {
                warnings.push(issue(
                    'COMPOSITION_SCENE_DURATION_SHORT',
                    `${basePath}.durationMs`,
                    `Scene with text lasts ${validDuration} ms; less than ${COMPOSITION_MIN_TEXT_DURATION_MS} ms is a technical heuristic, not editorial approval.`,
                ))
            }
        }
    })

    if (overflow) {
        errors.push(issue(
            'COMPOSITION_DURATION_OVERFLOW',
            'scenes',
            'The sum of scene durations exceeds Number.MAX_SAFE_INTEGER; totalDurationMs is reported as null.',
        ))
        return { sceneCount: value.length, totalDurationMs: null, warnings }
    }

    return { sceneCount: value.length, totalDurationMs, warnings }
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
    if (value.profile === undefined || !isNonEmptyString(value.profile)) {
        errors.push(issue(
            'COMPOSITION_FORMAT_PROFILE_REQUIRED',
            'format.profile',
            'format.profile is required and must be a non-empty string.',
        ))
    } else if (!KEBAB_CASE_PATTERN.test(value.profile)) {
        errors.push(issue(
            'COMPOSITION_FORMAT_PROFILE_INVALID',
            'format.profile',
            'format.profile must be kebab-case (lowercase letters, digits and dashes).',
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

function validateRenderer(value: unknown, errors: ValidationIssue[], warnings: ValidationIssue[]): string | null {
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

    if (value.adapter === undefined || !isNonEmptyString(value.adapter)) {
        errors.push(issue(
            'COMPOSITION_RENDERER_ADAPTER_REQUIRED',
            'renderer.adapter',
            'renderer.adapter is required and must be a non-empty string.',
        ))
        return null
    }

    if (!KEBAB_CASE_PATTERN.test(value.adapter)) {
        errors.push(issue(
            'COMPOSITION_RENDERER_ADAPTER_INVALID',
            'renderer.adapter',
            'renderer.adapter must be kebab-case (lowercase letters, digits and dashes).',
        ))
        return null
    }

    if (value.adapter === 'undecided') {
        warnings.push(issue(
            'COMPOSITION_RENDERER_UNDECIDED',
            'renderer.adapter',
            'renderer.adapter is "undecided": no renderer is adopted by this composition yet.',
        ))
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
                'COMPOSITION_METADATA_INVALID',
                'metadata.tags',
                `metadata.tags must be an array with at most ${COMPOSITION_MAX_TAGS} items.`,
            ))
            return
        }
        const seen = new Set<string>()
        value.tags.forEach((tag, index) => {
            if (!isNonEmptyString(tag)) {
                errors.push(issue(
                    'COMPOSITION_METADATA_INVALID',
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

/**
 * Valida uma composicao contra um manifesto de projeto qualquer. Ambos sao
 * dados de entrada: o nucleo nao le arquivos, nao acessa rede e nao conhece
 * projetos especificos. As entradas nao sao mutadas.
 */
export function validateComposition(compositionInput: unknown, projectInput: unknown): CompositionValidationReport {
    const errors: ValidationIssue[] = []
    const warnings: ValidationIssue[] = []

    const projectReport = validateProjectManifest(projectInput)
    if (!projectReport.valid) {
        errors.push(issue(
            'COMPOSITION_MANIFEST_INVALID',
            'project',
            `The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`,
        ))
    }

    let compositionId: string | null = null
    let projectId: string | null = null
    let schemaVersion: number | null = null
    let sceneCount = 0
    let totalDurationMs: number | null = 0
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

        if (record.projectId === undefined || !isNonEmptyString(record.projectId)) {
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

        if (record.id === undefined || !isNonEmptyString(record.id)) {
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

        const sceneScan = validateScenes(record.scenes, errors, warnings)
        sceneCount = sceneScan.sceneCount
        totalDurationMs = sceneScan.totalDurationMs

        rendererAdapter = validateRenderer(record.renderer, errors, warnings)

        if (record.metadata !== undefined) {
            validateMetadata(record.metadata, errors)
        }

        schemaVersion = typeof record.schemaVersion === 'number' ? record.schemaVersion : null
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
                    'COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED',
                    'format.profile',
                    `format.profile "${format.profile}" is not declared in project.outputProfiles.`,
                ))
            }
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings,
        summary: errors.length === 0 ? COMPOSITION_VALID_SUMMARY : compositionInvalidSummary(errors.length),
        projectId,
        compositionId,
        schemaVersion,
        sceneCount,
        totalDurationMs,
        format,
        rendererAdapter,
    }
}
