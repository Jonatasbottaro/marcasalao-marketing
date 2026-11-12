/**
 * Testes da fronteira publica minima da platform (TEMPORAL-02-01).
 *
 * Verifica a superficie publica de `composition-validation-api`, a guarda de
 * exports em runtime e em tipos, a identidade referencial e paridade total com
 * `validateComposition` interno e a preservacao da ordem dos argumentos
 * `validateComposition(composition, project)`.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import {
    existsSync,
    lstatSync,
    mkdirSync,
    mkdtempSync,
    readFileSync,
    readdirSync,
    realpathSync,
    rmSync,
    symlinkSync,
    writeFileSync,
    type Dirent,
} from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'

import * as publicApi from '../src/composition-validation-api.js'
import {
    validateComposition,
    type Composition,
    type CompositionValidationReport,
    type ProjectManifest,
} from '../src/composition-validation-api.js'
import type { Composition as InternalComposition } from '../src/composition-contract.js'
import type { ProjectManifest as InternalProjectManifest } from '../src/project-contract.js'
import { validateComposition as internalValidateComposition } from '../src/validate-composition.js'
import type { CompositionValidationReport as InternalCompositionValidationReport } from '../src/validation-report.js'
import { semanticCases, structuralCompositionCases } from './contract-corpus.js'
import {
    moduleRoot,
    officialPairs,
    projectWith,
    readCompositionExample,
    readProjectExample,
} from './contract-harness.js'

type Equals<A, B> = (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2 ? true : false
type Assert<T extends true> = T

// Assercoes em tempo de compilacao: os tipos reexportados pela fronteira publica
// sao identicos aos tipos canonicos internos, sem duplicacao de contrato.
type PublicCompositionMatchesInternal = Assert<Equals<Composition, InternalComposition>>
type PublicProjectManifestMatchesInternal = Assert<Equals<ProjectManifest, InternalProjectManifest>>
type PublicReportMatchesInternal = Assert<
    Equals<CompositionValidationReport, InternalCompositionValidationReport>
>
type PublicValidatorSignatureMatchesInternal = Assert<
    Equals<typeof validateComposition, typeof internalValidateComposition>
>

const typeLevelAssertions: readonly [
    PublicCompositionMatchesInternal,
    PublicProjectManifestMatchesInternal,
    PublicReportMatchesInternal,
    PublicValidatorSignatureMatchesInternal,
] = [true, true, true, true]

test('guarda de exports publicos: expoe apenas validateComposition em runtime e nenhum simbolo extra', () => {
    const exportedKeys = new Set(Object.keys(publicApi))
    assert.deepEqual(
        exportedKeys,
        new Set(['validateComposition']),
        `superficie publica inesperada: ${JSON.stringify([...exportedKeys])}`,
    )
    assert.equal(typeof publicApi.validateComposition, 'function')
    assert.equal(typeLevelAssertions.length, 4)

    const forbiddenRuntimeSymbols = [
        'Composition',
        'ProjectManifest',
        'CompositionValidationReport',
        'validateProjectManifest',
        'inspectRelativePath',
        'containsControlCharacter',
        'OutputPlan',
        'BeatPlan',
        'validateCompositionActivity',
        'validateCompositionWorkflow',
    ]
    for (const symbolName of forbiddenRuntimeSymbols) {
        assert.equal(
            Object.prototype.hasOwnProperty.call(publicApi, symbolName),
            false,
            `simbolo "${symbolName}" nao pode existir em runtime no entrypoint publico`,
        )
    }
})

test('entrypoint reexporta a mesma funcao validateComposition sem wrapper nem reimplementacao', () => {
    assert.equal(validateComposition, internalValidateComposition)
    assert.equal(publicApi.validateComposition, internalValidateComposition)
})

test('paridade: chamada pelo entrypoint produz exatamente o mesmo relatorio do modulo interno', () => {
    for (const pair of officialPairs) {
        const composition = readCompositionExample(pair.composition)
        const project = readProjectExample(pair.project)

        const fromPublic = validateComposition(composition, project)
        const fromInternal = internalValidateComposition(composition, project)

        assert.deepEqual(fromPublic, fromInternal)
        assert.equal(fromPublic.valid, true)
        assert.equal(fromPublic.valid, fromInternal.valid)
        assert.deepEqual(fromPublic.errors, fromInternal.errors)
        assert.deepEqual(fromPublic.warnings, fromInternal.warnings)
        assert.equal(fromPublic.summary, fromInternal.summary)
        assert.equal(fromPublic.projectId, fromInternal.projectId)
        assert.equal(fromPublic.compositionId, fromInternal.compositionId)
        assert.equal(fromPublic.schemaVersion, fromInternal.schemaVersion)
        assert.equal(fromPublic.sceneCount, fromInternal.sceneCount)
        assert.equal(fromPublic.totalDurationMs, fromInternal.totalDurationMs)
        assert.deepEqual(fromPublic.format, fromInternal.format)
        assert.equal(fromPublic.rendererAdapter, fromInternal.rendererAdapter)
    }

    const baseProject = projectWith()
    for (const caseItem of structuralCompositionCases.slice(0, 15)) {
        const fromPublic = validateComposition(caseItem.document, baseProject)
        const fromInternal = internalValidateComposition(caseItem.document, baseProject)
        assert.deepEqual(fromPublic, fromInternal, `divergencia em caso estrutural "${caseItem.name}"`)
    }

    for (const caseItem of semanticCases) {
        const fromPublic = validateComposition(caseItem.document, caseItem.project)
        const fromInternal = internalValidateComposition(caseItem.document, caseItem.project)
        assert.deepEqual(fromPublic, fromInternal, `divergencia em caso semantico "${caseItem.name}"`)
    }
})

test('ordem dos argumentos: Composition primeiro e ProjectManifest depois; inversao nao e equivalente', () => {
    for (const pair of officialPairs) {
        const composition = readCompositionExample(pair.composition)
        const project = readProjectExample(pair.project)

        const correctOrder = validateComposition(composition, project)
        assert.equal(correctOrder.valid, true)
        assert.deepEqual(correctOrder.errors, [])

        const invertedOrder = validateComposition(project, composition)
        assert.equal(invertedOrder.valid, false, 'ordem invertida (project, composition) deve ser invalida')
        assert.notDeepEqual(invertedOrder, correctOrder)
        assert.ok(
            invertedOrder.errors.some((err) => err.code === 'COMPOSITION_MANIFEST_INVALID'),
            'ordem invertida deve acusar COMPOSITION_MANIFEST_INVALID no segundo argumento',
        )
        assert.deepEqual(
            invertedOrder,
            internalValidateComposition(project, composition),
            'entrypoint nao deve alterar o comportamento na inversao de argumentos',
        )
    }
})

interface PlatformPackageJson {
    name?: string
    private?: boolean
    type?: string
    main?: string
    types?: string
    exports?: {
        '.'?: {
            types?: string
            import?: string
        }
        [subpath: string]: unknown
    }
    files?: string[]
    dependencies?: Record<string, string>
    devDependencies?: Record<string, string>
}

function readPlatformPackageJson(): PlatformPackageJson {
    return JSON.parse(readFileSync(path.join(moduleRoot, 'package.json'), 'utf8')) as PlatformPackageJson
}

function resolveNpmCli(): string {
    const fromEnv = process.env.npm_execpath
    if (fromEnv && existsSync(fromEnv)) return fromEnv
    const execDir = path.dirname(process.execPath)
    const candidates = [
        path.join(execDir, 'node_modules', 'npm', 'bin', 'npm-cli.js'),
        path.join(execDir, '..', 'lib', 'node_modules', 'npm', 'bin', 'npm-cli.js'),
    ]
    for (const candidate of candidates) {
        if (existsSync(candidate)) return candidate
    }
    throw new Error('npm-cli.js nao localizado a partir de process.execPath')
}

test('package.json e artefatos de build declaram entrypoint publico compilado e declaracoes TypeScript', () => {
    const pkg = readPlatformPackageJson()

    assert.equal(pkg.name, 'marcasalao-marketing-platform')
    assert.equal(pkg.private, true)
    assert.equal(pkg.type, 'module')
    assert.equal(pkg.main, './dist/src/composition-validation-api.js')
    assert.equal(pkg.types, './dist/src/composition-validation-api.d.ts')
    assert.deepEqual(pkg.exports, {
        '.': {
            types: './dist/src/composition-validation-api.d.ts',
            import: './dist/src/composition-validation-api.js',
        },
    })
    assert.ok(Array.isArray(pkg.files) && pkg.files.includes('dist/src'))

    const compiledJs = path.join(moduleRoot, 'dist', 'src', 'composition-validation-api.js')
    const compiledDts = path.join(moduleRoot, 'dist', 'src', 'composition-validation-api.d.ts')
    assert.ok(existsSync(compiledJs), 'JavaScript compilado do entrypoint deve existir em dist/src/')
    assert.ok(existsSync(compiledDts), 'declaracao TypeScript (.d.ts) do entrypoint deve existir em dist/src/')

    const dtsContent = readFileSync(compiledDts, 'utf8')
    assert.match(dtsContent, /validateComposition/)
    assert.match(dtsContent, /CompositionValidationReport/)
    assert.match(dtsContent, /ProjectManifest/)
    assert.match(dtsContent, /Composition\b/)
})

test('fronteira limpa: platform permanece sem dependencia de runtime, sem @temporalio e sem orchestration', () => {
    const pkg = readPlatformPackageJson()
    assert.equal(pkg.dependencies, undefined)

    const allDeps = [
        ...Object.keys(pkg.dependencies ?? {}),
        ...Object.keys(pkg.devDependencies ?? {}),
    ]
    for (const dep of allDeps) {
        assert.ok(!dep.startsWith('@temporalio'), `dependencia Temporal proibida na platform: ${dep}`)
    }

    const srcDir = path.join(moduleRoot, 'src')
    const srcDirReal = realpathSync(srcDir)
    const moduleRootReal = realpathSync(moduleRoot)
    for (const filePath of collectSourceFiles(srcDir)) {
        assert.ok(isWithinRoot(srcDirReal, filePath, true), `arquivo fora de platform/src: ${filePath}`)
        const relativePath = path.relative(moduleRootReal, filePath).replace(/\\/g, '/')
        const content = readFileSync(filePath, 'utf8')
        assert.ok(!content.includes('@temporalio'), `import @temporalio proibido em ${relativePath}`)
        assert.ok(!content.includes('orchestration'), `referencia a orchestration proibida em ${relativePath}`)
    }
})

const IGNORED_SOURCE_DIRS = new Set(['node_modules', 'dist'])

function isWithinRoot(rootReal: string, candidateReal: string, expectFile: boolean): boolean {
    const relative = path.relative(rootReal, candidateReal)
    if (expectFile && relative === '') return false
    if (relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) return false
    return true
}

/**
 * Varredura recursiva deterministica restrita ao root informado: ordena entradas,
 * ignora symlinks (arquivo ou diretorio), exclui defensivamente dist/ e node_modules/
 * e garante confinamento de caminho real dentro de rootReal.
 */
