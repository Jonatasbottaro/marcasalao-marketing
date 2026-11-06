/**
 * Discriminacao de cena no nivel de tipos.
 *
 * `CompositionScene` e uma uniao discriminada por `type`, entao combinacoes
 * invalidas de type/content sao rejeitadas na compilacao. As sentencas marcadas
 * com `@ts-expect-error` sao o teste: se o TypeScript deixar de rejeitar alguma
 * delas, a diretiva fica nao-usada, `tsc` falha e `npm run build`/`typecheck`
 * quebra. Nada aqui usa `any`, `@ts-ignore` ou relaxa `strict`.
 *
 * A metade em tempo de execução confere que os tipos, o mapa de campos permitidos
 * e o schema draft-07 descrevem o mesmo conjunto de cenas.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE,
    COMPOSITION_SCENE_TYPES,
    type AssetReference,
    type Composition,
    type CompositionContentFields,
    type CompositionCtaScene,
    type CompositionImageScene,
    type CompositionMediaContent,
    type CompositionScene,
    type CompositionSceneOfType,
    type CompositionSceneType,
    type CompositionTextScene,
    type CompositionVideoScene,
} from '../../src/composition-contract.js'
import type { ProjectManifest } from '../../src/project-contract.js'
import { validateComposition } from '../../src/validate-composition.js'
import { moduleRoot } from '../contract-harness.js'

const asset: AssetReference = { id: 'tela-01', path: 'projects/projeto-teste/assets/tela-01.png' }

/** Content de midia declarado no proprio tipo, para testar o intercambio entre ramos. */
const mediaContent: CompositionMediaContent = { asset }

// ---------------------------------------------------------------------------
// Combinacoes validas: precisam compilar.
// ---------------------------------------------------------------------------

const textScene: CompositionTextScene = {
    id: 'abertura',
    type: 'text',
    durationMs: 2000,
    content: { text: 'Abertura.', accessibilityLabel: 'Abertura falada.' },
}

const imageScene: CompositionImageScene = {
    id: 'tela',
    type: 'image',
    durationMs: 2000,
    content: { asset, alt: 'Agenda do salao.', accessibilityLabel: 'Imagem da agenda.' },
}

const videoScene: CompositionVideoScene = {
    id: 'demo',
    type: 'video',
    durationMs: 2000,
    content: { asset },
}

const ctaScene: CompositionCtaScene = {
    id: 'chamada',
    type: 'cta',
    durationMs: 2000,
    content: { text: 'Conheca o sistema.', href: 'https://example.com.br' },
}

/** As quatro cenas convivem na mesma composicao tipada. */
const typedComposition: Composition = {
    schemaVersion: 1,
    projectId: 'projeto-teste',
    id: 'comp-tipada',
    title: 'Composicao Tipada',
    locale: 'pt-BR',
    format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30 },
    scenes: [textScene, imageScene, videoScene, ctaScene],
    renderer: { adapter: 'undecided' },
    metadata: { status: 'approved', description: 'Fixture tipada.', tags: ['contrato'] },
}

const typedManifest: ProjectManifest = {
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
}

// ---------------------------------------------------------------------------
// Combinacoes invalidas: o TypeScript precisa rejeitar cada linha marcada.
// ---------------------------------------------------------------------------

const textWithAsset: CompositionTextScene = {
    id: 'a',
    type: 'text',
    durationMs: 1000,
    // @ts-expect-error cena "text" nao aceita content.asset
    content: { text: 'Abertura.', asset },
}

const textWithHref: CompositionTextScene = {
    id: 'a',
    type: 'text',
    durationMs: 1000,
    // @ts-expect-error href e proprio de cena "cta"
    content: { text: 'Abertura.', href: 'https://example.com.br' },
}

const textWithAlt: CompositionTextScene = {
    id: 'a',
    type: 'text',
    durationMs: 1000,
    // @ts-expect-error alt e proprio de cena de midia
    content: { text: 'Abertura.', alt: 'Alternativo.' },
}

const textWithoutText: CompositionTextScene = {
    id: 'a',
    type: 'text',
    durationMs: 1000,
    // @ts-expect-error content.text e obrigatorio em cena "text"
    content: { accessibilityLabel: 'Rotulo.' },
}

