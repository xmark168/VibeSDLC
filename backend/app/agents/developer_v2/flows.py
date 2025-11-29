from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
import functools
import cocoindex
import os
from numpy.typing import NDArray
import numpy as np

# This transform flow is used by the dynamic project manager to create embeddings.
@cocoindex.transform_flow()
def code_to_embedding(
    text: cocoindex.DataSlice[str],
) -> cocoindex.DataSlice[NDArray[np.float32]]:
    """Embeds text using a SentenceTransformer model."""
    return text.transform(
        cocoindex.functions.SentenceTransformerEmbed(
            model="sentence-transformers/all-MiniLM-L6-v2"
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
