import assert from 'node:assert/strict'
import { test } from 'node:test'

import { CATALOG_VERSION, OUTPUT_PROFILES, findOutputProfile, listOutputProfiles } from '../src/output-profiles/catalog.js'
import {
    GEOMETRY_LANDSCAPE_16_9,
    GEOMETRY_PORTRAIT_4_5,
    GEOMETRY_SQUARE_1080,
    GEOMETRY_VERTICAL_9_16,
} from '../src/output-profiles/geometry.js'
import { CATALOG_RULES, POLICY_NOTES, findCatalogRule, findPolicyNote } from '../src/output-profiles/rules.js'
import type {
    CatalogRule,
    ImageOutputProfile,
    InternalDefaultRule,
    OfficialRule,
    OutputProfile,
    PendingSourceRule,
    VideoOutputProfile,
} from '../src/output-profiles/types.js'
import { RULE_CONTEXTS } from '../src/output-profiles/types.js'
import { KEBAB_CASE_PATTERN } from '../src/project-contract.js'

/**
 * Invariantes do catalogo de perfis sociais (R001-02).
 *
 * O que se testa e a **forma** do catalogo: unicidade e resolucao por ID, ordem
 * estavel, coerencia geometria x proporcao, separacao imagem/video pela uniao
 * discriminada, procedencia obrigatoria de regra oficial, ausencia tipada de
 * valor em pendencia e compatibilidade de rede/contexto entre perfil e regra.
 * Resolucao de plano e compatibilidade de Composition pertencem a R001-03.
 */

/** Ordem documentada do catalogo: imagem por rede e destino, depois video. */
const EXPECTED_PROFILE_IDS = [
    'instagram-feed-image-square',
    'instagram-feed-image-portrait',
    'instagram-stories-image',
    'facebook-feed-image-square',
    'facebook-feed-image-portrait',
    'facebook-stories-image',
    'instagram-stories-video',
    'instagram-reels-video',
    'facebook-stories-video',
    'facebook-reels-video',
    'youtube-video-horizontal',
    'youtube-shorts',
] as const

const imageProfiles = (): ImageOutputProfile[] =>
    OUTPUT_PROFILES.filter((profile) => profile.mediaKind === 'image') as ImageOutputProfile[]

const videoProfiles = (): VideoOutputProfile[] =>
    OUTPUT_PROFILES.filter((profile) => profile.mediaKind === 'video') as VideoOutputProfile[]

test('os doze perfis da matriz existem, sao unicos e resolvem por findOutputProfile', () => {
    assert.equal(OUTPUT_PROFILES.length, 12)
    const ids = OUTPUT_PROFILES.map((profile) => profile.id)
    assert.deepEqual(ids, [...EXPECTED_PROFILE_IDS], 'ordem ou conjunto de perfis divergiu da matriz')
    assert.equal(new Set(ids).size, ids.length, 'profileId duplicado')

    for (const id of EXPECTED_PROFILE_IDS) {
        const profile = findOutputProfile(id)
        assert.notEqual(profile, null, `findOutputProfile(${id}) nao resolveu`)
        assert.equal(profile?.id, id)
    }
    assert.equal(findOutputProfile('instagram-feed-image'), null, 'ID inexistente deve devolver null')
    assert.equal(findOutputProfile(''), null)
})

test('ids de perfil cabem em ProjectManifest.outputProfiles sem campo novo', () => {
    for (const profile of OUTPUT_PROFILES) {
        assert.match(profile.id, KEBAB_CASE_PATTERN, `id fora do padrao kebab-case: ${profile.id}`)
        assert.ok(profile.name.length > 0, `rotulo vazio em ${profile.id}`)
        assert.ok(Number.isInteger(profile.revision) && profile.revision >= 1, `revision invalida em ${profile.id}`)
    }
})

test('geometria declarada bate com a proporcao reduzida dos presets', () => {
    const presets: readonly [number, number, string, { width: number; height: number; aspectRatio: string }][] = [
        [1080, 1080, '1:1', GEOMETRY_SQUARE_1080],
        [1080, 1350, '4:5', GEOMETRY_PORTRAIT_4_5],
        [1080, 1920, '9:16', GEOMETRY_VERTICAL_9_16],
        [1920, 1080, '16:9', GEOMETRY_LANDSCAPE_16_9],
    ]
    for (const [width, height, ratio, geometry] of presets) {
        assert.equal(geometry.width, width)
        assert.equal(geometry.height, height)
        assert.equal(geometry.aspectRatio, ratio, `proporcao do preset ${width}x${height}`)
    }

    for (const profile of OUTPUT_PROFILES) {
        const { width, height, aspectRatio } = profile.geometry
        const expected = `${width / gcd(width, height)}:${height / gcd(width, height)}`
        assert.equal(aspectRatio, expected, `${profile.id}: proporcao diverge da geometria`)
        if (profile.publication === 'stories' || profile.publication === 'reels' || profile.publication === 'shorts') {
            assert.equal(aspectRatio, '9:16', `${profile.id}: destino vertical sem preset 9:16`)
        }
        if (profile.id.endsWith('-portrait')) assert.equal(aspectRatio, '4:5', profile.id)
        if (profile.id.endsWith('-square')) assert.equal(aspectRatio, '1:1', profile.id)
    }
})

