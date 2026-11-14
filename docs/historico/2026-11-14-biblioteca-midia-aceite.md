# Aceite da biblioteca de mídia por trabalho — 14/11/2026

Registro da prova de aceite da branch técnica `codex/media-library-v1` (base `c9601990d4dbb3b291402adb23f17710115b1509`). Dados 100% fictícios; nenhum provedor externo real chamado (Gemini sem chave no ambiente; simulador nos testes e na demonstração). Evidências binárias (capturas) em `<RAIZ>/.workspace/logs/media-library-v1/browser/` e `browser-e2e.json` na mesma pasta (local, não sincroniza).

## Fluxo provado no navegador (Chromium real via Playwright, http://127.0.0.1:8799)

Trabalhos fictícios: `aceite-midias-ms` (Marca Salão) e `aceite-midias-mth` (Multitrack Hub).

1. Cena sem mídia no Planejamento → **Preparar imagem** → pedido `ImageRequest` v1 com prompt derivado do descritor, perfil `instagram-reels-video` (9:16, 1080×1920).
2. Aba **Mídias**: importação manual de `opcao-externa.png` (origem `external-tool`, ferramenta fictícia), referência `VisualAnchor` `referencia-visual-do-aceite` vinculada por versão + SHA-256.
3. Pedido com referência enviada ao provedor; prévia do texto exato exibida antes da confirmação.
4. Duas opções comparadas: importada manual + gerada pelo simulador (`simulator-v1`, marcada SIMULADA); confirmação de uma chamada por ação listando o material e a versão da referência.
5. Seleção do candidato simulador → prévia de diferenças → aplicação ao editor (`mediaId` + `media[]` com origem `generated-simulator`, licença `owned-synthetic`).
6. Exportação de vídeo (`instagram-reels-video`) e carrossel (3 JPEGs na ordem do manifesto) pelos fluxos existentes.
7. Revisão & Entrega: origens com ilustração gerada distinguida de captura/evidência; peças aprovadas; ZIP `aceite-midias-ms-pkg-6bb9f5ccef` (233854 bytes, 9 entradas, integridade OK).
8. **Revisão localizada**: troca da imagem do card `capa` → carrossel `draft_outdated`, vídeo mantém aprovação.
9. **Mídia compartilhada**: nova versão de `agenda` com `updateLinkedTargets` → confirmação identifica `video:cena-prova`, `motion:cena-prova`, `carousel:conteudo`; ambos os rascunhos apontam para a mesma versão; ambas as peças pedem nova revisão; entregas válidas anteriores preservadas.
10. **Multitrack Hub**: importação própria (`mth-referencia`), âncora `referencia-mth`, pedido e candidato simulador; nenhum asset/prompt/âncora da Marca Salão no trabalho MTH e vice-versa.
11. **Falhas**: imagem inválida rejeitada pelo conteúdo com diagnóstico pt-BR (biblioteca preservada); Gemini sem chave → HTTP 503 `IMAGE_PROVIDER_NO_CREDENTIAL` (botão desabilitado no painel); checksum divergente e seleção desatualizada cobertos na suíte Python.
12. **Reinício**: servidor reiniciado → 2 pedidos com candidatos/seleções, âncora, 4 seleções, 8/8 miniaturas e ZIP válido anterior preservado (mesmo SHA-256).

## Hashes conferidos

| Artefato | SHA-256 |
| --- | --- |
| ZIP de entrega (Marca Salão) | `e3ccf7cfb60b3edb078e7294d1a86f93868b6cbd4dd0ef438eaef4b95577b5b3` |
| MP4 final `instagram-reels-video` | `e6db59342d2928328619376b2b70aee65e5602b312d15684b8b8818891366ec3` |
| Asset gerado (simulador) no AssetManifest | prefixo `52a4ff755ac6` (conferido igual à versão da biblioteca) |

FFprobe do MP4 final: 1 stream de vídeo 1080×1920, **0 streams de áudio**.

## Gates locais (Node v22.23.2, Python 3.14, FFmpeg/FFprobe presentes)

- `platform`: `npm run build`, `npm run typecheck`, `npm run test:contracts` (323/323), suíte completa (961/961, incluindo os 30 testes novos de `VisualAnchor`/`ImageRequest` e paridade Ajv).
- Python: suíte completa `python -m unittest discover -s tools/tests` com `REQUIRE_RENDER=1` (inclui `test_studio_media.py` com 44 testes: contratos, importação, versões, seleção, concorrência 409, checksum, simulador determinístico, Gemini simulado sem rede, falhas, reinício, isolamento, AssetManifest e revisão localizada).
- Prova HTTP dedicada: `python tools/ci_media_library_proof.py --port 8797` (fluxo completo + ZIP + reinício) — executada localmente e adicionada ao CI `.github/workflows/local-render-validation.yml` (Ubuntu e Windows).
- Resultados separados: **simulador** (testes + demonstração no navegador), **servidor de teste** (prova HTTP acima), **chamada real Google**: não executada nesta rodada por ausência de `GEMINI_API_KEY` autorizada no ambiente; comando documentado no README para ambiente com chave.

Links de jobs CI e SHA de merge: merge commit `5d9a900` (PR #8, branch `codex/media-library-v1`, HEAD `46f5d93`). CI pós-merge no SHA `5d9a900`: `Validar contratos da platform` run [43619839530](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43619839530) — 4/4 jobs verdes (Ubuntu/Windows × Node 22/24); `Validar render local de prova` run [43619839527](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43619839527) — Ubuntu e Windows com a etapa dedicada `Prova da biblioteca de midia por trabalho (Studio HTTP em 127.0.0.1)`.