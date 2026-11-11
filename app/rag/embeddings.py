import math
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from app.core.config import settings


class EmbeddingModelError(RuntimeError):
    """Raised when dense embeddings cannot be generated."""


class VolcMultimodalEmbeddingClient:
    def __init__(self) -> None:
        self.api_key = (
            settings.embedding_api_key or settings.ark_api_key
        ).strip()
        self.base_url = (
            settings.embedding_base_url or settings.ark_base_url
        ).rstrip("/")
        self.model = settings.embedding_model
        self.dimensions = settings.rag_dense_dimensions

    def _embed_one(self, text: str) -> list[float]:
        if not self.api_key:
            raise EmbeddingModelError("未配置 EMBEDDING_API_KEY 或 ARK_API_KEY")
        payload = {
            "model": self.model,
            "input": [{"type": "text", "text": text[:6000]}],
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(
                    timeout=settings.embedding_timeout_seconds
                ) as client:
                    response = client.post(
                        f"{self.base_url}/embeddings/multimodal",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    raise EmbeddingModelError(
                        f"向量接口暂时不可用：HTTP {response.status_code}"
                    )
                if response.is_error:
                    raise EmbeddingModelError(
                        f"向量接口请求失败：{response.text[:300]}"
                    )
                data: dict[str, Any] = response.json()
                embedding_data = data.get("data")
                if isinstance(embedding_data, dict):
                    embedding = embedding_data.get("embedding")
                elif isinstance(embedding_data, list) and embedding_data:
                    embedding = embedding_data[0].get("embedding")
                else:
                    embedding = None
                if not embedding:
                    raise EmbeddingModelError("向量接口没有返回 embedding")
                vector = [float(value) for value in embedding[: self.dimensions]]
                if len(vector) != self.dimensions:
                    raise EmbeddingModelError(
                        f"向量维度不足：期望 {self.dimensions}，实际 {len(vector)}"
                    )
                norm = math.sqrt(sum(value * value for value in vector))
                if norm <= 0:
                    raise EmbeddingModelError("向量接口返回了零向量")
                return [value / norm for value in vector]
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exception:
                last_error = exception
                if attempt < 2:
                    time.sleep(0.8 * (attempt + 1))
        raise EmbeddingModelError(
            f"向量生成失败：{last_error or '未知错误'}"
        )

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        workers = max(1, min(settings.rag_embedding_concurrency, 8))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(self._embed_one, texts))
