/**
 * CLI de resolucao do OutputPlan canonico (`content:plan-output`).
 *
 * Uso:
 *   node dist/src/output-plan-cli.js --project <caminho> --profile <id>
 *       [--network <rede>] [--publication <destino>] [--media <tipo>]
 *       [--rule-context <contexto>] [--composition <caminho>] [--json]
 *
 * Exit codes:
 *   0 — plano resolvido e, se a composicao foi informada, compativel;
 *   1 — JSON legivel com plano, selecao ou compatibilidade invalidos;
 *   2 — erro de uso, arquivo ausente ou JSON malformado.
 *
 * Em `--json` o stdout e **exatamente** `resolution.plan`, com indentacao de dois
 * espacos e newline final: o artefato pode ser relido pelo schema e pelo
 * validador sem nenhuma edicao. Todo resto — avisos, codigos, caminhos, causas,
 * pendencias e itens de `requiresInspection` — sai em stderr, inclusive no
 * sucesso, porque "o que ainda nao pode ser certificado" nao e erro. Na falha o
 * stdout fica vazio. A verificacao opcional de Composition acontece **antes** de
 * emitir o plano, para nunca imprimir um plano recem-resolvido cuja composicao ja
 * se sabe que nao casa com ele.
 */

import {
    EXIT_INVALID,
    EXIT_USAGE,
    EXIT_VALID,
    formatIssue,
    parseFlags,
    readFilters,
    readJsonFile,
    type CliFilters,
} from './cli-input.js'
import type { OutputPlan } from './output-plan-contract.js'
import { findOutputProfile } from './output-profiles/catalog.js'
import {
    resolveOutputPlan,
    type OutputPlanResolutionOptions,
} from './resolve-output-profile.js'
import { validateCompositionForOutputPlan } from './validate-composition-output.js'
import type { OutputCompatibilityReport, OutputPlanReport, ValidationIssue } from './validation-report.js'

const VALUE_FLAGS = [
    '--project',
    '--profile',
    '--network',
    '--publication',
    '--media',
    '--rule-context',
    '--composition',
] as const

const USAGE = 'Uso: npm run content:plan-output -- --project <caminho> --profile <id> [--network <rede>] [--publication <destino>] [--media <tipo>] [--rule-context <contexto>] [--composition <caminho>] [--json]'

/** Camada de onde o diagnostico veio: distingue a duracao ausente no plano da declarada na composicao. */
type Layer = 'plano' | 'composicao' | 'compatibilidade'

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
}

/** So as chaves realmente informadas: `ruleContext: undefined` nao e "ausente", e entrada invalida. */
function resolutionOptions(filters: CliFilters): OutputPlanResolutionOptions {
    const options: Record<string, unknown> = {}
    if (filters.network !== null) options.network = filters.network
    if (filters.publication !== null) options.publication = filters.publication
    if (filters.mediaKind !== null) options.mediaKind = filters.mediaKind
    if (filters.ruleContext !== null) options.ruleContext = filters.ruleContext
    return options as OutputPlanResolutionOptions
}

function pushLayer(lines: string[], layer: Layer, kind: 'Erros' | 'Avisos', items: readonly ValidationIssue[]): void {
    if (items.length === 0) return
    lines.push(`${kind} (camada ${layer}):`)
    for (const item of items) {
        lines.push(formatIssue(item))
    }
}

function compatLine(compat: OutputCompatibilityReport): string {
    return compat.valid
        ? `compatibilidade: composicao "${String(compat.compositionId)}" compativel`
        : `compatibilidade: composicao "${String(compat.compositionId)}" incompativel (${compat.errors.length} erro(s))`
}

/** O que ainda nao pode ser certificado: sempre mostrado, inclusive no sucesso. */
function statusLines(report: OutputPlanReport, compat: OutputCompatibilityReport | null): string[] {
    const lines: string[] = [
        `pendencias de fonte: ${report.pendingRuleIds.length > 0 ? report.pendingRuleIds.join(', ') : '(nenhuma)'}`,
        `requer inspecao: ${report.requiresInspection.length > 0 ? report.requiresInspection.join(', ') : '(nenhuma)'}`,
    ]
    if (compat !== null) lines.push(compatLine(compat))
    return lines
}

