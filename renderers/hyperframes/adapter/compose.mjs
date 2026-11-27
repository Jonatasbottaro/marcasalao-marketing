// compose.mjs — materializa um projeto de composicao HyperFrames a partir de um
// perfil compilado (VideoRequest -> compile-video-request) e dos tokens do tenant.
// Adaptador HF-001 (F6/F9/F10). VIDEO CLEAN: nenhum elemento de audio; textos
// graficos editoriais (header, headline, subline) permanecem; narracao NAO e
// queimada.
//
// F9 — templates nativos por funcao narrativa, seguindo as "Regras de composicao
// por tipo de cena" do frame.md: hook -> card de marca centrado (fundo
// `background`); demonstration -> captura como estrela com texto ancorado na
// base sobre scrim suave; cta -> card de marca com convite centrado, sem
// aparencia de botao. A funcao vem do contrato neutro
// `profile.beatPlan.beats[].narrativeFunction` (hook|demonstration|cta); o
// `kind` legado (hook-card/manager-agenda/cta-card) nao existe no contrato.
// F10 — layout generico por geometria (1:1, 4:5, 9:16, 16:9) e modo still
// (desliga o fade do ultimo beat; o PNG e capturado pelo orquestrador via
// `hyperframes snapshot`).

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

/** Escala horizontal relativa a largura de referencia 1080 (margens, barras). */
function px(width, base) {
    return Math.max(1, Math.round((width / 1080) * base))
}

/** Margem inferior de area segura por geometria (interface do Reels + legendas futuras). */
function safeBottomMargin(height) {
    return Math.max(120, Math.round(height * 0.14))
}

function fontSizeFor(width, base) {
    return Math.max(20, Math.round((width / 1080) * base))
}

/** Valor aceito pelo atributo data-resolution do HyperFrames (inclui square). */
function resolutionFor(geometry) {
    if (geometry.width > geometry.height) return 'landscape'
    if (geometry.width < geometry.height) return 'portrait'
    return 'square'
}

