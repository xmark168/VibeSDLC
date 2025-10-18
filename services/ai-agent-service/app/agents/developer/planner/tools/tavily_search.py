"""
Tavily Search Tool

Wrapper cho Tavily Search API để tìm kiếm web khi cần thông tin bổ sung
cho việc tạo implementation plan.
"""

import json
import os
from typing import Any

from langchain_tavily import TavilySearch
from pydantic import BaseModel


def create_tavily_search_tool(max_results: int = 5, topic: str = "general"):
    """
    Tạo Tavily Search Tool theo hướng dẫn LangChain.

    Args:
        max_results: Số lượng kết quả tối đa (default: 5)
        topic: Chủ đề tìm kiếm (default: "general")

    Returns:
        TavilySearch tool instance hoặc None nếu không available
    """
    try:
        return TavilySearch(
            max_results=max_results,
            topic=topic,
        )
    except Exception:
        return None


class SearchResult(BaseModel):
    """Model cho kết quả tìm kiếm từ Tavily."""

    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 0.0
    published_date: str | None = None


class WebSearchResults(BaseModel):
    """Model cho tổng hợp kết quả web search."""

    query: str = ""
    results: list[SearchResult] = []
    total_results: int = 0
    search_time: float = 0.0
    summary: str = ""


def tavily_search_tool(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_images: bool = False,
) -> str:
    """
    Tìm kiếm web sử dụng Tavily Search API.

    Args:
        query: Search query string
        max_results: Số lượng kết quả tối đa (default: 5)
        search_depth: Độ sâu tìm kiếm - "basic" hoặc "advanced" (default: "basic")
        include_answer: Có bao gồm AI-generated answer không (default: True)
        include_raw_content: Có bao gồm raw content không (default: False)
        include_images: Có bao gồm images không (default: False)

    Returns:
        JSON string với kết quả tìm kiếm
    """
    try:
        print(f"🔍 Searching web for: {query}")

        # Kiểm tra API key
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return json.dumps(
                {
                    "status": "error",
                    "message": "TAVILY_API_KEY not found in environment variables",
                    "query": query,
                    "results": [],
                },
                indent=2,
            )

        # Khởi tạo Tavily search tool theo hướng dẫn LangChain
        search_tool = create_tavily_search_tool(max_results=max_results)

        if search_tool is None:
            return json.dumps(
                {
                    "status": "error",
                    "message": "TavilySearch not available. Please install langchain-tavily package.",
                    "query": query,
                    "results": [],
                },
                indent=2,
            )

        # Thực hiện tìm kiếm
        import time

        start_time = time.time()

        raw_results = search_tool.invoke({"query": query})

        search_time = time.time() - start_time

        print(
            f"📊 Found {len(raw_results) if isinstance(raw_results, list) else 0} results in {search_time:.2f}s"
        )

        # Parse và format kết quả
        search_results = []

        if isinstance(raw_results, list):
            for result in raw_results:
                if isinstance(result, dict):
                    search_result = SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        content=result.get("content", ""),
                        score=result.get("score", 0.0),
                        published_date=result.get("published_date"),
                    )
                    search_results.append(search_result)

        # Tạo summary từ kết quả
        summary = _generate_search_summary(query, search_results)

        # Tạo WebSearchResults object
        web_results = WebSearchResults(
            query=query,
            results=search_results,
            total_results=len(search_results),
            search_time=search_time,
            summary=summary,
        )

        # Return JSON
        result_dict = {
            "status": "success",
            "query": query,
            "total_results": len(search_results),
            "search_time": search_time,
            "summary": summary,
            "results": [result.model_dump() for result in search_results],
        }

        print("✅ Web search completed successfully")
        return json.dumps(result_dict, indent=2)

    except Exception as e:
        print(f"❌ Web search failed: {e}")
        return json.dumps(
            {
                "status": "error",
                "message": f"Search failed: {str(e)}",
                "query": query,
                "results": [],
            },
            indent=2,
        )


def _generate_search_summary(query: str, results: list[SearchResult]) -> str:
    """
    Tạo summary từ kết quả tìm kiếm.

    Args:
        query: Original search query
        results: List of search results

    Returns:
        Summary string
    """
    if not results:
        return f"No relevant results found for query: {query}"

    # Lấy top 3 results để tạo summary
    top_results = results[:3]

    summary_parts = [f"Found {len(results)} results for '{query}':"]

    for i, result in enumerate(top_results, 1):
        content_preview = (
            result.content[:200] + "..."
            if len(result.content) > 200
            else result.content
        )
        summary_parts.append(f"{i}. {result.title}: {content_preview}")

    return "\n".join(summary_parts)


def should_perform_websearch(
    task_description: str, task_requirements: dict[str, Any], codebase_context: str = ""
) -> tuple[bool, str]:
    """
    Quyết định có cần thực hiện web search hay không dựa trên task analysis.

    Args:
        task_description: Mô tả task gốc
        task_requirements: Parsed task requirements
        codebase_context: Context về codebase hiện tại

    Returns:
        Tuple of (should_search: bool, reason: str)
    """
    # Các keywords cho thấy cần tìm kiếm thêm thông tin
    search_indicators = [
        "best practices",
        "how to implement",
        "integration with",
        "latest version",
        "documentation",
        "tutorial",
        "example",
        "guide",
        "API reference",
        "configuration",
        "setup",
        "install",
        "deploy",
        "security",
        "performance",
        "optimization",
        "third-party",
        "external service",
        "library",
        "framework",
        "tool",
        "service",
        "platform",
    ]

    # Kiểm tra task description
    task_lower = task_description.lower()
    found_indicators = [
        indicator for indicator in search_indicators if indicator in task_lower
    ]

    # Kiểm tra requirements
    requirements = task_requirements.get("requirements", [])
    technical_specs = task_requirements.get("technical_specs", {})

    # Nếu có ít thông tin technical specs
    has_limited_tech_info = len(technical_specs) < 2

    # Nếu có nhiều requirements phức tạp
    has_complex_requirements = len(requirements) > 5

    # Quyết định
    if found_indicators:
        return True, f"Found search indicators: {', '.join(found_indicators[:3])}"
    elif has_limited_tech_info and has_complex_requirements:
        return True, "Limited technical specifications for complex requirements"
    elif not codebase_context.strip():
        return True, "No codebase context provided, need external information"
    else:
        return False, "Sufficient information available for implementation planning"


def generate_search_queries(
    task_description: str, task_requirements: dict[str, Any]
) -> list[str]:
    """
    Tạo danh sách search queries dựa trên task analysis.

    Args:
        task_description: Mô tả task gốc
        task_requirements: Parsed task requirements

    Returns:
        List of search query strings
    """
    queries = []

    # Base query từ task description
    base_query = task_description[:100]  # Limit length
    queries.append(f"{base_query} implementation guide")

    # Queries từ technical specs
    technical_specs = task_requirements.get("technical_specs", {})
    for tech, spec in technical_specs.items():
        if isinstance(spec, str) and spec:
            queries.append(f"{tech} {spec} best practices")

    # Queries từ requirements
    requirements = task_requirements.get("requirements", [])
    for req in requirements[:2]:  # Limit to top 2 requirements
        if len(req) > 10:  # Only meaningful requirements
            queries.append(f"{req} implementation example")

    # Limit total queries
    return queries[:3]
