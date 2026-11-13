#!/usr/bin/env node
/**
 * Ponte interna entre a camada de ferramentas (Python) e o nucleo puro da
 * platform. Suporta dois modos:
 *
 * 1. Legado (render_local.py):
 *    node tools/render_bridge.mjs <package.json> <assets.json>
 *    Valida o pacote e a associacao via validateLocalRenderInput.
 *
 * 2. Pipeline (render_pipeline.py):
 *    node tools/render_bridge.mjs --case <case.pipeline.json> [--root <rootDir>] [--assets <assets.json> | --asset-manifest <manifest.json>] [--plan-only]
 *    Carrega o caso, gera o CreativeExecutionPackage canonico a partir do caso
 *    valido e opcionalmente valida a associacao de assets ou o inventario de midia.
 *
 * Exit codes: 0 sucesso/valido; 2 uso ou JSON ilegivel; 3 entrada invalida.
 */

import { readFileSync } from 'node:fs'
import path from 'node:path'

import { createCreativeExecutionPackageFromCase } from '../platform/dist/src/creative-execution-packages.js'
import { compileVideoRequest } from '../platform/dist/src/compile-video-request.js'
import { validateCarouselRequest } from '../platform/dist/src/validate-carousel-request.js'
import { resolveOutputPlan } from '../platform/dist/src/resolve-output-profile.js'
import { serializeAssetManifest } from '../platform/dist/src/serialize-asset-manifest.js'
import { serializeCreativeExecutionPackage } from '../platform/dist/src/serialize-creative-execution-package.js'
import { serializeTextOverlayPlan } from '../platform/dist/src/serialize-text-overlay-plan.js'
import { serializeVisualStyle } from '../platform/dist/src/serialize-visual-style.js'
import { validateAssetManifest } from '../platform/dist/src/validate-asset-manifest.js'
import {
    checkLocalRenderConfiguration,
    validateLocalRenderInput,
} from '../platform/dist/src/validate-local-render-input.js'
import { validateTextOverlayPlan } from '../platform/dist/src/validate-text-overlay-plan.js'
import { validateVisualStyle } from '../platform/dist/src/validate-visual-style.js'

function buildPlan(caseId, pkg, configCheck) {
    const output = pkg.output
    const beats = pkg.timeline.map((step) => step.beatId)
    return {
        caseId,
        packageId: pkg.packageId,
        perfil: output.profileId,
        profileId: output.profileId,
        geometria: `${output.width}x${output.height} (${output.aspectRatio})`,
        geometry: {
            width: output.width,
            height: output.height,
            aspectRatio: output.aspectRatio,
        },
        fps: output.fps,
        FPS: output.fps,
        duracao: `${(output.durationMs / 1000.0).toFixed(1)}s`,
        durationMs: output.durationMs,
        durationSeconds: output.durationMs / 1000.0,
        beats,
        requiredBeats: beats,
        supported: configCheck.supported,
        cabeNoRecorte: configCheck.supported,
        unsupportedReason: configCheck.unsupportedReason,
    }
}

