/**
 * CLI de validacao de manifesto de projeto.
 *
 * Uso:
 *   node src/validate-project-cli.ts --project <caminho> [--json]
 *
 * Exit codes:
 *   0 — manifesto valido;
 *   1 — manifesto invalido (relatorio emitido);
 *   2 — erro de uso, arquivo ausente ou JSON malformado.
 *
 * A CLI le somente o arquivo informado, nao acessa rede, nao altera arquivos,
 * nao cria outputs e nao le .env. Erros sao sanitizados, sem stack trace.
 */

import { readFileSync } from 'node:fs'

import { validateProjectManifest } from './validate-project.ts'
import type { ProjectValidationReport, ValidationIssue } from './validation-report.ts'

const EXIT_VALID = 0
const EXIT_INVALID = 1
const EXIT_USAGE = 2

interface CliOptions {
    projectPath: string | null
    json: boolean
}

function parseArgs(argv: string[]): CliOptions {
    const options: CliOptions = { projectPath: null, json: false }

    for (let index = 0; index < argv.length; index++) {
        const arg = argv[index]
        if (arg === '--project') {
            const value = argv[index + 1]
            if (value === undefined) {
                return { projectPath: null, json: options.json }
            }
            options.projectPath = value
            index++
            continue
        }
        if (arg === '--json') {
            options.json = true
            continue
        }
        // Argumento desconhecido: tratamento sanitizado como erro de uso.
        return { projectPath: null, json: options.json }
    }

    return options
}

function formatIssue(item: ValidationIssue): string {
    const location = item.path.length > 0 ? ` em \`${item.path}\`` : ''
    return `  [${item.code}]${location}: ${item.message}`
}

function renderHuman(report: ProjectValidationReport): string {
    const lines: string[] = [report.summary]
    for (const error of report.errors) {
        lines.push(formatIssue(error))
    }
    for (const warning of report.warnings) {
        lines.push(formatIssue(warning))
    }
    return lines.join('\n')
}

function main(argv: string[]): number {
    const options = parseArgs(argv)

    if (options.projectPath === null) {
        console.error('Uso: node src/validate-project-cli.ts --project <caminho> [--json]')
        return EXIT_USAGE
    }

    let rawContent: string
    try {
        rawContent = readFileSync(options.projectPath, 'utf8')
    } catch {
        console.error(`Erro: arquivo nao encontrado ou ilegivel: ${options.projectPath}`)
        return EXIT_USAGE
    }

    let parsed: unknown
    try {
        parsed = JSON.parse(rawContent)
    } catch {
        console.error(`Erro: JSON malformado em: ${options.projectPath}`)
        return EXIT_USAGE
    }

    const report = validateProjectManifest(parsed)

    if (options.json) {
        console.log(JSON.stringify(report, null, 2))
    } else {
        console.log(renderHuman(report))
    }

    return report.valid ? EXIT_VALID : EXIT_INVALID
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    // Sanitizado: nenhuma stack trace por padrao.
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
