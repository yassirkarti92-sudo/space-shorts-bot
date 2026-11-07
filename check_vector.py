import vector, script_gen2
print("TYPES", vector.TYPES)
print("MIN", getattr(vector, "MIN_ELEMENTS", None), "MAX", vector.MAX_ELEMENTS)
print("CAMERAS", vector.CAMERAS)
spec = {"background": "navy", "camera": "push", "elements": [
    {"type": "sky", "style": "night"},
    {"type": "ground", "style": "rock", "x": 50, "y": 75, "s": 100},
    {"type": "figure", "x": 50, "y": 55, "s": 45, "act": "walk"},
    {"type": "icon", "icon": "flame", "x": 70, "y": 30, "s": 14},
    {"type": "badge", "x": 50, "y": 15, "text": "DAY 1"}]}
print("check:", vector.check_scene(spec))
r = script_gen2.repair_spec(spec)
print("repaired elements:", len(r["elements"]), vector.check_scene(r))
vector.render_scene(r, 1.0, 4).save("check.png")
print("render ok")
