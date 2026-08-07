"""
Gemini API Client
=================
Async wrapper around the Google Gemini API with retry logic,
JSON extraction, and error handling.
"""

import json
import re
from typing import Any, Dict, Optional

import google.generativeai as genai
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class GeminiClient:
    """
    Singleton-style wrapper for Google Gemini API calls.

    Features:
    - Auto-configures on first use
    - Strips markdown fences from JSON responses
    - Retries on transient API errors (up to 3 times)
    - Returns parsed dict or raises ValueError on bad JSON
    """

    _configured: bool = False

    def __init__(self) -> None:
        if not GeminiClient._configured:
            if not settings.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Add it to your .env file."
                )
            genai.configure(api_key=settings.GEMINI_API_KEY)
            GeminiClient._configured = True
        self._model = genai.GenerativeModel(settings.GEMINI_MODEL)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the raw text response.

        Retries up to 3 times on failure with exponential backoff.

        Args:
            prompt: The full formatted prompt string.

        Returns:
            Raw response text from Gemini.
        """
        logger.debug(f"Sending prompt to Gemini ({len(prompt)} chars)...")
        response = await self._model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                top_p=0.95,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        return response.text

    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generate a response and parse it as JSON.

        Handles Gemini's tendency to wrap JSON in markdown code fences.

        Args:
            prompt: Prompt instructing Gemini to return JSON.

        Returns:
            Parsed Python dictionary.

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        raw = await self.generate(prompt)
        return self._extract_json(raw)

    async def generate_json_list(self, prompt: str) -> list:
        """
        Generate a response and parse it as a JSON array.

        Returns:
            Parsed Python list.
        """
        raw = await self.generate(prompt)
        return self._extract_json_list(raw)

    # ── JSON extraction helpers ────────────────────────────────
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract and parse a JSON object from text that may contain markdown fences.
        """
        # Strip ```json ... ``` or ``` ... ``` wrappers
        cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()

        # Find the first { ... } block
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object found in Gemini response: {cleaned[:200]}")

        json_str = cleaned[start:end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw: {json_str[:500]}")
            raise ValueError(f"Gemini returned invalid JSON: {e}")

    def _extract_json_list(self, text: str) -> list:
        """Extract and parse a JSON array from text."""
        cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON array found in Gemini response: {cleaned[:200]}")
        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON array: {e}")
