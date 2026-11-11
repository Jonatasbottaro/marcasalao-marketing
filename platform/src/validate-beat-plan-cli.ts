/**
 * CLI de validacao de BeatPlan (`content:validate-beat-plan`).
 *
 * Uso:
 *   node dist/src/validate-beat-plan-cli.js --project <caminho> --composition
 *       <caminho> --beat-plan <caminho> [--json]
 *
 * Exit codes:
 *   0 — ProjectManifest, Composition e BeatPlan validos entre si;
 *   1 — JSON legivel com plano, projeto ou composicao invalidos (relatorio emitido);
 *   2 — erro de uso, arquivo ausente ou JSON malformado.
 *
 * Flags, leitura de JSON, exit codes e formato de diagnostico vem de
 * `cli-input.ts`, o mesmo helper das CLIs de saida: nem parser, nem codigo de
 * saida, nem leitura de arquivo e reimplementado aqui. O stdout contem
 * **somente** o relatorio (JSON em `--json`, texto nos demais casos) inclusive
 * quando o documento e invalido; erro de uso, arquivo ausente e JSON malformado
 * saem em stderr com o stdout vazio. A CLI le somente os tres arquivos
 * informados, nao acessa rede, nao abre assets, nao altera arquivos, nao cria
 * outputs, nao gera midia e nao le `.env`. Erros sao sanitizados, sem stack trace.
 */

import {
    EXIT_INVALID,
    EXIT_USAGE,
    EXIT_VALID,
    formatIssue,
    parseFlags,
    readJsonFile,
} from './cli-input.js'
import { validateBeatPlan } from './validate-beat-plan.js'
import type { BeatPlanValidationReport } from './validation-report.js'

const VALUE_FLAGS = ['--project', '--composition', '--beat-plan'] as const

const USAGE = 'Uso: node dist/src/validate-beat-plan-cli.js --project <caminho> --composition <caminho> --beat-plan <caminho> [--json]'

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
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
    const parsed = parseFlags(argv, VALUE_FLAGS)
    if (parsed.error !== null) {
        usageError(parsed.error)
        return EXIT_USAGE
    }

    const projectPath = parsed.values.project
    const compositionPath = parsed.values.composition
    const beatPlanPath = parsed.values['beat-plan']
    if (projectPath === undefined || compositionPath === undefined || beatPlanPath === undefined) {
        usageError('as flags --project, --composition e --beat-plan sao obrigatorias')
        return EXIT_USAGE
    }

    const projectFile = readJsonFile(projectPath)
    if ('error' in projectFile) {
        console.error(projectFile.error)
        return EXIT_USAGE
    }

    const compositionFile = readJsonFile(compositionPath)
    if ('error' in compositionFile) {
        console.error(compositionFile.error)
        return EXIT_USAGE
    }

    const beatPlanFile = readJsonFile(beatPlanPath)
    if ('error' in beatPlanFile) {
        console.error(beatPlanFile.error)
        return EXIT_USAGE
    }

    const report = validateBeatPlan(beatPlanFile.value, compositionFile.value, projectFile.value)
    console.log(parsed.json ? JSON.stringify(report, null, 2) : renderHuman(report))

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
