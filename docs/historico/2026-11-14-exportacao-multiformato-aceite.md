# Aceite da exportação multiformato no Studio local — 14/11/2026

Registro da prova de aceite da branch técnica `codex/multi-format-export-v1` (base `68b2721cb0d08a28b015b52ec25a56af89708f25`). Dados 100% fictícios; nenhum provedor externo chamado. Evidências binárias em `<RAIZ>/.workspace/logs/multi-format-export-v1/browser/` e `browser-e2e.json` na mesma pasta (local, não sincroniza).

## Fluxo provado no navegador (Chromium real via Playwright, http://127.0.0.1:8795)

Trabalhos fictícios: `mf-aceite-ms` (Marca Salão, projeto `mf-aceite-proj` com horizontal+4:5 na allowlist) e `mf-aceite-mth` (Multitrack Hub).

1. Planejamento com seletor de formato do carrossel (1:1 1080×1080 · 4:5 1080×1350) e perfis recomendados por modalidade.
2. Biblioteca: importação de versão 16:9 da mídia `abertura`; atualização de mídia compartilhada identificando `video:cena-1`, `motion:cena-1`, `carousel:capa`.
3. Pedido de imagem 16:9 pela biblioteca: geometria 1920×1080 derivada do perfil; nota de enquadramento da mídia atual (fit + pad centralizado); comparação simulador × importação manual (mídia quadrada fora de proporção); seleção aplicada pela prévia de diferenças.
4. Editor de Vídeos: tabela de perfis com `youtube-video-horizontal` 1920×1080 (16:9) @30 compatível ao lado dos verticais; prévia offline do quadro efetivo (canvas 320×180) com regra de enquadramento.
5. Exportação dos dois destinos no mesmo pedido: 2/2 entregas válidas (MP4 + SRT + TXT por perfil).
6. Carrossel 4:5: prévia com letterbox para a mídia 16:9 da capa; 3 JPEGs 1080×1350 na ordem; hashes conferidos.
7. Revisão & Entrega: aprovação de canais e peças; ZIP `mf-aceite-ms-pkg-733c3d4049` (322077 bytes, 18 entradas) com vertical + horizontal + 4:5 + textos por canal; manifesto conferido contra os bytes do ZIP; integridade OK.
8. Texto-only do canal horizontal → `copy_outdated` só naquele canal; hashes dos MP4s e artefatos dos outros perfis preservados.
9. Motion: seletor restrito a 9:16 e nota explicando o recorte (coordenadas relativas ao quadro final).
10. Multitrack Hub: projeto de exemplo sem 4:5 (seletor só 1:1); projeto fictício `mf-aceite-mth-proj` habilita portrait; exportação 1080×1350 concluída; isolamento de arquivos/prompts/decisões preservado.
11. Falha: `MotionPlan` em destino horizontal → `MOTION_LOCAL_UNSUPPORTED_GEOMETRY` somente naquele perfil; entrega vertical válida preservada.
12. Reinício do servidor: peças aprovadas nos três destinos, ZIP válido anterior preservado, trabalhos reabertos.

## Medidas FFprobe (bytes finais promovidos)

| Destino | Geometria | Codec | FPS | Áudio | Duração | SHA-256 (prefixo) |
| --- | --- | --- | --- | --- | --- | --- |
| instagram-reels-video | 1080×1920 | h264 | 30/1 | 0 | 8.0 s | `830f45154830ea5b` |
| youtube-video-horizontal | 1920×1080 | h264 | 30/1 | 0 | 8.0 s | `095dcdb204ff144f` |

JPEGs do carrossel (ambas as marcas): 1080×1350, hashes do manifesto conferidos contra os bytes. Quadro extraído do MP4 horizontal mostra título no topo e legenda na base, dentro das áreas úteis (captura 12).

## ZIP multiformato

- Pacote: `mf-aceite-ms-pkg-733c3d4049` · 322077 bytes · SHA-256 `ce7c87e28a0cdf3e2b6a5b69361c8ecd872e184cb96cd7fd167618a0442883f4`
- 18 entradas: `video/instagram-reels-video/`, `video/youtube-video-horizontal/`, `carousel/instagram-feed-image-portrait/`, `textos-por-canal/<3 perfis>/`, `briefing/`, `package-manifest.json`.
- Manifesto × bytes do ZIP: 0 divergências; `testzip()` OK.

## Gates locais (Node v22.23.2, Python 3.14, FFmpeg/FFprobe presentes)

- `platform`: build, typecheck, `test:contracts`, suíte completa (inclui `local-export.test.ts` e geometria horizontal em `local-render-input.test.ts`).
- Python: suíte completa com `REQUIRE_RENDER=1` (inclui `tools/tests/test_multi_format.py`, 12 testes).
- Prova HTTP dedicada: `python tools/ci_multi_format_proof.py --port 8796` (local + etapa CI Ubuntu/Windows).
- Resultados separados: simulador (testes + demonstração), servidor de teste (prova HTTP), chamada real externa: nenhuma nesta rodada.

Links de jobs CI e SHA de merge: merge commit `bff2e46` (PR #9, branch `codex/multi-format-export-v1`, HEAD `6c48f20`). CI pós-merge no SHA `bff2e46`: `Validar contratos da platform` run [43631007343](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43631007343) — 4/4 jobs verdes (Ubuntu/Windows × Node 22/24); `Validar render local de prova` run [43631007337](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43631007337) — Ubuntu e Windows com a etapa dedicada `Prova da exportacao multiformato (horizontal 16:9 e carrossel 4:5, Studio HTTP)`.