"""
Test Tavily SDK Integration

Test script để kiểm tra Tavily Python SDK integration với workflow search + crawl.
"""

import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_tavily_client():
    """Test tạo Tavily client."""
    print("🔧 Testing Tavily Client Creation")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import create_tavily_client
        
        # Test với API key từ environment
        client = create_tavily_client()
        
        if client is not None:
            print("✅ Tavily client created successfully")
            print(f"   Client type: {type(client)}")
            return True
        else:
            print("❌ Tavily client creation failed")
            print("   Possible reasons:")
            print("   - tavily-python package not installed")
            print("   - TAVILY_API_KEY not set in environment")
            return False
            
    except Exception as e:
        print(f"❌ Tavily client test failed: {e}")
        return False


def test_search_only():
    """Test search functionality only (without crawl)."""
    print("\n🔍 Testing Search Only")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import tavily_search_tool
        
        # Test query
        query = "FastAPI authentication best practices"
        
        print(f"Query: {query}")
        print("Performing search (no crawl)...")
        
        # Call với include_raw_content=False để skip crawl
        result_json = tavily_search_tool(
            query=query,
            max_results=3,
            include_raw_content=False
        )
        
        result = json.loads(result_json)
        
        print(f"Status: {result.get('status')}")
        print(f"Total results: {result.get('total_results', 0)}")
        print(f"Search time: {result.get('search_time', 0):.2f}s")
        print(f"Has crawl content: {result.get('has_crawl_content', False)}")
        
        if result.get('results'):
            print("\nTop result:")
            top_result = result['results'][0]
            print(f"  Title: {top_result.get('title', 'N/A')}")
            print(f"  URL: {top_result.get('url', 'N/A')}")
            print(f"  Score: {top_result.get('score', 0):.2f}")
            content = top_result.get('content', '')
            if content:
                preview = content[:150] + "..." if len(content) > 150 else content
                print(f"  Content: {preview}")
        
        return result.get('status') == 'success'
        
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


def test_search_with_crawl():
    """Test search + crawl functionality."""
    print("\n🕷️ Testing Search + Crawl")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import tavily_search_tool
        
        # Test query
        query = "Python FastAPI tutorial"
        
        print(f"Query: {query}")
        print("Performing search + crawl...")
        
        # Call với include_raw_content=True để enable crawl
        result_json = tavily_search_tool(
            query=query,
            max_results=2,
            include_raw_content=True
        )
        
        result = json.loads(result_json)
        
        print(f"Status: {result.get('status')}")
        print(f"Total results: {result.get('total_results', 0)}")
        print(f"Search time: {result.get('search_time', 0):.2f}s")
        print(f"Crawl time: {result.get('crawl_time', 0):.2f}s")
        print(f"Has crawl content: {result.get('has_crawl_content', False)}")
        
        if result.get('crawl_result'):
            crawl_result = result['crawl_result']
            print(f"\nCrawl result:")
            print(f"  URL: {crawl_result.get('url', 'N/A')}")
            raw_content = crawl_result.get('raw_content', '')
            if raw_content:
                preview = raw_content[:200] + "..." if len(raw_content) > 200 else raw_content
                print(f"  Raw content preview: {preview}")
                print(f"  Raw content length: {len(raw_content)} chars")
        
        # Check if first result has raw_content
        if result.get('results') and result['results'][0].get('raw_content'):
            print(f"\n✅ First search result enhanced with raw content")
            raw_content_length = len(result['results'][0]['raw_content'])
            print(f"   Enhanced content length: {raw_content_length} chars")
        
        return result.get('status') == 'success'
        
    except Exception as e:
        print(f"❌ Search + crawl test failed: {e}")
        return False


def test_enhanced_summary():
    """Test enhanced summary generation."""
    print("\n📄 Testing Enhanced Summary")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import tavily_search_tool
        
        # Test query
        query = "Docker deployment best practices"
        
        print(f"Query: {query}")
        print("Testing enhanced summary generation...")
        
        result_json = tavily_search_tool(
            query=query,
            max_results=2,
            include_raw_content=True
        )
        
        result = json.loads(result_json)
        
        summary = result.get('summary', '')
        if summary:
            print(f"Summary generated: {len(summary)} chars")
            print("\nSummary preview:")
            print("-" * 20)
            preview = summary[:500] + "..." if len(summary) > 500 else summary
            print(preview)
            print("-" * 20)
            
            # Check for key sections
            has_search_results = "Search Results for" in summary
            has_detailed_content = "Detailed Content (from crawl)" in summary
            has_key_insights = "Key Insights" in summary
            
            print(f"\nSummary sections:")
            print(f"  ✅ Search Results: {has_search_results}")
            print(f"  ✅ Detailed Content: {has_detailed_content}")
            print(f"  ✅ Key Insights: {has_key_insights}")
            
            return has_search_results and has_key_insights
        else:
            print("❌ No summary generated")
            return False
        
    except Exception as e:
        print(f"❌ Enhanced summary test failed: {e}")
        return False


def test_error_handling():
    """Test error handling scenarios."""
    print("\n⚠️ Testing Error Handling")
    print("-" * 40)
    
    try:
        from app.agents.developer.planner.tools.tavily_search import tavily_search_tool
        
        # Test với query rỗng
        print("Testing empty query...")
        result_json = tavily_search_tool(query="")
        result = json.loads(result_json)
        
        print(f"Empty query status: {result.get('status')}")
        
        # Test với query rất dài
        print("Testing very long query...")
        long_query = "a" * 1000
        result_json = tavily_search_tool(query=long_query, max_results=1)
        result = json.loads(result_json)
        
        print(f"Long query status: {result.get('status')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def main():
    """Chạy tất cả tests."""
    print("🧪 Tavily SDK Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Tavily Client Creation", test_tavily_client),
        ("Search Only", test_search_only),
        ("Search + Crawl", test_search_with_crawl),
        ("Enhanced Summary", test_enhanced_summary),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Test: {test_name}")
        print("=" * 50)
        
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Tavily SDK integration is working correctly.")
        print("\n📋 Summary:")
        print("✅ Tavily Python SDK integration")
        print("✅ Search functionality")
        print("✅ Crawl functionality")
        print("✅ Enhanced summary generation")
        print("✅ Error handling")
        print("\n🚀 Ready for production use!")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        print("\n📋 Possible issues:")
        print("- tavily-python package not installed")
        print("- TAVILY_API_KEY not set or invalid")
        print("- Network connectivity issues")
        print("- API rate limits")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
