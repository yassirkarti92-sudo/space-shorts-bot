"""test_places.py - render ONE test video for a chosen subject. Never posts, never writes to the repo.
Usage: SUBJECT="What if gravity doubled overnight?" python -u test_places.py"""
import os
import sys

import render2
import script_gen2

subject = os.environ.get("SUBJECT", "").strip()
if not subject:
    sys.exit("SUBJECT is empty")

script_gen2.pick_subject = lambda: subject   # force the subject, subjects.csv is not touched
plan, tags, used_ai, _ = script_gen2.generate([])

n_place = sum(1 for p in plan if p["spec"].get("place"))
print(f"\nSCENES WITH A PLACE: {n_place} of {len(plan)}")
for i, p in enumerate(plan, 1):
    print(f"{i:2}. place={p['spec'].get('place')}  {p['caption']}")

narration, secs = None, None
try:
    import voice
    text = " ".join(p["narration"] for p in plan)
    narration, secs = voice.synthesize(text, "narration.wav")
    print("narration:", round(secs, 1), "seconds")
except Exception as e:
    print("voice failed:", e)

render2.render("pipeline_test_places.mp4", plan, narration=narration, narration_secs=secs)
print("done: pipeline_test_places.mp4 (nothing posted)")
