"""Embedded manual retrieval demo: chunking, lexical + vector retrieval, gating."""

from .chunking import Chunk, build_chunks
from .hybrid import HybridIndex
from .normalize import EntityNormalizer
from .rerank_gate import needs_rerank

__all__ = ["Chunk", "build_chunks", "HybridIndex", "EntityNormalizer", "needs_rerank"]
