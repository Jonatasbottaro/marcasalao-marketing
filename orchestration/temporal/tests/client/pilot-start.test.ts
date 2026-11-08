/**
 * Opcoes de inicio do piloto pelo cliente.
 *
 * O cliente e a unica camada que escolhe task queue, workflowId e politicas de
 * colisao. As politicas sao fixas de proposito: REJECT_DUPLICATE e FAIL para
 * que um segundo pedido com o mesmo requestId seja barrado em vez de criar uma
 * execucao paralela silenciosa. O endereco aceito e sempre local.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { WorkflowExecutionAlreadyStartedError } from '@temporalio/common'
import { WorkflowIdConflictPolicy, WorkflowIdReusePolicy } from '@temporalio/client'

import { PILOT_FAILURE_CODES } from '../../src/pilot-core/failures.js'
import { PILOT_OPERATION, PILOT_SCHEMA_VERSION, parsePilotInput } from '../../src/pilot-core/pilot-input.js'
import { PILOT_NAMESPACE, PILOT_TASK_QUEUE } from '../../src/workflows/content-pilot-workflow.js'
import { describeStartFailure, parseInputArguments, parseRunArguments, pilotStartOptions } from '../../src/client/pilot-start.js'

function validInput(requestId = 'req-0001') {
    const parsed = parsePilotInput({
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId,
        projectId: 'marcasalao',
        operation: PILOT_OPERATION,
        payload: { label: 'piloto' },
    })
    assert.ok(parsed.ok)
    return parsed.input
}

test('os argumentos padrao apontam para o servidor local e para a entrada de demonstracao', () => {
    const parsed = parseRunArguments([])

    assert.deepEqual(parsed, {
        ok: true,
        config: {
            address: '127.0.0.1:7233',
            rawInput: {
                schemaVersion: PILOT_SCHEMA_VERSION,
                requestId: 'req-0001',
                projectId: 'marcasalao',
                operation: PILOT_OPERATION,
                payload: { label: 'piloto' },
            },
        },
    })
})

test('requestId, projectId, label e endereco podem ser passados por argumento', () => {
    const parsed = parseRunArguments(['--request-id', 'req-0009', '--project-id', 'multitrack-hub', '--label', 'colisao', '--address', 'localhost:7234'])

    assert.equal(parsed.ok, true)
    assert.ok(parsed.ok)
    assert.equal(parsed.config.address, 'localhost:7234')
    assert.ok(!('address' in (parsed.config.rawInput as object)))
    const input = parsePilotInput(parsed.config.rawInput)
    assert.ok(input.ok)
    assert.equal(input.input.requestId, 'req-0009')
    assert.equal(input.input.projectId, 'multitrack-hub')
    assert.deepEqual(input.input.payload, { label: 'colisao' })
})

test('um endereco que nao e local e recusado', () => {
    for (const argv of [['--address', 'temporal.example.com:443'], ['--address', '10.0.0.5:7233'], ['--address', 'example.com:7233']]) {
        const parsed = parseRunArguments(argv)

        assert.equal(parsed.ok, false)
        assert.ok(!parsed.ok)
        assert.match(parsed.message, /localhost/i)
    }
})

test('flag desconhecida, flag sem valor e valor invalido sao recusados', () => {
    const cases = [['--namespace', 'producao'], ['--address'], ['--request-id'], ['--request-id', 'REQ-0009'], ['--position'], ['--label', 'x'.repeat(60)]]

    for (const argv of cases) {
        const parsed = parseRunArguments(argv)
        assert.equal(parsed.ok, false, `deveria recusar ${argv.join(' ')}`)
    }
})

test('as opcoes de inicio derivam o workflowId e barram colisao', () => {
    const options = pilotStartOptions(validInput('req-0009'))

    assert.equal(options.taskQueue, 'marketing-temporal-pilot-v1')
    assert.equal(options.workflowId, 'temporal-pilot-req-0009')
    assert.deepEqual(options.args, [validInput('req-0009')])
    assert.equal(options.workflowIdReusePolicy, WorkflowIdReusePolicy.REJECT_DUPLICATE)
    assert.equal(options.workflowIdConflictPolicy, WorkflowIdConflictPolicy.FAIL)
})

test('as opcoes de inicio carregam exatamente as cinco chaves declaradas', () => {
    const options = pilotStartOptions(validInput('req-0009'))

    assert.deepEqual(Object.keys(options).sort(), ['args', 'taskQueue', 'workflowId', 'workflowIdConflictPolicy', 'workflowIdReusePolicy'])
    assert.equal(options.args.length, 1, 'o Workflow recebe um unico argumento')
})

test('a mesma entrada produz opcoes equivalentes, sem relogio nem aleatoriedade', () => {
    const input = validInput('req-estavel')

    assert.deepEqual(pilotStartOptions(input), pilotStartOptions(input))
    assert.equal(pilotStartOptions(input).workflowId, `temporal-pilot-${input.requestId}`)
    assert.equal(pilotStartOptions(input).taskQueue, PILOT_TASK_QUEUE)
})

test('requestIds diferentes mudam apenas o workflowId', () => {
    const first = pilotStartOptions(validInput('req-um'))
    const second = pilotStartOptions(validInput('req-dois'))

    assert.notEqual(first.workflowId, second.workflowId)
    assert.equal(first.taskQueue, second.taskQueue)
    assert.equal(first.workflowIdReusePolicy, second.workflowIdReusePolicy)
    assert.equal(first.workflowIdConflictPolicy, second.workflowIdConflictPolicy)
})

test('as opcoes de inicio nao escolhem namespace: quem o escolhe e o cliente', () => {
    const options = pilotStartOptions(validInput('req-namespace'))

    assert.ok(!('namespace' in options), 'o namespace nao sai pelas opcoes de inicio')
    assert.equal(PILOT_NAMESPACE, 'default')
})

test('a colisao de workflowId tem codigo proprio e os demais erros nao', () => {
    assert.equal(describeStartFailure(new WorkflowExecutionAlreadyStartedError('já existe', 'temporal-pilot-req-0009', 'run-1')), PILOT_FAILURE_CODES.workflowIdConflict)
    assert.equal(describeStartFailure(new Error('falha de conexao')), PILOT_FAILURE_CODES.workflowFailed)
    assert.equal(describeStartFailure('texto solto'), PILOT_FAILURE_CODES.workflowFailed)
    assert.equal(describeStartFailure(undefined), PILOT_FAILURE_CODES.workflowFailed)
})

test('a execucao local sem argumentos usa a mesma entrada de demonstracao do cliente', () => {
    const parsed = parseInputArguments([])

    assert.deepEqual(parsed, {
        ok: true,
        rawInput: {
            schemaVersion: PILOT_SCHEMA_VERSION,
            requestId: 'req-0001',
            projectId: 'marcasalao',
            operation: PILOT_OPERATION,
            payload: { label: 'piloto' },
        },
    })
})

test('a execucao local aceita requestId, projectId e label', () => {
    const parsed = parseInputArguments(['--request-id', 'req-0042', '--project-id', 'multitrack-hub', '--label', 'local'])

    assert.equal(parsed.ok, true)
    assert.ok(parsed.ok)
    assert.ok(!('address' in (parsed.rawInput as object)))
    const input = parsePilotInput(parsed.rawInput)
    assert.ok(input.ok)
    assert.equal(input.input.requestId, 'req-0042')
    assert.deepEqual(input.input.payload, { label: 'local' })
})

test('a execucao local recusa --address porque o servidor dela e efemero', () => {
    const parsed = parseInputArguments(['--address', 'localhost:7233'])

    assert.equal(parsed.ok, false)
    assert.ok(!parsed.ok)
    assert.match(parsed.message, /--address/)
})

test('a execucao local recusa flag desconhecida, sem valor e entrada fora do contrato', () => {
    const casos = [['--namespace', 'default'], ['--request-id'], ['--project-id', 'Projeto'], ['--label', 'x'.repeat(60)], ['--request-id', 'req-1', '--request-id', 'req-2']]

    for (const argv of casos) {
        const parsed = parseInputArguments(argv)

        assert.equal(parsed.ok, false, `deveria recusar: ${argv.join(' ')}`)
    }
})
