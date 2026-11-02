import re
from typing import List, Dict, Any, Optional


def _detect_heading(line: str) -> Optional[str]:
    """Detect if a line looks like a Markdown heading, section title, or policy header."""
    stripped = line.strip()
    if not stripped:
        return None
    # Markdown headers: # Heading, ## Subheading
    if stripped.startswith("#"):
        return stripped.lstrip("#").strip()
    # Numbered policy headers: "Section 1: ...", "Rule 4.2: ...", "Policy - Attendance"
    if re.match(r"^(Section|Rule|Policy|Article|Chapter)\s+[\d\w\.\-]+[:\s]", stripped, re.IGNORECASE):
        return stripped
    # All uppercase short line (e.g. "HOSTEL RULES", "EXAMINATION GUIDELINES")
    if stripped.isupper() and 3 <= len(stripped) <= 60 and not stripped.endswith("."):
        return stripped
    return None


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences while respecting abbreviations, decimals, and bullet points."""
    # Protect common abbreviations: e.g., i.e., Dr., Prof., vs., Fig., No.
    protected = text
    subs = [
        (r"\bDr\.", "Dr__DOT__"),
        (r"\bProf\.", "Prof__DOT__"),
        (r"\be\.g\.", "eg__DOT__"),
        (r"\bi\.e\.", "ie__DOT__"),
        (r"\bvs\.", "vs__DOT__"),
        (r"\bNo\.", "No__DOT__"),
        (r"(\d+)\.(\d+)", r"\1__DECIMAL__\2"),  # preserve decimals like 7.5 or 4.0
    ]
    for pattern, replacement in subs:
        protected = re.sub(pattern, replacement, protected)

    # Split on sentence terminals followed by whitespace or newline
    raw_sentences = re.split(r"(?<=[.?!;])\s+", protected)
    sentences = []
    for s in raw_sentences:
        # Restore protected tokens
        restored = s.replace("Dr__DOT__", "Dr.").replace("Prof__DOT__", "Prof.")
        restored = restored.replace("eg__DOT__", "e.g.").replace("ie__DOT__", "i.e.")
        restored = restored.replace("vs__DOT__", "vs.").replace("No__DOT__", "No.")
        restored = restored.replace("__DECIMAL__", ".")
        if restored.strip():
            sentences.append(restored.strip())
    return sentences


def chunk_text(
    text: str,
    chunk_size: int = 300,
    chunk_overlap: int = 40,
    metadata: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """
    Sentence-Aware Recursive Semantic Chunker.
    
    1. Splits document into paragraphs and detects section headings.
    2. Groups sentences together until target word limit is reached.
    3. Maintains clean sliding window overlap without splitting sentences mid-way.
    4. Enriches every chunk with heading, section, word_count, and positional metadata.
    """
    if not text or not text.strip():
        return []

    metadata = metadata or {}
    doc_id = metadata.get("doc_id", "doc")
    base_title = metadata.get("title", "Document")

    # Split document by double-newline or explicit section dividers
    paragraphs = re.split(r"\n\s*\n+", text)
    
    chunks: List[Dict[str, Any]] = []
    current_sentences: List[str] = []
    current_word_count = 0
    current_heading = base_title
    chunk_id = 0

    def finalize_chunk(sentences_to_pack: List[str], heading: str):
        nonlocal chunk_id
        if not sentences_to_pack:
            return
        chunk_body = " ".join(sentences_to_pack).strip()
        if len(chunk_body) < 15:
            return  # skip trivial fragments

        words = chunk_body.split()
        chunk_meta = metadata.copy()
        chunk_meta.update({
            "chunk_id": f"{doc_id}_chunk_{chunk_id}",
            "chunk_index": chunk_id,
            "section_heading": heading,
            "word_count": len(words),
            "char_length": len(chunk_body),
        })

        chunks.append({
            "chunk_id": f"{doc_id}_chunk_{chunk_id}",
            "text": chunk_body,
            "metadata": chunk_meta,
        })
        chunk_id += 1

    for para in paragraphs:
        lines = para.strip().splitlines()
        if not lines:
            continue

        # Check if first line is a heading
        first_line_heading = _detect_heading(lines[0])
        if first_line_heading:
            current_heading = first_line_heading
            para_content = "\n".join(lines[1:]).strip()
        else:
            para_content = para.strip()

        if not para_content:
            continue

        sentences = _split_into_sentences(para_content)
        for sentence in sentences:
            s_words = sentence.split()
            s_word_count = len(s_words)

            # If a single sentence exceeds chunk_size, split by words
            if s_word_count > chunk_size:
                if current_sentences:
                    finalize_chunk(current_sentences, current_heading)
                    current_sentences = []
                    current_word_count = 0
                for i in range(0, s_word_count, max(1, chunk_size - chunk_overlap)):
                    sub_words = s_words[i : i + chunk_size]
                    finalize_chunk([" ".join(sub_words)], current_heading)
                continue

            # Check if adding this sentence exceeds chunk_size
            if current_word_count + s_word_count > chunk_size and current_sentences:
                finalize_chunk(current_sentences, current_heading)
                
                # Create overlap by retaining trailing sentences from previous chunk
                overlap_sentences: List[str] = []
                overlap_words = 0
                for prev_s in reversed(current_sentences):
                    pw = len(prev_s.split())
                    if overlap_words + pw <= chunk_overlap:
                        overlap_sentences.insert(0, prev_s)
                        overlap_words += pw
                    else:
                        break
                current_sentences = overlap_sentences
                current_word_count = overlap_words

            current_sentences.append(sentence)
            current_word_count += s_word_count

    # Finalize remaining sentences
    if current_sentences:
        finalize_chunk(current_sentences, current_heading)

    # Attach total_chunks to all chunk metadata
    total_count = len(chunks)
    for c in chunks:
        c["metadata"]["total_chunks"] = total_count

    return chunks
