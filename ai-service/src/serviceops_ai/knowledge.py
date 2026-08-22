from __future__ import annotations

import base64
import binascii
import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

MIN_RETRIEVAL_SCORE = 0.08
MAX_CITATIONS = 3
PROMPT_SAFETY_MESSAGE = (
    "I cannot follow instructions to override safety controls or expose protected context. "
    "Rephrase the request as a ServiceOps question or escalate it to a human operator."
)
PROMPT_ATTACK_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)
    for pattern in (
        (
            r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,80}"
            r"\b(?:previous|prior|above|system|developer|safety|hidden)\b.{0,40}"
            r"\b(?:instructions?|rules?|policy|prompt|controls?)\b"
        ),
        (
            r"\b(?:reveal|show|print|expose|leak|dump|return)\b.{0,80}"
            r"\b(?:system|developer|hidden)\s+(?:prompt|message|instructions?)\b"
        ),
        (
            r"\b(?:reveal|show|print|expose|leak|dump|return)\b.{0,80}"
            r"\b(?:secrets?|passwords?|credentials?|access tokens?|api keys?|"
            r"environment variables?)\b"
        ),
        r"<\s*/?\s*(?:system|developer|assistant)\s*>",
        r"\[(?:system|developer|assistant)\]",
        r"(?:^|\s)(?:system|developer|assistant)\s*:",
        r"\b(?:jailbreak|dan mode|developer mode|unrestricted mode)\b",
        (
            r"\b(?:do not|don't)\s+(?:cite|use|follow)\b.{0,40}"
            r"\b(?:sources?|runbooks?|instructions?)\b"
        ),
        r"\b(?:invent|fabricate|make up)\b.{0,50}\b(?:answer|procedure|policy|facts?)\b",
        (
            r"\b(?:zignoruj|pomiń|zlekceważ)\b.{0,80}"
            r"\b(?:poprzednie|wcześniejsze|systemowe|ukryte)\b.{0,40}"
            r"\b(?:instrukcje|zasady|politykę|prompt|zabezpieczenia)\b"
        ),
        r"\b(?:obejdź|wyłącz)\b.{0,40}\b(?:zabezpieczenia|ograniczenia)\b",
        (
            r"\b(?:ujawnij|pokaż|wyświetl|wypisz|zwróć)\b.{0,80}"
            r"\b(?:prompt systemowy|ukryte instrukcje|hasła|dane uwierzytelniające|"
            r"tokeny dostępu|klucze api|zmienne środowiskowe)\b"
        ),
        (
            r"\b(?:проігноруй|ігноруй|забудь)\b.{0,80}"
            r"\b(?:попередні|системні|приховані)\b.{0,40}"
            r"\b(?:інструкції|правила|політику|промпт|обмеження)\b"
        ),
        r"\b(?:обійди|вимкни)\b.{0,40}\b(?:захист|обмеження|правила безпеки)\b",
        (
            r"\b(?:розкрий|покажи|виведи|надрукуй|поверни)\b.{0,80}"
            r"\b(?:системний промпт|приховані інструкції|паролі|облікові дані|"
            r"токени доступу|ключі api|змінні середовища)\b"
        ),
    )
)
PROMPT_SAFE_NEGATIONS = tuple(
    re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)
    for pattern in (
        (
            r"\b(?:do not|don't|never)\b[^.!?\r\n]{0,120}"
            r"\b(?:reveal|show|print|expose|leak|dump|return)\b[^.!?\r\n]{0,80}"
            r"\b(?:(?:system|developer|hidden)\s+(?:prompt|message|instructions?)|"
            r"secrets?|passwords?|credentials?|access tokens?|api keys?|"
            r"environment variables?)\b"
        ),
        (
            r"\b(?:nie|nigdy nie)\b[^.!?\r\n]{0,120}"
            r"\b(?:ujawniaj|pokazuj|wyświetlaj|wypisuj|zwracaj)\b[^.!?\r\n]{0,80}"
            r"\b(?:prompt systemowy|ukryte instrukcje|hasła|dane uwierzytelniające|"
            r"tokeny dostępu|klucze api|zmienne środowiskowe)\b"
        ),
        (
            r"\b(?:не|ніколи не)\b[^.!?\r\n]{0,120}"
            r"\b(?:розкривай|показуй|виводь|друкуй|повертай)\b[^.!?\r\n]{0,80}"
            r"\b(?:системний промпт|приховані інструкції|паролі|облікові дані|"
            r"токени доступу|ключі api|змінні середовища)\b"
        ),
    )
)
INVISIBLE_CONTROL_CHARACTERS = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
SEPARATED_ASCII_WORD = re.compile(
    r"(?<![A-Za-z])(?:[A-Za-z][._-]){3,}[A-Za-z](?![A-Za-z])"
)
BASE64_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{16,}={0,2}(?![A-Za-z0-9+/_=-])"
)


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
        if _contains_prompt_attack(question):
            return KnowledgeAnswer(
                answer=PROMPT_SAFETY_MESSAGE,
                citations=(),
                grounded=False,
            )

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


def _contains_prompt_attack(question: str) -> bool:
    variants = [_normalize_safety_text(question)]
    variants.extend(_decoded_base64_variants(variants[0]))
    for variant in variants:
        for safe_pattern in PROMPT_SAFE_NEGATIONS:
            variant = safe_pattern.sub("", variant)
        if any(pattern.search(variant) for pattern in PROMPT_ATTACK_PATTERNS):
            return True
    return False


def _normalize_safety_text(value: str) -> str:
    normalized = value
    for _ in range(2):
        decoded = html.unescape(unquote(normalized))
        if decoded == normalized:
            break
        normalized = decoded
    normalized = unicodedata.normalize("NFKC", normalized)
    normalized = INVISIBLE_CONTROL_CHARACTERS.sub("", normalized)
    normalized = SEPARATED_ASCII_WORD.sub(
        lambda match: re.sub(r"[._-]", "", match.group()),
        normalized,
    )
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    normalized = re.sub(r"\r\n?", "\n", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return re.sub(r"\n+", "\n", normalized).strip()


def _decoded_base64_variants(value: str) -> list[str]:
    variants: list[str] = []
    for match in BASE64_CANDIDATE.finditer(value):
        candidate = match.group()
        padded = candidate + ("=" * (-len(candidate) % 4))
        try:
            decoded_bytes = base64.b64decode(padded, altchars=b"-_", validate=True)
            decoded = decoded_bytes.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            continue
        if decoded and all(character.isprintable() or character.isspace() for character in decoded):
            variants.append(_normalize_safety_text(decoded))
    return variants


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

    safety_text = list(metadata.values())
    for section_name, section_lines in sections:
        safety_text.append(section_name)
        safety_text.extend(section_lines)
    if _contains_prompt_attack("\n".join(safety_text)):
        raise ValueError(
            f"Knowledge document {path.name} failed prompt-safety validation"
        )

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
