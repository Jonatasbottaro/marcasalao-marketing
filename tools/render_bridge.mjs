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
 *    node tools/render_bridge.mjs --case <case.pipeline.json> [--root <rootDir>] [--assets <assets.json>] [--plan-only]
 *    Carrega o caso, gera o CreativeExecutionPackage canonico a partir do caso
 *    valido e opcionalmente valida a associacao de assets e o recorte de configuracao.
 *
 * Exit codes: 0 sucesso/valido; 2 uso ou JSON ilegivel; 3 entrada invalida.
 */

import { readFileSync } from 'node:fs'
import path from 'node:path'

import { createCreativeExecutionPackageFromCase } from '../platform/dist/src/creative-execution-packages.js'
import { serializeCreativeExecutionPackage } from '../platform/dist/src/serialize-creative-execution-package.js'
import { serializeTextOverlayPlan } from '../platform/dist/src/serialize-text-overlay-plan.js'
import {
    checkLocalRenderConfiguration,
    validateLocalRenderInput,
} from '../platform/dist/src/validate-local-render-input.js'
import { validateTextOverlayPlan } from '../platform/dist/src/validate-text-overlay-plan.js'

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
    let textOverlaysPath = null
    let rootDir = process.cwd()
    let planOnly = false

    for (let i = 0; i < args.length; i++) {
        const arg = args[i]
        if (arg === '--case' && i + 1 < args.length) {
            casePath = args[++i]
        } else if (arg === '--assets' && i + 1 < args.length) {
            assetsPath = args[++i]
        } else if (arg === '--text-overlays' && i + 1 < args.length) {
            textOverlaysPath = args[++i]
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
        console.error('uso: node tools/render_bridge.mjs --case <caso.pipeline.json> [--root <raiz>] [--assets <assets.json>] [--text-overlays <overlays.json>] [--plan-only]')
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

    if (planOnly || !assetsPath) {
        console.log(JSON.stringify({
            ok: true,
            status: 'generated',
            caseId: creation.caseId,
            packageId: pkg.packageId,
            package: pkg,
            canonicalJson,
            canonicalTextOverlayJson,
            textOverlays: textOverlayPlan,
            resolvedTextOverlays,
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
        textOverlays: textOverlayPlan,
        resolvedTextOverlays,
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

const rawArgs = process.argv.slice(2)
if (rawArgs.length === 0) {
    console.error('uso: node tools/render_bridge.mjs <package.json> <assets.json> OU --case <caso.pipeline.json>')
    process.exit(2)
}

if (rawArgs[0].startsWith('--')) {
    handleCasePipeline(rawArgs)
} else {
    if (rawArgs.length !== 2) {
        console.error('uso: node tools/render_bridge.mjs <package.json> <assets.json>')
        process.exit(2)
    }
    handleLegacy(rawArgs[0], rawArgs[1])
}
