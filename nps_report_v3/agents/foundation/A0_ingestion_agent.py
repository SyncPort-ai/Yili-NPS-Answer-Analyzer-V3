"""
A0 - Data Ingestion Agent
Foundation Pass Agent for data cleaning and PII scrubbing.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from ..base import FoundationAgent, AgentResult, AgentStatus
from ...state import CleanedData, SurveyResponse, DataQuality
from ...schemas import validate_chinese_text, validate_product_line, validate_nps_batch

logger = logging.getLogger(__name__)


class DataIngestionAgent(FoundationAgent):
    """
    A0 - Data Ingestion Agent

    Responsibilities:
    - Clean and validate raw survey data
    - Remove PII (Personally Identifiable Information)
    - Standardize data formats
    - Assess data quality
    - Generate unique IDs for responses
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # PII patterns for Chinese context
        self.pii_patterns = {
            "phone": re.compile(r"1[3-9]\d{9}"),  # Chinese mobile
            "email": re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
            "id_card": re.compile(r"\d{15}(\d{2}[0-9xX])?"),  # Chinese ID
            "bank_card": re.compile(r"\d{16,19}"),
            "name": re.compile(r"[张王李赵刘陈杨黄周吴徐孙马胡郭何高林郑谢罗梁宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯陶贺顾毛郝龚邵万钱严覃武戴莫孔向汤][^\s，。！？]{1,3}")
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute data ingestion and cleaning.

        Args:
            state: Current workflow state with raw_data

        Returns:
            AgentResult with cleaned data
        """
        try:
            raw_data = state.get("raw_data", [])

            if not raw_data:
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.FAILED,
                    errors=["No raw data provided"],
                    data={}
                )

            # Process each response
            cleaned_responses = []
            invalid_responses = []
            cleaning_notes = []

            for idx, raw_response in enumerate(raw_data):
                try:
                    # Validate and clean response
                    cleaned = await self._process_response(raw_response, idx, state.get("language", "zh"))

                    if cleaned:
                        cleaned_responses.append(cleaned)
                    else:
                        invalid_responses.append(idx)

                except Exception as e:
                    logger.error(f"Error processing response {idx}: {e}")
                    invalid_responses.append(idx)
                    cleaning_notes.append(f"Response {idx}: {str(e)}")

            # Assess data quality
            data_quality = self._assess_data_quality(
                total=len(raw_data),
                valid=len(cleaned_responses),
                invalid=len(invalid_responses)
            )

            # Create cleaned data output
            cleaned_data = CleanedData(
                total_responses=len(raw_data),
                valid_responses=len(cleaned_responses),
                invalid_responses=len(invalid_responses),
                cleaned_responses=cleaned_responses,
                data_quality=data_quality,
                cleaning_notes=cleaning_notes,
                pii_scrubbed=True
            )

            logger.info(
                f"Data ingestion complete: {len(cleaned_responses)}/{len(raw_data)} valid responses, "
                f"quality: {data_quality}"
            )

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "cleaned_data": cleaned_data,
                    "summary": {
                        "total_processed": len(raw_data),
                        "valid_count": len(cleaned_responses),
                        "invalid_count": len(invalid_responses),
                        "data_quality": data_quality,
                        "pii_removed": True
                    }
                }
            )

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                data={}
            )

    async def _process_response(
        self,
        raw_response: Dict[str, Any],
        index: int,
        language: str = "zh"
    ) -> Optional[SurveyResponse]:
        """
        Process individual survey response.

        Args:
            raw_response: Raw response data
            index: Response index

        Returns:
            Cleaned SurveyResponse or None if invalid
        """
        try:
            # Extract and validate NPS score
            nps_score = raw_response.get("nps_score") or raw_response.get("score")

            if nps_score is None:
                logger.warning(f"Response {index}: Missing NPS score")
                return None

            # Ensure score is valid (0-10)
            try:
                nps_score = int(nps_score)
                if not 0 <= nps_score <= 10:
                    logger.warning(f"Response {index}: Invalid NPS score {nps_score}")
                    return None
            except (ValueError, TypeError):
                logger.warning(f"Response {index}: Non-numeric NPS score")
                return None

            # Extract and clean comment (support multiple field names)
            comment = (raw_response.get("comment") or
                      raw_response.get("feedback") or
                      raw_response.get("feedback_text") or "")

            if comment:
                # Remove PII
                comment = self._remove_pii(comment)

                # Clean text
                comment = self._clean_text(comment)

                # Validate Chinese text if expected
                if language == "zh":
                    try:
                        comment = validate_chinese_text(comment, min_length=2, max_length=5000)
                    except ValueError:
                        comment = ""  # Invalid text, treat as no comment

            # Extract metadata
            product_line = raw_response.get("product_line") or raw_response.get("product")

            if product_line:
                product_line = validate_product_line(product_line)

            # Generate response ID if not present
            response_id = raw_response.get("response_id") or raw_response.get("id")

            if not response_id:
                # Generate deterministic ID
                content = f"{index}_{nps_score}_{comment[:50] if comment else ''}"
                response_id = hashlib.md5(content.encode()).hexdigest()[:12]

            # Extract timestamp
            timestamp = raw_response.get("timestamp") or raw_response.get("created_at")

            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except:
                        timestamp = datetime.now()
                elif not isinstance(timestamp, datetime):
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Create cleaned response
            cleaned = SurveyResponse(
                response_id=response_id,
                timestamp=timestamp,
                nps_score=nps_score,
                comment=comment if comment else None,
                product_line=product_line,
                customer_segment=raw_response.get("customer_segment"),
                channel=raw_response.get("channel"),
                metadata=self._clean_metadata(raw_response.get("metadata", {}))
            )

            return cleaned

        except Exception as e:
            logger.error(f"Failed to process response {index}: {e}")
            return None

    def _remove_pii(self, text: str) -> str:
        """
        Remove PII from text.

        Args:
            text: Input text

        Returns:
            Text with PII removed
        """
        if not text:
            return text

        # Replace PII patterns
        for pii_type, pattern in self.pii_patterns.items():
            if pii_type == "name":
                # Special handling for Chinese names
                text = pattern.sub("[姓名]", text)
            elif pii_type == "phone":
                text = pattern.sub("[电话]", text)
            elif pii_type == "email":
                text = pattern.sub("[邮箱]", text)
            elif pii_type == "id_card":
                text = pattern.sub("[身份证]", text)
            elif pii_type == "bank_card":
                text = pattern.sub("[银行卡]", text)
            else:
                text = pattern.sub(f"[{pii_type}]", text)

        return text

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return text

        # Remove excessive whitespace
        text = " ".join(text.split())

        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char == '\n')

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)

        # Limit consecutive punctuation
        text = re.sub(r'([!?。！？]){3,}', r'\1\1', text)

        return text.strip()

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata dictionary.

        Args:
            metadata: Raw metadata

        Returns:
            Cleaned metadata
        """
        if not metadata:
            return {}

        cleaned = {}

        for key, value in metadata.items():
            # Skip sensitive keys
            if any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]):
                continue

            # Clean string values
            if isinstance(value, str):
                value = self._remove_pii(value)
                value = self._clean_text(value)

            cleaned[key] = value

        return cleaned

    def _assess_data_quality(
        self,
        total: int,
        valid: int,
        invalid: int
    ) -> DataQuality:
        """
        Assess overall data quality.

        Args:
            total: Total responses
            valid: Valid responses
            invalid: Invalid responses

        Returns:
            DataQuality assessment
        """
        if total == 0:
            return DataQuality.INSUFFICIENT

        valid_ratio = valid / total

        if valid_ratio >= 0.9:
            return DataQuality.HIGH
        elif valid_ratio >= 0.7:
            return DataQuality.MEDIUM
        elif valid_ratio >= 0.5:
            return DataQuality.LOW
        else:
            return DataQuality.INSUFFICIENT