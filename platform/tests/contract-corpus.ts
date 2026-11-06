/**
 * Corpus compartilhado dos contratos ProjectManifest e Composition v1.
 *
 * Classificacao dos casos (o que cada grupo prova):
 *
 * - **estruturais** (`structuralProjectCases`, `structuralCompositionCases`): a regra vive
 *   na forma do proprio documento, entao o schema draft-07 e o validador TypeScript
 *   precisam chegar ao MESMO veredicto de aceitacao;
 * - **semanticas** (`semanticCases`): a regra depende de outro documento (ProjectManifest),
 *   de identidade entre itens, de aritmetica de duracoes ou de comparacao por tokens — o
 *   validador TypeScript e a autoridade, com codigos proprios, e o que o schema faz com o
 *   mesmo documento fica registrado em `schemaAccepts`, caso a caso.
 *
 * Nao ha categoria de "schema mais estrito". A forma canonica `scheme://host` do `href` e
 * conferida na string original, antes da normalizacao do parser de URL: a etapa 5 fechou o
 * prefixo (`http:/example.com`) e a etapa 6 fechou o inicio e o termino da autoridade
 * (`https:///example.com` rejeitado, `@` em caminho/query/fragmento aceito). Restam apenas
 * divergencias em que o CORE e mais estrito que o espelho — nomes por token e sintaxe de
 * host do parser de URL —, nunca o contrario: nenhuma estrutura declarada invalida pelo
 * schema normativo retorna `valid: true` no core.
 */
import {
    B,
    NUL,
    compositionWith,
    compositionWithAssetPath,
    compositionWithHref,
    compositionWithScenes,
    compositionWithTextField,
    projectWith,
    safeAsset,
    sceneWith,
    withoutFields,
} from './contract-harness.js'

export interface StructuralCase {
    readonly name: string
    readonly document: Record<string, unknown>
    readonly valid: boolean
    /** Codigos esperados do validador TypeScript quando o caso e invalido. */
    readonly codes?: readonly string[]
}

export type SemanticReason =
    | 'vinculo-com-o-projectmanifest'
    | 'manifesto-invalido'
    | 'unicidade-de-id-de-cena'
    | 'soma-de-duracoes'
    | 'nomes-sensiveis-por-token'
    | 'sintaxe-de-url-no-parser'
    | 'heuristica-de-warning'

export interface SemanticCase {
    readonly name: string
    readonly contract: 'project' | 'composition'
    readonly document: Record<string, unknown>
    readonly project: Record<string, unknown>
    readonly codes: readonly string[]
    readonly reason: SemanticReason
    /** O que o schema decide sobre este mesmo documento (registrado, nao exigido). */
    readonly schemaAccepts: boolean
    readonly totalDurationMs?: number | null
    readonly warnings?: readonly string[]
}

/** Violacao lexica compartilhada e os codigos que cada contrato produz para ela. */
export interface LexicalPathCase {
    readonly value: string
    readonly violation: 'CONTROL_CHARACTER' | 'ABSOLUTE' | 'URL' | 'TRAVERSAL' | 'SENSITIVE'
    readonly projectCode: string
    readonly compositionCode: string
}

