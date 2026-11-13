/**
 * Compilador puro do VideoRequest v1.
 *
 * Transforma um pedido unico + ProjectManifest nos documentos existentes por
 * perfil (Composition, BeatPlan, OutputPlan, CreativeExecutionPackage,
 * associacao de midia e titulos sobrepostos), resolvendo cada perfil apenas
 * pelo catalogo via resolveOutputPlan, respeitando a allowlist do projeto e
 * validando cada caso pelo pipeline canonico. Os casos gerados sao rascunhos
 * editoriais (metadata.status e validationStatus 'draft').
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 * Nenhuma regra por marca: perfis, geometria e tempos vem do catalogo e do
 * pedido; nada aqui conhece um projeto consumidor especifico.
 */

import type { Beat, BeatPlan, BeatNarrativeFunction } from './beat-plan-contract.js'
import type { Composition, CompositionScene } from './composition-contract.js'
import {
    createCreativeExecutionPackage,
} from './create-creative-execution-package.js'
import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import { serializeCreativeExecutionPackage } from './serialize-creative-execution-package.js'
import type { LocalRenderAssetAssociation } from './local-render-input-contract.js'
import { checkLocalRenderConfiguration } from './validate-local-render-input.js'
import type { OutputPlan } from './output-plan-contract.js'
import type { ProjectManifest } from './project-contract.js'
import { resolveOutputPlan } from './resolve-output-profile.js'
import type { TextOverlayPlan } from './text-overlay-plan-contract.js'
import { validateContentPipeline } from './validate-content-pipeline.js'
import { validateCreativeExecutionPackage } from './validate-creative-execution-package.js'
import { validateProjectManifest } from './validate-project.js'
import { validateVideoRequest } from './validate-video-request.js'
import { validateVisualStyle } from './validate-visual-style.js'
import type { VisualStyle } from './visual-style-contract.js'
import {
    VIDEO_REQUEST_DEFAULT_LICENSE,
    VIDEO_REQUEST_DEFAULT_LOCALE,
    type VideoRequest,
    type VideoRequestMedia,
    type VideoRequestScene,
} from './video-request-contract.js'

export interface VideoProfileBeatPreview {
    readonly beatId: string
    readonly order: number
    readonly startMs: number
    readonly endMs: number
    readonly durationMs: number
    readonly mediaId: string
    readonly mediaPath: string
    readonly caption: string
    readonly narration: string
    readonly title: string | null
}

export interface VideoProfilePreview {
    readonly profileId: string
    readonly caseId: string
    readonly packageId: string
    readonly geometry: { readonly width: number; readonly height: number; readonly aspectRatio: string }
    readonly fps: number
    readonly durationMs: number
    readonly durationSeconds: number
    readonly beats: readonly VideoProfileBeatPreview[]
    readonly supported: boolean
    readonly unsupportedReason: string | null
}

export interface CompiledVideoProfile {
    readonly profileId: string
    readonly caseId: string
    readonly status: 'compiled' | 'failed'
    readonly failureCode: string | null
    readonly errors: readonly { readonly code: string; readonly path: string; readonly message: string }[]
    readonly composition: Composition | null
    readonly beatPlan: BeatPlan | null
    readonly outputPlan: OutputPlan | null
    readonly package: CreativeExecutionPackage | null
    readonly canonicalPackageJson: string | null
    readonly association: LocalRenderAssetAssociation | null
    readonly textOverlayPlan: TextOverlayPlan | null
    readonly visualStyle: VisualStyle | null
    readonly plan: VideoProfilePreview | null
    readonly warnings: readonly { readonly code: string; readonly path: string; readonly message: string }[]
}

export interface CompileVideoRequestOptions {
    readonly profileFilter?: string
}

export type CompileVideoRequestResult =
    | {
        readonly ok: true
        readonly requestId: string
        readonly project: ProjectManifest
        readonly profiles: readonly CompiledVideoProfile[]
        readonly media: readonly { readonly id: string; readonly path: string; readonly type: string; readonly origin: string; readonly license: string }[]
    }
    | { readonly ok: false; readonly failureCode: string; readonly subject: string | null }

interface Issue {
    readonly code: string
    readonly path: string
    readonly message: string
}

function defaultNarrativeFunction(index: number, total: number): BeatNarrativeFunction {
    if (total === 1) return 'demonstration'
    if (index === 0) return 'hook'
    if (index === total - 1) return 'cta'
    return 'demonstration'
}

