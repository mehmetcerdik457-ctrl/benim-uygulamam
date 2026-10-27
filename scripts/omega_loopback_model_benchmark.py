#!/usr/bin/env python3
"""Opt-in read-only inference smoke benchmark against an ALREADY running local Ollama.

Only contacts numeric IPv4 loopback; never pulls/installs models or prints
responses. This is a tiny bilingual smoke set, NOT a general quality ranking.
No private documents, prompts, credentials, or GPU allocations are requested.
"""
from __future__ import annotations

import argparse
import http.client
import json
import re
import statistics
import time

CASES = (
    ("tr", "7 ile 5'i topla. Yalnızca sonucu sayı olarak yaz.", "12"),
    ("en", "Add 7 and 5. Return the number only.", "12"),
    ("code", "Give the output of Python print(2 + 3). Only the number.", "5"),
)


def installed_model_metadata(model: str, port: int, timeout: int = 3):
    """Fail closed unless the exact tag is already installed on this loopback daemon.

    A tags GET does not pull weights; no other host or model catalogue is queried.
    """
    conn = http.client.HTTPConnection("127.0.0.1", port=port, timeout=timeout)
    try:
        conn.request("GET", "/api/tags", headers={"Accept": "application/json"})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError("local_model_catalogue_unavailable")
        data = response.read(262145)
        if len(data) > 262144:
            raise RuntimeError("local_model_catalogue_too_large")
        try:
            entries = json.loads(data).get("models")
        except (ValueError, AttributeError):
            raise RuntimeError("local_model_catalogue_invalid") from None
        if not isinstance(entries, list) or len(entries) > 512:
            raise RuntimeError("local_model_catalogue_invalid")
        for item in entries:
            if isinstance(item, dict) and item.get("name") == model:
                digest = item.get("digest")
                size = item.get("size")
                return {
                    "digest": digest if isinstance(digest, str)
                              and re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest) else None,
                    "size_bytes": size if type(size) is int and size >= 0 else None,
                }
        raise RuntimeError("requested_model_not_installed")
    finally:
        conn.close()


def probe(model: str, port: int, prompt: str, output_limit: int, timeout: int):
    conn = http.client.HTTPConnection("127.0.0.1", port=port, timeout=timeout)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": 0, "num_predict": output_limit}}).encode()
    began = time.monotonic()
    first = None
    text = []
    final = {}
    try:
        conn.request("POST", "/api/generate", body=payload,
                     headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError("local_model_http_failed")
        for _ in range(output_limit * 8 + 32):
            raw = response.readline(65536)
            if not raw:
                break
            try:
                chunk = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise RuntimeError("local_model_invalid_stream") from None
            if chunk.get("error"):
                raise RuntimeError("local_model_reported_error")
            token = chunk.get("response", "")
            if token:
                if first is None:
                    first = time.monotonic()
                text.append(token)
            if chunk.get("done") is True:
                final = chunk
                break
        if not final:
            raise RuntimeError("local_model_stream_incomplete")
        if len("".join(text)) > 16000:
            raise RuntimeError("local_model_response_too_long")
        elapsed = time.monotonic() - began
        eval_tokens = final.get("eval_count")
        eval_ns = final.get("eval_duration")
        return {"result": "ok", "ttft_ms": round((first - began) * 1000, 2) if first else None,
                "elapsed_ms": round(elapsed * 1000, 2),
                "eval_tokens": eval_tokens if type(eval_tokens) is int and eval_tokens >= 0 else None,
                "eval_tokens_per_s": (round(eval_tokens * 1e9 / eval_ns, 2)
                                      if type(eval_tokens) is int and type(eval_ns) is int and eval_ns > 0 else None),
                "answer": "".join(text)}
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Already-installed local Ollama model tag")
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--max-output-tokens", type=int, default=32)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", args.model):
        parser.error("invalid model tag")
    if not 1 <= args.port <= 65535 or not 1 <= args.max_output_tokens <= 128:
        parser.error("unsafe limits")
    try:
        existing = installed_model_metadata(args.model, args.port)
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({
            "status": "NOT_MEASURED", "error": "existing_local_model_not_verified",
            "evidence_scope": "EXECUTING_MACHINE_LOOPBACK_ONLY",
            "production_accepted": False,
        }, sort_keys=True))
        return 2
    records = []
    for lang, prompt, expected in CASES:
        try:
            result = probe(args.model, args.port, prompt, args.max_output_tokens, timeout=20)
            answer = result.pop("answer")  # No raw model response ever printed.
            result.update({"case": lang, "exact_match": answer.strip() == expected})
            records.append(result)
        except (OSError, ValueError, RuntimeError):
            records.append({"case": lang, "result": "NOT_MEASURED", "error": "local_runtime_unavailable_or_invalid"})
            break
    successful = [r for r in records if r.get("result") == "ok"]
    summary = {"evidence_scope": "EXECUTING_MACHINE_LOOPBACK_ONLY_NOT_OWNER_UNLESS_OWNER_RAN_IT",
               "model_tag": args.model, "model_digest": existing["digest"],
               "model_size_bytes": existing["size_bytes"], "benchmark_type": "synthetic_tr_en_code_smoke_not_full_quality",
               "num_cases": len(successful),
               "exact_match_count": sum(bool(r.get("exact_match")) for r in successful),
               "mean_ttft_ms": (round(statistics.mean(r["ttft_ms"] for r in successful if r["ttft_ms"] is not None), 2)
                                if any(r["ttft_ms"] is not None for r in successful) else None),
               "cases": records, "vram_bytes": None, "peak_ram_bytes": None,
               "cost_measurement": None, "production_accepted": False}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if len(successful) == len(CASES) else 2


if __name__ == "__main__":
    raise SystemExit(main())
