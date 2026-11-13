/**
 * Contrato interno CarouselRequest v1 — entrada unica de carrossel de imagens.
 *
 * Um pedido descreve o carrossel (id, projeto, perfil de imagem, titulo), um
 * cadastro reutilizavel de midias de imagem e uma lista ordenada de cards. Cada
 * card tem id, titulo, corpo opcional e referencia opcional a midia. O texto
 * permanece editavel no pedido; a origem e a licenca de cada material sao
 * declaradas ou pendentes.
 *
 * O perfil de imagem e resolvido apenas pelo catalogo (resolveOutputPlan) e pela
 * allowlist do projeto na camada de exportacao; este contrato e estrutural e
 * puro. Nucleo sem I/O, sem rede, sem relogio, sem aleatoriedade, sem marca.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const CAROUSEL_REQUEST_SCHEMA_VERSION = 1

/** Perfil de imagem padrao do recorte local de carrossel. */
export const CAROUSEL_DEFAULT_PROFILE = 'instagram-feed-image-square'

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
export const CAROUSEL_REQUEST_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'id',
    'project',
    'profile',
    'title',
    'media',
    'cards',
] as const

/** Campos obrigatorios de topo (profile opcional, padrao do recorte). */
export const CAROUSEL_REQUEST_REQUIRED_FIELDS = [
    'schemaVersion',
    'id',
    'project',
    'title',
    'media',
    'cards',
] as const

/** Campos conhecidos de cada material de midia. */
export const CAROUSEL_MEDIA_FIELDS = ['id', 'path', 'type', 'origin', 'license'] as const

/** Campos obrigatorios de cada material (license opcional, padrao 'pending'). */
export const CAROUSEL_MEDIA_REQUIRED_FIELDS = ['id', 'path', 'type', 'origin'] as const

/** Campos conhecidos de cada card. */
export const CAROUSEL_CARD_FIELDS = ['id', 'title', 'body', 'mediaId'] as const

/** Campos obrigatorios de cada card (body e mediaId opcionais). */
export const CAROUSEL_CARD_REQUIRED_FIELDS = ['id', 'title'] as const

/** Carrossel usa apenas midia de imagem nesta fatia. */
export const CAROUSEL_MEDIA_TYPES = ['image'] as const

export type CarouselMediaType = (typeof CAROUSEL_MEDIA_TYPES)[number]

/** Licenca padrao quando o material omite o campo. */
export const CAROUSEL_DEFAULT_LICENSE = 'pending'

export { KEBAB_CASE_PATTERN }

/** Material de imagem cadastrado uma vez e vinculavel a varios cards. */
export interface CarouselMedia {
    readonly id: string
    readonly path: string
    readonly type: CarouselMediaType
    readonly origin: string
    readonly license?: string
}

/** Card ordenado do carrossel: titulo, corpo opcional e midia opcional. */
export interface CarouselCard {
    readonly id: string
    readonly title: string
    readonly body?: string
    readonly mediaId?: string
}

/** Pedido de carrossel v1. */
export interface CarouselRequest {
    readonly schemaVersion: 1
    readonly id: string
    readonly project: string
    readonly profile?: string
    readonly title: string
    readonly media: readonly CarouselMedia[]
    readonly cards: readonly CarouselCard[]
}

/** Codigos de falha estaveis; a automacao confia no codigo, nao na mensagem. */
export type CarouselRequestFailureCode =
    | 'CAROUSEL_REQUEST_INVALID'
    | 'CAROUSEL_REQUEST_SCHEMA_VERSION_UNSUPPORTED'
    | 'CAROUSEL_REQUEST_ID_INVALID'
    | 'CAROUSEL_REQUEST_PROJECT_INVALID'
    | 'CAROUSEL_REQUEST_TITLE_INVALID'
    | 'CAROUSEL_REQUEST_PROFILE_INVALID'
    | 'CAROUSEL_MEDIA_INVALID'
    | 'CAROUSEL_MEDIA_ID_INVALID'
    | 'CAROUSEL_MEDIA_ID_DUPLICATE'
    | 'CAROUSEL_MEDIA_PATH_INVALID'
    | 'CAROUSEL_MEDIA_TYPE_INVALID'
    | 'CAROUSEL_MEDIA_ORIGIN_INVALID'
    | 'CAROUSEL_MEDIA_LICENSE_INVALID'
    | 'CAROUSEL_CARDS_INVALID'
    | 'CAROUSEL_CARD_ID_INVALID'
    | 'CAROUSEL_CARD_ID_DUPLICATE'
    | 'CAROUSEL_CARD_TITLE_INVALID'
    | 'CAROUSEL_CARD_BODY_INVALID'
    | 'CAROUSEL_CARD_MEDIA_REFERENCE_INVALID'
    | 'CAROUSEL_REQUEST_UNKNOWN_FIELD'

export type CarouselRequestValidationResult =
    | { readonly ok: true; readonly request: CarouselRequest }
    | { readonly ok: false; readonly failureCode: CarouselRequestFailureCode; readonly subject: string | null }