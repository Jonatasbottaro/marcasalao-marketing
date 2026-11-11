import type { CatalogRule, PolicyNote } from './types.js'

/**
 * Registro de regras, padroes internos, pendencias de fonte e notas de politica.
 *
 * Cada entrada declara a propria classe por `kind` (uniao discriminada) e traz
 * a procedencia: fonte oficial para regra, caminho interno do repositorio para
 * padrao interno, **ausencia** de valor para pendencia. Regra de uma rede nunca
 * migra para outra, e numero nao certificado permanece fora do catalogo com ID
 * nominal em vez de virar 0, Infinity ou aproximacao.
 *
 * As datas de consulta e as citacoes literais vem da leitura documentada em
 * docs/planejamento/R001-formatos-sociais.md (secoes 2, 2.1 e 2.2). Revalidar a
 * fonte antes de promover qualquer pendencia a limite rigido.
 *
 * Os campos `quote` e `title` reproduzem o texto da pagina como ele apareceu na
 * consulta (inclusive acentos); `statement` e a formulacao propria do catalogo.
 * Quando a fonte e uma tabela de especificacoes, a citacao reproduz as celulas
 * na ordem impressa, separadas por " · " -- nada de reescrever o numero.
 *
 * Na R001-05 as pendencias certificadas viraram regras oficiais (R-IG-06 a
 * R-IG-10, R-FB-01 a R-FB-09, R-YT-05 a R-YT-07 e a nota PN-YT-02) e sairam do
 * registro de pendencias. O que continua sem numero oficial segue como `P-*`.
 */