function buildComposition(request: VideoRequest, project: ProjectManifest, profileId: string, plan: OutputPlan, mediaById: Map<string, VideoRequestMedia>): Composition {
    const video = plan.mediaKind === 'video' ? plan.video : null
    const scenes: CompositionScene[] = request.scenes.map((scene) => {
        const media = mediaById.get(scene.mediaId) as VideoRequestMedia
        return {
            id: scene.id,
            type: media.type,
            durationMs: scene.durationMs,
            content: { asset: { id: media.id, path: media.path }, alt: scene.caption },
        } as CompositionScene
    })
    return {
        schemaVersion: 1,
        projectId: project.id,
        id: `${request.id}-${profileId}`,
        title: request.title,
        locale: request.locale ?? VIDEO_REQUEST_DEFAULT_LOCALE,
        format: {
            profile: profileId,
            width: video ? video.width : 0,
            height: video ? video.height : 0,
            fps: video ? video.fps : 0,
        },
        scenes,
        renderer: { adapter: 'undecided' },
        metadata: { status: 'draft', description: request.title, tags: ['video-request'] },
    }
}

function buildBeatPlan(request: VideoRequest, project: ProjectManifest, compositionId: string, profileId: string): BeatPlan {
    let startMs = 0
    const total = request.scenes.length
    const beats: Beat[] = request.scenes.map((scene, index) => {
        const beat: Beat = {
            id: scene.id,
            order: index + 1,
            sceneIds: [scene.id],
            narrativeFunction: scene.narrativeFunction ?? defaultNarrativeFunction(index, total),
            startMs,
            durationMs: scene.durationMs,
            narration: { text: scene.narration },
            onScreenText: scene.caption,
            visualIntent: scene.caption,
            motionIntent: scene.motionIntent ?? 'none',
            transitionIn: index === 0 ? 'none' : 'cut',
            transitionOut: index === total - 1 ? 'fade' : 'cut',
            editorialEvidence: [request.id],
            validationStatus: 'draft',
        }
        startMs += scene.durationMs
        return beat
    })
    return {
        schemaVersion: 1,
        projectId: project.id,
        compositionId,
        id: `${request.id}-${profileId}-beats`,
        locale: request.locale ?? VIDEO_REQUEST_DEFAULT_LOCALE,
        beats,
        metadata: { status: 'draft', description: request.title, tags: ['video-request'] },
    }
}

function failedProfile(profileId: string, caseId: string, failureCode: string, errors: readonly Issue[]): CompiledVideoProfile {
    return {
        profileId,
        caseId,
        status: 'failed',
        failureCode,
        errors,
        composition: null,
        beatPlan: null,
        outputPlan: null,
        package: null,
        canonicalPackageJson: null,
        association: null,
        textOverlayPlan: null,
        visualStyle: null,
        plan: null,
        warnings: [],
    }
}

