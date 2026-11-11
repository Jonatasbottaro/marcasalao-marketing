/**
 * Schema do OutputPlan (R001-03): paridade entre o espelho draft-07 executado
 * em ajv e o validador TypeScript, sobre os mesmos objetos.
 *
 * O corpus deste contrato vive neste arquivo, e nao em `contract-corpus.ts`:
 * aquele arquivo e o corpus compartilhado dos dois contratos antigos e sua
 * assercao de espaco de codigos so aceita `PROJECT_`/`COMPOSITION_`. OutputPlan
 * tem codigos proprios (`OUTPUT_*`) e uma segunda entrada obrigatoria (o
 * catalogo), entao o corpus e proprio.
 *
 * Separacao exigida pela revisao:
 * - **estrutural**: a regra mora na forma do documento, os dois motores precisam
 *   chegar ao mesmo veredicto;
 * - **semantic**: a regra depende do projeto, do catalogo ou do contexto — o
 *   TypeScript e a autoridade, e o que o schema decide fica registrado por caso.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    catalogProfileRevision,
    catalogProject,
    imagePlanWith,
    moduleRoot,
    outputPlanSchemaCheck,
    validateOutputPlanDocument,
    videoPlanWith,
    withoutFields,
} from '../contract-harness.js'
import {
    OUTPUT_PLAN_IMAGE_FIELDS,
    OUTPUT_PLAN_TOP_LEVEL_FIELDS,
    OUTPUT_PLAN_VIDEO_FIELDS,
} from '../../src/output-plan-contract.js'
import { OUTPUT_PROFILES } from '../../src/output-profiles/catalog.js'
import { CATALOG_VERSION, OUTPUT_MEDIA_KINDS, RULE_CONTEXTS } from '../../src/output-profiles/types.js'

interface StructuralCase {
    readonly name: string
    readonly document: unknown
    readonly valid: boolean
    readonly codes?: readonly string[]
}

interface SemanticCase {
    readonly name: string
    readonly document: Record<string, unknown>
    readonly project: Record<string, unknown>
    readonly codes: readonly string[]
    readonly warnings?: readonly string[]
    /** O que o schema decide sobre o mesmo documento (registrado, nao exigido). */
    readonly schemaAccepts: boolean
    readonly reason: string
}

