/**
 * Fonte compartilhada de exportabilidade local por modulo do Studio.
 *
 * O catalogo declara formatos e regras de rede; este modulo declara o que o
 * adaptador local de prova efetivamente renderiza hoje, por modulo (video,
 * carrossel, motion). CLI, API do Studio, Planejamento, biblioteca de midia e
 * seletores do painel consomem esta unica fonte — nunca um segundo dicionario
 * local de formatos.
 *
 * Estar no catalogo e na allowlist do projeto nao basta: um perfil conhecido
 * pode ter render local indisponivel (geometria ou fps fora do adaptador, ou
 * motion restrito ao vertical nesta rodada). O motivo fica explicito para a
 * interface distinguir "desconhecido", "fora da allowlist" e "sem render local".
 *
 * Camada pura: sem I/O, sem rede, sem relogio, sem marca.
 */

import type { OutputProfile } from './types.js'

/** Modulos locais do Studio que exportam entregas. */
export const LOCAL_EXPORT_MODULES = ['video', 'carousel', 'motion'] as const
export type LocalExportModule = (typeof LOCAL_EXPORT_MODULES)[number]

/** Motivos estaveis de render local indisponivel para um perfil conhecido. */
export type LocalExportUnsupportedReason =
    | 'MEDIA_KIND_MISMATCH'
    | 'GEOMETRY_UNSUPPORTED'
    | 'FPS_UNSUPPORTED'
    | 'MOTION_VERTICAL_ONLY'

export interface LocalExportSupport {
    readonly supported: boolean
    readonly reason: LocalExportUnsupportedReason | null
}

export interface LocalExportCapabilities {
    readonly video: LocalExportSupport
    readonly carousel: LocalExportSupport
    readonly motion: LocalExportSupport
}

/** Geometrias de video suportadas pelo adaptador local (vertical e horizontal). */
export const LOCAL_VIDEO_GEOMETRIES: readonly { readonly width: number; readonly height: number }[] = [
    { width: 1080, height: 1920 },
    { width: 1920, height: 1080 },
]

/** Geometrias de carrossel suportadas pelo layout local (quadrado e retrato 4:5). */
export const LOCAL_CAROUSEL_GEOMETRIES: readonly { readonly width: number; readonly height: number }[] = [
    { width: 1080, height: 1080 },
    { width: 1080, height: 1350 },
]

/** Motion permanece enquadrado no vertical 9:16 nesta rodada. */
export const LOCAL_MOTION_GEOMETRIES: readonly { readonly width: number; readonly height: number }[] = [
    { width: 1080, height: 1920 },
]

/** FPS de video suportado pelo adaptador local. */
export const LOCAL_VIDEO_FPS = 30

function matchesGeometry(
    profile: OutputProfile,
    geometries: readonly { readonly width: number; readonly height: number }[],
): boolean {
    return geometries.some((g) => g.width === profile.geometry.width && g.height === profile.geometry.height)
}

function videoSupport(profile: OutputProfile): LocalExportSupport {
    if (profile.mediaKind !== 'video') return { supported: false, reason: 'MEDIA_KIND_MISMATCH' }
    if (profile.fps !== LOCAL_VIDEO_FPS) return { supported: false, reason: 'FPS_UNSUPPORTED' }
    if (!matchesGeometry(profile, LOCAL_VIDEO_GEOMETRIES)) return { supported: false, reason: 'GEOMETRY_UNSUPPORTED' }
    return { supported: true, reason: null }
}

function carouselSupport(profile: OutputProfile): LocalExportSupport {
    if (profile.mediaKind !== 'image') return { supported: false, reason: 'MEDIA_KIND_MISMATCH' }
    if (!matchesGeometry(profile, LOCAL_CAROUSEL_GEOMETRIES)) return { supported: false, reason: 'GEOMETRY_UNSUPPORTED' }
    return { supported: true, reason: null }
}

function motionSupport(profile: OutputProfile): LocalExportSupport {
    const video = videoSupport(profile)
    if (!video.supported) return video
    if (!matchesGeometry(profile, LOCAL_MOTION_GEOMETRIES)) return { supported: false, reason: 'MOTION_VERTICAL_ONLY' }
    return { supported: true, reason: null }
}

/** Capacidades de exportacao local de um perfil do catalogo, por modulo. */
export function localExportCapabilities(profile: OutputProfile): LocalExportCapabilities {
    return {
        video: videoSupport(profile),
        carousel: carouselSupport(profile),
        motion: motionSupport(profile),
    }
}

/** Rotulos em portugues dos motivos, para seletores e diagnosticos. */
export const LOCAL_EXPORT_REASON_LABELS: Record<LocalExportUnsupportedReason, string> = {
    MEDIA_KIND_MISMATCH: 'tipo de midia diferente do modulo',
    GEOMETRY_UNSUPPORTED: 'geometria ainda nao suportada pelo render local',
    FPS_UNSUPPORTED: 'fps fora do suportado pelo render local (30)',
    MOTION_VERTICAL_ONLY: 'Motion disponivel apenas em 9:16 nesta rodada; o contorno usa coordenadas relativas ao quadro final',
}