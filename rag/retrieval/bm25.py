import math
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words, preserving percentages and codes."""
    if not text:
        return []
    # Match words, numbers with %, hyphenated words (e.g. re-evaluation, CS401, 75%)
    tokens = re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", text.lower())
    # Filter very short non-digit tokens (except significant singles)
    return [t for t in tokens if len(t) > 1 or t.isdigit()]


class BM25Index:
    """
    Okapi BM25 Lexical Search Index for University Knowledge Documents.
    
    Parameters:
      k1: Tuning parameter for term frequency saturation (standard: 1.5).
      b: Tuning parameter for document length normalization (standard: 0.75).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Dict[str, Any]] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_len: List[int] = []
        self.avg_dl: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.total_docs: int = 0

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Append chunks to the index and recompute IDF scores."""
        if not chunks:
            return

        for chunk in chunks:
            # Check if chunk ID already exists, replace if so
            existing_idx = next((i for i, c in enumerate(self.chunks) if c["chunk_id"] == chunk["chunk_id"]), None)
            tokens = tokenize(chunk["text"])
            
            if existing_idx is not None:
                self.chunks[existing_idx] = chunk
                self.doc_tokens[existing_idx] = tokens
                self.doc_len[existing_idx] = len(tokens)
            else:
                self.chunks.append(chunk)
                self.doc_tokens.append(tokens)
                self.doc_len.append(len(tokens))

        self.rebuild_stats()

    def remove_by_doc_id(self, doc_id: int):
        """Remove all chunks associated with a specific document ID."""
        keep_indices = [
            i for i, c in enumerate(self.chunks)
            if c.get("metadata", {}).get("doc_id") != doc_id
        ]
        self.chunks = [self.chunks[i] for i in keep_indices]
        self.doc_tokens = [self.doc_tokens[i] for i in keep_indices]
        self.doc_len = [self.doc_len[i] for i in keep_indices]
        self.rebuild_stats()

    def clear(self):
        """Clear the index."""
        self.chunks = []
        self.doc_tokens = []
        self.doc_len = []
        self.doc_freqs = {}
        self.idf = {}
        self.total_docs = 0
        self.avg_dl = 0.0

    def rebuild_stats(self):
        """Compute document frequencies and IDF for all unique terms in the corpus."""
        self.total_docs = len(self.chunks)
        if self.total_docs == 0:
            self.avg_dl = 0.0
            self.doc_freqs = {}
            self.idf = {}
            return

        self.avg_dl = sum(self.doc_len) / self.total_docs
        df_counter: Counter = Counter()

        for tokens in self.doc_tokens:
            unique_terms = set(tokens)
            df_counter.update(unique_terms)

        self.doc_freqs = dict(df_counter)
        self.idf = {}
        for term, freq in self.doc_freqs.items():
            # Standard Okapi BM25 IDF with smoothing
            val = math.log((self.total_docs - freq + 0.5) / (freq + 0.5) + 1.0)
            self.idf[term] = max(val, 0.01)

    def search(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search corpus using Okapi BM25 scoring.
        Returns chunks with 'bm25_score', 'matched_keywords', and normalized similarity score.
        """
        if self.total_docs == 0:
            return []

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scores: List[Tuple[int, float, List[str]]] = []

        for idx in range(self.total_docs):
            chunk = self.chunks[idx]
            meta = chunk.get("metadata", {})
            if category_filter:
                cat = meta.get("category", "").lower().strip()
                if cat != category_filter.lower().strip():
                    continue

            d_len = self.doc_len[idx]
            tokens = self.doc_tokens[idx]
            tf = Counter(tokens)

            score = 0.0
            matched_terms = []

            for q_term in q_tokens:
                if q_term in tf:
                    matched_terms.append(q_term)
                    term_freq = tf[q_term]
                    idf_val = self.idf.get(q_term, 0.01)

                    numerator = term_freq * (self.k1 + 1.0)
                    denominator = term_freq + self.k1 * (1.0 - self.b + self.b * (d_len / (self.avg_dl or 1.0)))
                    score += idf_val * (numerator / denominator)

                    # Exact match boost for numbers, percentages, codes
                    if "%" in q_term or q_term.isdigit() or len(q_term) >= 5:
                        score += 0.5

            if score > 0:
                scores.append((idx, score, matched_terms))

        if not scores:
            return []

        # Sort descending by BM25 score
        scores.sort(key=lambda x: x[1], reverse=True)
        top_results = scores[:top_k]

        max_score = top_results[0][1] if top_results else 1.0
        results = []

        for idx, raw_score, matched in top_results:
            chunk = self.chunks[idx]
            norm_score = round(min(1.0, raw_score / (max_score + 1e-6)), 4)
            results.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "metadata": chunk.get("metadata", {}),
                "bm25_score": round(raw_score, 4),
                "similarity_score": norm_score,
                "matched_keywords": matched,
            })

        return results


_bm25_instance = None


def get_bm25_index() -> BM25Index:
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Index()
    return _bm25_instance

