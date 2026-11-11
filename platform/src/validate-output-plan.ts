import {
    OUTPUT_PLAN_ASPECT_RATIO_PATTERN,
    OUTPUT_PLAN_FPS_MAX,
    OUTPUT_PLAN_FPS_MIN,
    OUTPUT_PLAN_IMAGE_FIELDS,
    OUTPUT_PLAN_SCHEMA_VERSION,
    OUTPUT_PLAN_TOP_LEVEL_FIELDS,
    OUTPUT_PLAN_VIDEO_FIELDS,
    REQUIRES_INSPECTION_IMAGE,
    REQUIRES_INSPECTION_VIDEO,
    type OutputPlan,
    type OutputPlanGeometry,
    type RequiresInspection,
    type RuleAssessmentScope,
} from './output-plan-contract.js'
import { findOutputProfile } from './output-profiles/catalog.js'
import { findCatalogRule } from './output-profiles/rules.js'
import { CATALOG_VERSION, OUTPUT_MEDIA_KINDS, RULE_CONTEXTS } from './output-profiles/types.js'
import type { OutputMediaKind, OutputProfile, RuleContext, RuleValue } from './output-profiles/types.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    OUTPUT_PLAN_VALID_SUMMARY,
    issue,
    outputPlanInvalidSummary,
    type OutputPlanReport,
    type ValidationIssue,
} from './validation-report.js'
import { validateProjectManifest } from './validate-project.js'

/**
 * Validacao do OutputPlan v1: estrutura, vinculos com projeto e catalogo e
 * avaliacao das regras do perfil. Ver docs/planejamento/R001-formatos-sociais.md
 * (secoes 6.1, 6.2, 6.3 e 6.4).
 *
 * Camadas separadas: os **limites estruturais** vem de `output-plan-contract.ts`
 * e a **relacao semantica** com o catalogo e decidida aqui. Divergencia de
 * preset interno nunca e escrita como exigencia da rede, e exigencia oficial so
 * vira erro com o contexto declarado e o dado necessario em maos. Esta funcao
 * nao le arquivo, nao acessa rede, nao muta entrada e nao emite plano.
 */

/** Campos do relatorio que dependem do plano lido ou do catalogo. */
type ReportEcho = Pick<
    OutputPlanReport,
    'catalogVersion' | 'profileId' | 'profileRevision' | 'mediaKind' | 'geometry' | 'fps' | 'pendingRuleIds' | 'requiresInspection'
>

const EMPTY_ECHO: ReportEcho = {
    catalogVersion: null,
    profileId: null,
    profileRevision: null,
    mediaKind: null,
    geometry: null,
    fps: null,
    pendingRuleIds: [],
    requiresInspection: [],
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isSafePositiveInteger(value: unknown): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value > 0 && value <= Number.MAX_SAFE_INTEGER
}

