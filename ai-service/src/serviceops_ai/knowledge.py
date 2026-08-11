from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

MIN_RETRIEVAL_SCORE = 0.08
MAX_CITATIONS = 3


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    title: str
    revision: str
    section: str
    source_path: str
    text: str


@dataclass(frozen=True)
class RetrievedCitation:
    document_id: str
    title: str
    section: str
    revision: str
    source_path: str
    excerpt: str
    relevance: float


@dataclass(frozen=True)
class KnowledgeAnswer:
    answer: str
    citations: tuple[RetrievedCitation, ...]
    grounded: bool


class KnowledgeBase:
    """Deterministic sparse retrieval plus citation-bound extractive generation."""

    def __init__(self, knowledge_path: Path) -> None:
        self._knowledge_path = knowledge_path
        self.chunks = tuple(_load_chunks(knowledge_path))
        if not self.chunks:
            raise ValueError(f"No Markdown knowledge documents found in {knowledge_path}")

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        searchable_text = [
            f"{chunk.title}. {chunk.section}. {chunk.text}" for chunk in self.chunks
        ]
        self._chunk_vectors = self._vectorizer.fit_transform(searchable_text)
        self._title_vectors = self._vectorizer.transform(
            [f"{chunk.title}. {chunk.section}" for chunk in self.chunks]
        )
        self._searchable_terms = tuple(_terms(text) for text in searchable_text)
        self.document_count = len({chunk.document_id for chunk in self.chunks})
        self.index_version = _index_digest(self.chunks)

    def ask(self, question: str, top_k: int = MAX_CITATIONS) -> KnowledgeAnswer:
        query_vector = self._vectorizer.transform([question])
        content_scores = linear_kernel(query_vector, self._chunk_vectors).ravel()
        title_scores = linear_kernel(query_vector, self._title_vectors).ravel()
        scores = (content_scores * 0.75) + (title_scores * 0.25)
        ranked_indices = scores.argsort()[::-1]
        question_terms = _terms(question)
        matches: list[tuple[KnowledgeChunk, float]] = []
        for index in ranked_indices:
            score = float(scores[index])
            term_overlap = len(question_terms & self._searchable_terms[index])
            if score >= MIN_RETRIEVAL_SCORE and (term_overlap >= 2 or score >= 0.2):
                matches.append((self.chunks[index], score))
            if len(matches) == top_k:
                break
        if not matches:
            return KnowledgeAnswer(
                answer=(
                    "I could not find a supported answer in the ServiceOps knowledge base. "
                    "Escalate the question to a human operator instead of acting on an "
                    "uncited answer."
                ),
                citations=(),
                grounded=False,
            )

        citations = tuple(
            _citation_for_match(self._vectorizer, query_vector, chunk, score)
            for chunk, score in matches
        )
        answer_lines = ["The ServiceOps knowledge base recommends:"]
        answer_lines.extend(
            f"- {citation.excerpt} [{position}]"
            for position, citation in enumerate(citations, start=1)
        )
        return KnowledgeAnswer(
            answer="\n".join(answer_lines),
            citations=citations,
            grounded=True,
        )


def _load_chunks(knowledge_path: Path) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    document_ids: set[str] = set()
    for path in sorted(knowledge_path.glob("*.md")):
        document_chunks = _parse_document(path, knowledge_path)
        document_id = document_chunks[0].document_id
        if document_id in document_ids:
            raise ValueError(f"Duplicate knowledge document id: {document_id}")
        document_ids.add(document_id)
        chunks.extend(document_chunks)
    return chunks


def _parse_document(path: Path, knowledge_path: Path) -> list[KnowledgeChunk]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Knowledge document {path.name} must start with metadata")
    try:
        metadata_end = lines.index("---", 1)
    except ValueError as exception:
        raise ValueError(f"Knowledge document {path.name} has unterminated metadata") from exception

    metadata: dict[str, str] = {}
    for line in lines[1:metadata_end]:
        key, separator, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not separator or not key or not value:
            raise ValueError(f"Invalid metadata in knowledge document {path.name}")
        if key in metadata:
            raise ValueError(
                f"Duplicate metadata key '{key}' in knowledge document {path.name}"
            )
        metadata[key] = value
    required = {"id", "title", "revision"}
    if missing := required - metadata.keys():
        raise ValueError(f"Knowledge document {path.name} is missing {sorted(missing)}")

    source_path = f"knowledge/{path.relative_to(knowledge_path).as_posix()}"
    sections: list[tuple[str, list[str]]] = []
    section = "Overview"
    content: list[str] = []
    for line in lines[metadata_end + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            _append_section(sections, section, content)
            section = stripped[3:].strip()
            content = []
        elif stripped.startswith("# "):
            continue
        elif stripped:
            content.append(stripped.lstrip("- "))
    _append_section(sections, section, content)
    if not sections:
        raise ValueError(f"Knowledge document {path.name} has no usable content")

    return [
        KnowledgeChunk(
            chunk_id=f"{metadata['id']}#{_slug(section_name)}",
            document_id=metadata["id"],
            title=metadata["title"],
            revision=metadata["revision"],
            section=section_name,
            source_path=source_path,
            text=" ".join(section_lines),
        )
        for section_name, section_lines in sections
    ]


def _append_section(
    sections: list[tuple[str, list[str]]], section: str, content: list[str]
) -> None:
    if content:
        sections.append((section, content.copy()))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _terms(value: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in ENGLISH_STOP_WORDS
    )


def _citation_for_match(
    vectorizer: TfidfVectorizer,
    query_vector: object,
    chunk: KnowledgeChunk,
    score: float,
) -> RetrievedCitation:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", chunk.text)
        if sentence.strip()
    ]
    sentence_vectors = vectorizer.transform(sentences)
    sentence_scores = linear_kernel(query_vector, sentence_vectors).ravel()
    excerpt = sentences[int(sentence_scores.argmax())]
    return RetrievedCitation(
        document_id=chunk.document_id,
        title=chunk.title,
        section=chunk.section,
        revision=chunk.revision,
        source_path=chunk.source_path,
        excerpt=excerpt,
        relevance=round(score, 5),
    )


def _index_digest(chunks: tuple[KnowledgeChunk, ...]) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(
            "\x1f".join(
                (
                    chunk.chunk_id,
                    chunk.title,
                    chunk.revision,
                    chunk.source_path,
                    chunk.text,
                )
            ).encode("utf-8")
        )
        digest.update(b"\x1e")
    return f"tfidf-extractive-1-{digest.hexdigest()[:12]}"
