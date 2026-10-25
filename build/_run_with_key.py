"""Run the audit with the user-level API key. Never print the key."""
import os
import subprocess
import sys
from pathlib import Path

key = subprocess.check_output(
    [
        "powershell",
        "-NoProfile",
        "-Command",
        "[Environment]::GetEnvironmentVariable('XAI_API_KEY','User')",
    ],
    text=True,
).strip()
if not key:
    print("XAI_API_KEY is not set for the user", file=sys.stderr)
    raise SystemExit(1)
os.environ["XAI_API_KEY"] = key
os.environ.setdefault("DELETION_AUDIT_MODEL", "grok-4.7")
root = Path(__file__).resolve().parents[1]
raise SystemExit(
    subprocess.call([sys.executable, "code/main.py"], cwd=root, env=os.environ)
)
