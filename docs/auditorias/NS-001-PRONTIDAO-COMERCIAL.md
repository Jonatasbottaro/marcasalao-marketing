# NS-001 — Prontidão Comercial (auditoria pré-lançamento)

> **Data:** 26/11/2026
> **Escopo:** diagnóstico e preparação — **não** publica, **não** faz deploy, **não** altera produção.
> **Campanha:** NS-001 · Studio Bella (vídeo demonstrativo da agenda) · CTA do vídeo: "Conheça o Marca Salão."
> **Repositórios:** marketing `Jonatasbottaro/marcasalao-marketing` (branch `feat/ns001-studio-bella-v2`, PR #33 rascunho) e aplicativo `Jonatasbottaro/Salao02` (branch `fix/ns-001-landing-conversao`, **sem PR**, **não integrada à main**).
> **Verificação de produção:** `https://marcasalao.com.br` lido em 26/11/2026 (conteúdo público).

---

> **RETIFICAÇÃO DE IDENTIDADE (26/11/2026):** decisão expressa do titular registrada em [MKT-BRAND-001](../decisoes/MKT-BRAND-001-marca-salao-meu-salao-studio-bella.md). **Marca Salão** é apresentação comercial/projeto; **Meu Salão** é a experiência de uso após adesão e o nome intencional do PWA; **Studio Bella** é demonstração fictícia. O antigo item B2 **não é conflito de marca nem autorização para renomear o aplicativo**. Resta somente verificar se a transição é clara ao visitante. Os bloqueadores B1 (destino), B3/B4 (UTM e conversão) continuam válidos; claims devem ser comprovados ou removidos. As menções históricas abaixo refletem a auditoria original e devem ser interpretadas à luz desta retificação.

## 1. CTA recomendado

- **Endcard do vídeo (já aprovado):** "Conheça o Marca Salão." — neutro, serve às três redes (padrão de arte quadrada compartilhada).
- **CTA de legenda por plataforma** (ver seção 4 e tabela da seção 5).
- **CTA da página de destino:** "Conheça a agenda" → `/register?role=gestor` (dois pontos de entrada na página, topo e rodapé).

## 2. Destino recomendado

- **Destino oficial da marca:** `https://marcasalao.com.br` (raiz).
- **Destino ideal para a NS-001:** `https://marcasalao.com.br/conheca-a-agenda` — página editada na branch `fix/ns-001-landing-conversao`, coerente com o vídeo (dia/semana/mês, filtro por profissional, status, detalhes).
- **Situação real:** `/conheca-a-agenda` **existe só na branch** (commit `b143105`), **não está na main**, **não tem PR** e responde **404 em produção**. O domínio serve hoje a aplicação com a marca **"Meu Salão"** (ver seção 3).
- **Recomendação:** publicar a NS-001 apontando para a **raiz** `https://marcasalao.com.br/?utm_...` (200, já no ar) **somente depois** de resolvida a divergência de marca da seção 3; ou integrar e publicar `/conheca-a-agenda` antes do tráfego pago. Enquanto a página não estiver publicada, usá-la como destino é **bloqueador**.

## 3. Jornada de cadastro verificada

| Etapa | Estado real (26/11/2026) | Observação |
| --- | --- | --- |
| `/conheca-a-agenda` | **404 em produção**; existe só na branch `fix/ns-001-landing-conversao` (`b143105`), sem PR, fora da main | Bloqueador de destino |
| `/register?role=gestor` | **200 em produção**; pré-seleciona o papel Gestor (lido em `register/page.tsx`, já na main) | Funciona |
| `/register/gestor` | Existe (branch e main) | Fluxo de gestor disponível |
| Encaminhamento UTM → cadastro | `UtmLink`/`withUtms` **só na branch**; ausente na main e em produção | Bloqueador de mensuração |
| Persistência do UTM no cadastro | **Não existe** (nem na branch): UTMs não são salvos no submit nem no perfil | Bloqueador de mensuração |
| Evento de cadastro concluído | **Não existe** evento de marketing/conversão; "analytics" do app é métrica interna de salão | Bloqueador de mensuração |

**Identidade de marca na jornada (ver Fase 2 do briefing):**

- **Marca comercial (campanha/domínio):** **Marca Salão** — `marcasalao.com.br`, endcard, roteiros.
- **Identidade intencional da experiência do cliente (aplicativo/PWA):** **Meu Salão** — `layout.tsx` (título), `manifest.ts`, `terms`, design system, cabeçalho e rodapé do site em produção. É o nome que o usuário vê ao chegar.
- **Salão fictício de demonstração:** **Studio Bella** — ambiente do vídeo NS-001; não é marca nem aparece como destino.
- **Avaliação retificada:** essa coexistência é intencional, não um defeito. Verificar se o visitante compreende a passagem da marca comercial **Marca Salão** para sua experiência **Meu Salão**. Preservar o nome do PWA; não renomear globalmente.

## 4. Estado dos UTMs

- **Padrão (marketing):** `docs/rastreio-utm.md` v1.4 (rascunho, 3 decisões do titular em aberto) e `04-legendas/matriz-utm-consolidada.csv`. NS-001 na matriz: `utm_campaign=camp-saas-demo-ns001-agenda-001`, `utm_content=marca-salao`, destino **raiz** `https://marcasalao.com.br/`.
- **Preservação na navegação (branch):** `withUtms` (`src/lib/utm.ts`) copia `utm_source/medium/campaign/term/content` da URL atual para destinos relativos via `UtmLink`, descarta parâmetros não-UTM (anti open-redirect), preserva `role=gestor`. Testes unitários existem (`src/lib/utm.test.ts`).
- **Limite real:** UTMs chegam a `/register` **na URL**, mas **não são persistidos** no cadastro e **nenhum evento de conversão** é disparado. Parâmetro de URL **não é** conversão registrada.
- **Conclusão:** hoje a NS-001 **não é mensurável** de ponta a ponta (origem → cadastro concluído).

## 5. Tabela de decisão comercial

### Bloqueadores de publicação

| # | Item | Situação atual | Problema | Impacto na conversão | Correção necessária | Repositório | Prioridade | Depende de autorização humana |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Destino `/conheca-a-agenda` | 404 em produção; só em branch sem PR | Página não publicada | Tráfego pago cai em 404 ou na raiz genérica | Integrar `fix/ns-001-landing-conversao` à main e publicar, **ou** apontar para a raiz | Salao02 | Alta | Sim (merge/deploy) |
| B2 (retificado) | Identidades complementares **Marca Salão** (comercial) e **Meu Salão** (uso/PWA) | Coexistência deliberada, registrada em MKT-BRAND-001 | **Não é bloqueador por si só**; avaliar apenas clareza da transição na aquisição | Não renomear PWA; propor copy de transição somente se houver confusão comprovada | Marketing / Salao02 | Revisão editorial, sem bloqueio automático | Comunicação pública sujeita a revisão |
| B3 | Preservação de UTM até o cadastro | `withUtms` só na branch | UTMs não chegam à produção | Atribuição de origem perdida | Integrar a branch (B1) | Salao02 | Alta | Sim (merge/deploy) |
| B4 | Persistência de UTM + evento de conversão | Inexistente | Não há registro de cadastro concluído por campanha | Impossível medir CPA/ROAS | Persistir UTMs no cadastro e emitir evento de conversão confiável | Salao02 | Alta | Sim (desenvolvimento + deploy) |

### Melhorias posteriores (não bloqueiam)

| # | Item | Problema | Impacto | Correção | Repositório | Prioridade | Autorização |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | Claims sem comprovação na home | "5.000+ salões", "100 mil/mês", "+40%", "1.1★" sem fonte | Risco de confiança/CONAR | Substituir por números comprováveis ou remover | Salao02 | Média | Sim |
| M2 | Depoimentos genéricos | "Maria Silva", "Beauty Studio" etc. | Baixa credibilidade | Confirmar ou sinalizar como ilustrativos | Salao02 | Baixa | Sim |
| M3 | Link de contato | `contato@melhorsalao.com.br` (terceiro domínio) | Confusão de marca | Alinhar ao domínio oficial | Salao02 | Baixa | Sim |
| M4 | Convergência de nomenclatura UTM | Matriz usa `camp-saas-demo-ns001-agenda-001`/`marca-salao`; playbook usa `ns-001`/`h15` | Relatórios divergentes | Padronizar (3 decisões do titular em aberto) | Marketing | Baixa | Sim |

## 6. CTAs por plataforma (Fase 4)

| Plataforma | CTA recomendado | Mecanismo real | Observação |
| --- | --- | --- | --- |
| Instagram Reels | "Conheça o sistema — link na bio" | Link da bio **não é clicável na legenda** | Só prometer após confirmar o link cadastrado no perfil |
| Facebook Reels | URL completa na descrição + "Acesse pelo link da descrição" | Descrição do Reels | Formato de publicação pode limitar clique; validar |
| YouTube Shorts | Descrição com URL + canal | Shorts não tem link clicável na tela; usar descrição/canal | Não presumir botão clicável |

**URLs (todas reais, com UTM):**

- Raiz (produção, 200): `https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=marca-salao` (trocar `source/medium` por canal).
- Destino ideal (após B1): `https://marcasalao.com.br/conheca-a-agenda?utm_source=...&utm_medium=...&utm_campaign=ns-001&utm_content=marca-salao`.

## 7. Riscos de publicação

- **Destino 404** se usar `/conheca-a-agenda` antes de B1.
- **Clareza da transição comercial → aplicativo** (Marca Salão → Meu Salão), sem conflito de identidade: decisão do titular registrada e nome do PWA preservado.
- **Sem mensuração**: UTMs não persistem e não há evento de conversão (B3/B4).
- **Claims não comprovados** na home (M1) sob o domínio da campanha.
- **Vídeo** permanece **sem áudio** (padrão VIDEO CLEAN); a versão final com narração é do titular — não confundir master limpo com peça final.

## 8. Pendências do titular

1. **Decisão de identidade concluída**: Marca Salão = comercial/site; Meu Salão = experiência/PWA; Studio Bella = demonstração. Revisar a clareza da transição, sem renomeação global (MKT-BRAND-001).
2. Autorizar **merge/deploy** de `fix/ns-001-landing-conversao` (B1/B3) — **sem PR hoje**.
3. Autorizar **desenvolvimento** de persistência de UTM + evento de conversão (B4).
4. Confirmar **link da bio** do Instagram antes de prometer CTA (Fase 4).
5. Resolver as **3 decisões UTM em aberto** (`checklist-decisoes-titular.md`).
6. Provar ou remover **claims/depoimentos** (M1/M2).

## 9. Critérios de liberação

A NS-001 pode ser publicada e medida quando:

- [ ] Destino responde 200 e apresenta uma transição compreensível entre **Marca Salão** (comercial) e **Meu Salão** (experiência/PWA); não exigir renomeação do PWA (B1 + checagem editorial de B2).
- [ ] UTMs chegam e **persistem** até o cadastro, com **evento de conversão** confiável (B3 + B4).
- [ ] CTA por plataforma confirmado (link da bio validado; descrição/Shorts conforme mecanismo real).
- [ ] Claims/depoimentos comprovados ou removidos (M1/M2).
- [x] Decisão de identidade registrada pelo titular em MKT-BRAND-001 (26/11/2026); clareza da jornada ainda sujeita a revisão.

**Sem isso, a NS-001 não deve receber tráfego pago.** Esta auditoria não publicou nada; apenas diagnostica a prontidão.

---

*Relatório de diagnóstico. Nenhuma alteração de código, produção, identidade global ou publicação foi feita nesta tarefa.*