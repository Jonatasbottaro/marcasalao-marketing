/**
 * CLI de validacao consolidada do pipeline criativo (`content:validate-pipeline`).
 *
 * Uso:
 *   node dist/src/content-pipeline-validation-cli.js --project <caminho> --composition <caminho> --output-plan <caminho> --beat-plan <caminho> [--json]
 *
 * Exit codes:
 *   0 — Pipeline completo valido;
 *   1 — Pipeline invalido de dominio (relatorio emitido em stdout);
 *   2 — Erro de uso, arquivo ausente ou JSON malformado.
 *
 * Flags, leitura de JSON, exit codes e formato de diagnostico vem de
 * `cli-input.ts`, o mesmo helper compartilhado das demais CLIs. O stdout
 * contem **somente** o relatorio; mensagens de uso e de erro operacional vao
 * para stderr com stdout vazio. Zero stack trace, zero caminho absoluto em erro.
 */

import {
    EXIT_INVALID,
    EXIT_USAGE,
    EXIT_VALID,
    parseFlags,
    readJsonFile,
} from './cli-input.js'
import type { ContentPipelineValidationReport } from './content-pipeline-validation-contract.js'
import { validateContentPipeline } from './validate-content-pipeline.js'

const VALUE_FLAGS = ['--project', '--composition', '--output-plan', '--beat-plan'] as const

const USAGE = 'Uso: node dist/src/content-pipeline-validation-cli.js --project <caminho> --composition <caminho> --output-plan <caminho> --beat-plan <caminho> [--json]'

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
}

function renderHuman(report: ContentPipelineValidationReport): string {
    const lines: string[] = [report.summary]
    for (const error of report.errors) {
        lines.push(`  [${error.stage}] ${error.code} @${error.path}: ${error.message}`)
    }
    for (const warning of report.warnings) {
        lines.push(`  [${warning.stage}] ${warning.code} @${warning.path}: ${warning.message}`)
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
    const outputPlanPath = parsed.values['output-plan']
    const beatPlanPath = parsed.values['beat-plan']

    if (
        projectPath === undefined ||
        compositionPath === undefined ||
        outputPlanPath === undefined ||
        beatPlanPath === undefined
    ) {
        usageError('as flags --project, --composition, --output-plan e --beat-plan sao obrigatorias')
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

    const outputPlanFile = readJsonFile(outputPlanPath)
    if ('error' in outputPlanFile) {
        console.error(outputPlanFile.error)
        return EXIT_USAGE
    }

    const beatPlanFile = readJsonFile(beatPlanPath)
    if ('error' in beatPlanFile) {
        console.error(beatPlanFile.error)
        return EXIT_USAGE
    }

    const report = validateContentPipeline({
        project: projectFile.value,
        composition: compositionFile.value,
        outputPlan: outputPlanFile.value,
        beatPlan: beatPlanFile.value,
    })

    console.log(parsed.json ? JSON.stringify(report, null, 2) : renderHuman(report))

    return report.valid ? EXIT_VALID : EXIT_INVALID
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
