"""
tools/seo_tool.py
──────────────────
SEO analyzer tool.
Reads state["scraped_data"] directly.
Writes result to state["seo_report"].

Checks:
  meta title, meta description, H1, heading hierarchy,
  image alts, links, robots.txt, sitemap.xml, page size, canonical
"""

import httpx
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from agent.state import AgentState


WEIGHTS = {
    "meta_title":        15,
    "meta_description":  15,
    "h1_tag":            15,
    "heading_hierarchy": 10,
    "image_alts":        15,
    "links":              5,
    "robots_txt":         5,
    "sitemap":            5,
    "page_size":         10,
    "canonical":          5,
}


async def _check_url(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            r = await client.get(url)
            return r.status_code == 200
    except Exception:
        return False


@tool
async def seo_tool(state: AgentState) -> dict:
    """
    Analyzes the SEO quality of the scraped page.
    Reads HTML from state["scraped_data"].
    Writes the full SEO report to state["seo_report"].
    Call scraper_tool before this.
    """
    scraped_data = state.get("scraped_data", {})

    if not scraped_data.get("success"):
        print('No scrapped data')
        return {"seo_report": {
            "success": False, "seo_score": 0,
            "error": scraped_data.get("error", "No scraped data. Call scraper_tool first.")
        }}

    html         = scraped_data["html"]
    final_url    = scraped_data["final_url"]
    page_size_kb = scraped_data["page_size_kb"]
    soup         = BeautifulSoup(html, "lxml")
    parsed_url   = urlparse(final_url)
    base_url     = f"{parsed_url.scheme}://{parsed_url.netloc}"
    issues       = []
    score        = 0
    # ── Meta title ───────────────────────────────────────────────────
    title_tag  = soup.find("title")
    has_title  = title_tag is not None and bool(title_tag.get_text(strip=True))
    title_text = title_tag.get_text(strip=True) if has_title else ""
    title_len  = len(title_text)

    if not has_title:
        issues.append("Missing meta title")
    elif title_len < 30:
        score += WEIGHTS["meta_title"] * 0.5
        issues.append(f"Meta title too short ({title_len} chars, aim for 50-60)")
    elif title_len > 70:
        score += WEIGHTS["meta_title"] * 0.7
        issues.append(f"Meta title too long ({title_len} chars, aim for 50-60)")
    else:
        score += WEIGHTS["meta_title"]

    # ── Meta description ─────────────────────────────────────────────
    desc_tag  = soup.find("meta", attrs={"name": "Description"})
    has_desc  = desc_tag is not None and bool(desc_tag.get("content", "").strip())
    desc_text = desc_tag.get("content", "").strip() if has_desc else ""
    desc_len  = len(desc_text)

    if not has_desc:
        issues.append("Missing meta description")
    elif desc_len < 70:
        score += WEIGHTS["meta_description"] * 0.5
        issues.append(f"Meta description too short ({desc_len} chars, aim for 150-160)")
    elif desc_len > 170:
        score += WEIGHTS["meta_description"] * 0.7
        issues.append(f"Meta description too long ({desc_len} chars, aim for 150-160)")
    else:
        score += WEIGHTS["meta_description"]

    # ── H1 tag ───────────────────────────────────────────────────────
    h1_tags  = soup.find_all("h1")
    h1_count = len(h1_tags)
    h1_text  = h1_tags[0].get_text(strip=True) if h1_tags else ""

    if h1_count == 0:
        issues.append("No H1 tag found — every page needs exactly one H1")
    elif h1_count > 1:
        score += WEIGHTS["h1_tag"] * 0.5
        issues.append(f"Multiple H1 tags ({h1_count}) — use only one")
    else:
        score += WEIGHTS["h1_tag"]

    # ── Heading hierarchy ────────────────────────────────────────────
    h2_tags    = soup.find_all("h2")
    h3_tags    = soup.find_all("h3")
    h4_tags    = soup.find_all("h4")
    heading_ok = True

    if h3_tags and not h2_tags:
        issues.append("H3 used without H2 — maintain heading hierarchy")
        heading_ok = False
    if h4_tags and not h3_tags:
        issues.append("H4 used without H3 — maintain heading hierarchy")
        heading_ok = False

    score += WEIGHTS["heading_hierarchy"] if heading_ok else WEIGHTS["heading_hierarchy"] * 0.5

    # ── Image alts ───────────────────────────────────────────────────
    all_images      = soup.find_all("img")
    total_images    = len(all_images)
    missing_alt     = [img for img in all_images if not img.get("alt", "").strip()]
    images_with_alt = total_images - len(missing_alt)

    if total_images == 0 or not missing_alt:
        score += WEIGHTS["image_alts"]
    else:
        score += WEIGHTS["image_alts"] * (images_with_alt / total_images)
        issues.append(f"{len(missing_alt)}/{total_images} images missing alt attributes")

    # ── Links ────────────────────────────────────────────────────────
    internal_links = 0
    external_links = 0

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            if parsed_url.netloc in href:
                internal_links += 1
            else:
                external_links += 1
        elif href.startswith("/") or not href.startswith("#"):
            internal_links += 1

    if internal_links > 0:
        score += WEIGHTS["links"]
    else:
        issues.append("No internal links found")

    # ── robots.txt ───────────────────────────────────────────────────
    has_robots = await _check_url(urljoin(base_url, "/robots.txt"))
    if has_robots:
        score += WEIGHTS["robots_txt"]
    else:
        issues.append("robots.txt not found")

    # ── sitemap.xml ──────────────────────────────────────────────────
    has_sitemap = await _check_url(urljoin(base_url, "/sitemap.xml"))
    if has_sitemap:
        score += WEIGHTS["sitemap"]
    else:
        issues.append("sitemap.xml not found")

    # ── Page size ────────────────────────────────────────────────────
    if page_size_kb < 500:
        score += WEIGHTS["page_size"]
    elif page_size_kb < 1000:
        score += WEIGHTS["page_size"] * 0.7
        issues.append(f"Page size is large ({page_size_kb:.1f} KB)")
    else:
        score += WEIGHTS["page_size"] * 0.3
        issues.append(f"Page size too large ({page_size_kb:.1f} KB)")

    # ── Canonical tag ────────────────────────────────────────────────
    canonical     = soup.find("link", attrs={"rel": "canonical"})
    has_canonical = canonical is not None
    if has_canonical:
        score += WEIGHTS["canonical"]
    else:
        issues.append("No canonical tag found")

    print(f"[seo_tool] Score: {round(min(score, 100), 1)}/100")
    return {"seo_report": {
        "success":                 True,
        "seo_score":               round(min(score, 100), 1),
        "has_meta_title":          has_title,
        "meta_title":              title_text,
        "meta_title_length":       title_len,
        "has_meta_description":    has_desc,
        "meta_description":        desc_text,
        "meta_description_length": desc_len,
        "h1_count":                h1_count,
        "h2_count":                len(h2_tags),
        "h3_count":                len(h3_tags),
        "h1_text":                 h1_text,
        "total_images":            total_images,
        "images_with_alt":         images_with_alt,
        "images_without_alt":      len(missing_alt),
        "internal_links":          internal_links,
        "external_links":          external_links,
        "has_robots_txt":          has_robots,
        "has_sitemap":             has_sitemap,
        "has_canonical":           has_canonical,
        "page_size_kb":            page_size_kb,
        "issues":                  issues,
        "issues_count":            len(issues),
    }}