function gcd(a: number, b: number): number {
    return b === 0 ? a : gcd(b, a % b)
}

test('uniao imagem x video: fps e contêiner existem so no ramo de video', () => {
    assert.equal(imageProfiles().length, 6, 'seis perfis de imagem (feed e Stories por rede)')
    assert.equal(videoProfiles().length, 6, 'seis perfis de video')

    for (const profile of imageProfiles()) {
        assert.ok(!('fps' in profile), `perfil de imagem com fps: ${profile.id}`)
        assert.ok(!('plannedContainer' in profile), `perfil de imagem com contêiner: ${profile.id}`)
        assert.ok(
            profile.publication === 'feed' || profile.publication === 'stories',
            `${profile.id}: imagem em destino que nao existe como imagem`,
        )
    }
    for (const profile of videoProfiles()) {
        assert.ok(Number.isInteger(profile.fps) && profile.fps >= 1, `fps sem sentido em ${profile.id}`)
    }

    const containers = videoProfiles().filter((profile) => profile.plannedContainer !== undefined)
    assert.deepEqual(containers.map((profile) => profile.id), ['youtube-video-horizontal'])
    for (const profile of containers) {
        assert.ok(profile.plannedContainerEvidence, `${profile.id} declara contêiner sem evidência`)
    }
})

test('CatalogRule: oficial exige source, interno exige evidence, pendência não tem valor nem fonte', () => {
    const ids = CATALOG_RULES.map((rule) => rule.id)
    assert.equal(new Set(ids).size, ids.length, 'ruleId duplicado no registro')

    for (const rule of CATALOG_RULES) {
        assert.equal(findCatalogRule(rule.id), rule, `findCatalogRule(${rule.id})`)
        switch (rule.kind) {
            case 'requirement':
            case 'recommendation': {
                assert.ok(rule.network !== null, `regra oficial sem rede: ${rule.id}`)
                assert.ok(rule.source.url.startsWith('https://'), `fonte nao-https: ${rule.id}`)
                assert.ok(rule.source.quote.length > 0, `citacao vazia: ${rule.id}`)
                assert.ok(rule.source.title.length > 0, `titulo vazio: ${rule.id}`)
                assert.match(rule.source.accessedOn, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$/, `data de consulta: ${rule.id}`)
                assert.ok(rule.contexts.length > 0, `regra oficial sem escopo certificado: ${rule.id}`)
                break
            }
            case 'internal-default': {
                assert.equal(rule.network, null, `default interno com rede: ${rule.id}`)
                assert.ok(rule.evidence.length > 0, `default interno sem evidencia: ${rule.id}`)
                assert.ok(!('source' in rule), `default interno com fonte externa: ${rule.id}`)
                assert.ok(!('context' in rule) && !('contexts' in rule), `default interno com contexto de uso: ${rule.id}`)
                break
            }
            case 'pending-source': {
                for (const forbidden of ['value', 'source', 'evidence'] as const) {
                    assert.ok(
                        !Object.hasOwn(rule, forbidden),
                        `pendencia ${rule.id} representa desconhecido como ${forbidden}`,
                    )
                }
                break
            }
        }
    }

    const noteIds = POLICY_NOTES.map((note) => note.id)
    assert.equal(new Set(noteIds).size, noteIds.length, 'noteId duplicado')
    assert.ok(!ids.some((id) => noteIds.includes(id)), 'nota de politica registrada como regra')
    assert.equal(findPolicyNote('PN-INEXISTENTE'), null)
})

