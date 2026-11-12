/**
 * CLI local de validacao de Composition (`npm run composition:validate`).
 *
 * Le --project e --composition de disco, exige --request-id, roda o preflight
 * antes de qualquer conexao, inicia o Workflow uma unica vez e aguarda o
 * resultado. stdout carrega somente resultado JSON; stderr somente mensagens
 * operacionais fixas. Zero stack, zero payload, zero caminho absoluto em saida.
 *
 * Exit codes: 0 valid; 1 invalid (dominio); 2 uso/argumento/arquivo/preflight;
 * 3 failed (execucao); 4 colisao de Workflow ID; 5 conexao ou start desconhecido.
 */
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

import { Client, Connection } from '@temporalio/client'

import { preflightCompositionValidationInput } from '../composition-validation/composition-validation-preflight.js'
import {
    COMPOSITION_VALIDATION_NAMESPACE,
    COMPOSITION_VALIDATION_START_FAILURE_CODES,
    executeCompositionValidation,
    type CompositionValidationStartFailure,
} from './composition-validation-start.js'
import { DEFAULT_PILOT_ADDRESS, checkLocalAddress } from '../local-address.js'

const VALUE_FLAGS = ['--project', '--composition', '--request-id', '--address', '--namespace']

export const COMPOSITION_VALIDATION_EXIT_CODES = Object.freeze({
    valid: 0,
    invalid: 1,
    usage: 2,
    failed: 3,
    conflict: 4,
    connection: 5,
} as const)

interface CliArguments {
    readonly projectPath: string
    readonly compositionPath: string
    readonly requestId: string
    readonly address: string
    readonly namespace: string
    readonly fullJson: boolean
}

function parseArguments(argv: readonly string[]): { ok: true; args: CliArguments } | { ok: false; message: string } {
    const values = new Map<string, string>()
    let fullJson = false
    for (let index = 0; index < argv.length; index += 1) {
        const flag = argv[index] as string
        if (flag === '--json') {
            fullJson = true
            continue
        }
        if (!VALUE_FLAGS.includes(flag)) {
            return { ok: false, message: `Flag nao reconhecida: ${flag}. As flags sao ${VALUE_FLAGS.join(', ')} e --json.` }
        }
        const value = argv[index + 1]
        if (value === undefined || value.startsWith('--')) {
            return { ok: false, message: `A flag ${flag} exige um valor.` }
        }
        if (values.has(flag)) {
            return { ok: false, message: `A flag ${flag} foi repetida.` }
        }
        values.set(flag, value)
        index += 1
    }
    for (const required of ['--project', '--composition', '--request-id']) {
        if (!values.has(required)) {
            return { ok: false, message: `A flag ${required} e obrigatoria.` }
        }
    }
    const address = values.get('--address') ?? DEFAULT_PILOT_ADDRESS
    const addressProblem = checkLocalAddress(address)
    if (addressProblem !== null) {
        return { ok: false, message: addressProblem }
    }
    return {
        ok: true,
        args: {
            projectPath: values.get('--project') as string,
            compositionPath: values.get('--composition') as string,
            requestId: values.get('--request-id') as string,
            address,
            namespace: values.get('--namespace') ?? COMPOSITION_VALIDATION_NAMESPACE,
            fullJson,
        },
    }
}

function readJsonDocument(filePath: string, label: string): { ok: true; value: unknown } | { ok: false; message: string } {
    let raw: string
    try {
        raw = fs.readFileSync(filePath, 'utf8')
    } catch {
        return { ok: false, message: `Nao foi possivel ler o arquivo de ${label}.` }
    }
    try {
        return { ok: true, value: JSON.parse(raw) }
    } catch {
        return { ok: false, message: `O arquivo de ${label} nao contem JSON valido.` }
    }
}

function refuse(message: string): number {
    process.stderr.write(`${message}\n`)
    return COMPOSITION_VALIDATION_EXIT_CODES.usage
}