function collectSourceFiles(
    rootDirectory: string,
    readEntries: (directory: string) => readonly Dirent[] = (directory) => readdirSync(directory, { withFileTypes: true }),
): string[] {
    const rootReal = realpathSync(rootDirectory)

    function walk(currentDirectory: string): string[] {
        const entries = readEntries(currentDirectory)
            .slice()
            .sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0))

        const collected: string[] = []
        for (const entry of entries) {
            if (entry.isSymbolicLink()) continue

            const entryPath = path.join(currentDirectory, entry.name)
            if (lstatSync(entryPath).isSymbolicLink()) continue

            const candidateReal = realpathSync(entryPath)

            if (entry.isDirectory()) {
                if (IGNORED_SOURCE_DIRS.has(entry.name)) continue
                if (!isWithinRoot(rootReal, candidateReal, false)) continue
                collected.push(...walk(candidateReal))
                continue
            }

            if (entry.isFile()) {
                if (!isWithinRoot(rootReal, candidateReal, true)) continue
                collected.push(candidateReal)
            }
        }
        return collected
    }

    return walk(rootReal)
}

function createSymlinkOrSkip(
    t: { skip: (message?: string) => void },
    target: string,
    linkPath: string,
    type: 'file' | 'dir',
): boolean {
    try {
        symlinkSync(target, linkPath, type)
        return true
    } catch (error: unknown) {
        const code = error && typeof error === 'object' && 'code' in error ? String(error.code) : ''
        if (process.platform === 'win32' && (code === 'EPERM' || code === 'EACCES' || code === 'ENOTSUP')) {
            t.skip(`criacao de symlink indisponivel neste Windows (${code})`)
            return false
        }
        throw error
    }
}