test('regra oficial so vira exigencia quando rede e contexto batem com a fonte', () => {
    for (const profile of OUTPUT_PROFILES) {
        for (const reference of profile.rules) {
            const rule = findCatalogRule(reference.ruleId)
            assert.ok(rule, `${profile.id} referencia regra inexistente ${reference.ruleId}`)
            assert.notEqual(rule?.kind, 'pending-source', `${profile.id}: pendencia em rules, nao em pendingIds`)
            assert.equal(rule?.network, profile.network, `regra de outra rede em ${profile.id}`)
            if (reference.state === 'applies') {
                const official = rule !== null && (rule.kind === 'requirement' || rule.kind === 'recommendation') ? rule : null
                assert.ok(official, `${profile.id}: estado applies exige regra oficial com fonte`)
                // Regra **exclusiva** de app nao e exigencia de perfil: o app nunca e o
                // caminho que o nucleo exporta. Regra certificada tambem para o Studio
                // (escopo com mais de um contexto) pode ser applies -- e o caso de Shorts.
                assert.notDeepEqual(official.contexts, ['in-app'], `${profile.id}: regra so de app promovida a applies`)
            }
            if (reference.state === 'not-evaluated') {
                assert.ok(
                    profile.pendingIds.length > 0,
                    `${profile.id}: not-evaluated precisa de pendencia nomeada em pendingIds`,
                )
            }
        }
        for (const pendingId of profile.pendingIds) {
            const pending = findCatalogRule(pendingId)
            assert.ok(pending, `${profile.id} referencia pendencia inexistente ${pendingId}`)
            assert.equal(pending?.kind, 'pending-source', `${pendingId} nao e pendencia de fonte`)
            assert.equal(pending?.network, profile.network, `pendencia de outra rede em ${profile.id}`)
        }
        for (const noteId of profile.noteIds) {
            const note = findPolicyNote(noteId)
            assert.ok(note, `${profile.id} referencia nota inexistente ${noteId}`)
            assert.equal(note?.network, profile.network, `nota de outra rede em ${profile.id}`)
        }
    }

    const officials = CATALOG_RULES.filter(
        (rule): rule is OfficialRule => rule.kind === 'requirement' || rule.kind === 'recommendation',
    )
    assert.ok(officials.length > 0, 'o registro precisa ter regra oficial para o teste acima fazer sentido')
    // Regra de uma rede nao migra para a outra: hoje o Facebook tem fonte propria, entao
    // o perfil referencia R-FB-*. O que continua proibido e o perfil do Facebook
    // apontar para uma regra do Instagram, mesmo dizendo o mesmo numero.
    for (const profile of OUTPUT_PROFILES.filter((item) => item.network === 'facebook')) {
        assert.ok(
            !profile.rules.some((reference) => reference.ruleId.startsWith('R-IG-')),
            `${profile.id}: regra do Instagram foi copiada para o Facebook`,
        )
        assert.ok(
            profile.rules.every((reference) => reference.ruleId.startsWith('R-FB-')),
            `${profile.id}: regra de outra rede em perfil do Facebook`,
        )
    }
})

/** Busca regra oficial pelo ID; falha alto se a classe mudar. */
function officialRule(id: string): OfficialRule {
    const rule = findCatalogRule(id)
    if (rule === null || (rule.kind !== 'requirement' && rule.kind !== 'recommendation')) {
        throw new Error(`${id} nao e regra oficial com fonte`)
    }
    return rule
}

test('escopo de regra oficial e uma lista de contextos certificada, nunca um contexto solto', () => {
    const officials = CATALOG_RULES.filter(
        (rule): rule is OfficialRule => rule.kind === 'requirement' || rule.kind === 'recommendation',
    )
    for (const rule of officials) {
        assert.ok(rule.contexts.length > 0, `${rule.id}: escopo vazio significaria "nenhuma aplicacao", e isso e pendencia, nao regra`)
        assert.equal(new Set(rule.contexts).size, rule.contexts.length, `${rule.id}: contexto duplicado no escopo`)
        for (const context of rule.contexts) {
            assert.ok(RULE_CONTEXTS.includes(context), `${rule.id}: contexto "${context}" fora do enum do catalogo`)
        }
    }
})

test('R-YT-01 e R-YT-02 valem no app e no Studio com uma unica definicao cada', () => {
    const duration = officialRule('R-YT-01')
    const orientation = officialRule('R-YT-02')

    assert.deepEqual([...duration.contexts], ['in-app', 'studio-upload'], 'Shorts de ate tres minutos e enviado pelos dois caminhos')
    assert.deepEqual([...orientation.contexts], ['in-app', 'studio-upload'], 'a condicao de proporcao e a mesma nos dois caminhos')

    // Uma so definicao por regra: o numero/valor mora no `value`, nao em tabela por contexto.
    assert.deepEqual(duration.value, { kind: 'max-duration-seconds', seconds: 180 })
    assert.deepEqual(orientation.value, { kind: 'orientation-any-of', orientations: ['square', 'portrait'] })

    // Procedencia do escopo amplo sao as proprias fontes, citadas nos dois caminhos.
    assert.match(duration.source.quote, /pelo app YouTube e pelo YouTube Studio/)
    assert.match(orientation.source.note ?? '', /YouTube Studio/)
    assert.match(orientation.source.note ?? '', /app/)
})

test('Instagram mantem a separacao entre regra de app e regra de API', () => {
    // Alargamos o escopo de Shorts, nao o de qualquer regra de app: no Instagram a
    // exigencia certificada continua a da API, e as de app seguem informational.
    assert.deepEqual([...officialRule('R-IG-01').contexts], ['api-publishing'])
    assert.deepEqual([...officialRule('R-IG-04').contexts], ['in-app'])
    assert.deepEqual([...officialRule('R-IG-05').contexts], ['in-app'])

    const storiesVideo = findOutputProfile('instagram-stories-video')
    assert.equal(storiesVideo?.rules.find((reference) => reference.ruleId === 'R-IG-04')?.state, 'informational')
    assert.equal(storiesVideo?.rules.find((reference) => reference.ruleId === 'R-IG-05')?.state, 'informational')
    assert.equal(
        storiesVideo?.rules.some((reference) => reference.ruleId === 'R-IG-01' && reference.state === 'applies'),
        false,
        'regra de API nao pode ser applies num perfil cujo caminho certificado e o app',
    )
})

