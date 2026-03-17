"""
scraper/scraper.py
───────────────────
Pure scraping logic — no LangGraph, no @tool, no agent.
Only exports scrape_page() which is called directly by
scrape_node in graph.py.
"""

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


async def scrape_page(url: str, timeout_ms: int = 30000) -> dict:
    """
    Scrapes a URL using Playwright headless Chromium.

    Returns:
    {
        "success":      bool,
        "url":          str,   original url
        "final_url":    str,   url after redirects
        "html":         str,   full page HTML
        "page_size_kb": float,
        "status_code":  int,
        "error":        str | None
    }
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True
        )
        page        = await context.new_page()
        status_code = 200
        final_url   = url

        try:
            response = await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            if response:
                status_code = response.status
                final_url   = page.url

            html         = await page.content()
            page_size_kb = round(len(html.encode("utf-8")) / 1024, 2)
            await browser.close()

            return {
                "success":      True,
                "url":          url,
                "final_url":    final_url,
                "html":         html,
                "page_size_kb": page_size_kb,
                "status_code":  status_code,
                "error":        None
            }

        except PlaywrightTimeout:
            await browser.close()
            return {
                "success":      False,
                "url":          url,
                "final_url":    url,
                "html":         "",
                "page_size_kb": 0,
                "status_code":  0,
                "error":        f"Timeout: page did not respond within {timeout_ms // 1000}s"
            }

        except Exception as e:
            await browser.close()
            return {
                "success":      False,
                "url":          url,
                "final_url":    url,
                "html":         "",
                "page_size_kb": 0,
                "status_code":  0,
                "error":        f"Scrape failed: {str(e)}"
            }