function compileProfile(
    request: VideoRequest,
    project: ProjectManifest,
    profileId: string,
    mediaById: Map<string, VideoRequestMedia>,
    visualStyle: VisualStyle | null,
): CompiledVideoProfile {
    const caseId = `${request.id}-${profileId}`
    const resolution = resolveOutputPlan(project, profileId)
    const warnings: Issue[] = resolution.report.warnings.map((item) => ({ code: item.code, path: item.path, message: item.message }))
    if (resolution.plan === null) {
        const errors = resolution.report.errors.map((item) => ({ code: item.code, path: item.path, message: item.message }))
        return failedProfile(profileId, caseId, errors[0]?.code ?? 'OUTPUT_PLAN_INVALID', errors)
    }
    const plan = resolution.plan
    const composition = buildComposition(request, project, profileId, plan, mediaById)
    const beatPlan = buildBeatPlan(request, project, composition.id, profileId)
    const input = { project, composition, outputPlan: plan, beatPlan }
    const report = validateContentPipeline(input)
    if (!report.valid) {
        const errors = report.errors.map((item) => ({ code: item.code, path: item.path, message: item.message }))
        return failedProfile(profileId, caseId, errors[0]?.code ?? 'PIPELINE_INVALID', errors)
    }
    for (const item of report.warnings) {
        warnings.push({ code: item.code, path: item.path, message: item.message })
    }
    const creation = createCreativeExecutionPackage(input, report)
    if (!creation.ok) {
        return failedProfile(profileId, caseId, creation.failureCode, [])
    }
    const pkg = creation.package
    const validation = validateCreativeExecutionPackage(pkg)
    if (!validation.valid) {
        return failedProfile(profileId, caseId, 'PACKAGE_INVALID', validation.errors.map((item) => ({ code: item.code, path: item.path, message: item.message })))
    }

    const sceneById = new Map(request.scenes.map((scene) => [scene.id, scene]))
    const association: LocalRenderAssetAssociation = {
        schemaVersion: 1,
        packageId: pkg.packageId,
        assets: pkg.timeline.map((step) => {
            const scene = sceneById.get(step.beatId) as VideoRequestScene
            const media = mediaById.get(scene.mediaId) as VideoRequestMedia
            return { beatId: step.beatId, path: media.path }
        }),
    }
    const textOverlayPlan: TextOverlayPlan = {
        schemaVersion: 1,
        caseId,
        overlays: request.scenes
            .filter((scene) => scene.title !== undefined)
            .map((scene) => ({ beatId: scene.id, text: scene.title as string })),
    }
    const configCheck = checkLocalRenderConfiguration(pkg)
    const preview: VideoProfilePreview = {
        profileId,
        caseId,
        packageId: pkg.packageId,
        geometry: { width: pkg.output.width, height: pkg.output.height, aspectRatio: pkg.output.aspectRatio },
        fps: pkg.output.fps,
        durationMs: pkg.output.durationMs,
        durationSeconds: pkg.output.durationMs / 1000.0,
        beats: pkg.timeline.map((step) => {
            const scene = sceneById.get(step.beatId) as VideoRequestScene
            const media = mediaById.get(scene.mediaId) as VideoRequestMedia
            return {
                beatId: step.beatId,
                order: step.order,
                startMs: step.startMs,
                endMs: step.endMs,
                durationMs: step.durationMs,
                mediaId: scene.mediaId,
                mediaPath: media.path,
                caption: scene.caption,
                narration: scene.narration,
                title: scene.title ?? null,
            }
        }),
        supported: configCheck.supported,
        unsupportedReason: configCheck.unsupportedReason,
    }

    return {
        profileId,
        caseId,
        status: 'compiled',
        failureCode: null,
        errors: [],
        composition,
        beatPlan,
        outputPlan: plan,
        package: pkg,
        canonicalPackageJson: serializeCreativeExecutionPackage(pkg),
        association,
        textOverlayPlan,
        visualStyle,
        plan: preview,
        warnings,
    }
}

export function compileVideoRequest(
    requestInput: unknown,
    projectInput: unknown,
    options?: CompileVideoRequestOptions,
): CompileVideoRequestResult {
    const validation = validateVideoRequest(requestInput)
    if (!validation.ok) {
        return { ok: false, failureCode: validation.failureCode, subject: validation.subject }
    }
    const request = validation.request

    const projectReport = validateProjectManifest(projectInput)
    if (!projectReport.valid) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_PROJECT_INVALID', subject: projectReport.errors[0]?.code ?? null }
    }
    const project = projectInput as ProjectManifest

    let visualStyle: VisualStyle | null = null
    if (request.visualStyle !== undefined) {
        const styleResult = validateVisualStyle(request.visualStyle)
        if (!styleResult.ok) {
            return { ok: false, failureCode: 'VIDEO_REQUEST_VISUAL_STYLE_INVALID', subject: styleResult.failureCode }
        }
        visualStyle = styleResult.style
    }

    const profileIds = options?.profileFilter !== undefined ? [options.profileFilter] : [...request.profiles]
    if (options?.profileFilter !== undefined && !request.profiles.includes(options.profileFilter)) {
        return { ok: false, failureCode: 'VIDEO_REQUEST_PROFILES_INVALID', subject: options.profileFilter }
    }

    const mediaById = new Map(request.media.map((media) => [media.id, media]))
    const profiles = profileIds.map((profileId) => compileProfile(request, project, profileId, mediaById, visualStyle))
    const media = request.media.map((entry) => ({
        id: entry.id,
        path: entry.path,
        type: entry.type,
        origin: entry.origin,
        license: entry.license ?? VIDEO_REQUEST_DEFAULT_LICENSE,
    }))

    return { ok: true, requestId: request.id, project, profiles, media }
}