// compose.mjs — materializa um projeto de composicao HyperFrames a partir de um
// perfil compilado (VideoRequest -> compile-video-request) e dos tokens do tenant.
// Adaptador HF-001 (F6). VIDEO CLEAN: nenhum elemento de audio; textos graficos
// editoriais (header, headline, subline) permanecem; narracao NAO e queimada.

import { mkdirSync, copyFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const HYPERFRAMES_VERSION = '0.9.103'
const GSAP_CDN = 'https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js'

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;')
}

function seconds(ms) {
    return Math.round(ms) / 1000
}

/** Margem inferior de area segura por geometria (interface do Reels + legendas futuras). */
function safeBottomMargin(height) {
    return Math.max(120, Math.round(height * 0.14))
}

function fontSizeFor(width, base) {
    return Math.max(20, Math.round((width / 1080) * base))
}

/**
 * Copia a midia referenciada pelos beats para <workdir>/assets e devolve o mapa
 * beatId -> {file, type, sourceStartSeconds}.
 */
export function stageAssets(beats, root, workdir) {
    const assetsDir = path.join(workdir, 'assets')
    mkdirSync(assetsDir, { recursive: true })
    const rootAbs = path.resolve(root)
    const staged = new Map()
    const usedFiles = new Map()
    for (const beat of beats) {
        if (!beat.mediaPath) continue
        const sourceAbs = path.resolve(rootAbs, beat.mediaPath)
        if (sourceAbs !== rootAbs && !sourceAbs.startsWith(rootAbs + path.sep)) {
            throw new Error(`ASSET_PATH_ESCAPE: midia fora da raiz: ${beat.mediaPath}`)
        }
        const name = `${beat.beatId}${path.extname(beat.mediaPath) || ''}`
        const target = path.join(assetsDir, name)
        if (!usedFiles.has(sourceAbs)) {
            copyFileSync(sourceAbs, target)
            usedFiles.set(sourceAbs, name)
        }
        staged.set(beat.beatId, {
            file: `assets/${usedFiles.get(sourceAbs)}`,
            type: beat.mediaType ?? 'image',
            sourceStartSeconds: beat.sourceStartMs ? seconds(beat.sourceStartMs) : 0,
        })
    }
    return staged
}

function mediaClipHtml(beat, staged, geometry, motionIntent) {
    const start = seconds(beat.startMs)
    const duration = seconds(beat.durationMs)
    const asset = staged.get(beat.beatId)
    if (!asset) return ''
    const id = `media-${beat.beatId}`
    if (asset.type === 'video') {
        const mediaStart = asset.sourceStartSeconds
            ? ` data-media-start="${asset.sourceStartSeconds}"`
            : ''
        // VIDEO CLEAN: video sempre muted; a exportacao nao tem faixa de audio.
        return `      <video id="${id}" class="clip" src="${escapeHtml(asset.file)}" muted${mediaStart}
        data-start="${start}" data-duration="${duration}" data-track-index="0"
        style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;"></video>`
    }
    const position = beat.framing
        ? `background-position:${Math.round(beat.framing.centerX * 100)}% ${Math.round(beat.framing.centerY * 100)}%;`
        : 'background-position:50% 50%;'
    const zoom = beat.framing?.zoomPercent ? beat.framing.zoomPercent / 100 : 1
    const innerId = `${id}-inner`
    const staticStyle = motionIntent !== 'slow-zoom' && zoom !== 1
        ? `transform:scale(${zoom});`
        : ''
    return `      <div id="${id}" class="clip"
        data-start="${start}" data-duration="${duration}" data-track-index="0"
        style="position:absolute; inset:0; overflow:hidden;">
        <div id="${innerId}"
          style="position:absolute; inset:0; background-image:url('${escapeHtml(asset.file)}'); background-size:cover; ${position} transform-origin:50% 50%; ${staticStyle}"></div>
      </div>`
}

