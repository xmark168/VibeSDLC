import os
import logging

import cocoindex
from cocoindex import FlowBuilder
from cocoindex.functions import DetectProgrammingLanguage, SplitRecursively
from pgvector.psycopg import register_vector
from sentence_transformers import CrossEncoder

from pathlib import Path
from app.agents.developer_v2.flows import code_to_embedding, connection_pool, embed_query_fast

logger = logging.getLogger(__name__)


def create_structure_document(project_root):
    """Generate a markdown string representing the project's folder structure."""
    structure_content = "# Project Structure\n\n"

    for root, dirs, files in os.walk(project_root):
        # Exclude common unnecessary directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d != "node_modules" and d != "__pycache__"
        ]

        level = root.replace(project_root, "").count(os.sep)
        indent = "  " * level
        folder_name = (
            os.path.basename(root)
            if root != project_root
            else os.path.basename(project_root)
        )
        structure_content += f"{indent}📁 {folder_name}/\n"

        sub_indent = "  " * (level + 1)
        for file in files:
            # Include relevant file types
            if not file.startswith(".") and file.endswith(
                (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".prisma")
            ):
                structure_content += f"{sub_indent}📄 {file}\n"

    return structure_content


def create_project_flow(project_id: str, project_path: str):
    """Dynamically create a cocoindex flow for a specific project."""

    # Sanitize the project_id to create a valid flow name (alphanumeric and underscores only)
    sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

    @cocoindex.flow_def(name=f"code_embeddings_{sanitized_project_id}")
    def project_flow(
        flow_builder: FlowBuilder, data_scope: cocoindex.DataScope
    ) -> None:
        data_scope["files"] = flow_builder.add_source(
            cocoindex.sources.LocalFile(
                path=project_path,
                included_patterns=[
                    "*.py",
                    "*.ts",
                    "*.tsx",
                    "*.js",
                    "*.jsx",
                    "*.json",
                    "*.md",
                    "*.prisma",
                ],
                excluded_patterns=[
                    "**/.*",
                    "**/node_modules",
                    "__pycache__",
                    "*.pyc",
                    "dist",
                    "build",
                    ".next",
                    "coverage",
                    "*.lock",
                    "bun.lock",
                    "pnpm-lock.yaml",
                    "package-lock.json",
                    "node_modules",
                    "AGENTS.md",
                    "**/AGENTS.md",
                ],
            )
        )

        code_embeddings = data_scope.add_collector()

        with data_scope["files"].row() as file:
            file["language"] = file["filename"].transform(DetectProgrammingLanguage())
            file["chunks"] = file["content"].transform(
                SplitRecursively(),
                language=file["language"],
                chunk_size=800,       # Smaller chunks for better precision
                min_chunk_size=200,   # Allow smaller function chunks
                chunk_overlap=150,    # Less overlap
            )
            with file["chunks"].row() as chunk:
                chunk["embedding"] = chunk["text"].call(code_to_embedding)
                code_embeddings.collect(
                    filename=file["filename"],
                    location=chunk["location"],
                    code=chunk["text"],
                    embedding=chunk["embedding"],
                    start=chunk["start"],
                    end=chunk["end"],
                )

        code_embeddings.export(
            "code_embedding",  # Correctly use the dynamic project_id
            cocoindex.targets.Postgres(),
            primary_key_fields=["filename", "location"],
            vector_indexes=[
                cocoindex.VectorIndexDef(
                    field_name="embedding",
                    metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
                )
            ],
        )

    return project_flow


