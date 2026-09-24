"""
Intent Classifier module using LLMProvider with structured JSON output.
Classifies customer inquiries into canonical data-driven taxonomy.
"""

import logging
from typing import Any, Dict, List, Optional
from app.llm.base import LLMProvider
from app.prompts.registry import prompt_registry
from app.schemas.inference import IntentClassificationSchema, IntentAlternative
from app.data.loaders.few_shot_loader import FewShotLoader

logger = logging.getLogger(__name__)

# Canonical AppleSupport Intent Taxonomy (12 categories) - v2.0
DEFAULT_TAXONOMY: List[Dict[str, Any]] = [
    {
        "label": "battery_performance",
        "description": "Rapid battery percentage drop, battery draining fast, overheating phone, battery health degradation warnings.",
        "examples": ["battery dying in 3 hours", "battery draining fast from 100% to 20%", "phone super hot and losing charge", "battery health 75%"],
    },
    {
        "label": "charging_issues",
        "description": "Issues charging iPhone/iPad, dirty Lightning/USB-C port, cable errors, dead device.",
        "examples": ["iPhone won't charge", "charger not working", "cable says accessory not supported"],
    },
    {
        "label": "ios_update_bugs",
        "description": "Errors downloading or installing iOS update, software glitches or bugs, operating system issues, checking software/iOS/iPadOS version or device model specifications, device stuck on Apple logo during reboot.",
        "examples": [
            "update error 4013",
            "stuck on Apple logo after iOS 18",
            "not enough space to update",
            "problem with my software with my apple iphone 12",
            "iOS software glitches",
            "how to check software version of my iPad",
            "i cant see the version of my current ipad where to find it",
        ],
    },
    {
        "label": "app_crashes",
        "description": "Apps freezing, quitting unexpectedly, stuck on 'Waiting', unable to open from home screen.",
        "examples": ["Instagram keeps crashing on launch", "apps won't download from App Store"],
    },
    {
        "label": "connectivity_wifi_bluetooth",
        "description": "AirPods Bluetooth dropping, Wi-Fi grayed out or disconnecting, Cellular no service.",
        "examples": ["AirPods won't connect to MacBook", "Wi-Fi keeps dropping every few minutes"],
    },
    {
        "label": "icloud_sync_storage",
        "description": "iCloud storage full alerts, photos not syncing across devices, iCloud backup failed or stuck.",
        "examples": ["iCloud backup stuck at estimating time", "photos not uploading to cloud storage"],
    },
    {
        "label": "apple_id_account",
        "description": "Locked account, forgotten Apple ID password, 2FA verification code issues, hack inquiries.",
        "examples": ["locked out of my Apple ID", "can't receive verification code", "forgot iCloud password"],
    },
    {
        "label": "hardware_damage",
        "description": "Cracked screen, water or liquid ingress, bent frame, repair appointment requests.",
        "examples": ["dropped phone in water", "screen shattered need repair", "how much is back glass repair"],
    },
    {
        "label": "audio_speaker_mic",
        "description": "One AirPod silent, speaker crackling, microphone muffled on calls, no sound during video.",
        "examples": ["left AirPod has no sound", "microphone not working on phone calls"],
    },
    {
        "label": "display_screen",
        "description": "Green line on display, touch screen unresponsive, screen flickering, black screen of death.",
        "examples": ["green line running down screen", "touch screen stopped responding after drop"],
    },
    {
        "label": "performance_speed",
        "description": "Mac running very slow, kernel panics, fan spinning loud, sluggish keyboard lag.",
        "examples": ["MacBook spinning wheel of death", "iPhone lagging when typing", "fan running super loud"],
    },
    {
        "label": "purchase_refund_billing",
        "description": "Unrecognized charge on card, Apple bill refund, cancellation of active subscription, Apple Trade In or device exchange process.",
        "examples": [
            "charged $14.99 unauthorized",
            "cancel my Apple Music subscription",
            "request refund for app",
            "i need to exchange my iphone 12 what is the process",
            "how does apple trade in exchange work",
        ],
    },
    {
        "label": "lost_device_find_my",
        "description": "Locating physically lost or stolen EarPods, AirPods, iPhone, iPad, or Mac using Find My app or iCloud.com (not for finding settings, software version, or device menus).",
        "examples": ["my EarPods i lost i need to find", "lost my right AirPod in park", "how to track lost iPhone with Find My", "stolen iPad locate with Find My"],
    },
    {
        "label": "out_of_scope",
        "description": "General non-technical questions, regional pricing/tax inquiries, personal matters, grocery/produce questions, or non-Apple hardware.",
        "examples": [
            "why apple products are costly in indai",
            "apple 1 kg how much?",
            "my wife not talking to me",
            "what is the weather today",
            "my Samsung Galaxy screen is broken",
        ],
    },
]

V1_TO_V2_INTENT_MAP: Dict[str, str] = {
    "iphone_wont_charge": "charging_issues",
    "battery_drain": "battery_performance",
    "apple_id_account_access": "apple_id_account",
    "ios_update_issue": "ios_update_bugs",
    "airpods_sound_connectivity": "connectivity_wifi_bluetooth",
    "hardware_damage_repair": "hardware_damage",
    "billing_and_subscriptions": "purchase_refund_billing",
    "icloud_storage_sync": "icloud_sync_storage",
    "mac_performance_macos": "performance_speed",
    "app_store_downloads": "app_crashes",
    "watch_fitness_sync": "audio_speaker_mic",
    "other_inquiry": "out_of_scope",
    "out_of_scope": "out_of_scope",
    "lost_device_find_my": "lost_device_find_my",
}


class IntentClassifier:
    """Classifies customer message into intent taxonomy."""

    def __init__(
        self,
        provider: LLMProvider,
        taxonomy: Optional[List[Dict[str, Any]]] = None,
        prompt_version: str = "v1",
        few_shot_loader: Optional[FewShotLoader] = None,
    ):
        self.provider = provider
        self.taxonomy = taxonomy or DEFAULT_TAXONOMY
        self.prompt_version = prompt_version
        self.few_shot_loader = few_shot_loader or FewShotLoader()

    async def classify(
        self,
        customer_message: str,
        use_few_shot: bool = True,
    ) -> IntentClassificationSchema:
        """Execute intent classification."""
        few_shots = []
        if use_few_shot and self.few_shot_loader:
            try:
                few_shots = self.few_shot_loader.get_few_shot_examples(n=3, query=customer_message)
            except Exception as e:
                logger.debug(f"Could not load dynamic few-shot examples: {e}")

        prompt = prompt_registry.render(
            "classifier",
            version=self.prompt_version,
            taxonomy=self.taxonomy,
            customer_message=customer_message,
            few_shot_examples=few_shots,
        )

        safe_default = IntentClassificationSchema(
            intent="out_of_scope",
            confidence=0.50,
            reasoning="Fallback default classification due to extraction error or non-Apple inquiry.",
            alternatives=[],
        )

        response = await self.provider.generate(
            prompt,
            schema=IntentClassificationSchema,
            temperature=0.0,
            max_tokens=256,
        )

        if response.parsed and isinstance(response.parsed, IntentClassificationSchema):
            return response.parsed

        return safe_default

