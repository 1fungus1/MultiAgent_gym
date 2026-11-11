import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import BASE_DIR, settings

ITEM_HEADING = re.compile(r"^###\s+([A-Z]+-\d+)｜(.+)$")
CHAPTER_HEADING = re.compile(r"^##\s+(.+)$")
LATIN_WORD = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_+-]*")
CHINESE_RUN = re.compile(r"[\u4e00-\u9fff]+")
MINIMUM_RELEVANCE_SCORE = 2.5


@dataclass(frozen=True)
class KnowledgeChunk:
    item_id: str
    title: str
    chapter: str
    content: str
    term_frequency: Counter[str]
    length: int


@dataclass(frozen=True)
class KnowledgeHit:
    item_id: str
    title: str
    chapter: str
    content: str
    score: float


def _tokens(text: str) -> list[str]:
    normalized = text.lower()
    tokens = LATIN_WORD.findall(normalized)
    for run in CHINESE_RUN.findall(normalized):
        if len(run) == 1:
            tokens.append(run)
            continue
        for width in (2, 3):
            tokens.extend(
                run[index : index + width]
                for index in range(len(run) - width + 1)
            )
    return tokens


class KnowledgeBase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.chunks = self._parse(path)
        self.document_frequency = Counter(
            term for chunk in self.chunks for term in chunk.term_frequency
        )
        self.average_length = (
            sum(chunk.length for chunk in self.chunks) / len(self.chunks)
            if self.chunks
            else 1.0
        )

    @staticmethod
    def _parse(path: Path) -> list[KnowledgeChunk]:
        if not path.exists():
            return []

        lines = path.read_text(encoding="utf-8").splitlines()
        chunks: list[KnowledgeChunk] = []
        chapter = ""
        current_id = ""
        current_title = ""
        body: list[str] = []

        def flush() -> None:
            if not current_title:
                return
            content = "\n".join(body).strip()
            weighted_text = f"{current_title}\n{current_title}\n{content}"
            tokens = _tokens(weighted_text)
            if tokens:
                chunks.append(
                    KnowledgeChunk(
                        item_id=current_id,
                        title=current_title,
                        chapter=chapter,
                        content=content,
                        term_frequency=Counter(tokens),
                        length=len(tokens),
                    )
                )

        for line in lines:
            chapter_match = CHAPTER_HEADING.match(line)
            item_match = ITEM_HEADING.match(line)
            if item_match:
                flush()
                current_id, current_title = item_match.groups()
                body = []
            elif chapter_match:
                flush()
                current_id = ""
                current_title = ""
                body = []
                chapter = chapter_match.group(1).strip()
            elif current_title:
                body.append(line)
        flush()
        return chunks

    def search(self, query: str, top_k: int = 5) -> list[KnowledgeHit]:
        query_terms = Counter(_tokens(query))
        if not query_terms or not self.chunks:
            return []

        total_documents = len(self.chunks)
        scored: list[KnowledgeHit] = []
        for chunk in self.chunks:
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = chunk.term_frequency.get(term, 0)
                if frequency == 0:
                    continue
                document_frequency = self.document_frequency[term]
                inverse_document_frequency = math.log(
                    1 + (total_documents - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                denominator = frequency + 1.5 * (
                    1 - 0.75 + 0.75 * chunk.length / self.average_length
                )
                score += (
                    inverse_document_frequency
                    * frequency
                    * 2.5
                    / denominator
                    * min(query_frequency, 3)
                )
            if query.strip() and query.strip() in chunk.title:
                score += 8.0
            if score > 0:
                scored.append(
                    KnowledgeHit(
                        item_id=chunk.item_id,
                        title=chunk.title,
                        chapter=chunk.chapter,
                        content=chunk.content,
                        score=round(score, 4),
                    )
                )

        scored.sort(key=lambda item: item.score, reverse=True)
        if not scored:
            return []
        threshold = max(
            MINIMUM_RELEVANCE_SCORE,
            scored[0].score * 0.35,
        )
        relevant = [item for item in scored if item.score >= threshold]
        return relevant[: max(1, min(top_k, 10))]


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    path = Path(settings.agent_knowledge_file)
    if not path.is_absolute():
        path = BASE_DIR / path
    return KnowledgeBase(path)