const ctaWithAsset: CompositionCtaScene = {
    id: 'a',
    type: 'cta',
    durationMs: 1000,
    // @ts-expect-error cena "cta" nao aceita content.asset
    content: { text: 'Conheca.', asset },
}

const ctaWithAlt: CompositionCtaScene = {
    id: 'a',
    type: 'cta',
    durationMs: 1000,
    // @ts-expect-error cena "cta" nao aceita content.alt
    content: { text: 'Conheca.', alt: 'Alternativo.' },
}

const imageWithText: CompositionImageScene = {
    id: 'a',
    type: 'image',
    durationMs: 1000,
    // @ts-expect-error cena de midia nao aceita content.text
    content: { asset, text: 'Descricao.' },
}

const imageWithoutAsset: CompositionImageScene = {
    id: 'a',
    type: 'image',
    durationMs: 1000,
    // @ts-expect-error content.asset e obrigatorio em cena de midia
    content: { alt: 'Agenda.' },
}

const videoWithHref: CompositionVideoScene = {
    id: 'a',
    type: 'video',
    durationMs: 1000,
    // @ts-expect-error href e proprio de cena "cta"
    content: { asset, href: 'https://example.com.br' },
}

const videoWithUnknownField: CompositionVideoScene = {
    id: 'a',
    type: 'video',
    durationMs: 1000,
    // @ts-expect-error campo desconhecido em content
    content: { asset, estilo: 'neon' },
}

const sceneWithAudioType: CompositionScene = {
    id: 'a',
    // @ts-expect-error "audio" nao e tipo de cena da v1
    type: 'audio',
    durationMs: 1000,
    content: { text: 'Abertura.' },
}

const sceneWithUnknownField: CompositionScene = {
    id: 'a',
    type: 'text',
    durationMs: 1000,
    content: { text: 'Abertura.' },
    // @ts-expect-error campo desconhecido na cena
    beat: 'abertura',
}

const sceneWithStringDuration: CompositionScene = {
    id: 'a',
    type: 'text',
    // @ts-expect-error durationMs e numero, nao string
    durationMs: '1000',
    content: { text: 'Abertura.' },
}

const mediaContentInTextScene: CompositionTextScene = {
    id: 'a',
    type: 'text',
    durationMs: 1000,
    // @ts-expect-error content de midia nao serve em cena "text"
    content: mediaContent,
}

// @ts-expect-error uma cena image nao e uma cena text
const imageSceneAsTextScene: CompositionSceneOfType<'text'> = imageScene

const compositionWithRendererOptions: Composition = {
    ...typedComposition,
    // @ts-expect-error renderer.options nao existe na v1
    renderer: { adapter: 'undecided', options: { preset: 'x' } },
}

const compositionWithUnknownStatus: Composition = {
    ...typedComposition,
    // @ts-expect-error status fora de COMPOSITION_METADATA_STATUSES
    metadata: { status: 'publicado' },
}

/**
 * Referencia unica as literais rejeitadas: mantem o bloco acima no modulo sem
 * introduzir comportamento. A verificacao mesma e a compilacao.
 */
export const compileAssertions: readonly unknown[] = [
    textWithAsset,
    textWithHref,
    textWithAlt,
    textWithoutText,
    ctaWithAsset,
    ctaWithAlt,
    imageWithText,
    imageWithoutAsset,
    videoWithHref,
    videoWithUnknownField,
    sceneWithAudioType,
    sceneWithUnknownField,
    sceneWithStringDuration,
    mediaContentInTextScene,
    imageSceneAsTextScene,
    compositionWithRendererOptions,
    compositionWithUnknownStatus,
]

// ---------------------------------------------------------------------------
// Paridade de tipos: os campos de content sao exatamente os declarados no mapa.
// ---------------------------------------------------------------------------

