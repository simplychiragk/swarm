"""
Launch Swarm Sidecar in Golden Run Replay Mode.
Works cross-platform across CMD, PowerShell, and Bash without shell syntax issues.
"""

import os
import uvicorn

if __name__ == "__main__":
    os.environ["SWARM_DEMO_MODE"] = "golden"
    print("=" * 60)
    print("🌟 SWARM DEMO: GOLDEN RUN REPLAY (OFFLINE DEMO SAFE)")
    print("   Zero API keys required. Exact timing. Blue [REPLAY] badges.")
    print("   Listening at: http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=8000, reload=False)