test('as pendencias promovidas saem do registro e as restantes nomeiam o que falta', () => {
    for (const resolvedId of [
        'P-IG-01',
        'P-IG-02',
        'P-IG-03',
        'P-IG-04',
        'P-IG-05',
        'P-FB-02',
        'P-YT-01',
        'P-YT-02',
    ]) {
        assert.equal(findCatalogRule(resolvedId), null, `${resolvedId} foi certificada: nao pode continuar pendente`)
    }

    const pendings = CATALOG_RULES.filter((rule): rule is PendingSourceRule => rule.kind === 'pending-source')
    assert.deepEqual(pendings.map((rule) => rule.id).sort(), ['P-FB-01', 'P-FB-03', 'P-HELP-01', 'P-YT-03'])
    for (const pending of pendings) {
        assert.match(pending.statement, /n[ãa]o |sem /, `${pending.id}: pendencia precisa dizer o que falta, nao so existir`)
    }
})

test('duracao de Reels e de Story por API tem numero, fonte e valor avaliavel', () => {
    const reels = officialRule('R-IG-09')
    const story = officialRule('R-IG-08')

    assert.deepEqual([...reels.contexts], ['api-publishing'], 'a pagina de contêiner e do caminho por API')
    assert.deepEqual(reels.value, { kind: 'max-duration-seconds', seconds: 900 })
    assert.match(reels.source.quote, /Duration: 15 mins maximum, 3 seconds minimum/)
    assert.deepEqual(story.value, { kind: 'max-duration-seconds', seconds: 60 })
    assert.match(story.source.quote, /Duration: 60 seconds maximum, 3 seconds minimum/)

    // O minimo de 3 segundos e certificado pela mesma linha, mas RuleValue nao tem
    // "duracao minima": ele fica no enunciado e na citacao. Transforma-lo em valor
    // geraria erro de plano que a fonte nao sustenta.
    assert.match(reels.statement, /3 segundos/)
    assert.match(story.statement, /3 segundos/)
})

test('o bloco de imagem da API do Instagram certifica faixa de proporcao e largura', () => {
    // Resposta de P-IG-03: a faixa de proporcao (4:5 a 1.91:1) e a janela de largura
    // (320 a 1440) sao limites de range, e a uniao so expressa lista fechada ou
    // minimo. Sem valor, o relatorio diz que o documento nao traz o dado; com um
    // valor inventado, diria "passou" sem verificar nada.
    const image = officialRule('R-IG-06')
    assert.equal(image.value, undefined, 'faixa certificada nao cabe em RuleValue')
    assert.equal(image.kind, 'requirement')
    assert.match(image.statement, /4:5/)
    assert.match(image.statement, /1\.91:1/)
    assert.match(image.statement, /320/)
    assert.match(image.statement, /1440/)
    assert.match(image.source.quote, /Aspect ratio: Must be within a 4:5 to 1\.91:1 range/)
})

test('o Stories de imagem por API exige JPEG com fonte da propria publicacao', () => {
    const story = officialRule('R-IG-07')
    assert.equal(story.kind, 'requirement')
    assert.deepEqual([...story.contexts], ['api-publishing'])
    assert.deepEqual(story.value, { kind: 'allowed-formats', formats: ['jpeg'] })
    assert.match(story.source.quote, /Format: JPEG/)
    assert.match(story.source.url, /instagram-graph-api\/reference\/ig-user\/media/)
})

test('o Facebook certifica os proprios formatos de imagem e aceita PNG', () => {
    // Resposta de P-FB-02, e ela nega a migracao: a regra JPEG do Instagram nao vale
    // para o Facebook, cuja pagina de foto lista PNG, BMP, GIF e TIFF.
    const photos = officialRule('R-FB-01')
    const storyPhotos = officialRule('R-FB-02')
    assert.deepEqual(photos.value, { kind: 'allowed-formats', formats: ['jpeg', 'bmp', 'png', 'gif', 'tiff'] })
    assert.match(photos.source.quote, /\.jpeg, \.bmp, \.png, \.gif, \.tiff/)
    assert.match(photos.source.quote, /Files can not exceed 10MB/)
    assert.deepEqual(storyPhotos.value, { kind: 'allowed-formats', formats: ['jpeg', 'bmp', 'png', 'gif', 'tiff'] })
    assert.equal(storyPhotos.source.url, 'https://developers.facebook.com/documentation/video-api/page-stories-api')
})

test('resolucao minima e teto de duracao do video do Facebook saem da pendencia', () => {
    const storyDuration = officialRule('R-FB-03')
    const storyResolution = officialRule('R-FB-04')
    const reelsDuration = officialRule('R-FB-06')
    const reelsResolution = officialRule('R-FB-07')

    assert.deepEqual(storyResolution.value, { kind: 'min-dimensions', width: 540, height: 960 })
    assert.match(storyResolution.source.quote, /Minimum is 540 x 960 pixels/)
    assert.deepEqual(reelsResolution.value, { kind: 'min-dimensions', width: 540, height: 960 })
    assert.match(reelsResolution.source.url, /video-api\/guides\/reels-publishing/)

    assert.deepEqual(storyDuration.value, { kind: 'max-duration-seconds', seconds: 60 })
    assert.deepEqual(reelsDuration.value, { kind: 'max-duration-seconds', seconds: 90 })
})

