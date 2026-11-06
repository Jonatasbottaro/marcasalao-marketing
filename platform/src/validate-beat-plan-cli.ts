/**
 * CLI de validacao de BeatPlan contra um manifesto de projeto e uma composicao.
 *
 * Uso:
 *   node dist/src/validate-beat-plan-cli.js --project <caminho> --composition <caminho> --beat-plan <caminho> [--json]
 *
 * Exit codes:
 *   0 — ProjectManifest, Composition e BeatPlan validos;
 *   1 — erro semantico ou de validacao (relatorio emitido);
 *   2 — erro de uso, arquivo ausente ou JSON malformado.
 *
 * A CLI le somente os tres arquivos informados, nao acessa rede, nao abre
 * assets, nao altera arquivos, nao cria outputs, nao gera midia e nao le .env.
 * Erros sao sanitizados, sem stack trace.
 */

import { readFileSync } from 'node:fs'

import { validateBeatPlan } from './validate-beat-plan.js'
import type { BeatPlanValidationReport, ValidationIssue } from './validation-report.js'

const EXIT_VALID = 0
const EXIT_INVALID = 1
const EXIT_USAGE = 2

const USAGE = 'Uso: node dist/src/validate-beat-plan-cli.js --project <caminho> --composition <caminho> --beat-plan <caminho> [--json]'

interface CliOptions {
    projectPath: string | null
    compositionPath: string | null
    beatPlanPath: string | null
    json: boolean
}

function emptyOptions(json: boolean): CliOptions {
    return { projectPath: null, compositionPath: null, beatPlanPath: null, json }
}

function parseArgs(argv: string[]): CliOptions {
    const options: CliOptions = emptyOptions(false)

    for (let index = 0; index < argv.length; index++) {
        const arg = argv[index]
        if (arg === '--project' || arg === '--composition' || arg === '--beat-plan') {
            const value = argv[index + 1]
            if (value === undefined) {
                return emptyOptions(options.json)
            }
            if (arg === '--project') {
                options.projectPath = value
            } else if (arg === '--composition') {
                options.compositionPath = value
            } else {
                options.beatPlanPath = value
            }
            index++
            continue
        }
        if (arg === '--json') {
            options.json = true
            continue
        }
        // Argumento desconhecido: tratamento sanitizado como erro de uso.
        return emptyOptions(options.json)
    }

    return options
}

function readJsonFile(filePath: string): { value: unknown } | { error: string } {
    let rawContent: string
    try {
        rawContent = readFileSync(filePath, 'utf8')
    } catch {
        return { error: `Erro: arquivo nao encontrado ou ilegivel: ${filePath}` }
    }

    try {
        return { value: JSON.parse(rawContent) as unknown }
    } catch {
        return { error: `Erro: JSON malformado em: ${filePath}` }
    }
}

function formatIssue(item: ValidationIssue): string {
    const location = item.path.length > 0 ? ` em \`${item.path}\`` : ''
    return `  [${item.code}]${location}: ${item.message}`
}

function renderHuman(report: BeatPlanValidationReport): string {
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

    if (options.projectPath === null || options.compositionPath === null || options.beatPlanPath === null) {
        console.error(USAGE)
        return EXIT_USAGE
    }

    const projectRead = readJsonFile(options.projectPath)
    if ('error' in projectRead) {
        console.error(projectRead.error)
        return EXIT_USAGE
    }

    const compositionRead = readJsonFile(options.compositionPath)
    if ('error' in compositionRead) {
        console.error(compositionRead.error)
        return EXIT_USAGE
    }

    const beatPlanRead = readJsonFile(options.beatPlanPath)
    if ('error' in beatPlanRead) {
        console.error(beatPlanRead.error)
        return EXIT_USAGE
    }

    const report = validateBeatPlan(beatPlanRead.value, compositionRead.value, projectRead.value)

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
