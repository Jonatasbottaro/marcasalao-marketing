/**
 * CLI de leitura do catalogo de perfis de saida (`content:profiles`).
 *
 * Uso:
 *   node dist/src/output-profiles-cli.js [--network <rede>] [--publication <destino>]
 *                                        [--media <tipo>] [--project <caminho>] [--json]
 *
 * Exit codes:
 *   0 — listagem produzida (com ou sem projeto; lista vazia e resultado valido);
 *   1 — o JSON do projeto e legivel, mas o manifesto foi rejeitado;
 *   2 — erro de uso, arquivo ausente ou JSON malformado.
 *
 * A CLI nao contem dicionario de formatos: a lista vem de `listOutputProfiles`,
 * o allowlist vem de `projectAllowedProfiles` (a mesma funcao do resolvedor) e os
 * codigos de bloqueio sao os codigos estaveis do contrato do plano. Sem projeto
 * a permissao e "ainda nao consultada", nunca "permitida". Nao acessa rede, nao
 * altera arquivos e nao le .env.
 */

import {
    EXIT_INVALID,
    EXIT_USAGE,
    EXIT_VALID,
    formatIssue,
    parseFlags,
    readFilters,
    readJsonFile,
} from './cli-input.js'
import { CATALOG_VERSION, listOutputProfiles } from './output-profiles/catalog.js'
import type { OutputProfile } from './output-profiles/types.js'
import { projectAllowedProfiles } from './resolve-output-profile.js'
import type { ProjectValidationReport, ValidationIssue } from './validation-report.js'

const VALUE_FLAGS = ['--network', '--publication', '--media', '--project'] as const
const USAGE = 'Uso: npm run content:profiles -- [--network <rede>] [--publication <destino>] [--media <tipo>] [--project <caminho>] [--json]'

/** Disponibilidade real de um perfil para o projeto informado. */
export type ProfileAvailability = 'allowed' | 'blocked' | 'not-consulted'

export interface ListedProfile {
    readonly id: string
    readonly name: string
    readonly revision: number
    readonly network: string
    readonly publication: string
    readonly mediaKind: string
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
    /** null em perfil de imagem: fps nunca e 0 nem inventado. */
    readonly fps: number | null
    /** Capacidade observada por preset; informacao de catalogo, nao promessa de exportacao. */
    readonly exportState: string
    readonly exportEvidence: readonly string[]
    readonly pendingRuleIds: readonly string[]
    readonly availability: ProfileAvailability
    readonly blockCode: string | null
    readonly blockReason: string | null
}

/** Forma JSON estavel da listagem; documentada em platform/README.md. */
export interface ProfilesListing {
    readonly catalogVersion: string
    readonly filters: {
        readonly network: string | null
        readonly publication: string | null
        readonly mediaKind: string | null
    }
    readonly project: { readonly consulted: boolean; readonly valid: boolean | null; readonly id: string | null }
    readonly counts: { readonly listed: number; readonly allowed: number; readonly blocked: number; readonly notConsulted: number }
    readonly profiles: readonly ListedProfile[]
    /** Diagnosticos do validador de manifesto, quando um projeto foi informado. */
    readonly diagnostics: readonly ValidationIssue[]
    readonly summary: string
}

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
}

function toListedProfile(
    profile: OutputProfile,
    availability: ProfileAvailability,
    blockCode: string | null,
    blockReason: string | null,
): ListedProfile {
    return {
        id: profile.id,
        name: profile.name,
        revision: profile.revision,
        network: profile.network,
        publication: profile.publication,
        mediaKind: profile.mediaKind,
        width: profile.geometry.width,
        height: profile.geometry.height,
        aspectRatio: profile.geometry.aspectRatio,
        fps: profile.mediaKind === 'video' ? profile.fps : null,
        exportState: profile.exportState,
        exportEvidence: profile.exportEvidence,
        pendingRuleIds: profile.pendingIds,
        availability,
        blockCode,
        blockReason,
    }
}

/**
 * Disponibilidade e bloqueio vem do mesmo allowlist que o resolvedor usa: um
 * perfil fora dele recebe `OUTPUT_PROFILE_NOT_ALLOWED`, e um manifesto rejeitado
 * recebe `OUTPUT_PROJECT_INVALID` em cada perfil, com a lista preservada.
 */
function classify(
    profiles: readonly OutputProfile[],
    projectInput: unknown | undefined,
    projectReport: ProjectValidationReport | null,
    allowed: readonly string[],
): ListedProfile[] {
    return profiles.map((profile) => {
        if (projectInput === undefined || projectReport === null) {
            return toListedProfile(profile, 'not-consulted', null, null)
        }
        if (!projectReport.valid) {
            return toListedProfile(
                profile,
                'blocked',
                'OUTPUT_PROJECT_INVALID',
                `The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`,
            )
        }
        if (allowed.includes(profile.id)) {
            return toListedProfile(profile, 'allowed', null, null)
        }
        return toListedProfile(
            profile,
            'blocked',
            'OUTPUT_PROFILE_NOT_ALLOWED',
            `Profile "${profile.id}" is not listed in project "${String(projectReport.projectId)}" outputProfiles.`,
        )
    })
}

