"""Quick smoke test (run while server is up on port 8765)."""
import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8765"
SAMPLE = Path(__file__).resolve().parent.parent / "sample_docs" / "company_policy.txt"


def main() -> None:
    with httpx.Client(timeout=300.0) as client:
        health = client.get(f"{BASE}/api/health")
        health.raise_for_status()
        print("health:", health.json())

        with SAMPLE.open("rb") as f:
            upload = client.post(
                f"{BASE}/api/upload",
                files={"file": (SAMPLE.name, f, "text/plain")},
            )
        upload.raise_for_status()
        print("upload:", upload.json())

        query = client.post(
            f"{BASE}/api/query",
            json={"question": "How many vacation days do new employees get?"},
        )
        query.raise_for_status()
        data = query.json()
        print("provider:", data["provider"])
        print("answer:", data["answer"][:300], "...")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAILED:", exc, file=sys.stderr)
        sys.exit(1)
