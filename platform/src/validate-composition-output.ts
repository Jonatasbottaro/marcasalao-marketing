import type { OutputPlan } from './output-plan-contract.js'
import type { OutputProfile, RuleContext } from './output-profiles/types.js'
import { findOutputProfile } from './output-profiles/catalog.js'
import {
    OUTPUT_COMPAT_VALID_SUMMARY,
    issue,
    outputCompatInvalidSummary,
    type CompositionValidationReport,
    type OutputCompatibilityReport,
    type OutputPlanReport,
    type ValidationIssue,
} from './validation-report.js'
import type { CompositionReportFormat } from './validation-report.js'
import { validateComposition } from './validate-composition.js'
import { assessProfileRules, readOutputPlan, validateOutputPlan } from './validate-output-plan.js'

/**
 * Compatibilidade entre uma Composition v1 e um OutputPlan do catalogo.
 *
 * Nenhuma regra de estrutura e reimplementada aqui: a Composition passa antes
 * por `validateComposition` e o plano por `validateOutputPlan`, e os dois
 * relatorios vao **por inteiro** no resultado para preservar a causa da falha.
 * Esta camada compara o artefato do plano (lido por `readOutputPlan`), nunca os
 * campos ecoados de um relatorio, e so compara quando as duas camadas
 * aceitaram os documentos. Codigo, peso, duracao efetiva de arquivo, existencia
 * de asset e faixas de audio seguem necessidade de inspecao: somar
 * `durationMs` de cena nao prova duracao de arquivo exportado.
 */

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Compara `composition.format` com o ramo de video do plano e avalia a duracao
 * declarada contra as regras de duracao do perfil no contexto declarado.
 *
 * Plano de imagem e rejeitado sem fabricar `fps`: a Composition descreve video
 * com frame rate, e inventar um valor para comparar seria criar dado ficticio.
 */
export function validateCompositionForOutputPlan(
    compositionInput: unknown,
    projectInput: unknown,
    planInput: unknown,
): OutputCompatibilityReport {
    const errors: ValidationIssue[] = []
    const warnings: ValidationIssue[] = []

    const compositionReport = validateComposition(compositionInput, projectInput)
    const planReport = validateOutputPlan(planInput, projectInput)
    const plan = readOutputPlan(planInput)

    const totalDurationMs = compositionReport.valid ? compositionReport.totalDurationMs : null

    if (!compositionReport.valid) {
        errors.push(issue(
            'OUTPUT_COMPAT_COMPOSITION_INVALID',
            'composition',
            `The Composition was rejected by the v1 validator: ${compositionReport.errors.length} error(s).`,
        ))
    }

    if (!planReport.valid || plan === null) {
        errors.push(issue(
            'OUTPUT_COMPAT_PLAN_INVALID',
            'plan',
            planReport.valid
                ? 'The output plan is not a readable OutputPlan artifact.'
                : `The output plan was rejected before comparison: ${planReport.errors.length} error(s).`,
        ))
    }

    if (errors.length > 0) {
        return finalize(
            errors,
            warnings,
            compositionReport.compositionId,
            planReport.profileId,
            planReport.ruleContext,
            totalDurationMs,
            compositionReport,
            planReport,
        )
    }

    const acceptedPlan = plan as OutputPlan
    const format = compositionReport.format as CompositionReportFormat

    if (acceptedPlan.mediaKind === 'image') {
        errors.push(issue(
            'OUTPUT_COMPAT_IMAGE_NO_COMPOSITION',
            'mediaKind',
            `Plan "${acceptedPlan.profileId}" is an image plan; composition-to-plan compatibility compares video plans and never fabricates fps.`,
        ))
        return finalize(
            errors,
            warnings,
            compositionReport.compositionId,
            planReport.profileId,
            planReport.ruleContext,
            totalDurationMs,
            compositionReport,
            planReport,
        )
    }

    const video = acceptedPlan.video
    const profile = findOutputProfile(acceptedPlan.profileId) as OutputProfile

    if (format.profile !== acceptedPlan.profileId) {
        errors.push(issue(
            'OUTPUT_COMPAT_PROFILE_MISMATCH',
            'format.profile',
            `composition.format.profile "${format.profile}" is not the plan profile "${acceptedPlan.profileId}".`,
        ))
    }

    if (format.width !== video.width || format.height !== video.height) {
        errors.push(issue(
            'OUTPUT_COMPAT_DIMENSIONS_MISMATCH',
            'format.width',
            `composition.format is ${format.width}x${format.height}, the plan preset is ${video.width}x${video.height}.`,
        ))
    }

    if (format.fps !== video.fps) {
        errors.push(issue(
            'OUTPUT_COMPAT_FPS_MISMATCH',
            'format.fps',
            `composition.format.fps ${format.fps} is not the plan preset fps ${video.fps}.`,
        ))
    }

    const assessment = assessProfileRules({
        profile,
        ruleContext: acceptedPlan.ruleContext ?? null,
        scope: 'composition-output',
        facts: { path: 'scenes', geometry: null, durationMs: totalDurationMs },
    })
    errors.push(...assessment.errors)
    warnings.push(...assessment.warnings)

    return finalize(
        errors,
        warnings,
        compositionReport.compositionId,
        planReport.profileId,
        planReport.ruleContext,
        totalDurationMs,
        compositionReport,
        planReport,
    )
}

function finalize(
    errors: ValidationIssue[],
    warnings: ValidationIssue[],
    compositionId: string | null,
    profileId: string | null,
    ruleContext: RuleContext | null,
    totalDurationMs: number | null,
    compositionReport: CompositionValidationReport,
    planReport: OutputPlanReport,
): OutputCompatibilityReport {
    return {
        valid: errors.length === 0,
        errors,
        warnings,
        summary: errors.length === 0 ? OUTPUT_COMPAT_VALID_SUMMARY : outputCompatInvalidSummary(errors.length),
        compositionId,
        profileId,
        ruleContext,
        totalDurationMs,
        compositionReport,
        planReport,
    }
}
