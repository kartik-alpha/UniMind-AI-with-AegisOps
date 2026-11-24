import os
import re
from typing import List, Dict, Any, Optional
from app.core.config import settings
from ai.prompts.assistant_prompts import SYSTEM_PROMPT_TEMPLATE, USER_PROMPT_TEMPLATE


def calculate_groundedness_score(query: str, context_chunks: List[Dict[str, Any]]) -> float:
    """
    Computes a groundedness confidence score between 0.0 and 1.0.
    Evaluates:
      1. Overlap of substantive query terms (excluding generic filler & domain stopwords).
      2. Maximum retrieval similarity score.
    """
    if not context_chunks or not query.strip():
        return 0.0

    domain_stopwords = {
        "what", "is", "the", "are", "for", "how", "can", "does", "rule", "policy",
        "university", "tell", "me", "about", "a", "an", "in", "at", "to", "of", "and",
        "campus", "college", "student", "rules", "give", "please", "with", "from"
    }

    tokens = [
        t for t in re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", query.lower())
        if (len(t) > 2 or t.isdigit() or "%" in t) and t not in domain_stopwords
    ]

    if not tokens:
        tokens = [t for t in re.findall(r"\b\w+\b", query.lower()) if t not in domain_stopwords]

    if not tokens:
        max_sim = max((c.get("similarity_score", 0.0) for c in context_chunks), default=0.0)
        return round(float(max_sim), 2)

    # Check presence across chunk texts
    all_context_text = " ".join(c.get("text", "").lower() for c in context_chunks)
    matched_tokens = [t for t in tokens if t in all_context_text]

    # If NO substantive query terms exist in context, confidence is zero
    if not matched_tokens:
        return 0.0

    token_overlap_ratio = len(matched_tokens) / len(tokens)

    # Substantive coverage threshold: If query has multiple terms and less than 35% match, consider ungrounded
    if len(tokens) >= 3 and token_overlap_ratio < 0.35:
        return 0.0

    max_sim = max((c.get("similarity_score", 0.0) for c in context_chunks), default=0.0)

    groundedness = (token_overlap_ratio * 0.6) + (float(max_sim) * 0.4)
    return round(min(1.0, max(0.0, groundedness)), 2)


def _format_context_blocks(context_chunks: List[Dict[str, Any]]) -> str:
    context_blocks = []
    for idx, chunk in enumerate(context_chunks, 1):
        meta = chunk.get("metadata", {})
        title = meta.get("title", "Document")
        category = meta.get("category", "General")
        heading = meta.get("section_heading", "")
        heading_str = f" - Section: {heading}" if heading else ""
        text = chunk.get("text", "")
        context_blocks.append(f"[Source {idx}: {title} ({category}){heading_str}]\n{text}")
    return "\n\n".join(context_blocks)


def _call_openai(
    query: str,
    context_str: str,
    conversation_history: Optional[List[Dict[str, str]]],
    sources: List[Dict[str, Any]],
    groundedness: float,
) -> Optional[Dict[str, Any]]:
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-placeholder"):
        return None
    try:
        import httpx
        sys_prompt = SYSTEM_PROMPT_TEMPLATE
        user_prompt = USER_PROMPT_TEMPLATE.format(context=context_str, query=query)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": sys_prompt}]
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": 0.1,
        }
        resp = httpx.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=15.0)
        if resp.status_code == 200:
            answer = resp.json()["choices"][0]["message"]["content"]
            return {
                "answer": answer,
                "sources": sources,
                "grounded": True,
                "groundedness_score": groundedness,
                "provider": "openai",
            }
    except Exception:
        pass
    return None


def _call_ollama(
    query: str,
    context_str: str,
    conversation_history: Optional[List[Dict[str, str]]],
    sources: List[Dict[str, Any]],
    groundedness: float,
) -> Optional[Dict[str, Any]]:
    try:
        import httpx
        base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        sys_prompt = SYSTEM_PROMPT_TEMPLATE
        user_prompt = USER_PROMPT_TEMPLATE.format(context=context_str, query=query)
        messages = [{"role": "system", "content": sys_prompt}]
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": getattr(settings, "LLM_MODEL", "llama3.2") or "llama3.2",
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=5.0)
        if resp.status_code == 200:
            answer = resp.json().get("message", {}).get("content", "")
            if answer:
                return {
                    "answer": answer,
                    "sources": sources,
                    "grounded": True,
                    "groundedness_score": groundedness,
                    "provider": "ollama",
                }
    except Exception:
        pass
    return None


def _call_claude(
    query: str,
    context_str: str,
    conversation_history: Optional[List[Dict[str, str]]],
    sources: List[Dict[str, Any]],
    groundedness: float,
) -> Optional[Dict[str, Any]]:
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        sys_prompt = SYSTEM_PROMPT_TEMPLATE
        user_prompt = USER_PROMPT_TEMPLATE.format(context=context_str, query=query)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        messages = []
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "system": sys_prompt,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.1,
        }
        resp = httpx.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            content_blocks = data.get("content", [])
            answer = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            if answer:
                return {
                    "answer": answer,
                    "sources": sources,
                    "grounded": True,
                    "groundedness_score": groundedness,
                    "provider": "claude",
                }
    except Exception:
        pass
    return None