function handleCasePipeline(args) {
    let casePath = null
    let assetsPath = null
    let assetManifestPath = null
    let textOverlaysPath = null
    let visualStylePath = null
    let rootDir = process.cwd()
    let planOnly = false

    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === '--case' && i + 1 < args.length) {
            casePath = args[++i]
        } else if (arg === '--assets' && i + 1 < args.length) {
            assetsPath = args[++i]
        } else if (arg === '--asset-manifest' && i + 1 < args.length) {
            assetManifestPath = args[++i]
        } else if (arg === '--text-overlays' && i + 1 < args.length) {
            textOverlaysPath = args[++i]
        } else if (arg === '--visual-style' && i + 1 < args.length) {
            visualStylePath = args[++i]
        } else if (arg === '--root' && i + 1 < args.length) {
            rootDir = args[++i]
        } else if (arg === '--plan-only') {
            planOnly = true
        } else {
            console.error(`erro: flag desconhecida na ponte: ${arg}`)
            process.exit(2)
        }
    }

    if (!casePath) {
        console.error('uso: node tools/render_bridge.mjs --case <caso.pipeline.json> [--root <raiz>] [--assets <assets.json> | --asset-manifest <manifest.json>] [--text-overlays <overlays.json>] [--visual-style <style.json>] [--plan-only]')
        process.exit(2)
    }

    if (assetsPath && assetManifestPath) {
        console.error('erro: informe apenas um entre --assets e --asset-manifest')
        process.exit(2)
    }

    const creation = createCreativeExecutionPackageFromCase(casePath, path.resolve(rootDir))
    if (creation.status !== 'generated' || !creation.package) {
        const failureCode = creation.failureCode || (creation.status === 'case-invalid' ? 'CASE_INVALID' : 'GENERATION_FAILED')
        console.log(JSON.stringify({
            ok: false,
            status: creation.status,
            caseId: creation.caseId,
            failureCode,
            packageErrors: creation.packageErrors,
            summary: creation.summary,
        }))
        process.exit(3)
    }

    const pkg = creation.package
    const canonicalJson = serializeCreativeExecutionPackage(pkg)
    const configCheck = checkLocalRenderConfiguration(pkg)
    const plan = buildPlan(creation.caseId, pkg, configCheck)

    let canonicalTextOverlayJson = null
    let resolvedTextOverlays = []
    let textOverlayPlan = null

    if (textOverlaysPath) {
        let textOverlaysInput
        try {
            textOverlaysInput = JSON.parse(readFileSync(textOverlaysPath, 'utf8'))
        } catch {
            console.error('erro: arquivo de sobreposicao de texto ilegivel ou JSON invalido')
            process.exit(2)
        }

        const overlayValidation = validateTextOverlayPlan(pkg, creation.caseId, textOverlaysInput)
        if (!overlayValidation.ok) {
            console.log(JSON.stringify({
                ok: false,
                caseId: creation.caseId,
                packageId: pkg.packageId,
                failureCode: overlayValidation.failureCode,
                subject: overlayValidation.subject,
                plan,
            }))
            process.exit(3)
        }

        textOverlayPlan = overlayValidation.plan
        canonicalTextOverlayJson = serializeTextOverlayPlan(overlayValidation.plan)
        resolvedTextOverlays = overlayValidation.resolvedOverlays
        plan.textOverlays = resolvedTextOverlays
    }

    let canonicalVisualStyleJson = null
    let visualStyle = null

    if (visualStylePath) {
        let visualStyleInput
        try {
            visualStyleInput = JSON.parse(readFileSync(visualStylePath, 'utf8'))
        } catch {
            console.error('erro: arquivo de estilo visual ilegivel ou JSON invalido')
            process.exit(2)
        }

        const styleValidation = validateVisualStyle(visualStyleInput)
        if (!styleValidation.ok) {
            console.log(JSON.stringify({
                ok: false,
                caseId: creation.caseId,
                packageId: pkg.packageId,
                failureCode: styleValidation.failureCode,
                subject: styleValidation.subject,
                plan,
            }))
            process.exit(3)
        }

        visualStyle = styleValidation.style
        canonicalVisualStyleJson = serializeVisualStyle(styleValidation.style)
        plan.visualStyle = visualStyle
        plan.hasTitles = resolvedTextOverlays.length > 0
        plan.hasTitlesToApply = resolvedTextOverlays.length > 0
    }

    let canonicalAssetManifestJson = null
    let assetManifest = null
    let resolvedAssetBindings = []
    let manifestAssociation = null

    if (assetManifestPath) {
        let assetManifestInput
        try {
            assetManifestInput = JSON.parse(readFileSync(assetManifestPath, 'utf8'))
        } catch {
            console.error('erro: arquivo de inventario de midia ilegivel ou JSON invalido')
            process.exit(2)
        }

        const manifestValidation = validateAssetManifest(pkg, creation.caseId, assetManifestInput)
        if (!manifestValidation.ok) {
            console.log(JSON.stringify({
                ok: false,
                caseId: creation.caseId,
                packageId: pkg.packageId,
                failureCode: manifestValidation.failureCode,
                subject: manifestValidation.subject,
                plan,
            }))
            process.exit(3)
        }

        assetManifest = manifestValidation.manifest
        canonicalAssetManifestJson = serializeAssetManifest(manifestValidation.manifest)
        resolvedAssetBindings = manifestValidation.resolvedBindings
        manifestAssociation = manifestValidation.association
        plan.assetManifest = {
            caseId: assetManifest.caseId,
            packageId: assetManifest.packageId,
            assetCount: assetManifest.assets.length,
            assets: assetManifest.assets,
            bindings: assetManifest.bindings,
            resolvedBindings: resolvedAssetBindings,
        }
    }

    if (planOnly || !assetsPath) {
        console.log(JSON.stringify({
            ok: true,
            status: 'generated',
            caseId: creation.caseId,
            packageId: pkg.packageId,
            package: pkg,
            canonicalJson,
            canonicalTextOverlayJson,
            canonicalVisualStyleJson,
            canonicalAssetManifestJson,
            textOverlays: textOverlayPlan,
            resolvedTextOverlays,
            visualStyle,
            assetManifest,
            resolvedAssetBindings,
            association: manifestAssociation,
            plan,
        }))
        process.exit(0)
    }

    let associationInput
    try {
        associationInput = JSON.parse(readFileSync(assetsPath, 'utf8'))
    } catch {
        console.error('erro: arquivo de associacao ilegivel ou JSON invalido')
        process.exit(2)
    }

    const validation = validateLocalRenderInput(pkg, associationInput)
    if (!validation.ok) {
        console.log(JSON.stringify({
            ok: false,
            caseId: creation.caseId,
            packageId: pkg.packageId,
            failureCode: validation.failureCode,
            subject: validation.subject,
            plan,
        }))
        process.exit(3)
    }

    console.log(JSON.stringify({
        ok: true,
        status: 'generated',
        caseId: creation.caseId,
        packageId: pkg.packageId,
        package: pkg,
        canonicalJson,
        canonicalTextOverlayJson,
        canonicalVisualStyleJson,
        canonicalAssetManifestJson: null,
        textOverlays: textOverlayPlan,
        resolvedTextOverlays,
        visualStyle,
        assetManifest: null,
        resolvedAssetBindings: [],
        association: validation.association,
        plan,
    }))
    process.exit(0)
}