function isKebabCase(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function isMediaKind(value: unknown): value is OutputMediaKind {
    return typeof value === 'string' && (OUTPUT_MEDIA_KINDS as readonly string[]).includes(value)
}

function isRuleContext(value: unknown): value is RuleContext {
    return typeof value === 'string' && (RULE_CONTEXTS as readonly string[]).includes(value)
}

/** Orientacao real derivada das dimensoes; quadrada nao e vertical. */
function orientationOf(width: number, height: number): 'square' | 'portrait' | 'landscape' {
    if (width === height) return 'square'
    return height > width ? 'portrait' : 'landscape'
}

/**
 * Fatos que a camada chamadora traz. `path` e o campo de onde eles vem;
 * `geometry` e `durationMs` sao nulos quando aquela camada nao carrega o dado,
 * o que produz aviso de nao-avaliabilidade em vez de conclusao ficticia.
 */
export interface RuleAssessmentFacts {
    readonly path: string
    readonly geometry: OutputPlanGeometry | null
    readonly durationMs: number | null
}

export interface RuleAssessmentInput {
    readonly profile: OutputProfile
    /** Contexto declarado no documento; null quando a chave esta ausente. */
    readonly ruleContext: RuleContext | null
    readonly scope: RuleAssessmentScope
    readonly facts: RuleAssessmentFacts
}

export interface RuleAssessment {
    readonly errors: ValidationIssue[]
    readonly warnings: ValidationIssue[]
}

/**
 * Unica regra avaliada pela camada de saida: duracao declarada. Os demais tipos
 * de valor pertencem ao plano, cujo relatorio e embutido na compatibilidade —
 * avaliar de novo duplicaria diagnostico entre camadas.
 */
const COMPOSITION_ASSESSED_KINDS: readonly RuleValue['kind'][] = ['max-duration-seconds']

/** Codigo do erro oficial conforme a camada que tinha o dado. */
function officialErrorCode(scope: RuleAssessmentScope): string {
    return scope === 'output-plan' ? 'OUTPUT_PLAN_OFFICIAL_REQUIREMENT_VIOLATED' : 'OUTPUT_COMPAT_DURATION_EXCEEDED'
}

/** Rotulo do escopo certificado: um `@contexto` por item, na ordem declarada no catalogo. */
function scopeLabel(contexts: readonly RuleContext[]): string {
    return contexts.map((context) => `@${context}`).join(', ')
}

interface RuleValueOutcome {
    readonly satisfied: boolean
    readonly path: string
    readonly detail: string
}

/**
 * Algoritmo unico de avaliacao das referencias de regra de um perfil (§6.4).
 *
 * Nao ha `if` por nome de rede, ID de perfil ou marca: o que muda o resultado
 * sao dados do catalogo (classe, estado de aplicacao, escopo certificado da
 * fonte) e o escopo da camada. Estado `informational`/`not-evaluated` e
 * recomendacao nunca viram erro; `requirement` com estado `applies` so erra com
 * o contexto declarado dentro do escopo da regra e o documento trazendo o dado.
 */
export function assessProfileRules(input: RuleAssessmentInput): RuleAssessment {
    const errors: ValidationIssue[] = []
    const warnings: ValidationIssue[] = []

    input.profile.rules.forEach((reference, index) => {
        const rulePath = `rules[${index}]`
        const rule = findCatalogRule(reference.ruleId)

        if (rule === null) {
            errors.push(issue(
                'OUTPUT_PLAN_RULE_UNRESOLVED',
                rulePath,
                `Rule reference "${reference.ruleId}" does not resolve in the catalog rule registry.`,
            ))
            return
        }

        if (rule.kind === 'pending-source') {
            // Pendencia de fonte vive em pendingRuleIds; nao e avaliacao.
            return
        }

        if (rule.kind === 'internal-default') {
            // Default interno alimenta a comparacao de preset, nao a avaliacao
            // de regra oficial; um perfil que o citasse em `rules` nao ganharia
            // exigencia de rede por isso.
            return
        }

        if (input.scope === 'composition-output'
            && !(rule.value !== undefined && COMPOSITION_ASSESSED_KINDS.includes(rule.value.kind))) {
            return
        }

        if (reference.state === 'informational') {
            warnings.push(issue(
                'OUTPUT_PLAN_RULE_INFORMATIONAL',
                rulePath,
                `Rule "${rule.id}" (${scopeLabel(rule.contexts)}) is informational for profile "${input.profile.id}"; it is never a plan error.`,
            ))
            return
        }

        if (reference.state === 'not-evaluated') {
            warnings.push(issue(
                'OUTPUT_PLAN_RULE_NOT_EVALUATED',
                rulePath,
                `Rule "${rule.id}" (${scopeLabel(rule.contexts)}) has no evidence of reaching profile "${input.profile.id}"; application is not evaluated.`,
            ))
            return
        }

        if (input.ruleContext === null) {
            warnings.push(issue(
                'OUTPUT_PLAN_CONTEXT_NOT_DECLARED',
                'ruleContext',
                `Rule "${rule.id}" (${scopeLabel(rule.contexts)}) cannot be assessed because the document declares no context; structural validity does not confirm an official requirement.`,
            ))
            return
        }

        if (!rule.contexts.includes(input.ruleContext)) {
            warnings.push(issue(
                'OUTPUT_PLAN_RULE_NOT_APPLIED',
                rulePath,
                `Rule "${rule.id}" is stated for context ${scopeLabel(rule.contexts)}, not for the declared @${input.ruleContext}; it is not applied.`,
            ))
            return
        }

        const outcome = rule.value === undefined ? null : assessRuleValue(rule.value, input.facts)
        if (outcome === null) {
            warnings.push(issue(
                'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
                input.facts.path,
                `Rule "${rule.id}" (${scopeLabel(rule.contexts)}) is stated for the declared context but needs data this document does not carry; nothing was verified.`,
            ))
            return
        }

        if (outcome.satisfied) return

        const origin = rule.kind === 'requirement' ? 'official rule' : 'recommendation'
        const message = `${outcome.detail}${origin} "${rule.id}" ${scopeLabel(rule.contexts)} states: ${rule.statement}`
        if (rule.kind === 'requirement') {
            errors.push(issue(officialErrorCode(input.scope), outcome.path, message))
        } else {
            warnings.push(issue('OUTPUT_PLAN_RECOMMENDATION_NOT_MET', outcome.path, message))
        }
    })

    return { errors, warnings }
}

/** `null` significa "a camada nao traz o dado desta regra", nunca "esta ok". */
function assessRuleValue(value: RuleValue, facts: RuleAssessmentFacts): RuleValueOutcome | null {
    if (value.kind === 'max-duration-seconds') {
        if (facts.durationMs === null) return null
        return {
            satisfied: facts.durationMs <= value.seconds * 1000,
            path: facts.path,
            detail: `Declared scene total of ${facts.durationMs} ms exceeds ${value.seconds} s. `,
        }
    }

    const geometry = facts.geometry
    if (geometry === null) return null

    if (value.kind === 'aspect-ratios') {
        return {
            satisfied: value.ratios.includes(geometry.aspectRatio),
            path: `${facts.path}.aspectRatio`,
            detail: `Aspect ratio "${geometry.aspectRatio}" is outside the allowed set ${value.ratios.join(', ')}. `,
        }
    }

    if (value.kind === 'orientation-any-of') {
        const orientation = orientationOf(geometry.width, geometry.height)
        return {
            satisfied: value.orientations.includes(orientation),
            path: facts.path,
            detail: `Geometry ${geometry.width}x${geometry.height} is ${orientation}, outside ${value.orientations.join(' or ')}. `,
        }
    }

    if (value.kind === 'min-dimensions') {
        return {
            satisfied: geometry.width >= value.width && geometry.height >= value.height,
            path: facts.path,
            detail: `Geometry ${geometry.width}x${geometry.height} is below the minimum ${value.width}x${value.height}. `,
        }
    }

    // `allowed-formats`, `container`, `max-count`, `geometry` e `fps` dependem
    // de arquivo, de campo que o plano nao tem ou do preset ja comparado abaixo.
    return null
}

/** Necessidades de inspecao do tipo de midia, na ordem fixa de §6.2.1. */
export function requiresInspectionFor(mediaKind: OutputMediaKind): readonly RequiresInspection[] {
    return mediaKind === 'image' ? REQUIRES_INSPECTION_IMAGE : REQUIRES_INSPECTION_VIDEO
}

/**
 * Eco de um perfil do catalogo para relatorios sem plano: os campos vém da
 * tabela lida, nao de um artefato resolvido. Usado quando a resolucao falha
 * antes de produzir o OutputPlan.
 */
export function catalogProfileEcho(profile: OutputProfile): ReportEcho {
    return {
        catalogVersion: CATALOG_VERSION,
        profileId: profile.id,
        profileRevision: profile.revision,
        mediaKind: profile.mediaKind,
        geometry: profile.geometry,
        fps: profile.mediaKind === 'video' ? profile.fps : null,
        pendingRuleIds: profile.pendingIds,
        requiresInspection: requiresInspectionFor(profile.mediaKind),
    }
}

/**
 * Relatorio sem plano, para a resolucao que falhou antes de produzir o
 * artefato: os campos ecoam o perfil do catalogo quando ele existe e ficam
 * nulos quando nao existe. Nunca inventa plano nem completa default.
 */
export interface OutputPlanDiagnosticInput {
    readonly projectId: string | null
    readonly profileId: string | null
    readonly ruleContext: RuleContext | null
    readonly profile: OutputProfile | null
    readonly errors: readonly ValidationIssue[]
    readonly warnings?: readonly ValidationIssue[]
}

export function outputPlanDiagnosticReport(input: OutputPlanDiagnosticInput): OutputPlanReport {
    const echo: ReportEcho = input.profile === null
        ? { ...EMPTY_ECHO, profileId: input.profileId }
        : catalogProfileEcho(input.profile)
    return finalize([...input.errors], [...(input.warnings ?? [])], input.projectId, input.ruleContext, echo)
}

/**
 * Le um artefato OutputPlan sem emitir diagnostico. Existe para a camada de
 * compatibilidade comparar **o plano**, nao campos ecoados de um relatorio:
 * `validateOutputPlan` devolve relatorio e a serializacao do artefato continua
 * sendo obra exclusiva de `resolve-output-profile.ts`. Os limites estruturais
 * lidos aqui sao os mesmos de `output-plan-contract.ts`; `null` significa
 * "nada disto e um plano", nunca plano parcial.
 */
export function readOutputPlan(planInput: unknown): OutputPlan | null {
    if (!isPlainObject(planInput)) return null

    const mediaKind = isMediaKind(planInput.mediaKind) ? planInput.mediaKind : null
    const profileId = isKebabCase(planInput.profileId) ? planInput.profileId : null
    const projectId = isKebabCase(planInput.projectId) ? planInput.projectId : null
    if (mediaKind === null || profileId === null || projectId === null) return null
    if (planInput.schemaVersion !== OUTPUT_PLAN_SCHEMA_VERSION) return null
    if (typeof planInput.catalogVersion !== 'string') return null
    if (!isSafePositiveInteger(planInput.profileRevision)) return null

    const ruleContext = planInput.ruleContext === undefined
        ? null
        : isRuleContext(planInput.ruleContext) ? planInput.ruleContext : null
    if (planInput.ruleContext !== undefined && ruleContext === null) return null

    const payload = planInput[mediaKind]
    if (!isPlainObject(payload) || planInput[mediaKind === 'image' ? 'video' : 'image'] !== undefined) return null
    const geometry = readGeometry(payload)
    if (geometry === null) return null

    const context = ruleContext === null ? {} : { ruleContext }

    if (mediaKind === 'image') {
        return {
            schemaVersion: OUTPUT_PLAN_SCHEMA_VERSION,
            projectId,
            catalogVersion: planInput.catalogVersion,
            profileId,
            profileRevision: planInput.profileRevision,
            mediaKind,
            ...context,
            image: geometry,
        }
    }

    const fps = payload.fps
    if (!Number.isInteger(fps) || (fps as number) < OUTPUT_PLAN_FPS_MIN || (fps as number) > OUTPUT_PLAN_FPS_MAX) {
        return null
    }
    return {
        schemaVersion: OUTPUT_PLAN_SCHEMA_VERSION,
        projectId,
        catalogVersion: planInput.catalogVersion,
        profileId,
        profileRevision: planInput.profileRevision,
        mediaKind,
        ...context,
        video: { ...geometry, fps: fps as number },
    }
}

function readGeometry(payload: Record<string, unknown>): OutputPlanGeometry | null {
    const fields = OUTPUT_PLAN_IMAGE_FIELDS
    for (const key of Object.keys(payload)) {
        if (!(fields as readonly string[]).includes(key) && key !== 'fps') return null
    }
    if (!isSafePositiveInteger(payload.width) || !isSafePositiveInteger(payload.height)) return null
    if (typeof payload.aspectRatio !== 'string' || !OUTPUT_PLAN_ASPECT_RATIO_PATTERN.test(payload.aspectRatio)) {
        return null
    }
    return {
        width: payload.width,
        height: payload.height,
        aspectRatio: payload.aspectRatio,
    }
}

/**
 * Valida um OutputPlan qualquer contra um ProjectManifest qualquer. Devolve
 * relatorio, nunca plano. Ordem de emissao: topo do plano, payload, projeto,
 * catalogo, preset, regras.
 */
export function validateOutputPlan(planInput: unknown, projectInput: unknown): OutputPlanReport {
    const errors: ValidationIssue[] = []
    const warnings: ValidationIssue[] = []
    const echo: ReportEcho = { ...EMPTY_ECHO }

    const projectReport = validateProjectManifest(projectInput)
    const projectId = projectReport.valid ? projectReport.projectId : null

    if (!isPlainObject(planInput)) {
        errors.push(issue('OUTPUT_PLAN_INVALID', '', 'Output plan must be a JSON object.'))
        return finalize(errors, warnings, null, null, echo)
    }
    const record = planInput

    for (const key of Object.keys(record)) {
        if (!(OUTPUT_PLAN_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'OUTPUT_PLAN_UNKNOWN_FIELD',
                key,
                `Unknown top-level field "${key}"; the schema does not allow additional properties.`,
            ))
        }
    }

    if (record.schemaVersion !== OUTPUT_PLAN_SCHEMA_VERSION) {
        errors.push(issue(
            'OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED',
            'schemaVersion',
            `schemaVersion must be ${OUTPUT_PLAN_SCHEMA_VERSION}.`,
        ))
    }

    if (!isKebabCase(record.projectId)) {
        errors.push(issue(
            'OUTPUT_PLAN_PROJECT_ID_INVALID',
            'projectId',
            'projectId is required and must be a kebab-case string.',
        ))
    }

    echo.catalogVersion = typeof record.catalogVersion === 'string' ? record.catalogVersion : null
    if (record.catalogVersion !== CATALOG_VERSION) {
        errors.push(issue(
            'OUTPUT_PLAN_CATALOG_VERSION_UNKNOWN',
            'catalogVersion',
            `catalogVersion must be "${CATALOG_VERSION}", the only catalog this build resolves against.`,
        ))
    }

    const profileId = isKebabCase(record.profileId) ? record.profileId : null
    if (profileId === null) {
        errors.push(issue(
            'OUTPUT_PROFILE_ID_INVALID',
            'profileId',
            'profileId is required and must be a kebab-case string.',
        ))
    } else {
        echo.profileId = profileId
    }

    if (!isSafePositiveInteger(record.profileRevision)) {
        errors.push(issue(
            'OUTPUT_PLAN_PROFILE_REVISION_INVALID',
            'profileRevision',
            'profileRevision must be a safe positive integer.',
        ))
    } else {
        echo.profileRevision = record.profileRevision
    }

    if (!isMediaKind(record.mediaKind)) {
        errors.push(issue(
            'OUTPUT_PLAN_MEDIA_KIND_INVALID',
            'mediaKind',
            `mediaKind must be one of ${OUTPUT_MEDIA_KINDS.map((kind) => `"${kind}"`).join(', ')}.`,
        ))
    } else {
        echo.mediaKind = record.mediaKind
    }

    if ('ruleContext' in record && !isRuleContext(record.ruleContext)) {
        errors.push(issue(
            'OUTPUT_PLAN_RULE_CONTEXT_INVALID',
            'ruleContext',
            `ruleContext, when present, must be one of ${RULE_CONTEXTS.map((context) => `"${context}"`).join(', ')}; absence is an omitted key, never null.`,
        ))
    }
    const ruleContext = isRuleContext(record.ruleContext) ? record.ruleContext : null

    const payloadKey = echo.mediaKind
    let payload: Record<string, unknown> | null = null

    if (payloadKey === null) {
        if (record.image !== undefined || record.video !== undefined) {
            errors.push(issue(
                'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH',
                'mediaKind',
                'mediaKind is invalid, so neither the "image" nor the "video" payload can be resolved.',
            ))
        }
    } else {
        const otherKey = payloadKey === 'image' ? 'video' : 'image'
        const expected = record[payloadKey]
        if (!isPlainObject(expected)) {
            errors.push(issue(
                'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH',
                payloadKey,
                `A "${payloadKey}" plan requires the "${payloadKey}" payload as an object.`,
            ))
        } else if (record[otherKey] !== undefined) {
            errors.push(issue(
                'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH',
                otherKey,
                `A "${payloadKey}" plan must not carry a "${otherKey}" payload.`,
            ))
        } else {
            payload = expected
        }
    }

    let geometry: OutputPlanGeometry | null = null
    if (payload !== null && payloadKey !== null) {
        const fields = payloadKey === 'image' ? OUTPUT_PLAN_IMAGE_FIELDS : OUTPUT_PLAN_VIDEO_FIELDS
        for (const key of Object.keys(payload)) {
            if (!(fields as readonly string[]).includes(key)) {
                errors.push(issue(
                    'OUTPUT_PLAN_UNKNOWN_FIELD',
                    `${payloadKey}.${key}`,
                    `Unknown "${payloadKey}" payload field "${key}"; the schema does not allow additional properties.`,
                ))
            }
        }

        const widthOk = isSafePositiveInteger(payload.width)
        const heightOk = isSafePositiveInteger(payload.height)
        const ratioOk = typeof payload.aspectRatio === 'string' && OUTPUT_PLAN_ASPECT_RATIO_PATTERN.test(payload.aspectRatio)
        if (!widthOk) {
            errors.push(issue('OUTPUT_PLAN_DIMENSIONS_INVALID', `${payloadKey}.width`, 'width must be a safe positive integer.'))
        }
        if (!heightOk) {
            errors.push(issue('OUTPUT_PLAN_DIMENSIONS_INVALID', `${payloadKey}.height`, 'height must be a safe positive integer.'))
        }
        if (!ratioOk) {
            errors.push(issue(
                'OUTPUT_PLAN_ASPECT_RATIO_INVALID',
                `${payloadKey}.aspectRatio`,
                'aspectRatio must be a string in "W:H" form.',
            ))
        }
        if (widthOk && heightOk && ratioOk) {
            geometry = {
                width: payload.width as number,
                height: payload.height as number,
                aspectRatio: payload.aspectRatio as string,
            }
            echo.geometry = geometry
        }

        if (payloadKey === 'video') {
            const fpsOk = Number.isInteger(payload.fps)
                && (payload.fps as number) >= OUTPUT_PLAN_FPS_MIN
                && (payload.fps as number) <= OUTPUT_PLAN_FPS_MAX
            if (!fpsOk) {
                errors.push(issue(
                    'OUTPUT_PLAN_FPS_INVALID',
                    'video.fps',
                    `fps must be an integer between ${OUTPUT_PLAN_FPS_MIN} and ${OUTPUT_PLAN_FPS_MAX}.`,
                ))
            } else {
                echo.fps = payload.fps as number
            }
        }
    }

    // Pendencias e necessidades de inspecao sao fatos do perfil no catalogo, nao do
    // projeto: continuam no relatorio mesmo quando a relacao com o manifesto falha.
    const profile = profileId === null ? null : findOutputProfile(profileId)
    if (profile !== null) {
        const fromCatalog = catalogProfileEcho(profile)
        echo.pendingRuleIds = fromCatalog.pendingRuleIds
        echo.requiresInspection = fromCatalog.requiresInspection
    }

    if (!projectReport.valid) {
        errors.push(issue(
            'OUTPUT_PROJECT_INVALID',
            'project',
            `The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`,
        ))
        return finalize(errors, warnings, projectId, ruleContext, echo)
    }

    if (profileId === null) {
        return finalize(errors, warnings, projectId, ruleContext, echo)
    }

    if (profile === null) {
        errors.push(issue(
            'OUTPUT_PROFILE_UNKNOWN',
            'profileId',
            `profileId "${profileId}" does not exist in catalog version "${CATALOG_VERSION}".`,
        ))
        return finalize(errors, warnings, projectId, ruleContext, echo)
    }

    const allowed = allowedProfilesOf(projectInput)
    if (!allowed.includes(profile.id)) {
        errors.push(issue(
            'OUTPUT_PROFILE_NOT_ALLOWED',
            'profileId',
            `Profile "${profile.id}" is not listed in project "${String(projectId)}" outputProfiles.`,
        ))
    }

    const planProjectId = isKebabCase(record.projectId) ? record.projectId : null
    if (planProjectId !== null && planProjectId !== projectId) {
        errors.push(issue(
            'OUTPUT_PLAN_PROJECT_MISMATCH',
            'projectId',
            `plan.projectId "${planProjectId}" does not match project.id "${String(projectId)}".`,
        ))
    }

    if (echo.profileRevision !== null && echo.profileRevision !== profile.revision) {
        errors.push(issue(
            'OUTPUT_PLAN_PROFILE_REVISION_INVALID',
            'profileRevision',
            `profileRevision ${echo.profileRevision} is not the catalog revision ${profile.revision} of profile "${profile.id}".`,
        ))
    }

    if (echo.mediaKind !== null && echo.mediaKind !== profile.mediaKind) {
        errors.push(issue(
            'OUTPUT_PLAN_MEDIA_KIND_MISMATCH',
            'mediaKind',
            `plan mediaKind "${echo.mediaKind}" is not the mediaKind "${profile.mediaKind}" of profile "${profile.id}".`,
        ))
    }

    if (geometry !== null && payloadKey !== null) {
        pushPresetIssue(errors, 'width', geometry.width, profile.geometry.width, payloadKey, profile)
        pushPresetIssue(errors, 'height', geometry.height, profile.geometry.height, payloadKey, profile)
        if (geometry.aspectRatio !== profile.geometry.aspectRatio) {
            errors.push(issue(
                'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
                `${payloadKey}.aspectRatio`,
                `aspectRatio "${geometry.aspectRatio}" is not the internal default preset "${profile.geometry.aspectRatio}" of profile "${profile.id}" (internal default ${defaultIdsFor(profile, 'geometry')}).`,
            ))
        }
    }

    if (payloadKey === 'video' && echo.fps !== null && profile.mediaKind === 'video' && echo.fps !== profile.fps) {
        errors.push(issue(
            'OUTPUT_PLAN_FPS_NOT_IN_CATALOG',
            'video.fps',
            `fps ${echo.fps} is not the internal default preset ${profile.fps} of profile "${profile.id}" (internal default ${defaultIdsFor(profile, 'fps')}).`,
        ))
    }

    const assessment = assessProfileRules({
        profile,
        ruleContext,
        scope: 'output-plan',
        facts: { path: payloadKey ?? 'mediaKind', geometry, durationMs: null },
    })
    errors.push(...assessment.errors)
    warnings.push(...assessment.warnings)

    return finalize(errors, warnings, projectId, ruleContext, echo)
}

