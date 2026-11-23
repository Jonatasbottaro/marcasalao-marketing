"""Testes do auditor de release em 8 dominios (tools/release_audit.py).

Cobertura (Etapa 4, Agente 4 + Etapa 11, Agente 1):
  - Relatorio schemaVersion 2 com 8 dominios ordenados, problemas tipados
    (severity/code/message) e aprovacao nao-strict no repositorio atual.
  - Avisos dos dominios 4/5/6/8 antes da consolidacao completa: nao reprovam
    sem --strict, reprovam com --strict; sandbox completo aprova no --strict.
  - Falhas simuladas por dominio: hash corrompido, arquivo/diretorio ausente,
    politica de audio violada, autoPublish true, guardrailsAudited false,
    contagem de slots divergente, caminho absoluto vazado no portal, declaracao
    de derivado incompleta, midia rastreada, .gitattributes sem cobertura
    eol=lf e worktrees irregulares.
  - Dominio 8 (empacotamento_distribuicao): sem bundles na estação gera aviso
    `BUNDLES_AUSENTES`; bundles adulterados geram erro.
  - CLI: --json, --strict, --report-out (com contencao sob a raiz) e erros
    de uso (exit 2).
"""

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
# Caminho curto: o worktree ja e profundo e o Windows falha com WinError 3
# acima de ~248 caracteres (limiar de render_local.fs_path).
TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "rel-audit")

sys.path.insert(0, TOOLS_DIR)

import release_audit  # noqa: E402
import render_local  # noqa: E402

DOMAIN_IDS = [
    "contratos_tenants",
    "entregas_video",
    "pacotes_sociais",
    "derivados_multiformato",
    "calendario_utm",
    "portal_revisao",
    "higiene_git",
    "empacotamento_distribuicao",
]

DOMAIN_NAMES = [
    "Contratos & Tenants",
    "Entregas de Vídeo & Manifestos",
    "Pacotes Sociais & Guardrails",
    "Derivados Multiformato",
    "Calendário Editorial & Matriz UTM",
    "Portal Visual de Revisão",
    "Higiene Git, EOL e Worktrees",
    "Empacotamento de Distribuição",
]

WARN_ONLY_DOMAINS = {"derivados_multiformato", "calendario_utm", "portal_revisao"}


def _force_rmtree(path: str) -> None:
    if not os.path.isdir(path):
        return
    for dirpath, _dirnames, filenames in os.walk(path):
        for fname in filenames:
            target = os.path.join(dirpath, fname)
            try:
                os.chmod(target, stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)


def _count_campaign_files(root: str) -> int:
    tenants_dir = os.path.join(root, "tenants")
    total = 0
    for tenant in sorted(os.listdir(tenants_dir)):
        campaigns_dir = os.path.join(tenants_dir, tenant, "campaigns")
        if os.path.isdir(campaigns_dir):
            total += sum(1 for name in os.listdir(campaigns_dir) if name.endswith(".json"))
    return total


