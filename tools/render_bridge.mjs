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
import { validatePlanningSuggestion } from '../platform/dist/src/validate-planning-suggestion.js'
import { resolveOutputPlan } from '../platform/dist/src/resolve-output-profile.js'
import { resolveMotionPlan } from '../platform/dist/src/resolve-motion-plan.js'
import { serializeAssetManifest } from '../platform/dist/src/serialize-asset-manifest.js'
import { serializeCreativeExecutionPackage } from '../platform/dist/src/serialize-creative-execution-package.js'
import { serializeTextOverlayPlan } from '../platform/dist/src/serialize-text-overlay-plan.js'
import { serializeVisualStyle } from '../platform/dist/src/serialize-visual-style.js'
import { validateAssetManifest } from '../platform/dist/src/validate-asset-manifest.js'
import { findOutputProfile } from '../platform/dist/src/output-profiles/catalog.js'
import { localExportCapabilities } from '../platform/dist/src/output-profiles/local-export.js'
import { validateVisualAnchor } from '../platform/dist/src/validate-visual-anchor.js'
import { validateImageRequest } from '../platform/dist/src/validate-image-request.js'
import {
    checkLocalRenderConfiguration,
    validateLocalRenderInput,
} from '../platform/dist/src/validate-local-render-input.js'
import { validateTextOverlayPlan } from '../platform/dist/src/validate-text-overlay-plan.js'
import { validateVisualStyle } from '../platform/dist/src/validate-visual-style.js'

function emitJsonAndExit(payload, exitCode) {
    process.exitCode = exitCode
    process.stdout.write(JSON.stringify(payload) + '\n', () => {
        process.exit(exitCode)
    })
}

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
        return emitJsonAndExit({
            ok: false,
            status: creation.status,
            caseId: creation.caseId,
            failureCode,
            packageErrors: creation.packageErrors,
            summary: creation.summary,
        }, 3)
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
            return emitJsonAndExit({
                ok: false,
                caseId: creation.caseId,
                packageId: pkg.packageId,
                failureCode: overlayValidation.failureCode,
                subject: overlayValidation.subject,
                plan,
            }, 3)
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
            return emitJsonAndExit({
                ok: false,
                caseId: creation.caseId,
                packageId: pkg.packageId,
                failureCode: styleValidation.failureCode,
                subject: styleValidation.subject,
                plan,
            }, 3)
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
            return emitJsonAndExit({
                ok: false,
                caseId: creation.caseId,
                packageId: pkg.packageId,
                failureCode: manifestValidation.failureCode,
                subject: manifestValidation.subject,
                plan,
            }, 3)
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
        return emitJsonAndExit({
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
        }, 0)
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
        return emitJsonAndExit({
            ok: false,
            caseId: creation.caseId,
            packageId: pkg.packageId,
            failureCode: validation.failureCode,
            subject: validation.subject,
            plan,
        }, 3)
    }

    return emitJsonAndExit({
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
    }, 0)
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
    return emitJsonAndExit(result, result.ok ? 0 : 3)
}