export const lexicalPathCases: readonly LexicalPathCase[] = [
    {
        value: `/var/assets`,
        violation: 'ABSOLUTE',
        projectCode: 'PROJECT_ASSET_ROOT_ABSOLUTE',
        compositionCode: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
    },
    {
        value: `C:${B}assets${B}x`,
        violation: 'ABSOLUTE',
        projectCode: 'PROJECT_ASSET_ROOT_ABSOLUTE',
        compositionCode: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
    },
    {
        value: `${B}${B}servidor${B}share${B}a.png`,
        violation: 'ABSOLUTE',
        projectCode: 'PROJECT_ASSET_ROOT_ABSOLUTE',
        compositionCode: 'COMPOSITION_ASSET_PATH_ABSOLUTE',
    },
    {
        value: 'https://example.com/assets',
        violation: 'URL',
        projectCode: 'PROJECT_ASSET_ROOT_URL',
        compositionCode: 'COMPOSITION_ASSET_PATH_URL',
    },
    {
        value: 'file:///c:/assets/a.png',
        violation: 'URL',
        projectCode: 'PROJECT_ASSET_ROOT_URL',
        compositionCode: 'COMPOSITION_ASSET_PATH_URL',
    },
    {
        value: '//example.com/a.png',
        violation: 'URL',
        projectCode: 'PROJECT_ASSET_ROOT_URL',
        compositionCode: 'COMPOSITION_ASSET_PATH_URL',
    },
    {
        value: '../assets',
        violation: 'TRAVERSAL',
        projectCode: 'PROJECT_ASSET_ROOT_TRAVERSAL',
        compositionCode: 'COMPOSITION_ASSET_PATH_TRAVERSAL',
    },
    {
        value: `assets${B}..${B}fora.png`,
        violation: 'TRAVERSAL',
        projectCode: 'PROJECT_ASSET_ROOT_TRAVERSAL',
        compositionCode: 'COMPOSITION_ASSET_PATH_TRAVERSAL',
    },
    {
        value: 'projects/x/.env',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'assets/.env.local',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'assets/.git/config',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/server.pem',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/service.key',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/legacy.p12',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/legacy.pfx',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/id_rsa',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: 'keys/id_ed25519.pub',
        violation: 'SENSITIVE',
        projectCode: 'PROJECT_ASSET_ROOT_SENSITIVE',
        compositionCode: 'COMPOSITION_ASSET_PATH_SENSITIVE',
    },
    {
        value: `assets${NUL}b.png`,
        violation: 'CONTROL_CHARACTER',
        projectCode: 'PROJECT_ASSET_ROOT_CONTROL_CHARACTER',
        compositionCode: 'COMPOSITION_ASSET_PATH_CONTROL_CHARACTER',
    },
]

/** Caminhos que os dois contratos e os dois motores devem ACEITAR. */
export const acceptedPaths: readonly string[] = [
    'assets/secretaria',
    'assets/secretaria.png',
    'assets/cenas/01.png',
    'projects/projeto-teste/assets',
    'assets/keys/x.png',
    'assets/.gitignore',
    'assets/env/.gitmodules',
    'assets/passphrase.txt',
    'assets/./ok.png',
]

/** Hrefs que os dois contratos e os dois motores devem ACEITAR. */
export const acceptedHrefs: readonly string[] = [
    'http://example.com',
    'https://example.com',
    'https://example.com.br/roda-pe',
    'HTTPS://EXAMPLE.COM',
    'HtTpS://example.com/a?b=1#c',
    'https://example.com:8443/rota',
    'https://example.com/@mencao',
    'https://[::1]:8080/',
]

