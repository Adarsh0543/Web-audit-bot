"""
tools/db/db_save_tool.py
─────────────────────────
Reads seo_report, accessibility_report, content_report
directly from state and saves them to MySQL.
"""

import json
# from langchain_core.tools import tool
from database.executor import execute_safe
from tools.db.db_helper_tool import get_or_create_site
from agent.state import AgentState


# @tool
async def db_save_tool(state: AgentState) -> dict:
    """
    Saves analysis reports to MySQL.
    Reads all reports directly from state.
    Call after running analyzer tools.
    """
    print('reached save.py file')
    url                  = state.get("url", "")
    seo_report           = state.get("seo_report", {})
    accessibility_report = state.get("accessibility_report", {})
    content_report       = state.get("content_report", {})

    site_id = get_or_create_site(url)
    if not site_id:
        print('failed to generate id')
        return {"db_result": {"success": False, "error": "Could not create site record."}}

    saved = []
    print('starting to save seo report')
    if seo_report.get("success"):
        r = seo_report
        execute_safe(
            """
            INSERT INTO seo_reports (
                site_id, url, seo_score,
                has_meta_title, meta_title, meta_title_length,
                has_meta_description, meta_description, meta_description_length,
                h1_count, h2_count, h3_count, h1_text,
                total_images, images_with_alt, images_without_alt,
                internal_links, external_links,
                has_robots_txt, has_sitemap, page_size_kb, issues
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                site_id, url, r["seo_score"],
                r["has_meta_title"], r["meta_title"], r["meta_title_length"],
                r["has_meta_description"], r["meta_description"], r["meta_description_length"],
                r["h1_count"], r["h2_count"], r["h3_count"], r["h1_text"],
                r["total_images"], r["images_with_alt"], r["images_without_alt"],
                r["internal_links"], r["external_links"],
                r["has_robots_txt"], r["has_sitemap"],
                r["page_size_kb"], json.dumps(r["issues"])
            )
        )
        saved.append("SEO report")

    if accessibility_report.get("success"):
        r = accessibility_report
        execute_safe(
            """
            INSERT INTO accessibility_reports (
                site_id, url, accessibility_score,
                images_missing_alt, inputs_missing_labels, total_form_inputs,
                aria_landmarks_count, aria_labels_count,
                has_main_tag, has_nav_tag, has_header_tag, has_footer_tag,
                has_lang_attribute, lang_value, has_skip_link, issues
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                site_id, url, r["accessibility_score"],
                r["images_missing_alt"], r["inputs_missing_labels"], r["total_form_inputs"],
                r["aria_landmarks_count"], r["aria_labels_count"],
                r["has_main_tag"], r["has_nav_tag"], r["has_header_tag"], r["has_footer_tag"],
                r["has_lang_attribute"], r["lang_value"], r["has_skip_link"],
                json.dumps(r["issues"])
            )
        )
        saved.append("Accessibility report")

    if content_report.get("success"):
        r = content_report
        execute_safe(
            """
            INSERT INTO content_reports (
                site_id, url, content_score,
                readability_score, readability_grade,
                word_count, sentence_count, paragraph_count,
                avg_words_per_sentence, total_links,
                broken_links_count, broken_links,
                duplicate_content_flag, issues
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                site_id, url, r["content_score"],
                r["readability_score"], r["readability_grade"],
                r["word_count"], r["sentence_count"], r["paragraph_count"],
                r["avg_words_per_sentence"], r["total_links"],
                r["broken_links_count"], json.dumps(r["broken_links"]),
                r["duplicate_content_flag"], json.dumps(r["issues"])
            )
        )
        saved.append("Content report")

    msg = f"Saved: {', '.join(saved)}" if saved else "No completed reports to save."
    print(f"[db_save_tool] {msg}")
    return {"db_result": {"success": True, "message": msg}}