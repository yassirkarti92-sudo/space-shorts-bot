"""ping_gemini.py - finds out why Gemini text requests time out. Posts nothing, renders nothing."""
import json
import os
import time
import urllib.error
import urllib.request

KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.8-flash")
BASE = "https://generativelanguage.googleapis.com/v1beta"


def call(url, body=None, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body else None,
        headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r), time.time() - t0
    except urllib.error.HTTPError as e:
        return {"HTTP_ERROR": e.code, "body": e.read().decode()[:400]}, time.time() - t0
    except Exception as e:
        return {"ERROR": str(e)}, time.time() - t0


print("1) Models that can generate text (names with 'flash' or 'gemini'):")
res, secs = call(BASE + "/models?pageSize=200")
for m in res.get("models", []):
    if "generateContent" in m.get("supportedGenerationMethods", []) and "tts" not in m["name"]:
        print("  ", m["name"].replace("models/", ""))
if "ERROR" in res or "HTTP_ERROR" in res:
    print("  list failed:", res)
print(f"   ({secs:.1f}s)\n")

print(f"2) Tiny request to {MODEL}:")
body = {"contents": [{"role": "user", "parts": [{"text": "Reply with the single word: ok"}]}]}
res, secs = call(f"{BASE}/models/{MODEL}:generateContent", body)
print(f"   {secs:.1f}s ->", json.dumps(res)[:600], "\n")

print(f"3) Small JSON request to {MODEL}:")
body = {"contents": [{"role": "user", "parts": [{"text": 'Write JSON: {"scenes": [3 short sentences about the ocean]}'}]}],
        "generationConfig": {"responseMimeType": "application/json"}}
res, secs = call(f"{BASE}/models/{MODEL}:generateContent", body)
print(f"   {secs:.1f}s ->", json.dumps(res)[:900])
