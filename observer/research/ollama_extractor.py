"""Optional Ollama-backed extractor.

Law (docs/SPEC.md + CHARTER.md): this stays UNAVAILABLE unless OLLAMA_MODEL is
configured AND Ollama is actually reachable and answers. No simulated output.
The heuristic extractor remains the primary; this only refines/adds.
"""

from __future__ import annotations

import json
import os
import urllib.request

from observer.extractors import html_to_text

OLLAMA_HOST = "http://127.0.0.1:11434"
PROBE_TIMEOUT = 3
EXTRACT_TIMEOUT = 120


def configured_model() -> str | None:
    model = (os.environ.get("OLLAMA_MODEL") or "").strip()
    return model or None


def _ollama_chat(model: str, prompt: str, num_predict: int = 400) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "keep_alive": "5m",
        "options": {"num_ctx": 4096, "temperature": 0.1, "num_predict": num_predict},
    }
    req = urllib.request.Request(
        OLLAMA_HOST + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=EXTRACT_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return (data.get("message") or {}).get("content", "").strip()


def probe() -> dict:
    """Live probe: CONFIGURED+REACHABLE only if Ollama truly answers this model."""
    model = configured_model()
    if not model:
        return {"status": "UNAVAILABLE", "reason": "OLLAMA_MODEL unset", "adapter": "NOT CONFIGURED"}
    try:
        req = urllib.request.Request(
            OLLAMA_HOST + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            tags = json.loads(resp.read())
        names = [m.get("name", "") for m in tags.get("models", [])]
        if not any(n == model or n.split(":")[0] == model.split(":")[0] for n in names):
            return {"status": "UNAVAILABLE", "reason": f"model {model!r} not in Ollama store",
                    "adapter": "CONFIGURED"}
        # real generation probe - the only honest proof
        reply = _ollama_chat(model, 'Reply with exactly: PROBE-OK', num_predict=10)
        if "PROBE-OK" not in reply.upper():
            return {"status": "UNAVAILABLE", "reason": "live probe returned unexpected output",
                    "adapter": "CONFIGURED"}
        return {"status": "CONNECTED", "reason": f"live probe OK (model {model})",
                "adapter": "CONFIGURED", "last_verified": "this probe"}
    except Exception as exc:
        return {"status": "UNAVAILABLE", "reason": f"ollama unreachable or failed: {exc}",
                "adapter": "CONFIGURED"}


def availability() -> dict:
    return probe()


def extract_claims(html: str, url: str) -> dict:
    """LLM-assisted claim extraction. Falls back honest: raises nothing, reports status.

    Returns {"status": ..., "model": ..., "claims": [...], "limitations": ...}
    Claims are SUGGESTIONS from a model - each arrives UNVERIFIED and carries
    provenance that it was machine-proposed (per epistemic standard).
    """
    model = configured_model()
    if not model:
        return {"status": "UNAVAILABLE", "model": None, "claims": [],
                "limitations": "OLLAMA_MODEL unset"}
    text = html_to_text(html)[:6000]
    if not text:
        return {"status": "NOT_FOUND", "model": model, "claims": [],
                "limitations": "no readable text"}
    prompt = (
        "You are a claim-extraction assistant for an investigative ledger.\n"
        "From the TEXT below, extract up to 6 atomic factual claims the document "
        "asserts. One per line, prefix each with 'CLAIM: '. No commentary.\n\n"
        f"SOURCE_URL: {url}\nTEXT:\n{text}\n"
    )
    try:
        reply = _ollama_chat(model, prompt, num_predict=400)
    except Exception as exc:
        return {"status": "SOURCE_UNAVAILABLE", "model": model, "claims": [],
                "limitations": f"ollama call failed: {exc}"}
    claims = []
    for line in reply.splitlines():
        line = line.strip()
        if line.upper().startswith("CLAIM:"):
            body = line[6:].strip()
            if body:
                claims.append({
                    "text": body[:400],
                    "status": "UNVERIFIED",
                    "provenance": f"machine-proposed by local ollama:{model}; human/ledger review required",
                })
    status = "CONNECTED" if claims else "NOT_FOUND"
    return {
        "status": status,
        "model": model,
        "claims": claims,
        "limitations": "Model-proposed claims are UNVERIFIED by epistemic law; "
                       "heuristic extractor remains primary.",
    }
