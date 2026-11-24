import requests

BASE = "http://127.0.0.1:8000"

endpoints = [
    ("GET", "/health"),
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/documents"),
    ("GET", "/api/v1/incidents"),
    ("GET", "/api/v1/tickets/tickets"),
    ("GET", "/api/v1/aegisops/services"),
    ("GET", "/api/v1/aegisops/overview"),
    ("GET", "/api/v1/aegisops/monitoring"),
    ("GET", "/api/v1/aegisops/metrics"),
    ("GET", "/api/v1/aegisops/logs"),
    ("GET", "/api/v1/ml/anomaly-scores"),
    ("GET", "/api/v1/assistant/conversations"),
]

print("Testing all frontend-polled API endpoints on live server:")
for method, ep in endpoints:
    url = f"{BASE}{ep}"
    try:
        r = requests.request(method, url, timeout=5)
        status = r.status_code
        ok = 200 <= status < 300
        mark = "OK " if ok else "ERR"
        print(f"[{mark}] {status} {method} {ep}")
    except Exception as e:
        print(f"[ERR] FAILED {method} {ep}: {e}")

