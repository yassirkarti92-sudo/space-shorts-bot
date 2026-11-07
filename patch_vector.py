"""python patch_vector.py - edits vector.py (safe to run twice)."""
import re
src = open("vector.py", encoding="utf-8").read().replace("\r\n", "\n")
if "import scenery" in src:
    raise SystemExit("already patched")
open("vector.py.bak", "w", encoding="utf-8").write(src)


def sub(pattern, repl, label):
    global src
    new, n = re.subn(pattern, lambda m: repl.replace("@@", m.group(0)), src, count=1, flags=re.M)
    if n != 1:
        print("MISSING:", label)
        print("\n".join(l for l in src.split("\n") if label.split()[0] in l)[:600])
        raise SystemExit(1)
    src = new


sub(r"^from PIL import .*$", "@@\n\nimport scenery", "from PIL")
sub(r"^MAX_ELEMENTS\s*=.*$",
    "MAX_ELEMENTS = 22\nMIN_ELEMENTS = 4\nTYPES = tuple(TYPES) + scenery.TYPES\nNEEDS_SIZE = tuple(NEEDS_SIZE) + scenery.NEEDS_SIZE",
    "MAX_ELEMENTS")
sub(r"^( +)for e in els:\n",
    "@@".replace("@@", "") + "        if sum(1 for e in els if isinstance(e, dict) and e.get(\"type\") != \"timer\") < MIN_ELEMENTS:\n"
    "            return False, \"scene too empty\"\n@@", "for e in els")
sub(r"^( +)if kind != \"timer\":$", "            if kind not in (\"timer\", \"sky\", \"particles\"):", "if kind != timer")
sub(r"^( +)if kind == \"window\" and .*$",
    "            ok, why = scenery.check(e)\n            if not ok:\n                return False, why\n@@", "if kind == window")
sub(r"COLORS\[e\.get\(\"head\", \"gray\"\)\]",
    "COLORS[{\"skin\": \"gray\"}.get(e.get(\"head\", \"gray\"), e.get(\"head\", \"gray\"))]", "COLORS[e.get head")
sub(r"^    sc = pop_scale\(e, t\)\n    if sc <= 0\.02:\n        return\n    kind = e\[\"type\"\]$",
    "    kind = e[\"type\"]\n    sc = 1.0 if kind in scenery.STATIC else pop_scale(e, t)\n    if sc <= 0.02:\n        return\n"
    "    if kind in scenery.TYPES:\n        x, y = (0, 0) if kind in (\"sky\", \"particles\") else place(e, t)\n"
    "        w = px(e.get(\"s\", 10)) * sc\n        h = px(e.get(\"h\", e.get(\"s\", 10))) * sc\n"
    "        scenery.draw(img, d, e, x, y, w, h, t)\n        return", "sc = pop_scale")
open("vector.py", "w", encoding="utf-8").write(src)
print("vector.py patched")
