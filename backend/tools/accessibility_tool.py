"""
tools/accessibility_tool.py
─────────────────────────────
Accessibility analyzer tool.
Reads state["scraped_data"] directly.
Writes result to state["accessibility_report"].

Checks:
  image alts, form labels, ARIA, semantic HTML,
  lang attribute, skip link, button text, link text, headings
"""

from bs4 import BeautifulSoup
from langchain_core.tools import tool
from agent.state import AgentState


WEIGHTS = {
    "image_alts":    20,
    "form_labels":   15,
    "aria":          10,
    "semantic_html": 15,
    "lang":          10,
    "skip_link":      5,
    "button_text":   10,
    "link_text":     10,
    "headings":       5,
}


@tool
async def accessibility_tool(state: AgentState) -> dict:
    """
    Analyzes the accessibility compliance of the scraped page.
    Reads HTML from state["scraped_data"].
    Writes the full accessibility report to state["accessibility_report"].
    Call scraper_tool before this.
    """
    scraped_data = state.get("scraped_data", {})

    if not scraped_data.get("success"):
        return {"accessibility_report": {
            "success": False, "accessibility_score": 0,
            "error": scraped_data.get("error", "No scraped data. Call scraper_tool first.")
        }}

    soup   = BeautifulSoup(scraped_data["html"], "lxml")
    issues = []
    score  = 0

    # ── Image alts ───────────────────────────────────────────────────
    all_images         = soup.find_all("img")
    missing_alt_imgs   = [img for img in all_images if img.get("alt") is None]
    decorative_imgs    = [
        img for img in all_images
        if img.get("alt") is not None
        and img.get("alt", "").strip() == ""
        and img.get("role") != "presentation"
    ]
    images_missing_alt = len(missing_alt_imgs)

    if not all_images or images_missing_alt == 0:
        score += WEIGHTS["image_alts"]
        if decorative_imgs:
            issues.append(f"{len(decorative_imgs)} images have empty alt — verify intentionally decorative")
    else:
        score += WEIGHTS["image_alts"] * (1 - images_missing_alt / len(all_images))
        issues.append(f"{images_missing_alt} images missing alt attribute")

    # ── Form labels ──────────────────────────────────────────────────
    inputs         = soup.find_all("input", type=lambda t: t not in ["hidden", "submit", "button", "reset"])
    all_inputs     = inputs + soup.find_all("textarea") + soup.find_all("select")
    total_inputs   = len(all_inputs)
    missing_labels = 0

    for inp in all_inputs:
        inp_id    = inp.get("id")
        has_label = (
            (inp_id and soup.find("label", attrs={"for": inp_id})) or
            inp.get("aria-label", "").strip() or
            inp.get("aria-labelledby", "").strip() or
            inp.find_parent("label")
        )
        if not has_label:
            missing_labels += 1

    if total_inputs == 0 or missing_labels == 0:
        score += WEIGHTS["form_labels"]
    else:
        score += WEIGHTS["form_labels"] * (1 - missing_labels / total_inputs)
        issues.append(f"{missing_labels}/{total_inputs} form inputs missing labels")

    # ── ARIA ─────────────────────────────────────────────────────────
    aria_landmarks   = soup.find_all(attrs={"role": True})
    aria_labels      = soup.find_all(attrs={"aria-label": True})
    aria_count       = len(aria_landmarks)
    aria_label_count = len(aria_labels)

    if aria_count > 0:
        score += WEIGHTS["aria"]
    else:
        issues.append("No ARIA landmark roles found")

    # ── Semantic HTML ────────────────────────────────────────────────
    has_main   = bool(soup.find("main"))
    has_nav    = bool(soup.find("nav"))
    has_header = bool(soup.find("header"))
    has_footer = bool(soup.find("footer"))

    semantic_count = sum([has_main, has_nav, has_header, has_footer])
    score         += WEIGHTS["semantic_html"] * (semantic_count / 4)

    missing_tags = [tag for tag, present in [
        ("<main>", has_main), ("<nav>", has_nav),
        ("<header>", has_header), ("<footer>", has_footer)
    ] if not present]

    if missing_tags:
        issues.append(f"Missing semantic HTML: {', '.join(missing_tags)}")

    # ── Language attribute ───────────────────────────────────────────
    html_tag   = soup.find("html")
    lang_value = html_tag.get("lang", "").strip() if html_tag else ""
    has_lang   = bool(lang_value)

    if has_lang:
        score += WEIGHTS["lang"]
    else:
        issues.append("Missing lang attribute on <html>")

    # ── Skip link ────────────────────────────────────────────────────
    has_skip_link = any(
        any(p in a.get_text(strip=True).lower() for p in ["skip", "jump to"])
        and a.get("href", "").startswith("#")
        for a in soup.find_all("a", href=True)
    )

    if has_skip_link:
        score += WEIGHTS["skip_link"]
    else:
        issues.append("No skip navigation link found")

    # ── Button text ──────────────────────────────────────────────────
    empty_buttons = [
        btn for btn in soup.find_all("button")
        if not btn.get_text(strip=True)
        and not btn.get("aria-label", "").strip()
        and not btn.get("aria-labelledby", "").strip()
        and not any(img.get("alt", "").strip() for img in btn.find_all("img"))
    ]

    if not empty_buttons:
        score += WEIGHTS["button_text"]
    else:
        issues.append(f"{len(empty_buttons)} buttons have no accessible text")

    # ── Link text ────────────────────────────────────────────────────
    bad_texts   = {"click here", "here", "read more", "more", "link", "this"}
    all_links   = soup.find_all("a", href=True)
    bad_links   = sum(1 for a in all_links if a.get_text(strip=True).lower() in bad_texts)
    empty_links = sum(
        1 for a in all_links
        if not a.get_text(strip=True) and not a.get("aria-label", "").strip()
    )

    link_issues = bad_links + empty_links
    if link_issues == 0:
        score += WEIGHTS["link_text"]
    else:
        score += WEIGHTS["link_text"] * max(0, 1 - link_issues / max(len(all_links), 1))
        if empty_links:
            issues.append(f"{empty_links} links have no text content")
        if bad_links:
            issues.append(f"{bad_links} links use non-descriptive text")

    # ── Headings ─────────────────────────────────────────────────────
    if soup.find(["h1", "h2", "h3", "h4", "h5", "h6"]):
        score += WEIGHTS["headings"]
    else:
        issues.append("No heading tags found")

    print(f"[accessibility_tool] Score: {round(min(score, 100), 1)}/100")
    return {"accessibility_report": {
        "success":               True,
        "accessibility_score":   round(min(score, 100), 1),
        "images_missing_alt":    images_missing_alt,
        "total_images":          len(all_images),
        "total_form_inputs":     total_inputs,
        "inputs_missing_labels": missing_labels,
        "aria_landmarks_count":  aria_count,
        "aria_labels_count":     aria_label_count,
        "has_main_tag":          has_main,
        "has_nav_tag":           has_nav,
        "has_header_tag":        has_header,
        "has_footer_tag":        has_footer,
        "has_lang_attribute":    has_lang,
        "lang_value":            lang_value,
        "has_skip_link":         has_skip_link,
        "empty_buttons_count":   len(empty_buttons),
        "bad_links_count":       bad_links,
        "empty_links_count":     empty_links,
        "issues":                issues,
        "issues_count":          len(issues),
    }}