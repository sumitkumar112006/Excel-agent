import urllib.request
import json

def test_api():
    base = "http://127.0.0.1:8000"
    print("Testing Backend API Endpoints on " + base)
    
    # Health check
    req = urllib.request.Request(f"{base}/api/health")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"[*] /api/health: status={resp.status}, response={res}")
        assert res.get("status") == "online"

    # Config check
    req = urllib.request.Request(f"{base}/api/config")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"[*] /api/config: status={resp.status}")

    # Auth status (unauthenticated)
    req = urllib.request.Request(f"{base}/api/auth/status")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"[*] /api/auth/status (public/unauth): {res}")

    print("[SUCCESS] All endpoint connectivity checks passed!")

if __name__ == "__main__":
    test_api()
