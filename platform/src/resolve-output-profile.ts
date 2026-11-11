import { OUTPUT_PLAN_SCHEMA_VERSION, type OutputPlan } from './output-plan-contract.js'
import { CATALOG_VERSION, findOutputProfile, listOutputProfiles } from './output-profiles/catalog.js'
import {
    OUTPUT_MEDIA_KINDS,
    OUTPUT_NETWORKS,
    OUTPUT_PUBLICATIONS,
    RULE_CONTEXTS,
} from './output-profiles/types.js'
import type {
    OutputMediaKind,
    OutputNetwork,
    OutputProfile,
    OutputPublication,
    RuleContext,
} from './output-profiles/types.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'
import {
    issue,
    type OutputPlanReport,
    type ProjectValidationReport,
    type ValidationIssue,
} from './validation-report.js'
import { validateProjectManifest } from './validate-project.js'
import { outputPlanDiagnosticReport, validateOutputPlan } from './validate-output-plan.js'

/**
 * Selecao pura entre o allowlist do projeto e o catalogo de perfis (§7).
 *
 * Esta camada e a unica que escreve um OutputPlan, e o faz **lendo o catalogo**:
 * nao existe segundo dicionario de formatos por rede ou por marca, e o plano
 * nunca e reconstruido a partir dos campos ecoados de um relatorio. Um pedido
 * resolve **um** plano; nao ha expansao automatica de variacoes.
 */

/** Filtros de leitura do catalogo mais o contexto das regras (§2.1.1). */
export interface OutputPlanResolutionOptions {
    readonly network?: OutputNetwork
    readonly publication?: OutputPublication
    readonly mediaKind?: OutputMediaKind
    /** Ausente = contexto nao informado. `null` ou valor fora do enum e entrada invalida. */
    readonly ruleContext?: RuleContext
}

/** O resolvedor devolve o plano canonico e o diagnostico; nunca so o relatorio. */
export interface OutputPlanResolution {
    readonly plan: OutputPlan | null
    readonly report: OutputPlanReport
}

const OPTION_FIELDS = ['network', 'publication', 'mediaKind', 'ruleContext'] as const

