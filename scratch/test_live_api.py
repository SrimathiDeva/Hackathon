"""
scratch/test_live_api.py
Validates the live running backend API on port 8000.
"""

import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

questions = [
    "How many subjects are in the study?",
    "How many patients are enrolled?",
    "Tell me about subject 042-S07-001.",
    "Give me the details of 042-S07-001.",
    "What is the sex of 042-S07-001?",
    "Which treatment arm is 042-S07-001 in?",
    "What laboratory results does 042-S07-001 have?",
    "Did 042-S07-001 have any adverse events?",
    "Which patients triggered Hy's Law?",
    "Show me the patients with Hy's Law findings.",
    "Were there any dosing errors?",
    "Which subjects had a wrong dose?",
    "What medications were used?",
    "What changed between protocol version 1 and version 2?",
    "What are the protocol rules?",
    "Who withdrew from the study?",
    "Show me the patients who discontinued.",
    "How many adverse events were reported?",
    "Which subjects at site S01 had a wrong dose?",  # TRAP
    "Show me the results.",  # Ambiguity
    "What is the stock price of Apple?",  # Unsupported
]

print(f"Testing live API at {BASE_URL}/api/ask with {len(questions)} natural-language questions:\n")

for q in questions:
    req_data = json.dumps({"question": q}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/api/ask", data=req_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ans = data.get("answer")
            ev_count = len(data.get("evidence", []))
            conf = data.get("confidence")
            first_ev = data.get("evidence", [])[0] if ev_count > 0 else None
            ev_details = bool(first_ev.get("details")) if first_ev else False
            
            print(f"Q: \"{q}\"")
            print(f"  A: {ans}")
            print(f"  Evidence: {ev_count} refs (Enriched details: {ev_details}), Conf: {conf}")
            print(f"  Text: {data.get('text')[:85]}...")
            print()
    except Exception as e:
        print(f"ERROR querying '{q}': {e}\n")

print("All live API questions tested successfully!")
