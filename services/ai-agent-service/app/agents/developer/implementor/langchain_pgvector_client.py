# app/agents/developer/implementor/langchain_pgvector_client.py
"""
LangChain PGVector client for codebase indexing and semantic search
Following LangChain's official pgvector tutorial approach
"""

import os
import hashlib
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging

try:
    from langchain_postgres import PGVector
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.documents import Document

    LANGCHAIN_POSTGRES_AVAILABLE = True
except ImportError:
    LANGCHAIN_POSTGRES_AVAILABLE = False
load_dotenv()
logger = logging.getLogger(__name__)


class LangChainPgVectorClient:
    """
    LangChain-based pgvector client for codebase indexing and semantic search.

    Uses langchain-postgres and follows LangChain's official tutorial approach.
    Provides better integration with LangChain ecosystem and RAG workflows.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        collection_name: str = "code_snippets",
        embedding_model: str = "text-embedding-3-large",
    ):
        """
        Initialize LangChain pgvector client.

        Args:
            connection_string: PostgreSQL connection string (psycopg3 format)
            collection_name: Name of the collection/table
            embedding_model: OpenAI embedding model to use
        """
        self.connection_string = connection_string or os.getenv("PGVECTOR_CONNECTION_STRING")
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        if not self.connection_string:
            logger.warning("No pgvector connection string provided. Using mock mode.")
            self.mock_mode = True
            self.mock_documents = []
            self.vector_store = None
        else:
            self.mock_mode = False
            self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Initialize the LangChain PGVector store."""
        if not LANGCHAIN_POSTGRES_AVAILABLE:
            logger.error(
                "langchain-postgres not available. Install with: pip install langchain-postgres"
            )
            self.mock_mode = True
            self.mock_documents = []
            return

        try:
            # Initialize OpenAI embeddings
            embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL"),
            )

            # Convert connection string to psycopg3 format if needed
            connection = self.connection_string
            if "postgresql+psycopg2://" in connection:
                connection = connection.replace("postgresql+psycopg2://", "postgresql+psycopg://")
                logger.info("Converted connection string to psycopg3 format")

            # Initialize PGVector store
            self.vector_store = PGVector(
                embeddings=embeddings,
                collection_name=self.collection_name,
                connection=connection,
                use_jsonb=True,  # Enable JSONB for better metadata support
            )

            logger.info(f"LangChain PGVector initialized with collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to initialize LangChain PGVector: {e}")
            self.mock_mode = True
            self.mock_documents = []
            self.vector_store = None

    def index_code_snippet(
        self,
        file_path: str,
        snippet_type: str,
        content: str,
        snippet_name: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Index a single code snippet using LangChain Documents.

        Args:
            file_path: Path to the source file
            snippet_type: Type of snippet (function, class, file, etc.)
            content: Code content
            snippet_name: Name of the snippet (function/class name)
            start_line: Starting line number
            end_line: Ending line number
            language: Programming language
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate content hash for deduplication
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Prepare metadata
            doc_metadata = {
                "file_path": file_path,
                "snippet_type": snippet_type,
                "snippet_name": snippet_name,
                "start_line": start_line,
                "end_line": end_line,
                "language": language,
                "content_hash": content_hash,
                **(metadata or {}),
            }

            # Remove None values from metadata
            doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}

            # Create LangChain Document
            document = Document(page_content=content, metadata=doc_metadata)

            if self.mock_mode:
                # Store in mock documents
                # Check for duplicates by content_hash
                existing_hashes = [doc.metadata.get("content_hash") for doc in self.mock_documents]
                if content_hash not in existing_hashes:
                    self.mock_documents.append(document)
                    logger.debug(f"Added document to mock store: {content_hash}")
                else:
                    logger.debug(f"Document already exists in mock store: {content_hash}")
                return True

            if not self.vector_store:
                logger.error("Vector store not initialized")
                return False

            # Check if document already exists
            existing_docs = self.vector_store.similarity_search(
                content[:100],  # Use first 100 chars for quick check
                k=1,
                filter={"content_hash": content_hash},
            )

            if existing_docs:
                logger.debug(f"Document already indexed: {content_hash}")
                return True

            # Add document to vector store
            self.vector_store.add_documents([document], ids=[content_hash])
            logger.debug(f"Successfully indexed document: {content_hash}")
            return True

        except Exception as e:
            logger.error(f"Failed to index snippet: {e}")
            return False

    def search_similar_code(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        language: Optional[str] = None,
        snippet_type: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code snippets using LangChain's similarity search.

        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            language: Filter by programming language
            snippet_type: Filter by snippet type
            file_path: Filter by file path

        Returns:
            List of similar code snippets with metadata
        """
        try:
            if self.mock_mode:
                # Mock search - simple keyword matching
                results = []
                query_words = query.lower().split()

                for doc in self.mock_documents:
                    content_lower = doc.page_content.lower()
                    matches = sum(1 for word in query_words if word in content_lower)

                    if matches > 0:
                        # Apply filters
                        if language and doc.metadata.get("language") != language:
                            continue
                        if snippet_type and doc.metadata.get("snippet_type") != snippet_type:
                            continue
                        if file_path and doc.metadata.get("file_path") != file_path:
                            continue

                        similarity = min(matches / len(query_words), 1.0)
                        if similarity >= similarity_threshold:
                            results.append(
                                {
                                    "similarity": similarity,
                                    "content": doc.page_content[:500] + "..."
                                    if len(doc.page_content) > 500
                                    else doc.page_content,
                                    **doc.metadata,
                                }
                            )

                # Sort by similarity and limit results
                results.sort(key=lambda x: x["similarity"], reverse=True)
                return results[:limit]

            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []

            # Build filter dictionary
            filter_dict = {}
            if language:
                filter_dict["language"] = language
            if snippet_type:
                filter_dict["snippet_type"] = snippet_type
            if file_path:
                filter_dict["file_path"] = file_path

            # Perform similarity search with score
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query=query,
                k=limit * 2,  # Get more results to filter by threshold
                filter=filter_dict if filter_dict else None,
            )

            # Filter by similarity threshold and format results
            results = []
            for doc, score in docs_with_scores:
                # Convert distance to similarity (assuming cosine distance)
                similarity = 1 - score if score <= 1 else 0

                if similarity >= similarity_threshold:
                    result = {
                        "similarity": similarity,
                        "content": doc.page_content[:500] + "..."
                        if len(doc.page_content) > 500
                        else doc.page_content,
                        **doc.metadata,
                    }
                    results.append(result)

                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            logger.error(f"Failed to search similar code: {e}")
            return []

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed code.

        Returns:
            Dictionary with index statistics
        """
        try:
            if self.mock_mode:
                languages = {}
                snippet_types = {}

                for doc in self.mock_documents:
                    lang = doc.metadata.get("language")
                    if lang:
                        languages[lang] = languages.get(lang, 0) + 1

                    stype = doc.metadata.get("snippet_type")
                    if stype:
                        snippet_types[stype] = snippet_types.get(stype, 0) + 1

                return {
                    "total_snippets": len(self.mock_documents),
                    "languages": languages,
                    "snippet_types": snippet_types,
                    "mock_mode": True,
                    "collection_name": self.collection_name,
                }

            if not self.vector_store:
                return {"error": "Vector store not initialized"}

            # For LangChain PGVector, we need to query the database directly
            # This is a simplified version - in practice, you might want to
            # access the underlying connection for detailed stats

            return {
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
                "mock_mode": False,
                "note": "Detailed stats require direct database access",
            }

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}

    def clear_index(self, file_path: Optional[str] = None) -> bool:
        """
        Clear the index (all or for specific file).

        Args:
            file_path: If provided, only clear snippets from this file

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.mock_mode:
                if file_path:
                    # Remove documents from specific file
                    self.mock_documents = [
                        doc
                        for doc in self.mock_documents
                        if doc.metadata.get("file_path") != file_path
                    ]
                else:
                    # Clear all documents
                    self.mock_documents.clear()
                return True

            if not self.vector_store:
                logger.error("Vector store not initialized")
                return False

            # For LangChain PGVector, we need to use delete method
            if file_path:
                # Delete documents with specific file_path
                # Note: This requires the vector store to support deletion by filter
                logger.warning(
                    "Selective deletion by file_path not directly supported in current LangChain PGVector"
                )
                return False
            else:
                # Clear entire collection - this would require recreating the vector store
                logger.warning("Full collection clearing requires manual database operations")
                return False

        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False

    def as_retriever(self, **kwargs):
        """
        Convert to LangChain retriever for RAG workflows.

        Returns:
            LangChain retriever object
        """
        if self.mock_mode or not self.vector_store:
            logger.warning("Cannot create retriever in mock mode or without vector store")
            return None

        return self.vector_store.as_retriever(**kwargs)

    def get_vector_store(self):
        """
        Get the underlying LangChain PGVector store.

        Returns:
            PGVector instance or None
        """
        return self.vector_store
