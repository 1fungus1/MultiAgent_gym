import hashlib
import logging
from typing import Any

from pymilvus import DataType, MilvusClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class MilvusKnowledgeStore:
    def __init__(self) -> None:
        if not settings.rag_milvus_uri:
            raise RuntimeError("未配置 RAG_MILVUS_URI")
        self.collection_name = settings.rag_collection
        self.dimensions = settings.rag_dense_dimensions
        self.client = MilvusClient(
            uri=settings.rag_milvus_uri,
            token=settings.rag_milvus_token or None,
            timeout=10,
        )
        self.client.use_database("default")

    def _create_collection(self) -> None:
        schema = self.client.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field(
            field_name="chunk_id",
            datatype=DataType.VARCHAR,
            is_primary=True,
            max_length=64,
        )
        schema.add_field(
            field_name="item_id",
            datatype=DataType.VARCHAR,
            max_length=32,
        )
        schema.add_field(
            field_name="title",
            datatype=DataType.VARCHAR,
            max_length=500,
        )
        schema.add_field(
            field_name="chapter",
            datatype=DataType.VARCHAR,
            max_length=300,
        )
        schema.add_field(
            field_name="content",
            datatype=DataType.VARCHAR,
            max_length=60000,
        )
        schema.add_field(
            field_name="source",
            datatype=DataType.VARCHAR,
            max_length=1000,
        )
        schema.add_field(
            field_name="document_hash",
            datatype=DataType.VARCHAR,
            max_length=64,
        )
        schema.add_field(
            field_name="dense",
            datatype=DataType.FLOAT_VECTOR,
            dim=self.dimensions,
        )
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense",
            index_name="gym_dense_index",
            index_type="AUTOINDEX",
            metric_type="IP",
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info("Created Milvus collection %s", self.collection_name)

    def ensure_collection(self) -> None:
        if not self.client.has_collection(self.collection_name):
            self._create_collection()
        self.client.load_collection(self.collection_name)

    def existing_chunk_ids(self, document_hash: str) -> set[str]:
        rows = self.client.query(
            collection_name=self.collection_name,
            filter=f'document_hash == "{document_hash}"',
            output_fields=["chunk_id"],
            limit=10000,
        )
        return {str(row["chunk_id"]) for row in rows}

    def upsert_chunks(
        self,
        *,
        chunks: list[Any],
        vectors: list[list[float]],
        document_hash: str,
        source_path: str,
    ) -> int:
        records = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk_id = hashlib.sha256(
                f"{document_hash}:{chunk.item_id}".encode()
            ).hexdigest()[:32]
            records.append(
                {
                    "chunk_id": chunk_id,
                    "item_id": chunk.item_id,
                    "title": chunk.title,
                    "chapter": chunk.chapter,
                    "content": chunk.content,
                    "source": source_path,
                    "document_hash": document_hash,
                    "dense": vector,
                }
            )
        if records:
            self.client.upsert(
                collection_name=self.collection_name,
                data=records,
            )
            self.client.flush(self.collection_name)
        return len(records)

    def search(
        self,
        *,
        query_vector: list[float],
        document_hash: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        raw_results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            anns_field="dense",
            filter=f'document_hash == "{document_hash}"',
            limit=limit,
            output_fields=[
                "item_id",
                "title",
                "chapter",
                "content",
                "source",
            ],
            search_params={
                "metric_type": "IP",
                "params": {},
            },
        )
        if not raw_results:
            return []
        results = []
        for hit in raw_results[0]:
            entity = hit.get("entity", {})
            results.append(
                {
                    "item_id": str(entity.get("item_id", "")),
                    "title": str(entity.get("title", "")),
                    "chapter": str(entity.get("chapter", "")),
                    "content": str(entity.get("content", "")),
                    "distance": float(hit.get("distance", 0.0)),
                }
            )
        return results

    def close(self) -> None:
        self.client.close()
