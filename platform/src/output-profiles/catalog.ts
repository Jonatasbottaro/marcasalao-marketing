import {
    DEFAULT_VIDEO_FPS,
    GEOMETRY_LANDSCAPE_16_9,
    GEOMETRY_PORTRAIT_4_5,
    GEOMETRY_SQUARE_1080,
    GEOMETRY_VERTICAL_9_16,
} from './geometry.js'
import { CATALOG_VERSION } from './types.js'
import type { ImageOutputProfile, OutputProfile, OutputProfileFilter, VideoOutputProfile } from './types.js'

/**
 * Catalogo de perfis de saida sociais: rede -> publicacao -> midia -> perfil tecnico.
 *
 * Os doze perfis abaixo sao a unica fonte de formatos da plataforma: CLI, teste
 * e exemplo leem daqui, nunca um segundo dicionario local. Geometria e fps sao
 * **presets internos**; as exigencias das redes vem do registro de regras e so
 * viram restricao quando o contexto declarado bate com a fonte (estado
 * `applies`). Estar no catalogo nao significa existir exportador pronto.
 *
 * Ver docs/planejamento/R001-formatos-sociais.md (secoes 3 e 5).
 */

const IMAGE_PROFILES: readonly ImageOutputProfile[] = [
    {
        id: 'instagram-feed-image-square',
        name: 'Feed de imagem quadrada do Instagram',
        revision: 2,
        network: 'instagram',
        publication: 'feed',
        mediaKind: 'image',
        geometry: GEOMETRY_SQUARE_1080,
        defaults: ['D-LOCAL-01'],
        rules: [
            { ruleId: 'R-IG-01', state: 'applies' },
            { ruleId: 'R-IG-06', state: 'applies' },
            { ruleId: 'R-IG-10', state: 'informational' },
        ],
        pendingIds: [],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: ['docs/planejamento/R001-formatos-sociais.md#1.3'],
    },
    {
        id: 'instagram-feed-image-portrait',
        name: 'Feed de imagem retrato do Instagram',
        revision: 2,
        network: 'instagram',
        publication: 'feed',
        mediaKind: 'image',
        geometry: GEOMETRY_PORTRAIT_4_5,
        defaults: ['D-LOCAL-02'],
        rules: [
            { ruleId: 'R-IG-01', state: 'applies' },
            { ruleId: 'R-IG-06', state: 'applies' },
            { ruleId: 'R-IG-10', state: 'informational' },
        ],
        pendingIds: [],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: ['docs/planejamento/R001-formatos-sociais.md#1.3'],
    },
    {
        id: 'instagram-stories-image',
        name: 'Stories de imagem do Instagram',
        revision: 2,
        network: 'instagram',
        publication: 'stories',
        mediaKind: 'image',
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03'],
        rules: [
            { ruleId: 'R-IG-07', state: 'applies' },
            { ruleId: 'R-IG-04', state: 'informational' },
            { ruleId: 'R-IG-05', state: 'informational' },
        ],
        pendingIds: [],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: ['docs/planejamento/R001-formatos-sociais.md#1.3'],
    },
    {
        id: 'facebook-feed-image-square',
        name: 'Feed de imagem quadrada do Facebook',
        revision: 2,
        network: 'facebook',
        publication: 'feed',
        mediaKind: 'image',
        geometry: GEOMETRY_SQUARE_1080,
        defaults: ['D-LOCAL-01'],
        rules: [{ ruleId: 'R-FB-01', state: 'applies' }],
        pendingIds: ['P-FB-01'],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: ['docs/planejamento/R001-formatos-sociais.md#1.3'],
    },
    {
        id: 'facebook-feed-image-portrait',
        name: 'Feed de imagem retrato do Facebook',
        revision: 2,
        network: 'facebook',
        publication: 'feed',
        mediaKind: 'image',
        geometry: GEOMETRY_PORTRAIT_4_5,
        defaults: ['D-LOCAL-02'],
        rules: [{ ruleId: 'R-FB-01', state: 'applies' }],
        pendingIds: ['P-FB-01'],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: ['docs/planejamento/R001-formatos-sociais.md#1.3'],
    },
    {
        id: 'facebook-stories-image',
        name: 'Stories de imagem do Facebook',
        revision: 2,
        network: 'facebook',
        publication: 'stories',
        mediaKind: 'image',
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03'],
        rules: [{ ruleId: 'R-FB-02', state: 'applies' }],
        pendingIds: ['P-FB-01'],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: ['docs/planejamento/R001-formatos-sociais.md#1.3'],
    },
]

