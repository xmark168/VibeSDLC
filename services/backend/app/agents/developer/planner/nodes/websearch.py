"""
WebSearch Node

Node thực hiện web search khi cần thông tin bổ sung để tạo implementation plan.
Sử dụng Tavily Search API để tìm kiếm thông tin liên quan.
"""

import json
import time
from typing import Any, Dict

from langchain_core.messages import AIMessage

from ..state import PlannerState, WebSearchResults
from ..tools.tavily_search import (
    generate_search_queries,
    should_perform_websearch,
    tavily_search_tool,
)


def websearch(state: PlannerState) -> PlannerState:
    """
    WebSearch node - Thực hiện web search khi cần thông tin bổ sung.

    Logic:
    1. Đánh giá xem có cần web search hay không
    2. Nếu cần: tạo search queries và thực hiện search
    3. Nếu không cần: bỏ qua và ghi lý do
    4. Lưu kết quả vào state.websearch_results
    5. Cập nhật codebase_context với thông tin tìm được

    Args:
        state: PlannerState với task_requirements

    Returns:
        Updated PlannerState với websearch_results
    """
    print("\n" + "=" * 80)
    print("PLAN: WEBSEARCH NODE - Web Search for Additional Information")
    print("=" * 80)

    try:
        # Lấy thông tin từ state
        task_description = state.task_description
        task_requirements = state.task_requirements.model_dump()
        codebase_context = state.codebase_context

        print(f"🔍 Evaluating need for web search...")
        print(f"📝 Task: {task_description[:100]}...")

        # Quyết định có cần web search hay không
        should_search, reason = should_perform_websearch(
            task_description=task_description,
            task_requirements=task_requirements,
            codebase_context=codebase_context
        )

        print(f"🤔 Search decision: {should_search}")
        print(f"📋 Reason: {reason}")

        # Khởi tạo WebSearchResults
        websearch_results = WebSearchResults()

        if should_search:
            print("🌐 Performing web search...")
            
            # Tạo search queries
            queries = generate_search_queries(task_description, task_requirements)
            print(f"🔎 Generated {len(queries)} search queries:")
            for i, query in enumerate(queries, 1):
                print(f"  {i}. {query}")

            # Thực hiện search cho từng query
            all_results = []
            total_search_time = 0.0

            for query in queries:
                print(f"\n🔍 Searching: {query}")
                
                # Gọi Tavily search
                search_result_json = tavily_search_tool(
                    query=query,
                    max_results=3,  # Giới hạn kết quả cho mỗi query
                    search_depth="basic",
                    include_answer=True
                )

                try:
                    search_data = json.loads(search_result_json)
                    if search_data.get("status") == "success":
                        results = search_data.get("results", [])
                        all_results.extend(results)
                        total_search_time += search_data.get("search_time", 0.0)
                        print(f"  ✅ Found {len(results)} results")
                    else:
                        print(f"  ❌ Search failed: {search_data.get('message', 'Unknown error')}")
                except json.JSONDecodeError:
                    print(f"  ❌ Invalid JSON response from search")

                # Delay giữa các queries để tránh rate limiting
                time.sleep(0.5)

            # Tạo summary từ tất cả kết quả
            summary = _create_search_summary(all_results, task_description)

            # Cập nhật WebSearchResults
            websearch_results = WebSearchResults(
                performed=True,
                queries=queries,
                results=all_results,
                summary=summary,
                search_time=total_search_time,
                reason_for_search=reason,
                reason_for_skip=""
            )

            # Cập nhật codebase_context với thông tin từ search
            if summary:
                enhanced_context = f"{codebase_context}\n\n--- Web Search Results ---\n{summary}"
                state.codebase_context = enhanced_context

            print(f"✅ Web search completed:")
            print(f"  📊 Total results: {len(all_results)}")
            print(f"  ⏱️  Total time: {total_search_time:.2f}s")
            print(f"  📄 Summary length: {len(summary)} chars")

        else:
            print("⏭️  Skipping web search")
            websearch_results = WebSearchResults(
                performed=False,
                reason_for_skip=reason
            )

        # Cập nhật state
        state.websearch_results = websearch_results
        state.current_phase = "analyze_codebase"
        state.status = "websearch_completed"

        # Lưu vào tools_output
        state.tools_output["websearch"] = websearch_results.model_dump()

        # Tạo AI message
        if websearch_results.performed:
            message_content = f"""WebSearch Phase - COMPLETED

Search Results:
- Queries executed: {len(websearch_results.queries)}
- Total results found: {len(websearch_results.results)}
- Search time: {websearch_results.search_time:.2f}s
- Reason: {websearch_results.reason_for_search}

Summary:
{websearch_results.summary[:500]}...

Enhanced context has been added to codebase analysis.
Ready to proceed to Phase 2: Codebase Analysis."""
        else:
            message_content = f"""WebSearch Phase - SKIPPED

Reason: {websearch_results.reason_for_skip}

Proceeding directly to Phase 2: Codebase Analysis with existing information."""

        ai_message = AIMessage(content=message_content)
        state.messages.append(ai_message)

        print("SUCCESS: WebSearch phase completed")
        print(f"INFO: Search performed: {websearch_results.performed}")
        print(f"PLAN: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in websearch: {e}")
        state.status = "error_websearch"
        state.error_message = f"WebSearch failed: {str(e)}"
        
        # Vẫn cho phép tiếp tục workflow
        state.current_phase = "analyze_codebase"
        
        # Tạo error WebSearchResults
        state.websearch_results = WebSearchResults(
            performed=False,
            reason_for_skip=f"Error occurred: {str(e)}"
        )
        
        return state