const structuralCases: StructuralCase[] = [
    { name: 'plano de video sem contexto declarado', document: videoPlanWith(), valid: true },
    { name: 'plano de video com contexto studio-upload', document: videoPlanWith({ ruleContext: 'studio-upload' }), valid: true },
    { name: 'plano de video com contexto api-publishing', document: videoPlanWith({ ruleContext: 'api-publishing' }), valid: true },
    { name: 'plano de video com contexto ads', document: videoPlanWith({ ruleContext: 'ads' }), valid: true },
    { name: 'plano de imagem', document: imagePlanWith(), valid: true },
    { name: 'plano de imagem com contexto in-app', document: imagePlanWith({ ruleContext: 'in-app' }), valid: true },
    { name: 'entrada nula', document: null, valid: false, codes: ['OUTPUT_PLAN_INVALID'] },
    { name: 'entrada string', document: 'plano', valid: false, codes: ['OUTPUT_PLAN_INVALID'] },
    { name: 'entrada array', document: [videoPlanWith()], valid: false, codes: ['OUTPUT_PLAN_INVALID'] },
    {
        name: 'campo desconhecido no topo',
        document: videoPlanWith({ exportReady: true }),
        valid: false,
        codes: ['OUTPUT_PLAN_UNKNOWN_FIELD'],
    },
    {
        name: 'campo desconhecido aninhado no payload',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, codec: 'h264' } }),
        valid: false,
        codes: ['OUTPUT_PLAN_UNKNOWN_FIELD'],
    },
    {
        name: 'fps dentro do payload de imagem',
        document: imagePlanWith({ image: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_UNKNOWN_FIELD'],
    },
    {
        name: 'duracao dentro do payload de video',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, durationMs: 5000 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_UNKNOWN_FIELD'],
    },
    {
        name: 'contener dentro do payload de video',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 30, container: 'mp4' } }),
        valid: false,
        codes: ['OUTPUT_PLAN_UNKNOWN_FIELD'],
    },
    { name: 'schemaVersion 2', document: videoPlanWith({ schemaVersion: 2 }), valid: false, codes: ['OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED'] },
    { name: 'schemaVersion como string', document: videoPlanWith({ schemaVersion: '1' }), valid: false, codes: ['OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED'] },
    { name: 'schemaVersion ausente', document: withoutFields(videoPlanWith(), ['schemaVersion']), valid: false, codes: ['OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED'] },
    { name: 'catalogVersion divergente da suportada', document: videoPlanWith({ catalogVersion: '2' }), valid: false, codes: ['OUTPUT_PLAN_CATALOG_VERSION_UNKNOWN'] },
    { name: 'catalogVersion numerico', document: videoPlanWith({ catalogVersion: 1 }), valid: false, codes: ['OUTPUT_PLAN_CATALOG_VERSION_UNKNOWN'] },
    { name: 'projectId fora de kebab-case', document: videoPlanWith({ projectId: 'Projeto_Teste' }), valid: false, codes: ['OUTPUT_PLAN_PROJECT_ID_INVALID'] },
    { name: 'projectId vazio', document: videoPlanWith({ projectId: '' }), valid: false, codes: ['OUTPUT_PLAN_PROJECT_ID_INVALID'] },
    { name: 'projectId numerico', document: videoPlanWith({ projectId: 7 }), valid: false, codes: ['OUTPUT_PLAN_PROJECT_ID_INVALID'] },
    { name: 'profileId fora de kebab-case', document: videoPlanWith({ profileId: 'YouTube Shorts' }), valid: false, codes: ['OUTPUT_PROFILE_ID_INVALID'] },
    { name: 'profileRevision zero', document: videoPlanWith({ profileRevision: 0 }), valid: false, codes: ['OUTPUT_PLAN_PROFILE_REVISION_INVALID'] },
    { name: 'profileRevision fracionaria', document: videoPlanWith({ profileRevision: 1.5 }), valid: false, codes: ['OUTPUT_PLAN_PROFILE_REVISION_INVALID'] },
    {
        name: 'profileRevision acima de Number.MAX_SAFE_INTEGER',
        document: videoPlanWith({ profileRevision: 9007199254740992 }),
        valid: false,
        codes: ['OUTPUT_PLAN_PROFILE_REVISION_INVALID'],
    },
    // mediaKind invalido tambem derruba o payload: sem tipo nao ha como resolver qual dos dois ramos e o esperado.
    {
        name: 'mediaKind audio',
        document: videoPlanWith({ mediaKind: 'audio' }),
        valid: false,
        codes: ['OUTPUT_PLAN_MEDIA_KIND_INVALID', 'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'],
    },
    {
        name: 'mediaKind IMAGE em maiusculo',
        document: imagePlanWith({ mediaKind: 'IMAGE' }),
        valid: false,
        codes: ['OUTPUT_PLAN_MEDIA_KIND_INVALID', 'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'],
    },
    {
        name: 'mediaKind ausente com payload presente',
        document: withoutFields(videoPlanWith(), ['mediaKind']),
        valid: false,
        codes: ['OUTPUT_PLAN_MEDIA_KIND_INVALID', 'OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'],
    },
    { name: 'ruleContext null explicito', document: videoPlanWith({ ruleContext: null }), valid: false, codes: ['OUTPUT_PLAN_RULE_CONTEXT_INVALID'] },
    { name: 'ruleContext fora do enum', document: videoPlanWith({ ruleContext: 'whatsapp' }), valid: false, codes: ['OUTPUT_PLAN_RULE_CONTEXT_INVALID'] },
    {
        name: 'payload image e video juntos',
        document: { ...videoPlanWith(), image: { width: 1080, height: 1920, aspectRatio: '9:16' } },
        valid: false,
        codes: ['OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'],
    },
    { name: 'plano de video sem payload', document: withoutFields(videoPlanWith(), ['video']), valid: false, codes: ['OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'] },
    { name: 'plano de imagem sem payload', document: withoutFields(imagePlanWith(), ['image']), valid: false, codes: ['OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'] },
    {
        name: 'payload de imagem no plano de video',
        document: { ...withoutFields(videoPlanWith(), ['video']), image: { width: 1080, height: 1920, aspectRatio: '9:16' } },
        valid: false,
        codes: ['OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'],
    },
    { name: 'payload como string', document: videoPlanWith({ video: '1080x1920' }), valid: false, codes: ['OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'] },
    { name: 'payload array', document: videoPlanWith({ video: [{ width: 1080 }] }), valid: false, codes: ['OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH'] },
    {
        name: 'payload vazio',
        document: videoPlanWith({ video: {} }),
        valid: false,
        codes: [
            'OUTPUT_PLAN_DIMENSIONS_INVALID',
            'OUTPUT_PLAN_DIMENSIONS_INVALID',
            'OUTPUT_PLAN_ASPECT_RATIO_INVALID',
            'OUTPUT_PLAN_FPS_INVALID',
        ],
    },
    {
        name: 'dimensao zero',
        document: videoPlanWith({ video: { width: 0, height: 1920, aspectRatio: '9:16', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_DIMENSIONS_INVALID'],
    },
    {
        name: 'dimensao negativa',
        document: videoPlanWith({ video: { width: -1080, height: 1920, aspectRatio: '9:16', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_DIMENSIONS_INVALID'],
    },
    {
        name: 'dimensao fracionaria',
        document: videoPlanWith({ video: { width: 1080.5, height: 1920, aspectRatio: '9:16', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_DIMENSIONS_INVALID'],
    },
    {
        name: 'dimensao acima de Number.MAX_SAFE_INTEGER',
        document: videoPlanWith({ video: { width: 9007199254740992, height: 1920, aspectRatio: '9:16', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_DIMENSIONS_INVALID'],
    },
    {
        name: 'proporcao com barra',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9/16', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_ASPECT_RATIO_INVALID'],
    },
    {
        name: 'proporcao com tres termos',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16:9', fps: 30 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_ASPECT_RATIO_INVALID'],
    },
    {
        name: 'proporcao com texto',
        document: imagePlanWith({ image: { width: 1080, height: 1920, aspectRatio: 'vertical' } }),
        valid: false,
        codes: ['OUTPUT_PLAN_ASPECT_RATIO_INVALID'],
    },
    { name: 'fps zero', document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 0 } }), valid: false, codes: ['OUTPUT_PLAN_FPS_INVALID'] },
    { name: 'fps 121', document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 121 } }), valid: false, codes: ['OUTPUT_PLAN_FPS_INVALID'] },
    {
        name: 'fps fracionario',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 29.97 } }),
        valid: false,
        codes: ['OUTPUT_PLAN_FPS_INVALID'],
    },
    {
        name: 'fps ausente no payload de video',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16' } }),
        valid: false,
        codes: ['OUTPUT_PLAN_FPS_INVALID'],
    },
]