test('a contradicao interna da pagina de Stories e registrada, nao apagada', () => {
    // A mesma pagina imprime "3 to 90 seconds." na tabela de video e, na secao
    // Limitations, "A video story can not exceed 60 seconds". Promovemos o teto mais
    // estrito porque as duas frases vem da mesma fonte: nada autoriza um video-story
    // de ate 90 segundos.
    const duration = officialRule('R-FB-03')
    assert.match(duration.source.quote, /A video story can not exceed 60 seconds/)
    assert.match(duration.source.note ?? '', /3 to 90 seconds/)
    // A variante pt-BR da pagina traduz "3 to 90 seconds" como "3 a 9 segundos": por
    // isso toda citacao desta etapa sai da locale EN.
    assert.match(duration.source.note ?? '', /3 a 9 segundos/)
})

test('limite certificado que a uniao nao expressa fica no enunciado, sem valor inventado', () => {
    for (const id of ['R-IG-06', 'R-IG-10', 'R-FB-05', 'R-FB-08', 'R-YT-05', 'R-YT-06', 'R-YT-07']) {
        const rule = officialRule(id)
        assert.equal(rule.value, undefined, `${id}: nenhum numero deste bloco cabe em RuleValue`)
        assert.match(rule.statement, /\d/, `${id}: o numero certificado precisa aparecer no enunciado`)
    }
    assert.match(officialRule('R-FB-05').statement, /24 a 60/)
    assert.match(officialRule('R-YT-06').statement, /256 GB/)
    assert.match(officialRule('R-YT-05').statement, /15 minutos/)
})

test('o teto do app e o piso da API continuam duas regras separadas', () => {
    // Instagram no app aceita proporcao ate 3:4 (1080x1440); a API exige 4:5 para cima.
    // Unir as duas apagaria uma divergencia real, e o app nunca e o caminho que o
    // nucleo exporta: a regra de la entra como informational.
    const app = officialRule('R-IG-10')
    const api = officialRule('R-IG-06')
    assert.equal(app.kind, 'recommendation')
    assert.deepEqual([...app.contexts], ['in-app'])
    assert.match(app.source.url, /help\.instagram\.com/)
    assert.match(app.source.quote, /between 1\.91:1 and 3:4/)
    assert.deepEqual([...api.contexts], ['api-publishing'])

    for (const profile of OUTPUT_PROFILES.filter((item) => item.network === 'instagram' && item.publication === 'feed')) {
        assert.equal(
            profile.rules.find((reference) => reference.ruleId === 'R-IG-10')?.state,
            'informational',
            `${profile.id}: regra de app nunca e exigencia do plano`,
        )
        assert.equal(profile.rules.find((reference) => reference.ruleId === 'R-IG-06')?.state, 'applies')
    }
})

test('video longo do YouTube: 15 minutos e 256 GB ou 12 horas viram regras com fonte', () => {
    const minutes = officialRule('R-YT-05')
    const size = officialRule('R-YT-06')
    assert.deepEqual([...minutes.contexts], ['in-app', 'studio-upload'], 'as duas abas da pagina repetem o numero')
    assert.deepEqual([...size.contexts], ['in-app', 'studio-upload'])
    assert.match(minutes.source.quote, /up to 15 minutes long/)
    assert.match(size.source.quote, /256 GB or 12 hours, whichever is less/)

    const profile = findOutputProfile('youtube-video-horizontal')
    assert.deepEqual([...(profile?.pendingIds ?? [])], [], 'P-YT-01 foi certificada')
    assert.equal(profile?.rules.find((reference) => reference.ruleId === 'R-YT-05')?.state, 'applies')
    assert.equal(profile?.rules.find((reference) => reference.ruleId === 'R-YT-06')?.state, 'applies')
})

test('cota da Data API e nota de politica e o limite de arquivo do upload e regra', () => {
    const insert = officialRule('R-YT-07')
    assert.deepEqual([...insert.contexts], ['api-publishing'])
    assert.match(insert.source.quote, /Maximum file size: 256GB/)

    const quota = findPolicyNote('PN-YT-02')
    assert.ok(quota, 'cota e informacao que o nucleo nao verifica: nota de politica, nao regra')
    assert.match(quota?.source.quote ?? '', /default daily limit of 100 per day/)
    assert.ok(!findCatalogRule('PN-YT-02'), 'nota de politica nao entra no registro de regras')

    const profile = findOutputProfile('youtube-video-horizontal')
    assert.ok(profile?.noteIds.includes('PN-YT-02'), 'o perfil publicado por API mostra a cota')
    assert.equal(profile?.rules.find((reference) => reference.ruleId === 'R-YT-07')?.state, 'applies')
})

