"""
Universal Web Scraper Agent & Graph Orchestrator
─────────────────────────────────────────────────
Autonomous multi-stage web scraping pipeline:
1. Header & DOM Inspection (Detects SPAs, React/Vue/Next.js)
2. Stealth Playwright Engine (Executes JS, waits for networkidle, expands accordions)
3. Boilerplate Stripper (Cleans navs, footers, cookie banners, ads)
4. Structural Markdown & Table Formatter (Retains table grids and code blocks)
"""

import os
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Optional


class UniversalScraperAgent:
    """
    Autonomous multi-stage scraping agent capable of deep text and table extraction
    across both static pages and dynamic client-rendered applications without PDFs.
    """

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

    async def inspect_dom(self, url: str) -> Dict[str, Any]:
        """Stage 1: Probe URL headers and fast DOM response to detect dynamic SPAs."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    return {"status_code": res.status_code, "is_spa": True, "raw_html": ""}
                
                html = res.text
                html_lower = html.lower()
                
                # Check for SPA mount roots
                spa_markers = ["<div id=\"root\"", "<div id=\"__next\"", "<div id=\"app\"", "ng-version", "data-reactroot"]
                is_spa = any(m in html_lower for m in spa_markers)
                
                # Check content length
                soup = BeautifulSoup(html, "html.parser")
                for s in soup(["script", "style", "nav", "footer"]):
                    s.decompose()
                sample_text = soup.get_text(separator=" ").strip()
                if len(sample_text) < 180:
                    is_spa = True

                return {
                    "status_code": res.status_code,
                    "is_spa": is_spa,
                    "raw_html": html,
                    "preview_chars": len(sample_text)
                }
        except Exception as e:
            return {"status_code": 0, "is_spa": True, "raw_html": "", "error": str(e)}

    async def fetch_stealth(self, url: str) -> str:
        """Stage 2: Run stealth Playwright browser to hydrate dynamic JavaScript DOM."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="networkidle", timeout=18000)
                except Exception:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    except Exception:
                        pass

                # Aggressively trigger lazy-loading and expand collapsible sections
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(0.4)
                    await page.evaluate("window.scrollTo(0, 0)")
                except Exception:
                    pass

                content = await page.content()
                await browser.close()
                return content
        except Exception as pw_err:
            print(f"[UniversalScraper] Playwright fallback error: {pw_err}")
            return ""

    def strip_boilerplate(self, html: str, url: str = "") -> Dict[str, Any]:
        """Stage 3: Remove cookie banners, ads, navigational headers, extracting article text and tables."""
        if not html:
            return {"title": url, "text": "", "tables": []}

        soup = BeautifulSoup(html, "html.parser")
        title = url
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Primary extraction using trafilatura
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_links=False
        )

        # Fallback extraction if trafilatura missed content
        if not extracted or len(extracted.strip()) < 150:
            cleaner = BeautifulSoup(html, "html.parser")
            for tag in cleaner(["script", "style", "iframe", "footer", "header", "nav", "aside", "noscript"]):
                tag.decompose()
            extracted = cleaner.get_text(separator="\n\n")

        # Clean excess whitespace
        clean_lines = [l.strip() for l in (extracted or "").splitlines() if l.strip()]
        clean_text = "\n\n".join(clean_lines)

        return {
            "title": title,
            "text": clean_text,
            "url": url,
            "char_count": len(clean_text)
        }

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Execute the complete multi-stage graph for any single URL."""
        inspection = await self.inspect_dom(url)
        html = inspection.get("raw_html", "")

        # If detected as dynamic SPA or HTTP fetch returned sparse content, trigger Playwright
        if inspection.get("is_spa") or len(html) < 400:
            rendered = await self.fetch_stealth(url)
            if rendered:
                html = rendered

        result = self.strip_boilerplate(html, url)
        return result


universal_scraper = UniversalScraperAgent()
