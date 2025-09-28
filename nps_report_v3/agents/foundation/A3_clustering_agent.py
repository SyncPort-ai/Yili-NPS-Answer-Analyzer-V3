"""
A3 - Semantic Clustering Agent
Foundation Pass Agent for clustering similar responses and identifying themes.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import jieba

from ..base import FoundationAgent, AgentResult, AgentStatus
from ...state import SemanticCluster, TaggedResponse
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class SemanticClusteringAgent(FoundationAgent):
    """
    A3 - Semantic Clustering Agent

    Responsibilities:
    - Group similar responses into clusters
    - Identify common themes and patterns
    - Extract representative quotes
    - Analyze cluster characteristics
    - Generate cluster descriptions
    """

    def __init__(self, llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client

        # Clustering parameters
        self.min_cluster_size = 3
        self.max_clusters = 20
        self.random_state = 42

        # Chinese stop words
        self.stop_words = self._load_chinese_stopwords()

    def _load_chinese_stopwords(self) -> set:
        """Load Chinese stop words."""
        return {
            "的", "了", "是", "我", "你", "他", "她", "它", "们",
            "这", "那", "有", "在", "和", "与", "或", "但", "因为",
            "所以", "如果", "就", "还", "也", "都", "很", "非常",
            "可以", "能", "会", "要", "不", "没", "无", "非",
            "个", "些", "把", "被", "让", "给", "为", "对",
            "从", "到", "上", "下", "里", "去", "来", "过"
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute semantic clustering on responses.

        Args:
            state: Current workflow state with tagged_responses

        Returns:
            AgentResult with semantic clusters
        """
        try:
            tagged_responses = state.get("tagged_responses", [])

            if not tagged_responses:
                logger.warning("No tagged responses available for clustering")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    data={
                        "semantic_clusters": [],
                        "clustering_summary": {
                            "total_clusters": 0,
                            "clustered_responses": 0,
                            "unclustered_responses": 0
                        }
                    }
                )

            # Extract texts for clustering
            texts = []
            response_ids = []

            for response in tagged_responses:
                if response.get("original_text"):
                    texts.append(response["original_text"])
                    response_ids.append(response.get("response_id"))

            if len(texts) < self.min_cluster_size:
                logger.warning(f"Insufficient texts for clustering: {len(texts)}")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    data={
                        "semantic_clusters": [],
                        "clustering_summary": {
                            "insufficient_data": True,
                            "total_texts": len(texts)
                        }
                    }
                )

            # Perform clustering
            clusters = await self._perform_clustering(texts, response_ids, tagged_responses)

            # Generate cluster descriptions
            if self.llm_client:
                clusters = await self._enhance_cluster_descriptions(clusters)

            # Generate summary
            summary = self._generate_clustering_summary(clusters, len(texts))

            # Extract insights
            insights = self._generate_clustering_insights(clusters, summary)

            logger.info(
                f"Clustering complete: {len(clusters)} clusters from {len(texts)} responses"
            )

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "semantic_clusters": clusters,
                    "clustering_summary": summary,
                    "clustering_insights": insights
                }
            )

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                data={}
            )

    async def _perform_clustering(
        self,
        texts: List[str],
        response_ids: List[str],
        tagged_responses: List[TaggedResponse]
    ) -> List[SemanticCluster]:
        """
        Perform clustering on texts.

        Args:
            texts: Text documents
            response_ids: Response IDs
            tagged_responses: Tagged response data

        Returns:
            List of semantic clusters
        """
        # Preprocess texts for Chinese
        processed_texts = [self._preprocess_chinese(text) for text in texts]

        # Vectorize texts
        vectorizer = TfidfVectorizer(
            max_features=100,
            min_df=2,
            max_df=0.8,
            tokenizer=jieba.lcut,
            stop_words=list(self.stop_words)
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
        except ValueError as e:
            logger.warning(f"Vectorization failed: {e}")
            # Fallback to simple vectorization
            vectorizer = TfidfVectorizer(max_features=50)
            tfidf_matrix = vectorizer.fit_transform(texts)

        # Determine optimal number of clusters
        n_clusters = self._determine_optimal_clusters(tfidf_matrix)

        # Perform K-means clustering
        if n_clusters > 1:
            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=self.random_state,
                n_init=10
            )
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
        else:
            # All in one cluster
            cluster_labels = np.zeros(len(texts), dtype=int)

        # Try DBSCAN for outlier detection
        dbscan = DBSCAN(eps=0.3, min_samples=2)
        dbscan_labels = dbscan.fit_predict(tfidf_matrix)

        # Combine results (prefer K-means but mark outliers from DBSCAN)
        outliers = set(i for i, label in enumerate(dbscan_labels) if label == -1)

        # Build clusters
        clusters = []
        unique_labels = set(cluster_labels)

        for label in unique_labels:
            if label == -1:  # Skip noise
                continue

            # Get cluster members
            indices = [i for i, l in enumerate(cluster_labels) if l == label]

            if len(indices) < self.min_cluster_size and len(unique_labels) > 1:
                continue  # Skip small clusters

            # Extract cluster data
            cluster_texts = [texts[i] for i in indices]
            cluster_ids = [response_ids[i] for i in indices if i < len(response_ids)]

            # Get sentiment distribution
            sentiment_dist = self._get_sentiment_distribution(
                [tagged_responses[i] for i in indices if i < len(tagged_responses)]
            )

            # Extract theme
            theme = self._extract_cluster_theme(cluster_texts, vectorizer, label)

            # Get representative quotes
            representative_quotes = self._get_representative_quotes(
                cluster_texts,
                tfidf_matrix[indices] if len(indices) > 0 else None
            )

            cluster = SemanticCluster(
                cluster_id=f"cluster_{label}",
                theme=theme,
                description=f"包含 {len(indices)} 条相关反馈",
                response_ids=cluster_ids,
                size=len(indices),
                representative_quotes=representative_quotes[:3],
                sentiment_distribution=sentiment_dist
            )

            clusters.append(cluster)

        # Sort by size
        clusters.sort(key=lambda x: x["size"], reverse=True)

        return clusters

    def _preprocess_chinese(self, text: str) -> str:
        """
        Preprocess Chinese text for clustering.

        Args:
            text: Input text

        Returns:
            Preprocessed text
        """
        # Remove punctuation and special characters
        import re
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)

        # Remove extra spaces
        text = ' '.join(text.split())

        return text

    def _determine_optimal_clusters(self, tfidf_matrix) -> int:
        """
        Determine optimal number of clusters.

        Args:
            tfidf_matrix: TF-IDF feature matrix

        Returns:
            Optimal number of clusters
        """
        n_samples = tfidf_matrix.shape[0]

        if n_samples < 2:
            return 1

        # Try different cluster numbers
        max_k = min(self.max_clusters, n_samples // 2)
        min_k = 2

        if max_k < min_k:
            return 1

        best_k = min_k
        best_score = -1

        for k in range(min_k, max_k + 1):
            try:
                kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=5)
                labels = kmeans.fit_predict(tfidf_matrix)

                # Calculate silhouette score
                if len(set(labels)) > 1:
                    score = silhouette_score(tfidf_matrix, labels)

                    if score > best_score:
                        best_score = score
                        best_k = k
            except:
                continue

        # Heuristic: prefer fewer clusters unless significant improvement
        if best_score < 0.3 and best_k > 5:
            best_k = max(3, best_k // 2)

        return best_k

    def _extract_cluster_theme(
        self,
        cluster_texts: List[str],
        vectorizer,
        cluster_label: int
    ) -> str:
        """
        Extract theme for a cluster.

        Args:
            cluster_texts: Texts in cluster
            vectorizer: TF-IDF vectorizer
            cluster_label: Cluster label

        Returns:
            Cluster theme description
        """
        if not cluster_texts:
            return f"主题 {cluster_label + 1}"

        try:
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()

            # Re-vectorize cluster texts
            cluster_tfidf = vectorizer.transform([" ".join(cluster_texts)])

            # Get top terms
            scores = cluster_tfidf.toarray()[0]
            top_indices = scores.argsort()[-5:][::-1]

            top_terms = [feature_names[i] for i in top_indices if scores[i] > 0]

            if top_terms:
                return " / ".join(top_terms[:3])
            else:
                # Fallback to common words
                all_text = " ".join(cluster_texts)
                words = jieba.lcut(all_text)
                word_freq = {}

                for word in words:
                    if len(word) > 1 and word not in self.stop_words:
                        word_freq[word] = word_freq.get(word, 0) + 1

                if word_freq:
                    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                    return " / ".join([w for w, _ in top_words[:3]])

        except Exception as e:
            logger.debug(f"Theme extraction failed: {e}")

        return f"主题 {cluster_label + 1}"

    def _get_representative_quotes(
        self,
        cluster_texts: List[str],
        cluster_tfidf=None
    ) -> List[str]:
        """
        Get representative quotes from cluster.

        Args:
            cluster_texts: Texts in cluster
            cluster_tfidf: TF-IDF matrix for cluster

        Returns:
            Representative quotes
        """
        if not cluster_texts:
            return []

        # Simple approach: get texts closest to centroid
        if cluster_tfidf is not None and cluster_tfidf.shape[0] > 1:
            try:
                # Calculate centroid
                centroid = cluster_tfidf.mean(axis=0)

                # Calculate distances
                distances = []

                for i in range(cluster_tfidf.shape[0]):
                    dist = np.linalg.norm(cluster_tfidf[i].toarray() - centroid)
                    distances.append(dist)

                # Get closest texts
                closest_indices = np.argsort(distances)[:5]
                quotes = [cluster_texts[i] for i in closest_indices if i < len(cluster_texts)]

            except:
                # Fallback to first few
                quotes = cluster_texts[:5]
        else:
            # Return first few texts
            quotes = cluster_texts[:5]

        # Clean and truncate quotes
        cleaned_quotes = []

        for quote in quotes:
            if len(quote) > 100:
                quote = quote[:97] + "..."
            cleaned_quotes.append(quote)

        return cleaned_quotes

    def _get_sentiment_distribution(
        self,
        responses: List[TaggedResponse]
    ) -> Dict[str, float]:
        """
        Get sentiment distribution for cluster.

        Args:
            responses: Responses in cluster

        Returns:
            Sentiment distribution
        """
        if not responses:
            return {}

        sentiments = [r.get("sentiment", "neutral") for r in responses]
        total = len(sentiments)

        distribution = {}

        for sentiment in ["positive", "negative", "neutral", "mixed"]:
            count = sentiments.count(sentiment)
            distribution[sentiment] = round(count / total, 2) if total > 0 else 0

        return distribution

    async def _enhance_cluster_descriptions(
        self,
        clusters: List[SemanticCluster]
    ) -> List[SemanticCluster]:
        """
        Use LLM to enhance cluster descriptions.

        Args:
            clusters: Semantic clusters

        Returns:
            Enhanced clusters
        """
        if not self.llm_client or not clusters:
            return clusters

        for cluster in clusters[:5]:  # Enhance top 5 clusters
            try:
                quotes = cluster.get("representative_quotes", [])

                if not quotes:
                    continue

                prompt = f"""
基于以下客户反馈样本，生成一个简洁的主题描述（不超过20字）：

样本反馈：
{chr(10).join([f"- {q}" for q in quotes[:3]])}

当前主题：{cluster.get("theme", "")}

请提供：
1. 更准确的主题名称
2. 主题的简要说明（一句话）

格式：
主题：xxx
说明：xxx
"""

                response = await self.llm_client.generate(prompt, temperature=0.3, max_tokens=100)

                # Parse response
                lines = response.strip().split("\n")

                for line in lines:
                    if line.startswith("主题："):
                        cluster["theme"] = line.replace("主题：", "").strip()
                    elif line.startswith("说明："):
                        cluster["description"] = line.replace("说明：", "").strip()

            except Exception as e:
                logger.debug(f"Failed to enhance cluster {cluster['cluster_id']}: {e}")

        return clusters

    def _generate_clustering_summary(
        self,
        clusters: List[SemanticCluster],
        total_responses: int
    ) -> Dict[str, Any]:
        """
        Generate clustering summary.

        Args:
            clusters: Semantic clusters
            total_responses: Total number of responses

        Returns:
            Summary dictionary
        """
        clustered_responses = sum(c["size"] for c in clusters)

        summary = {
            "total_clusters": len(clusters),
            "clustered_responses": clustered_responses,
            "unclustered_responses": total_responses - clustered_responses,
            "coverage_rate": round(clustered_responses / total_responses * 100, 1) if total_responses > 0 else 0,
            "avg_cluster_size": round(clustered_responses / len(clusters), 1) if clusters else 0,
            "largest_cluster": clusters[0]["theme"] if clusters else None,
            "largest_cluster_size": clusters[0]["size"] if clusters else 0
        }

        # Sentiment summary across clusters
        overall_sentiment = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}

        for cluster in clusters:
            dist = cluster.get("sentiment_distribution", {})
            size = cluster["size"]

            for sentiment, ratio in dist.items():
                overall_sentiment[sentiment] += ratio * size

        if clustered_responses > 0:
            for sentiment in overall_sentiment:
                overall_sentiment[sentiment] = round(
                    overall_sentiment[sentiment] / clustered_responses, 2
                )

        summary["overall_sentiment"] = overall_sentiment

        return summary

    def _generate_clustering_insights(
        self,
        clusters: List[SemanticCluster],
        summary: Dict[str, Any]
    ) -> List[str]:
        """
        Generate insights from clustering.

        Args:
            clusters: Semantic clusters
            summary: Clustering summary

        Returns:
            List of insights
        """
        insights = []

        # Coverage insight
        coverage = summary.get("coverage_rate", 0)

        if coverage > 80:
            insights.append(f"聚类覆盖率高达{coverage:.1f}%，反馈具有明显的主题集中性")
        elif coverage < 50:
            insights.append(f"聚类覆盖率仅{coverage:.1f}%，反馈较为分散，需要个性化分析")

        # Top themes insight
        if clusters:
            top_3 = [c["theme"] for c in clusters[:3]]
            insights.append(f"主要反馈主题：{', '.join(top_3)}")

        # Sentiment pattern insight
        overall_sentiment = summary.get("overall_sentiment", {})

        if overall_sentiment.get("positive", 0) > 0.6:
            insights.append("各主题群体整体情感偏正面，产品获得较好认可")
        elif overall_sentiment.get("negative", 0) > 0.4:
            insights.append("多个主题群体存在负面情感，需要针对性改进")

        # Cluster size insight
        if clusters and clusters[0]["size"] > summary.get("avg_cluster_size", 0) * 2:
            insights.append(
                f"最大主题群'{clusters[0]['theme']}'包含{clusters[0]['size']}条反馈，"
                f"是重点关注领域"
            )

        return insights