test('Shorts continua sem contêiner e peso certificados e isso tem ID', () => {
    // A pagina de Shorts so certifica duracao e proporcao; a lista geral de
    // contêineres aceitos pelo YouTube nao e especifica de Shorts nem traz peso.
    // Resolver pendencia nao e preencher buraco com numero vizinho.
    const pending = findCatalogRule('P-YT-03')
    assert.equal(pending?.kind, 'pending-source')
    assert.equal(pending?.network, 'youtube')
    const shorts = findOutputProfile('youtube-shorts')
    assert.ok(shorts)
    assert.equal(
        (shorts as VideoOutputProfile).plannedContainer,
        undefined,
        'sem fonte especifica, o perfil nao declara contêiner',
    )
})

test('revisao de perfil sobe quando regras ou pendencias mudam; a versao do catalogo nao', () => {
    // A R001-02 subiu shorts para 2 pelo escopo novo de Shorts; a R001-05 mudou
    // regras/pendencias de todo o catalogo, entao cada perfil sobe uma vez e Shorts
    // sobe duas. Revisao e o mecanismo de invalidar artefato antigo: o plano com a
    // revisao prévia passa a dar OUTPUT_PLAN_PROFILE_REVISION_MISMATCH.
    assert.equal(findOutputProfile('youtube-shorts')?.revision, 3, 'Shorts mudou de escopo (R001-04) e de pendencia (R001-05)')
    for (const profile of OUTPUT_PROFILES.filter((item) => item.id !== 'youtube-shorts')) {
        assert.equal(profile.revision, 2, `${profile.id}: regras ou pendencias mudaram na R001-05, revisao sobe (§5)`)
    }
    // Versao de catalogo e contrato, nao conteudo: a tabela continua a geracao 1 e
    // um numero novo so entra por decisao de contrato (schema `const` + §6.1).
    assert.equal(CATALOG_VERSION, '1', 'promover evidencia nao e mudar o contrato da tabela')
})

test('Stories de imagem por API tem certificacao propria: nem pendencia, nem regra emprestada do feed', () => {
    // A R001-02 deixou R-IG-01 em `not-evaluated` nesse perfil porque a unica pagina
    // lida era a de compartilhamento no app. A pagina de contêiner de usuaria do
    // Instagram traz o bloco "Story Image Specifications" com `Format: JPEG`: a
    // aplicacao esta certificada, entao sai a pendencia e entra a regra da publicacao.
    const stories = findOutputProfile('instagram-stories-image')
    assert.notEqual(stories, null)
    assert.equal(stories?.rules.find((reference) => reference.ruleId === 'R-IG-07')?.state, 'applies')
    assert.ok(
        !stories?.rules.some((reference) => reference.ruleId === 'R-IG-01'),
        'a regra do feed nao e a fonte desta publicacao: perfil aponta para R-IG-07',
    )
    assert.deepEqual([...(stories?.pendingIds ?? [])], [], 'nenhuma pendencia de Instagram sobra depois da promocao')

    const storiesVideo = findOutputProfile('instagram-stories-video')
    assert.equal(storiesVideo?.rules.find((reference) => reference.ruleId === 'R-IG-04')?.state, 'informational')
    assert.equal(storiesVideo?.rules.find((reference) => reference.ruleId === 'R-IG-05')?.state, 'informational')

    const feed = findOutputProfile('instagram-feed-image-square')
    assert.equal(feed?.rules.find((reference) => reference.ruleId === 'R-IG-01')?.state, 'applies')
})

test('orientacao permitida pelo destino nao e a geometria exata do preset', () => {
    const rule = findCatalogRule('R-YT-02')
    assert.ok(rule && rule.kind !== 'pending-source')
    const value = (rule as OfficialRule).value
    assert.equal(value?.kind, 'orientation-any-of', 'Shorts precisa de condicao de orientacao, nao de lista de razoes')
    assert.deepEqual((value as { kind: 'orientation-any-of'; orientations: readonly string[] }).orientations, [
        'square',
        'portrait',
    ])

    const shorts = findOutputProfile('youtube-shorts')
    assert.equal(shorts?.geometry.aspectRatio, '9:16', 'o preset interno continua 1080x1920')
    assert.notEqual(
        value?.kind,
        'aspect-ratios',
        'a condicao oficial nao pode ser reduzida as proporcoes exatas dos presets',
    )
})

test('limite certificado so onde a fonte o da; desconhecido permanece pendencia', () => {
    const shortsDuration = findCatalogRule('R-YT-01') as OfficialRule
    assert.deepEqual(shortsDuration.value, { kind: 'max-duration-seconds', seconds: 180 })

    for (const profile of OUTPUT_PROFILES) {
        const serialized = JSON.stringify(profile)
        assert.ok(!serialized.includes('Infinity'), `${profile.id} usa Infinity como desconhecido`)
        assert.ok(!serialized.includes('"null"'), `${profile.id} serializa null como valor`)
        assert.ok(
            !/"(maxDuration|duration|weight|maxWidth|maxHeight)[A-Za-z]*":/.test(serialized),
            `${profile.id} declara um limite que nao tem fonte`,
        )
    }

    // Duracao de Reels por API saiu da pendencia: a pagina de contêiner certifica o
    // numero, entao ele vira `value` avaliavel. O que nao tem numero oficial
    // (peso de video do Facebook, contêiner/peso de Short) continua pendencia nomeada.
    const reels = findOutputProfile('instagram-reels-video')
    assert.equal(reels?.rules.find((reference) => reference.ruleId === 'R-IG-09')?.state, 'applies')
    assert.deepEqual((officialRule('R-IG-09').value ?? { kind: 'sem-valor' }).kind, 'max-duration-seconds')
    assert.deepEqual([...(reels?.pendingIds ?? [])], [], 'as pendencias do Instagram foram resolvidas')
    assert.deepEqual(
        [...(findOutputProfile('facebook-reels-video')?.pendingIds ?? [])],
        ['P-FB-03'],
        'peso maximo de arquivo de video continua sem fonte',
    )
    assert.deepEqual(
        [...(findOutputProfile('youtube-shorts')?.pendingIds ?? [])],
        ['P-YT-03'],
        'contêiner e peso especificos de Short continuam sem fonte',
    )
})