test('collectSourceFiles ordena de forma deterministica, ignora dist/node_modules e confina ao root', () => {
    const tempRoot = mkdtempSync(path.join(os.tmpdir(), 'platform-collect-guard-'))
    const scanRoot = path.join(tempRoot, 'src')
    const subDir = path.join(scanRoot, 'nested')
    const distDir = path.join(scanRoot, 'dist')
    const nodeModulesDir = path.join(scanRoot, 'node_modules', 'pkg')

    try {
        mkdirSync(subDir, { recursive: true })
        mkdirSync(distDir, { recursive: true })
        mkdirSync(nodeModulesDir, { recursive: true })

        writeFileSync(path.join(scanRoot, 'zeta.ts'), 'export const z = 1\n', 'utf8')
        writeFileSync(path.join(scanRoot, 'alpha.ts'), 'export const a = 1\n', 'utf8')
        writeFileSync(path.join(subDir, 'second.ts'), 'export const s = 2\n', 'utf8')
        writeFileSync(path.join(subDir, 'first.ts'), 'export const f = 1\n', 'utf8')
        writeFileSync(path.join(distDir, 'compiled.js'), '// @temporalio\n', 'utf8')
        writeFileSync(path.join(nodeModulesDir, 'dep.js'), '// orchestration\n', 'utf8')

        const rootReal = realpathSync(scanRoot)
        const files = collectSourceFiles(scanRoot)
        const reversedFsFiles = collectSourceFiles(scanRoot, (dir) =>
            readdirSync(dir, { withFileTypes: true }).reverse(),
        )
        const relativeFiles = files.map((filePath) => path.relative(rootReal, filePath).replace(/\\/g, '/'))
        const relativeReversed = reversedFsFiles.map((filePath) =>
            path.relative(rootReal, filePath).replace(/\\/g, '/'),
        )

        assert.deepEqual(
            relativeFiles,
            ['alpha.ts', 'nested/first.ts', 'nested/second.ts', 'zeta.ts'],
            'varredura deve ordenar entradas de modo deterministico e ignorar dist/ e node_modules/',
        )
        assert.deepEqual(
            relativeReversed,
            relativeFiles,
            'ordem final nao pode depender da ordem devolvida pelo filesystem',
        )

        for (const filePath of files) {
            const candidateReal = realpathSync(filePath)
            assert.ok(isWithinRoot(rootReal, candidateReal, true), `caminho externo ao root alcancado: ${filePath}`)
        }

        assert.equal(isWithinRoot(rootReal, rootReal, true), false, 'arquivo esperado nao pode coincidir com o proprio root')
        assert.equal(isWithinRoot(rootReal, realpathSync(tempRoot), true), false, 'caminho pai deve ser rejeitado')
    } finally {
        rmSync(tempRoot, { recursive: true, force: true })
    }
})

