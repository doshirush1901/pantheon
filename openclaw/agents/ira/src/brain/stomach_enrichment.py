#!/usr/bin/env python3
"""
STOMACH: NER + Keyword Enrichment for Ingestion
================================================

The "Gastric Acid" phase of Ira's digestive architecture. Enriches knowledge
items with extracted entities (NER) and keywords before they enter the bloodstream.
Improves retrieval, graph clustering, and semantic search.

Biological analogy: Chemical digestion — breaking down raw text into structured
nutrients (entities, keywords) that the bloodstream can distribute more effectively.

Enrichment adds to metadata:
- ner_entities: List of {text, label} from spaCy NER (PERSON, ORG, PRODUCT, etc.)
- keywords: List of significant terms for search/retrieval

Usage:
    from stomach_enrichment import enrich_items

    for item in enrich_items(items):
        item.metadata  # now has ner_entities, keywords
"""

import logging
import re
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Entity labels we care about for knowledge
RELEVANT_NER_LABELS = {"PERSON", "ORG", "PRODUCT", "GPE", "WORK_OF_ART", "MONEY", "DATE"}

# Simple English stopwords (subset)
_STOPWORDS = frozenset(
    "a an the and or but in on at to for of with by from as is was are were be been being have has had do does did will would could should may might must shall can need".split()
)


def _extract_entities_spacy(text: str, max_chars: int = 50000) -> List[dict]:
    """Extract named entities using spaCy. Returns [{text, label}, ...]."""
    try:
        import spacy
        nlp = getattr(_extract_entities_spacy, "_nlp", None)
        if nlp is None:
            try:
                nlp = spacy.load("en_core_web_sm", disable=["parser"])
            except OSError:
                return []  # Model not downloaded: python -m spacy download en_core_web_sm
            _extract_entities_spacy._nlp = nlp

        trunc = text[:max_chars] if len(text) > max_chars else text
        doc = nlp(trunc)
        seen = set()
        entities = []
        for ent in doc.ents:
            if ent.label_ in RELEVANT_NER_LABELS and ent.text.strip():
                key = (ent.text.strip().lower(), ent.label_)
                if key not in seen:
                    seen.add(key)
                    entities.append({"text": ent.text.strip(), "label": ent.label_})
        return entities[:50]  # Cap to avoid metadata bloat
    except ImportError:
        return []
    except Exception as e:
        logger.debug(f"[STOMACH] NER failed: {e}")
        return []


def _extract_keywords_simple(text: str, max_keywords: int = 15) -> List[str]:
    """Extract significant keywords using frequency + heuristics. No external deps beyond stdlib."""
    if not text or len(text) < 50:
        return []

    # Normalize: lowercase, split on non-alphanumeric
    words = re.findall(r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*", text.lower())
    if not words:
        return []

    # Filter stopwords, single chars, pure numbers
    filtered = []
    for w in words:
        if w in _STOPWORDS or len(w) < 2:
            continue
        if w.isdigit():
            continue
        filtered.append(w)

    if not filtered:
        return []

    # Count and rank
    from collections import Counter
    counts = Counter(filtered)
    # Boost longer words (likely domain terms)
    scored = [(word, count * (1 + 0.1 * len(word))) for word, count in counts.most_common(30)]
    scored.sort(key=lambda x: x[1], reverse=True)

    result = [w for w, _ in scored[:max_keywords]]
    return list(dict.fromkeys(result))  # Preserve order, dedupe


def _extract_keywords_yake(text: str, max_keywords: int = 15) -> List[str]:
    """Extract keywords using YAKE if available (better quality)."""
    try:
        import yake
        kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.8, top=max_keywords)
        keywords = kw_extractor.extract_keywords(text[:30000])
        return [kw for kw, _ in keywords[:max_keywords]]
    except ImportError:
        return []
    except Exception as e:
        logger.debug(f"[STOMACH] YAKE failed: {e}")
        return []


def enrich_item(item: Any, text_attr: str = "text") -> None:
    """Enrich a single item in-place. Adds ner_entities and keywords to metadata."""
    text = getattr(item, text_attr, None)
    if not text or len(str(text)) < 30:
        return

    text = str(text)
    metadata = getattr(item, "metadata", None) or {}
    if not hasattr(item, "metadata"):
        return

    # NER
    entities = _extract_entities_spacy(text)
    if entities:
        metadata["ner_entities"] = entities
        # Supplement entity field if empty and we found a PRODUCT
        if not getattr(item, "entity", None) or not str(getattr(item, "entity", "")).strip():
            for e in entities:
                if e.get("label") == "PRODUCT":
                    item.entity = e.get("text", "")
                    break

    # Keywords (YAKE first, fallback to simple)
    keywords = _extract_keywords_yake(text) or _extract_keywords_simple(text)
    if keywords:
        metadata["keywords"] = keywords

    item.metadata = metadata


def enrich_items(
    items: List[Any],
    text_attr: str = "text",
) -> List[Any]:
    """Enrich a list of items. Modifies in place, returns the same list."""
    enriched_count = 0
    for item in items:
        try:
            enrich_item(item, text_attr=text_attr)
            if "ner_entities" in (getattr(item, "metadata", None) or {}) or "keywords" in (getattr(item, "metadata", None) or {}):
                enriched_count += 1
        except Exception as e:
            logger.debug(f"[STOMACH] Enrichment failed for item: {e}")
    if enriched_count:
        logger.info(f"[STOMACH] Enriched {enriched_count}/{len(items)} items with NER + keywords")
    return items
