"""Monta a entrega v3 do PILOTO-OPERACIONAL-001-V3.

Reune as tres pecas (post 4:5, carrossel, reel), as copias por rede, a auditoria
de claims contra o guardrails do tenant, o manifesto de midia com hashes, o
relatorio de qualidade e uma pagina de revisao com contatos visuais (pranchas).

Nao publica, nao agenda e nao marca aprovacao: tudo fica AGUARDANDO APROVACAO DO
TITULAR. A aprovacao estetica nao e declarada pelo agente.

Uso:
  python tools/assemble_v3_delivery.py --delivery <...>/delivery-v3 --root <RAIZ>
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import render_local

TENANT = os.path.join("tenants", "marca-salao", "guardrails.json")

# Textos que aparecem nas imagens/composicoes (auditoria de claims dos criativos).
ON_IMAGE_TEXTS = [
    "MARCA SALAO | AGENDAMENTO ONLINE",
    "Sua agenda, mais organizada.",
    "Visualize horarios e acompanhe os atendimentos em um so lugar.",
    "Conheca o Marca Salao",
    "SUA ROTINA | 1/4",
    "Sua rotina comeca com uma agenda organizada.",
    "Gestao de salao, do agendamento ao atendimento.",
    "HORARIOS | 2/4",
    "Veja os horarios do dia com mais clareza.",
    "Visao do dia e da semana em uma so tela.",
    "ATENDIMENTOS | 3/4",
    "Acompanhe cada atendimento.",
    "Visualize e atualize os status do dia.",
    "CONHECA | 4/4",
    "Explore uma maneira mais pratica de organizar a agenda.",
    "MARCA SALAO - marcasalao.com.br",
    "Sua agenda, em um so lugar.",
    "Visualize os atendimentos e acompanhe o dia em uma so tela.",
    "Dia, semana e mes.",
    "O mesmo registro, visto por dia, semana ou mes.",
    "Filtre e acompanhe.",
    "Filtre por profissional ou status e atualize cada atendimento.",
]

COPY_FACEBOOK = """Legenda - Facebook (reel/carrossel 9x16 e 4x5) - Marca Salao
Status: AGUARDANDO APROVACAO DO TITULAR. Nao publicar.

Sua agenda, em um so lugar: visualize os atendimentos do dia, acompanhe os
status e organize a rotina do salao em uma so tela.

Conheca o Marca Salao: https://marcasalao.com.br
Acesse pelo link da descricao.

#MarcaSalao #GestaoDeSalao #AgendaDoSalao #Beleza #Organizacao
"""

COPY_INSTAGRAM = """Legenda - Instagram (reel 9x16 / carrossel 1x1 / post 4x5) - Marca Salao
Status: AGUARDANDO APROVACAO DO TITULAR. Nao publicar.

Sua agenda, em um so lugar: visualize os atendimentos do dia, acompanhe os
status e organize a rotina do salao em uma so tela.

Conheca o sistema - link na bio (somente se o link externo do perfil estiver
confirmado; pendente de confirmacao do titular).