function pushPresetIssue(
    errors: ValidationIssue[],
    field: 'width' | 'height',
    value: number,
    presetValue: number,
    payloadKey: string,
    profile: OutputProfile,
): void {
    if (value === presetValue) return
    errors.push(issue(
        'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        `${payloadKey}.${field}`,
        `${field} ${value} is not the internal default preset ${presetValue} of profile "${profile.id}" (internal default ${defaultIdsFor(profile, 'geometry')}).`,
    ))
}

/** IDs de default interno que sustentam o preset comparado; servem so a mensagem. */
function defaultIdsFor(profile: OutputProfile, kind: 'geometry' | 'fps'): string {
    const ids = profile.defaults.filter((id) => {
        const rule = findCatalogRule(id)
        return rule !== null && rule.kind === 'internal-default' && rule.value.kind === kind
    })
    return ids.length > 0 ? ids.join(', ') : 'catalog preset'
}

/**
 * Allowlist lida do manifesto **ja aceito** pelo validador de projeto, sem
 * reimplementar regra nenhuma; o relatorio de projeto nao e reemitido aqui.
 */
function allowedProfilesOf(projectInput: unknown): string[] {
    if (!isPlainObject(projectInput)) return []
    const profiles = projectInput.outputProfiles
    return Array.isArray(profiles) ? profiles.filter((item): item is string => typeof item === 'string') : []
}

function finalize(
    errors: ValidationIssue[],
    warnings: ValidationIssue[],
    projectId: string | null,
    ruleContext: RuleContext | null,
    echo: ReportEcho,
): OutputPlanReport {
    return {
        valid: errors.length === 0,
        errors,
        warnings,
        summary: errors.length === 0 ? OUTPUT_PLAN_VALID_SUMMARY : outputPlanInvalidSummary(errors.length),
        projectId,
        profileId: echo.profileId,
        catalogVersion: echo.catalogVersion,
        profileRevision: echo.profileRevision,
        mediaKind: echo.mediaKind,
        ruleContext,
        geometry: echo.geometry,
        fps: echo.fps,
        pendingRuleIds: echo.pendingRuleIds,
        requiresInspection: echo.requiresInspection,
    }
}
