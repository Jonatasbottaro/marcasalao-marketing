/**
 * CLI do Worker local de validacao de Composition (`npm run composition:worker`).
 *
 * Anuncia somente Task Queue, namespace e endereco local sanitizado; encerra por
 * sinal (SIGINT/SIGTERM) ou shutdown programatico, com cleanup em finally.
 * Importar este modulo nao inicia nada. Nao imprime documentos recebidos.
 */
import path from 'node:path'
import { pathToFileURL } from 'node:url'

import { runCompositionValidationWorker } from './composition-validation-worker.js'

const FLAG_NAMES = ['--address', '--namespace']

function parseWorkerArguments(argv: readonly string[]): { ok: true; address?: string; namespace?: string } | { ok: false; message: string } {
    const values = new Map<string, string>()
    for (let index = 0; index < argv.length; index += 2) {
        const flag = argv[index] as string
        if (!FLAG_NAMES.includes(flag)) {
            return { ok: false, message: `Flag nao reconhecida: ${flag}. As flags sao ${FLAG_NAMES.join(', ')}.` }
        }
        const value = argv[index + 1]
        if (value === undefined || value.startsWith('--')) {
            return { ok: false, message: `A flag ${flag} exige um valor.` }
        }
        if (values.has(flag)) {
            return { ok: false, message: `A flag ${flag} foi repetida.` }
        }
        values.set(flag, value)
    }
    return { ok: true, address: values.get('--address'), namespace: values.get('--namespace') }
}

export async function runCompositionValidationWorkerCli(argv: readonly string[]): Promise<number> {
    const parsed = parseWorkerArguments(argv)
    if (!parsed.ok) {
        process.stderr.write(`${parsed.message}\n`)
        return 2
    }
    return runCompositionValidationWorker({ address: parsed.address, namespace: parsed.namespace })
}

function isEntrypoint(): boolean {
    const argv1 = process.argv[1]
    return argv1 !== undefined && import.meta.url === pathToFileURL(path.resolve(argv1)).href
}

if (isEntrypoint()) {
    runCompositionValidationWorkerCli(process.argv.slice(2)).then(
        (code) => {
            process.exitCode = code
        },
        (error: unknown) => {
            const message = error instanceof Error ? error.message : 'erro desconhecido'
            process.stderr.write(`o worker de validacao de composition nao rodou: ${message}\n`)
            process.exitCode = 1
        },
    )
}