import os
import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from models import MenuItem, CompetitorSnapshot

class MenuExtractor:
    """
    Extracts structured pricing data from rendered HTML / text using LLM or structured parsing.
    """
    def __init__(self, api_key: str = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider

    def clean_html_to_text(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines[:300])

    def extract_items_from_html(self, competitor_id: str, competitor_name: str, url: str, html_content: str) -> CompetitorSnapshot:
        # If an LLM API key is present, call LLM
        if self.api_key and self.provider == "gemini":
            cleaned_text = self.clean_html_to_text(html_content)
            items = self._call_gemini_extraction(competitor_name, cleaned_text)
            if items:
                return CompetitorSnapshot(
                    competitor_id=competitor_id,
                    competitor_name=competitor_name,
                    url=url,
                    items=items
                )
        
        # DOM & HTML-aware heuristic extraction
        items = self._dom_heuristic_extraction(html_content)
        return CompetitorSnapshot(
            competitor_id=competitor_id,
            competitor_name=competitor_name,
            url=url,
            items=items
        )

    def _call_gemini_extraction(self, competitor_name: str, text_content: str) -> List[MenuItem]:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        prompt = f"""Extract all services/treatments/products and their prices from this competitor website text ({competitor_name}).
Format as pure JSON with this structure:
[
  {{"name": "Service Name", "category": "Category", "price": 120.0, "currency": "USD", "unit": "session", "description": "brief desc"}}
]
Website text:
{text_content}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        try:
            resp = httpx.post(url, json=payload, timeout=20.0)
            if resp.status_code == 200:
                raw_json = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(raw_json)
                return [MenuItem(**item) for item in data if "name" in item and "price" in item]
        except Exception:
            pass
        return []

    def _dom_heuristic_extraction(self, html_content: str) -> List[MenuItem]:
        items = []
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. Check for table rows <tr><td>Name</td><td>Price</td></tr>
        for row in soup.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) >= 2:
                for i, col in enumerate(cols):
                    price_match = re.search(r"[\$£€]?\s*([0-9]+(?:\.[0-9]{2})?)", col)
                    if price_match and col.startswith(("$", "£", "€", "AED")) or (price_match and i > 0):
                        try:
                            price_val = float(price_match.group(1))
                            service_name = cols[0]
                            if 5.0 <= price_val <= 10000.0 and len(service_name) > 2 and service_name.lower() not in ["price", "treatment", "service"]:
                                items.append(MenuItem(name=service_name, category="Aesthetics", price=price_val, currency="USD", unit="session"))
                                break
                        except ValueError:
                            continue

        # 2. Check for card blocks with headers and prices
        for card in soup.find_all(["div", "section", "article", "li"]):
            h_tag = card.find(["h2", "h3", "h4", "h5", "strong", ".title", ".name"])
            if h_tag:
                name = h_tag.get_text(strip=True)
                card_text = card.get_text(separator=" ")
                price_match = re.search(r"[\$£€]\s*([0-9]+(?:\.[0-9]{2})?)", card_text)
                if price_match and name and len(name) > 3 and not any(it.name == name for it in items):
                    try:
                        price_val = float(price_match.group(1))
                        if 5.0 <= price_val <= 10000.0:
                            items.append(MenuItem(name=name, category="Aesthetics", price=price_val, currency="USD", unit="session"))
                    except ValueError:
                        continue

        # 3. Text-based sequential fallback
        if not items:
            cleaned_text = self.clean_html_to_text(html_content)
            lines = [l.strip() for l in cleaned_text.splitlines() if l.strip()]
            for idx, line in enumerate(lines):
                price_match = re.search(r"[\$£€]\s*([0-9]+(?:\.[0-9]{2})?)", line)
                if price_match and idx > 0:
                    prev_line = lines[idx - 1]
                    try:
                        price_val = float(price_match.group(1))
                        if 5.0 <= price_val <= 10000.0 and len(prev_line) > 3:
                            items.append(MenuItem(name=prev_line, category="Aesthetics", price=price_val, currency="USD", unit="session"))
                    except ValueError:
                        continue
        return items