test('defaults internos: compartilháveis por network null e coerentes com o perfil', () => {
    for (const profile of OUTPUT_PROFILES) {
        assert.ok(profile.defaults.length > 0, `${profile.id} sem default interno`)
        for (const defaultId of profile.defaults) {
            const rule = findCatalogRule(defaultId)
            assert.ok(rule, `${profile.id} referencia default inexistente ${defaultId}`)
            assert.equal(rule?.kind, 'internal-default', `${defaultId} nao e default interno`)
            const value = (rule as InternalDefaultRule).value
            if (value.kind === 'geometry') {
                assert.deepEqual(
                    { width: value.width, height: value.height, aspectRatio: value.aspectRatio },
                    profile.geometry,
                    `${profile.id} instancia default de geometria divergente`,
                )
            }
            if (value.kind === 'fps' && profile.mediaKind === 'video') {
                assert.equal(profile.fps, value.fps, `${profile.id} diverge do fps default`)
            }
        }
    }

    const square = findCatalogRule('D-LOCAL-01') as InternalDefaultRule
    assert.equal(square.network, null, 'default interno compartilhavel precisa de network null')
    for (const rule of CATALOG_RULES) {
        if (rule.kind !== 'internal-default') continue
        assert.ok(
            !rule.evidence.includes('marcas/') && !rule.evidence.includes('marcasalao'),
            `${rule.id}: evidencia aponta caminho de cliente`,
        )
    }
})

test('filtros de listagem por rede, publicacao e tipo de midia', () => {
    assert.equal(listOutputProfiles().length, 12, 'sem filtro devolve o catalogo inteiro')
    assert.equal(listOutputProfiles({}).length, 12, 'filtro vazio nao restringe')

    for (const network of ['instagram', 'facebook', 'youtube'] as const) {
        const filtered = listOutputProfiles({ network })
        assert.ok(filtered.length > 0, `nenhum perfil para ${network}`)
        assert.ok(filtered.every((profile) => profile.network === network))
    }

    assert.equal(listOutputProfiles({ network: 'instagram', publication: 'feed' }).length, 2)
    assert.equal(listOutputProfiles({ publication: 'stories', mediaKind: 'image' }).length, 2)
    assert.deepEqual(
        listOutputProfiles({ network: 'youtube', publication: 'shorts' }).map((profile) => profile.id),
        ['youtube-shorts'],
    )
    assert.deepEqual(listOutputProfiles({ network: 'youtube', publication: 'feed' }), [])
    assert.deepEqual(listOutputProfiles({ mediaKind: 'image', publication: 'reels' }), [])

    assert.ok(listOutputProfiles({ mediaKind: 'image' }).length >= 1)
    for (const network of ['instagram', 'facebook'] as const) {
        assert.equal(listOutputProfiles({ network, publication: 'reels' }).length, 1, `Reels de ${network}`)
    }
    assert.equal(listOutputProfiles({ network: 'youtube', publication: 'shorts' }).length, 1)
})

test('leitura do catalogo e deterministica e nao muta filtro nem registro', () => {
    assert.equal(CATALOG_VERSION, '1')

    assert.equal(JSON.stringify(listOutputProfiles()), JSON.stringify(listOutputProfiles()), 'listagem instavel')
    assert.equal(JSON.stringify(OUTPUT_PROFILES, null, 2), JSON.stringify(listOutputProfiles(), null, 2))

    const filter = { network: 'instagram' as const, mediaKind: 'image' as const }
    const filterCopy = JSON.stringify(filter)
    const filtered = listOutputProfiles(filter)
    assert.equal(JSON.stringify(filter), filterCopy, 'filtro foi mutado')
    assert.equal(OUTPUT_PROFILES.length, 12)
    assert.ok(filtered.every((profile) => profile.network === 'instagram' && profile.mediaKind === 'image'))

    const ids = OUTPUT_PROFILES.map((profile) => profile.id)
    assert.deepEqual(ids, [...EXPECTED_PROFILE_IDS], 'ordem do catalogo nao e a documentada')
})