type Equals<A, B> = (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2 ? true : false

type Assert<T extends true> = T

type TextFieldsMatch = Assert<Equals<keyof CompositionSceneOfType<'text'>['content'], CompositionContentFields<'text'>>>
type ImageFieldsMatch = Assert<Equals<keyof CompositionSceneOfType<'image'>['content'], CompositionContentFields<'image'>>>
type VideoFieldsMatch = Assert<Equals<keyof CompositionSceneOfType<'video'>['content'], CompositionContentFields<'video'>>>
type CtaFieldsMatch = Assert<Equals<keyof CompositionSceneOfType<'cta'>['content'], CompositionContentFields<'cta'>>>
type UnionIsFourScenes = Assert<
    Equals<CompositionScene, CompositionTextScene | CompositionImageScene | CompositionVideoScene | CompositionCtaScene>
>
type ExtractIsNarrowing = Assert<Equals<CompositionSceneOfType<'image'>, CompositionImageScene>>
type SceneTypesAreTheUnion = Assert<Equals<CompositionSceneType, 'text' | 'image' | 'video' | 'cta'>>

/**
 * Sem `default`: uma cena nova na uniao deixaria o fim da funcao alcancavel e o
 * `tsc` reclamaria do tipo de retorno declarado. Exaustividade em compilacao, sem cast.
 */
function allowedFieldsOf(scene: CompositionScene): readonly string[] {
    switch (scene.type) {
        case 'text':
        case 'cta':
            return COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE[scene.type]
        case 'image':
        case 'video':
            return COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE[scene.type]
    }
}

interface SceneDefinition {
    properties?: Record<string, { const?: unknown }>
    required?: string[]
    additionalProperties?: unknown
}

const compositionSchema = JSON.parse(
    readFileSync(path.join(moduleRoot, 'schemas', 'composition.schema.json'), 'utf8'),
) as { definitions?: Record<string, SceneDefinition> }

function schemaProperties(name: string): string[] {
    const definition = compositionSchema.definitions?.[name]
    if (!definition?.properties) throw new Error(`definicao "${name}" ausente no schema`)
    return Object.keys(definition.properties)
}

test('a uniao discriminada aceita as quatro cenas e a composicao tipada passa no validador', () => {
    const report = validateComposition(typedComposition, typedManifest)
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.sceneCount, 4)
    assert.equal(report.totalDurationMs, 8000)
    assert.equal(compileAssertions.length, 17)
})

test('o narrowing por type so expoe os campos daquele tipo', () => {
    assert.deepEqual(
        typedComposition.scenes.map((scene) => [...allowedFieldsOf(scene)]),
        [
            ['text', 'accessibilityLabel'],
            ['asset', 'alt', 'accessibilityLabel'],
            ['asset', 'alt', 'accessibilityLabel'],
            ['text', 'href', 'accessibilityLabel'],
        ],
    )

    for (const scene of typedComposition.scenes) {
        if (scene.type === 'image' || scene.type === 'video') {
            assert.equal(typeof scene.content.asset.path, 'string')
        } else {
            assert.equal(typeof scene.content.text, 'string')
        }
    }
})

test('os tipos, o mapa de campos e o schema descrevem as mesmas cenas', () => {
    assert.deepEqual([...COMPOSITION_SCENE_TYPES], Object.keys(COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE))

    const contentDefinitionByType: Record<CompositionSceneType, string> = {
        text: 'textContent',
        image: 'mediaContent',
        video: 'mediaContent',
        cta: 'ctaContent',
    }
    for (const sceneType of COMPOSITION_SCENE_TYPES) {
        assert.deepEqual(
            [...COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE[sceneType]].sort(),
            schemaProperties(contentDefinitionByType[sceneType]).sort(),
            `campos de "${sceneType}" divergem do schema`,
        )
    }

    for (const sceneType of COMPOSITION_SCENE_TYPES) {
        const sceneDefinition = compositionSchema.definitions?.[`${sceneType}Scene`]
        assert.ok(sceneDefinition, `definicao "${sceneType}Scene" ausente no schema`)
        assert.equal(sceneDefinition.properties?.type?.const, sceneType)
        assert.deepEqual(sceneDefinition.required, ['id', 'type', 'durationMs', 'content'])
        assert.equal(sceneDefinition.additionalProperties, false)
    }

    for (const definitionName of ['textContent', 'ctaContent', 'mediaContent']) {
        assert.equal(
            compositionSchema.definitions?.[definitionName]?.additionalProperties,
            false,
            `${definitionName} nao fecha propriedades no schema`,
        )
    }
})