test('collectSourceFiles ignora symlink de arquivo apontando para fora do root', (t) => {
    const tempRoot = mkdtempSync(path.join(os.tmpdir(), 'platform-collect-symlink-file-'))
    const scanRoot = path.join(tempRoot, 'src')
    const outsideDir = path.join(tempRoot, 'outside')
    const outsideFile = path.join(outsideDir, 'secret-orchestration.ts')
    const insideFile = path.join(scanRoot, 'safe.ts')
    const symlinkFile = path.join(scanRoot, 'escape-link.ts')

    try {
        mkdirSync(scanRoot, { recursive: true })
        mkdirSync(outsideDir, { recursive: true })
        writeFileSync(insideFile, 'export const safe = true\n', 'utf8')
        writeFileSync(outsideFile, "import '@temporalio/workflow'\n// orchestration\n", 'utf8')

        if (!createSymlinkOrSkip(t, outsideFile, symlinkFile, 'file')) return

        const rootReal = realpathSync(scanRoot)
        const files = collectSourceFiles(scanRoot)
        const relativeFiles = files.map((filePath) => path.relative(rootReal, filePath).replace(/\\/g, '/'))

        assert.deepEqual(
            relativeFiles,
            ['safe.ts'],
            `symlink de arquivo externo foi listado/alcancado pela varredura: ${JSON.stringify(relativeFiles)}`,
        )
    } finally {
        rmSync(tempRoot, { recursive: true, force: true })
    }
})

