"""Run inside the Open WebUI container; no third-party Python libraries required.

Tests input processing and a 128K configured context, not a 100K output.
No real credentials, network targets, or customer data are included.
"""

import json
import sys
import time
import urllib.request

BASE_URL = "http://ollama:11434"
MODEL = "redteam-qwen35-128k"
CONTEXT = 131072


def post(path, payload):
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=14400) as response:
        return json.load(response)


def probe(lines):
    records = "\n".join(
        f"Record {i:06d}: lab asset alpha, service status unknown, no evidence collected."
        for i in range(lines)
    )
    prompt = (
        "Read these synthetic records. Reply with one short sentence about their "
        "common status. Do not reproduce the records.\n" + records
    )
    started = time.monotonic()
    result = post(
        "/api/chat",
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "think": False,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "num_ctx": CONTEXT,
                "num_predict": 32,
                "temperature": 0,
            },
        },
    )
    if "error" in result:
        raise RuntimeError(result["error"])
    tokens = result.get("prompt_eval_count")
    if not isinstance(tokens, int) or tokens < 1:
        raise RuntimeError("Backend did not return a usable prompt_eval_count")
    elapsed = time.monotonic() - started
    generated = result.get("eval_count", 0)
    duration = result.get("eval_duration", 0)
    rate = generated * 1e9 / duration if duration else None
    print(
        json.dumps(
            {
                "lines": lines,
                "input_tokens": tokens,
                "remaining_context_before_output": CONTEXT - tokens,
                "generated_tokens": generated,
                "generation_tokens_per_second": rate,
                "elapsed_seconds": round(elapsed, 2),
                "done_reason": result.get("done_reason"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return tokens


def main():
    info = post("/api/show", {"model": MODEL})
    print("Model capabilities:", info.get("capabilities"), flush=True)
    print("Model parameters:", info.get("parameters"), flush=True)
    lines = 1000
    for target in (26000, 64000):
        for _ in range(4):
            actual = probe(lines)
            if target * 0.9 <= actual <= target * 1.1:
                break
            lines = max(1, int(lines * target / actual))
        if not target * 0.9 <= actual <= target * 1.1:
            raise RuntimeError(f"Could not calibrate input to target {target} tokens")
        print(
            f"Input near {target} tokens processed; this does not validate long-output quality.",
            flush=True,
        )
    print("Inspect ollama ps, nvidia-smi and Ollama logs separately.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