const semanticCases: SemanticCase[] = [
    {
        name: 'profileId fora do catalogo',
        document: videoPlanWith({ profileId: 'youtube-shorts-v2' }),
        project: catalogProject(),
        codes: ['OUTPUT_PROFILE_UNKNOWN'],
        schemaAccepts: true,
        reason: 'o catalogo e dado do core; o schema so ve kebab-case',
    },
    {
        name: 'perfil existente fora do allowlist do projeto',
        document: videoPlanWith(),
        project: catalogProject({ outputProfiles: ['instagram-reels-video'] }),
        codes: ['OUTPUT_PROFILE_NOT_ALLOWED'],
        schemaAccepts: true,
        reason: 'allowlist e relacao entre dois documentos',
    },
    {
        name: 'payload de video sobre perfil de imagem',
        document: videoPlanWith({ profileId: 'instagram-feed-image-square', profileRevision: catalogProfileRevision('instagram-feed-image-square') }),
        project: catalogProject(),
        codes: [
            'OUTPUT_PLAN_MEDIA_KIND_MISMATCH',
            'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
            'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
        ],
        warnings: ['OUTPUT_PLAN_CONTEXT_NOT_DECLARED', 'OUTPUT_PLAN_CONTEXT_NOT_DECLARED', 'OUTPUT_PLAN_RULE_INFORMATIONAL'],
        schemaAccepts: true,
        reason: 'a forma do payload de video e valida; o que a proibe e o perfil resolvido no catalogo (height e aspectRatio divergem do preset 1080x1080 1:1; fps nao e comparado em perfil de imagem). R-IG-01 e R-IG-06 pedem contexto declarado, e R-IG-10 e de app: informativa antes de qualquer contexto',
    },
    {
        name: 'payload de imagem sobre perfil de video',
        document: imagePlanWith({ profileId: 'youtube-shorts', profileRevision: catalogProfileRevision('youtube-shorts') }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_MEDIA_KIND_MISMATCH'],
        schemaAccepts: true,
        reason: 'os doze presets compartilham geometria vertical; so o catalogo distingue imagem de video',
    },
    {
        name: 'revisao divergente do catalogo',
        document: videoPlanWith({ profileRevision: 2 }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_PROFILE_REVISION_INVALID'],
        schemaAccepts: true,
        reason: 'inteiro positivo valido, mas nao a revisao atual do perfil (Shorts chegou a 3 na R001-05; 2 era a anterior)',
    },
    {
        name: 'projectId divergente do manifesto informado',
        document: videoPlanWith({ projectId: 'outro-projeto' }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_PROJECT_MISMATCH'],
        schemaAccepts: true,
        reason: 'comparacao entre dois documentos',
    },
    {
        name: 'geometria divergente do preset interno',
        document: videoPlanWith({ video: { width: 720, height: 1280, aspectRatio: '9:16', fps: 30 } }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG', 'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG'],
        schemaAccepts: true,
        reason: 'o preset e comparacao com o catalogo, nao forma do documento',
    },
    {
        name: 'fps divergente do preset interno',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '9:16', fps: 25 } }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_FPS_NOT_IN_CATALOG'],
        schemaAccepts: true,
        reason: 'fps 25 e estruturalmente valido; o preset do perfil e 30',
    },
    {
        name: 'proporcao 0:0 rejeitada pela comparacao de preset',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '0:0', fps: 30 } }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG'],
        schemaAccepts: true,
        reason: 'a forma W:H e aceita; a relacao com o preset e semantica',
    },
    {
        name: 'proporcao nao reduzida rejeitada pelo preset',
        document: videoPlanWith({ video: { width: 1080, height: 1920, aspectRatio: '18:32', fps: 30 } }),
        project: catalogProject(),
        codes: ['OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG'],
        schemaAccepts: true,
        reason: 'o preset declara 9:16, nao uma proporcao equivalente',
    },
    {
        name: 'requisito oficial de orientacao violado por plano adulterado',
        document: videoPlanWith({
            ruleContext: 'studio-upload',
            video: { width: 1920, height: 1080, aspectRatio: '16:9', fps: 30 },
        }),
        project: catalogProject(),
        codes: [
            'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
            'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
            'OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG',
            'OUTPUT_PLAN_OFFICIAL_REQUIREMENT_VIOLATED',
        ],
        schemaAccepts: true,
        reason: '16:9 e uma proporcao bem formada; a violacao e da regra R-YT-02 com contexto declarado',
    },
    {
        name: 'contexto nao declarado e aviso, nunca erro',
        document: videoPlanWith(),
        project: catalogProject(),
        codes: [],
        warnings: ['OUTPUT_PLAN_CONTEXT_NOT_DECLARED', 'OUTPUT_PLAN_CONTEXT_NOT_DECLARED'],
        schemaAccepts: true,
        reason: 'sem contexto declarado as regras condicionais oficiais nao sao avaliadas (§2.1.1)',
    },
    {
        name: 'contexto diferente do da fonte nao aplica a regra',
        document: videoPlanWith({ ruleContext: 'api-publishing' }),
        project: catalogProject(),
        codes: [],
        warnings: ['OUTPUT_PLAN_RULE_NOT_APPLIED', 'OUTPUT_PLAN_RULE_NOT_APPLIED'],
        schemaAccepts: true,
        reason: 'R-YT-01 e R-YT-02 sao de in-app e studio-upload; em api-publishing ficam como aviso',
    },
    {
        name: 'regra oficial de formato de arquivo nao e avaliavel por plano',
        document: imagePlanWith({
            profileId: 'instagram-feed-image-square',
            profileRevision: catalogProfileRevision('instagram-feed-image-square'),
            image: { width: 1080, height: 1080, aspectRatio: '1:1' },
            ruleContext: 'api-publishing',
        }),
        project: catalogProject(),
        codes: [],
        warnings: ['OUTPUT_PLAN_RULE_NOT_ASSESSABLE', 'OUTPUT_PLAN_RULE_NOT_ASSESSABLE', 'OUTPUT_PLAN_RULE_INFORMATIONAL'],
        schemaAccepts: true,
        reason: 'JPEG e formato de arquivo, e a faixa 4:5-1.91:1 com largura de 320 a 1440 e de pixels do arquivo: o plano nao carrega nenhum dos dois, entao viram avisos, nunca erro. R-IG-10 e do app e fica informativa',
    },
    {
        name: 'recomendacao nao atendida nunca e erro',
        document: videoPlanWith({
            profileId: 'youtube-video-horizontal',
            profileRevision: catalogProfileRevision('youtube-video-horizontal'),
            video: { width: 1920, height: 1080, aspectRatio: '16:9', fps: 30 },
            ruleContext: 'studio-upload',
        }),
        project: catalogProject(),
        codes: [],
        warnings: [
            'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
            'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
            'OUTPUT_PLAN_RULE_NOT_ASSESSABLE',
            'OUTPUT_PLAN_RULE_NOT_APPLIED',
        ],
        schemaAccepts: true,
        reason: 'R-YT-04 e recomendacao de contener e R-YT-05/R-YT-06 sao de duracao e de peso de arquivo: o plano nao tem nenhum dos tres, entao viram aviso. R-YT-07 e da Data API, ou seja, de outro contexto -- tampouco afunda o plano',
    },
    {
        name: 'manifesto invalido bloqueia a relacao com o catalogo',
        document: videoPlanWith(),
        project: catalogProject({ id: 'id invalido' }),
        codes: ['OUTPUT_PROJECT_INVALID'],
        schemaAccepts: true,
        reason: 'o plano e valido na forma; o projeto dele e que nao e',
    },
    {
        name: 'perfil de rede diferente continua valido para o projeto que o permite',
        document: imagePlanWith({
            profileId: 'facebook-stories-image',
            profileRevision: catalogProfileRevision('facebook-stories-image'),
            image: { width: 1080, height: 1920, aspectRatio: '9:16' },
            ruleContext: 'in-app',
        }),
        project: catalogProject({ outputProfiles: ['facebook-stories-image'] }),
        codes: [],
        warnings: ['OUTPUT_PLAN_RULE_NOT_APPLIED'],
        schemaAccepts: true,
        reason: 'R-FB-02 e certificada para api-publishing; declarado in-app, ela nao se aplica -- aviso, nunca erro. Facebook nao copia regra do Instagram',
    },
]