test('collectSourceFiles ignora symlink de diretorio apontando para fora do root', (t) => {
    const tempRoot = mkdtempSync(path.join(os.tmpdir(), 'platform-collect-symlink-dir-'))
    const scanRoot = path.join(tempRoot, 'src')
    const outsideDir = path.join(tempRoot, 'outside-dir')
    const outsideFile = path.join(outsideDir, 'leak.ts')
    const insideFile = path.join(scanRoot, 'safe.ts')
    const symlinkDir = path.join(scanRoot, 'linked-outside')

    try {
        mkdirSync(scanRoot, { recursive: true })
        mkdirSync(outsideDir, { recursive: true })
        writeFileSync(insideFile, 'export const safe = true\n', 'utf8')
        writeFileSync(outsideFile, "import '@temporalio/activity'\n// orchestration\n", 'utf8')

        if (!createSymlinkOrSkip(t, outsideDir, symlinkDir, 'dir')) return

        const rootReal = realpathSync(scanRoot)
        const files = collectSourceFiles(scanRoot)
        const relativeFiles = files.map((filePath) => path.relative(rootReal, filePath).replace(/\\/g, '/'))

        assert.deepEqual(
            relativeFiles,
            ['safe.ts'],
            `symlink de diretorio externo foi listado/alcancado pela varredura: ${JSON.stringify(relativeFiles)}`,
        )
    } finally {
        rmSync(tempRoot, { recursive: true, force: true })
    }
})

