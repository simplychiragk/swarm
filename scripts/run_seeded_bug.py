"""
Launch Swarm Sidecar in Seeded-Bug Demo Mode.
Works cross-platform across CMD, PowerShell, and Bash without shell syntax issues.
"""

import os
import uvicorn

if __name__ == "__main__":
    os.environ["SWARM_DEMO_MODE"] = "seeded_bug"
    os.environ["SWARM_PERMISSION_MODE"] = "demo"
    print("=" * 60)
    print("🐛 SWARM DEMO: SEEDED-BUG CLOSED LOOP (FAIL -> FIX -> PASS)")
    print("   QA Bee detects disabled button -> routes fix -> verifies fix -> passes.")
    print("   Listening at: http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=8000, reload=False)