test('capacidade de exportacao e informada como observada, nunca como integrada', () => {
    for (const profile of OUTPUT_PROFILES) {
        assert.ok(
            ['preset-only', 'canvas-template-mapped', 'tool-export-observed'].includes(profile.exportState),
            `${profile.id} declara exportState desconhecido`,
        )
        assert.ok(profile.exportEvidence.length > 0, `${profile.id} declara export sem evidencia`)
        for (const evidence of profile.exportEvidence) {
            assert.ok(!/integrada|integrated/i.test(evidence), `${profile.id}: ${evidence} promete exportacao integrada`)
            assert.ok(!evidence.includes('marcas/'), `${profile.id}: evidencia de caminho de cliente`)
        }
        if (profile.exportState === 'canvas-template-mapped') {
            assert.ok(
                profile.exportEvidence.some((evidence) => evidence.startsWith('templates/')),
                `${profile.id}: canvas-template-mapped sem template correspondente`,
            )
        }
    }

    const reels = findOutputProfile('instagram-reels-video')
    assert.ok(reels?.exportEvidence.some((evidence) => evidence.startsWith('tools/')), 'ferramenta de exportacao observada')
})

test('independencia: nenhum dado de cliente nos dados do catalogo', () => {
    const serialized = (JSON.stringify(OUTPUT_PROFILES) + JSON.stringify(CATALOG_RULES) + JSON.stringify(POLICY_NOTES)).toLowerCase()
    for (const forbidden of ['marcasalao', 'marca salão', 'marca salao', 'multitrack', 'postiz', '.com.br', 'capcut']) {
        assert.ok(!serialized.includes(forbidden), `dado de cliente no catalogo: ${forbidden}`)
    }
    // Procedencia oficial e permitida e necessaria: sem URL a regra perde a origem.
    assert.ok(serialized.includes('https://support.google.com/youtube/'))
    assert.ok(serialized.includes('https://developers.facebook.com/'))
})

test('combinacoes proibidas: o tipo rejeita ate atraves de variavel intermediaria', () => {
    const baseImage = imageProfiles()[0]
    assert.ok(baseImage)

    const fpsValue = 30
    // @ts-expect-error fps e proibido no ramo image mesmo vindo de uma variavel
    const imageWithFps: ImageOutputProfile = { ...baseImage, fps: fpsValue }

    const containerValue = 'mp4'
    // @ts-expect-error conteiner planificado nao existe em perfil de imagem
    const imageWithContainer: ImageOutputProfile = { ...baseImage, plannedContainer: containerValue }

    const { fps: _omitted, ...videoWithoutFps } = videoProfiles()[0] as VideoOutputProfile
    // @ts-expect-error perfil de video exige fps
    const brokenVideo: VideoOutputProfile = videoWithoutFps

    const unknownNetwork = 'tiktok'
    // @ts-expect-error rede fora do catalogo nao e aceitavel por tipo
    const tiktokProfile: OutputProfile = { ...baseImage, network: unknownNetwork }

    const state = 'verified'
    // @ts-expect-error estado de aplicacao desconhecido
    const badState: OutputProfile = { ...baseImage, rules: [{ ruleId: 'R-IG-01', state }] }

    // Os cinco casos acima so existem para o compilador; em runtime viram dados extras.
    assert.equal(imageWithFps.fps, fpsValue)
    assert.equal(imageWithContainer.plannedContainer, containerValue)
    assert.equal(brokenVideo.mediaKind, 'video')
    assert.equal(tiktokProfile.network, unknownNetwork)
    assert.equal(badState.rules[0]?.state, state)
})

test('combinacoes proibidas: classes de regra nao se misturam', () => {
    const pending: PendingSourceRule = {
        id: 'P-TEST-01',
        network: 'youtube',
        kind: 'pending-source',
        context: null,
        statement: 'Pendencia de exemplo.',
    }
    const seconds = 30
    // @ts-expect-error pendencia nao pode carregar value: desconhecido nao e numero
    const pendingWithValue: PendingSourceRule = { ...pending, value: { kind: 'max-duration-seconds', seconds } }

    const official = CATALOG_RULES.find(
        (rule): rule is OfficialRule => rule.kind === 'requirement' && rule.id === 'R-YT-01',
    )
    assert.ok(official)
    // @ts-expect-error regra oficial sem source nao existe
    const officialWithoutSource: OfficialRule = { ...official, source: undefined }

    const internal = CATALOG_RULES.find((rule): rule is InternalDefaultRule => rule.kind === 'internal-default')
    assert.ok(internal)
    // @ts-expect-error default interno nao tem contexto de uso
    const internalWithContext: InternalDefaultRule = { ...internal, contexts: ['in-app'] }

    const orientation = 'diagonal'
    // @ts-expect-error orientacao inexistente na condicao oficial de Shorts
    const badOrientation: CatalogRule = { ...official, value: { kind: 'orientation-any-of', orientations: [orientation] } }

    assert.equal(pendingWithValue.kind, 'pending-source')
    assert.equal(officialWithoutSource.id, 'R-YT-01')
    assert.equal(internalWithContext.id, internal.id)
    assert.equal(badOrientation.kind, 'requirement')
})