class AdvancedProjectManager:
    """CocoIndex-based code search with two-stage retrieval (vector + rerank).

    Manages vector embeddings for code search. Stage 1: pgvector similarity,
    Stage 2: cross-encoder reranking (ms-marco-MiniLM-L-6-v2).

    Attrs: flows (project-level), task_flows (per-story), reranker (lazy-loaded)
    Config: chunk_size=800, overlap=150, embedding=jina-embeddings-v2-base-code
    """

    def __init__(self):
        self.flows = {}  # Project-level CocoIndex flows
        self.task_flows = {}  # Task-level CocoIndex flows (per-story)
        self._reranker = None  # Lazy-loaded cross-encoder for reranking
    
    @property
    def reranker(self):
        """Lazy load reranker to avoid slow startup."""
        if self._reranker is None:
            logger.info("[CocoIndex] Loading reranker model...")
            try:
                import torch
                self._reranker = CrossEncoder(
                    'cross-encoder/ms-marco-MiniLM-L-6-v2',
                    device='cuda',
                    max_length=512  # Limit input length for speed
                )
                # Enable FP16 for faster inference on GPU
                if torch.cuda.is_available():
                    self._reranker.model.half()
                logger.info("[CocoIndex] Reranker loaded on GPU with FP16")
            except Exception as e:
                logger.warning(f"[CocoIndex] GPU not available, using CPU: {e}")
                self._reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
        return self._reranker

    def register_project(self, project_id: str, project_path: str):
        """Register and index a new project."""
        # Sanitize the project_id to create a valid flow name
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id in self.flows:
            return

        flow = create_project_flow(project_id, project_path)
        self.flows[sanitized_project_id] = flow

        print(f"Attempting to index project '{project_id}' (sanitized as '{sanitized_project_id}')...")
        try:
            stats = flow.update()
            print(f"✅ Indexing completed for '{project_id}': {stats}")
        except Exception as e:
            if "not up-to-date" in str(e):
                print(
                    f"🔄 Database setup required for flow '{project_id}'. Running setup..."
                )
                flow.setup()
                print("✅ Setup complete. Retrying indexing...")
                stats = flow.update()
                print(f"✅ Indexing completed for '{project_id}' after setup: {stats}")
            else:
                print(f"❌ An unexpected error during indexing for '{project_id}':")
                raise e

    def register_task(self, project_id: str, task_id: str, task_path: str):
        """Register and index a specific task workspace."""
        # task_id is already unique (UUID), no need to include project_id
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id in self.task_flows:
            return

        # Create a flow specific to this task
        flow = create_project_flow(task_identifier, task_path)
        self.task_flows[sanitized_task_id] = flow

        print(f"Attempting to index task '{task_identifier}' (sanitized as '{sanitized_task_id}')...")
        try:
            stats = flow.update()
            print(f"✅ Indexing completed for task '{task_identifier}': {stats}")
        except Exception as e:
            if "not up-to-date" in str(e):
                print(
                    f"🔄 Database setup required for task '{task_identifier}'. Running setup..."
                )
                flow.setup()
                print("✅ Setup complete. Retrying indexing...")
                stats = flow.update()
                print(f"✅ Indexing completed for task '{task_identifier}' after setup: {stats}")
            else:
                print(f"❌ An unexpected error during indexing for task '{task_identifier}':")
                raise e

    def search(self, project_id: str, query: str, top_k: int = 5, search_type: str = "project"):
        """Search in a specific project using two-stage retrieval (vector + rerank)."""
        if search_type == "task":
            raise ValueError("Use search_task for task-specific searches")
        
        # Stage 1: Vector search - get candidates for reranking (20 is optimal for speed/quality)
        candidates = self._vector_search_project(project_id, query, top_k=20)
        
        if not candidates:
            return []
        
        # Stage 2: Rerank with cross-encoder if we have more than top_k results
        if len(candidates) > top_k:
            candidates = self._rerank_results(query, candidates, top_k)
        
        return candidates[:top_k]
    
    def _vector_search_project(self, project_id: str, query: str, top_k: int = 30):
        """Stage 1: Fast vector similarity search."""
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id not in self.flows:
            project_path = f"services/ai-agent-service/app/agents/dev/workspaces/{project_id}"
            if os.path.exists(project_path):
                self.register_project(project_id, project_path)
            else:
                raise ValueError(f"Project {project_id} not registered and path not found.")

        flow = self.flows[sanitized_project_id]
        table_name = cocoindex.utils.get_target_default_name(flow, "code_embedding")
        query_vector = embed_query_fast(query)  # ONNX-optimized

        with connection_pool().connection() as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                sql_query = f'SELECT filename, code, embedding <=> %s AS distance, start, "end" FROM "{table_name}" ORDER BY distance LIMIT %s'
                cur.execute(sql_query, (query_vector, top_k))
                return [
                    {
                        "filename": row[0],
                        "code": row[1],
                        "score": 1.0 - row[2],
                        "start": row[3],
                        "end": row[4],
                    }
                    for row in cur.fetchall()
                ]
    
    def _rerank_results(self, query: str, candidates: list, top_k: int = 5):
        """Stage 2: Rerank candidates with cross-encoder for better precision."""
        try:
            pairs = [(query, c['code']) for c in candidates]
            scores = self.reranker.predict(pairs)
            
            for i, c in enumerate(candidates):
                c['rerank_score'] = float(scores[i])
            
            candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
            logger.debug(f"[CocoIndex] Reranked {len(candidates)} candidates")
            return candidates
        except Exception as e:
            logger.warning(f"[CocoIndex] Reranking failed, using vector scores: {e}")
            return candidates

    def search_task(self, project_id: str, task_id: str, query: str, top_k: int = 5):
        """Search in a specific task workspace using two-stage retrieval."""
        # Stage 1: Vector search
        candidates = self._vector_search_task(task_id, query, top_k=20)
        
        if not candidates:
            return []
        
        # Stage 2: Rerank
        if len(candidates) > top_k:
            candidates = self._rerank_results(query, candidates, top_k)
        
        return candidates[:top_k]
    
    def _vector_search_task(self, task_id: str, query: str, top_k: int = 30):
        """Stage 1: Fast vector similarity search for task."""
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id not in self.task_flows:
            raise ValueError(f"Task {task_identifier} not registered. Call register_task first.")

        flow = self.task_flows[sanitized_task_id]
        table_name = cocoindex.utils.get_target_default_name(flow, "code_embedding")
        query_vector = embed_query_fast(query)  # ONNX-optimized

        with connection_pool().connection() as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                sql_query = f'SELECT filename, code, embedding <=> %s AS distance, start, "end" FROM "{table_name}" ORDER BY distance LIMIT %s'
                cur.execute(sql_query, (query_vector, top_k))
                return [
                    {
                        "filename": row[0],
                        "code": row[1],
                        "score": 1.0 - row[2],
                        "start": row[3],
                        "end": row[4],
                    }
                    for row in cur.fetchall()
                ]

    def incremental_update_task(self, project_id: str, task_id: str):
        """Perform incremental update on task index (sync, fast).
        
        This only reprocesses changed files since last update.
        Call this after writing files to keep index up-to-date.
        
        Returns:
            Update stats or None if task not registered
        """
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id not in self.task_flows:
            return None  # Skip if not registered

        try:
            result = self.task_flows[sanitized_task_id].update()
            print(f"[CocoIndex] Incremental update {task_id}: {result}")
            return result
        except Exception as e:
            print(f"[CocoIndex] Incremental update failed for {task_identifier}: {e}")
            return None

    def incremental_update_project(self, project_id: str):
        """Perform incremental update on project index (sync, fast).
        
        This only reprocesses changed files since last update.
        
        Returns:
            Update stats or None if project not registered
        """
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id not in self.flows:
            return None  # Skip if not registered

        try:
            result = self.flows[sanitized_project_id].update()
            print(f"[CocoIndex] Incremental update {project_id}: {result}")
            return result
        except Exception as e:
            print(f"[CocoIndex] Incremental update failed for {project_id}: {e}")
            return None

    async def update_task(self, project_id: str, task_id: str):
        """Re-index a specific task workspace (async version)."""
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id not in self.task_flows:
            raise ValueError(f"Task {task_identifier} not registered")

        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.task_flows[sanitized_task_id].update()
        )

        print(f"[CocoIndex] Updated task {task_identifier}: {result}")
        return result

    async def update_project(self, project_id: str):
        """Re-index a specific project (async version)."""
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id not in self.flows:
            raise ValueError(f"Project {project_id} not registered")

        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.flows[sanitized_project_id].update()
        )

        print(f"[CocoIndex] Updated project {project_id}: {result}")
        return result

    def unregister_task(self, project_id: str, task_id: str):
        """Remove a task from memory (does not delete database table)."""
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)
        
        if sanitized_task_id in self.task_flows:
            del self.task_flows[sanitized_task_id]
            print(f"Unregistered task {task_identifier} from memory.")
        else:
            print(f"Task {task_identifier} was not registered.")

    def delete_project(self, project_id: str):
        """Remove a project and its index table."""
        # Sanitize the project_id to match the stored flow name
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id not in self.flows:
            print(
                f"Project {project_id} not in memory, cannot determine table name for deletion."
            )
            return

        flow = self.flows[sanitized_project_id]
        # Use the sanitized project_id for flow name
        sanitized_flow_name = f"code_embeddings_{sanitized_project_id}"
        table_name = cocoindex.utils.get_target_default_name(
            flow, sanitized_flow_name
        )

        with connection_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        del self.flows[sanitized_project_id]
        print(f"Deleted project {project_id} and its index table '{table_name}'.")


# Create a singleton instance of the manager to be used across the application
project_manager = AdvancedProjectManager()
