/**
 * CLI interna multiprojeto de casos do pipeline criativo (`content:validate-cases`).
 *
 * Uso:
 *   node dist/src/content-pipeline-cases-cli.js --case <manifesto> [--root <raiz>] [--json]
 *   node dist/src/content-pipeline-cases-cli.js --cases-root <diretorio> [--json]
 *
 * `--case` valida um unico manifesto de caso; a raiz de confinamento e `--root`
 * quando informado, ou o proprio diretorio do manifesto. `--cases-root` descobre
 * todos os `*.pipeline.json` sob o diretorio (ordem deterministica, symlinks
 * ignorados) e usa esse diretorio como raiz de confinamento de todos os casos.
 *
 * Exit codes:
 *   0 — caso valido, ou todos os casos validos;
 *   1 — caso(s) invalido(s) de dominio ou manifesto estruturalmente invalido;
 *   2 — erro de uso, documento ilegivel, manifesto malformado ou descoberta vazia.
 *
 * Flags, leitura de JSON e exit codes vem de `cli-input.ts`, o mesmo helper
 * compartilhado das demais CLIs. O stdout contem **somente** o relatorio de
 * dominio; mensagens de uso e de erro operacional (incluindo casos nao lidos)
 * vao para stderr com stdout vazio. Zero stack trace, zero caminho absoluto da
 * maquina em mensagens de erro.
 */

import path from 'node:path'

import {
    EXIT_INVALID,
    EXIT_USAGE,
    EXIT_VALID,
    parseFlags,
} from './cli-input.js'
import {
    discoverCaseManifests,
    validateContentPipelineCaseFromDisk,
} from './content-pipeline-case-loader.js'
import {
    aggregateContentPipelineCases,
    type ContentPipelineCasesValidationReport,
    type ContentPipelineCaseValidationReport,
} from './validate-content-pipeline-case.js'

const VALUE_FLAGS = ['--case', '--root', '--cases-root'] as const

const USAGE = 'Uso: node dist/src/content-pipeline-cases-cli.js --case <manifesto> [--root <raiz>] [--json] | --cases-root <diretorio> [--json]'

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
}

function renderCaseDetails(report: ContentPipelineCaseValidationReport): string[] {
    const lines: string[] = []
    for (const error of report.manifestReport.errors) {
        lines.push(`  [manifest] ${error.code} @${error.path}: ${error.message}`)
    }
    for (const readError of report.readErrors) {
        lines.push(`  [read] ${readError}`)
    }
    if (report.pipeline !== null) {
        for (const error of report.pipeline.errors) {
            lines.push(`  [${error.stage}] ${error.code} @${error.path}: ${error.message}`)
        }
        for (const warning of report.pipeline.warnings) {
            lines.push(`  [${warning.stage}] ${warning.code} @${warning.path}: ${warning.message}`)
        }
    }
    return lines
}

function renderCaseHuman(report: ContentPipelineCaseValidationReport): string {
    const lines: string[] = [report.summary]
    lines.push(...renderCaseDetails(report))
    return lines.join('\n')
}

function renderCasesHuman(report: ContentPipelineCasesValidationReport): string {
    const lines: string[] = [report.summary]
    for (const caseReport of report.cases) {
        lines.push(`  ${caseReport.caseId ?? '(sem id)'}: ${caseReport.status}`)
        if (!caseReport.valid) {
            lines.push(...renderCaseDetails(caseReport))
        }
    }
    for (const error of report.errors) {
        lines.push(`  [cases] ${error.code} @${error.path}: ${error.message}`)
    }
    return lines.join('\n')
}

function exitCodeForCase(report: ContentPipelineCaseValidationReport): number {
    if (report.valid) return EXIT_VALID
    return report.status === 'unreadable' ? EXIT_USAGE : EXIT_INVALID
}

function exitCodeForCases(report: ContentPipelineCasesValidationReport): number {
    if (report.valid) return EXIT_VALID
    if (report.cases.some((caseReport) => caseReport.status === 'unreadable')) return EXIT_USAGE
    return EXIT_INVALID
}

/** Erro operacional de leitura: diagnostico em stderr, nunca no stdout. */
function reportUnreadable(caseReport: ContentPipelineCaseValidationReport): void {
    const label = caseReport.caseId ?? '(sem id)'
    console.error(`Erro: caso ${label} ilegivel: ${caseReport.summary}`)
    for (const readError of caseReport.readErrors) {
        console.error(`  ${readError}`)
    }
    for (const error of caseReport.manifestReport.errors) {
        console.error(`  ${error.code}: ${error.message}`)
    }
}

function main(argv: string[]): number {
    const parsed = parseFlags(argv, VALUE_FLAGS)
    if (parsed.error !== null) {
        usageError(parsed.error)
        return EXIT_USAGE
    }

    const casePath = parsed.values.case
    const casesRoot = parsed.values['cases-root']
    const root = parsed.values.root

    if ((casePath === undefined) === (casesRoot === undefined)) {
        usageError('informe exatamente um modo: --case <manifesto> ou --cases-root <diretorio>')
        return EXIT_USAGE
    }
    if (root !== undefined && casePath === undefined) {
        usageError('--root so pode ser usado junto com --case')
        return EXIT_USAGE
    }

    if (casePath !== undefined) {
        const containmentRoot = root ?? path.dirname(path.resolve(casePath))
        const report = validateContentPipelineCaseFromDisk(casePath, containmentRoot)
        if (report.status === 'unreadable') {
            reportUnreadable(report)
            return EXIT_USAGE
        }
        console.log(parsed.json ? JSON.stringify(report, null, 2) : renderCaseHuman(report))
        return exitCodeForCase(report)
    }

    const discovery = discoverCaseManifests(casesRoot as string)
    if (!discovery.ok) {
        console.error(`Erro: ${discovery.error}`)
        return EXIT_USAGE
    }
    if (discovery.paths.length === 0) {
        console.error('Erro de uso: nenhum manifesto *.pipeline.json encontrado sob a raiz informada')
        console.error(USAGE)
        return EXIT_USAGE
    }

    const cases = discovery.paths.map((manifestPath) =>
        validateContentPipelineCaseFromDisk(manifestPath, casesRoot as string),
    )
    const report = aggregateContentPipelineCases(cases)
    if (report.cases.some((caseReport) => caseReport.status === 'unreadable')) {
        for (const caseReport of report.cases) {
            if (caseReport.status === 'unreadable') reportUnreadable(caseReport)
        }
        return EXIT_USAGE
    }
    console.log(parsed.json ? JSON.stringify(report, null, 2) : renderCasesHuman(report))
    return exitCodeForCases(report)
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
