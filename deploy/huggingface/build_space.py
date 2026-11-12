"""Stage the static Hugging Face Space from the GitHub Pages demo.

    python deploy/huggingface/build_space.py [out_dir]   # default: space/

The Space serves a copy of demo/public (index.html, runs.json, metrics.json):
recorded real runs, no backend, no model, no LLM. The copy gets a banner
with links to the repository and the Pages demo; demo/public itself is
never modified. The Space README (front matter) comes from
deploy/huggingface/README.md.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "demo" / "public"
HERE = Path(__file__).resolve().parent
FILES = ["index.html", "runs.json", "metrics.json"]
ANCHOR = '<div class="wrap">'
HEAD = "<head>"
# Hugging Face shows a Space inside its own frame; sites such as github.com
# refuse to load in a frame, so every link on the Space opens a new tab.
BASE = '<head>\n<base target="_blank">'

BANNER = """<div class="wrap">
  <div style="border:1px solid var(--accent);border-radius:12px;padding:10px 12px;margin-bottom:16px;font-size:14px;line-height:1.45">
    <b>Recorded real runs from 24 open-source repos. Dry-run only.</b><br>
    <a href="https://github.com/SreyaThota/pipeline-medic">GitHub repo</a> ·
    <a href="https://sreyathota.github.io/pipeline-medic/">Main demo (GitHub Pages)</a>
  </div>"""


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in FILES:
        shutil.copyfile(PUBLIC / name, out / name)
    page = (out / "index.html").read_text(encoding="utf-8")
    if page.count(ANCHOR) != 1:
        raise SystemExit(f"expected one {ANCHOR!r} in demo/public/index.html")
    if page.count(HEAD) != 1:
        raise SystemExit("expected one <head> in demo/public/index.html")
    page = page.replace(HEAD, BASE, 1).replace(ANCHOR, BANNER, 1)
    (out / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(HERE / "README.md", out / "README.md")
    shutil.copyfile(ROOT / "LICENSE", out / "LICENSE")
    print(f"staged {sorted(p.name for p in out.iterdir())} in {out}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "space")