test('o corpus do OutputPlan tem casos positivos e negativos nos dois grupos', () => {
    const positives = structuralCases.filter((caseItem) => caseItem.valid).length
    assert.ok(positives >= 6, `ao menos 6 casos estruturais validos, obtidos ${positives}`)
    assert.ok(structuralCases.length - positives >= 30, 'o corpus estrutural precisa de casos negativos')
    assert.ok(semanticCases.length >= 12, 'o corpus semantico precisa de ao menos 12 casos')
    assert.equal(new Set(structuralCases.map((caseItem) => caseItem.name)).size, structuralCases.length, 'nome de caso estrutural duplicado')
    assert.equal(new Set(semanticCases.map((caseItem) => caseItem.name)).size, semanticCases.length, 'nome de caso semantico duplicado')
})

for (const caseItem of structuralCases) {
    test(`OutputPlan estrutural: ${caseItem.name}`, () => {
        const report = validateOutputPlanDocument(caseItem.document, catalogProject())
        assert.equal(
            report.valid,
            caseItem.valid,
            `TypeScript esperava valid=${caseItem.valid}, obtido valid=${report.valid} (${report.errors.map((error) => error.code).join(', ')})`,
        )
        if (!caseItem.valid && caseItem.codes) {
            assert.deepEqual(report.errors.map((error) => error.code), [...caseItem.codes])
        }

        const schema = outputPlanSchemaCheck(caseItem.document)
        assert.equal(
            schema.valid,
            caseItem.valid,
            `schema esperava valid=${caseItem.valid}, obtido valid=${schema.valid} (${schema.detail})`,
        )
    })
}

