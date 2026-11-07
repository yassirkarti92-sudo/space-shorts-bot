import render

plan = [
    {"scene": "custom", "caption": "If the Sun exploded, you would not know for eight minutes.",
     "sfx": [{"type": "whoosh", "at": 0}, {"type": "boom", "at": 3.0}],
     "spec": {"background": "space", "label": "THE SUN", "elements": [
         {"type": "disc", "x": 67, "y": 105, "r": 4, "grow_to": 16, "grow_time": 2.0, "color": "yellow", "until": 3.0},
         {"type": "disc", "x": 67, "y": 105, "r": 3, "color": "blue", "at": 0.5, "until": 3.3,
          "orbit": {"cx": 67, "cy": 105, "radius": 40, "period": 5}},
         {"type": "explosion", "x": 67, "y": 105, "r": 45, "at": 3.0}]}},
    {"scene": "custom", "caption": "If you want a taller building, you add more floors.",
     "sfx": [{"type": "swell", "at": 0}, {"type": "boom", "at": 2.0}],
     "spec": {"background": "sky", "label": "", "elements": [
         {"type": "rect", "x": 40, "y": 170, "w": 55, "h": 8, "color": "green"},
         {"type": "rect", "x": 50, "y": 100, "w": 35, "h": 70, "color": "gray"},
         {"type": "rect", "x": 50, "y": 65, "w": 35, "h": 35, "color": "gray", "at": 2.0, "shake": 1}]}},
]

narration = None
try:
    import voice
    text = " ".join(p["caption"] for p in plan)
    narration, secs = voice.synthesize(text, "narration.wav")
    print("narration:", round(secs, 1), "seconds")
except Exception as e:
    print("no narration, music and effects only:", e)

render.render("scene_test.mp4", plan, narration=narration)
