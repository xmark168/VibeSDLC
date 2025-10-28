"""
Tavily Search Tool

Wrapper cho Tavily Search API để tìm kiếm web khi cần thông tin bổ sung
cho việc tạo implementation plan.
"""

import json
import os
import time
from typing import Any

from langchain_core.tools import tool

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

from pydantic import BaseModel


def create_tavily_client(api_key: str | None = None) -> TavilyClient | None:
    """
    Tạo Tavily Client để sử dụng Python SDK.

    Args:
        api_key: Tavily API key (optional, sẽ lấy từ env nếu không có)

    Returns:
        TavilyClient instance hoặc None nếu không available
    """
    if TavilyClient is None:
        return None

    try:
        if api_key is None:
            api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            return None

        return TavilyClient(api_key=api_key)
    except Exception:
        return None


class SearchResult(BaseModel):
    """Model cho kết quả tìm kiếm từ Tavily."""

    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 0.0
    published_date: str | None = None
    raw_content: str | None = None  # Thêm raw_content từ crawl


class CrawlResult(BaseModel):
    """Model cho kết quả crawl từ Tavily."""

    url: str = ""
    raw_content: str = ""
    favicon: str | None = None


class WebSearchResults(BaseModel):
    """Model cho tổng hợp kết quả web search."""

    query: str = ""
    results: list[SearchResult] = []
    crawl_result: CrawlResult | None = None  # Thêm crawl result
    total_results: int = 0
    search_time: float = 0.0
    crawl_time: float = 0.0  # Thêm crawl time
    summary: str = ""


@tool
def tavily_search_tool(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
    include_raw_content: bool = True,
    include_images: bool = False,
) -> str:
    """
    Tìm kiếm web sử dụng Tavily Python SDK với workflow search + crawl.

    Workflow:
    1. Search để lấy top URLs với summary content
    2. Crawl URL đầu tiên (highest score) để lấy raw_content chi tiết
    3. Kết hợp cả summary và raw_content để có thông tin đầy đủ

    Args:
        query: Search query string
        max_results: Số lượng kết quả tối đa (default: 5)
        search_depth: Độ sâu tìm kiếm - "basic" hoặc "advanced" (default: "basic")
        include_answer: Có bao gồm AI-generated answer không (default: True)
        include_raw_content: Có crawl để lấy raw content hay không (default: True)
        include_images: Có bao gồm images không (default: False)

    Returns:
        JSON string với kết quả tìm kiếm và crawl
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

        # Tạo Tavily client
        client = create_tavily_client()
        if client is None:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Tavily client not available. Please install tavily-python package and set TAVILY_API_KEY.",
                    "query": query,
                    "results": [],
                },
                indent=2,
            )

        # Bước 1: Search để lấy URLs và summary content
        start_time = time.time()

        search_response = client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=include_answer,
            include_images=include_images,
            include_raw_content=False,  # Không lấy raw_content trong search
        )

        search_time = time.time() - start_time

        print(
            f"📊 Found {len(search_response.get('results', []))} results in {search_time:.2f}s"
        )

        # Parse search results
        search_results = []
        crawl_result = None
        crawl_time = 0.0

        if search_response.get("results"):
            for result in search_response["results"]:
                search_result = SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    score=result.get("score", 0.0),
                    published_date=result.get("published_date"),
                )
                search_results.append(search_result)

            # Bước 2: Crawl URL đầu tiên (highest score) để lấy raw_content
            if include_raw_content and search_results:
                try:
                    top_result = search_results[0]  # URL có score cao nhất
                    print(f"🕷️ Crawling top result: {top_result.url}")

                    crawl_start_time = time.time()
                    crawl_response = client.crawl(
                        url=top_result.url,
                        instructions=f"Extract detailed information about: {query}",
                        max_depth=2,
                        max_breadth=10,
                        extract_depth="advanced",
                    )
                    crawl_time = time.time() - crawl_start_time

                    print(f"🕷️ Crawl completed in {crawl_time:.2f}s")

                    if crawl_response.get("results"):
                        crawl_data = crawl_response["results"][0]
                        crawl_result = CrawlResult(
                            url=crawl_data.get("url", top_result.url),
                            raw_content=crawl_data.get("raw_content", ""),
                            favicon=crawl_data.get("favicon"),
                        )

                        # Cập nhật search result đầu tiên với raw_content
                        search_results[0].raw_content = crawl_result.raw_content

                except Exception as crawl_error:
                    print(f"⚠️ Crawl failed: {crawl_error}")
                    # Tiếp tục với search results, không fail toàn bộ

        # Tạo summary từ search results và crawl content
        summary = _generate_enhanced_search_summary(query, search_results, crawl_result)

        # Tạo response dict
        result_dict = {
            "status": "success",
            "query": query,
            "total_results": len(search_results),
            "search_time": search_time,
            "crawl_time": crawl_time,
            "has_crawl_content": crawl_result is not None,
            "summary": summary,
            "results": [result.model_dump() for result in search_results],
            "crawl_result": crawl_result.model_dump() if crawl_result else None,
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


def _generate_enhanced_search_summary(
    query: str, results: list[SearchResult], crawl_result: CrawlResult | None = None
) -> str:
    """
    Tạo enhanced summary từ kết quả search và crawl.

    Args:
        query: Original search query
        results: List of search results
        crawl_result: Crawl result với raw content (optional)

    Returns:
        Enhanced summary string
    """
    if not results:
        return f"No search results found for query: '{query}'"

    summary_parts = []

    # Phần 1: Tổng quan từ search results
    summary_parts.append(f"Search Results for '{query}':")
    summary_parts.append(f"Found {len(results)} relevant sources:")

    for i, result in enumerate(results[:3], 1):  # Top 3 results
        summary_parts.append(f"{i}. {result.title}")
        if result.content:
            content_preview = (
                result.content[:200] + "..."
                if len(result.content) > 200
                else result.content
            )
            summary_parts.append(f"   Summary: {content_preview}")
        summary_parts.append(f"   Source: {result.url}")
        if result.score > 0:
            summary_parts.append(f"   Relevance: {result.score:.2f}")
        summary_parts.append("")

    # Phần 2: Detailed content từ crawl (nếu có)
    if crawl_result and crawl_result.raw_content:
        summary_parts.append("--- Detailed Content (from crawl) ---")
        raw_content = crawl_result.raw_content

        # Truncate raw content nếu quá dài
        if len(raw_content) > 2000:
            raw_content = raw_content[:2000] + "\n... (content truncated)"

        summary_parts.append(raw_content)
        summary_parts.append("")
        summary_parts.append(f"Full content source: {crawl_result.url}")

    # Phần 3: Key insights
    summary_parts.append("--- Key Insights ---")
    if crawl_result and crawl_result.raw_content:
        summary_parts.append(
            "✅ Detailed implementation information available from crawled content"
        )
    else:
        summary_parts.append("ℹ️ Summary information available from search results")

    summary_parts.append(f"📊 Total sources analyzed: {len(results)}")

    return "\n".join(summary_parts)


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
