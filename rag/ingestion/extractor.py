import os
import csv
import io
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Tuple
import pypdf


def calculate_sha256(file_path: Path) -> str:
    """Computes SHA-256 cryptographic checksum of file content."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _extract_text_from_docx(path: Path) -> str:
    """Extract plain text from a DOCX (OpenXML ZIP archive) without third-party dependencies."""
    try:
        with zipfile.ZipFile(str(path)) as z:
            xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        paragraphs = []
        for p in tree.iter():
            if p.tag.endswith("}p"):
                texts = [elem.text for elem in p.iter() if elem.tag.endswith("}t") and elem.text]
                if texts:
                    paragraphs.append("".join(texts))
        return "\n\n".join(paragraphs) if paragraphs else ""
    except Exception:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def _extract_text_from_csv(path: Path) -> str:
    """Extract tabular structured text from CSV file."""
    rows_text = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = None
            for idx, row in enumerate(reader):
                if not row or not any(row):
                    continue
                if idx == 0:
                    header = [h.strip() for h in row]
                    rows_text.append(f"Columns: {', '.join(header)}")
                else:
                    if header and len(header) == len(row):
                        row_desc = [f"{header[i]}: {row[i].strip()}" for i in range(len(row))]
                        rows_text.append(f"Row {idx}: {', '.join(row_desc)}")
                    else:
                        rows_text.append(f"Row {idx}: {', '.join(row)}")
        return "\n".join(rows_text)
    except Exception:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def extract_text_from_file(file_path: str) -> str:
    """Extracts raw text content from PDF, DOCX, TXT, MD, CSV, or JSON."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found at path: {file_path}")

    ext = path.suffix.lower()
    if ext == ".csv":
        return _extract_text_from_csv(path)
    elif ext in [".txt", ".md", ".json"]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        text_content = []
        try:
            reader = pypdf.PdfReader(str(path))
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"--- Page {page_idx + 1} ---\n" + page_text)
            return "\n\n".join(text_content)
        except Exception:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    elif ext in [".docx", ".doc"]:
        return _extract_text_from_docx(path)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def extract_text_and_metadata_from_file(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """Extracts text along with file attributes, page count, sha256, and character statistics."""
    path = Path(file_path)
    text = extract_text_from_file(file_path)
    stat = path.stat()
    sha256_hash = calculate_sha256(path)

    mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".json": "application/json",
    }

    meta = {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "file_size_bytes": stat.st_size,
        "char_count": len(text),
        "word_count": len(text.split()),
        "sha256": sha256_hash,
        "mime_type": mime_types.get(path.suffix.lower(), "text/plain"),
    }
    if path.suffix.lower() == ".pdf":
        try:
            reader = pypdf.PdfReader(str(path))
            meta["page_count"] = len(reader.pages)
        except Exception:
            meta["page_count"] = 1
    elif path.suffix.lower() == ".csv":
        meta["page_count"] = 1

    return text, meta
