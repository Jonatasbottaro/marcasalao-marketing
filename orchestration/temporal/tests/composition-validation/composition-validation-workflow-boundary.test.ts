/**
 * Guardas estaticas de fronteira para TEMPORAL-02 (fatia Workflow).
 *
 * Assegura que os modulos do Workflow de validacao de composicao:
 * - nao importam ou referenciam marcasalao-marketing-platform, platform/src,
 *   platform/dist ou caminhos relativos da platform (estatico, type, dinamico ou require);
 * - nao importam valores de runtime de src/activities/, worker/, client/ ou local/;
 * - nao usam APIs de I/O, rede, subprocesso, relogio, ambiente ou aleatoriedade;
 * - nao declaram, leem ou constroem workflowId, Reuse/Conflict policies, contentHash,
 *   SHA-256, workflow.start, OutputPlan ou BeatPlan;
 * - mantem o contrato de resultado livre de @temporalio/*;
 * - mantem src/worker/ e src/client/ intactos (sem registro de validateCompositionWorkflow).
 */
import assert from 'node:assert/strict'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const temporalRoot = fileURLToPath(new URL('../../../', import.meta.url))
const srcDir = path.join(temporalRoot, 'src')
const workflowsSrcDir = path.join(srcDir, 'workflows')
const builtWorkflowsDir = path.join(temporalRoot, 'dist', 'src', 'workflows')

const WORKFLOW_SLICE_FILES = [
    'composition-validation-workflow.ts',
    'composition-validation-result.ts',
    'composition-validation-failure-classifier.ts',
] as const

function listTsFiles(dir: string): string[] {
    if (!existsSync(dir)) return []
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const full = path.join(dir, entry.name)
        if (entry.isDirectory()) return listTsFiles(full)
        return entry.name.endsWith('.ts') ? [full] : []
    })
}

function stripComments(source: string): string {
    return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')
}

function importLines(source: string): string[] {
    return stripComments(source)
        .split(/\r?\n/)
        .filter((line) => /^\s*(import|export)\b/.test(line))
}