function hexToRgba(hex, alpha) {
    const value = String(hex ?? '#000000').replace('#', '')
    const r = parseInt(value.slice(0, 2), 16)
    const g = parseInt(value.slice(2, 4), 16)
    const b = parseInt(value.slice(4, 6), 16)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/** Mapa beatId -> funcao narrativa (contrato BeatPlan); ausente = demonstration. */
function narrativeByBeat(profile) {
    const beats = profile?.beatPlan?.beats
    if (!Array.isArray(beats)) return new Map()
    return new Map(beats
        .filter((beat) => beat && typeof beat.id === 'string')
        .map((beat) => [beat.id, beat.narrativeFunction]))
}

/**
 * Tratamentos por funcao narrativa (frame.md): tamanhos em base 1080 e
 * reposicao (centrado em card de marca x ancorado na base sobre a captura).
 */
const TREATMENTS = {
    hook: {
        barWidth: 96, barHeight: 10,
        headline: 76, subline: 40, sublineGap: 18,
        centered: true, brandCard: true,
    },
    demonstration: {
        barWidth: 72, barHeight: 8,
        headline: 64, subline: 38, sublineGap: 14,
        centered: false, brandCard: false,
    },
    cta: {
        barWidth: 88, barHeight: 10,
        headline: 68, subline: 42, sublineGap: 16,
        centered: true, brandCard: true,
    },
}

function treatmentFor(narrative) {
    return TREATMENTS[narrative] ?? TREATMENTS.demonstration
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

/**
 * Camada de cena entre a midia e os textos (trilho 1): card de marca solido
 * (hook/cta, fundo normativo `background`) ou scrim inferior de legibilidade
 * (demonstration — a captura continua visivel, sem cartao sobre ela).
 */
function sceneLayerHtml(beat, geometry, tokens, treatment) {
    const start = seconds(beat.startMs)
    const duration = seconds(beat.durationMs)
    const id = `layer-${beat.beatId}`
    if (treatment.brandCard) {
        return `      <div id="${id}" class="clip"
        data-start="${start}" data-duration="${duration}" data-track-index="1"
        style="position:absolute; inset:0; background:${tokens.background};"></div>`
    }
    const scrimHeight = Math.round(geometry.height * 0.38)
    return `      <div id="${id}" class="clip"
        data-start="${start}" data-duration="${duration}" data-track-index="1"
        style="position:absolute; left:0; right:0; bottom:0; height:${scrimHeight}px;
        background:linear-gradient(180deg, ${hexToRgba(tokens.background, 0)} 0%, ${hexToRgba(tokens.background, 0.85)} 100%);"></div>`
}

function headerHtml(tokens, geometry, totalSeconds) {
    if (!tokens.header.enabled) return ''
    const height = tokens.headerHeight
    const labelSize = fontSizeFor(geometry.width, 44)
    const badgeSize = fontSizeFor(geometry.width, 26)
    const pad = px(geometry.width, 48)
    return `      <div id="header" class="clip"
        data-start="0" data-duration="${totalSeconds}" data-track-index="2"
        style="position:absolute; top:0; left:0; right:0; height:${height}px; background:${tokens.header.bg}; display:flex; align-items:center; justify-content:space-between; padding:0 ${pad}px;">
        <span id="header-label" style="color:${tokens.header.text}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.titleWeight}; font-size:${labelSize}px; letter-spacing:0.04em;">${escapeHtml(tokens.header.label)}</span>
        <span id="header-badge" style="background:${tokens.primary}; color:${tokens.background}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.bodyWeight}; font-size:${badgeSize}px; padding:${px(geometry.width, 10)}px ${px(geometry.width, 22)}px; border-radius:999px; letter-spacing:0.06em;">${escapeHtml(tokens.header.badge)}</span>
      </div>`
}

function textClipHtml(beat, geometry, tokens, treatment) {
    if (!beat.title && !beat.caption) return ''
    const start = seconds(beat.startMs)
    const duration = seconds(beat.durationMs)
    const id = `text-${beat.beatId}`
    const marginX = px(geometry.width, 64)
    const headlineSize = fontSizeFor(geometry.width, treatment.headline)
    const sublineSize = fontSizeFor(geometry.width, treatment.subline)
    const barWidth = px(geometry.width, treatment.barWidth)
    const barHeight = px(geometry.width, treatment.barHeight)
    const placement = treatment.centered
        ? `top:50%; transform:translateY(-50%); text-align:center;`
        : `bottom:${safeBottomMargin(geometry.height)}px;`
    const barMargin = treatment.centered ? 'margin:0 auto 20px;' : 'margin-bottom:18px;'
    const headline = beat.title
        ? `        <h2 id="${id}-headline" style="margin:0; color:${tokens.textPrimary}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.titleWeight}; font-size:${headlineSize}px; line-height:1.15;">${escapeHtml(beat.title)}</h2>\n`
        : ''
    const subline = beat.caption
        ? `        <p id="${id}-subline" style="margin:${beat.title ? treatment.sublineGap : 0}px 0 0; color:${tokens.textMuted}; font-family:${tokens.fontFamily}, sans-serif; font-weight:${tokens.bodyWeight}; font-size:${sublineSize}px; line-height:1.3;">${escapeHtml(beat.caption)}</p>\n`
        : ''
    return `      <div id="${id}" class="clip"
        data-start="${start}" data-duration="${duration}" data-track-index="3"
        style="position:absolute; left:${marginX}px; right:${marginX}px; ${placement}">
        <div id="${id}-bar" style="width:${barWidth}px; height:${barHeight}px; background:${tokens.primary}; border-radius:4px; ${barMargin}"></div>
${headline}${subline}      </div>`
}

/**
 * Timeline GSAP seekable: entrada suave dos textos (fade + slide no no interno,
 * nunca autoAlpha/visibility no .clip), zoom lento na midia quando pedido e
 * fade-out apenas no ultimo beat (transitionOut: fade do BeatPlan). No modo
 * still o fade-out e desligado — o quadro capturado fica no estado final.
 */
function timelineScript(beats, staged, geometry, narratives, { still }) {
    const lines = []
    const total = beats.length
    beats.forEach((beat, index) => {
        const start = seconds(beat.startMs)
        const duration = seconds(beat.durationMs)
        const id = `text-${beat.beatId}`
        const treatment = treatmentFor(narratives.get(beat.beatId))
        const barWidth = px(geometry.width, treatment.barWidth)
        const hasText = Boolean(beat.title || beat.caption)
        if (hasText) {
            lines.push(`  tl.fromTo("#${id}-bar", { opacity: 0, width: "0px" }, { opacity: 1, width: "${barWidth}px", duration: 0.35, ease: "power2.out" }, ${start});`)
            if (beat.title) {
                lines.push(`  tl.fromTo("#${id}-headline", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, ${start + 0.08});`)
            }
            if (beat.caption) {
                lines.push(`  tl.fromTo("#${id}-subline", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, ${start + 0.18});`)
            }
            if (index === total - 1 && !still) {
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
 * Retorna {totalSeconds, beats, geometry, stillAtSeconds} para o orquestrador;
 * stillAtSeconds e o instante com entradas concluidas usado pelo snapshot (F10).
 */
export function composeProject({ profile, tokens, root, workdir, still = false }) {
    const plan = profile.plan
    if (!plan || !plan.geometry || !plan.durationMs || !Array.isArray(plan.beats) || plan.beats.length === 0) {
        throw new Error('PROFILE_PLAN_INVALID: plano do perfil compilado ausente ou vazio')
    }
    const geometry = plan.geometry
    const beats = plan.beats
    const narratives = narrativeByBeat(profile)
    const totalSeconds = seconds(plan.durationMs)
    mkdirSync(workdir, { recursive: true })
    const staged = stageAssets(beats, root, workdir)

    const mediaClips = beats.map((beat) => mediaClipHtml(beat, staged, geometry, beat.motionIntent)).filter(Boolean)
    const sceneLayers = beats
        .map((beat) => sceneLayerHtml(beat, geometry, tokens, treatmentFor(narratives.get(beat.beatId))))
        .filter(Boolean)
    const textClips = beats
        .map((beat) => textClipHtml(beat, geometry, tokens, treatmentFor(narratives.get(beat.beatId))))
        .filter(Boolean)
    const header = headerHtml(tokens, geometry, totalSeconds)

    const html = `<!doctype html>
<html lang="pt-BR" data-resolution="${resolutionFor(geometry)}">
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
${sceneLayers.join('\n')}
${header}
${textClips.join('\n')}
    </div>
    <script>
${timelineScript(beats, staged, geometry, narratives, { still })}
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
    const stillAtSeconds = still ? Math.min(1.2, totalSeconds * 0.75) : null
    return { totalSeconds, beats: beats.length, geometry, stillAtSeconds }
}
