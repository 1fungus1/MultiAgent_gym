from app.agent.knowledge import KnowledgeHit
from app.rag.retriever import HybridKnowledgeRetriever, fuse_rankings


def _keyword(item_id: str, score: float) -> KnowledgeHit:
    return KnowledgeHit(
        item_id=item_id,
        title=f"标题-{item_id}",
        chapter="测试章节",
        content=f"内容-{item_id}",
        score=score,
    )


def test_reciprocal_rank_fusion_prioritizes_results_found_by_both():
    fused = fuse_rankings(
        [_keyword("NUT-001", 20), _keyword("NUT-002", 10)],
        [
            {
                "item_id": "NUT-002",
                "title": "向量标题",
                "chapter": "营养",
                "content": "向量内容",
            },
            {
                "item_id": "BODY-001",
                "title": "体重管理",
                "chapter": "减脂",
                "content": "体重内容",
            },
        ],
        dense_weight=0.4,
        keyword_weight=0.6,
        limit=3,
    )

    assert [item.item_id for item in fused] == ["NUT-002", "NUT-001", "BODY-001"]


def test_hybrid_retriever_falls_back_to_keyword_before_vector_is_ready():
    retriever = HybridKnowledgeRetriever()
    hits = retriever.search("蛋白质摄入怎么安排", top_k=3)
    assert hits
    assert hits[0].item_id == "REC-003" or any(
        item.item_id == "NUT-002" for item in hits
    )
