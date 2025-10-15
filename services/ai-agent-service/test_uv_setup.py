#!/usr/bin/env python3
"""
Test script for uv setup with LangChain PGVector
"""


def test_imports():
    """Test all critical imports"""
    print("🧪 Testing imports...")

    try:
        # Test LangChain imports
        from langchain_postgres import PGVector
        from langchain_openai import OpenAIEmbeddings
        from langchain_core.documents import Document

        print("✅ LangChain imports successful")

        # Test psycopg
        import psycopg

        print("✅ psycopg import successful")

        # Test pgvector
        import pgvector

        print("✅ pgvector import successful")

        # Test deepagents
        import deepagents

        try:
            version = deepagents.__version__
        except AttributeError:
            version = "unknown"
        print(f"✅ deepagents {version} import successful")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_langchain_pgvector_client():
    """Test our custom LangChain PGVector client"""
    print("\n🧪 Testing LangChain PGVector client...")

    try:
        from app.agents.developer.implementor.langchain_pgvector_client import (
            LangChainPgVectorClient,
        )

        print("✅ LangChain PGVector client import successful")

        # Test mock mode
        client = LangChainPgVectorClient()
        print(f"✅ Client initialized in mock mode: {client.mock_mode}")

        # Test indexing
        success = client.index_code_snippet(
            file_path="hi.py",
            snippet_type="function",
            content='def hello(): return "Hello World"',
            language="python",
        )
        print(f"✅ Indexing test: {success}")

        # Test search
        results = client.search_similar_code("hello function")
        print(f"✅ Search test: found {len(results)} results")

        if results:
            print(f"   First result: {results[0]['content'][:50]}...")
            print(f"   Similarity: {results[0]['similarity']:.3f}")

        # Test stats
        stats = client.get_index_stats()
        print(f"✅ Stats test: {stats}")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_tools():
    """Test tools integration"""
    print("\n🧪 Testing tools integration...")

    try:
        from app.agents.developer.implementor.tools.codebase_tools import search_similar_code_tool

        print("✅ Tools import successful")

        # Test search tool (this will use mock mode)
        result = search_similar_code_tool.invoke(
            {"query": "authentication function", "limit": 3, "language": "python"}
        )
        print("✅ Search tool test successful")
        print(f"   Result: {result[:100]}...")

        return True

    except ImportError as e:
        print(f"❌ Tools import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Tools test error: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 UV Setup Test for LangChain PGVector")
    print("=" * 60)

    # Test 1: Basic imports
    imports_ok = test_imports()

    # Test 2: LangChain PGVector client
    client_ok = test_langchain_pgvector_client()

    # Test 3: Tools integration
    tools_ok = test_tools()

    # Summary
    print("\n" + "=" * 60)
    if imports_ok and client_ok and tools_ok:
        print("🎉 All tests passed! UV setup successful!")
        print("\n✅ Ready for:")
        print("1. Mock mode development")
        print("2. PostgreSQL setup with: uv run python setup_langchain_pgvector.py")
        print("3. Real database testing")
    elif imports_ok:
        print("✅ Basic setup successful!")
        print("⚠️ Some advanced features need debugging")
        print("\n🔧 Next steps:")
        print("1. Check file paths and imports")
        print("2. Test with PostgreSQL container")
    else:
        print("❌ Setup has issues")
        print("\n🔧 Troubleshooting:")
        print("1. Check dependency versions")
        print("2. Verify uv environment")
        print("3. Check import paths")


if __name__ == "__main__":
    main()