export const CATALOG_RULES: readonly CatalogRule[] = [
    {
        id: 'R-IG-01',
        network: 'instagram',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Na publicação de imagem por API do Instagram, JPEG é o único formato aceito.',
        value: { kind: 'allowed-formats', formats: ['jpeg'] },
        source: {
            url: 'https://developers.facebook.com/docs/instagram-platform/content-publishing/',
            title: 'Publicação de conteúdo – Instagram Platform',
            accessedOn: '2026-11-07T01:59Z',
            quote: 'O único formato de imagem compatível é o JPEG. Não há compatibilidade com formatos derivados de JPEG, como MPO e JPS.',
            note: 'A página se declara traduzida automaticamente; a citação foi conferida na versão exibida no navegador.',
        },
    },
    {
        id: 'R-IG-04',
        network: 'instagram',
        kind: 'requirement',
        contexts: ['in-app'],
        statement: 'No compartilhamento de Stories pelo app, o ativo de fundo exige dimensões mínimas 720×1280.',
        value: { kind: 'min-dimensions', width: 720, height: 1280 },
        source: {
            url: 'https://developers.facebook.com/documentation/instagram-platform/sharing-to-stories',
            title: 'Compartilhamento no Stories – Instagram Platform',
            accessedOn: '2026-11-07T01:59Z',
            quote: 'formato compatível (JPG, PNG). Dimensões mínimas 720 x 1.280.',
            note: 'Fluxo pelo app (intent Android / UIImage iOS), não publicação por API; a página se declara traduzida por IA.',
        },
    },
    {
        id: 'R-IG-05',
        network: 'instagram',
        kind: 'recommendation',
        contexts: ['in-app'],
        statement: 'Para o mesmo compartilhamento de Stories no app, as proporções recomendadas são 9:16 ou 9:18.',
        value: { kind: 'aspect-ratios', ratios: ['9:16', '9:18'] },
        source: {
            url: 'https://developers.facebook.com/documentation/instagram-platform/sharing-to-stories',
            title: 'Compartilhamento no Stories – Instagram Platform',
            accessedOn: '2026-11-07T01:59Z',
            quote: 'As proporções de imagem recomendadas são 9:16 ou 9:18.',
            note: 'Recomendação de contexto app; não é proporção exclusiva nem exigência de API.',
        },
    },
    {
        id: 'R-IG-06',
        network: 'instagram',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Imagem publicada por API do Instagram: proporção dentro da faixa de 4:5 a 1.91:1, largura mínima 320 pixels e máxima 1440 pixels; a altura varia conforme a largura e a proporção.',
        source: {
            url: 'https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media?locale=en_US',
            title: 'IG User Media | Meta for Developers',
            accessedOn: '2026-11-07T19:11Z',
            quote: 'Aspect ratio: Must be within a 4:5 to 1.91:1 range · Minimum width: 320 (will be scaled up to the minimum if necessary) · Maximum width: 1440 (will be scaled down to the maximum if necessary) · Height: Varies, depending on width and aspect ratio',
            note: 'Bloco "Image Specifications" (referência v27.0). A faixa é de proporção e de largura; nenhum par de pixels por proporção (1:1 ou 4:5) é declarado, e o peso máximo de imagem fica na mesma página, sem expressão em RuleValue. Os presets 1080×1080 e 1080×1350 do catálogo são pontos internos da faixa, não exigência da rede.',
        },
    },
    {
        id: 'R-IG-07',
        network: 'instagram',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Imagem de Stories publicada por API do Instagram: formato JPEG, com peso máximo de 8 MB e proporção recomendada 9:16.',
        value: { kind: 'allowed-formats', formats: ['jpeg'] },
        source: {
            url: 'https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media?locale=en_US',
            title: 'IG User Media | Meta for Developers',
            accessedOn: '2026-11-07T19:11Z',
            quote: 'Format: JPEG · File size: 8 MB maximum. · Aspect ratio: We recommended 9:16 to avoid cropping or blank space',
            note: 'Bloco "Story Image Specifications". Resolve a pergunta que a R001-02 deixou como pendência: a exigência de JPEG alcança Stories por API, declarada por tipo nesta página e corroborada no nível do documento por Content Publishing ("JPEG is the only image format supported. Extended JPEG formats such as MPO and JPS are not supported."). O "JPG, PNG" de Sharing to Stories é o fluxo do app por SDK, não publicação por API.',
        },
    },
    {
        id: 'R-IG-08',
        network: 'instagram',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Vídeo de Stories publicado por API do Instagram: duração máxima de 60 segundos e mínima de 3 segundos, peso máximo de 100 MB e contêiner MOV ou MP4.',
        value: { kind: 'max-duration-seconds', seconds: 60 },
        source: {
            url: 'https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media?locale=en_US',
            title: 'IG User Media | Meta for Developers',
            accessedOn: '2026-11-07T19:11Z',
            quote: 'Duration: 60 seconds maximum, 3 seconds minimum · File size: 100MB maximum · Container: MOV or MP4 (MPEG-4 Part 14), no edit lists, moov atom at the front of the file.',
            note: 'Bloco "Story Video Specifications". Só o teto de 60 segundos vira value: RuleValue não expressa duração mínima, peso, lista aberta de contêineres nem faixa de proporção, e inventá-los produziria erro de plano que a fonte não sustenta. A mesma página declara ao lado: "Maximum columns (horizontal pixels): 1920", "Required aspect ratio is between 0.1:1 and 10:1 but we recommend 9:16 to avoid cropping or blank space", "Audio bitrate: 128kbps" e "Stories expire after 24 hours." -- fatos lidos e certificados, sem forma no contrato, registrados aqui para a releitura não os tratar como desconhecidos.',
        },
    },
    {
        id: 'R-IG-09',
        network: 'instagram',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Reel publicado por API do Instagram: duração máxima de 15 minutos (900 segundos) e mínima de 3 segundos, peso máximo de 300 MB, bitrate VBR até 25 Mbps e contêiner MOV ou MP4.',
        value: { kind: 'max-duration-seconds', seconds: 900 },
        source: {
            url: 'https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media?locale=en_US',
            title: 'IG User Media | Meta for Developers',
            accessedOn: '2026-11-07T19:11Z',
            quote: 'Duration: 15 mins maximum, 3 seconds minimum · File size: 300MB maximum · Video bitrate: VBR, 25Mbps maximum · Container: MOV or MP4 (MPEG-4 Part 14), no edit lists, moov atom at the front of the file.',
            note: 'Bloco "Reel Specifications". A armadilha descartada: Reels Publishing API traz "Duration: 3 to 90 seconds.", mas a própria página delimita "This document explains how to publish a reel on a Facebook Page" -- é Facebook, não Instagram. Não copiar número entre redes.',
        },
    },
    {
        id: 'R-IG-10',
        network: 'instagram',
        kind: 'recommendation',
        contexts: ['in-app'],
        statement: 'No app, o Instagram orienta foto com proporção entre 1.91:1 e 3:4, isto é, largura de 1080 pixels e altura entre 566 e 1440 pixels.',
        source: {
            url: 'https://help.instagram.com/1631821640426723/?locale=en_US',
            title: 'Image resolution of photos you share on Instagram | Instagram Help Center',
            accessedOn: '2026-11-07T19:11Z',
            quote: 'aspect ratio is between 1.91:1 and 3:4 (a width of 1080 pixels with a height between 566 and 1440 pixels)',
            note: 'Regra de app, registrada como recomendação e sempre informational nos perfis: o caminho exportado pelo núcleo nunca é o app. O extremo do app (3:4, mais alto que 4:5) diverge do extremo declarado pela API (R-IG-06): são duas regras justamente para não apagar a divergência. Acesso: a URL sem locale responde 302 para login; o texto foi lido no navegador em locale en_US.',
        },
    },
    {
        id: 'R-FB-01',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Foto publicada por API numa Página do Facebook: arquivos aceitos .jpeg, .bmp, .png, .gif e .tiff, com peso máximo de 10 MB; para .png a própria página recomenda não passar de 1 MB.',
        value: { kind: 'allowed-formats', formats: ['jpeg', 'bmp', 'png', 'gif', 'tiff'] },
        source: {
            url: 'https://developers.facebook.com/docs/graph-api/reference/page/photos/',
            title: 'Graph API Reference v27.0: Page Photos',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'File type: .jpeg, .bmp, .png, .gif, .tiff · File size: Files can not exceed 10MB. For .png files, we recommend not exceeding 1MB or the image may appear pixelated.',
            note: 'Bloco "Photo Specifications". Esta lista refuta por fonte própria a hipótese de que a regra JPEG-only do Instagram se estende ao Facebook. A página não declara dimensão mínima, máxima nem proporção para foto de feed: continua pendência P-FB-01.',
        },
    },
    {
        id: 'R-FB-02',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Foto de Story publicada por API no Facebook: formatos .jpeg, .bmp, .png, .gif e .tiff, com peso máximo de 10 MB.',
        value: { kind: 'allowed-formats', formats: ['jpeg', 'bmp', 'png', 'gif', 'tiff'] },
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/page-stories-api',
            title: 'Facebook Stories API from Meta',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'File type: .jpeg, .bmp, .png, .gif, .tiff · Files can not exceed 10MB.',
            note: 'Bloco "Photo specifications" (página atualizada em 30 de julho de 2026). O peso de 10 MB não vira value: RuleValue não expressa bytes de arquivo.',
        },
    },
    {
        id: 'R-FB-03',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Vídeo de Story publicado por API no Facebook: não pode exceder 60 segundos.',
        value: { kind: 'max-duration-seconds', seconds: 60 },
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/page-stories-api',
            title: 'Facebook Stories API from Meta',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'A video story can not exceed 60 seconds',
            note: 'Contradição interna da fonte, registrada em vez de apagada: a tabela "Video specifications" imprime "Duration: 3 to 90 seconds." e a seção "Limitations" imprime "A video story can not exceed 60 seconds", ambas na mesma página. Promovemos o teto mais estrito, porque nenhuma das duas autoriza um vídeo-story de 90 segundos. A variante pt-BR da página é autodeclarada como tradução por IA e traduz "3 to 90 seconds" como "3 a 9 segundos" -- defeito real de tradução; por isso toda citação desta etapa saiu da locale en. O mínimo de 3 segundos fica no enunciado da fonte, sem value.',
        },
    },
    {
        id: 'R-FB-04',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Story de vídeo publicado por API no Facebook: resolução mínima 540 x 960 pixels, com 1080 x 1920 recomendados.',
        value: { kind: 'min-dimensions', width: 540, height: 960 },
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/page-stories-api',
            title: 'Facebook Stories API from Meta',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'Resolution: 1080 x 1920 pixels (recommended). Minimum is 540 x 960 pixels · Aspect Ratio: 9 x 16',
            note: 'Bloco "Video specifications". O preset 1080×1920 do catálogo cumpre o mínimo, por isso esta regra não gera aviso quando a geometria do plano é a do próprio preset.',
        },
    },
    {
        id: 'R-FB-05',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Frame rate do vídeo de Story publicado por API no Facebook: 24 a 60 quadros por segundo.',
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/page-stories-api',
            title: 'Facebook Stories API from Meta',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'Frame Rate: 24 to 60 frames per second',
            note: 'Faixa, não valor único: fixar `fps: 30` como exigência da rede aprovaria só o preset e reprovaria 25 ou 60 fps, que a página aceita. Sem value, o relatório diz que o plano não traz o dado.',
        },
    },
    {
        id: 'R-FB-06',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Reel publicado por API numa Página do Facebook: duração de 3 a 90 segundos; publicado como Story, o teto cai para 60 segundos.',
        value: { kind: 'max-duration-seconds', seconds: 90 },
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/guides/reels-publishing',
            title: 'Reels Publishing API',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'Duration: 3 to 90 seconds. A reel published as a story on a Facebook Page can not exceed 60 seconds.',
            note: 'Escopo da página: "You can only publish Reels to Facebook Pages". O valor promovido é o teto do caminho direto (90 s); a frase dos 60 s pertence à publicação como Story, afirmada na mesma página. Não confundir com R-IG-09 (Reel do Instagram, 15 minutos).',
        },
    },
    {
        id: 'R-FB-07',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Reel publicado por API numa Página do Facebook: resolução mínima 540 x 960 pixels, com 1080 x 1920 recomendados.',
        value: { kind: 'min-dimensions', width: 540, height: 960 },
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/guides/reels-publishing',
            title: 'Reels Publishing API',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'Resolution: 1080 x 1920 pixels (recommended). Minimum is 540 x 960 pixels',
            note: 'Bloco "Video Specifications", junto de "Chroma subsampling 4:2:0", "Closed GOP (2-5 seconds)", "Compression – H.264, H.265 (VP9, AV1 are also supported)", "Fixed frame rate" e "Progressive scan" -- none deles tem expressão em RuleValue e nenhum vira erro de plano. O frame rate de Reel também é certificado como faixa, na mesma página: "Reels frame rate must be between 24 and 60 frames per second." -- faixa não é `RuleValue.fps`, que é singular; por isso o enunciado vive aqui e em §2.2.3, não como regra com valor.',
        },
    },
    {
        id: 'R-FB-08',
        network: 'facebook',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Proporção declarada para Reel de Página: 9 x 16; a referência de vídeo de Páginas aceita 9x16 e 16x9, então não há lista fechada de proporções certificada para este perfil.',
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/guides/reels-publishing',
            title: 'Reels Publishing API',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'Aspect Ratio: 9 x 16',
            note: 'Sem value: a mesma família de páginas imprime duas relações diferentes ("Aspect Ratio: 9 x 16" aqui e "Aspect Ratio: 9x16, 16x9" em https://developers.facebook.com/documentation/video-api/reference, que é o objeto de vídeo de Página, não o Reel). Reduzir isso a uma lista fechada de proporções afirmaria exclusividade que a fonte não declara.',
        },
    },
    {
        id: 'R-FB-09',
        network: 'facebook',
        kind: 'recommendation',
        contexts: ['api-publishing'],
        statement: 'Contêiner recomendado para Reel publicado por API numa Página do Facebook: .mp4.',
        value: { kind: 'container', container: 'mp4' },
        source: {
            url: 'https://developers.facebook.com/documentation/video-api/guides/reels-publishing',
            title: 'Reels Publishing API',
            accessedOn: '2026-11-07T19:19Z',
            quote: 'File Type: .mp4 (recommended)',
            note: 'A própria fonte marca como recomendação, então descumprimento gera aviso, nunca erro. A página não declara peso máximo de arquivo de vídeo: pendência P-FB-03.',
        },
    },
    {
        id: 'R-YT-01',
        network: 'youtube',
        kind: 'requirement',
        contexts: ['in-app', 'studio-upload'],
        statement: 'Shorts tem até três minutos de duração.',
        value: { kind: 'max-duration-seconds', seconds: 180 },
        source: {
            url: 'https://support.google.com/youtube/answer/15424877?hl=pt-BR',
            title: 'Como criar Shorts com até três minutos – YouTube Help',
            accessedOn: '2026-11-07T18:21Z',
            quote: 'Você pode enviar Shorts de até três minutos pelo app YouTube e pelo YouTube Studio.',
            note: 'A frase cita os dois caminhos, então o escopo da regra é in-app e studio-upload. A qualificação como Short é automática por proporção e duração; não há mudança nas limitações de Shorts com menos de um minuto.',
        },
    },
    {
        id: 'R-YT-02',
        network: 'youtube',
        kind: 'requirement',
        contexts: ['in-app', 'studio-upload'],
        statement: 'Para ser classificado como Short, o vídeo precisa ter proporção quadrada ou vertical.',
        value: { kind: 'orientation-any-of', orientations: ['square', 'portrait'] },
        source: {
            url: 'https://support.google.com/youtube/answer/12779649?hl=pt-BR',
            title: 'Enviar vídeos ao YouTube Shorts – YouTube Help',
            accessedOn: '2026-11-07T18:21Z',
            quote: 'de até 3 minutos e com uma proporção quadrada ou vertical',
            note: 'Condição de orientação, não lista fechada de proporções; a página não declara resolução mínima. A mesma resposta existe em duas variantes de plataforma, e as duas repetem a condição: "Faça login no YouTube Studio" (Computador) e "Selecione um conteúdo com uma proporção quadrada ou vertical" (app no Smartphone e tablet Android). O escopo cobre portanto studio-upload e in-app.',
        },
    },
    {
        id: 'R-YT-04',
        network: 'youtube',
        kind: 'recommendation',
        contexts: ['studio-upload'],
        statement: 'Configurações recomendadas de codificação: contêiner MP4, vídeo H.264, sem entrelaçamento e no mesmo frame rate da gravação; 16:9 é a proporção padrão em desktop.',
        value: { kind: 'container', container: 'mp4' },
        source: {
            url: 'https://support.google.com/youtube/answer/1722171?hl=pt-BR',
            title: 'Configurações recomendadas de codificação de envio – YouTube Help',
            accessedOn: '2026-11-07T02:00Z',
            quote: 'O conteúdo precisa ser codificado e enviado no mesmo frame rate em que foi gravado',
            note: 'Seção autodeclarada disponível apenas para parceiros que usam o Gerenciador de conteúdo do YouTube Studio; é recomendação, não limite rígido, e não menciona Shorts.',
        },
    },
    {
        id: 'R-YT-05',
        network: 'youtube',
        kind: 'requirement',
        contexts: ['in-app', 'studio-upload'],
        statement: 'Envio de vídeo ao YouTube: por padrão até 15 minutos de duração; conta verificada envia vídeos mais longos.',
        source: {
            url: 'https://support.google.com/youtube/answer/71673?hl=en',
            title: 'Upload videos longer than 15 minutes - Computer - YouTube Help',
            accessedOn: '2026-11-07T19:24Z',
            quote: 'By default, you can upload videos that are up to 15 minutes long. Verified accounts can upload videos longer than 15 minutes.',
            note: 'As abas Computer e Android da mesma resposta repetem os números, então o escopo certificado é studio-upload e in-app. Não vira value: 15 minutos é o padrão de conta não verificada, e um `max-duration-seconds: 900` reprovaria um vídeo de conta verificada que a própria página permite.',
        },
    },
    {
        id: 'R-YT-06',
        network: 'youtube',
        kind: 'requirement',
        contexts: ['in-app', 'studio-upload'],
        statement: 'Teto do arquivo enviado ao YouTube: 256 GB ou 12 horas de duração, o que vier primeiro.',
        source: {
            url: 'https://support.google.com/youtube/answer/71673?hl=en',
            title: 'Upload videos longer than 15 minutes - Computer - YouTube Help',
            accessedOn: '2026-11-07T19:24Z',
            quote: 'The maximum file size you can upload is 256 GB or 12 hours, whichever is less.',
            note: 'A mesma resposta pede navegador atualizado para enviar arquivos acima de 20 GB. Sem value: o teto é um mínimo entre bytes e duração, e nenhum dos dois tem expressão em RuleValue -- um número inventado diria "passou" sem verificar nada.',
        },
    },
    {
        id: 'R-YT-07',
        network: 'youtube',
        kind: 'requirement',
        contexts: ['api-publishing'],
        statement: 'Upload pela YouTube Data API v3 (videos.insert): tamanho máximo de arquivo de 256 GB e tipos MIME aceitos video/* e application/octet-stream.',
        source: {
            url: 'https://developers.google.com/youtube/data/reference/rest/v3/videos/insert?hl=en',
            title: 'YouTube Data API: Videos.insert (REST reference)',
            accessedOn: '2026-11-07T19:24Z',
            quote: 'Maximum file size: 256GB. Accepted Media MIME types: video/*, application/octet-stream',
            note: 'O caminho curto /youtube/v3/docs/videos/insert redireciona para esta referência; a consulta foi feita na URL final, em hl=en, porque a variante pt-BR é autodeclarada como tradução automática. Cota diária não é regra do núcleo: veja a nota PN-YT-02.',
        },
    },
    {
        id: 'D-LOCAL-01',
        network: null,
        kind: 'internal-default',
        statement: 'Preset interno de imagem quadrada 1080×1080 (1:1).',
        value: { kind: 'geometry', width: 1080, height: 1080, aspectRatio: '1:1' },
        evidence: 'platform/examples/compositions/fixture-project-pilot.composition.json:9-10',
    },
    {
        id: 'D-LOCAL-02',
        network: null,
        kind: 'internal-default',
        statement: 'Preset interno de imagem retrato 1080×1350 (4:5).',
        value: { kind: 'geometry', width: 1080, height: 1350, aspectRatio: '4:5' },
        evidence: 'docs/planejamento/R001-formatos-sociais.md#1.2',
    },
    {
        id: 'D-LOCAL-03',
        network: null,
        kind: 'internal-default',
        statement: 'Preset interno de vídeo vertical 1080×1920 (9:16).',
        value: { kind: 'geometry', width: 1080, height: 1920, aspectRatio: '9:16' },
        evidence: 'templates/story_reel_vertical/index.html:5',
    },
    {
        id: 'D-LOCAL-04',
        network: null,
        kind: 'internal-default',
        statement: 'Preset interno de vídeo horizontal 1920×1080 (16:9).',
        value: { kind: 'geometry', width: 1920, height: 1080, aspectRatio: '16:9' },
        evidence: 'templates/youtube_horizontal/index.html:5',
    },
    {
        id: 'D-LOCAL-05',
        network: null,
        kind: 'internal-default',
        statement: 'Frame rate preset interno dos perfis de vídeo: 30 fps.',
        value: { kind: 'fps', fps: 30 },
        evidence: 'docs/planejamento/R001-formatos-sociais.md#1.2',
    },
    {
        id: 'P-FB-01',
        network: 'facebook',
        kind: 'pending-source',
        context: null,
        statement: 'Dimensões e proporção de foto de feed e de Story de imagem do Facebook: as páginas lidas listam formatos e peso, mas não afirmam mínimo, máximo nem proporção por destino; o número continua sem fonte certificada.',
    },
    {
        id: 'P-FB-03',
        network: 'facebook',
        kind: 'pending-source',
        context: 'api-publishing',
        statement: 'Peso máximo de arquivo de vídeo publicado por API no Facebook (Story e Reel de Página): as especificações de "Video specifications" não declaram limite de bytes.',
    },
    {
        id: 'P-YT-03',
        network: 'youtube',
        kind: 'pending-source',
        context: null,
        statement: 'Contêiner e peso máximos específicos de Short: a página de Shorts certifica duração e proporção, e a lista geral de contêineres aceitos pelo YouTube não é própria de Short nem declara peso.',
    },
    {
        id: 'P-HELP-01',
        network: null,
        kind: 'pending-source',
        context: 'in-app',
        statement: 'Central de ajuda do app no facebook.com/help: landing genérica, sem regra numérica lida; regra de app não é exigência de exportação do núcleo.',
    },
]

