# Decisões e conflitos — HF-001

Contradições históricas identificadas na auditoria e sua resolução registrada. Nenhuma
foi "corrigida" apagando o histórico: o registro anterior permanece como fato do seu
tempo, com nota datada apontando para o estado vigente.

## 1. "HyperFrames não foi adotado" × HyperFrames motor principal

- **Registro histórico:** `docs/decisoes/MKT-VIDEO-001-producao-modular.md` afirmava
  que o HyperFrames não foi adotado (era verdade na data em que foi escrito).
- **Estado vigente (27/11/2026):** `MKT-VIDEO-003` promove o HyperFrames a motor
  principal.
- **Resolução:** nota de classificação datada adicionada ao MKT-VIDEO-001, apontando
  para MKT-VIDEO-003. O texto original é preservado como registro histórico.

## 2. `requireSrt: true` (legado) × VIDEO CLEAN (sem SRT por padrão)

- **Registro legado:** `tenants/marca-salao/brand-kit.json` e `guardrails.json`
  carregam `audioPolicy.requireSrt: true` + `subtitleStyle` ASS — descrevem o fluxo
  da fábrica antiga (`preset_runner.py`/`factory_cli.py`), que exige legenda
  queimada + SRT.
- **Estado vigente:** MKT-VIDEO-002 (VIDEO CLEAN) — sem legenda queimada, sem SRT
  por padrão, narração TXT separada. `frame.md` registra a divergência
  explicitamente.
- **Resolução:** os dois fluxos coexistem por desenho. O legado fica **congelado**
  (LEGADO na matriz) e continua válido para campanhas antigas; produções novas
  (caminho VideoRequest/Studio) seguem VIDEO CLEAN. **Nenhum** dos arquivos legados
  é editado para "harmonizar" — a divergência é documentada, não apagada.

## 3. "Nenhum renderizador implementado" × runtime instalado

- **Registro desatualizado:** `platform/README.md` afirma que nenhum renderizador
  foi implementado — verdade até 27/11/2026.
- **Resolução:** atualizar `platform/README.md` na entrega do adaptador (F6),
  descrevendo `renderers/hyperframes/` como o primeiro consumidor de
  `renderer.adapter`. Até lá, o README descreve a base da branch `main`.

## 4. Skills HyperFrames: convenção `.agents/skills/` × `hyperframes skills check`

- **Fato:** o CLI `hyperframes skills check` não reconhece a convenção
  `.agents/skills/` (usada pelo harness); o caminho oficial de atualização é
  `npx skills add heygen-com/hyperframes --all`.
- **Resolução:** skills vendadas em `.agents/skills/` com `skills-lock.json` v2
  (upstream `cfaefdc` + hashes). Atualização somente pelo procedimento oficial,
  registrando o commit upstream no lock. O `skills check` do CLI não é gate deste
  projeto.

## 5. Lock de skills: v1 (main, não rastreado) × v2 (worktree hf001)

- **Fato:** o checkout principal tem um `skills-lock.json` v1 não rastreado
  (web-design-guidelines); a worktree hf001 criou o lock v2 (hyperframes) já
  commitado.
- **Resolução:** reconciliar na integração da branch (F18): o lock v2 versionado
  passa a ser o canônico; o v1 não rastreado do checkout principal é trabalho de
  outra sessão e não é tocado por esta operação.

## 6. Caches fora da raiz (incidente corrigido)

- **Fato:** na primeira instalação, `git rev-parse --git-common-dir` devolveu caminho
  Windows (`C:/...`) que o `env.sh` não reconhecia; caches npm (106 MB) e Chrome
  (717 MB) foram parar em `/.workspace` **fora de `<RAIZ>`** — violação da regra de
  portabilidade.
- **Resolução:** caches movidos para `<RAIZ>/.workspace/tmp/hf001/` (preservando o
  download do Chrome), diretório externo removido, `env.sh` corrigido com o case
  `[A-Za-z]:[/\\]*` + verificação de sanidade (`AGENTS.md` na raiz resolvida).
  Verificação de vazamento: nenhum `~/.hyperframes`, `~/.cache/puppeteer` ou
  `/.workspace` restante. Registrado como incidente e correção permanente do env.

## 7. Seleção de renderer: automática × explícita

- **Tentação registrada:** em erro do HyperFrames, cair automaticamente no FFmpeg
  "para não travar a produção".
- **Resolução (MKT-VIDEO-003):** proibido o fallback silencioso. A escolha de
  renderer é explícita no manifest; falha do motor = item `failed` com log para
  decisão humana. O FALLBACK existe e é testado, mas é **operacional** (RUNBOOK),
  não automático.

## 8. Publicação: capacidade × autorização

- **Fato:** o motor e o Studio são capazes de produzir peças prontas.
- **Resolução (permanente):** `autoPublish: false`; a HF-001 não publica, não agenda
  e não cria rascunhos Postiz. Campanha piloto (F12) para em pacote de entrega +
  revisão humana (F13). Publicação segue exigindo pedido/autorização do titular.