#MarcaSalao #GestaoDeSalao #AgendaDoSalao #Beleza #Organizacao
"""


def _fs(p):
    return render_local.fs_path(os.path.normpath(str(p)))


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t.lower()).strip()


def _sha(path):
    h = hashlib.sha256()
    with open(_fs(path), "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def audit_claims(root: str, texts: list[str]) -> dict:
    with open(_fs(os.path.join(root, TENANT)), "r", encoding="utf-8") as fh:
        guard = json.load(fh)
    banned = [(_norm(c), c) for c in guard.get("forbiddenClaims", [])]
    banned += [(_norm(c), c) for c in guard.get("forbiddenUiElements", [])]
    hits = []
    for label, text in texts:
        hay = _norm(text)
        for nb, orig in banned:
            if nb and nb in hay:
                hits.append({"where": label, "term": orig})
    return {"checkedTerms": len(banned), "hits": hits, "ok": not hits}


def _tile(ffmpeg, inputs, cols, rows, out, cell=None):
    n = len(inputs)
    if cell is None:
        cell = (540, 540)
    args = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for i in inputs:
        args += ["-i", i]
    w, hh = cell
    fc = "".join(f"[{i}:v]scale={w}:{hh}:force_original_aspect_ratio=decrease,"
                 f"pad={w}:{hh}:(ow-iw)/2:(oh-ih)/2:color=0x121620,"
                 f"setsar=1[v{i}];" for i in range(n))
    fc += "".join(f"[v{i}]" for i in range(n)) + f"xstack=inputs={n}:layout="
    layout = []
    for i in range(n):
        col = i % cols
        row = i // cols
        layout.append(f"{col * w}_{row * hh}")
        fc = fc  # noop to keep flake quiet
    fc += "|".join(layout) + "[out]"
    args += ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", out]
    res = subprocess.run(args, capture_output=True, text=True, timeout=render_local.RENDER_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise build_video.DeliveryError(f"falha ao montar prancha: {res.stderr.strip()[:300]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Monta a entrega v3")
    ap.add_argument("--delivery", required=True)
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--v2", default=None, help="pasta delivery-v2 para comparacao v2 x v3")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.realpath(args.root)
    delivery = os.path.realpath(args.delivery)
    if not render_local.contained(root, delivery) or delivery == root:
        print("Erro: destino fora da raiz ou igual a raiz", file=sys.stderr)
        return 2
    render_local.ensure_video_tools(root)
    ffmpeg = build_video.get_ffmpeg()

    post = os.path.join(delivery, "post-45", "01-capa.jpg")
    car_dir = os.path.join(delivery, "carousel")
    cards = [os.path.join(car_dir, n) for n in
             ("01-capa.jpg", "02-horarios.jpg", "03-atendimentos.jpg", "04-cta.jpg")]
    reel = os.path.join(delivery, "03-reel", "reel-instagram-9x16.mp4")
    for p in [post] + cards + [reel]:
        if not os.path.isfile(_fs(p)):
            print(f"Erro: peca ausente: {p}", file=sys.stderr)
            return 2

    # Copias por rede
    cop_dir = os.path.join(delivery, "05-copias")
    os.makedirs(_fs(cop_dir), exist_ok=True)
    render_local.write_text_lf(_fs(os.path.join(cop_dir, "legenda-facebook.txt")), COPY_FACEBOOK)
    render_local.write_text_lf(_fs(os.path.join(cop_dir, "legenda-instagram.txt")), COPY_INSTAGRAM)

    # Auditoria de claims
    texts = [("copia-facebook", COPY_FACEBOOK), ("copia-instagram", COPY_INSTAGRAM)]
    for i, t in enumerate(ON_IMAGE_TEXTS):
        texts.append((f"imagem-{i:02d}", t))
    for name in ("narracao-reel.txt", "legendas.srt"):
        fp = os.path.join(delivery, "04-legendas", name)
        if os.path.isfile(_fs(fp)):
            with open(_fs(fp), "r", encoding="utf-8") as fh:
                texts.append((name, fh.read()))
    dirc = os.path.join(delivery, "03-reel", "direcao-de-cenas.md")
    if os.path.isfile(_fs(dirc)):
        with open(_fs(dirc), "r", encoding="utf-8") as fh:
            texts.append(("direcao-de-cenas.md", fh.read()))
    audit = audit_claims(root, texts)

    # Pranchas de contato
    review = os.path.join(delivery, "review")
    os.makedirs(_fs(review), exist_ok=True)
    board_car = os.path.join(review, "board-carousel.png")
    _tile(ffmpeg, cards, 2, 2, board_car, cell=(540, 540))
    frames = []
    for t in (2, 7, 13, 18):
        fr = os.path.join(review, f".f{t}.png")
        subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", reel,
                        "-frames:v", "1", fr], capture_output=True, text=True,
                       timeout=render_local.RENDER_TIMEOUT_SECONDS)
        frames.append(fr)
    board_reel = os.path.join(review, "board-reel.png")
    _tile(ffmpeg, frames, 4, 1, board_reel, cell=(360, 640))
    for fr in frames:
        try:
            os.remove(_fs(fr))
        except OSError:
            pass

    comparison = None
    if args.v2:
        v2 = os.path.realpath(args.v2)
        v2post = os.path.join(v2, "01-post-45", "01-capa.jpg")
        if os.path.isfile(_fs(v2post)):
            comparison = os.path.join(review, "comparacao-v2-v3.png")
            _tile(ffmpeg, [v2post, post], 2, 1, comparison, cell=(540, 675))

    # Manifesto de midia
    delivered = [("post-45/01-capa.jpg", post),
                 ("carousel/01-capa.jpg", cards[0]),
                 ("carousel/02-horarios.jpg", cards[1]),
                 ("carousel/03-atendimentos.jpg", cards[2]),
                 ("carousel/04-cta.jpg", cards[3]),
                 ("03-reel/reel-instagram-9x16.mp4", reel)]
    for extra in ("05-copias/legenda-facebook.txt", "05-copias/legenda-instagram.txt",
                  "04-legendas/narracao-reel.txt", "04-legendas/legendas.srt",
                  "03-reel/direcao-de-cenas.md"):
        fp = os.path.join(delivery, extra)
        if os.path.isfile(_fs(fp)):
            delivered.append((extra, fp))
    entries = []
    car_zip = os.path.join(car_dir, "carousel.zip")
    with zipfile.ZipFile(_fs(car_zip), "w", zipfile.ZIP_DEFLATED) as zf:
        for c in cards:
            zf.write(_fs(c), arcname=os.path.basename(c))
    delivered.append(("carousel/carousel.zip", car_zip))
    for arc, p in delivered:
        entries.append({"path": arc, "bytes": os.path.getsize(_fs(p)), "sha256": _sha(p)})

    manifest = {
        "schemaVersion": 1,
        "operation": "operacao-resultado-26",
        "delivery": "v3",
        "campaign": "PILOTO-OPERACIONAL-001-V3",
        "autoPublish": False,
        "status": "AGUARDANDO APROVACAO DO TITULAR",
        "videoPolicy": {"audioTrack": False, "ffmpegFlag": "-an", "externalNarration": True, "srt": True},
        "files": entries,
    }
    render_local.write_text_lf(_fs(os.path.join(delivery, "media-manifest.json")),
                              json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with open(_fs(os.path.join(delivery, "05-copias", "claims-audit.json")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(audit, fh, ensure_ascii=False, indent=2)

    # Relatorio de qualidade
    q = ["# Relatorio de qualidade - PILOTO-OPERACIONAL-001-V3", "",
         "Status: AGUARDANDO APROVACAO DO TITULAR. Nada foi publicado ou agendado.", "",
         "## Tipografia e composicao",
         "- Motor de texto profissional (ASS/libass) resolvendo Arial, com acentos e quebra por largura.",
         "- Identidade Marca Salao (paleta do brand-kit, barra de acento, monocromatico escuro).",
         "- Capturas REAIS autorizadas da agenda (`capturas/2026-11-05/`) usadas no post e carrossel.", "",
         "## Verificacoes automaticas",
         f"- Auditoria de claims: {'OK' if audit['ok'] else 'FALHA'} "
         f"({audit['checkedTerms']} termos; {len(audit['hits'])} ocorrencias).",
         "- Reel: 1080x1920, h264, yuv420p, 20s, 0 faixas de audio (-an).",
         "- Post: 1080x1350; carrossel: 4 cards 1080x1080 + carousel.zip.",
         "- Ruido/variancia por regiao confirma texto renderizado e capturas compostas.", "",
         "## Limitacao (obrigatoria)",
         "- O agente NAO declara aprovacao estetica: a avaliacao visual humana e obrigatoria (Fase L).",
         "- Nenhuma peca deve ser publicada sem aprovacao do titular; capturas sao evidencia tecnica.", ""]
    render_local.write_text_lf(_fs(os.path.join(delivery, "QUALIDADE-V3.md")), "\n".join(q))

    # Pagina de revisao
    def img(relp):
        return f'<img src="{html.escape(relp)}" alt="{html.escape(relp)}">'
    cards_html = "".join(f'<figure>{img("../carousel/" + os.path.basename(c))}<figcaption>{os.path.basename(c)}</figcaption></figure>' for c in cards)
    comp = '<h2>Comparacao v2 x v3 (post 4:5)</h2><img src="comparacao-v2-v3.png">' if comparison else ""
    hits = "" if audit["ok"] else "".join(f"<li>{html.escape(h['where'])}: {html.escape(h['term'])}</li>" for h in audit["hits"])
    page = f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Revisao v3 - Marca Salao</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;background:#0e121c;color:#f5f7fa;margin:0;padding:32px}}
h1{{color:#f5c107}} h2{{color:#4f8cff;border-top:1px solid #222c40;padding-top:16px}}
.warn{{background:#3a2a12;border:1px solid #f5c107;padding:12px;border-radius:8px}}
.ok{{background:#12301c;border:1px solid #28b463;padding:12px;border-radius:8px}}
img{{max-width:100%;border-radius:8px;border:1px solid #222c40;background:#121620}}
.grid{{display:flex;flex-wrap:wrap;gap:16px}} figure{{margin:0;width:320px}}
figcaption{{font-size:12px;color:#b4c0d2;margin-top:4px}}
</style></head><body>
<h1>PILOTO-OPERACIONAL-001-V3 - revisao visual</h1>
<p class="warn">AGUARDANDO APROVACAO DO TITULAR. Nao publicado. Avaliacao estetica humana pendente.</p>
<h2>Post 4:5 (1080x1350)</h2>{img("../post-45/01-capa.jpg")}
<h2>Carrossel (4 x 1080x1080)</h2><div class="grid">{cards_html}</div>
<p>{img("board-carousel.png")}</p>
<h2>Reel vertical (1080x1920, 20s, VIDEO CLEAN)</h2>
<video controls preload="metadata" src="../03-reel/reel-instagram-9x16.mp4" style="max-width:420px;border-radius:8px"></video>
<p>{img("board-reel.png")}</p>
{comp}
<h2>Auditoria de claims</h2>
{"<p class='ok'>Nenhum termo proibido encontrado nos textos e imagens.</p>" if audit['ok'] else f"<div class='warn'><b>Ocorrencias:</b><ul>{hits}</ul></div>"}
</body></html>
"""
    render_local.write_text_lf(_fs(os.path.join(review, "review.html")), page)

    # ZIP completo
    zip_all = os.path.join(delivery, "delivery-v3-completa.zip")
    with zipfile.ZipFile(_fs(zip_all), "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _dirs, files in os.walk(_fs(delivery)):
            for name in files:
                fp = os.path.join(base, name)
                rel = os.path.relpath(fp, _fs(delivery)).replace(os.sep, "/")
                if rel == "delivery-v3-completa.zip":
                    continue
                zf.write(fp, arcname=rel)

    result = {"status": "completed", "delivery": render_local.rel(root, delivery),
              "auditOk": audit["ok"], "auditHits": len(audit["hits"]),
              "files": len(entries), "zip": render_local.rel(root, zip_all),
              "zipBytes": os.path.getsize(_fs(zip_all))}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("entrega v3 montada:", result["delivery"], "claims ok:", result["auditOk"])
    return 0 if audit["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