test('modulos da fatia Workflow nao importam platform, APIs de I/O, nao-determinismo nem escopo nao autorizado', () => {
    const forbiddenImports: ReadonlyArray<{ pattern: RegExp; category: string }> = [
        { pattern: /marcasalao-marketing-platform/, category: 'pacote publico marcasalao-marketing-platform' },
        { pattern: /platform\/src/, category: 'caminho proibido platform/src' },
        { pattern: /platform\/dist/, category: 'caminho proibido platform/dist' },
        { pattern: /\.\.\/platform/, category: 'caminho relativo ../platform' },
        { pattern: /\.\.\/worker\//, category: 'camada proibida src/worker' },
        { pattern: /\.\.\/client\//, category: 'camada proibida src/client' },
        { pattern: /\.\.\/local\//, category: 'camada proibida src/local' },
        { pattern: /node:fs/, category: 'I/O de disco (node:fs)' },
        { pattern: /['"]fs['"]/, category: 'I/O de disco (fs)' },
        { pattern: /node:net/, category: 'rede (node:net)' },
        { pattern: /node:http/, category: 'rede (node:http)' },
        { pattern: /node:https/, category: 'rede (node:https)' },
        { pattern: /node:dns/, category: 'rede (node:dns)' },
        { pattern: /node:tls/, category: 'rede (node:tls)' },
        { pattern: /node:child_process/, category: 'subprocesso (node:child_process)' },
        { pattern: /node:crypto/, category: 'criptografia/aleatoriedade (node:crypto)' },
    ]

    const forbiddenRuntimeTokens: ReadonlyArray<{ pattern: RegExp; category: string }> = [
        { pattern: /platform\/dist/, category: 'referencia proibida a platform/dist (dinamica ou estatica)' },
        { pattern: /platform\/src/, category: 'referencia proibida a platform/src (dinamica ou estatica)' },
        { pattern: /marcasalao-marketing-platform/, category: 'referencia proibida a marcasalao-marketing-platform' },
        { pattern: /\bfetch\s*\(/, category: 'rede (fetch)' },
        { pattern: /\bXMLHttpRequest\b/, category: 'rede (XMLHttpRequest)' },
        { pattern: /\bDate\.now\b/, category: 'relogio nao deterministico (Date.now)' },
        { pattern: /\bnew\s+Date\b/, category: 'relogio nao deterministico (new Date)' },
        { pattern: /\bMath\.random\b/, category: 'aleatoriedade (Math.random)' },
        { pattern: /\bprocess\.env\b/, category: 'leitura de ambiente (process.env)' },
        { pattern: /\bprocess\.cwd\b/, category: 'leitura de ambiente (process.cwd)' },
        { pattern: /\bconsole\./, category: 'logging via console' },
        { pattern: /\bsetTimeout\b/, category: 'timer nativo (setTimeout)' },
        { pattern: /\bsetInterval\b/, category: 'timer nativo (setInterval)' },
        { pattern: /\brequire\s*\(/, category: 'require dinamico/CommonJS' },
        { pattern: /\b__dirname\b/, category: 'caminho de host (__dirname)' },
        { pattern: /\bOutputPlan\b/, category: 'escopo proibido OutputPlan' },
        { pattern: /\bBeatPlan\b/, category: 'escopo proibido BeatPlan' },
        { pattern: /\bworkflowId\b/, category: 'escopo proibido de Workflow ID (workflowId)' },
        { pattern: /\bWorkflowIdReusePolicy\b/, category: 'escopo proibido WorkflowIdReusePolicy' },
        { pattern: /\bWorkflowIdConflictPolicy\b/, category: 'escopo proibido WorkflowIdConflictPolicy' },
        { pattern: /\bcontentHash\b/, category: 'escopo proibido contentHash' },
        { pattern: /\bsha-?256\b/i, category: 'escopo proibido SHA-256' },
        { pattern: /\bworkflow\.start\b/, category: 'escopo proibido workflow.start' },
    ]

    for (const fileName of WORKFLOW_SLICE_FILES) {
        const filePath = path.join(workflowsSrcDir, fileName)
        assert.equal(existsSync(filePath), true, `${fileName} deve existir em src/workflows/`)

        const raw = readFileSync(filePath, 'utf8')
        const normalizedCode = stripComments(raw).replace(/\\/g, '/')
        const normalizedImports = importLines(raw).map((line) => line.replace(/\\/g, '/'))

        for (const { pattern, category } of forbiddenImports) {
            assert.equal(
                normalizedImports.some((line) => pattern.test(line)),
                false,
                `${fileName} violou fronteira [${category}]: import correspondente a ${pattern}`,
            )
        }

        // Imports de activities devem ser exclusivamente import type
        const activityImports = normalizedImports.filter((line) => /activities\//.test(line))
        for (const line of activityImports) {
            assert.match(
                line,
                /^\s*import\s+type\b/,
                `${fileName} so pode importar Activity como tipo (${line})`,
            )
        }

        for (const { pattern, category } of forbiddenRuntimeTokens) {
            assert.equal(
                pattern.test(normalizedCode),
                false,
                `${fileName} violou fronteira [${category}]: token correspondente a ${pattern}`,
            )
        }
    }
})

test('composition-validation-workflow usa proxyActivities tipado e composition-validation-result permanece livre de Temporal', () => {
    const workflowCode = stripComments(
        readFileSync(path.join(workflowsSrcDir, 'composition-validation-workflow.ts'), 'utf8'),
    )
    assert.match(workflowCode, /proxyActivities<typeof compositionValidationActivities>/)
    assert.match(workflowCode, /import type \* as compositionValidationActivities/)

    const resultImports = importLines(
        readFileSync(path.join(workflowsSrcDir, 'composition-validation-result.ts'), 'utf8'),
    )
    assert.equal(
        resultImports.some((line) => /@temporalio\//.test(line)),
        false,
        'composition-validation-result.ts nao pode importar @temporalio/*',
    )
})

test('Worker e cliente de producao nao foram alterados nem referenciam o novo Workflow', () => {
    for (const subDir of ['worker', 'client', 'local']) {
        for (const file of listTsFiles(path.join(srcDir, subDir))) {
            const raw = readFileSync(file, 'utf8')
            assert.equal(
                raw.includes('validateCompositionWorkflow'),
                false,
                `${path.basename(file)} nao pode referenciar validateCompositionWorkflow`,
            )
            assert.equal(
                raw.includes('composition-validation-workflow'),
                false,
                `${path.basename(file)} nao pode importar composition-validation-workflow`,
            )
        }
    }
})

test('codigo JS compilado do Workflow nao contem imports de platform nem de I/O', () => {
    for (const fileName of WORKFLOW_SLICE_FILES) {
        const jsPath = path.join(builtWorkflowsDir, fileName.replace(/\.ts$/, '.js'))
        assert.equal(existsSync(jsPath), true, `${path.basename(jsPath)} compilado deve existir`)
        const jsCode = readFileSync(jsPath, 'utf8').replace(/\\/g, '/')

        assert.equal(jsCode.includes('marcasalao-marketing-platform'), false)
        assert.equal(jsCode.includes('platform/src'), false)
        assert.equal(jsCode.includes('platform/dist'), false)
        assert.equal(jsCode.includes('composition-validation-activity'), false)
        assert.equal(jsCode.includes('node:fs'), false)
        assert.equal(jsCode.includes('node:http'), false)
        assert.equal(jsCode.includes('node:child_process'), false)
    }
})
