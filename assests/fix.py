import json, sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding="utf-8").read()
for a, b in [("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'")]:
    t = t.replace(a, b)
d = json.loads(t)
json.dump(d, open(dst, "w", encoding="utf-8"), indent=1)
print("OK", len(d), "assets")
