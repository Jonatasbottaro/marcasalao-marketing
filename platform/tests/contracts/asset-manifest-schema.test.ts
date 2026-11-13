/**
 * Paridade estrutural do AssetManifest v1:
 * O espelho draft-07 executado via Ajv e o validador puro em TypeScript
 * avaliam os mesmos documentos estruturais e seus vereditos coincidem.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { createCreativeExecutionPackageFromCase } from '../../src/creative-execution-packages.js'
import { validateAssetManifest } from '../../src/validate-asset-manifest.js'
import { moduleRoot } from '../contract-harness.js'

const schemaPath = path.join(moduleRoot, 'schemas', 'asset-manifest.schema.json')
const schemaText = readFileSync(schemaPath, 'utf8')
const schema = JSON.parse(schemaText) as AnySchemaObject

const ajv = new AjvModule.default({ allErrors: true, strict: false })

function checkSchema(document: unknown): { valid: boolean; detail: string } {
    const fresh = ajv.compile(schema)
    const valid = fresh(document) === true
    const failures = (fresh.errors ?? []).map(
        (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
    )
    return { valid, detail: failures.join(' | ') }
}

const examplesRoot = path.join(moduleRoot, 'examples')
const marcaManifest = path.join(examplesRoot, 'pipelines', 'marca-salao-pipeline-pilot.pipeline.json')
const creation = createCreativeExecutionPackageFromCase(marcaManifest, examplesRoot)
if (creation.status !== 'generated' || creation.package === null) {
    throw new Error(`Falha ao preparar pacote para teste de schema: ${creation.summary}`)
}
const validPackage = creation.package
const validCaseId = creation.caseId as string
const validPackageId = validPackage.packageId

const SHA_A = 'a'.repeat(64)
const SHA_B = 'b'.repeat(64)
const SHA_C = '0123456789abcdef'.repeat(4)

test('paridade estrutural: inventarios validos sao aceitos pelo schema e pelo validador', () => {
    const validCases = [
        {
            schemaVersion: 1,
            caseId: validCaseId,
            packageId: validPackageId,
            assets: [
                {
                    id: 'hook-image',
                    type: 'image',
                    path: '.workspace/tmp/assets/opening-hook.png',
                    bytes: 1024,
                    sha256: SHA_A,
                    origin: 'synthetic-proof-generator',
                    license: 'pending',
                },
                {
                    id: 'demo-clip',
                    type: 'video',
                    path: '.workspace/tmp/assets/demonstration.mp4',
                    bytes: 204800,
                    sha256: SHA_B,
                    origin: 'screen-capture-local',
                    license: 'internal-proprietary',
                },
                {
                    id: 'cta-image',
                    type: 'image',
                    path: '.workspace/tmp/assets/closing-cta.jpg',
                    bytes: 4096,
                    sha256: SHA_C,
                    origin: 'synthetic-proof-generator',
                    license: 'pending',
                },
            ],
            bindings: [
                { beatId: 'opening-hook', assetId: 'hook-image' },
                { beatId: 'demonstration-body', assetId: 'demo-clip' },
                { beatId: 'closing-cta', assetId: 'cta-image' },
            ],
        },
        {
            schemaVersion: 1,
            caseId: validCaseId,
            packageId: validPackageId,
            assets: [
                {
                    id: 'shared-hero',
                    type: 'image',
                    path: '.workspace/tmp/assets/shared.webp',
                    bytes: 1,
                    sha256: SHA_A,
                    origin: 'brand-library',
                    license: 'CC-BY-4.0',
                },
                {
                    id: 'demo-mov',
                    type: 'video',
                    path: '.workspace/tmp/assets/demo.mov',
                    bytes: 999999,
                    sha256: SHA_B,
                    origin: 'local-capture',
                    license: 'internal-only',
                },
            ],
            bindings: [
                { beatId: 'opening-hook', assetId: 'shared-hero' },
                { beatId: 'demonstration-body', assetId: 'demo-mov' },
                { beatId: 'closing-cta', assetId: 'shared-hero' },
            ],
        },
    ]

    for (const doc of validCases) {
        const schemaRes = checkSchema(doc)
        assert.equal(schemaRes.valid, true, `Schema rejeitou caso valido: ${schemaRes.detail}`)

        const validatorRes = validateAssetManifest(validPackage, validCaseId, doc)
        assert.equal(
            validatorRes.ok,
            true,
            `Validador rejeitou caso valido: ${!validatorRes.ok ? validatorRes.failureCode : ''}`,
        )
    }
})

test('paridade estrutural: defeitos de formato sao rejeitados pelo schema e pelo validador', () => {
    const baseAsset = {
        id: 'asset-um',
        type: 'image',
        path: '.workspace/tmp/a.png',
        bytes: 100,
        sha256: SHA_A,
        origin: 'local-proof',
        license: 'pending',
    }
    const baseDoc = {
        schemaVersion: 1,
        caseId: validCaseId,
        packageId: validPackageId,
        assets: [baseAsset],
        bindings: [{ beatId: 'opening-hook', assetId: 'asset-um' }],
    }

    const invalidCases: Array<{ name: string; doc: unknown }> = [
        { name: 'nulo', doc: null },
        { name: 'array na raiz', doc: [] },
        { name: 'schemaVersion ausente', doc: { ...baseDoc, schemaVersion: undefined } },
        { name: 'schemaVersion diferente de 1', doc: { ...baseDoc, schemaVersion: 2 } },
        { name: 'caseId invalido', doc: { ...baseDoc, caseId: 'Invalid_Case' } },
        { name: 'packageId invalido', doc: { ...baseDoc, packageId: 'Invalid_Pkg' } },
        { name: 'campo extra de topo', doc: { ...baseDoc, extra: true } },
        { name: 'assets vazio', doc: { ...baseDoc, assets: [] } },
        { name: 'bindings vazio', doc: { ...baseDoc, bindings: [] } },
        { name: 'asset id nao kebab-case', doc: { ...baseDoc, assets: [{ ...baseAsset, id: 'Asset_1' }] } },
        { name: 'asset type invalido', doc: { ...baseDoc, assets: [{ ...baseAsset, type: 'audio' }] } },
        { name: 'asset path vazio', doc: { ...baseDoc, assets: [{ ...baseAsset, path: '   ' }] } },
        { name: 'asset path com controle', doc: { ...baseDoc, assets: [{ ...baseAsset, path: '.workspace/a\nb.png' }] } },
        { name: 'asset bytes zero', doc: { ...baseDoc, assets: [{ ...baseAsset, bytes: 0 }] } },
        { name: 'asset bytes decimal', doc: { ...baseDoc, assets: [{ ...baseAsset, bytes: 10.5 }] } },
        { name: 'asset sha256 curto', doc: { ...baseDoc, assets: [{ ...baseAsset, sha256: 'abc' }] } },
        { name: 'asset sha256 maiusculo', doc: { ...baseDoc, assets: [{ ...baseAsset, sha256: 'A'.repeat(64) }] } },
        { name: 'asset origin vazio', doc: { ...baseDoc, assets: [{ ...baseAsset, origin: '' }] } },
        { name: 'asset license apenas espacos', doc: { ...baseDoc, assets: [{ ...baseAsset, license: '  ' }] } },
        { name: 'asset com campo extra', doc: { ...baseDoc, assets: [{ ...baseAsset, extra: 1 }] } },
        {
            name: 'binding com campo extra',
            doc: { ...baseDoc, bindings: [{ beatId: 'opening-hook', assetId: 'asset-um', extra: 1 }] },
        },
        {
            name: 'binding com assetId invalido',
            doc: { ...baseDoc, bindings: [{ beatId: 'opening-hook', assetId: 'Asset_Um' }] },
        },
    ]

    for (const { name, doc } of invalidCases) {
        const cleanDoc =
            typeof doc === 'object' && doc !== null && !Array.isArray(doc) && 'schemaVersion' in doc && (doc as { schemaVersion?: unknown }).schemaVersion === undefined
                ? (() => {
                      const clone = { ...(doc as Record<string, unknown>) }
                      delete clone.schemaVersion
                      return clone
                  })()
                : doc

        const schemaRes = checkSchema(cleanDoc)
        assert.equal(schemaRes.valid, false, `Schema deveria rejeitar: ${name}`)

        const validatorRes = validateAssetManifest(validPackage, validCaseId, cleanDoc)
        assert.equal(validatorRes.ok, false, `Validador deveria rejeitar: ${name}`)
    }
})
