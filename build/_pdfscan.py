from pathlib import Path
from pypdf import PdfReader
root = Path(__file__).resolve().parents[1]
needles = ["account_4163","account_4857","account_4990","account_5037","account_5521","account_7012","account_8858","audit_record_5569","audit_record_6645","support_001","object_19","tombstone_17"]
for path in (root/"dataset"/"evidence").rglob("*.pdf"):
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    found = [n for n in needles if n in text]
    print(path.name, "chars", len(text), "found", found)