test('empacotamento e consumidor externo: npm pack gera pacote consumivel pelo nome publico com tipos validos', () => {
    const npmCli = resolveNpmCli()
    const tscCli = path.join(moduleRoot, 'node_modules', 'typescript', 'bin', 'tsc')
    assert.ok(existsSync(tscCli), 'binario JS do TypeScript deve existir em node_modules')

    const tempRoot = mkdtempSync(path.join(os.tmpdir(), 'platform-pack-consumer-'))
    const packDir = path.join(tempRoot, 'pack')
    const consumerDir = path.join(tempRoot, 'consumer')

    try {
        // 1. Empacota o pacote compilado em diretorio temporario fora do repositorio.
        const packDryRun = spawnSync(
            process.execPath,
            [npmCli, 'pack', '--dry-run', '--json'],
            { cwd: moduleRoot, encoding: 'utf8' },
        )
        assert.equal(packDryRun.status, 0, `npm pack --dry-run falhou: ${packDryRun.stderr}`)

        const packInfo = JSON.parse(packDryRun.stdout) as Array<{
            files?: Array<{ path: string }>
        }>
        const packedPaths = (packInfo[0]?.files ?? []).map((entry) => entry.path.replace(/\\/g, '/'))

        assert.ok(packedPaths.includes('package.json'))
        assert.ok(packedPaths.includes('dist/src/composition-validation-api.js'))
        assert.ok(packedPaths.includes('dist/src/composition-validation-api.d.ts'))
        for (const packedPath of packedPaths) {
            assert.ok(!packedPath.startsWith('src/'), `codigo-fonte TS nao deve entrar no pacote: ${packedPath}`)
            assert.ok(!packedPath.startsWith('tests/'), `testes TS nao devem entrar no pacote: ${packedPath}`)
            assert.ok(!packedPath.startsWith('dist/tests/'), `testes compilados nao devem entrar no pacote: ${packedPath}`)
            assert.ok(!packedPath.startsWith('examples/'), `exemplos nao devem entrar no pacote: ${packedPath}`)
            assert.ok(!packedPath.endsWith('-cli.js'), `CLIs nao devem entrar no pacote: ${packedPath}`)
            assert.ok(!packedPath.endsWith('-cli.d.ts'), `declaracoes de CLI nao devem entrar no pacote: ${packedPath}`)
        }

        const packReal = spawnSync(
            process.execPath,
            [npmCli, 'pack', '--pack-destination', tempRoot, '--silent'],
            { cwd: moduleRoot, encoding: 'utf8' },
        )
        assert.equal(packReal.status, 0, `npm pack falhou: ${packReal.stderr}`)
        const tarballName = packReal.stdout.trim().split(/\r?\n/).pop() ?? ''
        assert.ok(tarballName.endsWith('.tgz'), `esperado arquivo .tgz, obtido "${tarballName}"`)
        const tarballPath = path.join(tempRoot, tarballName)
        assert.ok(existsSync(tarballPath), 'tarball gerado deve existir no diretorio temporario')

        // 2. Cria consumidor externo temporario fora do repositorio e instala o tarball.
        rmSync(packDir, { recursive: true, force: true })
        writeFileSync(
            path.join(tempRoot, 'package.json'),
            JSON.stringify({ name: 'external-boundary-consumer', private: true, type: 'module' }, null, 2),
            'utf8',
        )

        const installResult = spawnSync(
            process.execPath,
            [
                npmCli,
                'install',
                tarballPath,
                '--no-save',
                '--no-package-lock',
                '--ignore-scripts',
                '--no-audit',
                '--no-fund',
            ],
            { cwd: tempRoot, encoding: 'utf8' },
        )
        assert.equal(installResult.status, 0, `npm install do tarball falhou: ${installResult.stderr}`)

        // 3. Escreve consumidor TypeScript que importa APENAS pelo nome publico do pacote.
        const consumerTsPath = path.join(tempRoot, 'consumer.ts')
        const consumerJsPath = path.join(tempRoot, 'consumer.js')
        const consumerTsCode = [
            "import * as pkg from 'marcasalao-marketing-platform'",
            "import {",
            "    validateComposition,",
            "    type Composition,",
            "    type CompositionValidationReport,",
            "    type ProjectManifest,",
            "} from 'marcasalao-marketing-platform'",
            '',
            'const typedProject: ProjectManifest = {',
            '    schemaVersion: 1,',
            "    id: 'marca-salao',",
            "    name: 'Marca Salao',",
            "    locale: 'pt-BR',",
            "    timezone: 'America/Sao_Paulo',",
            "    brandTheme: 'marca-salao-default',",
            "    assetRoot: 'projects/marca-salao/assets',",
            '    contentPolicies: {',
            '        requireApprovedBriefing: true,',
            '        requireApprovedScript: true,',
            '        prohibitPersonalData: true,',
            '        requireFunctionalEvidence: true,',
            '    },',
            "    outputProfiles: ['vertical-social'],",
            '}',
            '',
            'const typedComposition: Composition = {',
            '    schemaVersion: 1,',
            "    projectId: 'marca-salao',",
            "    id: 'pilot-composition',",
            "    title: 'Organizacao e visibilidade da agenda',",
            "    locale: 'pt-BR',",
            "    format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },",
            '    scenes: [',
            "        { id: 'hook', type: 'text', durationMs: 3000, content: { text: 'Texto.' } },",
            '    ],',
            "    renderer: { adapter: 'undecided' },",
            '}',
            '',
            'const invalidSceneComposition: Composition = {',
            '    ...typedComposition,',
            '    scenes: [',
            '        // @ts-expect-error consumidor externo recebe discriminacao estrita de Composition',
            "        { id: 'invalida', type: 'text', durationMs: 2000, content: { asset: { id: 'a', path: 'a.png' } } },",
            '    ],',
            '}',
            'void invalidSceneComposition',
            '',
            'const report: CompositionValidationReport = validateComposition(typedComposition, typedProject)',
            'void report',
            'void pkg',
        ].join('\n')
        writeFileSync(consumerTsPath, consumerTsCode, 'utf8')

        const consumerTsconfigPath = path.join(tempRoot, 'tsconfig.json')
        writeFileSync(
            consumerTsconfigPath,
            JSON.stringify(
                {
                    compilerOptions: {
                        target: 'ES2022',
                        lib: ['ES2023'],
                        module: 'NodeNext',
                        moduleResolution: 'NodeNext',
                        strict: true,
                        noEmit: true,
                        verbatimModuleSyntax: true,
                        skipLibCheck: false,
                    },
                    include: ['consumer.ts'],
                },
                null,
                2,
            ),
            'utf8',
        )

        // 4. Verifica resolucao dos tipos publicos pelo TypeScript no consumidor externo.
        const tscResult = spawnSync(
            process.execPath,
            [tscCli, '-p', consumerTsconfigPath],
            { cwd: tempRoot, encoding: 'utf8' },
        )
        assert.equal(
            tscResult.status,
            0,
            `tsc falhou no consumidor externo:\nstdout: ${tscResult.stdout}\nstderr: ${tscResult.stderr}`,
        )

        // 5. Executa o consumidor em runtime no Node 22 usando o exemplo integrado real.
        const marcaSalaoComposition = readCompositionExample('marca-salao-pilot.composition.json')
        const marcaSalaoProject = readProjectExample('marca-salao.project.json')
        const fixtureComposition = readCompositionExample('fixture-project-pilot.composition.json')
        const fixtureProject = readProjectExample('fixture-project.project.json')

        const runtimeScript = [
            "import assert from 'node:assert/strict'",
            "import * as pkg from 'marcasalao-marketing-platform'",
            "import { validateComposition } from 'marcasalao-marketing-platform'",
            '',
            `const marcaComposition = ${JSON.stringify(marcaSalaoComposition)}`,
            `const marcaProject = ${JSON.stringify(marcaSalaoProject)}`,
            `const fixtureComposition = ${JSON.stringify(fixtureComposition)}`,
            `const fixtureProject = ${JSON.stringify(fixtureProject)}`,
            '',
            "assert.deepEqual(Object.keys(pkg), ['validateComposition'])",
            'const marcaReport = validateComposition(marcaComposition, marcaProject)',
            'const fixtureReport = validateComposition(fixtureComposition, fixtureProject)',
            'const invertedReport = validateComposition(marcaProject, marcaComposition)',
            '',
            'let subpathBlocked = false',
            'try {',
            "    await import('marcasalao-marketing-platform/dist/src/validate-composition.js')",
            '} catch (err) {',
            "    subpathBlocked = (err && typeof err === 'object' && 'code' in err && err.code === 'ERR_PACKAGE_PATH_NOT_EXPORTED')",
            '}',
            '',
            'let executionPackageSubpathBlocked = false',
            'try {',
            "    await import('marcasalao-marketing-platform/dist/src/creative-execution-package-contract.js')",
            '} catch (err) {',
            "    executionPackageSubpathBlocked = (err && typeof err === 'object' && 'code' in err && err.code === 'ERR_PACKAGE_PATH_NOT_EXPORTED')",
            '}',
            '',
            'let simulatedExecutionSubpathBlocked = false',
            'try {',
            "    await import('marcasalao-marketing-platform/dist/src/simulated-execution-plan-contract.js')",
            '} catch (err) {',
            "    simulatedExecutionSubpathBlocked = (err && typeof err === 'object' && 'code' in err && err.code === 'ERR_PACKAGE_PATH_NOT_EXPORTED')",
            '}',
            '',
            'process.stdout.write(JSON.stringify({ marcaReport, fixtureReport, invertedReport, subpathBlocked, executionPackageSubpathBlocked, simulatedExecutionSubpathBlocked }))',
        ].join('\n')
        writeFileSync(consumerJsPath, runtimeScript, 'utf8')

        const nodeRun = spawnSync(process.execPath, [consumerJsPath], {
            cwd: tempRoot,
            encoding: 'utf8',
        })
        assert.equal(
            nodeRun.status,
            0,
            `execucao do consumidor externo falhou:\nstdout: ${nodeRun.stdout}\nstderr: ${nodeRun.stderr}`,
        )

        const output = JSON.parse(nodeRun.stdout) as {
            marcaReport: CompositionValidationReport
            fixtureReport: CompositionValidationReport
            invertedReport: CompositionValidationReport
            subpathBlocked: boolean
            executionPackageSubpathBlocked: boolean
            simulatedExecutionSubpathBlocked: boolean
        }

        assert.deepEqual(
            output.marcaReport,
            internalValidateComposition(marcaSalaoComposition, marcaSalaoProject),
        )
        assert.deepEqual(
            output.fixtureReport,
            internalValidateComposition(fixtureComposition, fixtureProject),
        )
        assert.equal(output.invertedReport.valid, false)
        assert.deepEqual(
            output.invertedReport,
            internalValidateComposition(marcaSalaoProject, marcaSalaoComposition),
        )
        assert.equal(
            output.subpathBlocked,
            true,
            'imports de modulos internos por subpath devem ser bloqueados pelo campo exports',
        )
        assert.equal(
            output.executionPackageSubpathBlocked,
            true,
            'subpaths do CreativeExecutionPackage devem responder ERR_PACKAGE_PATH_NOT_EXPORTED',
        )
        assert.equal(
            output.simulatedExecutionSubpathBlocked,
            true,
            'subpaths do executor simulado devem responder ERR_PACKAGE_PATH_NOT_EXPORTED',
        )
        void consumerDir
    } finally {
        rmSync(tempRoot, { recursive: true, force: true })
    }
})
