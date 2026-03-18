"""
tools/db/db_save_tool.py
─────────────────────────
Reads seo_report, accessibility_report, content_report
directly from state and UPSERTS them to MySQL.

UPSERT = INSERT if site not seen before, UPDATE if site already exists.
No duplicates ever — same site always has one row per report table.
"""

import json
from database.executor import execute_safe
from tools.db.db_helper_tool import get_or_create_site
from agent.state import AgentState


async def db_save_tool(state: AgentState) -> dict:
    """
    Upserts analysis reports to MySQL.
    Reads all reports directly from state.
    Call after running analyzer tools.
    """
    print("[db_save_tool] reached save file")
    url                  = state.get("url", "")
    seo_report           = state.get("seo_report", {})
    accessibility_report = state.get("accessibility_report", {})
    content_report       = state.get("content_report", {})

    site_id = get_or_create_site(url)
    if not site_id:
        return {"db_result": {"success": False, "error": "Could not create site record."}}

    saved = []

    # ── SEO report UPSERT ─────────────────────────────────────────────
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
            ON DUPLICATE KEY UPDATE
                seo_score              = VALUES(seo_score),
                has_meta_title         = VALUES(has_meta_title),
                meta_title             = VALUES(meta_title),
                meta_title_length      = VALUES(meta_title_length),
                has_meta_description   = VALUES(has_meta_description),
                meta_description       = VALUES(meta_description),
                meta_description_length= VALUES(meta_description_length),
                h1_count               = VALUES(h1_count),
                h2_count               = VALUES(h2_count),
                h3_count               = VALUES(h3_count),
                h1_text                = VALUES(h1_text),
                total_images           = VALUES(total_images),
                images_with_alt        = VALUES(images_with_alt),
                images_without_alt     = VALUES(images_without_alt),
                internal_links         = VALUES(internal_links),
                external_links         = VALUES(external_links),
                has_robots_txt         = VALUES(has_robots_txt),
                has_sitemap            = VALUES(has_sitemap),
                page_size_kb           = VALUES(page_size_kb),
                issues                 = VALUES(issues),
                analyzed_at            = CURRENT_TIMESTAMP
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
        saved.append("SEO")

    # ── Accessibility report UPSERT ───────────────────────────────────
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
            ON DUPLICATE KEY UPDATE
                accessibility_score  = VALUES(accessibility_score),
                images_missing_alt   = VALUES(images_missing_alt),
                inputs_missing_labels= VALUES(inputs_missing_labels),
                total_form_inputs    = VALUES(total_form_inputs),
                aria_landmarks_count = VALUES(aria_landmarks_count),
                aria_labels_count    = VALUES(aria_labels_count),
                has_main_tag         = VALUES(has_main_tag),
                has_nav_tag          = VALUES(has_nav_tag),
                has_header_tag       = VALUES(has_header_tag),
                has_footer_tag       = VALUES(has_footer_tag),
                has_lang_attribute   = VALUES(has_lang_attribute),
                lang_value           = VALUES(lang_value),
                has_skip_link        = VALUES(has_skip_link),
                issues               = VALUES(issues),
                analyzed_at          = CURRENT_TIMESTAMP
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
        saved.append("Accessibility")

    # ── Content report UPSERT ─────────────────────────────────────────
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
            ON DUPLICATE KEY UPDATE
                content_score          = VALUES(content_score),
                readability_score      = VALUES(readability_score),
                readability_grade      = VALUES(readability_grade),
                word_count             = VALUES(word_count),
                sentence_count         = VALUES(sentence_count),
                paragraph_count        = VALUES(paragraph_count),
                avg_words_per_sentence = VALUES(avg_words_per_sentence),
                total_links            = VALUES(total_links),
                broken_links_count     = VALUES(broken_links_count),
                broken_links           = VALUES(broken_links),
                duplicate_content_flag = VALUES(duplicate_content_flag),
                issues                 = VALUES(issues),
                analyzed_at            = CURRENT_TIMESTAMP
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
        saved.append("Content")

    msg = f"Upserted: {', '.join(saved)} report(s)" if saved else "No completed reports to save."
    print(f"[db_save_tool] {msg}")
    return {"db_result": {"success": True, "message": msg}}