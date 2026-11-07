import render2

plan = [
    {"caption": "What if you woke up in *3026*?",
     "narration": "What if you woke up in the year three thousand twenty six? You open your eyes.",
     "sfx": [{"type": "swell", "at": 0}, {"type": "whoosh", "at": 1.5}],
     "spec": {"background": "navy", "camera": "push", "elements": [
         {"type": "figure", "x": 50, "y": 50, "s": 30, "eyes": "closed", "until": 1.6, "body": "cyan"},
         {"type": "figure", "x": 50, "y": 50, "s": 30, "eyes": "wide", "at": 1.6, "pop": False, "body": "cyan"},
         {"type": "pod", "x": 50, "y": 50, "s": 34},
         {"type": "badge", "x": 50, "y": 17, "text": "YEAR 3026", "at": 0.6}]}},
    {"caption": "The light is soft and *blue*.",
     "narration": "The light is soft and blue. The air smells like nothing at all.",
     "spec": {"background": "teal", "camera": "pull", "elements": [
         {"type": "window", "x": 50, "y": 36, "s": 72, "view": "city"},
         {"type": "figure", "x": 50, "y": 68, "s": 32, "eyes": "open", "bob": 0.6},
         {"type": "badge", "x": 50, "y": 14, "text": "DAY 1", "at": 0.3}]}},
    {"caption": "A voice says something you do not understand.",
     "narration": "A voice says something you do not understand.",
     "sfx": [{"type": "whoosh", "at": 0}],
     "spec": {"background": "dusk", "camera": "push", "elements": [
         {"type": "planet", "x": 72, "y": 26, "s": 22, "color": "purple", "ring": True},
         {"type": "skyline", "x": 50, "y": 82, "s": 34},
         {"type": "figure", "x": 30, "y": 66, "s": 30, "arm_up": True, "move_to": [42, 66], "move_time": 2.5}]}},
    {"caption": "Day *three*. The planet is quiet now.",
     "narration": "Day three. They tell you the planet is quiet now.",
     "sfx": [{"type": "boom", "at": 0.3}],
     "spec": {"background": "navy", "camera": "static", "elements": [
         {"type": "clock", "x": 50, "y": 40, "s": 46, "spin": 180},
         {"type": "badge", "x": 50, "y": 14, "text": "DAY 3", "color": "mint"}]}},
    {"caption": "You ask about your brother.",
     "narration": "Day ten. You ask about your brother, but he is only a story in a museum.",
     "spec": {"background": "slate", "camera": "push", "elements": [
         {"type": "figure", "x": 30, "y": 58, "s": 34, "eyes": "wide"},
         {"type": "figure", "x": 70, "y": 58, "s": 34, "body": "amber", "hair": "gray", "at": 1.2},
         {"type": "badge", "x": 50, "y": 15, "text": "DAY 10"}]}},
    {"caption": "You kept your promise. Would you?",
     "narration": "You kept your promise. There was just nobody left to keep it for. Would you?",
     "sfx": [{"type": "swell", "at": 0}],
     "spec": {"background": "void", "camera": "pull", "elements": [
         {"type": "planet", "x": 50, "y": 36, "s": 34, "color": "blue"},
         {"type": "figure", "x": 50, "y": 72, "s": 30, "eyes": "closed"}]}},
]

narration, secs = None, None
try:
    import voice
    text = " ".join(p["narration"] for p in plan)
    narration, secs = voice.synthesize(text, "narration.wav")
    print("narration:", round(secs, 1), "seconds")
except Exception as e:
    print("no narration, music and effects only:", e)

render2.render("story_test.mp4", plan, narration=narration, narration_secs=secs)