function handleLegacy(packagePath, associationPath) {
    let packageInput
    let associationInput
    try {
        packageInput = JSON.parse(readFileSync(packagePath, 'utf8'))
        associationInput = JSON.parse(readFileSync(associationPath, 'utf8'))
    } catch {
        console.error('erro: arquivo de entrada ilegivel ou JSON invalido')
        process.exit(2)
    }

    const result = validateLocalRenderInput(packageInput, associationInput)
    console.log(JSON.stringify(result))
    process.exit(result.ok ? 0 : 3)
}

function handleVideoRequest(args) {
    let requestPath = null
    let rootDir = process.cwd()
    let profileFilter = null

    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === '--video-request' && i + 1 < args.length) {
            requestPath = args[++i]
        } else if (arg === '--root' && i + 1 < args.length) {
            rootDir = args[++i]
        } else if (arg === '--profile' && i + 1 < args.length) {
            profileFilter = args[++i]
        } else if (arg === '--plan-only') {
            // A compilacao e pura; a previa e a exportacao consomem o mesmo veredito.
        } else {
            console.error(`erro: flag desconhecida na ponte: ${arg}`)
            process.exit(2)
        }
    }

    if (!requestPath) {
        console.error('uso: node tools/render_bridge.mjs --video-request <pedido.json> [--root <raiz>] [--profile <id>] [--plan-only]')
        process.exit(2)
    }

    let requestInput
    try {
        requestInput = JSON.parse(readFileSync(requestPath, 'utf8'))
    } catch {
        console.error('erro: arquivo de pedido ilegivel ou JSON invalido')
        process.exit(2)
    }

    if (typeof requestInput !== 'object' || requestInput === null || typeof requestInput.project !== 'string') {
        console.log(JSON.stringify({ ok: false, failureCode: 'VIDEO_REQUEST_INVALID', subject: 'project' }))
        process.exit(3)
    }

    const projectPath = path.resolve(rootDir, requestInput.project)
    let projectInput
    try {
        projectInput = JSON.parse(readFileSync(projectPath, 'utf8'))
    } catch {
        console.error('erro: ProjectManifest do pedido ilegivel ou ausente')
        process.exit(2)
    }

    const options = profileFilter === null ? undefined : { profileFilter }
    const result = compileVideoRequest(requestInput, projectInput, options)
    console.log(JSON.stringify(result))
    process.exit(result.ok ? 0 : 3)
}