function renderHuman(plan: OutputPlan, report: OutputPlanReport, status: readonly string[]): string {
    const profile = findOutputProfile(plan.profileId)
    const geometry = report.geometry
    const lines: string[] = [
        `Plano de saida canonico — ${plan.profileId} — ${profile?.name ?? '(perfil sem nome no catalogo)'} (revisao ${plan.profileRevision})`,
        `  projeto: ${plan.projectId} | catalogo: v${plan.catalogVersion}`,
        geometry === null
            ? '  geometria: (nao resolvida)'
            : `  destino: ${profile?.network ?? 'desconhecido'}/${profile?.publication ?? 'desconhecido'} | midia: ${plan.mediaKind === 'image' ? 'imagem' : 'video'} | resolucao: ${geometry.width}x${geometry.height} (${geometry.aspectRatio}) | fps: ${report.fps ?? 'n/a'}`,
        `  contexto declarado: ${report.ruleContext ?? '(nao informado)'}`,
        `  capacidade de catalogo: ${profile?.exportState ?? '(perfil ausente no catalogo)'}`,
        ...status,
        '',
        'Plano canonico (JSON):',
        JSON.stringify(plan, null, 2),
    ]
    return lines.join('\n')
}

/** Diagnostico das tres camadas, sempre com o rotulo de origem. */
function diagnosticLines(report: OutputPlanReport, compat: OutputCompatibilityReport | null): string[] {
    const lines: string[] = []

    pushLayer(lines, 'plano', 'Erros', report.errors)
    pushLayer(lines, 'plano', 'Avisos', report.warnings)

    if (compat !== null) {
        pushLayer(lines, 'composicao', 'Erros', compat.compositionReport?.errors ?? [])
        pushLayer(lines, 'composicao', 'Avisos', compat.compositionReport?.warnings ?? [])
        pushLayer(lines, 'compatibilidade', 'Erros', compat.errors)
        pushLayer(lines, 'compatibilidade', 'Avisos', compat.warnings)
    }

    return lines
}

function main(argv: string[]): number {
    const parsed = parseFlags(argv, VALUE_FLAGS)
    if (parsed.error !== null) {
        usageError(parsed.error)
        return EXIT_USAGE
    }

    if (parsed.values.project === undefined || parsed.values.profile === undefined) {
        usageError('as flags --project e --profile sao obrigatorias')
        return EXIT_USAGE
    }

    const filters = readFilters(parsed.values, true)
    if ('error' in filters) {
        usageError(filters.error)
        return EXIT_USAGE
    }

    const projectFile = readJsonFile(parsed.values.project)
    if ('error' in projectFile) {
        console.error(projectFile.error)
        return EXIT_USAGE
    }

    let compositionInput: unknown = null
    if (parsed.values.composition !== undefined) {
        const compositionFile = readJsonFile(parsed.values.composition)
        if ('error' in compositionFile) {
            console.error(compositionFile.error)
            return EXIT_USAGE
        }
        compositionInput = compositionFile.value
    }

    const resolution = resolveOutputPlan(projectFile.value, parsed.values.profile, resolutionOptions(filters))
    const compat = resolution.plan === null || parsed.values.composition === undefined
        ? null
        : validateCompositionForOutputPlan(compositionInput, projectFile.value, resolution.plan)

    const plan = resolution.plan
    const compatible = compat === null || compat.valid

    const diagnostics = diagnosticLines(resolution.report, compat)
    const status = statusLines(resolution.report, compat)
    for (const line of diagnostics) {
        console.error(line)
    }

    if (plan === null || !compatible) {
        if (diagnostics.length > 0) console.error('')
        for (const line of status) {
            console.error(line)
        }
        return EXIT_INVALID
    }

    if (parsed.json) {
        for (const line of status) {
            console.error(line)
        }
        console.log(JSON.stringify(plan, null, 2))
        return EXIT_VALID
    }

    console.log(renderHuman(plan, resolution.report, status))
    return EXIT_VALID
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