def generate_llm_response(
    query: str,
    context_chunks: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Generates a strictly grounded response based on university knowledge chunks.
    Dispatches across configurable LLM providers (OpenAI, Ollama, Claude, Local Synthesizer)
    with automatic fallbacks and strict anti-hallucination verification.
    """
    if not context_chunks:
        return {
            "answer": "Information not found in the university knowledge base.",
            "sources": [],
            "grounded": False,
            "groundedness_score": 0.0,
            "provider": "none",
        }

    # Format sources list
    sources = []
    for idx, chunk in enumerate(context_chunks, 1):
        meta = chunk.get("metadata", {})
        title = meta.get("title") or meta.get("filename") or "University Document"
        category = meta.get("category", "General")
        sources.append({
            "source_number": idx,
            "title": title,
            "category": category,
            "filename": meta.get("filename", ""),
            "chunk_id": chunk.get("chunk_id", ""),
            "section_heading": meta.get("section_heading", ""),
            "similarity_score": chunk.get("similarity_score", 0.0),
            "matched_keywords": chunk.get("matched_keywords", []),
            "rrf_score": chunk.get("rrf_score"),
        })

    # Groundedness verification
    groundedness = calculate_groundedness_score(query, context_chunks)

    # Hallucination guardrail: if no substantive query tokens match context, deny
    if groundedness <= 0.0:
        return {
            "answer": "Information not found in the university knowledge base.",
            "sources": [],
            "grounded": False,
            "groundedness_score": 0.0,
            "provider": "guardrail_refusal",
        }

    # Provider Dispatch
    context_str = _format_context_blocks(context_chunks)
    provider = getattr(settings, "LLM_PROVIDER", "openai").lower()

    if provider == "ollama":
        res = _call_ollama(query, context_str, conversation_history, sources, groundedness)
        if res:
            return res
    elif provider == "claude":
        res = _call_claude(query, context_str, conversation_history, sources, groundedness)
        if res:
            return res
    elif provider == "openai":
        res = _call_openai(query, context_str, conversation_history, sources, groundedness)
        if res:
            return res

    # Intelligent Local Synthesis Engine (deterministic, grounded, zero-hallucination fallback)
    # Filter sentences containing substantive query words
    domain_stopwords = {
        "what", "is", "the", "are", "for", "how", "can", "does", "rule", "policy",
        "university", "tell", "me", "about", "a", "an", "in", "at", "to", "of", "and",
        "campus", "college", "student", "rules", "give", "please", "with", "from"
    }
    q_words = {
        w for w in re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", query.lower())
        if (len(w) > 2 or w.isdigit() or "%" in w) and w not in domain_stopwords
    }
    if not q_words:
        q_words = {w for w in re.findall(r"\b\w+\b", query.lower()) if w not in domain_stopwords}

    scored_sentences = []
    min_required_overlap = 2 if len(q_words) >= 3 else 1

    for chunk in context_chunks:
        text = chunk.get("text", "")
        meta = chunk.get("metadata", {})
        heading = meta.get("section_heading", "")

        sentences = re.split(r"(?<=[.!?])\s+", text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            s_words = set(re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", s_clean.lower()))
            overlap = len(q_words & s_words)
            if overlap >= min_required_overlap:
                rule_boost = 1.5 if ("%" in s_clean or any(c.isdigit() for c in s_clean) or "must" in s_words or "required" in s_words) else 1.0
                scored_sentences.append((overlap * rule_boost, s_clean, heading))

    if not scored_sentences:
        # Strict zero-hallucination guarantee: If no sentence matches query concepts, deny!
        return {
            "answer": "Information not found in the university knowledge base.",
            "sources": [],
            "grounded": False,
            "groundedness_score": 0.0,
            "provider": "guardrail_refusal",
        }

    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s[1] for s in scored_sentences[:4]]

    unique_sentences = []
    for s in top_sentences:
        if s not in unique_sentences:
            unique_sentences.append(s)

    primary_answer = unique_sentences[0]
    additional_rules = unique_sentences[1:]

    response_parts = [
        f"**Official University Policy Response:**",
        f"{primary_answer}",
    ]

    if additional_rules:
        response_parts.append("\n**Key Regulations & Details:**")
        for r in additional_rules:
            response_parts.append(f"- {r}")

    # Add section citations
    citations = []
    for s in sources:
        heading_info = f" ({s['section_heading']})" if s.get("section_heading") else ""
        citations.append(f"*{s['title']}{heading_info}*")
    if citations:
        response_parts.append(f"\n*Source Reference: {', '.join(set(citations))}*")

    formatted_answer = "\n".join(response_parts)

    return {
        "answer": formatted_answer,
        "sources": sources,
        "grounded": True,
        "groundedness_score": groundedness,
        "provider": "local_synthesizer",
    }
