"""main2.py - new pipeline: script_gen2 (Gemini) -> voice -> render2 -> Cloudinary -> Buffer."""
import json, os, pathlib, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
import render2, script_gen2

OUT = pathlib.Path("out/space.mp4")
HIST = pathlib.Path("history.json")
FOLDER, KEEP_DAYS = "space", 2

hist = json.loads(HIST.read_text()) if HIST.exists() else []
plan, tags, used_ai, subject = script_gen2.generate(hist)
OUT.parent.mkdir(exist_ok=True)

narration, secs = None, None
try:
    import voice
    text = " ".join(p["narration"] for p in plan)
    narration, secs = voice.synthesize(text, "narration.wav")
    print("narration:", round(secs, 1), "seconds")
except Exception as e:
    print("voice failed:", e)

render2.render(str(OUT), plan, narration=narration, narration_secs=secs)

if narration is None:
    print("No voice: video not posted.")
    sys.exit(0)
if not (used_ai and os.getenv("BUFFER_KEY") and os.getenv("CHANNEL_ID")):
    print("Render only (missing secrets). Nothing posted.")
    sys.exit(0)

import cloudinary, cloudinary.uploader, cloudinary.api
if not os.getenv("CLOUDINARY_URL"):
    cloudinary.config(cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
                      api_key=os.environ["CLOUDINARY_API_KEY"],
                      api_secret=os.environ["CLOUDINARY_API_SECRET"], secure=True)

up = cloudinary.uploader.upload(str(OUT), resource_type="video", folder=FOLDER)
text = plan[0]["caption"].replace("*", "") + "\n\n" + " ".join(tags)
query = f"""
mutation CreatePost {{
  createPost(input: {{
    text: {json.dumps(text)}
    channelId: {json.dumps(os.environ["CHANNEL_ID"])}
    schedulingType: automatic
    mode: shareNow
    assets: [ {{ video: {{ url: {json.dumps(up["secure_url"])} }} }} ]
  }}) {{
    ... on PostActionSuccess {{ post {{ id dueAt }} }}
    ... on MutationError {{ message }}
  }}
}}"""
req = urllib.request.Request(
    "https://api.buffer.com", data=json.dumps({"query": query}).encode(),
    headers={"Authorization": "Bearer " + os.environ["BUFFER_KEY"], "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
except urllib.error.HTTPError as e:
    raise SystemExit(f"Buffer HTTP {e.code}: {e.read().decode()[:400]}")
post = (res.get("data") or {}).get("createPost", {})
if res.get("errors") or not post.get("post"):
    raise SystemExit("Buffer failed: " + str(res.get("errors") or post.get("message")))
print("Posted. id:", post["post"]["id"])

script_gen2.mark_used(subject)
hist += [s["caption"] for s in plan]
HIST.write_text(json.dumps(hist[-60:], indent=2))

try:  # delete old Cloudinary videos, never fail the run
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    res = cloudinary.api.resources(resource_type="video", type="upload",
                                   prefix=FOLDER + "/", max_results=500)
    old = [i["public_id"] for i in res.get("resources", [])
           if datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")) < cutoff]
    if old:
        cloudinary.api.delete_resources(old[:100], resource_type="video", type="upload")
    print("Cloudinary cleanup:", len(old))
except Exception as e:
    print("cleanup skipped:", str(e)[:150])
