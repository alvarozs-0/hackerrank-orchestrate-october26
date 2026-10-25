from pathlib import Path

p = Path(__file__).resolve().parents[1] / "log.txt"
text = p.read_text(encoding="utf-8")
if not text.endswith("\n"):
    text += "\n"
entry = """## [2026-10-25T06:31:54Z] SESSION START

tool=OpenCode
model=grok-4.7
Repo Root: C:\\Users\\alvar\\OneDrive\\Documents\\Alvaro\\Programming\\hackerrank-orchestrate-october26
Branch: main
Worktree: main
Parent Agent: none
Language: py
Time Remaining: not configured

"""
p.write_text(text + entry, encoding="utf-8", newline="\n")
print("appended")