function renderHuman(listing: ProfilesListing): string {
    const lines: string[] = [listing.summary]
    lines.push(
        `Filtros: network=${listing.filters.network ?? '(sem filtro)'} | publication=${listing.filters.publication ?? '(sem filtro)'} | media=${listing.filters.mediaKind ?? '(sem filtro)'}`,
    )
    for (const profile of listing.profiles) {
        const availability = profile.availability === 'allowed' ? 'habilitado'
            : profile.availability === 'blocked' ? 'bloqueado'
                : 'permissao nao consultada'
        lines.push('')
        lines.push(`[${availability}] ${profile.id} — ${profile.name} (revisao ${profile.revision})`)
        lines.push(
            `  destino: ${profile.network}/${profile.publication} | midia: ${profile.mediaKind === 'image' ? 'imagem' : 'video'} | resolucao: ${profile.width}x${profile.height} (${profile.aspectRatio}) | fps: ${profile.fps ?? 'n/a'}`,
        )
        lines.push(`  capacidade de catalogo: ${profile.exportState}`)
        lines.push(`  evidencia da capacidade: ${profile.exportEvidence.length > 0 ? profile.exportEvidence.join(', ') : '(nenhuma)'}`)
        lines.push(`  pendencias de fonte: ${profile.pendingRuleIds.length > 0 ? profile.pendingRuleIds.join(', ') : '(nenhuma)'}`)
        if (profile.blockCode !== null) {
            lines.push(`  bloqueio: ${profile.blockCode} — ${profile.blockReason}`)
        }
    }
    for (const diagnostic of listing.diagnostics) {
        lines.push('')
        lines.push(`  manifesto: ${formatIssue(diagnostic).trimStart()}`)
    }
    return lines.join('\n')
}

function summary(
    listed: number,
    projectReport: ProjectValidationReport | null,
    counts: { allowed: number; blocked: number },
): string {
    const head = `Catalogo v${CATALOG_VERSION}: ${listed} perfil(es) listado(s)`
    if (projectReport === null) return `${head}; permissao de projeto ainda nao consultada.`
    if (!projectReport.valid) {
        return `${head}; o manifesto do projeto foi rejeitado (${counts.blocked} bloqueado(s) pelo manifesto).`
    }
    return `${head}; permissao consultada no allowlist do projeto "${String(projectReport.projectId)}" (${counts.allowed} habilitado(s), ${counts.blocked} bloqueado(s)).`
}

function main(argv: string[]): number {
    const parsed = parseFlags(argv, VALUE_FLAGS)
    if (parsed.error !== null) {
        usageError(parsed.error)
        return EXIT_USAGE
    }

    const filters = readFilters(parsed.values, false)
    if ('error' in filters) {
        usageError(filters.error)
        return EXIT_USAGE
    }

    let projectInput: unknown | undefined
    if (parsed.values.project !== undefined) {
        const file = readJsonFile(parsed.values.project)
        if ('error' in file) {
            console.error(file.error)
            return EXIT_USAGE
        }
        projectInput = file.value
    }

    const { allowed, report: projectReport } = projectInput === undefined
        ? { allowed: [] as string[], report: null }
        : projectAllowedProfiles(projectInput)

    const profiles = classify(
        listOutputProfiles({
            network: filters.network ?? undefined,
            publication: filters.publication ?? undefined,
            mediaKind: filters.mediaKind ?? undefined,
        }),
        projectInput,
        projectReport,
        allowed,
    )

    const counts = {
        listed: profiles.length,
        allowed: profiles.filter((profile) => profile.availability === 'allowed').length,
        blocked: profiles.filter((profile) => profile.availability === 'blocked').length,
        notConsulted: profiles.filter((profile) => profile.availability === 'not-consulted').length,
    }

    const listing: ProfilesListing = {
        catalogVersion: CATALOG_VERSION,
        filters: {
            network: filters.network,
            publication: filters.publication,
            mediaKind: filters.mediaKind,
        },
        project: {
            consulted: projectReport !== null,
            valid: projectReport === null ? null : projectReport.valid,
            id: projectReport?.projectId ?? null,
        },
        counts,
        profiles,
        diagnostics: projectReport === null ? [] : [...projectReport.errors, ...projectReport.warnings],
        summary: summary(profiles.length, projectReport, counts),
    }

    if (parsed.json) {
        console.log(JSON.stringify(listing, null, 2))
    } else {
        console.log(renderHuman(listing))
    }

    if (projectReport !== null && !projectReport.valid) {
        console.error(`Manifesto rejeitado: OUTPUT_PROJECT_INVALID — The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`)
        for (const diagnostic of listing.diagnostics) {
            console.error(formatIssue(diagnostic))
        }
        return EXIT_INVALID
    }

    return EXIT_VALID
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
