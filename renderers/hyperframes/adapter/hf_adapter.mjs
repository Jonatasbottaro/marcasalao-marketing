#!/usr/bin/env node
/**
 * hf_adapter.mjs — orquestrador do adaptador HyperFrames (HF-001, F6).
 *
 * Entrada: um perfil compilado do render_bridge (--video-request), o tenant e a
 * raiz do projeto. Fluxo: carga de identidade/guardrails -> validacao textual ->
 * materializacao da composicao -> hyperframes check -> hyperframes render ->
 * verificacao ffprobe (VIDEO CLEAN: 0 streams de audio) -> veredito JSON.
 *
 * Uso (sempre via wrapper com env confinado):
 *   bash renderers/hyperframes/scripts/hf-adapter.sh \
 *     --profile-json <perfil.json> --root <raiz> --tenant marca-salao \
 *     --workdir <dir> --out <video.mp4> [--quality draft|looks|delivery] [--skip-render]
 *
 * Exit codes: 0 ok; 2 uso; 3 entrada/guardrails; 4 check; 5 render; 6 ffprobe.
 */

import { readFileSync, existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { loadTenant, resolveVideoTokens, validateGuardrails } from './tenant.mjs'
import { composeProject } from './compose.mjs'

const RUNTIME_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const HF_CLI = path.join(RUNTIME_DIR, 'node_modules', 'hyperframes', 'bin', 'hyperframes.mjs')

function emit(payload, exitCode) {
    process.stdout.write(JSON.stringify(payload) + '\n')
    process.exitCode = exitCode
}

function parseArgs(argv) {
    const args = {
        profileJson: null,
        root: process.cwd(),
        tenant: null,
        workdir: null,
        out: null,
        quality: 'draft',
        skipRender: false,
        skipCheck: false,
    }
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i]
        if (arg === '--profile-json' && i + 1 < argv.length) args.profileJson = argv[++i]
        else if (arg === '--root' && i + 1 < argv.length) args.root = argv[++i]
        else if (arg === '--tenant' && i + 1 < argv.length) args.tenant = argv[++i]
        else if (arg === '--workdir' && i + 1 < argv.length) args.workdir = argv[++i]
        else if (arg === '--out' && i + 1 < argv.length) args.out = argv[++i]
        else if (arg === '--quality' && i + 1 < argv.length) args.quality = argv[++i]
        else if (arg === '--skip-render') args.skipRender = true
        else if (arg === '--skip-check') args.skipCheck = true
        else {
            process.stderr.write(`erro: flag desconhecida: ${arg}\n`)
            process.exit(2)
        }
    }
    if (!args.profileJson || !args.tenant || !args.workdir) {
        process.stderr.write('uso: hf_adapter.mjs --profile-json <perfil.json> --root <raiz> --tenant <id> --workdir <dir> [--out <mp4>] [--quality draft|looks|delivery] [--skip-render] [--skip-check]\n')
        process.exit(2)
    }
    if (!['draft', 'looks', 'delivery'].includes(args.quality)) {
        process.stderr.write('erro: --quality aceita draft|looks|delivery\n')
        process.exit(2)
    }
    if (!args.skipRender && !args.out) {
        process.stderr.write('erro: --out e obrigatorio sem --skip-render\n')
        process.exit(2)
    }
    return args
}

function assertInsideRoot(root, target, label) {
    const rootAbs = path.resolve(root)
    const targetAbs = path.resolve(target)
    if (targetAbs !== rootAbs && !targetAbs.startsWith(rootAbs + path.sep)) {
        emit({ ok: false, failureCode: 'PATH_ESCAPE', subject: label, path: target }, 3)
        process.exit(3)
    }
    return targetAbs
}

function runCommand(bin, args, cwd) {
    // Windows: shims de node_modules/.bin nao sao executaveis; o CLI e um modulo
    // ESM do proprio pacote, entao o spawn e sempre [node, cli.mjs, ...args].
    const argv = bin === HF_CLI ? [process.execPath, bin, ...args] : [bin, ...args]
    const result = spawnSync(argv[0], argv.slice(1), { cwd, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 })
    return {
        status: result.status,
        stdout: result.stdout ?? '',
        stderr: result.stderr ?? '',
        error: result.error ? String(result.error) : null,
    }
}

function tail(text, lines = 20) {
    const parts = String(text).trim().split(/\r?\n/)
    return parts.slice(-lines).join('\n')
}

function ffprobeStreams(outAbs) {
    const probe = runCommand('ffprobe', [
        '-v', 'error',
        '-show_entries', 'stream=codec_type,codec_name,width,height',
        '-show_entries', 'format=duration',
        '-of', 'json',
        outAbs,
    ], path.dirname(outAbs))
    if (probe.status !== 0) {
        return { ok: false, failureCode: 'FFPROBE_FAILED', detail: tail(probe.stderr || probe.stdout) }
    }
    let parsed
    try {
        parsed = JSON.parse(probe.stdout)
    } catch {
        return { ok: false, failureCode: 'FFPROBE_OUTPUT_INVALID', detail: tail(probe.stdout) }
    }
    const streams = parsed.streams ?? []
    const video = streams.filter((s) => s.codec_type === 'video')
    const audio = streams.filter((s) => s.codec_type === 'audio')
    return { ok: true, video, audio, durationSeconds: Number(parsed.format?.duration ?? 0) }
}

