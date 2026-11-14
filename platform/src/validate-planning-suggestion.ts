/**
 * Validador puro de PlanningSuggestion v1 ('briefing' e 'creative').
 *
 * Garante estrutura fechada, campos obrigatorios, limites de duracao,
 * referencias internas (selectedHookId -> hookOptions, motionSuggestions ->
 * videoScenes sem slow-zoom) e compatibilidade opcional com ProjectManifest +
 * catalogo oficial de perfis.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import type { BeatNarrativeFunction } from './beat-plan-contract.js'
import { findOutputProfile } from './output-profiles/catalog.js'
import { projectAllowedProfiles } from './resolve-output-profile.js'
import {
    BRIEFING_SUGGESTION_REQUIRED_FIELDS,
    BRIEFING_SUGGESTION_TOP_LEVEL_FIELDS,
    CREATIVE_SUGGESTION_REQUIRED_FIELDS,
    CREATIVE_SUGGESTION_TOP_LEVEL_FIELDS,
    KEBAB_CASE_PATTERN,
    PLANNING_CAROUSEL_CARD_FIELDS,
    PLANNING_CAROUSEL_CARD_REQUIRED_FIELDS,
    PLANNING_CAROUSEL_ROLES,
    PLANNING_CHANNEL_COPY_FIELDS,
    PLANNING_CHANNEL_COPY_REQUIRED_FIELDS,
    PLANNING_CLAIM_FIELDS,
    PLANNING_CLAIM_REQUIRED_FIELDS,
    PLANNING_CLAIM_STATUSES,
    PLANNING_HOOK_OPTION_FIELDS,
    PLANNING_HOOK_OPTION_REQUIRED_FIELDS,
    PLANNING_MOTION_SUGGESTION_FIELDS,
    PLANNING_MOTION_SUGGESTION_REQUIRED_FIELDS,
    PLANNING_NARRATIVE_FUNCTIONS,
    PLANNING_QUESTION_DIMENSIONS,
    PLANNING_QUESTION_FIELDS,
    PLANNING_QUESTION_REQUIRED_FIELDS,
    PLANNING_SCENE_DURATION_MAX_MS,
    PLANNING_SCENE_DURATION_MIN_MS,
    PLANNING_SCENE_MOTION_INTENTS,
    PLANNING_SUGGESTION_COLOR_PATTERN,
    PLANNING_SUGGESTION_SCHEMA_VERSION,
    PLANNING_VIDEO_SCENE_FIELDS,
    PLANNING_VIDEO_SCENE_REQUIRED_FIELDS,
    type BriefingStageSuggestion,
    type CreativeStageSuggestion,
    type PlanningCarouselCard,
    type PlanningCarouselRole,
    type PlanningChannelCopy,
    type PlanningClaim,
    type PlanningClaimStatus,
    type PlanningHookOption,
    type PlanningMotionSuggestion,
    type PlanningQuestion,
    type PlanningQuestionDimension,
    type PlanningSceneMotionIntent,
    type PlanningSuggestionFailureCode,
    type PlanningSuggestionValidationResult,
    type PlanningVideoScene,
} from './planning-suggestion-contract.js'

type ValidationError = {
    readonly ok: false
    readonly failureCode: PlanningSuggestionFailureCode
    readonly subject: string | null
    readonly message: string
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isString(value: unknown): value is string {
    return typeof value === 'string'
}

function isKebabCase(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function isNonNegativeInt(value: unknown): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value >= 0
}

function findUnknownField(obj: Record<string, unknown>, allowed: readonly string[]): string | null {
    return Object.keys(obj).find((k) => !allowed.includes(k)) ?? null
}

function findMissingField(obj: Record<string, unknown>, required: readonly string[]): string | null {
    return required.find((k) => obj[k] === undefined) ?? null
}

function fail(
    failureCode: PlanningSuggestionFailureCode,
    subject: string | null,
    message: string,
): ValidationError {
    return { ok: false, failureCode, subject, message }
}

function validateAllowedProfiles(
    profileIds: readonly string[],
    projectInput: unknown,
    subjectPrefix: string,
): ValidationError | null {
    if (projectInput === undefined) return null
    const { allowed, report } = projectAllowedProfiles(projectInput)
    if (!report.valid) {
        return fail('PLANNING_PROFILE_NOT_ALLOWED', 'project', 'ProjectManifest invalido para validar perfis permitidos.')
    }
    for (const pid of profileIds) {
        if (!findOutputProfile(pid)) {
            return fail(
                'PLANNING_PROFILE_NOT_ALLOWED',
                `${subjectPrefix}.${pid}`,
                `Perfil "${pid}" nao existe no catalogo oficial de formatos.`,
            )
        }
        if (!allowed.includes(pid)) {
            return fail(
                'PLANNING_PROFILE_NOT_ALLOWED',
                `${subjectPrefix}.${pid}`,
                `Perfil "${pid}" nao e permitido pela allowlist do projeto (${allowed.join(', ')}).`,
            )
        }
    }
    return null
}

function parseQuestion(
    raw: unknown,
    index: number,
    seenIds: Set<string>,
): { ok: true; value: PlanningQuestion } | ValidationError {
    const subj = `questions[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_QUESTION_INVALID', subj, `Pergunta ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_QUESTION_FIELDS)
    if (unknown) return fail('PLANNING_QUESTION_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_QUESTION_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_QUESTION_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.id)) return fail('PLANNING_QUESTION_INVALID', `${subj}.id`, `ID da pergunta em ${subj} deve usar kebab-case.`)
    if (seenIds.has(raw.id)) return fail('PLANNING_QUESTION_ID_DUPLICATE', raw.id, `ID de pergunta duplicado: "${raw.id}".`)
    if (typeof raw.dimension !== 'string' || !(PLANNING_QUESTION_DIMENSIONS as readonly string[]).includes(raw.dimension)) {
        return fail('PLANNING_QUESTION_INVALID', `${subj}.dimension`, `Dimensao invalida em ${subj}: use uma entre ${PLANNING_QUESTION_DIMENSIONS.join(', ')}.`)
    }
    if (!isNonEmptyString(raw.question)) {
        return fail('PLANNING_QUESTION_INVALID', `${subj}.question`, `Texto da pergunta em ${subj} nao pode ser vazio.`)
    }
    if (raw.suggestedAnswer !== undefined && !isString(raw.suggestedAnswer)) {
        return fail('PLANNING_QUESTION_INVALID', `${subj}.suggestedAnswer`, `suggestedAnswer em ${subj} deve ser texto.`)
    }
    seenIds.add(raw.id)
    return {
        ok: true,
        value: {
            id: raw.id,
            dimension: raw.dimension as PlanningQuestionDimension,
            question: raw.question,
            ...(raw.suggestedAnswer !== undefined ? { suggestedAnswer: raw.suggestedAnswer } : {}),
        },
    }
}

function parseClaim(
    raw: unknown,
    index: number,
    seenIds: Set<string>,
): { ok: true; value: PlanningClaim } | ValidationError {
    const subj = `claims[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_CLAIM_INVALID', subj, `Afirmacao ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_CLAIM_FIELDS)
    if (unknown) return fail('PLANNING_CLAIM_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_CLAIM_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_CLAIM_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.id)) return fail('PLANNING_CLAIM_INVALID', `${subj}.id`, `ID da afirmacao em ${subj} deve usar kebab-case.`)
    if (seenIds.has(raw.id)) return fail('PLANNING_CLAIM_ID_DUPLICATE', raw.id, `ID de afirmacao duplicado: "${raw.id}".`)
    if (!isNonEmptyString(raw.statement)) {
        return fail('PLANNING_CLAIM_INVALID', `${subj}.statement`, `Texto da afirmacao em ${subj} nao pode ser vazio.`)
    }
    if (typeof raw.status !== 'string' || !(PLANNING_CLAIM_STATUSES as readonly string[]).includes(raw.status)) {
        return fail('PLANNING_CLAIM_INVALID', `${subj}.status`, `Status de afirmacao invalido em ${subj}: use confirmed, hypothesis ou pending_validation.`)
    }
    if (typeof raw.requiresConfirmation !== 'boolean') {
        return fail('PLANNING_CLAIM_INVALID', `${subj}.requiresConfirmation`, `requiresConfirmation em ${subj} deve ser booleano (true/false).`)
    }
    if (raw.evidenceMediaId !== undefined && !isKebabCase(raw.evidenceMediaId)) {
        return fail('PLANNING_CLAIM_INVALID', `${subj}.evidenceMediaId`, `evidenceMediaId em ${subj} deve usar kebab-case.`)
    }
    if (raw.warning !== undefined && !isNonEmptyString(raw.warning)) {
        return fail('PLANNING_CLAIM_INVALID', `${subj}.warning`, `warning em ${subj} nao pode ser vazio quando informado.`)
    }
    seenIds.add(raw.id)
    return {
        ok: true,
        value: {
            id: raw.id,
            statement: raw.statement,
            status: raw.status as PlanningClaimStatus,
            requiresConfirmation: raw.requiresConfirmation,
            ...(raw.evidenceMediaId !== undefined ? { evidenceMediaId: raw.evidenceMediaId } : {}),
            ...(raw.warning !== undefined ? { warning: raw.warning } : {}),
        },
    }
}

function validateBriefingStage(input: Record<string, unknown>, projectInput?: unknown): PlanningSuggestionValidationResult {
    const unknown = findUnknownField(input, BRIEFING_SUGGESTION_TOP_LEVEL_FIELDS)
    if (unknown) {
        return fail('PLANNING_SUGGESTION_UNKNOWN_FIELD', unknown, `Campo desconhecido "${unknown}" na etapa briefing.`)
    }
    const missing = findMissingField(input, BRIEFING_SUGGESTION_REQUIRED_FIELDS)
    if (missing) {
        return fail('PLANNING_SUGGESTION_FIELD_INVALID', missing, `Campo obrigatorio "${missing}" ausente na sugestao de briefing.`)
    }

    const strFields = ['product', 'objective', 'audience', 'coreMessage', 'supportEvidence', 'cta', 'tone'] as const
    for (const field of strFields) {
        if (!isString(input[field])) {
            return fail('PLANNING_SUGGESTION_FIELD_INVALID', field, `Campo "${field}" deve ser texto (string).`)
        }
    }

    if (!Array.isArray(input.recommendedProfiles) || input.recommendedProfiles.length === 0) {
        return fail('PLANNING_SUGGESTION_FIELD_INVALID', 'recommendedProfiles', 'recommendedProfiles deve listar ao menos 1 perfil de saida permitido.')
    }
    const recommendedProfiles: string[] = []
    for (let i = 0; i < input.recommendedProfiles.length; i++) {
        const pid = input.recommendedProfiles[i]
        if (!isKebabCase(pid)) {
            return fail('PLANNING_SUGGESTION_FIELD_INVALID', `recommendedProfiles[${i}]`, 'Cada perfil recomendado deve usar kebab-case.')
        }
        if (recommendedProfiles.includes(pid)) {
            return fail('PLANNING_SUGGESTION_FIELD_INVALID', pid, `Perfil recomendado duplicado: "${pid}".`)
        }
        recommendedProfiles.push(pid)
    }

    const profileErr = validateAllowedProfiles(recommendedProfiles, projectInput, 'recommendedProfiles')
    if (profileErr) return profileErr

    if (!Array.isArray(input.gaps) || !input.gaps.every(isNonEmptyString)) {
        return fail('PLANNING_SUGGESTION_FIELD_INVALID', 'gaps', 'gaps deve ser uma lista de textos nao vazios.')
    }

    if (!Array.isArray(input.questions)) {
        return fail('PLANNING_QUESTION_INVALID', 'questions', 'questions deve ser uma lista de perguntas.')
    }
    const questions: PlanningQuestion[] = []
    const seenQ = new Set<string>()
    for (let i = 0; i < input.questions.length; i++) {
        const parsed = parseQuestion(input.questions[i], i, seenQ)
        if (!parsed.ok) return parsed
        questions.push(parsed.value)
    }

    if (!Array.isArray(input.claims)) {
        return fail('PLANNING_CLAIM_INVALID', 'claims', 'claims deve ser uma lista de afirmacoes.')
    }
    const claims: PlanningClaim[] = []
    const seenC = new Set<string>()
    for (let i = 0; i < input.claims.length; i++) {
        const parsed = parseClaim(input.claims[i], i, seenC)
        if (!parsed.ok) return parsed
        claims.push(parsed.value)
    }

    const suggestion: BriefingStageSuggestion = {
        schemaVersion: 1,
        stage: 'briefing',
        product: input.product as string,
        objective: input.objective as string,
        audience: input.audience as string,
        coreMessage: input.coreMessage as string,
        supportEvidence: input.supportEvidence as string,
        cta: input.cta as string,
        tone: input.tone as string,
        recommendedProfiles,
        gaps: input.gaps,
        questions,
        claims,
    }
    return { ok: true, suggestion }
}

function parseHookOption(
    raw: unknown,
    index: number,
    seenIds: Set<string>,
): { ok: true; value: PlanningHookOption } | ValidationError {
    const subj = `hookOptions[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_HOOK_INVALID', subj, `Hook ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_HOOK_OPTION_FIELDS)
    if (unknown) return fail('PLANNING_HOOK_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_HOOK_OPTION_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_HOOK_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.id)) return fail('PLANNING_HOOK_INVALID', `${subj}.id`, `ID do hook em ${subj} deve usar kebab-case.`)
    if (seenIds.has(raw.id)) return fail('PLANNING_HOOK_ID_DUPLICATE', raw.id, `ID de hook duplicado: "${raw.id}".`)
    if (!isNonEmptyString(raw.text)) return fail('PLANNING_HOOK_INVALID', `${subj}.text`, `Texto do hook em ${subj} nao pode ser vazio.`)
    if (raw.angle !== undefined && !isNonEmptyString(raw.angle)) {
        return fail('PLANNING_HOOK_INVALID', `${subj}.angle`, `angle em ${subj} nao pode ser vazio quando informado.`)
    }
    seenIds.add(raw.id)
    return {
        ok: true,
        value: {
            id: raw.id,
            text: raw.text,
            ...(raw.angle !== undefined ? { angle: raw.angle } : {}),
        },
    }
}

function parseVideoScene(
    raw: unknown,
    index: number,
    seenIds: Set<string>,
): { ok: true; value: PlanningVideoScene } | ValidationError {
    const subj = `videoScenes[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_SCENE_INVALID', subj, `Cena ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_VIDEO_SCENE_FIELDS)
    if (unknown) return fail('PLANNING_SCENE_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_VIDEO_SCENE_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_SCENE_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.id)) return fail('PLANNING_SCENE_INVALID', `${subj}.id`, `ID da cena em ${subj} deve usar kebab-case.`)
    if (seenIds.has(raw.id)) return fail('PLANNING_SCENE_ID_DUPLICATE', raw.id, `ID de cena duplicado: "${raw.id}".`)
    if (!isNonEmptyString(raw.objective)) return fail('PLANNING_SCENE_INVALID', `${subj}.objective`, `Objetivo da cena ${subj} nao pode ser vazio.`)
    if (typeof raw.narrativeFunction !== 'string' || !(PLANNING_NARRATIVE_FUNCTIONS as readonly string[]).includes(raw.narrativeFunction)) {
        return fail('PLANNING_SCENE_INVALID', `${subj}.narrativeFunction`, `narrativeFunction invalida em ${subj}.`)
    }
    if (typeof raw.durationMs !== 'number' || !Number.isInteger(raw.durationMs)
        || raw.durationMs < PLANNING_SCENE_DURATION_MIN_MS || raw.durationMs > PLANNING_SCENE_DURATION_MAX_MS) {
        return fail('PLANNING_SCENE_INVALID', `${subj}.durationMs`, `durationMs em ${subj} deve ser inteiro entre ${PLANNING_SCENE_DURATION_MIN_MS} e ${PLANNING_SCENE_DURATION_MAX_MS}.`)
    }
    for (const f of ['titleOverlay', 'caption', 'narration', 'requiredMediaDescriptor'] as const) {
        if (!isNonEmptyString(raw[f])) {
            return fail('PLANNING_SCENE_INVALID', `${subj}.${f}`, `Campo "${f}" em ${subj} nao pode ser vazio.`)
        }
    }
    if (raw.mediaId !== undefined && !isKebabCase(raw.mediaId)) {
        return fail('PLANNING_SCENE_INVALID', `${subj}.mediaId`, `mediaId em ${subj} deve usar kebab-case.`)
    }
    if (raw.motionIntent !== undefined && (typeof raw.motionIntent !== 'string' || !(PLANNING_SCENE_MOTION_INTENTS as readonly string[]).includes(raw.motionIntent))) {
        return fail('PLANNING_SCENE_INVALID', `${subj}.motionIntent`, `motionIntent invalido em ${subj}: use none ou slow-zoom.`)
    }
    seenIds.add(raw.id)
    return {
        ok: true,
        value: {
            id: raw.id,
            objective: raw.objective,
            narrativeFunction: raw.narrativeFunction as BeatNarrativeFunction,
            durationMs: raw.durationMs,
            titleOverlay: raw.titleOverlay as string,
            caption: raw.caption as string,
            narration: raw.narration as string,
            requiredMediaDescriptor: raw.requiredMediaDescriptor as string,
            ...(raw.mediaId !== undefined ? { mediaId: raw.mediaId } : {}),
            ...(raw.motionIntent !== undefined ? { motionIntent: raw.motionIntent as PlanningSceneMotionIntent } : {}),
        },
    }
}

function parseCarouselCard(
    raw: unknown,
    index: number,
    seenIds: Set<string>,
): { ok: true; value: PlanningCarouselCard } | ValidationError {
    const subj = `carouselCards[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_CARD_INVALID', subj, `Card ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_CAROUSEL_CARD_FIELDS)
    if (unknown) return fail('PLANNING_CARD_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_CAROUSEL_CARD_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_CARD_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.id)) return fail('PLANNING_CARD_INVALID', `${subj}.id`, `ID do card em ${subj} deve usar kebab-case.`)
    if (seenIds.has(raw.id)) return fail('PLANNING_CARD_ID_DUPLICATE', raw.id, `ID de card duplicado: "${raw.id}".`)
    if (typeof raw.role !== 'string' || !(PLANNING_CAROUSEL_ROLES as readonly string[]).includes(raw.role)) {
        return fail('PLANNING_CARD_INVALID', `${subj}.role`, `Papel (role) do card em ${subj} deve ser cover, content ou cta.`)
    }
    if (!isNonEmptyString(raw.title)) return fail('PLANNING_CARD_INVALID', `${subj}.title`, `Titulo do card ${subj} nao pode ser vazio.`)
    if (raw.body !== undefined && !isString(raw.body)) {
        return fail('PLANNING_CARD_INVALID', `${subj}.body`, `Corpo do card ${subj} deve ser texto.`)
    }
    if (raw.requiredMediaDescriptor !== undefined && !isString(raw.requiredMediaDescriptor)) {
        return fail('PLANNING_CARD_INVALID', `${subj}.requiredMediaDescriptor`, `requiredMediaDescriptor em ${subj} deve ser texto.`)
    }
    if (raw.mediaId !== undefined && !isKebabCase(raw.mediaId)) {
        return fail('PLANNING_CARD_INVALID', `${subj}.mediaId`, `mediaId em ${subj} deve usar kebab-case.`)
    }
    seenIds.add(raw.id)
    return {
        ok: true,
        value: {
            id: raw.id,
            role: raw.role as PlanningCarouselRole,
            title: raw.title,
            ...(raw.body !== undefined ? { body: raw.body } : {}),
            ...(raw.requiredMediaDescriptor !== undefined ? { requiredMediaDescriptor: raw.requiredMediaDescriptor } : {}),
            ...(raw.mediaId !== undefined ? { mediaId: raw.mediaId } : {}),
        },
    }
}

function parseChannelCopy(
    raw: unknown,
    index: number,
    seenProfiles: Set<string>,
): { ok: true; value: PlanningChannelCopy } | ValidationError {
    const subj = `channelCopies[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_CHANNEL_COPY_INVALID', subj, `Texto de canal ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_CHANNEL_COPY_FIELDS)
    if (unknown) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_CHANNEL_COPY_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.profileId)) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.profileId`, `profileId em ${subj} deve usar kebab-case.`)
    if (seenProfiles.has(raw.profileId)) return fail('PLANNING_CHANNEL_COPY_DUPLICATE', raw.profileId, `Texto duplicado para o perfil "${raw.profileId}".`)
    if (!isString(raw.title)) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.title`, `title em ${subj} deve ser texto.`)
    if (!isNonEmptyString(raw.postText)) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.postText`, `postText em ${subj} nao pode ser vazio.`)
    if (!isNonEmptyString(raw.cta)) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.cta`, `cta em ${subj} nao pode ser vazio.`)
    if (!isString(raw.destinationUrl)) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.destinationUrl`, `destinationUrl em ${subj} deve ser texto.`)
    if (!isString(raw.hashtags)) return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.hashtags`, `hashtags em ${subj} deve ser texto.`)
    if (raw.flags !== undefined && (!Array.isArray(raw.flags) || !raw.flags.every(isNonEmptyString))) {
        return fail('PLANNING_CHANNEL_COPY_INVALID', `${subj}.flags`, `flags em ${subj} deve ser uma lista de alertas nao vazios.`)
    }
    seenProfiles.add(raw.profileId)
    return {
        ok: true,
        value: {
            profileId: raw.profileId,
            title: raw.title,
            postText: raw.postText,
            cta: raw.cta,
            destinationUrl: raw.destinationUrl,
            hashtags: raw.hashtags,
            ...(raw.flags !== undefined ? { flags: raw.flags } : {}),
        },
    }
}

function parseMotionSuggestion(
    raw: unknown,
    index: number,
    scenesById: Map<string, PlanningVideoScene>,
): { ok: true; value: PlanningMotionSuggestion } | ValidationError {
    const subj = `motionSuggestions[${index}]`
    if (!isPlainObject(raw)) return fail('PLANNING_MOTION_SUGGESTION_INVALID', subj, `Sugestao de Motion ${index + 1} deve ser um objeto JSON.`)
    const unknown = findUnknownField(raw, PLANNING_MOTION_SUGGESTION_FIELDS)
    if (unknown) return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.${unknown}`, `Campo desconhecido "${unknown}" em ${subj}.`)
    const missing = findMissingField(raw, PLANNING_MOTION_SUGGESTION_REQUIRED_FIELDS)
    if (missing) return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.${missing}`, `Campo obrigatorio "${missing}" ausente em ${subj}.`)
    if (!isKebabCase(raw.sceneId)) return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.sceneId`, `sceneId em ${subj} deve usar kebab-case.`)
    const scene = scenesById.get(raw.sceneId)
    if (!scene) {
        return fail('PLANNING_MOTION_SCENE_UNKNOWN', raw.sceneId, `Sugestao de Motion referencia cena inexistente "${raw.sceneId}".`)
    }
    if ((scene.motionIntent ?? 'none') !== 'none') {
        return fail('PLANNING_MOTION_SCENE_MOVING', raw.sceneId, `Cena "${raw.sceneId}" usa "${scene.motionIntent}" e nao suporta contorno retangular no Motion.`)
    }
    if (!isNonEmptyString(raw.targetElement)) {
        return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.targetElement`, `targetElement em ${subj} nao pode ser vazio.`)
    }
    if (raw.suggestedColor !== undefined && (typeof raw.suggestedColor !== 'string' || !PLANNING_SUGGESTION_COLOR_PATTERN.test(raw.suggestedColor))) {
        return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.suggestedColor`, `suggestedColor em ${subj} deve usar formato #RRGGBB.`)
    }
    if (raw.suggestedStartMs !== undefined && !isNonNegativeInt(raw.suggestedStartMs)) {
        return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.suggestedStartMs`, `suggestedStartMs em ${subj} deve ser inteiro >= 0.`)
    }
    if (raw.suggestedEndMs !== undefined && (!isNonNegativeInt(raw.suggestedEndMs) || raw.suggestedEndMs < 1)) {
        return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.suggestedEndMs`, `suggestedEndMs em ${subj} deve ser inteiro >= 1.`)
    }
    if (raw.suggestedStartMs !== undefined && raw.suggestedEndMs !== undefined && raw.suggestedEndMs <= raw.suggestedStartMs) {
        return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.suggestedEndMs`, `suggestedEndMs deve ser maior que suggestedStartMs em ${subj}.`)
    }
    if (raw.note !== undefined && !isNonEmptyString(raw.note)) {
        return fail('PLANNING_MOTION_SUGGESTION_INVALID', `${subj}.note`, `note em ${subj} nao pode ser vazio quando informado.`)
    }
    return {
        ok: true,
        value: {
            sceneId: raw.sceneId,
            targetElement: raw.targetElement,
            ...(raw.suggestedColor !== undefined ? { suggestedColor: raw.suggestedColor } : {}),
            ...(raw.suggestedStartMs !== undefined ? { suggestedStartMs: raw.suggestedStartMs } : {}),
            ...(raw.suggestedEndMs !== undefined ? { suggestedEndMs: raw.suggestedEndMs } : {}),
            ...(raw.note !== undefined ? { note: raw.note } : {}),
        },
    }
}

function validateCreativeStage(input: Record<string, unknown>, projectInput?: unknown): PlanningSuggestionValidationResult {
    const unknown = findUnknownField(input, CREATIVE_SUGGESTION_TOP_LEVEL_FIELDS)
    if (unknown) {
        return fail('PLANNING_SUGGESTION_UNKNOWN_FIELD', unknown, `Campo desconhecido "${unknown}" na etapa creative.`)
    }
    const missing = findMissingField(input, CREATIVE_SUGGESTION_REQUIRED_FIELDS)
    if (missing) {
        return fail('PLANNING_SUGGESTION_FIELD_INVALID', missing, `Campo obrigatorio "${missing}" ausente na sugestao de roteiro/cards.`)
    }

    if (!Array.isArray(input.hookOptions) || input.hookOptions.length === 0) {
        return fail('PLANNING_HOOK_INVALID', 'hookOptions', 'hookOptions deve conter ao menos 1 opcao de hook.')
    }
    const hookOptions: PlanningHookOption[] = []
    const seenHooks = new Set<string>()
    for (let i = 0; i < input.hookOptions.length; i++) {
        const parsed = parseHookOption(input.hookOptions[i], i, seenHooks)
        if (!parsed.ok) return parsed
        hookOptions.push(parsed.value)
    }

    let selectedHookId: string | undefined
    if (input.selectedHookId !== undefined) {
        if (!isKebabCase(input.selectedHookId)) {
            return fail('PLANNING_SELECTED_HOOK_UNKNOWN', 'selectedHookId', 'selectedHookId deve usar kebab-case.')
        }
        if (!seenHooks.has(input.selectedHookId)) {
            return fail('PLANNING_SELECTED_HOOK_UNKNOWN', input.selectedHookId, `selectedHookId "${input.selectedHookId}" nao existe em hookOptions.`)
        }
        selectedHookId = input.selectedHookId
    }

    if (!isNonEmptyString(input.scriptSummary)) {
        return fail('PLANNING_SUGGESTION_FIELD_INVALID', 'scriptSummary', 'scriptSummary nao pode ser vazio.')
    }

    if (!Array.isArray(input.videoScenes) || input.videoScenes.length === 0) {
        return fail('PLANNING_SCENE_INVALID', 'videoScenes', 'videoScenes deve conter ao menos 1 cena.')
    }
    const videoScenes: PlanningVideoScene[] = []
    const scenesById = new Map<string, PlanningVideoScene>()
    const seenScenes = new Set<string>()
    for (let i = 0; i < input.videoScenes.length; i++) {
        const parsed = parseVideoScene(input.videoScenes[i], i, seenScenes)
        if (!parsed.ok) return parsed
        videoScenes.push(parsed.value)
        scenesById.set(parsed.value.id, parsed.value)
    }

    if (!Array.isArray(input.carouselCards) || input.carouselCards.length < 2) {
        return fail('PLANNING_CARD_INVALID', 'carouselCards', 'carouselCards deve conter ao menos 2 cards (capa e fechamento/conteudo).')
    }
    const carouselCards: PlanningCarouselCard[] = []
    const seenCards = new Set<string>()
    for (let i = 0; i < input.carouselCards.length; i++) {
        const parsed = parseCarouselCard(input.carouselCards[i], i, seenCards)
        if (!parsed.ok) return parsed
        carouselCards.push(parsed.value)
    }

    if (!Array.isArray(input.channelCopies) || input.channelCopies.length === 0) {
        return fail('PLANNING_CHANNEL_COPY_INVALID', 'channelCopies', 'channelCopies deve conter ao menos 1 perfil de publicacao.')
    }
    const channelCopies: PlanningChannelCopy[] = []
    const seenProfiles = new Set<string>()
    for (let i = 0; i < input.channelCopies.length; i++) {
        const parsed = parseChannelCopy(input.channelCopies[i], i, seenProfiles)
        if (!parsed.ok) return parsed
        channelCopies.push(parsed.value)
    }

    const profileErr = validateAllowedProfiles(
        channelCopies.map((c) => c.profileId),
        projectInput,
        'channelCopies',
    )
    if (profileErr) return profileErr

    let motionSuggestions: PlanningMotionSuggestion[] | undefined
    if (input.motionSuggestions !== undefined) {
        if (!Array.isArray(input.motionSuggestions)) {
            return fail('PLANNING_MOTION_SUGGESTION_INVALID', 'motionSuggestions', 'motionSuggestions deve ser uma lista.')
        }
        motionSuggestions = []
        for (let i = 0; i < input.motionSuggestions.length; i++) {
            const parsed = parseMotionSuggestion(input.motionSuggestions[i], i, scenesById)
            if (!parsed.ok) return parsed
            motionSuggestions.push(parsed.value)
        }
    }

    const suggestion: CreativeStageSuggestion = {
        schemaVersion: 1,
        stage: 'creative',
        hookOptions,
        ...(selectedHookId !== undefined ? { selectedHookId } : {}),
        scriptSummary: input.scriptSummary,
        videoScenes,
        carouselCards,
        channelCopies,
        ...(motionSuggestions !== undefined ? { motionSuggestions } : {}),
    }
    return { ok: true, suggestion }
}

/**
 * Valida uma sugestao versionada de planejamento (`briefing` ou `creative`).
 * Quando `projectInput` e informado, verifica tambem que todos os perfis
 * sugeridos existem no catalogo e pertencem a allowlist do projeto.
 */
export function validatePlanningSuggestion(
    input: unknown,
    projectInput?: unknown,
): PlanningSuggestionValidationResult {
    if (!isPlainObject(input)) {
        return fail('PLANNING_SUGGESTION_INVALID', null, 'A sugestao deve ser um objeto JSON.')
    }
    if (input.schemaVersion !== PLANNING_SUGGESTION_SCHEMA_VERSION) {
        return fail('PLANNING_SUGGESTION_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion', 'schemaVersion deve ser igual a 1.')
    }
    if (input.stage === 'briefing') {
        return validateBriefingStage(input, projectInput)
    }
    if (input.stage === 'creative') {
        return validateCreativeStage(input, projectInput)
    }
    return fail('PLANNING_SUGGESTION_STAGE_INVALID', 'stage', 'stage deve ser "briefing" ou "creative".')
}
