import re
from typing import List, Dict, Set, Any


# Common academic/university synonym and term expansion dictionary
UNIVERSITY_SYNONYM_MAP: Dict[str, List[str]] = {
    "attendance": ["minimum attendance", "75% attendance", "eligibility", "condonation", "medical certificate", "shortage"],
    "curfew": ["hostel timing", "in-time", "10:00 PM", "gate close", "entry rule", "resident curfew"],
    "hostel": ["hostel warden", "resident", "curfew", "mess", "room allotment", "hostel guidelines"],
    "exam": ["examination", "end-semester", "mid-semester", "grading", "evaluation", "hall ticket", "re-evaluation"],
    "examination": ["end-semester", "grade", "re-evaluation", "answer script", "weightage", "marks"],
    "re-evaluation": ["re-checking", "re-evaluation", "rechecking", "scrutiny", "7 days", "marks review"],
    "library": ["book renewal", "issue return", "library card", "catalogue", "borrowing", "fine"],
    "grading": ["credits", "grade point", "cgpa", "sgpa", "passing marks", "evaluation scheme"],
    "cgpa": ["cumulative grade point average", "sgpa", "grading scale", "10-point scale", "credits"],
    "it": ["wifi", "network", "portal", "lms", "credentials", "server"],
    "wifi": ["internet", "network", "hostel connectivity", "portal", "login"],
}


def expand_query(query: str) -> Dict[str, Any]:
    """
    Expands student queries with institutional synonyms, abbreviations, and key entity terms.
    Returns:
      - normalized_query: cleaned and normalized string
      - expanded_terms: list of high-priority additional keywords
      - expanded_query: augmented query string combining original + expanded concepts
    """
    if not query:
        return {"normalized_query": "", "expanded_terms": [], "expanded_query": ""}

    cleaned = query.strip()
    words = re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", cleaned.lower())

    expanded_terms: Set[str] = set()

    for word in words:
        if word in UNIVERSITY_SYNONYM_MAP:
            for syn in UNIVERSITY_SYNONYM_MAP[word]:
                expanded_terms.add(syn)
        # Check partial subwords (e.g. "attend" in "attendance")
        for key, syns in UNIVERSITY_SYNONYM_MAP.items():
            if key in word or word in key:
                for s in syns[:3]:
                    expanded_terms.add(s)

    # Exclude terms already in query to avoid redundancy
    query_lower = cleaned.lower()
    novel_terms = [t for t in expanded_terms if t.lower() not in query_lower]

    # Combine into enriched search query
    augmented_parts = [cleaned]
    if novel_terms:
        augmented_parts.append(" ".join(novel_terms[:4]))

    augmented_query = " ".join(augmented_parts)

    return {
        "normalized_query": cleaned,
        "expanded_terms": novel_terms[:6],
        "expanded_query": augmented_query,
    }
