/**
 * Contrato Composition v1 — segunda fatia do nucleo modular da Content Factory.
 *
 * Composition e um contrato declarativo: nao e roteiro, nao e BeatPlan, nao e
 * renderizacao. O texto canonico permanece estruturado; assets sao referenciados,
 * nunca gerados; o renderizador pode permanecer "undecided".
 *
 * O nucleo NAO conhece nenhum projeto especifico: a composicao e sempre validada
 * contra um ProjectManifest informado explicitamente.
 *
 * Ver docs/decisoes/MKT-VIDEO-001-producao-modular.md,
 * docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md e
 * docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const COMPOSITION_SCHEMA_VERSION = 1

/** Tipos de cena suportados na v1, em ordem fixa de documentacao. */
export const COMPOSITION_SCENE_TYPES = ['text', 'image', 'video', 'cta'] as const

export type CompositionSceneType = (typeof COMPOSITION_SCENE_TYPES)[number]

/** Status de metadata permitidos; "approved" aqui e tecnico, nao editorial. */
export const COMPOSITION_METADATA_STATUSES = ['draft', 'review', 'approved', 'archived'] as const

export type CompositionMetadataStatus = (typeof COMPOSITION_METADATA_STATUSES)[number]

/** Faixa de fps aceita na v1: inteiros entre estes limites, inclusive. */
export const COMPOSITION_FPS_MIN = 1
export const COMPOSITION_FPS_MAX = 120

/** Limite documentado de tags em metadata. */
export const COMPOSITION_MAX_TAGS = 8

/** Limite tecnico (heuristica) de caracteres em text/cta para warning. */
export const COMPOSITION_MAX_TEXT_LENGTH = 160

/** Duracao minima (heuristica) para cena com texto, em milissegundos. */
export const COMPOSITION_MIN_TEXT_DURATION_MS = 1000

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
export const COMPOSITION_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'projectId',
    'id',
    'title',
    'locale',
    'format',
    'scenes',
    'renderer',
    'metadata',
] as const

export { KEBAB_CASE_PATTERN }

/** Formato de saida da composicao: intencao de profile, nao imposicao de resolucao. */
export interface CompositionFormat {
    /** Identificador kebab-case que deve existir em ProjectManifest.outputProfiles. */
    profile: string
    width: number
    height: number
    fps: number
}

/**
 * Referencia minima de asset: apenas id e caminho relativo seguro.
 * Nao substitui o futuro AssetManifest: hash, licenca, origem, provider, prompt,
 * dimensoes e duracao pertencem a uma fatia futura. A existencia fisica NAO e
 * verificada nesta fatia.
 */
export interface AssetReference {
    id: string
    path: string
}

/** Conteudo de cena `text`: texto canonico estruturado; sem href, alt nem asset. */
export interface CompositionTextContent {
    text: string
    accessibilityLabel?: string
}

/** Conteudo de cena `cta`: chamada com href http(s) opcional; sem alt nem asset. */
export interface CompositionCtaContent {
    text: string
    href?: string
    accessibilityLabel?: string
}

/** Conteudo de cenas `image` e `video`: asset obrigatorio; sem text nem href. */
export interface CompositionMediaContent {
    asset: AssetReference
    alt?: string
    accessibilityLabel?: string
}

/**
 * Superficie de `content` por tipo de cena, na mesma ordem de COMPOSITION_SCENE_TYPES.
 * E a unica fonte dessa superficie: o validador a usa para rejeitar campos, o schema
 * espelha as mesmas chaves em `#/definitions/*Content` e os testes de contrato
 * comparam as tres.
 */
export const COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE = {
    text: ['text', 'accessibilityLabel'],
    image: ['asset', 'alt', 'accessibilityLabel'],
    video: ['asset', 'alt', 'accessibilityLabel'],
    cta: ['text', 'href', 'accessibilityLabel'],
} as const satisfies Record<CompositionSceneType, readonly string[]>

/** Nomes de campo permitidos em `content` para o tipo de cena dado. */
export type CompositionContentFields<T extends CompositionSceneType> =
    (typeof COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE)[T][number]

/**
 * Uniao das formas de content existentes na v1. So e meaningful como documentacao:
 * quem precisa de garantia de compatibilidade usa a cena, nao o conteudo isolado,
 * porque a mesma forma pertence a mais de um tipo (image e video).
 */
export type CompositionSceneContent = CompositionTextContent | CompositionCtaContent | CompositionMediaContent

interface CompositionSceneFields {
    /** Identificador kebab-case, unico dentro da composicao. */
    id: string
    /** Inteiro seguro maior que zero, em milissegundos. */
    durationMs: number
}

export interface CompositionTextScene extends CompositionSceneFields {
    type: 'text'
    content: CompositionTextContent
}

export interface CompositionImageScene extends CompositionSceneFields {
    type: 'image'
    content: CompositionMediaContent
}

export interface CompositionVideoScene extends CompositionSceneFields {
    type: 'video'
    content: CompositionMediaContent
}

export interface CompositionCtaScene extends CompositionSceneFields {
    type: 'cta'
    content: CompositionCtaContent
}

/**
 * Cena da composicao: uniao **discriminada por `type`**. A combinacao de um tipo com
 * a forma de content de outro tipo e um erro de compilacao, entao o TypeScript e o
 * schema e o validador rejeitam a mesma coisa (o schema faz isso com `oneOf` de quatro
 * definicoes com `type` constante).
 */
export type CompositionScene =
    | CompositionTextScene
    | CompositionImageScene
    | CompositionVideoScene
    | CompositionCtaScene

/** Cena de um tipo especifico; util para assertoes de tipo nos testes de contrato. */
export type CompositionSceneOfType<T extends CompositionSceneType> = Extract<CompositionScene, { type: T }>

/** Adaptador de renderizacao; nenhum adapter precisa estar instalado. */
export interface CompositionRenderer {
    adapter: string
}

/** Metadata opcional e pequena; "approved" nao concede autorizacao editorial. */
export interface CompositionMetadata {
    status?: CompositionMetadataStatus
    description?: string
    tags?: string[]
}

/** Composicao declarativa vinculada a um projeto por projectId. */
export interface Composition {
    schemaVersion: number
    projectId: string
    id: string
    title: string
    locale: string
    format: CompositionFormat
    scenes: CompositionScene[]
    renderer: CompositionRenderer
    metadata?: CompositionMetadata
}