const VIDEO_PROFILES: readonly VideoOutputProfile[] = [
    {
        id: 'instagram-stories-video',
        name: 'Stories de vídeo do Instagram',
        revision: 2,
        network: 'instagram',
        publication: 'stories',
        mediaKind: 'video',
        fps: DEFAULT_VIDEO_FPS,
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03', 'D-LOCAL-05'],
        rules: [
            { ruleId: 'R-IG-08', state: 'applies' },
            { ruleId: 'R-IG-04', state: 'informational' },
            { ruleId: 'R-IG-05', state: 'informational' },
        ],
        pendingIds: [],
        noteIds: [],
        exportState: 'canvas-template-mapped',
        exportEvidence: [
            'templates/story_reel_vertical/index.html:5',
            'docs/planejamento/R001-formatos-sociais.md#1.3',
        ],
    },
    {
        id: 'instagram-reels-video',
        name: 'Reels do Instagram',
        revision: 2,
        network: 'instagram',
        publication: 'reels',
        mediaKind: 'video',
        fps: DEFAULT_VIDEO_FPS,
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03', 'D-LOCAL-05'],
        rules: [{ ruleId: 'R-IG-09', state: 'applies' }],
        pendingIds: [],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: [
            'templates/story_reel_vertical/index.html:5',
            'tools/build_video.py:30',
        ],
    },
    {
        id: 'facebook-stories-video',
        name: 'Stories de vídeo do Facebook',
        revision: 2,
        network: 'facebook',
        publication: 'stories',
        mediaKind: 'video',
        fps: DEFAULT_VIDEO_FPS,
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03', 'D-LOCAL-05'],
        rules: [
            { ruleId: 'R-FB-03', state: 'applies' },
            { ruleId: 'R-FB-04', state: 'applies' },
            { ruleId: 'R-FB-05', state: 'applies' },
        ],
        pendingIds: ['P-FB-03'],
        noteIds: [],
        exportState: 'canvas-template-mapped',
        exportEvidence: [
            'templates/story_reel_vertical/index.html:5',
            'docs/planejamento/R001-formatos-sociais.md#1.3',
        ],
    },
    {
        id: 'facebook-reels-video',
        name: 'Reels do Facebook',
        revision: 2,
        network: 'facebook',
        publication: 'reels',
        mediaKind: 'video',
        fps: DEFAULT_VIDEO_FPS,
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03', 'D-LOCAL-05'],
        rules: [
            { ruleId: 'R-FB-06', state: 'applies' },
            { ruleId: 'R-FB-07', state: 'applies' },
            { ruleId: 'R-FB-08', state: 'applies' },
            { ruleId: 'R-FB-09', state: 'applies' },
        ],
        pendingIds: ['P-FB-03'],
        noteIds: [],
        exportState: 'tool-export-observed',
        exportEvidence: [
            'templates/story_reel_vertical/index.html:5',
            'tools/build_video.py:30',
        ],
    },
    {
        id: 'youtube-video-horizontal',
        name: 'Vídeo horizontal do YouTube',
        revision: 2,
        network: 'youtube',
        publication: 'video',
        mediaKind: 'video',
        fps: DEFAULT_VIDEO_FPS,
        geometry: GEOMETRY_LANDSCAPE_16_9,
        defaults: ['D-LOCAL-04', 'D-LOCAL-05'],
        rules: [
            { ruleId: 'R-YT-04', state: 'applies' },
            { ruleId: 'R-YT-05', state: 'applies' },
            { ruleId: 'R-YT-06', state: 'applies' },
            { ruleId: 'R-YT-07', state: 'applies' },
        ],
        pendingIds: [],
        noteIds: ['PN-YT-02'],
        exportState: 'canvas-template-mapped',
        exportEvidence: ['templates/youtube_horizontal/index.html:5'],
        plannedContainer: 'mp4',
        plannedContainerEvidence: 'R-YT-04',
    },
    {
        id: 'youtube-shorts',
        name: 'Shorts do YouTube',
        revision: 3,
        network: 'youtube',
        publication: 'shorts',
        mediaKind: 'video',
        fps: DEFAULT_VIDEO_FPS,
        geometry: GEOMETRY_VERTICAL_9_16,
        defaults: ['D-LOCAL-03', 'D-LOCAL-05'],
        rules: [
            { ruleId: 'R-YT-01', state: 'applies' },
            { ruleId: 'R-YT-02', state: 'applies' },
        ],
        pendingIds: ['P-YT-03'],
        noteIds: ['PN-YT-01'],
        exportState: 'canvas-template-mapped',
        exportEvidence: ['templates/story_reel_vertical/index.html:5'],
    },
]

/** Ordem estavel: imagem por rede e destino, depois video. Nao depende de Map. */
export const OUTPUT_PROFILES: readonly OutputProfile[] = [...IMAGE_PROFILES, ...VIDEO_PROFILES]

export { CATALOG_VERSION }

export function listOutputProfiles(filter?: OutputProfileFilter): readonly OutputProfile[] {
    if (filter === undefined) return OUTPUT_PROFILES
    return OUTPUT_PROFILES.filter(
        (profile) =>
            (filter.network === undefined || profile.network === filter.network) &&
            (filter.publication === undefined || profile.publication === filter.publication) &&
            (filter.mediaKind === undefined || profile.mediaKind === filter.mediaKind),
    )
}

export function findOutputProfile(profileId: string): OutputProfile | null {
    return OUTPUT_PROFILES.find((profile) => profile.id === profileId) ?? null
}
