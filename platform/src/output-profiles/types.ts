/**
 * Tipos do catalogo de perfis de saida sociais.
 *
 * Camada de dados pura: descreve o que cada rede, publicacao e tipo de midia
 * exige, recomenda ou ainda nao tem fonte certificada, sem resolucao de plano
 * e sem logica de validacao. O que e proibido aqui e dado especifico de cliente
 * (nome de marca, ID de canal, dominio comercial, tema editorial, caminho de
 * projeto); URL oficial de fonte e evidencia interna do repositorio sao
 * obrigatorias, porque sem elas a procedencia da regra se perde.
 *
 * Ver docs/planejamento/R001-formatos-sociais.md (secoes 2, 3 e 5).
 */

/** Redes cobertas pela primeira versao do catalogo. */
export const OUTPUT_NETWORKS = ['instagram', 'facebook', 'youtube'] as const
export type OutputNetwork = (typeof OUTPUT_NETWORKS)[number]

/** Destinos de publicacao conhecidos pelo catalogo. */
export const OUTPUT_PUBLICATIONS = ['feed', 'stories', 'reels', 'shorts', 'video'] as const
export type OutputPublication = (typeof OUTPUT_PUBLICATIONS)[number]

/** Tipo de midia do perfil; discrimina a uniao OutputProfile e a uniao OutputPlan. */
export const OUTPUT_MEDIA_KINDS = ['image', 'video'] as const
export type OutputMediaKind = (typeof OUTPUT_MEDIA_KINDS)[number]

/**
 * Contexto de uso de uma regra. A mesma rede muda de exigencia conforme o
 * caminho (app, API, anucios, estudio), entao contexto parte do enunciado.
 * A lista e a unica fonte do enum no contrato do plano e no schema.
 */
export const RULE_CONTEXTS = ['in-app', 'api-publishing', 'ads', 'studio-upload'] as const
export type RuleContext = (typeof RULE_CONTEXTS)[number]

/**
 * Estado de aplicacao de uma regra dentro de um perfil especifico.
 *
 * - `applies`: a fonte cobre exatamente esta rede, publicacao e contexto.
 * - `informational`: a regra existe, mas pertence a outro contexto ou o nucleo
 *   nao consegue verifica-la; nunca vira erro de plano.
 * - `not-evaluated`: nao ha evidencia de que a regra alcance esta aplicacao;
 *   vira pendencia nomeada, nunca erro.
 */
export type RuleApplicationState = 'applies' | 'informational' | 'not-evaluated'

/**
 * Estado real da ligacao entre o perfil e as ferramentas fora do nucleo.
 * Nenhum valor afirma exportacao integrada: `preset-only` e so o preset do
 * catalogo, `canvas-template-mapped` e um template de canvas compativel, e
 * `tool-export-observed` registra uma capacidade observada em ferramenta.
 */
export type ExportState = 'preset-only' | 'canvas-template-mapped' | 'tool-export-observed'

/** Geometria escolhida como preset interno, com proporcao ja reduzida. */
export interface GeometryPreset {
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
}

/** Procedencia de uma regra oficial: pagina, titulo, data e trecho literal. */
export interface RuleSource {
    readonly url: string
    readonly title: string
    /** Instante da consulta em UTC, no forma "YYYY-MM-DDThh:mmZ". */
    readonly accessedOn: string
    /** Trecho literal da pagina que sustenta o enunciado. */
    readonly quote: string
    /** Ressalva da propria fonte, ex.: pagina autodeclarada como traducao automatica. */
    readonly note?: string
}

/**
 * Valor certificado de uma regra. `orientation-any-of` representa condicao
 * geral de orientacao (ex.: proporcao quadrada ou vertical) sem reduzila a uma
 * lista fechada de proporcoes, preservando a distincao com a geometria do preset.
 */
export type RuleValue =
    | { readonly kind: 'allowed-formats'; readonly formats: readonly string[] }
    | { readonly kind: 'aspect-ratios'; readonly ratios: readonly string[] }
    | {
        readonly kind: 'orientation-any-of'
        readonly orientations: readonly ('square' | 'portrait' | 'landscape')[]
    }
    | { readonly kind: 'min-dimensions'; readonly width: number; readonly height: number }
    | { readonly kind: 'max-count'; readonly count: number }
    | { readonly kind: 'max-duration-seconds'; readonly seconds: number }
    | { readonly kind: 'geometry'; readonly width: number; readonly height: number; readonly aspectRatio: string }
    | { readonly kind: 'fps'; readonly fps: number }
    | { readonly kind: 'container'; readonly container: 'mp4' | 'webm' }