export const POLICY_NOTES: readonly PolicyNote[] = [
    {
        id: 'PN-YT-01',
        network: 'youtube',
        statement: 'Shorts com mais de um minuto e reivindicação ativa de Content ID geram bloqueio global, sem recomendação e sem monetização. Informação de política: o núcleo não sabe verificar reivindicação.',
        source: {
            url: 'https://support.google.com/youtube/answer/15424877?hl=pt-BR',
            title: 'Como criar Shorts com até três minutos – YouTube Help',
            accessedOn: '2026-11-07T01:58Z',
            quote: 'Shorts com mais de um minuto ... reivindicação ativa do Content ID ... bloqueados globalmente',
            note: 'Nota documental: não entra como RuleKind nem gera avaliação automática.',
        },
    },
    {
        id: 'PN-YT-02',
        network: 'youtube',
        statement: 'Cota da YouTube Data API: videos.insert e search.list têm buckets próprios, com limite padrão de 100 chamadas por dia e custo de 1 unidade por chamada. O histórico de revisões registra a mudança do custo de upload "from approximately 1600 units to approximately 100 units" (2025-12-04) e a quota granular de 2026-06-01, então qualquer número 1600 está obsoleto. Informação de cota e de conta: o núcleo não autentica nem consulta quota.',
        source: {
            url: 'https://developers.google.com/youtube/data/determine_quota_cost',
            title: 'Quota Calculator | YouTube Data API',
            accessedOn: '2026-11-07T19:24Z',
            quote: 'The search.list and videos.insert methods have their own quota buckets. Each of these methods has a default daily limit of 100 per day. The quota cost is 1 per call.',
            note: 'Nota documental, ao lado de https://developers.google.com/youtube/data/revision_history: não entra como RuleKind nem gera avaliação automática.',
        },
    },
]

/** Resolve qualquer classe de regra do registro pelo ID; `null` quando inexistente. */
export function findCatalogRule(ruleId: string): CatalogRule | null {
    return CATALOG_RULES.find((rule) => rule.id === ruleId) ?? null
}

/** Resolve nota de política pelo ID; notas não são regras e nunca viram erro. */
export function findPolicyNote(noteId: string): PolicyNote | null {
    return POLICY_NOTES.find((note) => note.id === noteId) ?? null
}