for (const caseItem of semanticCases) {
    test(`OutputPlan semantic: ${caseItem.name}`, () => {
        const report = validateOutputPlanDocument(caseItem.document, caseItem.project)
        assert.equal(report.valid, caseItem.codes.length === 0, `esperava valid=${caseItem.codes.length === 0}`)
        assert.deepEqual(
            report.errors.map((error) => error.code),
            [...caseItem.codes],
            `codigos divergentes para "${caseItem.name}": ${report.errors.map((error) => `${error.code} @${error.path}`).join(', ')}`,
        )
        if (caseItem.warnings) {
            assert.deepEqual(
                report.warnings.map((warning) => warning.code),
                [...caseItem.warnings],
                `avisos divergentes para "${caseItem.name}": ${report.warnings.map((warning) => `${warning.code} @${warning.path}`).join(', ')}`,
            )
        }
        assert.equal(
            outputPlanSchemaCheck(caseItem.document).valid,
            caseItem.schemaAccepts,
            `veredicto do schema mudou para "${caseItem.name}" (${caseItem.reason})`,
        )
    })
}

test('todo perfil do catalogo tem plano aceito pelos dois motores', () => {
    for (const profile of OUTPUT_PROFILES) {
        const payload = profile.mediaKind === 'image'
            ? { width: profile.geometry.width, height: profile.geometry.height, aspectRatio: profile.geometry.aspectRatio }
            : {
                width: profile.geometry.width,
                height: profile.geometry.height,
                aspectRatio: profile.geometry.aspectRatio,
                fps: profile.fps,
            }
        const document: Record<string, unknown> = {
            schemaVersion: 1,
            projectId: 'projeto-teste',
            catalogVersion: CATALOG_VERSION,
            profileId: profile.id,
            profileRevision: profile.revision,
            mediaKind: profile.mediaKind,
            [profile.mediaKind]: payload,
        }

        const report = validateOutputPlanDocument(document, catalogProject())
        assert.equal(
            report.valid,
            true,
            `${profile.id} rejeitado pelo TypeScript: ${report.errors.map((error) => `${error.code} @${error.path}`).join(', ')}`,
        )
        assert.equal(outputPlanSchemaCheck(document).valid, true, `${profile.id} rejeitado pelo schema`)
        assert.deepEqual(
            report.requiresInspection,
            profile.mediaKind === 'image'
                ? ['media-file', 'image-format', 'bytes', 'publication']
                : ['media-file', 'codec', 'bytes', 'audio-streams', 'publication'],
            `${profile.id} com lista de inspecao errada`,
        )
        assert.deepEqual(report.pendingRuleIds, [...profile.pendingIds], `${profile.id} com pendencias erradas`)
    }
})

