from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from app.citations.schemas import CitationDraft
from app.documents.interfaces import DocumentChunkContract
from app.knowledge_graph.schemas import (
    EdgeType,
    GraphExtractionOutput,
    GraphImportance,
    KnowledgeEdgeDraft,
    KnowledgeNodeDraft,
    NodeType,
    VerificationStatus,
)

LOCAL_KNOWLEDGE_GRAPH_EXECUTOR = "local-rule-engine-v1"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _display(value: str, limit: int = 240) -> str:
    value = " ".join(value.split()).strip(" ,;")
    return value if len(value) <= limit else f"{value[:limit].rsplit(' ', 1)[0]}..."


def _quote(value: str, limit: int = 360) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[:limit].rsplit(" ", 1)[0]


def _citation(chunk: DocumentChunkContract, value: str) -> CitationDraft:
    confidence = chunk.ocr_confidence if chunk.ocr_confidence is not None else 0.85
    return CitationDraft(
        documentId=chunk.document_id,
        chunkId=chunk.id,
        quote=_quote(value),
        page=chunk.pdf_page_start,
        article=chunk.article,
        clause=chunk.clause,
        point=chunk.point,
        sourceConfidence=max(0.0, min(1.0, confidence)),
    )


def _merge_citations(*groups: Iterable[CitationDraft]) -> list[CitationDraft]:
    values: dict[tuple[str, str, str, int], CitationDraft] = {}
    for citation in (item for group in groups for item in group):
        key = (citation.document_id, citation.chunk_id, citation.quote, citation.page)
        values.setdefault(key, citation)
    return list(values.values())


