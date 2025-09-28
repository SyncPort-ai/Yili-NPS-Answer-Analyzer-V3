"""
多智能体NPS分析系统的仅伊利AI客户端
仅使用伊利企业AI基础设施，无外部后备。
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YiliOnlyAIClient:
    """仅伊利独占AI网关客户端，无外部依赖。"""

    def __init__(self,
                 yili_app_key: Optional[str] = None,
                 yili_gateway_url: Optional[str] = None,
                 timeout: int = 60,
                 max_retries: int = 5):
        self.yili_gateway_url = yili_gateway_url or os.getenv(
            "YILI_GATEWAY_URL",
            "https://ycsb-gw-pub.xapi.digitalyili.com/restcloud/yili-gpt-prod/v1/getTextToThird"
        )
        self.yili_app_key = yili_app_key or os.getenv("YILI_APP_KEY")
        self.session = requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.yili_app_key:
            logger.warning("YILI_APP_KEY 未配置，YiliOnlyAIClient将不可用")
        if not self.yili_gateway_url:
            logger.warning("YILI_GATEWAY_URL 未配置，YiliOnlyAIClient将不可用")

    def chat_completion(self,
                        messages: List[Dict[str, str]],
                        temperature: float = 0.1,
                        max_tokens: Optional[int] = None) -> Optional[str]:
        return self._chat_via_yili_gateway_only(messages, temperature, max_tokens)

    def _chat_via_yili_gateway_only(self,
                                    messages: List[Dict[str, str]],
                                    temperature: float,
                                    max_tokens: Optional[int]) -> Optional[str]:
        if not self.yili_app_key or not self.yili_gateway_url:
            return None

        prompt = self._messages_to_prompt(messages)
        for attempt in range(self.max_retries):
            try:
                logger.info("Yili gateway call attempt %s/%s", attempt + 1, self.max_retries)
                headers = {'AppKey': self.yili_app_key, 'Content-Type': 'application/json'}
                data = {
                    "channelCode": "wvEO",
                    "tenantsCode": "Yun8457",
                    "choiceModel": 1,
                    "isMultiSession": 1,
                    "requestContent": prompt,
                    "requestType": 1,
                    "streamFlag": 0,
                    "userCode": "wvEO10047252",
                    "requestGroupCode": "1243112808144896"
                }
                resp = self.session.post(self.yili_gateway_url, json=data, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                js = resp.json()
                if js.get('code') == 0:
                    logger.info("Yili gateway call success")
                    return js['data']['responseVO']
                else:
                    raise Exception(f"Yili gateway error: {js}")
            except Exception:
                logger.exception("Yili gateway call failed on attempt %s", attempt + 1)
                if attempt == self.max_retries - 1:
                    logger.error("Yili gateway exhausted all retries")
                    return None
                time.sleep(min(1.0 * (2 ** attempt), 10.0))

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        parts = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"系统指示: {content}")
            elif role == "user":
                parts.append(f"用户问题: {content}")
            elif role == "assistant":
                parts.append(f"助手回复: {content}")
        return "\n\n".join(parts)

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
        formatted = prompt_template.format(text_data=text_data, **kwargs)
        messages = [
            {"role": "system", "content": "你是伊利集团的专业中文文本分析专家。"},
            {"role": "user", "content": formatted},
        ]
        resp = self.chat_completion(messages, temperature=0.1)
        if not resp:
            return None
        return self.parse_json_response(resp)


class YiliPromptTemplates:
    def qualitative_analysis_prompt(self) -> str:
        return (
            "请对以下客户评论进行中文定性分析，输出JSON，包括：top_themes, sentiment_overview, "
            "product_mentions, emotions_detected, comment_count。\n\n{text_data}"
        )
