"""Run once in the repo root: python patch_vector.py  (edits vector.py, keeps vector.py.bak)"""
import shutil
src = open("vector.py", encoding="utf-8").read()
shutil.copy("vector.py", "vector.py.bak")
R = [
 ("from PIL import Image, ImageDraw, ImageFilter, ImageFont\n",
  "from PIL import Image, ImageDraw, ImageFilter, ImageFont\n\nimport scenery\n"),
 ("MAX_ELEMENTS = 16\n",
  "MAX_ELEMENTS = 22\nMIN_ELEMENTS = 4\nTYPES = TYPES + scenery.TYPES\nNEEDS_SIZE = NEEDS_SIZE + scenery.NEEDS_SIZE\n"),
 ("        for e in els:\n            kind = e.get(\"type\")\n",
  "        if sum(1 for e in els if isinstance(e, dict) and e.get(\"type\") != \"timer\") < MIN_ELEMENTS:\n"
  "            return False, \"scene too empty\"\n        for e in els:\n            kind = e.get(\"type\")\n"),
 ("            if kind != \"timer\":\n", "            if kind not in (\"timer\", \"sky\", \"particles\"):\n"),
 ("            if kind == \"window\" and e.get(\"view\", \"stars\") not in VIEWS:\n",
  "            ok, why = scenery.check(e)\n            if not ok:\n                return False, why\n"
  "            if kind == \"window\" and e.get(\"view\", \"stars\") not in VIEWS:\n"),
 ("COLORS[e.get(\"head\", \"gray\")]",
  "COLORS[{\"skin\": \"gray\"}.get(e.get(\"head\", \"gray\"), e.get(\"head\", \"gray\"))]"),
 ("    sc = pop_scale(e, t)\n    if sc <= 0.02:\n        return\n    kind = e[\"type\"]\n",
  "    kind = e[\"type\"]\n    sc = 1.0 if kind in scenery.STATIC else pop_scale(e, t)\n    if sc <= 0.02:\n        return\n"
  "    if kind in scenery.TYPES:\n        x, y = (0, 0) if kind in (\"sky\", \"particles\") else place(e, t)\n"
  "        w = px(e.get(\"s\", 10)) * sc\n        h = px(e.get(\"h\", e.get(\"s\", 10))) * sc\n"
  "        scenery.draw(img, d, e, x, y, w, h, t)\n        return\n"),
]
for old, new in R:
    assert src.count(old) == 1, "pattern not found once: " + old[:50]
    src = src.replace(old, new)
open("vector.py", "w", encoding="utf-8").write(src)
print("vector.py patched")
