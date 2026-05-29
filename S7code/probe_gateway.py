"""Quick test: try each provider directly via the gateway and report which works."""
import httpx, sys, os
sys.stdout.reconfigure(encoding='utf-8')

GATEWAY = "http://localhost:8107"
MINI_PROMPT = [{"role": "user", "content": "Say OK in one word."}]

def test_chat(provider=None, model=None):
    payload = {"messages": MINI_PROMPT, "max_tokens": 10}
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    try:
        r = httpx.post(f"{GATEWAY}/v1/chat", json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            text = data.get("content", data.get("choices", [{}])[0].get("message", {}).get("content", "?"))
            prov = data.get("provider", "?")
            mod  = data.get("model", "?")
            return True, f"OK  provider={prov}  model={mod}  reply={str(text)[:40]!r}"
        else:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"Exception: {e}"

print("=" * 65)
print("Gateway provider probe")
print("=" * 65)

# 1. Default routing (let gateway choose)
ok, msg = test_chat()
print(f"\n[default routing]  {msg}")

# 2. Force each provider
for prov in ["groq", "gemini", "nvidia", "cerebras", "github", "openrouter"]:
    ok, msg = test_chat(provider=prov)
    status = "PASS" if ok else "FAIL"
    print(f"[{prov:<12}]  {status}  {msg}")

print("\n" + "=" * 65)
