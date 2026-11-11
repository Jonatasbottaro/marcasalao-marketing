/**
 * Infraestrutura compartilhada dos testes de contrato: motor JSON Schema real
 * (ajv), builders de documentos e leituras dos exemplos oficiais. ProjectManifest,
 * Composition e OutputPlan usam o mesmo harness, entao schema e validador
 * TypeScript sempre sao comparados sobre os mesmos objetos.
 *
 * Nada aqui acessa rede nem abre assets além dos exemplos oficiais do modulo.
 */
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { CATALOG_VERSION, OUTPUT_PROFILES } from '../src/output-profiles/catalog.js'
import { validateComposition } from '../src/validate-composition.js'
import { validateOutputPlan } from '../src/validate-output-plan.js'
import { validateProjectManifest } from '../src/validate-project.js'
import type { CompositionValidationReport, OutputPlanReport, ProjectValidationReport } from '../src/validation-report.js'

const testDir = path.dirname(fileURLToPath(import.meta.url))

/** Sobe ate o package.json do modulo: funciona em tests/ e em tests/contracts/. */
export function findModuleRoot(startDir: string): string {
    let current = path.resolve(startDir)
    for (;;) {
        if (existsSync(path.join(current, 'package.json'))) return current
        const parent = path.dirname(current)
        if (parent === current) {
            throw new Error(`package.json do modulo nao encontrado a partir de ${startDir}`)
        }
        current = parent
    }
}

export const moduleRoot = findModuleRoot(testDir)
export const projectsDir = path.join(moduleRoot, 'examples', 'projects')
export const compositionsDir = path.join(moduleRoot, 'examples', 'compositions')

/** Par de exemplo oficial: composicao e o projeto contra o qual ela e validada. */
export const officialPairs: readonly { composition: string; project: string }[] = [
    { composition: 'marca-salao-pilot.composition.json', project: 'marca-salao.project.json' },
    { composition: 'fixture-project-pilot.composition.json', project: 'fixture-project.project.json' },
]

export const B = '\\'
export const NUL = String.fromCharCode(0)

// strict desligado: o espelho normativo usa somente o vocabulario draft-07 e os
// avisos do strict mode dependeriam da versao do motor (saida nao estavel).
// O pacote e CommonJS: o construtor chega pela propriedade `default` do modulo.
const ajv = new AjvModule.default({ allErrors: true, strict: false })

export interface SchemaCheck {
    valid: boolean
    detail: string
}

function compileSchema(file: string): (document: unknown) => SchemaCheck {
    const schema = JSON.parse(readFileSync(path.join(moduleRoot, 'schemas', file), 'utf8')) as AnySchemaObject
    const validate = ajv.compile(schema)
    return (document: unknown): SchemaCheck => {
        const valid = validate(document) === true
        const failures = (validate.errors ?? []).map(
            (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
        )
        return { valid, detail: failures.join(' | ') }
    }
}

export const projectSchemaCheck = compileSchema('project.schema.json')
export const compositionSchemaCheck = compileSchema('composition.schema.json')
export const outputPlanSchemaCheck = compileSchema('output-plan.schema.json')

export function readProjectExample(name: string): Record<string, unknown> {
    return JSON.parse(readFileSync(path.join(projectsDir, name), 'utf8')) as Record<string, unknown>
}

export function readCompositionExample(name: string): Record<string, unknown> {
    return JSON.parse(readFileSync(path.join(compositionsDir, name), 'utf8')) as Record<string, unknown>
}

export function projectWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: 1,
        id: 'projeto-teste',
        name: 'Projeto Teste',
        locale: 'pt-BR',
        timezone: 'America/Sao_Paulo',
        brandTheme: 'tema-teste',
        assetRoot: 'projects/projeto-teste/assets',
        contentPolicies: {
            requireApprovedBriefing: true,
            requireApprovedScript: true,
            prohibitPersonalData: true,
            requireFunctionalEvidence: true,
        },
        outputProfiles: ['vertical-social'],
        ...overrides,
    }
}

export const safeAsset = { id: 'tela-01', path: 'projects/projeto-teste/assets/tela-01.png' }

export function sceneWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        id: 'opening',
        type: 'text',
        durationMs: 3000,
        content: { text: 'Texto de teste.' },
        ...overrides,
    }
}

export function withoutFields(value: Record<string, unknown>, keys: string[]): Record<string, unknown> {
    const copy = { ...value }
    for (const key of keys) delete copy[key]
    return copy
}