const args = parseArgs(process.argv.slice(2))
const rootAbs = path.resolve(args.root)
const workdirAbs = assertInsideRoot(rootAbs, args.workdir, 'workdir')
const outAbs = args.out ? assertInsideRoot(rootAbs, args.out, 'out') : null

let profile
try {
    profile = JSON.parse(readFileSync(path.resolve(args.profileJson), 'utf8'))
} catch {
    emit({ ok: false, failureCode: 'PROFILE_JSON_INVALID' }, 3)
    process.exit(3)
}
if (profile.status !== 'compiled' || !profile.plan) {
    emit({ ok: false, failureCode: 'PROFILE_NOT_COMPILED', profileId: profile.profileId ?? null, failureCodeFromCompiler: profile.failureCode ?? null }, 3)
    process.exit(3)
}

let tenant
try {
    tenant = loadTenant(rootAbs, args.tenant)
} catch (error) {
    emit({ ok: false, failureCode: String(error.message ?? error).split(':')[0], detail: String(error.message ?? error) }, 3)
    process.exit(3)
}

let tokens
try {
    tokens = resolveVideoTokens(tenant)
} catch (error) {
    emit({ ok: false, failureCode: String(error.message ?? error).split(':')[0], detail: String(error.message ?? error) }, 3)
    process.exit(3)
}

// Enrique os beats com o tipo de midia (composition.scenes carrega type por cena).
const typeByScene = new Map((profile.composition?.scenes ?? []).map((scene) => [scene.id, scene.type]))
for (const beat of profile.plan.beats) {
    beat.mediaType = typeByScene.get(beat.beatId) ?? 'image'
}

const violations = validateGuardrails(tenant, profile.plan.beats)
if (violations.length > 0) {
    emit({
        ok: false,
        failureCode: 'GUARDRAILS_VIOLATION',
        tenant: args.tenant,
        violations,
    }, 3)
    process.exit(3)
}

let composed
try {
    composed = composeProject({ profile, tokens, root: rootAbs, workdir: workdirAbs })
} catch (error) {
    emit({ ok: false, failureCode: String(error.message ?? error).split(':')[0], detail: String(error.message ?? error) }, 3)
    process.exit(3)
}

if (!args.skipCheck) {
    if (!existsSync(HF_CLI)) {
        emit({ ok: false, failureCode: 'HF_BINARY_MISSING', path: HF_CLI }, 4)
        process.exit(4)
    }
    const check = runCommand(HF_CLI, ['check'], workdirAbs)
    if (check.status !== 0) {
        emit({
            ok: false,
            failureCode: 'HF_CHECK_FAILED',
            exitCode: check.status,
            detail: tail(check.stderr || check.stdout, 40),
        }, 4)
        process.exit(4)
    }
}

if (args.skipRender) {
    emit({
        ok: true,
        adapter: 'hyperframes',
        caseId: profile.caseId,
        profileId: profile.profileId,
        rendered: false,
        workdir: workdirAbs,
        narrationFile: path.join(workdirAbs, 'narracao.txt'),
        geometry: composed.geometry,
        totalSeconds: composed.totalSeconds,
        beats: composed.beats,
        quality: args.quality,
    }, 0)
    process.exit(0)
}

const render = runCommand(HF_CLI, ['render', '--quality', args.quality, '--output', outAbs], workdirAbs)
if (render.status !== 0) {
    emit({
        ok: false,
        failureCode: 'HF_RENDER_FAILED',
        exitCode: render.status,
        detail: tail(render.stderr || render.stdout, 40),
    }, 5)
    process.exit(5)
}

const probe = ffprobeStreams(outAbs)
if (!probe.ok) {
    emit({ ok: false, failureCode: probe.failureCode, detail: probe.detail }, 6)
    process.exit(6)
}
if (probe.video.length !== 1) {
    emit({ ok: false, failureCode: 'FFPROBE_VIDEO_STREAMS', videoStreams: probe.video.length }, 6)
    process.exit(6)
}
if (probe.audio.length !== 0) {
    emit({ ok: false, failureCode: 'FFPROBE_AUDIO_PRESENT', audioStreams: probe.audio.length, policy: 'VIDEO_CLEAN' }, 6)
    process.exit(6)
}
const video = probe.video[0]
if (video.width !== composed.geometry.width || video.height !== composed.geometry.height) {
    emit({
        ok: false,
        failureCode: 'FFPROBE_GEOMETRY_MISMATCH',
        expected: composed.geometry,
        actual: { width: video.width, height: video.height },
    }, 6)
    process.exit(6)
}
const durationDelta = Math.abs(probe.durationSeconds - composed.totalSeconds)
if (durationDelta > 0.5) {
    emit({
        ok: false,
        failureCode: 'FFPROBE_DURATION_MISMATCH',
        expectedSeconds: composed.totalSeconds,
        actualSeconds: probe.durationSeconds,
    }, 6)
    process.exit(6)
}

emit({
    ok: true,
    adapter: 'hyperframes',
    caseId: profile.caseId,
    profileId: profile.profileId,
    rendered: true,
    outputPath: outAbs,
    codec: video.codec_name,
    geometry: { width: video.width, height: video.height },
    durationSeconds: probe.durationSeconds,
    expectedDurationSeconds: composed.totalSeconds,
    audioStreams: 0,
    videoStreams: 1,
    quality: args.quality,
    workdir: workdirAbs,
    narrationFile: path.join(workdirAbs, 'narracao.txt'),
    beats: composed.beats,
}, 0)
process.exit(0)
