"""Execute the notebooks and export each to a standalone HTML page in docs/.

The notebooks are the analysis narrative (EDA + Bayesian A/B test), written in
plain English. Rendering them to HTML means anyone can read the work in a
browser without installing anything — and GitHub Pages can host them.

Usage:
    uv run python src/render_notebooks.py
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
OUT_DIR = ROOT / "docs"

NOTEBOOKS = [
    ("01_eda.ipynb", "First look at the data (EDA)",
     "Who the users are, where they drop off, and whether the experiment split was fair."),
    ("02_ab_test.ipynb", "Did the quiz help? (A/B test)",
     "The Bayesian result in plain English: how sure we are, the side effects, the money, and the recommendation."),
]


def render(nb_path: Path, save_outputs: bool = True) -> str:
    nb = nbformat.read(nb_path, as_version=4)
    ExecutePreprocessor(timeout=600, kernel_name="python3", allow_errors=False).preprocess(
        nb, {"metadata": {"path": str(NB_DIR)}}
    )
    if save_outputs:
        # Persist executed outputs back into the .ipynb so they also render on
        # GitHub (and match the HTML exactly).
        nbformat.write(nb, str(nb_path))
    body, _ = HTMLExporter(template_name="lab").from_notebook_node(nb)
    return body


def index_page() -> str:
    cards = "\n".join(
        f'      <a class="card" href="{name.replace(".ipynb", ".html")}">'
        f'<h3>{title}</h3><p>{desc}</p></a>'
        for name, title, desc in NOTEBOOKS
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KiwiSaver onboarding A/B test — notebooks</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
         background:#0f172a; color:#e2e8f0; }}
  main {{ max-width: 820px; margin: 0 auto; padding: 48px 24px; }}
  h1 {{ font-size: 28px; margin-bottom: 6px; }}
  .sub {{ color:#94a3b8; margin-bottom: 28px; }}
  .card {{ display:block; text-decoration:none; color:inherit; background:#1e293b;
          border:1px solid #334155; border-radius:12px; padding:18px 20px; margin:14px 0; }}
  .card:hover {{ border-color:#2dd4bf; }}
  .card h3 {{ margin:0 0 6px; color:#2dd4bf; }}
  .card p {{ margin:0; color:#94a3b8; font-size:14px; }}
  footer {{ color:#64748b; font-size:13px; margin-top:28px; }}
  a {{ color:#38bdf8; }}
</style></head>
<body><main>
  <h1>KiwiSaver onboarding A/B test</h1>
  <div class="sub">Executed notebooks — synthetic data, Bayesian analysis, plain English.</div>
{cards}
  <footer>
    Personal portfolio project; not affiliated with Sharesies. All data synthetic.<br>
    <a href="https://github.com/ciscoviva-dev/kiwisaver-onboarding-ab-test">View the repository</a>
  </footer>
</main></body></html>
"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for name, _title, _desc in NOTEBOOKS:
        nb_path = NB_DIR / name
        html = render(nb_path)
        (OUT_DIR / name.replace(".ipynb", ".html")).write_text(html, encoding="utf-8")
        print(f"rendered {name} -> docs/{name.replace('.ipynb', '.html')}")
    (OUT_DIR / "index.html").write_text(index_page(), encoding="utf-8")
    print("rendered index -> docs/index.html")


if __name__ == "__main__":
    main()
