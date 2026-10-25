from datetime import datetime, timezone
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "log.txt"
text = p.read_text(encoding="utf-8")
if not text.endswith("\n"):
    text += "\n"
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
entry = f"""## [{stamp}] Where to set the API key

User Prompt (verbatim, secrets redacted):
where do I set the api key

Agent Response Summary:
The app reads XAI_API_KEY or GROK_API_KEY from the process environment. It does not load a .env file. Told the user to set the variable in the current terminal and not to commit it or paste it into chat.

Actions:
* grep XAI_API_KEY in code/

Context:
tool=OpenCode
model=grok-4.7
branch=main
repo_root=C:\\Users\\alvar\\OneDrive\\Documents\\Alvaro\\Programming\\hackerrank-orchestrate-october26
worktree=main
parent_agent=none
"""
p.write_text(text + entry, encoding="utf-8", newline="\n")
tail = p.read_text(encoding="utf-8")
start = tail.rfind(f"## [{stamp}]")
assert "tool=OpenCode" in tail[start:] and "model=grok-4.7" in tail[start:]
print(stamp)
