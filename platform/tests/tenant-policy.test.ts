/**
 * Testes unitarios da camada multi-tenant tipada da platform (Etapa 6).
 *
 * Cobre: validacao do TenantPolicyContract v1 nos 5 tenants, violacoes de
 * contrato (uiLabel ausente, chave desconhecida, AAC restrito, rotas iguais,
 * paleta invalida) e a compatibilidade aditiva CreativeExecutionPackage v1 x
 * TenantPolicyContract v1 no `validateContentPipeline` (incluindo bloqueio de
 * faixa de audio em tenants de servico e AAC apenas em multitrack-hub).
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import {
    PIPELINE_VALID_SUMMARY,
    type ContentPipelineValidationInput,
} from '../src/content-pipeline-validation-contract.js'
import type {
    TenantAudioCodecProfile,
    TenantPolicyContract,
    TenantUiLabels,
} from '../src/tenant-policy-contract.js'
import { validateContentPipeline } from '../src/validate-content-pipeline.js'
import { validateExecutionPackageTenantCompatibility } from '../src/validate-execution-tenant-compatibility.js'
import { validateTenantPolicy } from '../src/validate-tenant-policy.js'
import * as platformIndex from '../src/index.js'
import { moduleRoot } from './contract-harness.js'

const PALETTE = {
    primary: '#F5C107',
    secondary: '#4F8CFF',
    accent: '#28B463',
    background: '#121620',
    surface: '#222C40',
    textPrimary: '#F5F7FA',
    textMuted: '#B4C0D2',
} as const

const SERVICE_AUDIO: TenantAudioCodecProfile = {
    allowAudioTrack: false,
    allowedCodecs: [],
    requireSrt: true,
    requireExternalNarration: true,
}

const AUDIO_TENANT_PROFILE: TenantAudioCodecProfile = {
    allowAudioTrack: true,
    allowedCodecs: ['aac'],
    requireSrt: true,
    requireExternalNarration: false,
}

const BASE_LABELS: TenantUiLabels = {
    teamSectionTitle: 'PROFISSIONAIS DO SALAO',
    catalogSectionTitle: 'SERVICOS DISPONIVEIS',
    publicRouteFallback: '/booking/[salonId]',
    managerRouteFallback: '/gestor/agenda',
    journeyBridgeCaption: 'DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO',
    itemUnitLabel: 'atendimento',
    customerLabel: 'Cliente',
}

function uiLabels(over: Partial<TenantUiLabels>): TenantUiLabels {
    return {
        teamSectionTitle: over.teamSectionTitle ?? BASE_LABELS.teamSectionTitle,
        catalogSectionTitle: over.catalogSectionTitle ?? BASE_LABELS.catalogSectionTitle,
        publicRouteFallback: over.publicRouteFallback ?? BASE_LABELS.publicRouteFallback,
        managerRouteFallback: over.managerRouteFallback ?? BASE_LABELS.managerRouteFallback,
        journeyBridgeCaption: over.journeyBridgeCaption ?? BASE_LABELS.journeyBridgeCaption,
        itemUnitLabel: over.itemUnitLabel ?? BASE_LABELS.itemUnitLabel,
        customerLabel: over.customerLabel ?? BASE_LABELS.customerLabel,
    }
}

function policy(over: Partial<TenantPolicyContract> & Pick<TenantPolicyContract, 'tenantId'>): TenantPolicyContract {
    return {
        schemaVersion: 1,
        tenantId: over.tenantId,
        brandName: over.brandName ?? over.tenantId,
        defaultPreset: over.defaultPreset ?? 'saas-demo',
        palette: over.palette ?? PALETTE,
        uiLabels: over.uiLabels ?? BASE_LABELS,
        routes: over.routes ?? { public: '/booking/[salonId]', management: '/gestor/agenda' },
        audioProfile: over.audioProfile ?? SERVICE_AUDIO,
        guardrails: over.guardrails ?? { forbiddenClaims: ['termo-vetado'], forbiddenUiElements: ['pagamento'] },
    }
}

const POLICIES: Record<string, TenantPolicyContract> = {
    'marca-salao': policy({ tenantId: 'marca-salao' }),
    'meu-salao': policy({
        tenantId: 'meu-salao',
        uiLabels: uiLabels({ journeyBridgeCaption: 'DO AGENDAMENTO DA CLIENTE A AGENDA DO MEU SALAO' }),
    }),
    'estudio-flow': policy({
        tenantId: 'estudio-flow',
        uiLabels: uiLabels({
            teamSectionTitle: 'INSTRUTORES DO ESTUDIO',
            catalogSectionTitle: 'MODALIDADES DISPONIVEIS',
            publicRouteFallback: '/aulas/[studioId]',
            managerRouteFallback: '/gestor/turmas',
            journeyBridgeCaption: 'DA RESERVA DA ALUNA A GRADE DO ESTUDIO',
            itemUnitLabel: 'aula',
            customerLabel: 'Aluna',
        }),
        routes: { public: '/aulas/[studioId]', management: '/gestor/turmas' },
    }),
    'clinica-vital': policy({
        tenantId: 'clinica-vital',
        uiLabels: uiLabels({
            teamSectionTitle: 'ESPECIALISTAS DA CLINICA',
            catalogSectionTitle: 'PROCEDIMENTOS DISPONIVEIS',
            publicRouteFallback: '/avaliacao/[clinicId]',
            managerRouteFallback: '/gestor/consultas',
            journeyBridgeCaption: 'DA MARCACAO DO PACIENTE A AGENDA DA CLINICA',
            itemUnitLabel: 'consulta',
            customerLabel: 'Paciente',
        }),
        routes: { public: '/avaliacao/[clinicId]', management: '/gestor/consultas' },
    }),
    'multitrack-hub': policy({
        tenantId: 'multitrack-hub',
        defaultPreset: 'shorts-completo',
        uiLabels: uiLabels({
            teamSectionTitle: 'CATALOGO DE PROJETOS',
            catalogSectionTitle: 'FAIXAS E RATEIOS',
            publicRouteFallback: '/',
            managerRouteFallback: '/rateios',
            journeyBridgeCaption: 'DA ORGANIZACAO DOS STEMS AOS RATEIOS',
            itemUnitLabel: 'projeto',
            customerLabel: 'Musico',
        }),
        routes: { public: '/', management: '/rateios' },
        audioProfile: AUDIO_TENANT_PROFILE,
    }),
}

const TENANT_IDS = ['marca-salao', 'meu-salao', 'estudio-flow', 'clinica-vital', 'multitrack-hub'] as const

function marcPolicy(): TenantPolicyContract {
    return POLICIES['marca-salao'] as TenantPolicyContract
}
function multitrackPolicy(): TenantPolicyContract {
    return POLICIES['multitrack-hub'] as TenantPolicyContract
}

const CLEAN_ARTIFACTS = [
    { id: 'primary-output', kind: 'primary-output', required: true, logicalName: 'video.mp4', contentType: 'video/mp4' },
    { id: 'captions', kind: 'captions', required: true, logicalName: 'captions.srt', contentType: 'text/srt' },
    { id: 'narration-script', kind: 'narration-script', required: true, logicalName: 'narration.txt', contentType: 'text/plain' },
    { id: 'execution-report', kind: 'execution-report', required: false, logicalName: 'report.json', contentType: 'application/json' },
] as const

function packageWith(contentType: string | null): unknown {
    const artifacts = [...CLEAN_ARTIFACTS]
    if (contentType !== null) {
        artifacts.push({ id: 'audio-track', kind: 'audio', required: true, logicalName: 'track.bin', contentType } as never)
    }
    return { schemaVersion: 1, expectedArtifacts: artifacts }
}

function readJson(relativePath: string): unknown {
    return JSON.parse(readFileSync(path.join(moduleRoot, relativePath), 'utf8')) as unknown
}

function validPipelineInput(): ContentPipelineValidationInput {
    return {
        project: readJson('examples/projects/marca-salao-social.project.json'),
        composition: readJson('examples/compositions/marca-salao-social-reel.composition.json'),
        outputPlan: readJson('examples/output-plans/instagram-reels-video.output-plan.json'),
        beatPlan: readJson('examples/pipelines/marca-salao-social-reel.beat-plan.json'),
    }
}

// ---------------------------------------------------------------------------
// TenantPolicyContract v1: os 5 tenants e violacoes de contrato
// ---------------------------------------------------------------------------
test('os 5 tenants produzem TenantPolicyContract valido', () => {
    for (const tenantId of TENANT_IDS) {
        const report = validateTenantPolicy(POLICIES[tenantId])
        assert.equal(report.valid, true, `${tenantId}: ${JSON.stringify(report.errors)}`)
        assert.equal(report.tenantId, tenantId)
        assert.equal(report.errors.length, 0)
    }
})

test('uiLabel obrigatorio ausente e rejeitado', () => {
    const invalid = policy({ tenantId: 'marca-salao', uiLabels: uiLabels({ customerLabel: '' }) })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_UI_LABEL_MISSING' && e.path === 'uiLabels.customerLabel'))
})

test('chave desconhecida dentro de uiLabels e rejeitada', () => {
    const invalid = { ...marcPolicy(), uiLabels: { ...BASE_LABELS, chaveInventada: 'X' } }
    const report = validateTenantPolicy(invalid as unknown)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_UNKNOWN_FIELD' && e.path === 'uiLabels.chaveInventada'))
})

test('tenant de servico nao pode declarar codec de audio', () => {
    const invalid = policy({
        tenantId: 'marca-salao',
        audioProfile: { allowAudioTrack: false, allowedCodecs: ['aac'], requireSrt: true, requireExternalNarration: true },
    })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_AUDIO_CODEC_WITH_AUDIO_DISABLED'))
})

test('politica com audio habilitado exige codec declarado', () => {
    const invalid = policy({
        tenantId: 'multitrack-hub',
        audioProfile: { allowAudioTrack: true, allowedCodecs: [], requireSrt: true, requireExternalNarration: false },
    })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_AUDIO_ENABLED_WITHOUT_CODEC'))
})

test('rotas publicas e de gestao devem diferir', () => {
    const invalid = policy({ tenantId: 'marca-salao', routes: { public: '/mesma', management: '/mesma' } })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_ROUTE_NOT_DISTINCT'))
})

test('paleta com cor hex invalida e rejeitada', () => {
    const invalid = { ...marcPolicy(), palette: { ...PALETTE, primary: 'red' } }
    const report = validateTenantPolicy(invalid as unknown)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_PALETTE_INVALID' && e.path === 'palette.primary'))
})

// ---------------------------------------------------------------------------
// Compatibilidade ExecutionPackage v1 x TenantPolicyContract v1
// ---------------------------------------------------------------------------
test('tenant de servico bloqueia faixa de audio', () => {
    const report = validateExecutionPackageTenantCompatibility(packageWith('audio/aac'), marcPolicy())
    assert.equal(report.valid, false)
    assert.equal(report.audioArtifactCount, 1)
    assert.ok(report.errors.some((e) => e.code === 'EXEC_AUDIO_TRACK_NOT_ALLOWED'))
})

test('multitrack-hub permite AAC', () => {
    const report = validateExecutionPackageTenantCompatibility(packageWith('audio/aac'), multitrackPolicy())
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.audioArtifactCount, 1)
})

test('multitrack-hub bloqueia codec de audio nao permitido', () => {
    const report = validateExecutionPackageTenantCompatibility(packageWith('audio/opus'), multitrackPolicy())
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'EXEC_AUDIO_CODEC_NOT_ALLOWED'))
})

test('pacote sem faixa de audio e compativel em tenant de servico', () => {
    const report = validateExecutionPackageTenantCompatibility(packageWith(null), marcPolicy())
    assert.equal(report.valid, true)
    assert.equal(report.audioArtifactCount, 0)
})

test('politica invalida bloqueia compatibilidade com erros prefixados', () => {
    const badPolicy = policy({ tenantId: 'marca-salao', uiLabels: uiLabels({ teamSectionTitle: '' }) })
    const report = validateExecutionPackageTenantCompatibility(packageWith(null), badPolicy)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_UI_LABEL_MISSING' && e.path.startsWith('tenantPolicy.')))
})

// ---------------------------------------------------------------------------
// Integracao aditiva no validateContentPipeline
// ---------------------------------------------------------------------------
test('pipeline classico permanece de 5 estagios e sem tenantCompatibility', () => {
    const report = validateContentPipeline(validPipelineInput())
    assert.equal(report.valid, true)
    assert.equal(report.summary, PIPELINE_VALID_SUMMARY)
    assert.equal(report.stages.length, 5)
    assert.equal('tenantCompatibility' in report, false)
})

test('pipeline com politica marca + pacote limpo permanece valido', () => {
    const report = validateContentPipeline({
        ...validPipelineInput(),
        tenantPolicy: marcPolicy(),
        executionPackage: packageWith(null),
    })
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.stages.length, 5)
    assert.ok(report.tenantCompatibility)
    assert.equal(report.tenantCompatibility?.valid, true)
    assert.equal(report.errors.filter((e) => e.stage === 'tenant-policy').length, 0)
})

test('pipeline com pacote de audio em tenant de servico fica invalido', () => {
    const report = validateContentPipeline({
        ...validPipelineInput(),
        tenantPolicy: marcPolicy(),
        executionPackage: packageWith('audio/aac'),
    })
    assert.equal(report.valid, false)
    assert.equal(report.stages.length, 5)
    assert.ok(report.tenantCompatibility)
    assert.equal(report.tenantCompatibility?.valid, false)
    const tenantIssues = report.errors.filter((e) => e.stage === 'tenant-policy')
    assert.ok(tenantIssues.some((e) => e.code === 'EXEC_AUDIO_TRACK_NOT_ALLOWED'))
})

test('pipeline com entrada de compatibilidade incompleta reporta erro dedicado', () => {
    const report = validateContentPipeline({
        ...validPipelineInput(),
        tenantPolicy: marcPolicy(),
    })
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_COMPATIBILITY_INPUT_INCOMPLETE'))
})

// ---------------------------------------------------------------------------
// Etapa 8: rotas estritas, audio por tenant, invariante autoPublish e index
// ---------------------------------------------------------------------------
test('rota de gestao deve pertencer a superficie de gestao', () => {
    const invalid = policy({ tenantId: 'marca-salao', routes: { public: '/booking/[salonId]', management: '/dashboard' } })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_ROUTE_MANAGEMENT_INVALID'))
})

test('rota publica nao pode apontar para superficie de gestao', () => {
    const invalid = policy({ tenantId: 'marca-salao', routes: { public: '/gestor/agenda', management: '/gestor/turmas' } })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_ROUTE_PUBLIC_INVALID'))
})

test('tenant de servico nao pode habilitar faixa de audio', () => {
    const invalid = policy({
        tenantId: 'marca-salao',
        audioProfile: { allowAudioTrack: true, allowedCodecs: ['aac'], requireSrt: true, requireExternalNarration: true },
    })
    const report = validateTenantPolicy(invalid)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_AUDIO_TRACK_RESTRICTED'))
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_AAC_RESTRICTED'))
})

test('aac em tenant nao permitido e bloqueado na compatibilidade', () => {
    const policyPermittingAac = policy({
        tenantId: 'marca-salao',
        audioProfile: { allowAudioTrack: true, allowedCodecs: ['aac'], requireSrt: true, requireExternalNarration: true },
    })
    const report = validateExecutionPackageTenantCompatibility(packageWith('audio/aac'), policyPermittingAac)
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'TENANT_POLICY_AAC_RESTRICTED'))
})

test('invariante autoPublish: true e bloqueado no pipeline', () => {
    const report = validateContentPipeline({
        ...validPipelineInput(),
        tenantPolicy: marcPolicy(),
        executionPackage: { schemaVersion: 1, expectedArtifacts: CLEAN_ARTIFACTS, autoPublish: true },
    })
    assert.equal(report.valid, false)
    assert.ok(report.errors.some((e) => e.code === 'AUTO_PUBLISH_FORBIDDEN'))
})

test('invariante autoPublish: false e aceito', () => {
    const report = validateContentPipeline({
        ...validPipelineInput(),
        tenantPolicy: marcPolicy(),
        executionPackage: { schemaVersion: 1, expectedArtifacts: CLEAN_ARTIFACTS, autoPublish: false },
    })
    assert.equal(report.valid, true, JSON.stringify(report.errors))
})

test('index expoe a superficie publica tipada', () => {
    assert.equal(typeof platformIndex.validateComposition, 'function')
    assert.equal(typeof platformIndex.validateContentPipeline, 'function')
    assert.equal(typeof platformIndex.validateTenantPolicy, 'function')
    assert.equal(typeof platformIndex.validateExecutionPackageTenantCompatibility, 'function')
    assert.equal(typeof platformIndex.isManagementRoute, 'function')
    assert.ok(Array.isArray(platformIndex.AUDIO_PERMITTED_TENANTS))
})