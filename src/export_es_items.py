"""Export the Spanish report content (same text/numbers as the PDF) to JSON for the Word builder."""
import json, re
from pathlib import Path
from PIL import Image as PILImage

HERE = Path(__file__).resolve().parent
src = (HERE / "10_build_report_es.py").read_text()
m1 = src.index("# ----------------------------------------------------------------------------- traducciones de etiquetas")
m2 = src.index("# ----------------------------------------------------------------------------- document")
ns = {"__file__": str(HERE / "10_build_report_es.py")}
exec(compile(src[:m1], "head", "exec"), ns)          # fonts, styles, data, helpers (reportlab objects only)
items, cnt = [], {"fig": 0, "tab": 0}
FIG = ns["FIG"]
ROM = ns["ROM"]
class Rec(list):
    def append(self, o):
        n = type(o).__name__
        if "FrameBreak" in n: items.append({"t": "framebreak"})
        elif n == "Paragraph" and o.style.name == "ref": items.append({"t": "ref", "text": o.text})
ns["S"] = Rec()
def P(t, st=None): items.append({"t": "p", "style": (st.name if st is not None else "body"), "text": t})
def H1(t): items.append({"t": "h1", "text": t})
def H2(t): items.append({"t": "h2", "text": t})
def B(t): items.append({"t": "bullet", "text": t})
def fig(name, caption, w=3.4):
    cnt["fig"] += 1
    im = PILImage.open(FIG / name)
    items.append({"t": "fig", "path": str(FIG / name), "w": w, "h": w * im.height / im.width, "caption": f"Fig. {cnt['fig']}. {caption}"})
def table(caption, rows, widths, hdr=1, **k):
    cnt["tab"] += 1
    items.append({"t": "table", "title": f"TABLA {ROM[cnt['tab']]}", "caption": caption.upper(), "rows": [[str(c) for c in r] for r in rows], "widths": widths})
ns.update(P=P, H1=H1, H2=H2, B=B, fig=fig, table=table)
exec(compile(src[m1:m2], "body", "exec"), ns)
Path(HERE.parent / "reports/es_items.json").write_text(json.dumps(items, ensure_ascii=False))
print(len(items), "items;", cnt)
