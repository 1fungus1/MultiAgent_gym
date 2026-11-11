import hashlib
import logging
import threading
from functools import lru_cache
from typing import Any

from app.agent.knowledge import KnowledgeBase, KnowledgeHit, get_knowledge_base
from app.core.config import settings
from app.rag.embeddings import (
    EmbeddingModelError,
    VolcMultimodalEmbeddingClient,
)
from app.rag.milvus_store import MilvusKnowledgeStore

logger = logging.getLogger(__name__)


def _document_hash(path: Any) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fuse_rankings(
    keyword_hits: list[KnowledgeHit],
    vector_hits: list[dict[str, Any]],
    *,
    dense_weight: float,
    keyword_weight: float,
    limit: int,
) -> list[KnowledgeHit]:
    rank_constant = 60
    keyword_rank = {
        hit.item_id: index
        for index, hit in enumerate(keyword_hits, start=1)
    }
    vector_rank = {
        str(hit["item_id"]): index
        for index, hit in enumerate(vector_hits, start=1)
    }
    keyword_by_id = {hit.item_id: hit for hit in keyword_hits}
    vector_by_id = {str(hit["item_id"]): hit for hit in vector_hits}

    ranked: list[KnowledgeHit] = []
    for item_id in set(keyword_rank) | set(vector_rank):
        score = 0.0
        if item_id in keyword_rank:
            score += keyword_weight / (
                rank_constant + keyword_rank[item_id]
            )
        if item_id in vector_rank:
            score += dense_weight / (
                rank_constant + vector_rank[item_id]
            )
        keyword_hit = keyword_by_id.get(item_id)
        vector_hit = vector_by_id.get(item_id)
        ranked.append(
            KnowledgeHit(
                item_id=item_id,
                title=str(
                    keyword_hit.title
                    if keyword_hit
                    else vector_hit["title"]
                ),
                chapter=str(
                    keyword_hit.chapter
                    if keyword_hit
                    else vector_hit["chapter"]
                ),
                content=str(
                    keyword_hit.content
                    if keyword_hit
                    else vector_hit["content"]
                ),
                score=round(score * 1000, 4),
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


class HybridKnowledgeRetriever:
    def __init__(
        self,
        knowledge: KnowledgeBase | None = None,
        embedding_client: VolcMultimodalEmbeddingClient | None = None,
    ) -> None:
        self.knowledge = knowledge or get_knowledge_base()
        self.embedding_client = (
            embedding_client or VolcMultimodalEmbeddingClient()
        )
        self.store: MilvusKnowledgeStore | None = None
        self.document_hash = _document_hash(self.knowledge.path)
        self.vector_ready = False
        self._initialize_lock = threading.Lock()

    def initialize(self) -> None:
        if not settings.rag_enabled:
            logger.info("Hybrid knowledge retrieval is disabled")
            return
        if not settings.rag_auto_index:
            self.store = MilvusKnowledgeStore()
            self.store.ensure_collection()
            self.vector_ready = True
            return
        with self._initialize_lock:
            if self.vector_ready:
                return
            try:
                store = MilvusKnowledgeStore()
                store.ensure_collection()
                existing = store.existing_chunk_ids(self.document_hash)
                if len(existing) < len(self.knowledge.chunks):
                    texts = [
                        f"{chunk.title}\n{chunk.content}"
                        for chunk in self.knowledge.chunks
                    ]
                    logger.info(
                        "Indexing %s knowledge chunks into Milvus collection %s",
                        len(texts),
                        store.collection_name,
                    )
                    vectors = self.embedding_client.embed_documents(texts)
                    store.upsert_chunks(
                        chunks=self.knowledge.chunks,
                        vectors=vectors,
                        document_hash=self.document_hash,
                        source_path=str(self.knowledge.path),
                    )
                    logger.info(
                        "Milvus knowledge indexing complete: collection=%s chunks=%s",
                        store.collection_name,
                        len(vectors),
                    )
                else:
                    logger.info(
                        "Milvus knowledge index is current: collection=%s chunks=%s",
                        store.collection_name,
                        len(existing),
                    )
                self.store = store
                self.vector_ready = True
            except Exception:
                logger.exception("Failed to initialize Milvus knowledge index")
                if settings.rag_required:
                    raise

    def search(self, query: str, top_k: int | None = None) -> list[KnowledgeHit]:
        limit = top_k or settings.agent_knowledge_top_k
        keyword_hits = self.knowledge.search(
            query,
            top_k=settings.rag_candidate_limit,
        )
        vector_hits: list[dict[str, Any]] = []
        if self.vector_ready and self.store is not None:
            try:
                query_vector = self.embedding_client.embed_query(query)
                vector_hits = self.store.search(
                    query_vector=query_vector,
                    document_hash=self.document_hash,
                    limit=settings.rag_candidate_limit,
                )
            except EmbeddingModelError:
                logger.exception("Dense query embedding failed; using keyword fallback")
            except Exception:
                logger.exception("Milvus vector search failed; using keyword fallback")

        if not vector_hits:
            return keyword_hits[:limit]
        return fuse_rankings(
            keyword_hits,
            vector_hits,
            dense_weight=settings.rag_dense_weight,
            keyword_weight=settings.rag_keyword_weight,
            limit=limit,
        )


@lru_cache
def get_hybrid_retriever() -> HybridKnowledgeRetriever:
    return HybridKnowledgeRetriever()


def initialize_knowledge_index() -> None:
    get_hybrid_retriever().initialize()