function handleVideoRequest(args) {
    let requestPath = null
    let rootDir = process.cwd()
    let profileFilter = null
    let motionPlanPath = null

    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === '--video-request' && i + 1 < args.length) {
            requestPath = args[++i]
        } else if (arg === '--root' && i + 1 < args.length) {
            rootDir = args[++i]
        } else if (arg === '--profile' && i + 1 < args.length) {
            profileFilter = args[++i]
        } else if (arg === '--motion-plan' && i + 1 < args.length) {
            motionPlanPath = args[++i]
        } else if (arg === '--plan-only') {
            // A compilacao e pura; a previa e a exportacao consomem o mesmo veredito.
        } else {
            console.error(`erro: flag desconhecida na ponte: ${arg}`)
            process.exit(2)
        }
    }

    if (!requestPath) {
        console.error('uso: node tools/render_bridge.mjs --video-request <pedido.json> [--root <raiz>] [--profile <id>] [--motion-plan <plano.json>] [--plan-only]')
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
        return emitJsonAndExit({ ok: false, failureCode: 'VIDEO_REQUEST_INVALID', subject: 'project' }, 3)
    }

    const projectPath = path.resolve(rootDir, requestInput.project)
    let projectInput
    try {
        projectInput = JSON.parse(readFileSync(projectPath, 'utf8'))
    } catch {
        console.error('erro: ProjectManifest do pedido ilegivel ou ausente')
        process.exit(2)
    }

    let motionInput = null
    if (motionPlanPath) {
        try {
            motionInput = JSON.parse(readFileSync(motionPlanPath, 'utf8'))
        } catch {
            console.error('erro: plano de motion ilegivel ou JSON invalido')
            process.exit(2)
        }
    }

    const options = profileFilter === null ? undefined : { profileFilter }
    const result = compileVideoRequest(requestInput, projectInput, options)
    if (result.ok && motionInput !== null) {
        for (const profile of result.profiles) {
            if (profile.status !== 'compiled') continue
            const catalogProfile = findOutputProfile(profile.profileId)
            const motionCap = catalogProfile ? localExportCapabilities(catalogProfile).motion : null
            if (!motionCap || !motionCap.supported) {
                profile.status = 'failed'
                profile.failureCode = 'MOTION_LOCAL_UNSUPPORTED_GEOMETRY'
                profile.errors = [{
                    code: 'MOTION_LOCAL_UNSUPPORTED_GEOMETRY',
                    path: profile.profileId,
                    message: 'Motion local disponivel apenas em 9:16 nesta rodada; o contorno usa coordenadas relativas ao quadro final e exige configuracao propria para outro enquadramento.',
                }]
                continue
            }
            const resolution = resolveMotionPlan(profile.package, motionInput)
            if (resolution.ok) {
                profile.motion = { requestId: resolution.requestId, effects: resolution.effects }
            } else {
                profile.status = 'failed'
                profile.failureCode = resolution.failureCode
                profile.errors = [{ code: resolution.failureCode, path: resolution.subject ?? '', message: resolution.failureCode }]
            }
        }
    }
    return emitJsonAndExit(result, result.ok ? 0 : 3)
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
        return emitJsonAndExit({ ok: false, failureCode: 'CAROUSEL_REQUEST_INVALID', subject: 'project' }, 3)
    }
    let projectInput
    try { projectInput = JSON.parse(readFileSync(path.resolve(rootDir, requestInput.project), 'utf8')) }
    catch { console.error('erro: ProjectManifest do carrossel ilegivel ou ausente'); process.exit(2) }

    const validation = validateCarouselRequest(requestInput)
    if (!validation.ok) {
        return emitJsonAndExit({ ok: false, failureCode: validation.failureCode, subject: validation.subject }, 3)
    }
    const request = validation.request
    const profileId = profileOverride || request.profile || 'instagram-feed-image-square'
    const resolution = resolveOutputPlan(projectInput, profileId)
    if (resolution.plan === null) {
        return emitJsonAndExit({
            ok: false, requestId: request.id, profileId,
            failureCode: resolution.report.errors[0]?.code ?? 'OUTPUT_PLAN_INVALID',
            errors: resolution.report.errors,
        }, 3)
    }
    if (resolution.plan.mediaKind !== 'image') {
        return emitJsonAndExit({ ok: false, requestId: request.id, profileId, failureCode: 'CAROUSEL_PROFILE_NOT_IMAGE' }, 3)
    }
    const carouselProfile = findOutputProfile(profileId)
    const carouselCap = carouselProfile ? localExportCapabilities(carouselProfile).carousel : null
    if (!carouselCap || !carouselCap.supported) {
        return emitJsonAndExit({
            ok: false, requestId: request.id, profileId,
            failureCode: 'CAROUSEL_LOCAL_UNSUPPORTED_GEOMETRY',
            errors: [{ code: 'CAROUSEL_LOCAL_UNSUPPORTED_GEOMETRY', path: profileId, message: 'Geometria sem render local de carrossel nesta rodada (suportados: 1:1 1080x1080 e 4:5 1080x1350).' }],
        }, 3)
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
    return emitJsonAndExit({
        ok: true,
        requestId: request.id,
        profileId,
        geometry: resolution.plan.image,
        cards,
        warnings: resolution.report.warnings,
    }, 0)
}