export function compositionWithScenes(
    scenes: readonly Record<string, unknown>[],
    overrides: Record<string, unknown> = {},
): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        id: 'comp-contrato',
        title: 'Composicao Contrato',
        locale: 'pt-BR',
        format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
        scenes: [...scenes],
        renderer: { adapter: 'undecided' },
        ...overrides,
    }
}

export function compositionWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return compositionWithScenes([sceneWith()], overrides)
}

/** Composicao de uma unica cena image, cujo asset.path recebe o valor testado. */
export function compositionWithAssetPath(assetPath: unknown): Record<string, unknown> {
    return compositionWithScenes([
        sceneWith({ type: 'image', content: { asset: { id: 'tela-01', path: assetPath } } }),
    ])
}

/** Composicao de uma unica cena cta, cujo content.href recebe o valor testado. */
export function compositionWithHref(href: unknown): Record<string, unknown> {
    return compositionWithScenes([
        sceneWith({ type: 'cta', content: { text: 'Conheca o sistema.', href } }),
    ])
}

/** Manifesto com um valor especifico em assetRoot. */
export function manifestWithAssetRoot(assetRoot: unknown): Record<string, unknown> {
    return projectWith({ assetRoot })
}

/**
 * Composicao que coloca `value` no campo textual pedido — no topo (title/locale)
 * ou no content da cena adequada ao campo (text, alt, accessibilityLabel).
 */
export function compositionWithTextField(
    field: 'title' | 'locale' | 'text' | 'accessibilityLabel' | 'alt',
    value: unknown,
): Record<string, unknown> {
    if (field === 'title' || field === 'locale') {
        return compositionWith({ [field]: value })
    }
    if (field === 'alt') {
        return compositionWithScenes([sceneWith({ type: 'image', content: { asset: safeAsset, alt: value } })])
    }
    if (field === 'text') {
        return compositionWithScenes([sceneWith({ content: { text: value } })])
    }
    return compositionWithScenes([sceneWith({ content: { text: 'Abertura.', accessibilityLabel: value } })])
}

export function projectCodes(report: ProjectValidationReport): string[] {
    return report.errors.map((error) => error.code)
}

export function compositionCodes(report: CompositionValidationReport): string[] {
    return report.errors.map((error) => error.code)
}

export function compositionWarningCodes(report: CompositionValidationReport): string[] {
    return report.warnings.map((warning) => warning.code)
}

export function validateProjectDocument(document: unknown): ProjectValidationReport {
    return validateProjectManifest(document)
}

export function validateCompositionDocument(
    document: unknown,
    project: unknown = projectWith(),
): CompositionValidationReport {
    return validateComposition(document, project)
}

/**
 * Projeto tecnico de teste que permite os doze perfis do catalogo. `brandTheme`,
 * `locale` e `assetRoot` continuam opacos: nada aqui depende de marca.
 */
export function catalogProject(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return projectWith({
        outputProfiles: OUTPUT_PROFILES.map((profile) => profile.id),
        ...overrides,
    })
}

/**
 * Revisao atual do perfil no catalogo. Builders de documento valido nao podem
 * carregar numero de revisao proprio: o que fixa a revisao e o registro, e o
 * teste hostil sobrescreve explicitamente (`{ profileRevision: 9 }`).
 */
export function catalogProfileRevision(profileId: string): number {
    const profile = OUTPUT_PROFILES.find((item) => item.id === profileId)
    if (profile === undefined) {
        throw new Error(`perfil "${profileId}" nao existe no catalogo`)
    }
    return profile.revision
}

/**
 * Plano canonico de video (youtube-shorts). Builders de teste recebem entrada
 * hostil: a ordem canonica de §6.1 e garantia do resolvedor, nao destes builders.
 */
export function videoPlanWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        catalogVersion: CATALOG_VERSION,
        profileId: 'youtube-shorts',
        profileRevision: catalogProfileRevision('youtube-shorts'),
        mediaKind: 'video',
        video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30 },
        ...overrides,
    }
}

/** Builder de plano de imagem (instagram-stories-image). */
export function imagePlanWith(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        catalogVersion: CATALOG_VERSION,
        profileId: 'instagram-stories-image',
        profileRevision: catalogProfileRevision('instagram-stories-image'),
        mediaKind: 'image',
        image: { width: 1080, height: 1920, aspectRatio: '9:16' },
        ...overrides,
    }
}

export function validateOutputPlanDocument(
    document: unknown,
    project: unknown = catalogProject(),
): OutputPlanReport {
    return validateOutputPlan(document, project)
}

export function outputPlanCodes(report: OutputPlanReport): string[] {
    return report.errors.map((error) => error.code)
}

export function outputPlanWarningCodes(report: OutputPlanReport): string[] {
    return report.warnings.map((warning) => warning.code)
}