function headerHtml(tokens, totalSeconds) {
    if (!tokens.header.enabled) return ''
    const height = tokens.headerHeight
    const labelSize = fontSizeFor(1080, 44)
    const badgeSize = fontSizeFor(1080, 26)
    return `      <div id="header" class="clip"
        data-start="0" data-duration="${totalSeconds}" data-track-index="1"
        style="position:absolute; top:0; left:0; right:0; height:${height}px; background:${tokens.header.bg}; display:flex; align-items:center; justify-content:space-between; padding:0 48px;">
        <span id="header-label" style="color:${tokens.header.text}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.titleWeight}; font-size:${labelSize}px; letter-spacing:0.04em;">${escapeHtml(tokens.header.label)}</span>
        <span id="header-badge" style="background:${tokens.primary}; color:${tokens.background}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.bodyWeight}; font-size:${badgeSize}px; padding:10px 22px; border-radius:999px; letter-spacing:0.06em;">${escapeHtml(tokens.header.badge)}</span>
      </div>`
}

function textClipHtml(beat, geometry, tokens) {
    if (!beat.title && !beat.caption) return ''
    const start = seconds(beat.startMs)
    const duration = seconds(beat.durationMs)
    const id = `text-${beat.beatId}`
    const bottom = safeBottomMargin(geometry.height)
    const headlineSize = fontSizeFor(geometry.width, 64)
    const sublineSize = fontSizeFor(geometry.width, 38)
    const headline = beat.title
        ? `        <h2 id="${id}-headline" style="margin:0; color:${tokens.textPrimary}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.titleWeight}; font-size:${headlineSize}px; line-height:1.15;">${escapeHtml(beat.title)}</h2>\n`
        : ''
    const subline = beat.caption
        ? `        <p id="${id}-subline" style="margin:${beat.title ? '14px' : '0'} 0 0; color:${tokens.textMuted}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.bodyWeight}; font-size:${sublineSize}px; line-height:1.3;">${escapeHtml(beat.caption)}</p>\n`
        : ''
    return `      <div id="${id}" class="clip"
        data-start="${start}" data-duration="${duration}" data-track-index="2"
        style="position:absolute; left:64px; right:64px; bottom:${bottom}px;">
        <div id="${id}-bar" style="width:72px; height:8px; background:${tokens.primary}; border-radius:4px; margin-bottom:18px;"></div>
${headline}${subline}      </div>`
}

/**
 * Timeline GSAP seekable: entrada suave dos textos (fade + slide no no interno,
 * nunca autoAlpha/visibility no .clip), zoom lento na midia quando pedido e
 * fade-out apenas no ultimo beat (transitionOut: fade do BeatPlan).
 */
function timelineScript(beats, staged, geometry) {
    const lines = []
    const total = beats.length
    beats.forEach((beat, index) => {
        const start = seconds(beat.startMs)
        const duration = seconds(beat.durationMs)
        const id = `text-${beat.beatId}`
        const hasText = Boolean(beat.title || beat.caption)
        if (hasText) {
            lines.push(`  tl.fromTo("#${id}-bar", { opacity: 0, width: "0px" }, { opacity: 1, width: "72px", duration: 0.35, ease: "power2.out" }, ${start});`)
            if (beat.title) {
                lines.push(`  tl.fromTo("#${id}-headline", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, ${start + 0.08});`)
            }
            if (beat.caption) {
                lines.push(`  tl.fromTo("#${id}-subline", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, ${start + 0.18});`)
            }
            if (index === total - 1) {
                const fadeAt = Math.max(start + 0.6, start + duration - 0.5)
                lines.push(`  tl.to("#${id}-bar, #${id}-headline, #${id}-subline", { opacity: 0, duration: 0.4, ease: "power2.in" }, ${fadeAt});`)
            }
        }
        const asset = staged.get(beat.beatId)
        if (asset && beat.motionIntent === 'slow-zoom') {
            const zoom = beat.framing?.zoomPercent ? beat.framing.zoomPercent / 100 : 1
            const selector = asset.type === 'video' ? `#media-${beat.beatId}` : `#media-${beat.beatId}-inner`
            lines.push(`  tl.fromTo("${selector}", { scale: ${zoom} }, { scale: ${(zoom * 1.06).toFixed(3)}, duration: ${duration}, ease: "none" }, ${start});`)
        }
    })
    return `    const tl = gsap.timeline({ paused: true });
${lines.join('\n')}
    window.__timelines["main"] = tl;
    tl.seek(0);`
}

