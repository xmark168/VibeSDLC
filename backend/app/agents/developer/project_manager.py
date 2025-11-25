import os

import cocoindex
from cocoindex import FlowBuilder
from cocoindex.functions import DetectProgrammingLanguage, SplitRecursively
from pgvector.psycopg import register_vector

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
        self.flows = {}

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

    def search(self, project_id: str, query: str, top_k: int = 5):
        """Search in a specific project using the correct table name."""
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

    async def update_project(self, project_id: str):
        """Re-index a specific project."""
        # Sanitize the project_id to match the stored flow name
        sanitized_project_id = "".join(c if c.isalnum() else "_" for c in project_id)

        if sanitized_project_id not in self.flows:
            raise ValueError(f"Project {project_id} not registered")

        import concurrent.futures
        import asyncio

        # Run the synchronous update in a separate thread to avoid blocking the event loop
        def run_update():
            return self.flows[sanitized_project_id].update()

        # Use run_in_executor to run the blocking operation in a thread pool
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, run_update)
        result = await future  # Use await instead of asyncio.run

        print(f"Updated {project_id}: {result}")
        return result

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
