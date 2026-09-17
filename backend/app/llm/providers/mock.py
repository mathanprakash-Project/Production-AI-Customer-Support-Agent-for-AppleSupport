"""
Deterministic Mock LLM Provider for unit testing, CI, and offline smoke tests.
Does not require any external runtime or API keys.
"""

import hashlib
import json
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
        if "=== customer message ===" in lower:
            target_text = lower.split("=== customer message ===")[-1].split("respond strictly")[0]
        elif "customer message:" in lower:
            target_text = lower.split("customer message:")[-1]
        elif "customer inquiry:" in lower:
            target_text = lower.split("customer inquiry:")[-1]
        elif "inquiry:" in lower:
            target_text = lower.split("inquiry:")[-1]
        else:
            target_text = lower

        if "battery" in target_text or "overheating" in target_text or "drain" in target_text:
            intent_label = "battery_performance"
            draft_text = "Hello! Battery health is important. Check Settings > Battery > Battery Health to inspect peak performance capability."
        elif "charge" in target_text or "charging" in target_text or "cable" in target_text or "port" in target_text:
            intent_label = "charging_issues"
            draft_text = "Hi there, let's get your device charging again. Inspect the charging port for debris and test with an Apple-certified cable."
        elif "stuck on" in target_text or "ios 18" in target_text or "ios 17" in target_text or "recovery mode" in target_text or "update" in target_text:
            intent_label = "ios_update_bugs"
            draft_text = "Let's resolve the update error. Restart your device and ensure you have sufficient storage space before downloading."
        elif "crash" in target_text or "freeze" in target_text or "quitting" in target_text or "app" in target_text or "instagram" in target_text or "tiktok" in target_text:
            intent_label = "app_crashes"
            draft_text = "To resolve app issues, force quit the app, check for updates in the App Store, and reinstall if necessary."
        elif "wifi" in target_text or "wi-fi" in target_text or "bluetooth" in target_text or "cellular" in target_text:
            intent_label = "connectivity_wifi_bluetooth"
            draft_text = "Try toggling Airplane Mode on for 15 seconds, or reset Network Settings via Settings > General > Transfer or Reset iPhone."
        elif "icloud" in target_text or "storage full" in target_text or "backup" in target_text:
            intent_label = "icloud_sync_storage"
            draft_text = "You can manage your iCloud storage allocation and photo library sync under Settings > [Your Name] > iCloud."
        elif "apple id" in target_text or "password" in target_text or "locked" in target_text or "hacked" in target_text:
            intent_label = "apple_id_account"
            draft_text = "We can help with your Apple ID. You can reset your password securely via https://iforgot.apple.com."
        elif "refund" in target_text or "bill" in target_text or "charge" in target_text or "subscription" in target_text or "$" in target_text:
            intent_label = "purchase_refund_billing"
            draft_text = "You can review purchase history and request refunds directly at https://reportaproblem.apple.com."
        elif "cracked" in target_text or "shattered" in target_text or "water" in target_text or "liquid" in target_text or "repair" in target_text or "camera" in target_text or "imei" in target_text or "coffee" in target_text or "glass" in target_text or "human" in target_text or "sue" in target_text:
            intent_label = "hardware_damage"
            draft_text = "For physical hardware damage, you can check repair estimates and book a Genius Bar appointment at https://support.apple.com."
        elif "mic" in target_text or "speaker" in target_text or "airpod" in target_text or "audio" in target_text or "sound" in target_text or "earpiece" in target_text:
            intent_label = "audio_speaker_mic"
            draft_text = "We're here to help with your audio. Try resetting your AirPods in the case or checking microphone permissions."
        elif "screen" in target_text or "display" in target_text or "flicker" in target_text or "touch" in target_text or "green line" in target_text:
            intent_label = "display_screen"
            draft_text = "If your display is unresponsive or showing lines, perform a force restart and check if the issue persists across apps."
        elif "slow" in target_text or "lag" in target_text or "fan" in target_text or "spinning" in target_text or "boot" in target_text:
            intent_label = "performance_speed"
            draft_text = "Check Activity Monitor or Settings > General > Background App Refresh to see what processes are consuming resources."
        else:
            intent_label = "display_screen"
            draft_text = "Thanks for reaching out! We'd be glad to take a closer look and help resolve this for you."

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
                sample_data = {
                    "reply": draft_text,
                    "confidence": 0.85,
                    "grounded_thread_ids": ["mock-thread-101", "mock-thread-102"],
                    "reasoning": "Synthesized grounded solution from top retrieved AppleSupport historical resolutions.",
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

