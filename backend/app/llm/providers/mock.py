"""
Deterministic Mock LLM Provider for unit testing, CI, and offline smoke tests.
Does not require any external runtime or API keys.
"""

import hashlib
import json
import re
import time
from typing import AsyncIterator, List, Optional, Type
from pydantic import BaseModel

from app.llm.base import LLMProvider, LLMResponse, T


class MockProvider(LLMProvider):
    """Deterministic Mock Provider simulating an LLM with structured outputs."""

    def __init__(self, model_name: str = "mock-agent-model"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def health(self) -> bool:
        return True

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        start = time.time()
        
        # Isolate customer query from prompt template to avoid matching taxonomy keywords
        lower = prompt.lower()
        if "=== incoming customer message ===" in lower:
            target_text = lower.split("=== incoming customer message ===")[-1].split("respond strictly")[0].replace('"""', '').strip()
        elif "=== customer message ===" in lower:
            target_text = lower.split("=== customer message ===")[-1].split("respond strictly")[0].replace('"""', '').strip()
        elif "customer message:" in lower:
            target_text = lower.split("customer message:")[-1].replace('"""', '').strip()
        elif "customer inquiry:" in lower:
            target_text = lower.split("customer inquiry:")[-1].replace('"""', '').strip()
        elif "inquiry:" in lower:
            target_text = lower.split("inquiry:")[-1].replace('"""', '').strip()
        else:
            target_text = lower.strip()

        # Clean handle and brand names to prevent accidental substring collisions
        # e.g., "@AppleSupport" contains "port" which would otherwise trigger "charging_issues"!
        clean_text = re.sub(r"@?applesupport\b", "", target_text)
        clean_text = re.sub(r"\bapple\b", "", clean_text).strip()

        # Check if the prompt already provides a pre-classified intent (e.g. in drafter prompt)
        extracted_intent = None
        if "=== classified intent ===" in lower:
            raw_intent = lower.split("=== classified intent ===")[-1].split("===")[0].strip()
            if raw_intent:
                extracted_intent = raw_intent.split()[0]

        # Extract device model mention if present
        device_match = re.search(
            r"\b(i\s*phone\s*(?:1[1-6](?:\s*pro\s*max|\s*pro|\s*plus|\s*mini)?|[6-8](?:\s*plus)?|x[rs]?|se)|ipad\s*(?:pro|air|mini)?|macbook\s*(?:pro|air)?|apple\s*watch|airpods(?:\s*pro|\s*max)?)\b",
            target_text,
            re.IGNORECASE
        )
        detected_device = device_match.group(0).strip() if device_match else None
        # Format nice device name (e.g. iPhone 12)
        if detected_device:
            detected_device = re.sub(r"(?i)\bi\s*phone\b", "iPhone", detected_device)
            detected_device = re.sub(r"(?i)\bipad\b", "iPad", detected_device)
            detected_device = re.sub(r"(?i)\bmacbook\b", "MacBook", detected_device)
            detected_device = re.sub(r"(?i)\bairpods\b", "AirPods", detected_device)

        # 1. Out-of-Scope / Non-Apple Inquiries (produce, personal, pricing/cost, competitor hardware, APK)
        is_apk = bool(re.search(r"\b(apk|apks|sideload|sideloading|android package)\b", target_text))
        is_produce = any(kw in clean_text for kw in ["1 kg", "per kg", "how much for apple", "fruit", "grocery", "produce", "kilo", "gram", "apple price"])
        is_personal = any(kw in clean_text for kw in ["my wife", "husband", "girlfriend", "boyfriend", "not talking to me", "weather", "pizza", "football", "recipe"])
        is_cost_pricing = any(kw in clean_text for kw in ["costly in indai", "costly in india", "costly", "why apple products are costly", "expensive", "tax in india"])
        is_competitor = any(kw in clean_text for kw in ["samsung", "galaxy", "pixel", "playstation", "xbox", "nintendo", "dell", "lenovo", "thinkpad", "windows 10", "windows 11"])

        is_trade_in = bool(re.search(r"\b(exchange|trade\s*in|trade-in|trade|upgrade)\b", clean_text))

        # Display and Touch Screen issues
        is_display_touch = bool(re.search(r"\b(touch|touchscreen|touch screen|unresponsive touch|display|screen|flicker|flickering|green line|black screen)\b", clean_text))

        # Charging issues (strictly bounded, avoiding financial charge and bare 'port' collision with '@AppleSupport')
        is_financial = bool(re.search(r"\b(unauthorized|credit card|card|statement|bill|refund|subscription|\$)\b", clean_text))
        is_charging = ((bool(re.search(r"\b(charge|charging|charger|lightning cable|usbc cable|usb-c cable|charging cable|charging port|lightning port|usb-c port)\b", clean_text)) or ("cable" in clean_text and "not" in clean_text)) and not is_financial)

        # Software / iOS Update issues
        is_software_update = bool(re.search(r"\b(software|ios\b|ios\s*\d+|os\b|firmware|glitch|bug|system\b|update|recovery mode|stuck on)\b", clean_text))
        is_software_version = bool(re.search(r"\b(version|software version|ipados version|ios version|see the version|find the version|which version|model number|serial number)\b", clean_text))
        is_lost_device = (
            "find my" in clean_text
            or "findmy" in clean_text
            or "lost" in clean_text
            or "stolen" in clean_text
            or "locate my" in clean_text
            or "track my" in clean_text
            or (bool(re.search(r"\b(locate|track|lost|stolen)\b", clean_text)) and any(w in clean_text for w in ["phone", "ipad", "mac", "airpod", "watch", "device", "earpod"]))
        ) and not is_software_version

        if is_apk:
            intent_label = "out_of_scope"
            draft_text = "Thanks for reaching out to @AppleSupport! iPhone and iOS devices only support applications downloaded directly from the official Apple App Store and do not support Android APK installation packages. If you need assistance finding an app in the App Store, please let us know!"
        elif is_produce:
            intent_label = "out_of_scope"
            draft_text = "Thanks for reaching out to @AppleSupport! We provide official technical support for the Apple ecosystem (iPhone, iPad, Mac, Apple Watch). We do not sell or provide pricing for fresh produce or grocery items. Let us know if you need assistance with an Apple product!"
        elif is_cost_pricing:
            intent_label = "out_of_scope"
            draft_text = "Thanks for reaching out to @AppleSupport! We are dedicated to technical troubleshooting across the Apple ecosystem. For questions regarding product pricing, regional taxes, or purchasing options in India, please visit https://www.apple.com/in or check with an authorized Apple retailer. If you need technical support for your Apple devices, let us know how we can assist!"
        elif is_personal:
            intent_label = "out_of_scope"
            draft_text = "Thanks for reaching out to @AppleSupport! Our team is dedicated to technical support for the Apple ecosystem. We are unable to assist with personal inquiries, but please let us know if you ever need technical help with any of your Apple devices or services!"
        elif is_competitor:
            intent_label = "out_of_scope"
            draft_text = "Thanks for reaching out to @AppleSupport! We only provide technical support for Apple hardware and software. For assistance with your device, please reach out to the manufacturer's official customer support team."
        elif is_display_touch:
            intent_label = "display_screen"
            dev = detected_device or "iPhone"
            draft_text = f"If your {dev} touch screen is unresponsive or showing display issues, please perform a force restart (press Volume Up, Volume Down, then hold the Side button until the Apple logo appears). If the issue persists, let us know or visit https://support.apple.com to book a service appointment."
        elif is_software_version:
            intent_label = "ios_update_bugs"
            dev = detected_device or "iPad"
            draft_text = f"To find the software version on your {dev}, go to Settings > General > About. You will see the iPadOS/iOS Version, Model Name, and Model Number listed there. Learn more at https://support.apple.com/en-us/HT201685."
        elif is_lost_device:
            intent_label = "lost_device_find_my"
            draft_text = "You can locate your lost EarPods or Apple device using the Find My app or at https://www.icloud.com/find. Select your device under Devices to view its location or play a sound."
        elif "battery" in clean_text or "overheating" in clean_text or "drain" in clean_text:
            intent_label = "battery_performance"
            dev_str = f" on your {detected_device}" if detected_device else ""
            draft_text = f"Hello! Battery health{dev_str} is important. Check Settings > Battery > Battery Health to inspect peak performance capability."
        elif is_charging:
            intent_label = "charging_issues"
            dev_str = f"your {detected_device}" if detected_device else "your device"
            draft_text = f"Hi there, let's get {dev_str} charging again. Inspect the charging port for debris and test with an Apple-certified cable."
        elif is_software_update:
            intent_label = "ios_update_bugs"
            if detected_device:
                draft_text = f"We'd be glad to help with your {detected_device}! Could you share what iOS version you're on and describe what happens when the software issue occurs?"
            else:
                draft_text = "Let's resolve the update error. Restart your device and ensure you have sufficient storage space before downloading."
        elif "crash" in clean_text or "freeze" in clean_text or "quitting" in clean_text or "instagram" in clean_text or "tiktok" in clean_text or any(w in clean_text.split() for w in ["app", "apps"]):
            intent_label = "app_crashes"
            draft_text = "To resolve app issues, force quit the app, check for updates in the App Store, and reinstall if necessary."
        elif "wifi" in clean_text or "wi-fi" in clean_text or "bluetooth" in clean_text or "cellular" in clean_text:
            intent_label = "connectivity_wifi_bluetooth"
            draft_text = "Try toggling Airplane Mode on for 15 seconds, or reset Network Settings via Settings > General > Transfer or Reset iPhone."
        elif "icloud" in clean_text or "storage full" in clean_text or "backup" in clean_text:
            intent_label = "icloud_sync_storage"
            draft_text = "You can manage your iCloud storage allocation and photo library sync under Settings > [Your Name] > iCloud."
        elif "apple id" in clean_text or "password" in clean_text or "locked" in clean_text or "hacked" in clean_text:
            intent_label = "apple_id_account"
            draft_text = "We can help with your Apple ID. You can reset your password securely via https://iforgot.apple.com."
        elif is_trade_in or "refund" in clean_text or "bill" in clean_text or "subscription" in clean_text or "$" in clean_text:
            intent_label = "purchase_refund_billing"
            if is_trade_in:
                dev_str = f" for your {detected_device}" if detected_device else ""
                draft_text = f"You can trade in your eligible device{dev_str} toward a new purchase or an Apple Gift Card. Check estimated values and start the process online at https://www.apple.com/shop/trade-in or visit an Apple Store."
            else:
                draft_text = "You can review purchase history and request refunds directly at https://reportaproblem.apple.com."
        elif "cracked" in clean_text or "shattered" in clean_text or "water" in clean_text or "liquid" in clean_text or "repair" in clean_text or "camera" in clean_text or "imei" in clean_text or "coffee" in clean_text or "glass" in clean_text or "human" in clean_text or "sue" in clean_text:
            intent_label = "hardware_damage"
            draft_text = "For physical hardware damage, you can check repair estimates and book a Genius Bar appointment at https://support.apple.com."
        elif "mic" in clean_text or "speaker" in clean_text or "airpod" in clean_text or "audio" in clean_text or "sound" in clean_text or "earpiece" in clean_text:
            intent_label = "audio_speaker_mic"
            draft_text = "We're here to help with your audio. Try resetting your AirPods in the case or checking microphone permissions."
        elif "slow" in clean_text or "lag" in clean_text or "fan" in clean_text or "spinning" in clean_text or "boot" in clean_text:
            intent_label = "performance_speed"
            draft_text = "Check Activity Monitor or Settings > General > Background App Refresh to see what processes are consuming resources."
        else:
            intent_label = "out_of_scope"
            if detected_device:
                draft_text = f"Thanks for reaching out to @AppleSupport! We'd be glad to assist with your {detected_device}. Could you please describe what specific symptoms or errors you are seeing so we can help?"
            else:
                draft_text = "Thanks for reaching out to @AppleSupport! We are here to help with your Apple devices and ecosystem services. Could you please share more details about your Apple device or software issue so we can assist?"

        # If an explicit intent was provided in the prompt (e.g. Drafter pipeline), harmonize draft_text with it
        if extracted_intent:
            if extracted_intent == "display_screen":
                dev = detected_device or "iPhone"
                draft_text = f"If your {dev} touch screen is unresponsive or showing display issues, please perform a force restart (press Volume Up, Volume Down, then hold the Side button until the Apple logo appears). If the issue persists, let us know or visit https://support.apple.com to book a service appointment."
            elif extracted_intent == "charging_issues":
                dev_str = f"your {detected_device}" if detected_device else "your device"
                draft_text = f"Hi there, let's get {dev_str} charging again. Inspect the charging port for debris and test with an Apple-certified cable."
            elif extracted_intent in ["ios_update_bugs", "software_update_bugs"]:
                if is_software_version:
                    dev = detected_device or "iPad"
                    draft_text = f"To find the software version on your {dev}, go to Settings > General > About. You will see the iPadOS/iOS Version, Model Name, and Model Number listed there. Learn more at https://support.apple.com/en-us/HT201685."
                elif detected_device:
                    draft_text = f"We'd be glad to help with your {detected_device}! Could you share what iOS version you're on and describe what happens when the software issue occurs?"
                else:
                    draft_text = "Let's resolve the update error. Restart your device and ensure you have sufficient storage space before downloading."
            elif extracted_intent in ["purchase_refund_billing", "billing_and_subscriptions"]:
                if is_trade_in:
                    dev_str = f" for your {detected_device}" if detected_device else ""
                    draft_text = f"You can trade in your eligible device{dev_str} toward a new purchase or an Apple Gift Card. Check estimated values and start the process online at https://www.apple.com/shop/trade-in or visit an Apple Store."
                else:
                    draft_text = "You can review purchase history and request refunds directly at https://reportaproblem.apple.com."
            elif extracted_intent == "app_crashes":
                draft_text = "To resolve app issues, force quit the app, check for updates in the App Store, and reinstall if necessary."
            elif extracted_intent == "out_of_scope":
                if is_apk:
                    draft_text = "Thanks for reaching out to @AppleSupport! iPhone and iOS devices only support applications downloaded directly from the official Apple App Store and do not support Android APK installation packages. If you need assistance finding an app in the App Store, please let us know!"
                elif is_produce:
                    draft_text = "Thanks for reaching out to @AppleSupport! We provide official technical support for the Apple ecosystem (iPhone, iPad, Mac, Apple Watch). We do not sell or provide pricing for fresh produce or grocery items. Let us know if you need assistance with an Apple product!"
                elif is_cost_pricing:
                    draft_text = "Thanks for reaching out to @AppleSupport! We are dedicated to technical troubleshooting across the Apple ecosystem. For questions regarding product pricing, regional taxes, or purchasing options in India, please visit https://www.apple.com/in or check with an authorized Apple retailer. If you need technical support for your Apple devices, let us know how we can assist!"
                elif is_competitor:
                    draft_text = "Thanks for reaching out to @AppleSupport! We only provide technical support for Apple hardware and software. For assistance with your device, please reach out to the manufacturer's official customer support team."
                else:
                    if detected_device:
                        draft_text = f"Thanks for reaching out to @AppleSupport! We'd be glad to assist with your {detected_device}. Could you please describe what specific symptoms or errors you are seeing so we can help?"
                    else:
                        draft_text = "Thanks for reaching out to @AppleSupport! We are here to help with your Apple devices and ecosystem services. Could you please share more details about your Apple device or software issue so we can assist?"

        parsed_obj: Optional[BaseModel] = None

        if schema is not None:
            schema_name = schema.__name__.lower()
            if "classifier" in schema_name or "intent" in schema_name:
                sample_data = {
                    "intent": intent_label,
                    "confidence": 0.88,
                    "reasoning": f"Identified customer inquiry regarding {intent_label}.",
                    "alternatives": [
                        {"label": "hardware_troubleshooting", "confidence": 0.08},
                        {"label": "general_device_inquiry", "confidence": 0.04},
                    ],
                }
            elif "draft" in schema_name or "reply" in schema_name:
                found_threads = re.findall(r"\[Thread\s+([^\]]+)\]", prompt)
                grounded_ids = found_threads[:2] if found_threads else ["mock-thread-101", "mock-thread-102"]
                sample_data = {
                    "reply": draft_text,
                    "confidence": 0.85,
                    "grounded_thread_ids": grounded_ids,
                    "reasoning": f"Synthesized grounded solution for {intent_label} from top retrieved AppleSupport historical resolutions.",
                }
            elif "judge" in schema_name:
                sample_data = {
                    "relevance": 5,
                    "accuracy": 4,
                    "tone": 5,
                    "completeness": 4,
                    "groundedness": 5,
                    "overall_score": 4.6,
                    "critique": "The response is empathetic, accurate, and provides standard Apple troubleshooting steps without inventing policies.",
                }
            else:
                # Default generic schema fill
                sample_data = {"result": draft_text, "confidence": 0.9}

            raw_text = json.dumps(sample_data)
            parsed_obj = schema.model_validate(sample_data)
        else:
            raw_text = draft_text

        latency = int((time.time() - start) * 1000)
        return LLMResponse(
            text=raw_text,
            parsed=parsed_obj,
            tokens_prompt=len(prompt.split()),
            tokens_completion=len(raw_text.split()),
            latency_ms=max(1, latency),
            model=self.model_name,
            provider="mock",
            finish_reason="stop",
        )

    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        words = ["Hi", "there! ", "We ", "are ", "here ", "to ", "help ", "with ", "your ", "Apple ", "device."]
        for w in words:
            yield w

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Deterministic 384-dimensional embedding vector derived from text hash
        results = []
        for text in texts:
            seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
            # Generate deterministic pseudo-floats normalized to unit length
            vec = [((seed + i * 31) % 1000) / 1000.0 - 0.5 for i in range(384)]
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            results.append([x / norm for x in vec])
        return results


# Alias for backward compatibility with scripts and loaders
MockLLMProvider = MockProvider

