import os
from pathlib import Path
import pypdf


def extract_text_from_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found at path: {file_path}")

    ext = path.suffix.lower()
    if ext in [".txt", ".md", ".csv", ".json"]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        text_content = []
        reader = pypdf.PdfReader(str(path))
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_content.append(f"--- Page {page_idx + 1} ---\n" + page_text)
        return "\n\n".join(text_content)
    else:
        # Fallback to plain text read
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
