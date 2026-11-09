"""Deterministic editorial evidence gates and immutable review fingerprints."""
import hashlib
import json
from urllib.parse import urlparse


NEWS_CATEGORIES = {"news", "trending", "breaking", "current_affairs"}
MIN_EVIDENCE_SUMMARY_CHARS = 120


def _is_http_url(value):
    try:
        parsed = urlparse(str(value or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def topic_evidence(topic_data):
    """Return a normalized, auditable list of source records."""
    records = []
    candidates = topic_data.get("evidence_sources") or [topic_data]
    if not isinstance(candidates, list):
        candidates = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url") or item.get("url") or "").strip()
        title = str(item.get("source_title") or item.get("title") or "").strip()
        summary = str(item.get("source_summary") or item.get("summary") or "").strip()
        if _is_http_url(url):
            records.append({
                "url": url, "title": title[:300], "summary": summary[:5000],
                "published_at": str(item.get("published_at") or "").strip()[:100],
                "summary_chars": len(summary),
            })
    return records


def topic_is_generation_eligible(topic_data):
    """Reject current/news topics without a URL and a minimally useful source excerpt."""
    if not isinstance(topic_data, dict):
        return False
    category = str(topic_data.get("category", "general")).strip().lower()
    if category not in NEWS_CATEGORIES:
        return True
    return any(len(source["summary"]) >= MIN_EVIDENCE_SUMMARY_CHARS
               for source in topic_evidence(topic_data))


def build_editorial_context(topic_data):
    """Build source-constrained instructions; metadata is not independent verification."""
    sources = topic_evidence(topic_data)
    category = str(topic_data.get("category", "general")).strip().lower()
    if category in NEWS_CATEGORIES and not topic_is_generation_eligible(topic_data):
        raise ValueError("News/trending topic rejected: no usable source URL and excerpt.")
    if not sources:
        return (
            "Evidence status: NO SOURCE EXCERPT PROVIDED. Treat this as evergreen/general "
            "educational content only. Do not state current events, statistics, prices, "
            "legal/tax/medical/financial recommendations, named-person claims, or time-sensitive "
            "facts. Avoid precise claims that cannot be supported. State uncertainty plainly."
        )
    lines = [
        "Evidence status: SOURCE MATERIAL PROVIDED, NOT INDEPENDENTLY FACT-CHECKED.",
        "Use only facts explicitly supported by the source excerpts below.",
        "Do not invent dates, numbers, quotations, people, outcomes, or causal explanations.",
        "Separate source-reported facts from general explanation and clearly flag uncertainty.",
        "Do not claim that a source has been independently verified.",
    ]
    for index, source in enumerate(sources, 1):
        lines.extend([
            f"Source {index}: {source['title'] or 'Untitled source'}",
            f"URL: {source['url']}",
            f"Published: {source['published_at'] or 'not supplied'}",
            f"Excerpt: {source['summary'] or '[No excerpt supplied]'}",
        ])
    return "\n".join(lines)


def build_source_metadata(topic_data):
    sources = topic_evidence(topic_data)
    return {
        "evidence_status": (
            "source_excerpt_supplied_not_independently_verified" if sources
            else "no_source_excerpt_evergreen_only"
        ),
        "sources": [{
            "title": source["title"], "url": source["url"],
            "published_at": source["published_at"],
            "excerpt_chars": source["summary_chars"],
        } for source in sources],
    }


def content_review_hash(title, script, metadata):
    """Fingerprint the exact editorial text and source references presented for review."""
    metadata = metadata if isinstance(metadata, dict) else {}
    review_payload = {
        "title": str(title or ""),
        "script": str(script or ""),
        "description": str(metadata.get("description") or ""),
        "hashtags": metadata.get("hashtags") or [],
        "thumbnail_prompt": str(metadata.get("thumbnail_prompt") or ""),
        "sources": metadata.get("sources") or [],
        "evidence_status": str(metadata.get("evidence_status") or ""),
    }
    canonical = json.dumps(review_payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def editorial_package_approved(content_package):
    """Require explicit human approval metadata; AI generation cannot self-approve."""
    if not isinstance(content_package, dict):
        return False
    metadata = content_package.get("metadata")
    if not isinstance(metadata, dict):
        return False
    return (
        metadata.get("editorial_approved") is True
        and bool(str(metadata.get("approved_by") or "").strip())
        and bool(str(metadata.get("approved_at") or "").strip())
    )