def _create_search_summary(results: list[Dict[str, Any]], task_description: str) -> str:
    """
    Tạo summary từ kết quả web search.
    
    Args:
        results: List of search results
        task_description: Original task description
    
    Returns:
        Summary string
    """
    if not results:
        return f"No relevant web search results found for: {task_description}"

    summary_parts = [
        f"Web Search Summary for: {task_description}",
        f"Found {len(results)} relevant results:",
        ""
    ]

    # Lấy top 5 results để tạo summary
    top_results = results[:5]
    
    for i, result in enumerate(top_results, 1):
        title = result.get("title", "No title")
        content = result.get("content", "No content")
        url = result.get("url", "")
        
        # Truncate content
        content_preview = content[:300] + "..." if len(content) > 300 else content
        
        summary_parts.append(f"{i}. {title}")
        summary_parts.append(f"   {content_preview}")
        if url:
            summary_parts.append(f"   Source: {url}")
        summary_parts.append("")

    # Thêm key insights
    summary_parts.append("Key Insights:")
    
    # Extract key technical terms và concepts
    all_content = " ".join([r.get("content", "") for r in top_results])
    key_terms = _extract_key_terms(all_content, task_description)
    
    for term in key_terms[:5]:  # Top 5 key terms
        summary_parts.append(f"- {term}")

    return "\n".join(summary_parts)


def _extract_key_terms(content: str, task_description: str) -> list[str]:
    """
    Extract key technical terms từ search content.
    
    Args:
        content: Combined search content
        task_description: Original task description
    
    Returns:
        List of key terms
    """
    # Simple keyword extraction - có thể cải thiện với NLP
    technical_keywords = [
        "API", "REST", "GraphQL", "database", "authentication", "authorization",
        "security", "performance", "scalability", "microservices", "Docker",
        "Kubernetes", "CI/CD", "testing", "deployment", "monitoring",
        "logging", "caching", "queue", "message", "event", "stream",
        "framework", "library", "service", "component", "module",
        "configuration", "environment", "production", "development"
    ]
    
    content_lower = content.lower()
    task_lower = task_description.lower()
    
    found_terms = []
    
    for keyword in technical_keywords:
        if keyword.lower() in content_lower and keyword.lower() in task_lower:
            found_terms.append(f"{keyword} implementation patterns")
    
    # Thêm một số generic insights
    if "best practices" in content_lower:
        found_terms.append("Industry best practices identified")
    
    if "example" in content_lower or "tutorial" in content_lower:
        found_terms.append("Implementation examples available")
    
    if "security" in content_lower:
        found_terms.append("Security considerations documented")
    
    return found_terms[:5]  # Limit to 5 terms
