"""
Web Search MCP Service for Apple Support Co-Pilot.
Provides real-time web search grounding when internal RAG fails or lacks sufficient similarity (<0.60).
Queries official Apple Support resources with domain validation and fallback to curated guide sources.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Optional
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

APPROVED_APPLE_DOMAINS = [
    "support.apple.com",
    "apple.com",
    "iforgot.apple.com",
    "reportaproblem.apple.com",
    "checkcoverage.apple.com",
    "locate.apple.com",
]


class WebSearchResult(BaseModel):
    title: str = Field(..., description="Title of the support guide or article")
    snippet: str = Field(..., description="Actionable troubleshooting resolution steps")
    url: str = Field(..., description="Official Apple Support documentation URL")
    source: str = Field(default="apple_support_web", description="Origin source")


class WebSearchService:
    """MCP Web Search integration for retrieving official external Apple Support resolutions."""

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
        self._curated_cache = None

    def _load_curated_knowledge(self) -> List[dict]:
        """Loads fallback curated knowledge sources for fast offline resolution."""
        if self._curated_cache is not None:
            return self._curated_cache

        knowledge_dir = Path(__file__).resolve().parent.parent / "data" / "knowledge_sources"
        items = []

        # Load ifixit guides
        ifixit_file = knowledge_dir / "ifixit_apple_guides.json"
        if ifixit_file.exists():
            try:
                with open(ifixit_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        items.extend(data)
            except Exception as e:
                logger.debug(f"Could not load ifixit guides: {e}")

        # Load synthetic resolutions
        syn_file = knowledge_dir / "synthetic_resolutions.json"
        if syn_file.exists():
            try:
                with open(syn_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        items.extend(data)
            except Exception as e:
                logger.debug(f"Could not load synthetic resolutions: {e}")

        self._curated_cache = items
        return items

    async def search_apple_support(
        self,
        query: str,
        intent: Optional[str] = None,
        max_results: int = 3,
    ) -> List[WebSearchResult]:
        """
        Executes web search for official Apple troubleshooting steps.
        Attempts live search first, with fallback to verified Apple Support knowledge.
        """
        if not query or len(query.strip()) < 3:
            return []

        # 1. Try Live Web Search via DuckDuckGo HTML / instant search
        live_results = await self._live_duckduckgo_search(query, intent, max_results)
        if live_results:
            logger.info(f"Retrieved {len(live_results)} live web search results for query: '{query[:40]}...'")
            return live_results

        # 2. Fallback to Curated Knowledge Index
        logger.info(f"Live web search yielded no direct results. Falling back to curated Apple Knowledge search.")
        return self._fallback_knowledge_search(query, intent, max_results)

    async def _live_duckduckgo_search(
        self,
        query: str,
        intent: Optional[str],
        max_results: int,
    ) -> List[WebSearchResult]:
        clean_q = re.sub(r"@\w+", "", query).strip()
        search_query = f"(site:support.apple.com OR site:apple.com) {clean_q}"
        results: List[WebSearchResult] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": search_query},
                    headers=headers,
                )
                if resp.status_code == 200:
                    html = resp.text
                    # Extract result links and snippets
                    # Pattern matches DuckDuckGo HTML result blocks
                    snippets = re.findall(
                        r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE
                    )
                    urls = re.findall(
                        r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE
                    )
                    titles = re.findall(
                        r'<a class="result__title[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE
                    )

                    for i in range(min(len(snippets), len(urls), max_results)):
                        raw_url = urls[i][0] if isinstance(urls[i], tuple) else urls[i]
                        # DuckDuckGo wraps outbound links in /l/?kh=-1&uddg=...
                        actual_url_match = re.search(r"uddg=([^&]+)", raw_url)
                        if actual_url_match:
                            import urllib.parse
                            actual_url = urllib.parse.unquote(actual_url_match.group(1))
                        else:
                            actual_url = raw_url

                        # Validate domain against approved Apple domains
                        is_approved = any(domain in actual_url.lower() for domain in APPROVED_APPLE_DOMAINS)
                        if not is_approved:
                            actual_url = "https://support.apple.com"

                        clean_snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()
                        raw_title = titles[i][1] if i < len(titles) and isinstance(titles[i], tuple) else f"Apple Support Resolution {i+1}"
                        clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()

                        if clean_snippet:
                            results.append(
                                WebSearchResult(
                                    title=clean_title or "Official Apple Support Article",
                                    snippet=clean_snippet,
                                    url=actual_url,
                                    source="live_apple_web_search",
                                )
                            )
        except Exception as e:
            logger.debug(f"Live web search request failed or timed out: {e}")

        return results

    def _fallback_knowledge_search(
        self,
        query: str,
        intent: Optional[str],
        max_results: int,
    ) -> List[WebSearchResult]:
        """Provides verified Apple Support solutions mapped to the inquiry intent."""
        # Canonical high-authority Apple Support knowledge base map
        CANONICAL_APPLE_KB = {
            "ios_update_bugs": {
                "title": "If your iPhone or iPad won't update or is stuck on Apple logo",
                "snippet": "If an error occurred downloading iOS or your device is unresponsive, connect to Wi-Fi, remove the download from Settings > General > iPhone Storage, and force restart. If stuck on Apple logo, enter Recovery Mode and update via Mac Finder or iTunes without erasing data.",
                "url": "https://support.apple.com/en-us/HT201263",
            },
            "battery_performance": {
                "title": "iPhone Battery and Performance - Official Apple Support",
                "snippet": "To check battery health, go to Settings > Battery > Battery Health & Charging. If maximum capacity is below 80%, service is recommended. To preserve battery life, enable Low Power Mode, turn on Auto-Brightness in Settings > Accessibility > Display & Text Size, and disable Background App Refresh for high-consumption apps.",
                "url": "https://support.apple.com/en-us/HT201435",
            },
            "charging_issues": {
                "title": "If your iPhone won't charge or charges slowly",
                "snippet": "Inspect the charging port for dust or lint using a non-conductive tool under bright light. Try an official Apple MFi-certified USB-C or Lightning cable and a wall adapter that you know works. Allow your device to charge uninterrupted for at least 30 minutes, then perform a force restart.",
                "url": "https://support.apple.com/en-us/HT201569",
            },
            "apple_id_account": {
                "title": "If you forgot your Apple ID password or your account is locked",
                "snippet": "You can safely reset your password and verify your trusted phone number or recovery key at iforgot.apple.com. If your account is locked for security reasons, follow the automated account recovery process from any trusted browser.",
                "url": "https://iforgot.apple.com",
            },
            "purchase_refund_billing": {
                "title": "Request a refund for apps or content that you bought from Apple",
                "snippet": "Sign in to reportaproblem.apple.com with your Apple ID. Choose 'I'd like to', select 'Request a refund', choose the reason, and select the item or subscription charge. Apple reviews refund requests within 48 hours.",
                "url": "https://reportaproblem.apple.com",
            },
            "display_screen": {
                "title": "If the screen isn't working on your iPhone or iPad",
                "snippet": "If touch screen is unresponsive or flickering, force restart your device. Disconnect any Lightning/USB-C accessories. If part of the screen doesn't respond or displays vertical lines, remove any screen protector or case and contact Apple Support to schedule display service.",
                "url": "https://support.apple.com/en-us/HT201406",
            },
            "connectivity_wifi_bluetooth": {
                "title": "If your iPhone or iPad won't connect to a Wi-Fi network or Bluetooth accessory",
                "snippet": "Go to Settings > Wi-Fi, turn it off, wait 15 seconds, and turn it back on. To reset connectivity, tap Settings > General > Transfer or Reset iPhone > Reset > Reset Network Settings. For Bluetooth accessories or AirPods, unpair via Settings > Bluetooth, reset the accessory, and reconnect.",
                "url": "https://support.apple.com/en-us/HT204051",
            },
            "audio_speaker_mic": {
                "title": "If you hear no sound or distorted sound from your iPhone speaker or AirPods",
                "snippet": "Check that the Ring/Silent switch isn't set to silent. Go to Settings > Sounds & Haptics and drag the Ringtone slider. If sound is muffled, clear any debris from speaker mesh with a clean, dry, soft-bristled brush. For AirPods, perform a hardware reset by holding the setup button for 15 seconds.",
                "url": "https://support.apple.com/en-us/HT203794",
            },
            "app_crashes": {
                "title": "If an app on your iPhone or iPad stops responding, closes unexpectedly, or won't open",
                "snippet": "Force close the app by swiping up from the bottom of the screen. Restart your device. Open the App Store, tap your profile icon, and update the app. If the issue persists, delete and reinstall the app from the App Store.",
                "url": "https://support.apple.com/en-us/HT201398",
            },
            "hardware_damage": {
                "title": "iPhone Repair & Service - Official Apple Support",
                "snippet": "For cracked screens, back glass damage, or water exposure, check your AppleCare+ coverage and estimate service costs at support.apple.com/repair. Back up your device to iCloud or Mac before bringing it to an Apple Store or Authorized Service Provider.",
                "url": "https://support.apple.com/repair",
            },
            "lost_device_find_my": {
                "title": "Locate a lost device or item with Find My",
                "snippet": "Open the Find My app on a trusted Apple device or sign in to icloud.com/find. Select your device or item to view its location on a map, play a sound to locate it nearby, or mark it as lost to lock it remotely.",
                "url": "https://www.apple.com/icloud/find-my/",
            },
            "trade_in_exchange": {
                "title": "Apple Trade In - Official Exchange Process & Value",
                "snippet": "You can trade in your eligible iPhone for credit toward your next purchase or an Apple Gift Card. Answer a few questions about your device online to get an estimated trade-in value, back up your data, and use the prepaid trade-in kit to mail it in or bring it to an Apple Store.",
                "url": "https://www.apple.com/shop/trade-in",
            },
        }

        results: List[WebSearchResult] = []

        # 1. Match by query keywords (e.g. trade-in, exchange) or intent
        query_lower = query.lower()
        if any(w in query_lower for w in ["trade in", "trade-in", "exchange", "trade my", "upgrade"]):
            trade_guide = CANONICAL_APPLE_KB.get("trade_in_exchange")
            if trade_guide:
                results.append(
                    WebSearchResult(
                        title=trade_guide["title"],
                        snippet=trade_guide["snippet"],
                        url=trade_guide["url"],
                        source="verified_apple_kb_index",
                    )
                )
        elif intent and intent in CANONICAL_APPLE_KB:
            guide = CANONICAL_APPLE_KB[intent]
            results.append(
                WebSearchResult(
                    title=guide["title"],
                    snippet=guide["snippet"],
                    url=guide["url"],
                    source="verified_apple_kb_index",
                )
            )

        # 2. Check curated files for additional relevant articles
        curated_items = self._load_curated_knowledge()
        query_words = set(re.findall(r"\b\w{4,}\b", query.lower()))

        scored_items = []
        for item in curated_items:
            text = (item.get("question") or item.get("title") or item.get("summary") or "").lower()
            res = (item.get("resolution") or item.get("steps") or item.get("content") or "").strip()
            if not res or len(res) < 20:
                continue

            matches = sum(1 for w in query_words if w in text)
            if matches > 0:
                scored_items.append((matches, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        for _, item in scored_items[:max_results]:
            title = item.get("title") or item.get("question") or "Apple Troubleshooting Guide"
            snippet = item.get("resolution") or item.get("steps") or item.get("summary") or ""
            url = item.get("url") or "https://support.apple.com"
            results.append(
                WebSearchResult(
                    title=title,
                    snippet=snippet[:250],
                    url=url,
                    source="curated_apple_guides",
                )
            )

        # Ensure at least one verified fallback if empty
        if not results:
            results.append(
                WebSearchResult(
                    title="Official Apple Support Knowledge Base",
                    snippet="Check settings, restart your Apple device, and ensure your system is running the latest software update. For personalized diagnostics, contact official Apple Support.",
                    url="https://support.apple.com",
                    source="verified_apple_kb_index",
                )
            )

        return results[:max_results]