def _git(cwd: str, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ReleaseAuditTests(unittest.TestCase):
    maxDiff = None

    def tearDown(self) -> None:
        sandbox = getattr(self, "_sandbox", None)
        if sandbox:
            _force_rmtree(sandbox)

    @classmethod
    def tearDownClass(cls):
        _force_rmtree(TEST_TMP_ROOT)

    def _build_sandbox(self, *, with_matriz: bool = False) -> str:
        method = self.id().rsplit(".", 1)[-1]
        sandbox = os.path.join(TEST_TMP_ROOT, "sb-" + method.split("_")[1])
        _force_rmtree(sandbox)
        os.makedirs(sandbox)
        shutil.copytree(os.path.join(REPO_ROOT, "schemas"), os.path.join(sandbox, "schemas"))
        shutil.copytree(os.path.join(REPO_ROOT, "tenants"), os.path.join(sandbox, "tenants"))
        shutil.copytree(
            os.path.join(REPO_ROOT, "02-reels-shorts", "deliveries"),
            os.path.join(sandbox, "02-reels-shorts", "deliveries"),
        )
        shutil.copytree(
            os.path.join(REPO_ROOT, "04-legendas", "pacotes-publicacao"),
            os.path.join(sandbox, "04-legendas", "pacotes-publicacao"),
        )
        shutil.copytree(
            os.path.join(REPO_ROOT, "05-review-portal"),
            os.path.join(sandbox, "05-review-portal"),
        )
        for name in ("calendario-editorial.json", "calendario-editorial.md"):
            shutil.copy2(
                os.path.join(REPO_ROOT, "04-legendas", name),
                os.path.join(sandbox, "04-legendas", name),
            )
        if with_matriz:
            with open(
                os.path.join(sandbox, "04-legendas", "matriz-utm-consolidada.csv"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write("tenantId,slug,canal,formato,utmUrl\n")
                handle.write(
                    "marca-salao,camp-saas-demo-marca-salao-001,instagram,reels,"
                    "https://marcasalao.com.br/?utm_source=instagram\n"
                )
        shutil.copy2(
            os.path.join(REPO_ROOT, ".gitattributes"),
            os.path.join(sandbox, ".gitattributes"),
        )
        # Sem o .gitignore real, estacoes com midia local em disco rastreiam
        # MP4/WAV no `git add -A` do sandbox e disparam MIDIA_RASTREADA.
        shutil.copy2(
            os.path.join(REPO_ROOT, ".gitignore"),
            os.path.join(sandbox, ".gitignore"),
        )
        _git(sandbox, "init", "-q")
        _git(sandbox, "add", "-A")
        _git(
            sandbox,
            "-c", "user.name=release-audit-test",
            "-c", "user.email=release-audit-test@example.invalid",
            "commit", "-q", "-m", "sandbox",
        )
        self._sandbox = sandbox
        return sandbox

    def _find_domain(self, result: dict, domain_id: str) -> dict:
        for domain in result["domains"]:
            if domain["id"] == domain_id:
                return domain
        self.fail(f"dominio ausente no relatorio: {domain_id}")

    def _codes(self, domain: dict) -> list[str]:
        return [problem["code"] for problem in domain["problems"]]

    def _edit_json(self, path: str, mutate) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        mutate(data)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def _run_cli(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = release_audit.main(list(args))
        return code, stdout.getvalue()

    # ------------------------------------------------------------------
    # Dominio: relatorio e estado real do repositorio
    # ------------------------------------------------------------------

    def test_01_seven_domain_report_on_current_repo(self):
        result = release_audit.run_release_audit(root=REPO_ROOT)
        self.assertEqual(result["schemaVersion"], 2)
        self.assertFalse(result["strict"])
        self.assertEqual([domain["id"] for domain in result["domains"]], DOMAIN_IDS)
        self.assertEqual([domain["name"] for domain in result["domains"]], DOMAIN_NAMES)
        # .workspace/archives/ e local e nao versionado: outras estacoes/agentes
        # podem regera-lo entre execucoes. A deriva e permitida AQUI, mas e
        # reportada; o sandbox limpo (test_03) continua exigindo zero problemas.
        local_drift = {
            "ARCHIVE_HASH_DIVERGENTE", "ARCHIVE_FFPROBE_DIVERGENTE",
            "MIDIA_ORFA", "MIDIA_AUSENTE", "FFPROBE_INDISPONIVEL",
        }
        for domain in result["domains"]:
            self.assertTrue(domain["name"])
            self.assertIn(domain["status"], {"ok", "warn", "fail"})
            self.assertEqual(domain["ok"], domain["status"] != "fail")
            for problem in domain["problems"]:
                self.assertEqual(set(problem), {"severity", "code", "message"})
                self.assertIn(problem["severity"], {"error", "warning"})
                if problem["code"] not in local_drift:
                    self.assertEqual(problem["severity"], "warning")
                    self.assertIn(domain["id"], WARN_ONLY_DOMAINS)
        summary = result["summary"]
        self.assertEqual(sum(summary["domains"].values()), 8)
        self.assertGreaterEqual(summary["tenants"]["valid"], 4)
        self.assertEqual(summary["tenants"]["invalid"], 0)
        self.assertEqual(summary["campaigns"]["total"], _count_campaign_files(REPO_ROOT))
        code, stdout = self._run_cli("--root", REPO_ROOT, "--json")
        self.assertIn(code, (0, 1))
        payload = json.loads(stdout)
        self.assertEqual([domain["id"] for domain in payload["domains"]], DOMAIN_IDS)
        all_errors = [
            p for domain in payload["domains"] for p in domain["problems"]
            if p["severity"] == "error"
        ]
        self.assertEqual(payload["ok"], not all_errors)
        self.assertTrue(all(p["code"] in local_drift for p in all_errors))

    def test_02_missing_matriz_warns_and_strict_blocks(self):
        sandbox = self._build_sandbox()
        result = release_audit.run_release_audit(root=sandbox)
        self.assertTrue(result["ok"])
        calendario = self._find_domain(result, "calendario_utm")
        self.assertEqual(calendario["status"], "warn")
        self.assertIn("MATRIZ_UTM_AUSENTE", self._codes(calendario))
        self.assertEqual(result["summary"]["problems"]["errors"], 0)
        self.assertGreaterEqual(result["summary"]["problems"]["warnings"], 1)

        strict = release_audit.run_release_audit(root=sandbox, strict=True)
        self.assertFalse(strict["ok"])
        self.assertTrue(strict["strict"])
        strict_calendario = self._find_domain(strict, "calendario_utm")
        severities = [
            problem["severity"]
            for problem in strict_calendario["problems"]
            if problem["code"] == "MATRIZ_UTM_AUSENTE"
        ]
        # A severidade registrada nao muda; o modo strict bloqueia o resultado.
        self.assertEqual(severities, ["warning"])

        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 0)
        code, stdout = self._run_cli("--root", sandbox, "--strict", "--json")
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(stdout)["ok"])

    def test_03_complete_sandbox_passes_strict(self):
        sandbox = self._build_sandbox(with_matriz=True)
        result = release_audit.run_release_audit(root=sandbox, strict=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["problems"]["errors"], 0)
        self.assertEqual(result["summary"]["problems"]["warnings"], 0)
        for domain in result["domains"]:
            self.assertEqual(domain["status"], "ok", domain["id"])
            self.assertEqual(domain["problems"], [])
        code, _ = self._run_cli("--root", sandbox, "--strict", "--json")
        self.assertEqual(code, 0)

    # ------------------------------------------------------------------
    # Dominio 2: entregas de video e manifestos
    # ------------------------------------------------------------------

    def test_04_corrupted_srt_hash_fails(self):
        sandbox = self._build_sandbox()
        srt_path = os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "marca-salao",
            "camp-saas-demo-marca-salao-001", "camp-saas-demo-marca-salao-001.srt",
        )
        with open(srt_path, "a", encoding="utf-8") as handle:
            handle.write("x")
        result = release_audit.run_release_audit(root=sandbox)
        # Defeito de conteudo reprova tambem sem --strict.
        self.assertFalse(result["ok"])
        entregas = self._find_domain(result, "entregas_video")
        self.assertEqual(entregas["status"], "fail")
        divergent = [p for p in entregas["problems"] if p["code"] == "HASH_DIVERGENTE"]
        self.assertEqual(len(divergent), 1)
        self.assertEqual(divergent[0]["severity"], "error")
        self.assertIn("camp-saas-demo-marca-salao-001.srt", divergent[0]["message"])
        self.assertEqual(result["summary"]["campaigns"]["deliveriesFailed"], 1)
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_05_missing_storyboard_fails(self):
        sandbox = self._build_sandbox()
        os.remove(os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "meu-salao",
            "camp-saas-demo-meu-salao-001", "preview-storyboard.png",
        ))
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        entregas = self._find_domain(result, "entregas_video")
        self.assertIn("ARQUIVO_AUSENTE", self._codes(entregas))

    def test_06_missing_delivery_dir_fails(self):
        sandbox = self._build_sandbox()
        _force_rmtree(os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "estudio-flow",
            "camp-saas-demo-estudio-flow-001",
        ))
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        entregas = self._find_domain(result, "entregas_video")
        self.assertIn("DELIVERY_DIR_AUSENTE", self._codes(entregas))
        self.assertEqual(result["summary"]["campaigns"]["deliveriesFailed"], 1)

    def test_07_audio_policy_violation_fails(self):
        sandbox = self._build_sandbox()
        # Tenant que proibe audio (-an) com faixa declarada no ffprobe.
        self._edit_json(
            os.path.join(
                sandbox, "02-reels-shorts", "deliveries", "marca-salao",
                "camp-saas-demo-marca-salao-001", "manifest.json",
            ),
            lambda manifest: manifest["artifacts"]["video"]["ffprobe"].__setitem__("audioStreams", 1),
        )
        # Tenant que permite audio (aac) sem faixa declarada no ffprobe.
        self._edit_json(
            os.path.join(
                sandbox, "02-reels-shorts", "deliveries", "multitrack-hub",
                "camp-shorts-rateios-002", "manifest.json",
            ),
            lambda manifest: manifest["artifacts"]["video"]["ffprobe"].__setitem__("audioStreams", 0),
        )
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        entregas = self._find_domain(result, "entregas_video")
        violations = [
            p for p in entregas["problems"] if p["code"] == "POLITICA_AUDIO_DESCUMPRIDA"
        ]
        self.assertEqual(len(violations), 2)
        self.assertTrue(all(p["severity"] == "error" for p in violations))
        self.assertEqual(result["summary"]["campaigns"]["deliveriesFailed"], 2)

    # ------------------------------------------------------------------
    # Dominio 3: pacotes sociais e guardrails
    # ------------------------------------------------------------------

    def test_08_auto_publish_and_guardrails_fail(self):
        sandbox = self._build_sandbox()
        def flip(data):
            data["autoPublish"] = True
            data["guardrailsAudited"] = False
        self._edit_json(
            os.path.join(
                sandbox, "04-legendas", "pacotes-publicacao", "multitrack-hub",
                "camp-shorts-rateios-002", "checklist-publicacao.json",
            ),
            flip,
        )
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        pacotes = self._find_domain(result, "pacotes_sociais")
        self.assertEqual(pacotes["status"], "fail")
        codes = self._codes(pacotes)
        self.assertIn("AUTO_PUBLICACAO_ATIVO", codes)
        self.assertIn("GUARDRAILS_NAO_AUDITADOS", codes)
        self.assertEqual(result["summary"]["campaigns"]["packagesFailed"], 1)
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_09_missing_package_dir_fails(self):
        sandbox = self._build_sandbox()
        _force_rmtree(os.path.join(
            sandbox, "04-legendas", "pacotes-publicacao", "multitrack-hub",
            "camp-shorts-stems-workflow-003",
        ))
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        self.assertIn("PACOTE_AUSENTE", self._codes(self._find_domain(result, "pacotes_sociais")))

    def test_10_missing_social_file_fails(self):
        sandbox = self._build_sandbox()
        os.remove(os.path.join(
            sandbox, "04-legendas", "pacotes-publicacao", "marca-salao",
            "camp-saas-demo-marca-salao-001", "instagram-reels.md",
        ))
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        pacotes = self._find_domain(result, "pacotes_sociais")
        missing = [p for p in pacotes["problems"] if p["code"] == "ARQUIVO_PACOTE_AUSENTE"]
        self.assertEqual(len(missing), 1)
        self.assertIn("instagram-reels.md", missing[0]["message"])

    # ------------------------------------------------------------------
    # Dominio 4: derivados multiformato
    # ------------------------------------------------------------------

    def test_11_derivative_declaration_defects_fail(self):
        sandbox = self._build_sandbox(with_matriz=True)
        def break_declarations(data):
            del data["derivatives"]["1x1"]
            data["derivatives"]["16x9"]["sha256"] = None
        self._edit_json(
            os.path.join(
                sandbox, "02-reels-shorts", "deliveries", "marca-salao",
                "camp-saas-demo-marca-salao-001", "derivatives.json",
            ),
            break_declarations,
        )
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "derivados_multiformato")
        codes = self._codes(dominio)
        self.assertIn("DERIVADO_DECLARACAO_AUSENTE", codes)
        self.assertIn("DERIVADO_SEM_HASH", codes)
        self.assertTrue(all(p["severity"] == "error" for p in dominio["problems"]))

    def test_12_derivative_file_hash_divergent_fails(self):
        sandbox = self._build_sandbox(with_matriz=True)
        derivatives_path = os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "marca-salao",
            "camp-saas-demo-marca-salao-001", "derivatives.json",
        )
        with open(derivatives_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        cover_rel = data["derivatives"]["cover"]["path"]
        self.assertFalse(os.path.isabs(cover_rel))
        cover_abs = os.path.join(sandbox, *cover_rel.split("/"))
        os.makedirs(os.path.dirname(cover_abs), exist_ok=True)
        with open(cover_abs, "wb") as handle:
            handle.write(b"conteudo-divergente")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "derivados_multiformato")
        divergent = [p for p in dominio["problems"] if p["code"] == "HASH_DIVERGENTE"]
        self.assertEqual(len(divergent), 1)
        self.assertIn("cover", divergent[0]["message"])

    # ------------------------------------------------------------------
    # Dominio 5: calendario editorial e matriz UTM
    # ------------------------------------------------------------------

    def test_13_calendar_defects_fail(self):
        sandbox = self._build_sandbox(with_matriz=True)
        def break_calendar(data):
            data["slots"][0]["autoPublish"] = True
            data["totalSlots"] = data["totalSlots"] + 1
        self._edit_json(
            os.path.join(sandbox, "04-legendas", "calendario-editorial.json"),
            break_calendar,
        )
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "calendario_utm")
        codes = self._codes(dominio)
        self.assertIn("AUTO_PUBLICACAO_ATIVO", codes)
        self.assertIn("SLOTS_CONTAGEM_DIVERGENTE", codes)

    # ------------------------------------------------------------------
    # Dominio 6: portal visual de revisao
    # ------------------------------------------------------------------

    def test_14_absolute_path_leak_fails(self):
        sandbox = self._build_sandbox()
        self._edit_json(
            os.path.join(sandbox, "05-review-portal", "portal-data.json"),
            lambda data: data.__setitem__("estacao", "D:/Mega/Marketing/marcasalao-marketing"),
        )
        with open(os.path.join(sandbox, "05-review-portal", "index.html"), "a", encoding="utf-8") as handle:
            handle.write("<!-- gerado em C:/Users/agente -->\n")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "portal_revisao")
        leaks = [p for p in dominio["problems"] if p["code"] == "CAMINHO_ABSOLUTO_VAZADO"]
        self.assertEqual(len(leaks), 2)
        self.assertTrue(all(p["severity"] == "error" for p in leaks))
        messages = " ".join(p["message"] for p in leaks)
        self.assertIn("portal-data.json", messages)
        self.assertIn("index.html", messages)

    # ------------------------------------------------------------------
    # Consolidacao pendente: dominios 4/5/6 avisam sem reprovar
    # ------------------------------------------------------------------

    def test_15_missing_etapa4_artifacts_warn_not_fail(self):
        sandbox = self._build_sandbox()
        deliveries = os.path.join(sandbox, "02-reels-shorts", "deliveries")
        for tenant in sorted(os.listdir(deliveries)):
            tenant_dir = os.path.join(deliveries, tenant)
            if not os.path.isdir(tenant_dir):
                continue
            for slug in sorted(os.listdir(tenant_dir)):
                derivative = os.path.join(tenant_dir, slug, "derivatives.json")
                if os.path.isfile(derivative):
                    os.remove(derivative)
        _force_rmtree(os.path.join(sandbox, "05-review-portal"))
        os.remove(os.path.join(sandbox, "04-legendas", "calendario-editorial.json"))
        os.remove(os.path.join(sandbox, "04-legendas", "calendario-editorial.md"))

        result = release_audit.run_release_audit(root=sandbox)
        # Artefatos ausentes antes da consolidacao: aviso, nunca falha.
        self.assertTrue(result["ok"])
        for domain_id, code in (
            ("derivados_multiformato", "DERIVATIVES_AUSENTE"),
            ("calendario_utm", "CALENDARIO_AUSENTE"),
            ("portal_revisao", "PORTAL_ARQUIVO_AUSENTE"),
        ):
            domain = self._find_domain(result, domain_id)
            self.assertEqual(domain["status"], "warn", domain_id)
            self.assertIn(code, self._codes(domain))
            self.assertTrue(
                all(p["severity"] == "warning" for p in domain["problems"]), domain_id
            )
        strict = release_audit.run_release_audit(root=sandbox, strict=True)
        self.assertFalse(strict["ok"])
        code, _ = self._run_cli("--root", sandbox, "--strict", "--json")
        self.assertEqual(code, 1)

    # ------------------------------------------------------------------
    # Dominio 7: higiene Git, EOL e worktrees
    # ------------------------------------------------------------------

    def test_16_tracked_media_fails(self):
        sandbox = self._build_sandbox()
        with open(os.path.join(sandbox, "fake.mp4"), "wb") as handle:
            handle.write(b"fake-video")
        with open(os.path.join(sandbox, "fake.wav"), "wb") as handle:
            handle.write(b"fake-audio")
        _git(sandbox, "add", "-f", "fake.mp4", "fake.wav")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "higiene_git")
        tracked = [p for p in dominio["problems"] if p["code"] == "MIDIA_RASTREADA"]
        self.assertEqual(len(tracked), 1)
        self.assertIn("fake.mp4", tracked[0]["message"])
        self.assertIn("fake.wav", tracked[0]["message"])

    def test_17_gitattributes_without_eol_lf_fails(self):
        sandbox = self._build_sandbox()
        with open(os.path.join(sandbox, ".gitattributes"), "w", encoding="utf-8") as handle:
            handle.write("*.png binary\n")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        self.assertIn(
            "GITATTRIBUTES_SEM_EOL_LF", self._codes(self._find_domain(result, "higiene_git"))
        )

    def test_18_gitattributes_partial_extension_coverage_fails(self):
        sandbox = self._build_sandbox()
        with open(os.path.join(sandbox, ".gitattributes"), "w", encoding="utf-8") as handle:
            handle.write("tenants/**/*.json text eol=lf\n")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "higiene_git")
        missing = [p for p in dominio["problems"] if p["code"] == "GITATTRIBUTES_EXT_SEM_EOL_LF"]
        self.assertTrue(missing)
        messages = " ".join(p["message"] for p in missing)
        for ext in (".srt", ".md", ".html"):
            self.assertIn(ext, messages)
        self.assertNotIn(".json ", messages)

    def test_19_orphan_worktree_warns(self):
        sandbox = self._build_sandbox(with_matriz=True)
        os.makedirs(os.path.join(sandbox, ".workspace", "worktrees", "prova-campanha-conclusao"))
        result = release_audit.run_release_audit(root=sandbox)
        self.assertTrue(result["ok"])
        dominio = self._find_domain(result, "higiene_git")
        orphan = [p for p in dominio["problems"] if p["code"] == "WORKTREE_ORFA"]
        self.assertEqual(len(orphan), 1)
        self.assertEqual(orphan[0]["severity"], "warning")
        code, _ = self._run_cli("--root", sandbox, "--strict", "--json")
        self.assertEqual(code, 1)

    def test_20_registered_worktree_without_dir_fails(self):
        sandbox = self._build_sandbox(with_matriz=True)
        worktree_path = os.path.join(sandbox, ".workspace", "worktrees", "studio-package-verify2")
        os.makedirs(os.path.dirname(worktree_path), exist_ok=True)
        # --no-checkout: o checkout do worktree excederia MAX_PATH no Windows
        # (caminho do sandbox + arquivo mais profundo da entrega); o check do
        # auditor depende apenas do registro e do diretorio ausente.
        _git(sandbox, "worktree", "add", "--detach", "--no-checkout", worktree_path)
        _force_rmtree(worktree_path)
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        self.assertIn(
            "WORKTREE_REGISTRADA_SEM_DIRETORIO",
            self._codes(self._find_domain(result, "higiene_git")),
        )

    # ------------------------------------------------------------------
    # CLI: --json, --report-out, contencao e erros de uso
    # ------------------------------------------------------------------

    def test_21_cli_report_out_and_usage_errors(self):
        sandbox = self._build_sandbox(with_matriz=True)
        code, stdout = self._run_cli(
            "--root", sandbox, "--json", "--report-out", ".workspace/tmp/release-report.json"
        )
        self.assertEqual(code, 0)
        payload = json.loads(stdout)
        report_path = os.path.join(sandbox, ".workspace", "tmp", "release-report.json")
        self.assertTrue(os.path.isfile(report_path))
        with open(report_path, "r", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), payload)

        code, stdout = self._run_cli(
            "--root", sandbox, "--json", "--report-out", "../fora-da-raiz.json"
        )
        self.assertEqual(code, 2)
        self.assertIn("PATH_OUTSIDE_ROOT", json.loads(stdout)["error"])
        self.assertFalse(os.path.isfile(os.path.join(TEST_TMP_ROOT, "fora-da-raiz.json")))

        code, _ = self._run_cli("--root", os.path.join(sandbox, "nao-existe"), "--json")
        self.assertEqual(code, 2)

    def test_22_cli_json_stdout_is_utf8(self):
        # Os nomes de dominio sao acentuados: a saida do CLI precisa ser UTF-8
        # tambem no Windows, onde o encoding padrao de pipe/arquivo redirecionado
        # e o da locale (cp1252) e corromperia o relatorio para qualquer
        # consumidor UTF-8 (inclusive o runner windows-latest do CI).
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        env["PYTHONUTF8"] = "0"
        proc = subprocess.run(
            [sys.executable, os.path.join("tools", "release_audit.py"), "--root", REPO_ROOT, "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            env=env,
        )
        # Deriva de midia local em .workspace/archives/ pode reprovar o gate
        # nesta estacao; o que se exige aqui e UTF-8 valido e o relatorio completo.
        self.assertIn(proc.returncode, (0, 1), proc.stderr.decode("utf-8", "replace"))
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual([domain["name"] for domain in payload["domains"]], DOMAIN_NAMES)

        proc_human = subprocess.run(
            [sys.executable, os.path.join("tools", "release_audit.py"), "--root", REPO_ROOT],
            cwd=REPO_ROOT,
            capture_output=True,
            env=env,
        )
        self.assertIn(proc_human.returncode, (0, 1))
        self.assertIn("Entregas de Vídeo & Manifestos", proc_human.stdout.decode("utf-8"))

    # ------------------------------------------------------------------
    # Integridade manifestos <-> binarios locais e midia nao-ignorada
    # ------------------------------------------------------------------

    def _seed_one_campaign_archives(self, sandbox: str) -> str:
        """Traz para o sandbox apenas a midia local de uma campanha versionada."""
        slug = "camp-saas-demo-marca-salao-001"
        source = os.path.join(REPO_ROOT, ".workspace", "archives", slug)
        if not os.path.isdir(render_local.fs_path(source)):
            self.skipTest(f"arquivo real de arquivo nao disponível nesta estação: {source}")
        target = os.path.join(sandbox, ".workspace", "archives", slug)
        shutil.copytree(source, target)
        # No projeto real .workspace/ e ignorado por .git/info/exclude;
        # replicate isso para nao confundir com MIDIA_NAO_IGNORADA.
        info_exclude = os.path.join(sandbox, ".git", "info", "exclude")
        with open(info_exclude, "a", encoding="utf-8") as handle:
            handle.write("\n.workspace/\n")
        return target

    def _all_codes(self, result: dict) -> list[str]:
        return [p["code"] for domain in result["domains"] for p in domain["problems"]]

    def test_23_untracked_media_not_ignored_fails(self):
        sandbox = self._build_sandbox()
        # Remove a regra que ignorava *.mp4/*.wav para simular midia solta.
        with open(os.path.join(sandbox, ".gitignore"), "w", encoding="utf-8") as handle:
            handle.write("*.mov\n")
        with open(os.path.join(sandbox, "solto.mp4"), "wb") as handle:
            handle.write(b"video")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "higiene_git")
        problemas = [p for p in dominio["problems"] if p["code"] == "MIDIA_NAO_IGNORADA"]
        self.assertEqual(len(problemas), 1)
        self.assertIn("solto.mp4", problemas[0]["message"])

    def test_24_tracked_snapshot_fails(self):
        sandbox = self._build_sandbox()
        rel = ".workspace/snapshots/workspace-snapshot-teste.zip"
        dest = os.path.join(sandbox, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as handle:
            handle.write(b"PK\x03\x04fake")
        _git(sandbox, "add", "-f", rel)
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "higiene_git")
        problemas = [p for p in dominio["problems"] if p["code"] == "SNAPSHOT_RASTREADO"]
        self.assertEqual(len(problemas), 1)
        self.assertIn(rel, problemas[0]["message"])

    def test_25_archive_hash_divergent_fails(self):
        sandbox = self._build_sandbox()
        target = self._seed_one_campaign_archives(sandbox)
        with open(os.path.join(target, "camp-saas-demo-marca-salao-001.mp4"), "ab") as handle:
            handle.write(b"CORROMPIDO")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        self.assertIn("ARCHIVE_HASH_DIVERGENTE", self._all_codes(result))
        message = " ".join(
            p["message"] for domain in result["domains"] for p in domain["problems"]
            if p["code"] == "ARCHIVE_HASH_DIVERGENTE"
        )
        self.assertIn("camp-saas-demo-marca-salao-001.mp4", message)

    def test_26_orphan_archive_media_fails(self):
        sandbox = self._build_sandbox()
        target = self._seed_one_campaign_archives(sandbox)
        with open(os.path.join(target, "orfao-local.mp4"), "wb") as handle:
            handle.write(b"sem manifesto")
        result = release_audit.run_release_audit(root=sandbox)
        self.assertFalse(result["ok"])
        dominio = self._find_domain(result, "higiene_git")
        problemas = [p for p in dominio["problems"] if p["code"] == "MIDIA_ORFA"]
        self.assertEqual(len(problemas), 1)
        self.assertIn("orfao-local.mp4", problemas[0]["message"])


if __name__ == "__main__":
    unittest.main()