/** Roteiro de narracao separado (obrigatorio no modo clean; PT-BR, por cena e tempos). */
export function narrationText(profile, beats) {
    const lines = [
        `# Roteiro de narracao — ${profile.caseId ?? profile.profileId}`,
        `# Video: ${profile.plan?.geometry?.width ?? ''}x${profile.plan?.geometry?.height ?? ''} — duracao total ${(profile.plan?.durationMs ?? 0) / 1000}s`,
        '# Modo VIDEO CLEAN: este texto NAO esta no video; gravar a narracao em ferramenta externa.',
        '',
    ]
    for (const beat of beats) {
        const start = seconds(beat.startMs)
        const end = seconds(beat.startMs + beat.durationMs)
        lines.push(`[${start.toFixed(1)}s - ${end.toFixed(1)}s] ${beat.beatId}`)
        lines.push(String(beat.narration ?? ''))
        lines.push('')
    }
    return lines.join('\n')
}

/**
 * Escreve o projeto de composicao completo em workdir.
 * Retorna {totalSeconds, beats} para o orquestrador.
 */
export function composeProject({ profile, tokens, root, workdir }) {
    const plan = profile.plan
    if (!plan || !plan.geometry || !plan.durationMs || !Array.isArray(plan.beats) || plan.beats.length === 0) {
        throw new Error('PROFILE_PLAN_INVALID: plano do perfil compilado ausente ou vazio')
    }
    const geometry = plan.geometry
    const beats = plan.beats
    const totalSeconds = seconds(plan.durationMs)
    mkdirSync(workdir, { recursive: true })
    const staged = stageAssets(beats, root, workdir)

    const mediaClips = beats.map((beat) => mediaClipHtml(beat, staged, geometry, beat.motionIntent)).filter(Boolean)
    const textClips = beats.map((beat) => textClipHtml(beat, geometry, tokens)).filter(Boolean)
    const header = headerHtml(tokens, totalSeconds)

    const html = `<!doctype html>
<html lang="pt-BR" data-resolution="${geometry.width < geometry.height ? 'portrait' : 'landscape'}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${geometry.width}, height=${geometry.height}" />
    <script src="${GSAP_CDN}"></script>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body {
        width: ${geometry.width}px;
        height: ${geometry.height}px;
        overflow: hidden;
        background: ${tokens.background};
      }
      #root { width: 100%; height: 100%; position: relative; }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="${totalSeconds}"
      data-width="${geometry.width}"
      data-height="${geometry.height}"
    >
${mediaClips.join('\n')}
${header}
${textClips.join('\n')}
    </div>
    <script>
${timelineScript(beats, staged, geometry)}
    </script>
  </body>
</html>
`
    writeFileSync(path.join(workdir, 'index.html'), html, 'utf8')
    writeFileSync(path.join(workdir, 'hyperframes.json'), JSON.stringify({
        $schema: 'https://hyperframes.heygen.com/schema/hyperframes.json',
        registry: 'https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry',
        paths: { blocks: 'compositions', components: 'compositions/components', assets: 'assets' },
        media: { autoProxy: true },
    }, null, 2) + '\n', 'utf8')
    writeFileSync(path.join(workdir, 'package.json'), JSON.stringify({
        name: `hf-adapter-${(profile.caseId ?? 'case').replace(/[^a-z0-9-]/g, '-')}`,
        private: true,
        type: 'module',
        scripts: {
            dev: `npx --yes hyperframes@${HYPERFRAMES_VERSION} preview`,
            check: `npx --yes hyperframes@${HYPERFRAMES_VERSION} check`,
            render: `npx --yes hyperframes@${HYPERFRAMES_VERSION} render`,
        },
    }, null, 2) + '\n', 'utf8')
    writeFileSync(path.join(workdir, 'narracao.txt'), narrationText(profile, beats), 'utf8')
    return { totalSeconds, beats: beats.length, geometry }
}