class RuleBasedKnowledgeGraphExtractor:
    """Source-grounded fallback used only when no model adapter is configured."""

    max_provisions = 80
    max_facts = 40

    _article = re.compile(r"(?im)^\s*(Điều\s+\d+[a-zA-Z]?)\b")
    _sentences = re.compile(r"[^.!?;\n]+(?:[.!?;]|$)", re.UNICODE)
    _metadata = re.compile(r"(?im)^\s*(?P<label>Người ký|Cơ quan)\s*:\s*(?P<value>[^\r\n]+)")
    _assignment = re.compile(
        r"(?P<actor>(?:Bộ|Sở|Ủy ban nhân dân|Uỷ ban nhân dân|UBND|Chính phủ|"
        r"Thủ tướng Chính phủ|Văn phòng Chính phủ|Hội đồng nhân dân|HĐND)"
        r"\b.{0,120}?)\s+(?P<verb>có trách nhiệm|chịu trách nhiệm|chủ trì|"
        r"tổ chức thực hiện|thực hiện)\s+(?P<task>.{3,240})$",
        re.IGNORECASE | re.UNICODE,
    )
    _reference = re.compile(
        r"\b(?P<kind>Luật|Nghị định|Thông tư|Quyết định|Nghị quyết|Pháp lệnh)"
        r"(?:\s+[\wÀ-ỹĐđ-]+){0,12}?\s+số\s+(?P<number>\d[\w./-]*)",
        re.IGNORECASE | re.UNICODE,
    )
    _duration = re.compile(
        r"\b\d{1,3}(?:[.,]\d+)?\s*(?:ngày|tháng|năm|giờ|phút)\b",
        re.IGNORECASE | re.UNICODE,
    )
    _temporal_keywords = (
        "thời hạn",
        "thời hiệu",
        "trong vòng",
        "chậm nhất",
        "kể từ",
        "hoàn thành",
        "hết hạn",
    )

    def extract(
        self,
        document_id: str,
        chunks: list[DocumentChunkContract],
        *,
        document_name: str | None = None,
    ) -> GraphExtractionOutput:
        nodes: dict[tuple[NodeType, str], KnowledgeNodeDraft] = {}
        edges: dict[tuple[str, str, EdgeType], KnowledgeEdgeDraft] = {}

        def add_node(
            node_type: NodeType,
            name: str,
            citation: CitationDraft | None,
            *,
            confidence: float,
            properties: dict[str, object] | None = None,
        ) -> str:
            name = _display(name)
            key = node_type, " ".join(name.casefold().split())
            existing = nodes.get(key)
            if existing is not None:
                citations = [citation] if citation else []
                nodes[key] = existing.model_copy(
                    update={
                        "properties": {**existing.properties, **dict(properties or {})},
                        "confidence": max(existing.confidence, confidence),
                        "citations": _merge_citations(existing.citations, citations),
                    }
                )
                return existing.node_id
            node_id = _stable_id("local-node", node_type.value, key[1])
            nodes[key] = KnowledgeNodeDraft(
                nodeId=node_id,
                type=node_type,
                name=name,
                properties=dict(properties or {}),
                importance=GraphImportance.MEDIUM,
                confidence=confidence,
                citations=[citation] if citation else [],
            )
            return node_id

        def add_edge(
            source: str,
            target: str,
            edge_type: EdgeType,
            citation: CitationDraft,
            *,
            confidence: float,
            needs_review: bool = False,
        ) -> None:
            key = source, target, edge_type
            existing = edges.get(key)
            if existing is not None:
                edges[key] = existing.model_copy(
                    update={"citations": _merge_citations(existing.citations, [citation])}
                )
                return
            edges[key] = KnowledgeEdgeDraft(
                edgeId=_stable_id("local-edge", source, target, edge_type.value),
                sourceNodeId=source,
                targetNodeId=target,
                type=edge_type,
                importance=GraphImportance.MEDIUM,
                confidence=confidence,
                citations=[citation],
                verificationStatus=(
                    VerificationStatus.NEEDS_REVIEW
                    if needs_review
                    else VerificationStatus.NOT_REQUIRED
                ),
            )

        first = next((chunk for chunk in chunks if chunk.content.strip()), None)
        root_citation = _citation(first, self._first_line(first.content)) if first else None
        root_id = add_node(
            NodeType.LEGAL_DOCUMENT,
            document_name or f"Tài liệu {document_id}",
            root_citation,
            confidence=1.0,
            properties={
                "documentId": document_id,
                "extractionMode": "LOCAL_RULE_BASED",
                "sourceChunkCount": len(chunks),
            },
        )

        provisions: dict[str, str] = {}
        fact_count = 0
        for chunk in chunks:
            content = chunk.content.strip()
            if not content:
                continue
            line = self._first_line(content)
            anchor = _citation(chunk, line)
            parent_id = root_id
            article_match = self._article.search(content)
            article = chunk.article or (article_match.group(1) if article_match else None)
            if article and len(provisions) < self.max_provisions:
                article_key = " ".join(article.casefold().split())
                if article_key not in provisions:
                    title = line if line.casefold().startswith(article.casefold()) else article
                    provisions[article_key] = add_node(
                        NodeType.LEGAL_PROVISION,
                        title,
                        anchor,
                        confidence=0.98,
                        properties={"article": article, "excerpt": _quote(content)},
                    )
                    add_edge(
                        root_id, provisions[article_key], EdgeType.CONTAINS, anchor, confidence=0.98
                    )
                parent_id = provisions[article_key]

            for match in self._metadata.finditer(content):
                citation = _citation(chunk, match.group(0))
                node_type = (
                    NodeType.AGENCY
                    if match.group("label").casefold() == "cơ quan"
                    else NodeType.PERSON
                )
                node_id = add_node(
                    node_type,
                    match.group("value").strip(" ,.;"),
                    citation,
                    confidence=0.9,
                    properties={"sourceLabel": match.group("label")},
                )
                add_edge(
                    node_id,
                    root_id,
                    EdgeType.APPROVES,
                    citation,
                    confidence=0.65,
                    needs_review=True,
                )

            for sentence_match in self._sentences.finditer(content):
                sentence = sentence_match.group(0).strip()
                if not sentence or fact_count >= self.max_facts:
                    continue
                citation = _citation(chunk, sentence)
                fact_parent = parent_id
                assignment = self._assignment.search(sentence.rstrip(" .;"))
                if assignment:
                    actor_id = add_node(
                        NodeType.AGENCY,
                        assignment.group("actor").strip(" ,;:.0123456789)"),
                        citation,
                        confidence=0.78,
                    )
                    task_id = add_node(
                        NodeType.TASK,
                        f"{assignment.group('verb')} {assignment.group('task').strip(' ,;:.')}",
                        citation,
                        confidence=0.74,
                    )
                    add_edge(
                        actor_id,
                        task_id,
                        EdgeType.ASSIGNS_RESPONSIBILITY,
                        citation,
                        confidence=0.72,
                        needs_review=True,
                    )
                    if assignment.group("verb").casefold() == "chủ trì":
                        add_edge(
                            actor_id,
                            task_id,
                            EdgeType.LEADS,
                            citation,
                            confidence=0.78,
                            needs_review=True,
                        )
                    fact_parent = task_id
                    fact_count += 1

                for reference in self._reference.finditer(sentence):
                    if fact_count >= self.max_facts:
                        break
                    reference_id = add_node(
                        NodeType.LEGAL_REFERENCE,
                        reference.group(0).strip(" ,.;"),
                        citation,
                        confidence=0.9,
                        properties={
                            "documentType": reference.group("kind"),
                            "documentNumber": reference.group("number"),
                            "resolved": False,
                        },
                    )
                    add_edge(
                        fact_parent,
                        reference_id,
                        EdgeType.REFERENCES,
                        citation,
                        confidence=0.9,
                        needs_review=True,
                    )
                    fact_count += 1

                folded = sentence.casefold()
                if any(keyword in folded for keyword in self._temporal_keywords):
                    for duration in self._duration.finditer(sentence):
                        if fact_count >= self.max_facts:
                            break
                        deadline_id = add_node(
                            NodeType.DEADLINE,
                            duration.group(0),
                            citation,
                            confidence=0.82,
                            properties={"value": duration.group(0), "context": _display(sentence)},
                        )
                        add_edge(
                            fact_parent,
                            deadline_id,
                            EdgeType.HAS_DEADLINE,
                            citation,
                            confidence=0.78,
                            needs_review=True,
                        )
                        fact_count += 1

        return GraphExtractionOutput(nodes=list(nodes.values()), edges=list(edges.values()))

    @staticmethod
    def _first_line(content: str) -> str:
        return next(
            (line.strip() for line in content.splitlines() if line.strip()), content.strip()
        )