function handleCarouselRequest(args) {
    let requestPath = null
    let rootDir = process.cwd()
    let profileOverride = null

    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === '--carousel-request' && i + 1 < args.length) requestPath = args[++i]
        else if (arg === '--root' && i + 1 < args.length) rootDir = args[++i]
        else if (arg === '--profile' && i + 1 < args.length) profileOverride = args[++i]
        else if (arg === '--plan-only') { /* compilacao pura */ }
        else { console.error(`erro: flag desconhecida na ponte: ${arg}`); process.exit(2) }
    }
    if (!requestPath) {
        console.error('uso: node tools/render_bridge.mjs --carousel-request <pedido.json> [--root <raiz>] [--profile <id>]')
        process.exit(2)
    }
    let requestInput
    try { requestInput = JSON.parse(readFileSync(requestPath, 'utf8')) }
    catch { console.error('erro: pedido de carrossel ilegivel ou JSON invalido'); process.exit(2) }
    if (typeof requestInput !== 'object' || requestInput === null || typeof requestInput.project !== 'string') {
        console.log(JSON.stringify({ ok: false, failureCode: 'CAROUSEL_REQUEST_INVALID', subject: 'project' }))
        process.exit(3)
    }
    let projectInput
    try { projectInput = JSON.parse(readFileSync(path.resolve(rootDir, requestInput.project), 'utf8')) }
    catch { console.error('erro: ProjectManifest do carrossel ilegivel ou ausente'); process.exit(2) }

    const validation = validateCarouselRequest(requestInput)
    if (!validation.ok) {
        console.log(JSON.stringify({ ok: false, failureCode: validation.failureCode, subject: validation.subject }))
        process.exit(3)
    }
    const request = validation.request
    const profileId = profileOverride || request.profile || 'instagram-feed-image-square'
    const resolution = resolveOutputPlan(projectInput, profileId)
    if (resolution.plan === null) {
        console.log(JSON.stringify({
            ok: false, requestId: request.id, profileId,
            failureCode: resolution.report.errors[0]?.code ?? 'OUTPUT_PLAN_INVALID',
            errors: resolution.report.errors,
        }))
        process.exit(3)
    }
    if (resolution.plan.mediaKind !== 'image') {
        console.log(JSON.stringify({ ok: false, requestId: request.id, profileId, failureCode: 'CAROUSEL_PROFILE_NOT_IMAGE' }))
        process.exit(3)
    }
    const mediaById = new Map(request.media.map((m) => [m.id, m]))
    const cards = request.cards.map((card, index) => ({
        order: index + 1,
        id: card.id,
        title: card.title,
        body: card.body ?? null,
        mediaId: card.mediaId ?? null,
        mediaPath: card.mediaId ? mediaById.get(card.mediaId).path : null,
    }))
    console.log(JSON.stringify({
        ok: true,
        requestId: request.id,
        profileId,
        geometry: resolution.plan.image,
        cards,
        warnings: resolution.report.warnings,
    }))
    process.exit(0)
}

const rawArgs = process.argv.slice(2)
if (rawArgs.length === 0) {
    console.error('uso: node tools/render_bridge.mjs <package.json> <assets.json> OU --case <caso.pipeline.json> OU --video-request <pedido.json> OU --carousel-request <pedido.json>')
    process.exit(2)
}

if (rawArgs.includes('--carousel-request')) {
    handleCarouselRequest(rawArgs)
} else if (rawArgs.includes('--video-request')) {
    handleVideoRequest(rawArgs)
} else if (rawArgs[0].startsWith('--')) {
    handleCasePipeline(rawArgs)
} else {
    if (rawArgs.length !== 2) {
        console.error('uso: node tools/render_bridge.mjs <package.json> <assets.json>')
        process.exit(2)
    }
    handleLegacy(rawArgs[0], rawArgs[1])
}
