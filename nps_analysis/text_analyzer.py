"""
Text Analysis Engine
===================

Professional text analysis for NPS comments and open-ended responses.
Implements the traditional cleaning-labeling-clustering pipeline.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import re
from datetime import datetime

from .exceptions import LabelingError, EmbeddingError, ModelCallError

logger = logging.getLogger(__name__)


class TextAnalyzer:
    """
    Professional text analysis engine for NPS comments.
    
    Implements the proven cleaning-labeling-clustering pipeline:
    1. Text cleaning and preprocessing
    2. LLM-based sentiment and aspect labeling
    3. Embedding-based clustering
    4. Theme extraction and summarization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize text analyzer.
        
        Args:
            config: Configuration with:
                - llm_provider: 'openai' or 'yili'
                - batch_size: Number of texts to process together
                - max_clusters: Maximum number of clusters
        """
        self.config = config or {}
        self.batch_size = self.config.get("batch_size", 20)
        self.max_clusters = self.config.get("max_clusters", 10)
        
        # Import existing analysis functions
        try:
            from opening_question_analysis import auto_analysis
            self._legacy_analyzer = auto_analysis
        except ImportError:
            logger.warning("Legacy analysis functions not available")
            self._legacy_analyzer = None
        
        logger.info("TextAnalyzer initialized with config: %s", self.config)
    
    def analyze_comments(
        self,
        comments: List[str],
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of text comments.
        
        Args:
            comments: List of text comments to analyze
            analysis_options: Optional configuration:
                - theme: Analysis theme (概念设计/口味设计/包装设计)
                - emotion: Emotion filter (喜欢/不喜欢/其他)
                - include_clustering: bool (default: True)
                - include_sentiment: bool (default: True)
        
        Returns:
            Dict: Analysis results with themes, sentiment, clusters
        """
        if not comments:
            return {"message": "No comments to analyze", "results": []}
        
        options = analysis_options or {}
        start_time = datetime.now()
        
        try:
            logger.info("Analyzing %d comments", len(comments))
            
            # Clean and prepare data
            cleaned_comments = self._clean_comments(comments)
            
            # Create DataFrame for legacy compatibility
            df = pd.DataFrame({
                'origion': cleaned_comments,
                'mark': list(range(len(cleaned_comments)))
            })
            
            # Use legacy analyzer if available
            if self._legacy_analyzer:
                result = self._run_legacy_analysis(df, options)
            else:
                result = self._run_basic_analysis(cleaned_comments, options)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "analysis_results": result,
                "metadata": {
                    "total_comments": len(comments),
                    "cleaned_comments": len(cleaned_comments),
                    "processing_time": processing_time,
                    "options": options
                },
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            logger.error("Text analysis failed: %s", e)
            raise LabelingError("Comment analysis failed", 
                              text_sample=comments[0] if comments else None, 
                              cause=e)
    
    def _clean_comments(self, comments: List[str]) -> List[str]:
        """Clean and preprocess text comments."""
        cleaned = []
        
        for comment in comments:
            if not isinstance(comment, str):
                continue
                
            # Basic cleaning
            text = comment.strip()
            if not text:
                continue
                
            # Remove noise patterns (from existing list_process function)
            text = self._apply_cleaning_rules(text)
            
            if text and len(text.strip()) > 0:
                cleaned.append(text)
        
        logger.debug("Cleaned %d/%d comments", len(cleaned), len(comments))
        return cleaned
    
    def _apply_cleaning_rules(self, text: str) -> str:
        """Apply text cleaning rules (adapted from existing code)."""
        punctuation = r"[，。、,.;；：:/]"
        nonsense = r"(没有|无|追问|无追问|无已|已)"
        
        # Basic replacements
        text = text.replace(" ", "").replace("——", "；").replace("\\", "；")
        text = text.replace("（已追问）", "").replace("（无追问）", "")
        text = text.replace("(已追问)", "").replace("(无追问)", "")
        text = text.replace("已追问", "").replace("无追问", "")
        
        # Pattern replacements
        text = re.sub(rf'\d{punctuation}', '；', text)  # 1、
        text = re.sub(r'(?<!\d)\d/(?!\d)', '；', text)  # 1/
        text = re.sub(rf'{punctuation}{punctuation}', '；', text)
        
        # Remove nonsense patterns
        text = re.sub(rf'\d无已', '', text)
        text = re.sub(rf'无{punctuation}*已', '', text)
        text = re.sub(rf'{punctuation}*已$', '', text)
        text = text.replace('无已', '')
        
        text = re.sub(rf'{punctuation}+{nonsense}+{punctuation}', '', text)
        text = re.sub(rf'{punctuation}+{nonsense}$', '', text)
        text = re.sub(rf'\d{nonsense}$', '', text)
        
        # Clean start and end
        if text.startswith('；'):
            text = text[1:]
        
        text = re.sub(rf'{punctuation}$', '', text)
        text = re.sub(rf'^\d$', '', text)
        text = re.sub(rf'{nonsense}$', '', text)
        
        return text.strip()
    
    async def _run_legacy_analysis(self, df: pd.DataFrame, options: Dict[str, Any]) -> Any:
        """Run legacy analysis pipeline asynchronously."""
        try:
            # Extract parameters
            question = options.get("question", "")
            theme = options.get("theme", "其他设计")
            emotion = options.get("emotion", "其他")
            
            # Run legacy analysis
            result = await self._legacy_analyzer(question, theme, emotion, df, mode='prod')
            return result
            
        except Exception as e:
            raise ModelCallError("Legacy analysis failed", "text_analysis", cause=e)
    
    def _run_basic_analysis(self, comments: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """Run basic analysis when legacy functions unavailable."""
        logger.warning("Running basic analysis - legacy functions not available")
        
        # Simple frequency analysis
        word_freq = self._calculate_word_frequency(comments)
        
        # Basic sentiment classification
        sentiment_dist = self._classify_sentiment(comments)
        
        return {
            "word_frequency": word_freq,
            "sentiment_distribution": sentiment_dist,
            "total_processed": len(comments),
            "analysis_type": "basic"
        }
    
    def _calculate_word_frequency(self, comments: List[str]) -> Dict[str, int]:
        """Calculate word frequency for basic analysis."""
        word_counts = {}
        
        for comment in comments:
            # Simple word splitting (for Chinese text)
            words = list(comment.replace(" ", ""))
            for word in words:
                if word.strip() and len(word) > 0:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return top 20 words
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_words[:20])
    
    def _classify_sentiment(self, comments: List[str]) -> Dict[str, int]:
        """Basic sentiment classification."""
        positive_words = ["好", "喜欢", "棒", "优秀", "满意", "赞"]
        negative_words = ["差", "不好", "讨厌", "糟糕", "失望", "烂"]
        
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for comment in comments:
            has_positive = any(word in comment for word in positive_words)
            has_negative = any(word in comment for word in negative_words)
            
            if has_positive and not has_negative:
                sentiment_counts["positive"] += 1
            elif has_negative and not has_positive:
                sentiment_counts["negative"] += 1
            else:
                sentiment_counts["neutral"] += 1
        
        return sentiment_counts