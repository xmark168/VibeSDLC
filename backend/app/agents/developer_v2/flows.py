from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
import functools
import cocoindex
import os
import logging
from numpy.typing import NDArray
import numpy as np

logger = logging.getLogger(__name__)

# ONNX-optimized embedding model for fast query encoding
_onnx_embedding_model = None

def get_onnx_embedding_model():
    """Get ONNX-optimized embedding model (lazy loaded)."""
    global _onnx_embedding_model
    if _onnx_embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[CocoIndex] Loading ONNX embedding model...")
            _onnx_embedding_model = SentenceTransformer(
                "jinaai/jina-embeddings-v2-base-code",
                backend="onnx",
                model_kwargs={"provider": "CUDAExecutionProvider"},
                trust_remote_code=True
            )
            _onnx_embedding_model.max_seq_length = 512  # Limit for speed
            logger.info("[CocoIndex] ONNX embedding model loaded on GPU")
        except Exception as e:
            logger.warning(f"[CocoIndex] ONNX failed, using default: {e}")
            from sentence_transformers import SentenceTransformer
            _onnx_embedding_model = SentenceTransformer(
                "jinaai/jina-embeddings-v2-base-code",
                trust_remote_code=True
            )
    return _onnx_embedding_model


def embed_query_fast(query: str) -> np.ndarray:
    """Fast query embedding using ONNX model."""
    model = get_onnx_embedding_model()
    return model.encode(query, convert_to_numpy=True)


# This transform flow is used by CocoIndex for indexing (uses built-in for compatibility)
@cocoindex.transform_flow()
def code_to_embedding(
    text: cocoindex.DataSlice[str],
) -> cocoindex.DataSlice[NDArray[np.float32]]:
    """Embeds text using a code-optimized SentenceTransformer model."""
    return text.transform(
        cocoindex.functions.SentenceTransformerEmbed(
            model="jinaai/jina-embeddings-v2-base-code"  # Code-optimized, 768d
        )
    )

# This connection pool is shared with the project manager for database access.
@functools.cache
def connection_pool() -> ConnectionPool:
    """Creates a cached database connection pool."""
    # Ensure environment variables are loaded for direct script execution or testing.
    load_dotenv()
    return ConnectionPool(os.environ["COCOINDEX_DATABASE_URL"])

# NOTE: The static flow definition (`code_embedding_flow`) and its associated search handler
# have been removed. Flow creation and searching are now handled dynamically by the
# AdvancedProjectManager in `project_manager.py` to support multiple projects.