function handlePlanningSuggestion(args) {
    let suggestionPath = null
    let projectRel = null
    let rootDir = process.cwd()

    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === '--planning-suggestion' && i + 1 < args.length) suggestionPath = args[++i]
        else if (arg === '--project' && i + 1 < args.length) projectRel = args[++i]
        else if (arg === '--root' && i + 1 < args.length) rootDir = args[++i]
        else { console.error(`erro: flag desconhecida na ponte: ${arg}`); process.exit(2) }
    }
    if (!suggestionPath) {
        console.error('uso: node tools/render_bridge.mjs --planning-suggestion <sugestao.json> [--project <projeto.json>] [--root <raiz>]')
        process.exit(2)
    }
    let suggestionInput
    try { suggestionInput = JSON.parse(readFileSync(suggestionPath, 'utf8')) }
    catch { console.error('erro: sugestao de planejamento ilegivel ou JSON invalido'); process.exit(2) }

    let projectInput
    if (projectRel) {
        try { projectInput = JSON.parse(readFileSync(path.resolve(rootDir, projectRel), 'utf8')) }
        catch { console.error('erro: ProjectManifest informado ilegivel ou ausente'); process.exit(2) }
    }

    const result = validatePlanningSuggestion(suggestionInput, projectInput)
    return emitJsonAndExit(result, result.ok ? 0 : 3)
}

function handleVisualContract(args, flag, validator, resultKey, label) {
    let docPath = null
    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === flag && i + 1 < args.length) docPath = args[++i]
        else if (arg === '--root' && i + 1 < args.length) i++
        else { console.error(`erro: flag desconhecida na ponte: ${arg}`); process.exit(2) }
    }
    if (!docPath) {
        console.error(`uso: node tools/render_bridge.mjs ${flag} <${label}.json> [--root <raiz>]`)
        process.exit(2)
    }
    let docInput
    try { docInput = JSON.parse(readFileSync(docPath, 'utf8')) }
    catch { console.error(`erro: ${label} ilegivel ou JSON invalido`); process.exit(2) }

    const result = validator(docInput)
    if (result.ok) {
        return emitJsonAndExit({ ok: true, [resultKey]: result[resultKey] }, 0)
    }
    return emitJsonAndExit({
        ok: false,
        failureCode: result.failureCode,
        subject: result.subject,
        message: `${label} fora do contrato v1 (${result.failureCode}).`,
    }, 3)
}

const rawArgs = process.argv.slice(2)
if (rawArgs.length === 0) {
    console.error('uso: node tools/render_bridge.mjs <package.json> <assets.json> OU --case <caso.pipeline.json> OU --video-request <pedido.json> OU --carousel-request <pedido.json> OU --planning-suggestion <sugestao.json>')
    process.exit(2)
}

if (rawArgs.includes('--visual-anchor')) {
    handleVisualContract(rawArgs, '--visual-anchor', validateVisualAnchor, 'anchor', 'ancora visual')
} else if (rawArgs.includes('--image-request')) {
    handleVisualContract(rawArgs, '--image-request', validateImageRequest, 'request', 'pedido de imagem')
} else if (rawArgs.includes('--planning-suggestion')) {
    handlePlanningSuggestion(rawArgs)
} else if (rawArgs.includes('--carousel-request')) {
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
