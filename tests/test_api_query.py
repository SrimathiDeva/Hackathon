"""
tests/test_api_query.py

Automated test suite validating the Phase 2 backend API integration:
  - POST /api/query endpoint behavior, schema, and error handling
  - Request validation (HTTP 400 on empty/whitespace questions)
  - Scenario A: "How many subjects are in the study?" (Count: 241)
  - Scenario B: "What is the sex of 042-S07-001?" (Lookup: M)
  - Scenario C: "Which subjects triggered Hy's Law?" (Finding: 3 candidates, 6 LB evidence records)
  - Scenario D: "Which subjects at site S01 received a wrong dose?" (Trap: [] answer, 0 evidence, 0 fabricated)
  - Scenario E: "What changed between protocol version 1 and version 2?" (Protocol diff: grounded evidence)
  - Preservation of all existing endpoints:
      GET /api/health
      GET /api/stats
      GET /api/patient/{usubjid}
      POST /api/ask
      GET /api/public-questions
      GET /api/protocol
      GET /api/hys-law
"""

import os
import sys
import json
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def find_api_url() -> str:
    """Detect whether backend is running on 8000 or 8001."""
    candidates = ["http://127.0.0.1:8000", "http://127.0.0.1:8001"]
    for url in candidates:
        try:
            req = urllib.request.Request(f"{url}/api/health", headers={"User-Agent": "ATLAS-Test"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return "http://127.0.0.1:8000"


def http_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "ATLAS-Test"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_post(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ATLAS-Test"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}


def run_api_tests():
    print("=" * 80)
    print("ATLAS CLINICAL QUERY INVESTIGATION ENGINE - PHASE 2 API VERIFICATION")
    print("=" * 80)

    base_url = find_api_url()
    print(f"Target backend URL: {base_url}\n")

    # 1. Verify Preserved Endpoints
    print("--> 1. Testing Preserved Endpoints...")
    # GET /api/health
    status, data = http_get(f"{base_url}/api/health")
    assert status == 200 and data.get("status") == "ok", f"Health check failed: {status} {data}"
    print("  [PASS] GET /api/health -> 200 OK")

    # GET /api/stats
    status, data = http_get(f"{base_url}/api/stats")
    assert status == 200 and data.get("subjects") == 241, f"Stats failed: {status} {data}"
    print(f"  [PASS] GET /api/stats -> 200 OK ({data.get('subjects')} subjects, {data.get('clinical_records')} records)")

    # GET /api/patient/042-S07-001
    status, data = http_get(f"{base_url}/api/patient/042-S07-001")
    assert status == 200 and data.get("usubjid") == "042-S07-001", f"Patient lookup failed: {status}"
    print("  [PASS] GET /api/patient/042-S07-001 -> 200 OK")

    # POST /api/ask
    status, data = http_post(f"{base_url}/api/ask", {"question": "How many subjects are in the study?"})
    assert status == 200 and data.get("answer") == 241, f"POST /api/ask failed: {status} {data}"
    print("  [PASS] POST /api/ask -> 200 OK")

    # GET /api/public-questions
    status, data = http_get(f"{base_url}/api/public-questions")
    assert status == 200 and isinstance(data, list) and len(data) == 10, f"Public questions failed: {status} {data}"
    print(f"  [PASS] GET /api/public-questions -> 200 OK ({len(data)} questions)")

    # GET /api/protocol
    status, data = http_get(f"{base_url}/api/protocol")
    assert status == 200 and "timeline" in data, f"Protocol failed: {status}"
    print("  [PASS] GET /api/protocol -> 200 OK")

    # GET /api/hys-law
    status, data = http_get(f"{base_url}/api/hys-law")
    assert status == 200 and len(data.get("candidates", [])) == 3, f"Hy's Law failed: {status}"
    print("  [PASS] GET /api/hys-law -> 200 OK (3 candidates)")

    # 2. Test Request Validation for POST /api/query
    print("\n--> 2. Testing Request Validation for POST /api/query...")
    # Empty string
    status, data = http_post(f"{base_url}/api/query", {"question": ""})
    assert status == 400, f"Expected 400 for empty question, got {status}: {data}"
    print("  [PASS] Empty question '' -> HTTP 400 Bad Request")

    # Whitespace only
    status, data = http_post(f"{base_url}/api/query", {"question": "     "})
    assert status == 400, f"Expected 400 for whitespace question, got {status}: {data}"
    print("  [PASS] Whitespace question '     ' -> HTTP 400 Bad Request")

    # Missing question field
    status, data = http_post(f"{base_url}/api/query", {})
    assert status == 422, f"Expected 422 for missing question field, got {status}: {data}"
    print("  [PASS] Missing question field {} -> HTTP 422 Unprocessable Entity")

    # 3. Test Required Scenarios on POST /api/query
    print("\n--> 3. Testing Required Scenarios on POST /api/query...")

    # Required response keys
    expected_keys = {
        "question",
        "parsed_query",
        "query_plan",
        "explanation",
        "answer",
        "evidence",
        "provenance",
        "validation",
    }

    # Scenario A: Total subjects in study
    print("\n[A] 'How many subjects are in the study?'")
    status, res = http_post(f"{base_url}/api/query", {"question": "How many subjects are in the study?"})
    assert status == 200, f"Failed status {status}: {res}"
    assert expected_keys.issubset(res.keys()), f"Missing keys: {expected_keys - set(res.keys())}"
    assert res["answer"] == 241, f"Expected answer 241, got {res['answer']}"
    assert len(res["evidence"]) == 241, f"Expected 241 evidence records, got {len(res['evidence'])}"
    assert res["validation"]["status"] == "PASS", f"Validation failed: {res['validation']}"
    print(f"  Result: answer = {res['answer']}, evidence = {len(res['evidence'])}, validation = {res['validation']['status']}")

    # Scenario B: Sex of 042-S07-001
    print("\n[B] 'What is the sex of 042-S07-001?'")
    status, res = http_post(f"{base_url}/api/query", {"question": "What is the sex of 042-S07-001?"})
    assert status == 200, f"Failed status {status}: {res}"
    assert expected_keys.issubset(res.keys()), f"Missing keys: {expected_keys - set(res.keys())}"
    assert res["answer"] == "M", f"Expected answer 'M', got {res['answer']}"
    assert len(res["evidence"]) == 1, f"Expected 1 evidence record, got {len(res['evidence'])}"
    assert res["evidence"][0]["usubjid"] == "042-S07-001", f"Wrong evidence subject: {res['evidence'][0]}"
    assert res["validation"]["status"] == "PASS", f"Validation failed: {res['validation']}"
    print(f"  Result: answer = {res['answer']}, evidence = {len(res['evidence'])}, validation = {res['validation']['status']}")

    # Scenario C: Hy's Law
    print("\n[C] 'Which subjects triggered Hy's Law?'")
    status, res = http_post(f"{base_url}/api/query", {"question": "Which subjects triggered Hy's Law?"})
    assert status == 200, f"Failed status {status}: {res}"
    assert expected_keys.issubset(res.keys()), f"Missing keys: {expected_keys - set(res.keys())}"
    expected_cands = ["042-S05-003", "042-S07-001", "042-S08-014"]
    assert res["answer"] == expected_cands, f"Expected {expected_cands}, got {res['answer']}"
    assert len(res["evidence"]) == 6, f"Expected exactly 6 evidence records, got {len(res['evidence'])}"
    assert all(e["domain"] == "LB" for e in res["evidence"]), "All evidence must be from LB domain"
    assert res["validation"]["status"] == "PASS", f"Validation failed: {res['validation']}"
    assert res["validation"]["verified_evidence"] == 6, f"Verified count mismatch: {res['validation']}"
    assert res["validation"]["unsupported_fabrication_count"] == 0, f"Fabrications detected: {res['validation']}"
    assert res["validation"]["audit_compliant"] is True, f"Audit compliance failed: {res['validation']}"
    print(f"  Result: 3 candidates = {res['answer']}")
    print(f"  Evidence: {len(res['evidence'])} LB records, verified = {res['validation']['verified_evidence']}")
    print(f"  Audit compliant: {res['validation']['audit_compliant']}")

    # Scenario D: S01 Dosing Trap
    print("\n[D] 'Which subjects at site S01 received a wrong dose?'")
    status, res = http_post(f"{base_url}/api/query", {"question": "Which subjects at site S01 received a wrong dose?"})
    assert status == 200, f"Failed status {status}: {res}"
    assert expected_keys.issubset(res.keys()), f"Missing keys: {expected_keys - set(res.keys())}"
    assert res["answer"] == [], f"Dosing trap failed! Expected [], got {res['answer']}"
    assert len(res["evidence"]) == 0, f"Expected 0 evidence for trap, got {len(res['evidence'])}"
    assert res["validation"]["status"] == "PASS", f"Validation failed: {res['validation']}"
    assert res["validation"]["unsupported_fabrication_count"] == 0, f"Fabrication detected: {res['validation']}"
    print(f"  Result: answer = {res['answer']} (trap correctly preserved: no wrong dose subjects at S01)")
    print(f"  Evidence count: {len(res['evidence'])}, fabrications: {res['validation']['unsupported_fabrication_count']}")

    # Scenario E: Protocol changes v1 -> v2
    print("\n[E] 'What changed between protocol version 1 and version 2?'")
    status, res = http_post(f"{base_url}/api/query", {"question": "What changed between protocol version 1 and version 2?"})
    assert status == 200, f"Failed status {status}: {res}"
    assert expected_keys.issubset(res.keys()), f"Missing keys: {expected_keys - set(res.keys())}"
    assert isinstance(res["answer"], dict) and ("v1_window" in res["answer"] or "v2_window" in res["answer"]), f"Unexpected answer: {res['answer']}"
    assert len(res["evidence"]) >= 1, f"Expected >= 1 evidence record, got {len(res['evidence'])}"
    assert res["validation"]["status"] == "PASS", f"Validation failed: {res['validation']}"
    print(f"  Result: Protocol changes identified -> {res['answer']}")
    print(f"  Evidence count: {len(res['evidence'])}, validation = {res['validation']['status']}")

    print("\n" + "=" * 80)
    print("ALL PHASE 2 API INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_api_tests()
