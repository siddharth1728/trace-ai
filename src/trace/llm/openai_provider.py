"""OpenAI and OpenAI-compatible API Provider implementation for TRACE."""

import json
import os
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from trace.llm.provider import LLMProvider

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider(LLMProvider):
    """
    Vendor-neutral provider for any OpenAI-compatible API endpoint
    (OpenAI, LiteLLM, Ollama, LocalAI, vLLM, DeepSeek, etc.).
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key or "no-key",
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError(
                    "The 'openai' package is required for OpenAICompatibleProvider. "
                    "Install it via `pip install openai` or use the mock provider."
                )
        return self._client

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        client = self._get_client()
        messages = []
        
        # Augment prompt with JSON schema instruction for reliable parsing
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        instruction = (
            f"\nYou must respond ONLY with a valid JSON object matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any conversational filler, markdown formatting outside of json fences, or preamble."
        )

        sys_content = (system_prompt or "") + instruction
        messages.append({"role": "system", "content": sys_content})
        messages.append({"role": "user", "content": prompt})

        # Attempt structured output or json_object format
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_text = response.choices[0].message.content or "{}"
            parsed_json = json.loads(raw_text)
            return response_model.model_validate(parsed_json)
        except Exception:
            # Fallback: parse json from raw completion text
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
            )
            raw_text = response.choices[0].message.content or "{}"
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                parsed_json = json.loads(json_match.group(0))
                return response_model.model_validate(parsed_json)
            raise ValueError(f"Failed to parse structured response from LLM output: {raw_text[:200]}")
