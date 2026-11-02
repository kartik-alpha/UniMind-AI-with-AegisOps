import os
from typing import List
from app.core.config import settings

_model_cache = None


def get_embedding_model():
    global _model_cache
    if os.getenv("USE_FAST_EMBEDDINGS", "false").lower() in ("true", "1", "yes"):
        return None
    if _model_cache is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model_cache = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception:
            _model_cache = None
    return _model_cache


def generate_embedding(text: str) -> List[float]:
    model = get_embedding_model()
    if model:
        return model.encode(text).tolist()
    
    # Fallback deterministic pseudo-embedding (384 dimensions) for offline/lightweight testing
    import hashlib
    h = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((b / 255.0) * 2 - 1) for b in h]
    # Expand to 384 dimensions
    padded = (values * 12)[:384]
    return padded


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    model = get_embedding_model()
    if model:
        return model.encode(texts).tolist()
    return [generate_embedding(t) for t in texts]