/** Hrefs que os dois devem REJEITAR, com o codigo do core. */
export const rejectedHrefs: readonly { href: string; code: string }[] = [
    { href: 'https://usuario@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { href: 'https://user:pass@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { href: 'HTTPS://usuario:senha@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { href: 'https://@example.com', code: 'COMPOSITION_CTA_HREF_CREDENTIALS' },
    { href: 'ftp://example.com', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: 'file:///c:/assets/a.png', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: 'data:text/plain,oi', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: '//example.com/a.png', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: '/rota/relativa', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: 'example.com/a', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: 'https://', code: 'COMPOSITION_CTA_HREF_INVALID' },
    { href: `https://example.com${NUL}`, code: 'COMPOSITION_CTA_HREF_INVALID' },
]

/**
 * Hrefs com `@` fora da autoridade: caminho, query ou fragmento, com e sem barra depois do
 * host. Ate a etapa 6 a regex de credencial do schema procurava o `@` sem parar em `?` nem
 * em `#`, entao documentos validos eram rejeitados so pelo espelho. Nos dois motores e na
 * CLI esses hrefs precisam ser ACEITOS; credenciais reais seguem em `rejectedHrefs`.
 */
export const atOutsideAuthorityHrefs: readonly string[] = [
    'https://example.com?email=a@b.com',
    'https://example.com#@contato',
    'https://example.com/?email=a@b.com',
    `https://example.com${B}@mencao`,
    'https://example.com/agenda@2026',
    'https://example.com:8443/rota?q=a@b#f=c@d',
]

/**
 * Hrefs sem host imediatamente depois de `scheme://`. O parser WHATWG descarta barras e
 * barras invertidas extras e reconstrói o host com o trecho seguinte; o espelho normativo
 * declara essa entrada invalida, entao o core tambem precisa recusar (etapa 6). Nos dois
 * motores e na CLI esses hrefs saem COMPOSITION_CTA_HREF_INVALID.
 */
export const emptyAuthorityHrefs: readonly string[] = [
    'https:///example.com',
    'https:////example.com',
    `https://${B}example.com`,
    `HTTPS://${B}${B}example.com`,
    'https://?query=1',
    'https://#fragmento',
]

/** Campos textuais obrigatorios ou opcionais que nao podem ser so espacos. */
export const blankStringFields: readonly { field: 'title' | 'locale' | 'text' | 'accessibilityLabel' | 'alt'; code: string }[] = [
    { field: 'title', code: 'COMPOSITION_TITLE_REQUIRED' },
    { field: 'locale', code: 'COMPOSITION_LOCALE_REQUIRED' },
    { field: 'text', code: 'COMPOSITION_TEXT_REQUIRED' },
    { field: 'accessibilityLabel', code: 'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN' },
    { field: 'alt', code: 'COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN' },
]

export const blankValues: readonly string[] = ['   ', '\t\n ']

export const blankProjectFields: readonly string[] = ['name', 'locale', 'timezone', 'brandTheme']

/**
 * Casos estruturais do ProjectManifest: schema e TypeScript devem concordar.
 * Os caminhos testados aqui vem de `lexicalPathCases` e `acceptedPaths`; o resto e
 * superficie (campos obrigatorios, desconhecidos, politicas e profiles).
 */
export const structuralProjectCases: readonly StructuralCase[] = [
    ...acceptedPaths.map((value) => ({ name: `assetRoot relativo ${JSON.stringify(value)}`, document: projectWith({ assetRoot: value }), valid: true })),
    ...lexicalPathCases.map((caseItem) => ({
        name: `assetRoot ${caseItem.violation.toLowerCase()} ${JSON.stringify(caseItem.value)}`,
        document: projectWith({ assetRoot: caseItem.value }),
        valid: false,
        codes: [caseItem.projectCode],
    })),
    {
        name: 'assetRoot ausente',
        document: withoutFields(projectWith({}), ['assetRoot']),
        valid: false,
        codes: ['PROJECT_ASSET_ROOT_REQUIRED'],
    },
    { name: 'assetRoot vazio', document: projectWith({ assetRoot: '' }), valid: false, codes: ['PROJECT_ASSET_ROOT_REQUIRED'] },
    ...blankProjectFields.flatMap((field) => blankValues.map((value) => ({
        name: `${field} em branco ${JSON.stringify(value)}`,
        document: projectWith({ [field]: value }),
        valid: false,
        codes: [
            {
                name: 'PROJECT_NAME_REQUIRED',
                locale: 'PROJECT_LOCALE_REQUIRED',
                timezone: 'PROJECT_TIMEZONE_REQUIRED',
                brandTheme: 'PROJECT_BRAND_THEME_REQUIRED',
            }[field]!,
        ],
    }))),
    { name: 'manifesto valido baseline', document: projectWith({}), valid: true },
    {
        name: 'schemaVersion 2',
        document: projectWith({ schemaVersion: 2 }),
        valid: false,
        codes: ['PROJECT_SCHEMA_VERSION_UNSUPPORTED'],
    },
    { name: 'id fora do kebab-case', document: projectWith({ id: 'Projeto Teste' }), valid: false, codes: ['PROJECT_ID_INVALID'] },
    {
        name: 'campo desconhecido no topo',
        document: projectWith({ beatPlan: {} }),
        valid: false,
        codes: ['PROJECT_UNKNOWN_FIELD'],
    },
    {
        name: 'politica ausente',
        document: projectWith({
            contentPolicies: {
                requireApprovedScript: true,
                prohibitPersonalData: true,
                requireFunctionalEvidence: true,
            },
        }),
        valid: false,
        codes: ['PROJECT_CONTENT_POLICY_INVALID'],
    },
    {
        name: 'politica com campo desconhecido',
        document: projectWith({
            contentPolicies: {
                requireApprovedBriefing: true,
                requireApprovedScript: true,
                prohibitPersonalData: true,
                requireFunctionalEvidence: true,
                autoPublish: false,
            },
        }),
        valid: false,
        codes: ['PROJECT_CONTENT_POLICY_INVALID'],
    },
    {
        name: 'politica nao booleana',
        document: projectWith({
            contentPolicies: {
                requireApprovedBriefing: 'sim',
                requireApprovedScript: true,
                prohibitPersonalData: true,
                requireFunctionalEvidence: true,
            },
        }),
        valid: false,
        codes: ['PROJECT_CONTENT_POLICY_INVALID'],
    },
    { name: 'outputProfiles vazio', document: projectWith({ outputProfiles: [] }), valid: false, codes: ['PROJECT_OUTPUT_PROFILE_REQUIRED'] },
    {
        name: 'outputProfiles duplicado',
        document: projectWith({ outputProfiles: ['vertical-social', 'vertical-social'] }),
        valid: false,
        codes: ['PROJECT_OUTPUT_PROFILE_DUPLICATE'],
    },
    {
        name: 'outputProfiles fora do kebab-case',
        document: projectWith({ outputProfiles: ['Vertical Social'] }),
        valid: false,
        codes: ['PROJECT_OUTPUT_PROFILE_INVALID'],
    },
]

/** Discriminacao de cena por `type` (corrigida na etapa 1) e formas de content. */
export const sceneShapeCases: readonly StructuralCase[] = [
    { name: 'text com content.text', document: compositionWithScenes([sceneWith({ content: { text: 'Abertura.' } })]), valid: true },
    {
        name: 'text com text e accessibilityLabel',
        document: compositionWithScenes([sceneWith({ content: { text: 'Abertura.', accessibilityLabel: 'Rotulo.' } })]),
        valid: true,
    },
    {
        name: 'cta com text e href https',
        document: compositionWithScenes([sceneWith({ type: 'cta', content: { text: 'Conheca.', href: 'https://example.com.br' } })]),
        valid: true,
    },
    {
        name: 'cta sem href',
        document: compositionWithScenes([sceneWith({ type: 'cta', content: { text: 'Conheca.' } })]),
        valid: true,
    },
    {
        name: 'image com asset',
        document: compositionWithScenes([sceneWith({ type: 'image', content: { asset: safeAsset } })]),
        valid: true,
    },
    {
        name: 'image com asset, alt e accessibilityLabel',
        document: compositionWithScenes([
            sceneWith({ type: 'image', content: { asset: safeAsset, alt: 'Agenda do salao.', accessibilityLabel: 'Imagem da agenda.' } }),
        ]),
        valid: true,
    },
    {
        name: 'video com asset',
        document: compositionWithScenes([sceneWith({ type: 'video', content: { asset: safeAsset } })]),
        valid: true,
    },
    { name: 'text com href (proprio de cta)', document: compositionWithScenes([sceneWith({ content: { text: 'Abertura.', href: 'https://example.com.br' } })]), valid: false },
    { name: 'text com asset', document: compositionWithScenes([sceneWith({ content: { text: 'Abertura.', asset: safeAsset } })]), valid: false },
    { name: 'text com alt', document: compositionWithScenes([sceneWith({ content: { text: 'Abertura.', alt: 'Alternativo.' } })]), valid: false },
    { name: 'cta com asset', document: compositionWithScenes([sceneWith({ type: 'cta', content: { text: 'Conheca.', asset: safeAsset } })]), valid: false },
    { name: 'cta com alt', document: compositionWithScenes([sceneWith({ type: 'cta', content: { text: 'Conheca.', alt: 'Alternativo.' } })]), valid: false },
    { name: 'image com so text', document: compositionWithScenes([sceneWith({ type: 'image', content: { text: 'Descricao.' } })]), valid: false },
    { name: 'video com so text', document: compositionWithScenes([sceneWith({ type: 'video', content: { text: 'Descricao.' } })]), valid: false },
    { name: 'image com asset e text', document: compositionWithScenes([sceneWith({ type: 'image', content: { asset: safeAsset, text: 'Descricao.' } })]), valid: false },
    { name: 'video com href', document: compositionWithScenes([sceneWith({ type: 'video', content: { asset: safeAsset, href: 'https://example.com.br' } })]), valid: false },
    { name: 'text sem content.text', document: compositionWithScenes([sceneWith({ content: { accessibilityLabel: 'Rotulo.' } })]), valid: false },
    { name: 'text com content vazio', document: compositionWithScenes([sceneWith({ content: { text: '' } })]), valid: false, codes: ['COMPOSITION_TEXT_REQUIRED'] },
    { name: 'cena sem content', document: compositionWithScenes([withoutFields(sceneWith(), ['content'])]), valid: false },
    { name: 'cena sem durationMs', document: compositionWithScenes([withoutFields(sceneWith(), ['durationMs'])]), valid: false },
    { name: 'cena sem id', document: compositionWithScenes([withoutFields(sceneWith(), ['id'])]), valid: false },
    { name: 'cena sem type', document: compositionWithScenes([withoutFields(sceneWith(), ['type'])]), valid: false },
    { name: 'cena com type audio', document: compositionWithScenes([sceneWith({ type: 'audio' })]), valid: false },
    { name: 'cena com campo desconhecido', document: compositionWithScenes([sceneWith({ beat: 'abertura' })]), valid: false },
    { name: 'content com campo desconhecido', document: compositionWithScenes([sceneWith({ content: { text: 'Abertura.', estilo: 'neon' } })]), valid: false },
    { name: 'asset sem path', document: compositionWithScenes([sceneWith({ type: 'image', content: { asset: withoutFields(safeAsset, ['path']) } })]), valid: false },
    { name: 'asset com campo desconhecido', document: compositionWithScenes([sceneWith({ type: 'image', content: { asset: { ...safeAsset, hash: 'abc' } } })]), valid: false },
    { name: 'asset com id fora do kebab-case', document: compositionWithScenes([sceneWith({ type: 'image', content: { asset: { id: 'Tela 01', path: 'assets/a.png' } } })]), valid: false },
]

/** Superficie fora de cena: topo, format, renderer e metadata. */
export const surfaceCases: readonly StructuralCase[] = [
    { name: 'composicao baseline com as quatro cenas', document: compositionWithScenes([
        sceneWith({ id: 'abertura', content: { text: 'Abertura.' } }),
        sceneWith({ id: 'tela', type: 'image', content: { asset: safeAsset, alt: 'Agenda.' } }),
        sceneWith({ id: 'demo', type: 'video', durationMs: 2000, content: { asset: safeAsset } }),
        sceneWith({ id: 'chamada', type: 'cta', durationMs: 2000, content: { text: 'Conheca.', href: 'https://example.com.br' } }),
    ]), valid: true },
    {
        name: 'metadata tecnica com status approved',
        document: compositionWith({ metadata: { status: 'approved', description: 'Fixture.', tags: ['pilot'] } }),
        valid: true,
    },
    { name: 'fps no limite superior (120)', document: compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 120 } }), valid: true },
    { name: 'fps 24 fora de 30', document: compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 24 } }), valid: true },
    { name: 'renderer undecided', document: compositionWith({ renderer: { adapter: 'undecided' } }), valid: true },
    { name: 'schemaVersion 2', document: compositionWith({ schemaVersion: 2 }), valid: false },
    { name: 'campo desconhecido no topo', document: compositionWith({ renderPlan: {} }), valid: false, codes: ['COMPOSITION_UNKNOWN_FIELD'] },
    { name: 'campo desconhecido em format', document: compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 30, codec: 'h264' } }), valid: false },
    { name: 'campo desconhecido em renderer', document: compositionWith({ renderer: { adapter: 'undecided', speed: 1 } }), valid: false },
    { name: 'renderer.options nao suportado na v1', document: compositionWith({ renderer: { adapter: 'undecided', options: { preset: 'x' } } }), valid: false },
    { name: 'format.ausente', document: withoutFields(compositionWith({}), ['format']), valid: false },
    { name: 'renderer ausente', document: withoutFields(compositionWith({}), ['renderer']), valid: false },
    { name: 'scenes ausente', document: withoutFields(compositionWith({}), ['scenes']), valid: false },
    { name: 'scenes vazio (v1 aceita: nenhum minimo declarado)', document: compositionWithScenes([]), valid: true },
    { name: 'fps zero', document: compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 0 } }), valid: false },
    { name: 'fps acima de 120', document: compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 121 } }), valid: false },
    { name: 'fps nao inteiro', document: compositionWith({ format: { profile: 'vertical-social', width: 1080, height: 1920, fps: 29.5 } }), valid: false },
    { name: 'width zero', document: compositionWith({ format: { profile: 'vertical-social', width: 0, height: 1920, fps: 30 } }), valid: false },
    { name: 'profile fora do kebab-case', document: compositionWith({ format: { profile: 'Vertical Social', width: 1080, height: 1920, fps: 30 } }), valid: false },
    { name: 'metadata com campo desconhecido', document: compositionWith({ metadata: { owner: 'marketing' } }), valid: false },
    { name: 'metadata com status desconhecido', document: compositionWith({ metadata: { status: 'publicado' } }), valid: false },
    { name: 'metadata com mais de oito tags', document: compositionWith({ metadata: { tags: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'] } }), valid: false },
    { name: 'metadata com tags duplicadas', document: compositionWith({ metadata: { tags: ['pilot', 'pilot'] } }), valid: false },
    { name: 'id de composicao fora do kebab-case', document: compositionWith({ id: 'Comp Contrato' }), valid: false },
    { name: 'projectId fora do kebab-case', document: compositionWith({ projectId: 'Projeto Teste' }), valid: false },
]

/** Caminhos, hrefs, textos e duracoes corrigidos nas etapas 1 e 2. */
export const lexicalAndTextCases: readonly StructuralCase[] = [
    ...acceptedPaths.map((value) => ({ name: `asset.path ${JSON.stringify(value)}`, document: compositionWithAssetPath(value), valid: true })),
    ...lexicalPathCases.map((caseItem) => ({
        name: `asset.path ${caseItem.violation.toLowerCase()} ${JSON.stringify(caseItem.value)}`,
        document: compositionWithAssetPath(caseItem.value),
        valid: false,
        codes: [caseItem.compositionCode],
    })),
    { name: 'asset.path ausente em branco', document: compositionWithAssetPath(''), valid: false, codes: ['COMPOSITION_ASSET_PATH_REQUIRED'] },
    { name: 'asset.path apenas espacos', document: compositionWithAssetPath('   '), valid: false, codes: ['COMPOSITION_ASSET_PATH_REQUIRED'] },
    ...acceptedHrefs.map((href) => ({ name: `href ${href}`, document: compositionWithHref(href), valid: true })),
    ...rejectedHrefs.map((caseItem) => ({
        name: `href rejeitado ${caseItem.href}`,
        document: compositionWithHref(caseItem.href),
        valid: false,
        codes: [caseItem.code],
    })),
    { name: 'href ausente (so text)', document: compositionWithScenes([sceneWith({ type: 'cta', content: { text: 'Conheca.' } })]), valid: true },
    ...blankStringFields.flatMap((caseItem) => blankValues.map((value) => ({
        name: `${caseItem.field} em branco ${JSON.stringify(value)}`,
        document: compositionWithTextField(caseItem.field, value),
        valid: false,
        codes: [caseItem.code],
    }))),
    {
        name: 'metadata.description apenas espacos',
        document: compositionWith({ metadata: { description: '   ' } }),
        valid: false,
        codes: ['COMPOSITION_METADATA_INVALID'],
    },
    {
        name: 'metadata.tags com item em branco',
        document: compositionWith({ metadata: { tags: ['pilot', '   '] } }),
        valid: false,
        codes: ['COMPOSITION_METADATA_INVALID'],
    },
    { name: 'durationMs no inteiro seguro', document: compositionWithScenes([sceneWith({ durationMs: Number.MAX_SAFE_INTEGER })]), valid: true },
    {
        name: 'durationMs acima do inteiro seguro',
        document: compositionWithScenes([sceneWith({ durationMs: Number.MAX_SAFE_INTEGER + 1 })]),
        valid: false,
        codes: ['COMPOSITION_SCENE_DURATION_INVALID'],
    },
    {
        name: 'durationMs zero',
        document: compositionWithScenes([sceneWith({ durationMs: 0 })]),
        valid: false,
        codes: ['COMPOSITION_SCENE_DURATION_INVALID'],
    },
    {
        name: 'durationMs negativo',
        document: compositionWithScenes([sceneWith({ durationMs: -1 })]),
        valid: false,
        codes: ['COMPOSITION_SCENE_DURATION_INVALID'],
    },
    {
        name: 'durationMs nao inteiro',
        document: compositionWithScenes([sceneWith({ durationMs: 1.5 })]),
        valid: false,
        codes: ['COMPOSITION_SCENE_DURATION_INVALID'],
    },
    {
        name: 'href sem barras duplas (regressao de conformidade: o core normalizava)',
        document: compositionWithHref('http:/example.com'),
        valid: false,
        codes: ['COMPOSITION_CTA_HREF_INVALID'],
    },
    {
        name: 'href com barras invertidas (regressao de conformidade: o core normalizava)',
        document: compositionWithHref(`https:${B}${B}example.com`),
        valid: false,
        codes: ['COMPOSITION_CTA_HREF_INVALID'],
    },
    ...atOutsideAuthorityHrefs.map((href) => ({
        name: `href com @ fora da autoridade ${href} (regressao de conformidade: o espelho rejeitava)`,
        document: compositionWithHref(href),
        valid: true,
    })),
    ...emptyAuthorityHrefs.map((href) => ({
        name: `href com autoridade vazia ${href} (regressao de conformidade: o core normalizava)`,
        document: compositionWithHref(href),
        valid: false,
        codes: ['COMPOSITION_CTA_HREF_INVALID'],
    })),
]

/** Os tres grupos de estrutura juntos: cena, superficie do documento e lexica/texto/URL. */
export const structuralCompositionCases: readonly StructuralCase[] = [
    ...sceneShapeCases,
    ...surfaceCases,
    ...lexicalAndTextCases,
]

/** Nomes sensiveis decididos por token: regra do core, nao do schema (etapa 2). */
export const tokenSensitivePaths: readonly string[] = [
    'assets/secret.txt',
    'assets/secrets',
    'assets/secret/README.md',
    'assets/api-secrets.yaml',
    'assets/service_account.json',
    'assets/private_key.txt',
]

/** Hosts que apenas o parser de URL reprova (etapa 2). */
export const urlParserOnlyHrefs: readonly string[] = ['https://:8443', 'https://exa mple.com']

const baseProject = projectWith({})

export const semanticCases: readonly SemanticCase[] = [
    {
        name: 'projectId diferente do project.id do manifesto',
        contract: 'composition',
        document: compositionWith({ projectId: 'outro-projeto' }),
        project: baseProject,
        codes: ['COMPOSITION_PROJECT_ID_MISMATCH'],
        reason: 'vinculo-com-o-projectmanifest',
        schemaAccepts: true,
    },
    {
        name: 'locale diferente do project.locale do manifesto',
        contract: 'composition',
        document: compositionWith({ locale: 'en-US' }),
        project: baseProject,
        codes: ['COMPOSITION_LOCALE_MISMATCH'],
        reason: 'vinculo-com-o-projectmanifest',
        schemaAccepts: true,
    },
    {
        name: 'format.profile ausente em outputProfiles',
        contract: 'composition',
        document: compositionWith({ format: { profile: 'quadrado-social', width: 1080, height: 1080, fps: 30 } }),
        project: baseProject,
        codes: ['COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED'],
        reason: 'vinculo-com-o-projectmanifest',
        schemaAccepts: true,
    },
    {
        name: 'manifesto do projeto invalido acompanha a composicao',
        contract: 'composition',
        document: compositionWith({}),
        project: projectWith({ assetRoot: '/var/assets' }),
        codes: ['COMPOSITION_MANIFEST_INVALID'],
        reason: 'manifesto-invalido',
        schemaAccepts: true,
    },
    {
        name: 'ids de cena duplicados',
        contract: 'composition',
        document: compositionWithScenes([
            sceneWith({ id: 'abertura', content: { text: 'Abertura.' } }),
            sceneWith({ id: 'abertura', durationMs: 2000, content: { text: 'Segunda cena com o mesmo id.' } }),
        ]),
        project: baseProject,
        codes: ['COMPOSITION_SCENE_ID_DUPLICATE'],
        reason: 'unicidade-de-id-de-cena',
        schemaAccepts: true,
    },
    {
        name: 'soma de duracoes acima do inteiro seguro',
        contract: 'composition',
        document: compositionWithScenes([
            sceneWith({ id: 'primeira', durationMs: Number.MAX_SAFE_INTEGER }),
            sceneWith({ id: 'segunda', durationMs: Number.MAX_SAFE_INTEGER }),
        ]),
        project: baseProject,
        codes: ['COMPOSITION_DURATION_OVERFLOW'],
        reason: 'soma-de-duracoes',
        schemaAccepts: true,
        totalDurationMs: null,
    },
    ...tokenSensitivePaths.map((value) => ({
        name: `assetRoot com nome sensivel por token ${JSON.stringify(value)}`,
        contract: 'project' as const,
        document: projectWith({ assetRoot: value }),
        project: baseProject,
        codes: ['PROJECT_ASSET_ROOT_SENSITIVE'],
        reason: 'nomes-sensiveis-por-token' as const,
        schemaAccepts: true,
    })),
    ...tokenSensitivePaths.map((value) => ({
        name: `asset.path com nome sensivel por token ${JSON.stringify(value)}`,
        contract: 'composition' as const,
        document: compositionWithAssetPath(value),
        project: baseProject,
        codes: ['COMPOSITION_ASSET_PATH_SENSITIVE'],
        reason: 'nomes-sensiveis-por-token' as const,
        schemaAccepts: true,
    })),
    ...urlParserOnlyHrefs.map((href) => ({
        name: `href reprovado apenas pelo parser de URL ${href}`,
        contract: 'composition' as const,
        document: compositionWithHref(href),
        project: baseProject,
        codes: ['COMPOSITION_CTA_HREF_INVALID'],
        reason: 'sintaxe-de-url-no-parser' as const,
        schemaAccepts: true,
    })),
    {
        name: 'heuristicas viram warnings, nao erros',
        contract: 'composition',
        document: compositionWithScenes([
            sceneWith({ id: 'abertura', durationMs: 500, content: { text: 'X'.repeat(200) } }),
        ]),
        project: baseProject,
        codes: [],
        reason: 'heuristica-de-warning',
        schemaAccepts: true,
        warnings: ['COMPOSITION_SCENE_TEXT_LONG', 'COMPOSITION_SCENE_DURATION_SHORT', 'COMPOSITION_RENDERER_UNDECIDED'],
    },
]