/** Estado da leitura das opcoes: `declared` separa "ausente" de "invalido". */
interface ReadOptions {
    network: OutputNetwork | null
    publication: OutputPublication | null
    mediaKind: OutputMediaKind | null
    ruleContext: RuleContext | null
    declaredNetwork: boolean
    declaredPublication: boolean
    declaredMediaKind: boolean
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isKebabCase(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function inEnum<T extends string>(value: unknown, values: readonly T[]): value is T {
    return typeof value === 'string' && (values as readonly string[]).includes(value)
}

/**
 * Allowlist de `outputProfiles` de um manifesto **valido**. Quando o manifesto
 * e invalido, `allowed` fica vazio: comparar allowlist contra documento
 * rejeitado seria derivar regra de entrada malformada.
 */
export function projectAllowedProfiles(projectInput: unknown): {
    allowed: readonly string[]
    report: ProjectValidationReport
} {
    const report = validateProjectManifest(projectInput)
    if (!report.valid || !isPlainObject(projectInput)) {
        return { allowed: [], report }
    }
    const profiles = projectInput.outputProfiles
    const allowed = Array.isArray(profiles)
        ? profiles.filter((item): item is string => typeof item === 'string')
        : []
    return { allowed, report }
}

/**
 * Resolve **um** OutputPlan a partir do catalogo. Nunca lanca: todo motivo de
 * falha vira codigo estavel no relatorio, com `plan: null`.
 */
export function resolveOutputPlan(
    projectInput: unknown,
    profileIdInput: unknown,
    optionsInput?: OutputPlanResolutionOptions,
): OutputPlanResolution {
    const errors: ValidationIssue[] = []

    const { allowed, report: projectReport } = projectAllowedProfiles(projectInput)
    const projectId = projectReport.valid ? projectReport.projectId : null

    if (!projectReport.valid) {
        errors.push(issue(
            'OUTPUT_PROJECT_INVALID',
            'project',
            `The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`,
        ))
    }

    const profileId = isKebabCase(profileIdInput) ? profileIdInput : null
    if (profileId === null) {
        errors.push(issue(
            'OUTPUT_PROFILE_ID_INVALID',
            'profileId',
            'profileId is required and must be a kebab-case string.',
        ))
    }

    const options = readOptions(optionsInput, errors)
    const profile: OutputProfile | null = profileId === null ? null : findOutputProfile(profileId)

    if (profileId !== null && profile === null) {
        errors.push(issue(
            'OUTPUT_PROFILE_UNKNOWN',
            'profileId',
            `profileId "${profileId}" does not exist in catalog version "${CATALOG_VERSION}".`,
        ))
    }

    if (profile !== null) {
        checkFilters(profile, options, errors)
        if (projectReport.valid && !allowed.includes(profile.id)) {
            errors.push(issue(
                'OUTPUT_PROFILE_NOT_ALLOWED',
                'profileId',
                `Profile "${profile.id}" is not listed in project "${String(projectId)}" outputProfiles.`,
            ))
        }
    }

    if (errors.length > 0) {
        return {
            plan: null,
            report: outputPlanDiagnosticReport({
                projectId,
                profileId,
                ruleContext: options.ruleContext,
                profile,
                errors,
            }),
        }
    }

    const resolved = profile as OutputProfile
    // Manifesto aceito pelo validador de projeto sempre traz `id` em kebab-case.
    const planProjectId = projectReport.projectId as string
    const plan = buildOutputPlan(resolved, planProjectId, options.ruleContext)
    const report = validateOutputPlan(plan, projectInput)

    // Um perfil cujo proprio preset viole uma regra oficial aplicavel nao pode
    // virar plano: o artefato e descartado e a causa fica no relatorio.
    return report.valid ? { plan, report } : { plan: null, report }
}

/** Monta o plano na ordem canonica de §6.1, com `ruleContext` so quando informado. */
function buildOutputPlan(
    profile: OutputProfile,
    projectId: string,
    ruleContext: RuleContext | null,
): OutputPlan {
    const context: { ruleContext?: RuleContext } = ruleContext === null ? {} : { ruleContext }
    const head = {
        schemaVersion: OUTPUT_PLAN_SCHEMA_VERSION,
        projectId,
        catalogVersion: CATALOG_VERSION,
        profileId: profile.id,
        profileRevision: profile.revision,
    } as const

    if (profile.mediaKind === 'image') {
        return {
            ...head,
            mediaKind: 'image',
            ...context,
            image: {
                width: profile.geometry.width,
                height: profile.geometry.height,
                aspectRatio: profile.geometry.aspectRatio,
            },
        }
    }

    return {
        ...head,
        mediaKind: 'video',
        ...context,
        video: {
            width: profile.geometry.width,
            height: profile.geometry.height,
            aspectRatio: profile.geometry.aspectRatio,
            fps: profile.fps,
        },
    }
}

/**
 * Le as opcoes como dado nao confiavel: a CLI recebe string do usuario, entao
 * valor fora do enum e `null` explicito viram erro, nunca filtro silencioso.
 */
function readOptions(
    optionsInput: OutputPlanResolutionOptions | undefined,
    errors: ValidationIssue[],
): ReadOptions {
    const options: ReadOptions = {
        network: null,
        publication: null,
        mediaKind: null,
        ruleContext: null,
        declaredNetwork: false,
        declaredPublication: false,
        declaredMediaKind: false,
    }

    if (optionsInput === undefined) return options

    if (!isPlainObject(optionsInput)) {
        errors.push(issue(
            'OUTPUT_PROFILE_FILTER_INVALID',
            'options',
            'Resolution options, when present, must be a JSON object.',
        ))
        return options
    }

    const record: Record<string, unknown> = optionsInput

    for (const key of Object.keys(record)) {
        if (!(OPTION_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'OUTPUT_PROFILE_FILTER_INVALID',
                `options.${key}`,
                `Unknown resolution option "${key}"; allowed options are ${OPTION_FIELDS.map((field) => `"${field}"`).join(', ')}.`,
            ))
        }
    }

    if (record.network !== undefined) {
        options.declaredNetwork = true
        if (inEnum(record.network, OUTPUT_NETWORKS)) {
            options.network = record.network
        } else {
            errors.push(invalidFilterIssue('network', OUTPUT_NETWORKS))
        }
    }

    if (record.publication !== undefined) {
        options.declaredPublication = true
        if (inEnum(record.publication, OUTPUT_PUBLICATIONS)) {
            options.publication = record.publication
        } else {
            errors.push(invalidFilterIssue('publication', OUTPUT_PUBLICATIONS))
        }
    }

    if (record.mediaKind !== undefined) {
        options.declaredMediaKind = true
        if (inEnum(record.mediaKind, OUTPUT_MEDIA_KINDS)) {
            options.mediaKind = record.mediaKind
        } else {
            errors.push(invalidFilterIssue('mediaKind', OUTPUT_MEDIA_KINDS))
        }
    }

    if ('ruleContext' in record) {
        if (inEnum(record.ruleContext, RULE_CONTEXTS)) {
            options.ruleContext = record.ruleContext
        } else {
            errors.push(issue(
                'OUTPUT_PLAN_RULE_CONTEXT_INVALID',
                'options.ruleContext',
                `ruleContext, when present, must be one of ${RULE_CONTEXTS.map((value) => `"${value}"`).join(', ')}; absence is an omitted key, never null.`,
            ))
        }
    }

    return options
}

function invalidFilterIssue(field: string, values: readonly string[]): ValidationIssue {
    return issue(
        'OUTPUT_PROFILE_FILTER_INVALID',
        `options.${field}`,
        `${field} must be one of ${values.map((value) => `"${value}"`).join(', ')}.`,
    )
}

/**
 * Coerencia entre o filtro declarado e o perfil escolhido. O codigo e o mesmo
 * para "contradiz o perfil" e para "nenhum perfil casa": nos dois casos a
 * selecao e ambigua, e a mensagem diz quantos perfis os filtros deixariam.
 */
function checkFilters(profile: OutputProfile, options: ReadOptions, errors: ValidationIssue[]): void {
    const checks = [
        { field: 'network' as const, declared: options.declaredNetwork, value: options.network, expected: profile.network },
        { field: 'publication' as const, declared: options.declaredPublication, value: options.publication, expected: profile.publication },
        { field: 'mediaKind' as const, declared: options.declaredMediaKind, value: options.mediaKind, expected: profile.mediaKind },
    ]

    for (const check of checks) {
        if (!check.declared || check.value === null || check.value === check.expected) continue
        const matching = listOutputProfiles({
            network: options.network ?? undefined,
            publication: options.publication ?? undefined,
            mediaKind: options.mediaKind ?? undefined,
        }).length
        errors.push(issue(
            'OUTPUT_PROFILE_AMBIGUOUS_SELECTION',
            `options.${check.field}`,
            `profile "${profile.id}" has ${check.field} "${check.expected}", but the filter declares "${String(check.value)}"; ${matching} catalog profile(s) match the declared filters.`,
        ))
    }
}
