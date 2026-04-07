"""Lightweight embedding service using HuggingFace Inference API."""

from __future__ import annotations

import asyncio
import logging

import httpx
import numpy as np

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 1.0  # seconds


class LightweightEmbeddingService:
    """Drop-in replacement for EmbeddingService that calls HuggingFace API.

    Uses the free Inference API instead of loading sentence-transformers
    locally, saving ~137 MB RAM.
    """

    def __init__(
        self,
        inference_url: str,
        api_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        self._client = httpx.AsyncClient(
            base_url=inference_url,
            headers=headers,
            timeout=timeout,
        )
        self._inference_url = inference_url

    # ------------------------------------------------------------------
    # Public interface (matches EmbeddingService)
    # ------------------------------------------------------------------

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string. Returns L2-normalized (384,) float32 vector."""
        raw = await self._call_api({"inputs": text})
        vec = np.array(raw, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    async def embed_batch(self, texts: list[str], batch_size: int | None = None) -> np.ndarray:
        """Embed multiple texts. Returns L2-normalized (N, 384) float32 array."""
        raw = await self._call_api({"inputs": texts})
        arr = np.array(raw, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        return arr / norms

    @staticmethod
    def build_movie_text(
        title: str,
        overview: str | None = None,
        genres: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> str:
        """Build text representation for embedding.

        Identical to ``EmbeddingService.build_movie_text`` and
        ``pipeline/embedder.py:build_movie_text``.
        """
        parts: list[str] = [f"{title}."]
        if overview:
            parts.append(overview)
        if genres:
            parts.append(f"Genres: {', '.join(genres)}.")
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}.")
        return " ".join(parts)

    async def warm_up(self) -> None:
        """Send a throwaway request to wake up the HF model."""
        try:
            await self.embed_text("warm up")
            logger.info("HuggingFace Inference API warm-up successful")
        except Exception:
            logger.warning("HuggingFace Inference API warm-up failed; first request may be slow")

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call_api(self, payload: dict) -> list:
        """POST to HuggingFace Inference API with retry on 503 (model loading)."""
        backoff = _INITIAL_BACKOFF
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._client.post("", json=payload)
                if resp.status_code == 503:
                    # Model is loading — wait and retry
                    wait = min(backoff, 30.0)
                    logger.info(
                        "HF model loading (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    backoff *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code != 503:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
        msg = f"HuggingFace Inference API failed after {_MAX_RETRIES} retries"
        raise RuntimeError(msg) from last_exc
