"""
tools/content_tool.py
──────────────────────
Content quality analyzer tool.
Reads state["scraped_data"] directly.
Writes result to state["content_report"].

Checks:
  word count, readability, broken links,
  duplicate content, content ratio, structure
"""

import httpx
import textstat
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from agent.state import AgentState


WEIGHTS = {
    "word_count":        20,
    "readability":       25,
    "broken_links":      20,
    "duplicate_content": 15,
    "content_ratio":     10,
    "structure":         10,
}


def _extract_text(html: str) -> str:
    """Strips scripts/styles/nav and returns clean readable text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


async def _check_broken_links(soup, base_url: str, max_check: int = 15) -> list:
    """Checks up to max_check links for 4xx/5xx responses."""
    urls_to_check = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue
        full = href if href.startswith("http") else urljoin(base_url, href)
        urls_to_check.append(full)

    urls_to_check = list(dict.fromkeys(urls_to_check))[:max_check]
    broken        = []

    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        for url in urls_to_check:
            try:
                r = await client.head(url)
                if r.status_code >= 400:
                    broken.append({"url": url, "status": r.status_code})
            except Exception:
                broken.append({"url": url, "status": "unreachable"})

    return broken


def _has_duplicate_paragraphs(soup) -> bool:
    """Returns True if any paragraph >50 chars appears more than once."""
    paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 50]
    return len(paras) != len(set(paras))


@tool
async def content_tool(state: AgentState) -> dict:
    """
    Analyzes the content quality of the scraped page.
    Reads HTML from state["scraped_data"].
    Writes the full content report to state["content_report"].
    Call scraper_tool before this.
    """
    scraped_data = state.get("scraped_data", {})

    if not scraped_data.get("success"):
        return {"content_report": {
            "success": False, "content_score": 0,
            "error": scraped_data.get("error", "No scraped data. Call scraper_tool first.")
        }}

    html       = scraped_data["html"]
    final_url  = scraped_data["final_url"]
    parsed_url = urlparse(final_url)
    base_url   = f"{parsed_url.scheme}://{parsed_url.netloc}"
    soup       = BeautifulSoup(html, "lxml")
    main_text  = _extract_text(html)
    issues     = []
    score      = 0

    # ── Word count ───────────────────────────────────────────────────
    words           = main_text.split()
    word_count      = len(words)
    sentences       = [s.strip() for s in main_text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    sentence_count  = len(sentences)
    paragraph_count = len([p for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20])
    avg_wps         = round(word_count / max(sentence_count, 1), 1)

    if word_count >= 600:
        score += WEIGHTS["word_count"]
    elif word_count >= 300:
        score += WEIGHTS["word_count"] * 0.7
        issues.append(f"Thin content ({word_count} words) — aim for 600+")
    elif word_count >= 100:
        score += WEIGHTS["word_count"] * 0.4
        issues.append(f"Very thin content ({word_count} words)")
    else:
        issues.append(f"Almost no readable content ({word_count} words)")

    # ── Readability ──────────────────────────────────────────────────
    if word_count > 50:
        flesch_score = textstat.flesch_reading_ease(main_text)
        flesch_grade = textstat.flesch_kincaid_grade(main_text)
        readability_label = (
            "Very Easy"   if flesch_score >= 90 else
            "Easy"        if flesch_score >= 70 else
            "Fairly Easy" if flesch_score >= 60 else
            "Standard"    if flesch_score >= 50 else
            "Fairly Hard" if flesch_score >= 30 else
            "Difficult"
        )
        if flesch_score >= 60:
            score += WEIGHTS["readability"]
        elif flesch_score >= 40:
            score += WEIGHTS["readability"] * 0.7
            issues.append(f"Hard to read (Flesch: {flesch_score:.1f})")
        else:
            score += WEIGHTS["readability"] * 0.3
            issues.append(f"Very hard to read (Flesch: {flesch_score:.1f})")
    else:
        flesch_score, flesch_grade, readability_label = 0.0, 0.0, "N/A"

    # ── Broken links ─────────────────────────────────────────────────
    broken_links = await _check_broken_links(soup, base_url)
    total_links  = len(soup.find_all("a", href=True))

    if not broken_links:
        score += WEIGHTS["broken_links"]
    else:
        score += WEIGHTS["broken_links"] * max(0, 1 - len(broken_links) / max(total_links, 1))
        issues.append(f"{len(broken_links)} broken links found")

    # ── Duplicate content ────────────────────────────────────────────
    has_duplicates = _has_duplicate_paragraphs(soup)
    if not has_duplicates:
        score += WEIGHTS["duplicate_content"]
    else:
        score += WEIGHTS["duplicate_content"] * 0.3
        issues.append("Duplicate paragraphs detected")

    # ── Content ratio ────────────────────────────────────────────────
    content_ratio = (len(main_text) / max(len(html), 1)) * 100

    if content_ratio >= 15:
        score += WEIGHTS["content_ratio"]
    elif content_ratio >= 8:
        score += WEIGHTS["content_ratio"] * 0.6
        issues.append(f"Low content-to-HTML ratio ({content_ratio:.1f}%)")
    else:
        score += WEIGHTS["content_ratio"] * 0.2
        issues.append(f"Very low content-to-HTML ratio ({content_ratio:.1f}%)")

    # ── Structure ────────────────────────────────────────────────────
    has_lists    = bool(soup.find(["ul", "ol"]))
    has_tables   = bool(soup.find("table"))
    has_headings = bool(soup.find(["h1", "h2", "h3"]))

    score += WEIGHTS["structure"] * (sum([has_lists, has_tables, has_headings]) / 3)

    if not has_headings:
        issues.append("No headings found")
    if not has_lists:
        issues.append("No lists found — consider bullet points")

    print(f"[content_tool] Score: {round(min(score, 100), 1)}/100")
    return {"content_report": {
        "success":                True,
        "content_score":          round(min(score, 100), 1),
        "readability_score":      round(flesch_score, 1),
        "readability_grade":      readability_label,
        "flesch_kincaid_grade":   round(flesch_grade, 1) if word_count > 50 else 0,
        "word_count":             word_count,
        "sentence_count":         sentence_count,
        "paragraph_count":        paragraph_count,
        "avg_words_per_sentence": avg_wps,
        "content_ratio_pct":      round(content_ratio, 1),
        "total_links":            total_links,
        "broken_links_count":     len(broken_links),
        "broken_links":           broken_links,
        "duplicate_content_flag": has_duplicates,
        "has_lists":              has_lists,
        "has_tables":             has_tables,
        "issues":                 issues,
        "issues_count":           len(issues),
    }}