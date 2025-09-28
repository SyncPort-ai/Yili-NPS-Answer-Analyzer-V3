"""Minimal OpenAI client wrapper for qualitative analysis (optional)."""
from typing import Dict, List, Any, Optional
import json
import os

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        self.max_tokens_env = os.getenv("OPENAI_MAX_TOKENS")
        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None

    def chat_completion(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> Optional[str]:
        if not self.client:
            return None
        try:
            import logging
            temp = self.temperature if temperature is None else temperature
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temp,
            }
            if self.max_tokens_env:
                try:
                    kwargs["max_tokens"] = int(self.max_tokens_env)
                except Exception:
                    pass
            logging.getLogger("nps_report_analyzer").info(
                "OpenAI chat.completions.create model=%s temp=%s", self.model, temp
            )
            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception:
            import logging
            logging.getLogger("nps_report_analyzer").exception("OpenAI call failed")
            return None

    def parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None
        try:
            content = content.strip()
            if "```json" in content:
                s = content.find("```json") + 7
                e = content.find("```", s)
                if e != -1:
                    content = content[s:e].strip()
            elif "```" in content:
                s = content.find("```") + 3
                e = content.find("```", s)
                if e != -1:
                    content = content[s:e].strip()
            return json.loads(content)
        except Exception:
            return None

    def analyze_with_prompt(self, prompt_template: str, text_data: str, **kwargs) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        formatted = prompt_template.format(text_data=text_data, **kwargs)
        messages = [
            {"role": "system", "content": "You are a Chinese NLP expert."},
            {"role": "user", "content": formatted},
        ]
        resp = self.chat_completion(messages, temperature=0.1)
        return self.parse_json_response(resp) if resp else None


class PromptTemplates:
    def qualitative_analysis_prompt(self) -> str:
        return (
            "Analyze the following Chinese customer comments and return JSON with: top_themes, "
            "sentiment_overview, product_mentions, emotions_detected, comment_count.\n\n{text_data}"
        )
