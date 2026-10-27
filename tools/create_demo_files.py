from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.fixtures import docx_bytes, pdf_bytes

folder = Path(__file__).resolve().parents[1] / "evaluation/fixtures"
folder.mkdir(parents=True, exist_ok=True)
(folder / "sample-cv.docx").write_bytes(
    docx_bytes(
        "Riley Example\nriley@example.com\nSkills\nPython, Django\nExperience\nJan 2020 - Jan 2022\nEducation\nBachelor of Computer Science",
        table_text="Postgres",
    )
)
(folder / "unreadable.pdf").write_bytes(pdf_bytes("") + b"\n% E2E unreadable fixture\n")
print("Created real synthetic DOCX and blank PDF demonstration fixtures.")
