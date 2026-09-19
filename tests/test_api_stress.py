"""
tests/test_api_stress.py

Tests POST /api/query with 12 natural-language questions on http://127.0.0.1:8001.
Verifies:
  - HTTP status 200
  - Schema validity (question, parsed_query, query_plan, explanation, answer, text, evidence, provenance, validation)
  - Execution time profiling
"""

import urllib.request
import json
import time
import sys

API_URL = "http://127.0.0.1:8001/api/query"

TEST_QUESTIONS = [
    # 1. Total cohort count
    "How many subjects are in the study?",
    # 2. Count variation
    "How many patients are enrolled?",
    # 3. Patient demographic lookup
    "What is the sex of 042-S07-001?",
    # 4. Patient demographic lookup variation
    "Is 042-S07-001 male or female?",
    # 5. Hy's law candidate search
    "Which subjects triggered Hy's Law?",
    # 6. Hy's law variation
    "Find Hy's Law candidates",
    # 7. Dosing deviation query
    "Which subjects received the wrong dose?",
    # 8. Dosing trap query (site S01)
    "Which subjects at site S01 received a wrong dose?",
    # 9. Protocol amendment comparison
    "What changed between protocol version 1 and version 2?",
    # 10. Study withdrawal query
    "Who withdrew from the study?",
    # 11. Laboratory threshold with temporal anchor
    "Which subjects at S07 had ALT above 3 times ULN within 7 days of Week 8?",
    # 12. Adversarial / Unsupported out-of-scope query
    "Which patients developed cancer?",
]

REQUIRED_KEYS = [
    "question",
    "parsed_query",
    "query_plan",
    "explanation",
    "answer",
    "text",
    "evidence",
    "provenance",
    "validation",
]


def test_api():
    print("=" * 80)
    print("TESTING POST /api/query ON http://127.0.0.1:8001")
    print("=" * 80)

    # 1. Verify health check first
    try:
        req = urllib.request.Request("http://127.0.0.1:8001/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"[HEALTH CHECK] Status: {resp.status} | {health}")
    except Exception as e:
        print(f"[ERROR] Could not connect to backend on port 8001: {e}")
        # Try port 8000 as fallback check
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[NOTE] Port 8000 is listening: {resp.status}")
        except Exception:
            pass
        sys.exit(1)

    passed = 0
    failed = 0
    latencies = []

    for i, q in enumerate(TEST_QUESTIONS, start=1):
        payload = json.dumps({"question": q}).encode("utf-8")
        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                dt = (time.perf_counter() - t0) * 1000
                latencies.append(dt)
                status_code = resp.status
                body = json.loads(resp.read().decode("utf-8"))

                # Validate schema
                missing_keys = [k for k in REQUIRED_KEYS if k not in body]
                if status_code == 200 and not missing_keys:
                    passed += 1
                    ans_summary = (
                        f"list({len(body['answer'])})"
                        if isinstance(body["answer"], list)
                        else str(body["answer"])
                    )
                    print(
                        f"[{i:02d}/12] [PASS] HTTP {status_code} ({dt:.1f}ms) | Q: '{q}' -> Ans: {ans_summary}, Ev: {len(body['evidence'])}"
                    )
                else:
                    failed += 1
                    print(
                        f"[{i:02d}/12] [FAIL] HTTP {status_code} | Missing keys: {missing_keys}"
                    )
        except urllib.error.HTTPError as e:
            dt = (time.perf_counter() - t0) * 1000
            failed += 1
            print(f"[{i:02d}/12] [FAIL] HTTP {e.code}: {e.read().decode('utf-8')}")
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            failed += 1
            print(f"[{i:02d}/12] [FAIL] Exception: {e}")

    print("-" * 80)
    print(f"API Test Summary: {passed}/{len(TEST_QUESTIONS)} passed, {failed} failed.")
    if latencies:
        print(f"API Latency: Min={min(latencies):.2f}ms, Max={max(latencies):.2f}ms, Avg={sum(latencies)/len(latencies):.2f}ms")
    print("=" * 80)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    test_api()
