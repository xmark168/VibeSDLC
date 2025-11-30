import asyncio
import os

import cocoindex
from cocoindex import FlowBuilder
from cocoindex.functions import DetectProgrammingLanguage, SplitRecursively
from pgvector.psycopg import register_vector

from pathlib import Path
from app.agents.developer.flows import code_to_embedding, connection_pool


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

    # Create and write the project structure file before defining the flow
    structure_file_path = os.path.join(project_path, "PROJECT_STRUCTURE.md")
    if os.path.exists(project_path):
        structure_content = create_structure_document(project_path)
        with open(structure_file_path, "w", encoding="utf-8") as f:
            f.write(structure_content)

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
                    "PROJECT_STRUCTURE.md",
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
                    "pnpm-lock.yaml",
                    "package-lock.json",
                ],
            )
        )

        code_embeddings = data_scope.add_collector()

        with data_scope["files"].row() as file:
            file["language"] = file["filename"].transform(DetectProgrammingLanguage())
            file["chunks"] = file["content"].transform(
                SplitRecursively(),
                language=file["language"],
                chunk_size=1500,
                min_chunk_size=500,
                chunk_overlap=400,
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
    def __init__(self):
        self.flows = {}  # For project-level indexing
        self.task_flows = {}  # For task-level indexing

    def _is_in_event_loop(self) -> bool:
        """Check if we're inside an async event loop."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    def register_project(self, project_id: str, project_path: str):
        """Register and index a new project.
        
        Auto-detects async context and uses appropriate method.
        If in event loop, returns coroutine that caller must await.
        """
        if self._is_in_event_loop():
            # Return coroutine - caller must await to avoid deadlock
            # DO NOT use run_coroutine_threadsafe + future.result() - causes deadlock
            return self.register_project_async(project_id, project_path)
        
        return self._register_project_sync(project_id, project_path)

    def _register_project_sync(self, project_id: str, project_path: str):
        """Sync implementation of register_project."""
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

    async def register_project_async(self, project_id: str, project_path: str):
        """Register and index a new project (async version - no warnings)."""
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id in self.flows:
            return

        flow = create_project_flow(project_id, project_path)
        self.flows[sanitized_project_id] = flow

        print(f"Attempting to index project '{project_id}' (sanitized as '{sanitized_project_id}')...")
        try:
            stats = await flow.update_async()
            print(f"✅ Indexing completed for '{project_id}': {stats}")
        except Exception as e:
            if "not up-to-date" in str(e):
                print(
                    f"🔄 Database setup required for flow '{project_id}'. Running setup..."
                )
                await flow.setup_async()
                print("✅ Setup complete. Retrying indexing...")
                stats = await flow.update_async()
                print(f"✅ Indexing completed for '{project_id}' after setup: {stats}")
            else:
                print(f"❌ An unexpected error during indexing for '{project_id}':")
                raise e

    def register_task(self, project_id: str, task_id: str, task_path: str):
        """Register and index a specific task workspace.
        
        Auto-detects async context and uses appropriate method.
        If in event loop, returns coroutine that caller must await.
        """
        if self._is_in_event_loop():
            # Return coroutine - caller must await to avoid deadlock
            # DO NOT use run_coroutine_threadsafe + future.result() - causes deadlock
            return self.register_task_async(project_id, task_id, task_path)
        
        return self._register_task_sync(project_id, task_id, task_path)

    def _register_task_sync(self, project_id: str, task_id: str, task_path: str):
        """Sync implementation of register_task."""
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id in self.task_flows:
            return

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

    async def register_task_async(self, project_id: str, task_id: str, task_path: str):
        """Register and index a task workspace (async version - no warnings)."""
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id in self.task_flows:
            return

        flow = create_project_flow(task_identifier, task_path)
        self.task_flows[sanitized_task_id] = flow

        print(f"Attempting to index task '{task_identifier}' (sanitized as '{sanitized_task_id}')...")
        try:
            stats = await flow.update_async()
            print(f"✅ Indexing completed for task '{task_identifier}': {stats}")
        except Exception as e:
            if "not up-to-date" in str(e):
                print(
                    f"🔄 Database setup required for task '{task_identifier}'. Running setup..."
                )
                await flow.setup_async()
                print("✅ Setup complete. Retrying indexing...")
                stats = await flow.update_async()
                print(f"✅ Indexing completed for task '{task_identifier}' after setup: {stats}")
            else:
                print(f"❌ An unexpected error during indexing for task '{task_identifier}':")
                raise e

    def search(self, project_id: str, query: str, top_k: int = 5, search_type: str = "project"):
        """Search in a specific project or task using the correct table name."""
        if search_type == "task":
            # For task search, we need both project_id and task_id in the identifier
            # This method will be called differently for tasks
            raise ValueError("Use search_task for task-specific searches")
        else:
            # Sanitize the project_id to match the stored flow name
            sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

            if sanitized_project_id not in self.flows:
                project_path = (
                    f"services/ai-agent-service/app/agents/dev/workspaces/{project_id}"
                )
                if os.path.exists(project_path):
                    self.register_project(project_id, project_path)
                else:
                    raise ValueError(
                        f"Project {project_id} not registered and path not found."
                    )

            flow = self.flows[sanitized_project_id]
            # Use the official utility to get the correct, mangled table name
            table_name = cocoindex.utils.get_target_default_name(flow, "code_embedding")

            query_vector = code_to_embedding.eval(query)

            with connection_pool().connection() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    # Use quotes around the table name to handle special characters
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

    def search_task(self, project_id: str, task_id: str, query: str, top_k: int = 5):
        """Search in a specific task workspace using the correct table name."""
        task_identifier = task_id
        sanitized_task_id = "".join(c if c.isalnum() else "_" for c in task_identifier)

        if sanitized_task_id not in self.task_flows:
            raise ValueError(
                f"Task {task_identifier} not registered. Call register_task first."
            )

        flow = self.task_flows[sanitized_task_id]
        # Use the official utility to get the correct, mangled table name
        table_name = cocoindex.utils.get_target_default_name(flow, "code_embedding")

        query_vector = code_to_embedding.eval(query)

        with connection_pool().connection() as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                # Use quotes around the table name to handle special characters
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