/** Classe de uma regra com fonte ou evidencia; nota de politica nao e regra. */
export type RuleKind = 'requirement' | 'recommendation' | 'internal-default'

/** Regra oficial: fonte obrigatoria; `value` so existe quando a fonte certifica numero ou forma. */
export interface OfficialRule {
    readonly id: string
    readonly network: OutputNetwork
    readonly kind: 'requirement' | 'recommendation'
    /**
     * Escopo da regra: os contextos que a **mesma** fonte certifica. Lista, nao
     * contexto unico, porque uma mesma politica pode valer por mais de um caminho
     * (Shorts de ate tres minutos e enviado pelo app e pelo Studio). Uma definicao
     * por regra: o numero continua em `value`, nunca em tabela por contexto.
     */
    readonly contexts: readonly RuleContext[]
    readonly statement: string
    readonly value?: RuleValue
    readonly source: RuleSource
}

/** Default interno do repositorio: evidencia obrigatoria, sem fonte externa. */
export interface InternalDefaultRule {
    readonly id: string
    readonly network: null
    readonly kind: 'internal-default'
    readonly statement: string
    readonly value: RuleValue
    /** Caminho tecnico "arquivo:linha"; quando a unica evidencia mora em dado de marca, aponta a secao deste planejamento. */
    readonly evidence: string
}

/**
 * Pendencia de fonte: sem `value`, sem `source` e sem `evidence`. Ausencia
 * tipada, nao `null` -- proibido representar "desconhecido" como 0 ou Infinity.
 */
export interface PendingSourceRule {
    readonly id: string
    readonly network: OutputNetwork | null
    readonly kind: 'pending-source'
    readonly context: RuleContext | null
    readonly statement: string
}

/** Uniao discriminada por `kind`: cada classe tem exatamente uma representacao. */
export type CatalogRule = OfficialRule | InternalDefaultRule | PendingSourceRule

/**
 * Informacao de politica que o nucleo nao consegue verificar (ex.: reivindicacao
 * de Content ID). Vive fora de `RuleKind` para nao virar avaliacao ficticia.
 */
export interface PolicyNote {
    readonly id: string
    readonly network: OutputNetwork
    readonly statement: string
    readonly source: RuleSource
}

/** Referencia de regra dentro de um perfil, com o estado daquela aplicacao. */
export interface ProfileRuleReference {
    readonly ruleId: string
    readonly state: RuleApplicationState
}

/** Campos comuns aos perfis de imagem e de video. */
interface OutputProfileBase {
    /** Identificador kebab-case; entra em ProjectManifest.outputProfiles sem campo novo. */
    readonly id: string
    /** Rotulo legivel em portugues: dado do catalogo, nao mensagem de relatorio. */
    readonly name: string
    /** Revisao do perfil (>= 1); muda quando geometria, regras ou pendencias mudam. */
    readonly revision: number
    readonly network: OutputNetwork
    readonly publication: OutputPublication
    readonly geometry: GeometryPreset
    /** IDs `D-LOCAL-*` que este perfil instancia. */
    readonly defaults: readonly string[]
    readonly rules: readonly ProfileRuleReference[]
    /** IDs `P-*` de pendencia de fonte que ainda alcanham este perfil. */
    readonly pendingIds: readonly string[]
    /** IDs `PN-*` de nota de politica visivel no perfil. */
    readonly noteIds: readonly string[]
    readonly exportState: ExportState
    /** Evidencia interna da capacidade observada; nunca afirma "exportacao integrada". */
    readonly exportEvidence: readonly string[]
}

/** Perfil de imagem: fps e conteiner sao proibidos por tipo, nao apenas ausentes. */
export interface ImageOutputProfile extends OutputProfileBase {
    readonly mediaKind: 'image'
    readonly fps?: never
    readonly plannedContainer?: never
}

/** Perfil de video: fps e preset interno; conteiner so existe com evidencia. */
export interface VideoOutputProfile extends OutputProfileBase {
    readonly mediaKind: 'video'
    readonly fps: number
    readonly plannedContainer?: 'mp4' | 'webm'
    readonly plannedContainerEvidence?: string
}

export type OutputProfile = ImageOutputProfile | VideoOutputProfile

/** Filtro de leitura do catalogo; campos ausentes nao restringem. */
export interface OutputProfileFilter {
    readonly network?: OutputNetwork
    readonly publication?: OutputPublication
    readonly mediaKind?: OutputMediaKind
}

/** Versao do catalogo; entra no OutputPlan para tracar a tabela usada. */
export const CATALOG_VERSION = '1'
