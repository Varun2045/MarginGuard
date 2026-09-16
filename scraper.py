import asyncio
import os
import re
from typing import Dict, Any

class CompetitorScraper:
    """
    Headless Browser Agent using Playwright to render JS-heavy menus and pricing tables.
    """
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_page_content(self, url: str) -> Dict[str, Any]:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                try:
                    await page.goto(url, wait_until="load", timeout=25000)
                    for selector in ["button:has-text('Accept')", "button:has-text('Agree')", ".cookie-accept", "#accept-cookies"]:
                        if await page.locator(selector).count() > 0:
                            try:
                                await page.locator(selector).first.click(timeout=1000)
                            except Exception:
                                pass
                    
                    try:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                        await asyncio.sleep(0.5)
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass

                    content = await page.content()
                    title = await page.title()
                    
                    os.makedirs("./data/screenshots", exist_ok=True)
                    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', url.split("//")[-1])[:25]
                    screenshot_path = os.path.join(".", "data", "screenshots", f"{clean_name}.png")
                    await page.screenshot(path=screenshot_path)

                    return {
                        "url": url,
                        "title": title,
                        "html": content,
                        "screenshot_path": screenshot_path,
                        "status": "success"
                    }
                except Exception as e:
                    return {"url": url, "status": "error", "error": str(e)}
                finally:
                    await browser.close()
        except Exception as e:
            return {"url": url, "status": "error", "error": str(e)}