/**
 * Superficie do espelho normative conferida contra os tipos do contrato: se um
 * campo entrar no TypeScript e nao no schema (ou o contrario) o gate para.
 */
test('o schema de plano declara a mesma superficie do contrato', () => {
    const schema = JSON.parse(
        readFileSync(path.join(moduleRoot, 'schemas', 'output-plan.schema.json'), 'utf8'),
    ) as {
        additionalProperties?: boolean
        required?: string[]
        properties?: Record<string, { enum?: string[]; const?: unknown; pattern?: string }>
        definitions?: Record<string, {
            additionalProperties?: boolean
            required?: string[]
            properties?: Record<string, unknown>
        }>
    }

    assert.equal(schema.additionalProperties, false, 'o topo do plano deve fechar propriedades extras')
    assert.deepEqual(Object.keys(schema.properties ?? {}).sort(), [...OUTPUT_PLAN_TOP_LEVEL_FIELDS].sort(), 'superficie do topo divergiu do contrato')
    assert.deepEqual(schema.required, [
        'schemaVersion',
        'projectId',
        'catalogVersion',
        'profileId',
        'profileRevision',
        'mediaKind',
    ], 'campos obrigatorios do topo divergiram do contrato')

    assert.deepEqual(schema.properties?.mediaKind?.enum, [...OUTPUT_MEDIA_KINDS], 'enum de mediaKind divergiu de types.ts')
    assert.deepEqual(schema.properties?.ruleContext?.enum, [...RULE_CONTEXTS], 'enum de ruleContext divergiu de types.ts')
    assert.equal(schema.properties?.catalogVersion?.const, CATALOG_VERSION, 'catalogVersion fixa no schema deve ser a do codigo')

    const imagePayload = schema.definitions?.imagePayload
    const videoPayload = schema.definitions?.videoPayload
    assert.equal(imagePayload?.additionalProperties, false, 'payload de imagem aberto a campos extras')
    assert.equal(videoPayload?.additionalProperties, false, 'payload de video aberto a campos extras')
    assert.deepEqual(Object.keys(imagePayload?.properties ?? {}).sort(), [...OUTPUT_PLAN_IMAGE_FIELDS].sort(), 'superficie de imagem divergiu do contrato')
    assert.deepEqual(Object.keys(videoPayload?.properties ?? {}).sort(), [...OUTPUT_PLAN_VIDEO_FIELDS].sort(), 'superficie de video divergiu do contrato')
    assert.deepEqual(imagePayload?.required, [...OUTPUT_PLAN_IMAGE_FIELDS], 'campos obrigatorios de imagem divergiram')
    assert.deepEqual(videoPayload?.required, [...OUTPUT_PLAN_VIDEO_FIELDS], 'campos obrigatorios de video divergiram')

    // Duracao e formato de arquivo nao existem no contrato, entao nao podem existir no espelho.
    for (const forbidden of ['durationMs', 'duration', 'container', 'format', 'bytes']) {
        assert.ok(
            !JSON.stringify(schema.definitions).includes(`"${forbidden}"`),
            `o schema declara ${forbidden}, que nao pertence ao plano`,
        )
    }
})