function printJson(value: unknown): void {
    process.stdout.write(`${JSON.stringify(value)}\n`)
}

function printStartFailure(start: CompositionValidationStartFailure): number {
    printJson({
        ok: false,
        requestId: start.requestId,
        workflowId: start.workflowId,
        failureCode: start.failureCode,
    })
    if (start.failureCode === COMPOSITION_VALIDATION_START_FAILURE_CODES.workflowIdConflict) {
        return COMPOSITION_VALIDATION_EXIT_CODES.conflict
    }
    if (start.failureCode === COMPOSITION_VALIDATION_START_FAILURE_CODES.connectionFailed) {
        return COMPOSITION_VALIDATION_EXIT_CODES.connection
    }
    if (start.failureCode === COMPOSITION_VALIDATION_START_FAILURE_CODES.startFailed) {
        return COMPOSITION_VALIDATION_EXIT_CODES.connection
    }
    return COMPOSITION_VALIDATION_EXIT_CODES.usage
}

export async function runCompositionValidationCli(argv: readonly string[]): Promise<number> {
    const parsed = parseArguments(argv)
    if (!parsed.ok) return refuse(parsed.message)
    const { args } = parsed

    const project = readJsonDocument(args.projectPath, 'project')
    if (!project.ok) return refuse(project.message)
    const composition = readJsonDocument(args.compositionPath, 'composition')
    if (!composition.ok) return refuse(composition.message)

    const rawInput = {
        schemaVersion: 1,
        requestId: args.requestId,
        project: project.value,
        composition: composition.value,
    }

    // Preflight antes de qualquer conexao: nada sensivel ou invalido chega a history.
    const preflight = preflightCompositionValidationInput(rawInput)
    if (!preflight.ok) {
        return refuse(`A entrada nao passa no preflight: ${preflight.code} em ${preflight.path}.`)
    }

    let connection: Connection
    try {
        connection = await Connection.connect({ address: args.address })
    } catch {
        printJson({
            ok: false,
            requestId: args.requestId,
            workflowId: null,
            failureCode: COMPOSITION_VALIDATION_START_FAILURE_CODES.connectionFailed,
        })
        return COMPOSITION_VALIDATION_EXIT_CODES.connection
    }

    try {
        const client = new Client({ connection, namespace: args.namespace })
        const execution = await executeCompositionValidation(client, rawInput)
        if (!execution.ok) {
            return printStartFailure(execution.start)
        }
        const { start, result } = execution
        if (args.fullJson) {
            printJson({
                ok: true,
                requestId: start.requestId,
                workflowId: start.workflowId,
                runId: start.runId,
                result,
            })
        } else {
            printJson({
                ok: true,
                requestId: start.requestId,
                workflowId: start.workflowId,
                runId: start.runId,
                status: result.status,
                failureCode: result.failureCode,
                projectId: result.projectId,
                compositionId: result.compositionId,
                errorCount: result.validation?.errors.length ?? 0,
                warningCount: result.validation?.warnings.length ?? 0,
            })
        }
        if (result.status === 'valid') return COMPOSITION_VALIDATION_EXIT_CODES.valid
        if (result.status === 'invalid') return COMPOSITION_VALIDATION_EXIT_CODES.invalid
        return COMPOSITION_VALIDATION_EXIT_CODES.failed
    } finally {
        await connection.close()
    }
}

function isEntrypoint(): boolean {
    const argv1 = process.argv[1]
    return argv1 !== undefined && import.meta.url === pathToFileURL(path.resolve(argv1)).href
}

if (isEntrypoint()) {
    runCompositionValidationCli(process.argv.slice(2)).then(
        (code) => {
            process.exitCode = code
        },
        () => {
            process.stderr.write('a validacao de composition nao rodou: erro tecnico sanitizado.\n')
            process.exitCode = COMPOSITION_VALIDATION_EXIT_CODES.connection
        },
    )
}