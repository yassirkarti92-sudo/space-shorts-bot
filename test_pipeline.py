"""test_pipeline.py - Gemini script -> Gemini voice -> render2. Posts nothing.
Uses a RANDOM subject each time, so test videos are different (the real bot goes through the list in order)."""
import json
import random

import render2
import script_gen2

script_gen2.pick_subject = lambda: random.choice(script_gen2._read_subjects())

plan, tags, _, subject = script_gen2.generate([])
with open("pipeline_script.json", "w", encoding="utf-8") as f:
    json.dump({"subject": subject, "hashtags": tags, "plan": plan}, f, indent=2, ensure_ascii=False)

narration, secs = None, None
try:
    import voice
    text = " ".join(p["narration"] for p in plan)
    narration, secs = voice.synthesize(text, "narration.wav")
    print("narration:", round(secs, 1), "seconds")
except Exception as e:
    print("no narration, music and effects only:", e)

render2.render("pipeline_test.mp4", plan, narration=narration, narration_secs=secs)
