from typing import Any

from pydantic import Field

from app.model.schemas.base import APIModel


class GraphNode(APIModel):
    id: str
    type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    citation_ids: list[str] = Field(default_factory=list)


class GraphEdge(APIModel):
    id: str
    source: str
    target: str
    type: str
    label: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    citation_ids: list[str] = Field(default_factory=list)


class KnowledgeGraphResponse(APIModel):
    document_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
