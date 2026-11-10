/**
 * Testes de processo filho para o preflight de TEMPORAL-02-02.
 *
 * Comprova em processo isolado que:
 * - importar os modulos compilados de composition-validation nao abre conexao,
 *   nao cria listener e nao deixa handles ou requests ativos;
 * - rejeicoes de preflight (payload grande, conteudo sensivel, envelope invalido)
 *   retornam exit code 1 com saida sanitizada, sem tentar conectar a 127.0.0.1:7233
 *   e sem invocar o callback injetado (marcador em disco nao e criado);
 * - input valido atravessa o preflight e invoca o callback local exatamente uma vez
 *   com exit code 0.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const builtCompositionValidationDir = fileURLToPath(
    new URL('../../src/composition-validation', import.meta.url),
)

function runChildScenario(scenario: 'invalid' | 'too-large' | 'sensitive' | 'valid', markerPath: string) {
    const preflightUrl = pathToFileURL(
        path.join(builtCompositionValidationDir, 'composition-validation-preflight.js'),
    ).href

    const childScript = `
import { writeFileSync } from 'node:fs';
import net from 'node:net';
import { startAfterCompositionPreflight } from ${JSON.stringify(preflightUrl)};

const scenario = process.env.PREFLIGHT_SCENARIO;
const markerPath = process.env.PREFLIGHT_MARKER;

const origConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
    process.stderr.write('PROIBIDO: tentativa de conexao TCP detectada\\n');
    process.exit(99);
    return origConnect.apply(this, args);
};

const baseProject = {
    schemaVersion: 1,
    projectId: 'fixture-project',
    name: 'Projeto Processo',
    defaultLocale: 'pt-BR',
    supportedFormatProfiles: ['vertical-short-v1'],
    assetRoot: 'assets/fixture',
};

const baseComposition = {
    schemaVersion: 1,
    compositionId: 'comp-proc-01',
    projectId: 'fixture-project',
    locale: 'pt-BR',
    format: { profile: 'vertical-short-v1', aspectRatio: '9:16', width: 1080, height: 1920 },
    scenes: [{ sceneId: 's1', durationMs: 3000 }],
};

let candidate;
if (scenario === 'invalid') {
    candidate = {
        schemaVersion: 99,
        requestId: 'req-proc-invalid',
        project: baseProject,
        composition: baseComposition,
    };
} else if (scenario === 'too-large') {
    candidate = {
        schemaVersion: 1,
        requestId: 'req-proc-large',
        project: { ...baseProject, pad: 'x'.repeat(70000) },
        composition: baseComposition,
    };
} else if (scenario === 'sensitive') {
    candidate = {
        schemaVersion: 1,
        requestId: 'req-proc-sensitive',
        project: { ...baseProject, apiKey: 'marcador-sensivel-nao-ecoado' },
        composition: baseComposition,
    };
} else {
    candidate = {
        schemaVersion: 1,
        requestId: 'req-proc-valid',
        project: baseProject,
        composition: baseComposition,
    };
}

const outcome = await startAfterCompositionPreflight(candidate, (validated) => {
    writeFileSync(markerPath, JSON.stringify({ requestId: validated.requestId }), 'utf8');
    return { started: true };
});

if (!outcome.ok) {
    process.stderr.write(JSON.stringify(outcome) + '\\n');
    process.exitCode = 1;
} else {
    process.stdout.write(JSON.stringify({ ok: true, sizes: outcome.preflight.sizes }) + '\\n');
    process.exitCode = 0;
}
`

    const result = spawnSync(process.execPath, ['--input-type=module', '-e', childScript], {
        encoding: 'utf8',
        timeout: 30_000,
        env: {
            ...process.env,
            PREFLIGHT_SCENARIO: scenario,
            PREFLIGHT_MARKER: markerPath,
        },
    })

    assert.equal(result.error, undefined, `falha ao executar processo filho (${scenario}): ${result.error?.message}`)
    return {
        status: result.status,
        stdout: result.stdout ?? '',
        stderr: result.stderr ?? '',
    }
}

test('importar os modulos compilados de composition-validation nao inicia conexao nem deixa handles ativos', () => {
    const files = [
        'composition-validation-failures.js',
        'composition-validation-input.js',
        'composition-validation-preflight.js',
    ]

    for (const file of files) {
        const moduleUrl = pathToFileURL(path.join(builtCompositionValidationDir, file)).href
        const result = spawnSync(
            process.execPath,
            ['--input-type=module', '-e', `await import(${JSON.stringify(moduleUrl)})`],
            { encoding: 'utf8', timeout: 30_000 },
        )

        assert.equal(result.error, undefined)
        assert.equal(result.status, 0)
        assert.equal(result.stdout, '')
        assert.equal(result.stderr, '')
    }
})

test('processo filho recusa envelope invalido, payload grande e conteudo sensivel antes do start e aceita input valido no callback local', () => {
    const tempDir = mkdtempSync(path.join(os.tmpdir(), 'temporal-02-02-proc-'))
    try {
        // 1. Envelope invalido
        const invalidMarker = path.join(tempDir, 'invalid.marker')
        const invalidOutcome = runChildScenario('invalid', invalidMarker)
        assert.equal(invalidOutcome.status, 1)
        assert.equal(invalidOutcome.stdout, '')
        assert.equal(existsSync(invalidMarker), false, 'callback nao pode ser chamado para envelope invalido')
        assert.ok(!invalidOutcome.stderr.includes('    at '), 'stderr nao pode conter stack trace')
        const invalidPayload = JSON.parse(invalidOutcome.stderr.trim()) as Record<string, unknown>
        assert.equal(invalidPayload.code, 'TEMPORAL_COMPOSITION_INPUT_INVALID')
        assert.equal(invalidPayload.path, '$.schemaVersion')

        // 2. Payload grande
        const largeMarker = path.join(tempDir, 'large.marker')
        const largeOutcome = runChildScenario('too-large', largeMarker)
        assert.equal(largeOutcome.status, 1)
        assert.equal(largeOutcome.stdout, '')
        assert.equal(existsSync(largeMarker), false, 'callback nao pode ser chamado para payload acima do limite')
        const largePayload = JSON.parse(largeOutcome.stderr.trim()) as Record<string, unknown>
        assert.equal(largePayload.code, 'TEMPORAL_COMPOSITION_INPUT_TOO_LARGE')
        assert.equal(largePayload.path, '$.project')

        // 3. Conteudo sensivel
        const sensitiveMarker = path.join(tempDir, 'sensitive.marker')
        const sensitiveOutcome = runChildScenario('sensitive', sensitiveMarker)
        assert.equal(sensitiveOutcome.status, 1)
        assert.equal(sensitiveOutcome.stdout, '')
        assert.equal(existsSync(sensitiveMarker), false, 'callback nao pode ser chamado para conteudo sensivel')
        assert.ok(
            !sensitiveOutcome.stderr.includes('marcador-sensivel-nao-ecoado'),
            'stderr nao pode ecoar o valor sensivel rejeitado',
        )
        assert.ok(!sensitiveOutcome.stderr.includes('apiKey'), 'stderr nao pode ecoar a chave sensivel')
        const sensitivePayload = JSON.parse(sensitiveOutcome.stderr.trim()) as Record<string, unknown>
        assert.equal(sensitivePayload.code, 'TEMPORAL_COMPOSITION_SENSITIVE_INPUT')
        assert.equal(sensitivePayload.path, '$.project.<prohibited>')

        // 4. Input valido chega ao callback local exatamente uma vez sem tocar em rede
        const validMarker = path.join(tempDir, 'valid.marker')
        const validOutcome = runChildScenario('valid', validMarker)
        assert.equal(validOutcome.status, 0)
        assert.equal(validOutcome.stderr, '')
        assert.equal(existsSync(validMarker), true, 'callback local deve criar o marcador quando o preflight aprova')
        const markerContent = JSON.parse(readFileSync(validMarker, 'utf8')) as { requestId: string }
        assert.equal(markerContent.requestId, 'req-proc-valid')
    } finally {
        rmSync(tempDir, { recursive: true, force: true })
    }
})
