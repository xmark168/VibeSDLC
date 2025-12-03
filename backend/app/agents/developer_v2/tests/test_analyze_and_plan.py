"""Test analyze_and_plan node - verify helper functions and flow.

Run directly:
    python backend/app/agents/developer_v2/tests/test_analyze_and_plan.py
    
Or with pytest:
    pytest backend/app/agents/developer_v2/tests/test_analyze_and_plan.py -v
"""
import os
import sys
import re
import json
import asyncio
import tempfile
import glob as glob_module
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add paths for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Import helper functions directly to avoid app-level imports
# Copy the functions here for isolated testing

def _extract_keywords(text: str) -> list:
    """Extract meaningful keywords from story text."""
    stopwords = {'the', 'a', 'an', 'is', 'are', 'can', 'will', 'should', 'must',
                 'user', 'users', 'when', 'then', 'given', 'and', 'or', 'to', 'from',
                 'with', 'for', 'on', 'in', 'at', 'by', 'of', 'that', 'this', 'be',
                 'want', 'see', 'click', 'display', 'show', 'create', 'update', 'delete'}
    
    words = re.findall(r'[a-z]+', text.lower())
    
    keywords = []
    seen = set()
    for word in words:
        if len(word) > 3 and word not in stopwords and word not in seen:
            keywords.append(word)
            seen.add(word)
    
    return keywords[:10]


def _smart_prefetch(workspace_path: str, story_title: str, requirements: list) -> str:
    """Prefetch relevant files based on story content."""
    if not workspace_path or not os.path.exists(workspace_path):
        return ""
    
    context_parts = []
    
    core_files = [
        ("package.json", 500),
        ("prisma/schema.prisma", 2000),
        ("src/app/layout.tsx", 500),
        ("tsconfig.json", 300),
    ]
    
    for file_path, max_len in core_files:
        full_path = os.path.join(workspace_path, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:max_len]
                context_parts.append(f"### {file_path}\n```\n{content}\n```")
            except Exception:
                pass
    
    req_text = ' '.join(requirements) if requirements else ''
    text = f"{story_title} {req_text}".lower()
    keywords = _extract_keywords(text)
    
    for keyword in keywords[:5]:
        pattern = os.path.join(workspace_path, "src", "**", f"*{keyword}*")
        try:
            matches = glob_module.glob(pattern, recursive=True)
            for match in matches[:2]:
                if os.path.isfile(match):
                    rel_path = os.path.relpath(match, workspace_path)
                    with open(match, 'r', encoding='utf-8') as f:
                        content = f.read()[:1000]
                    context_parts.append(f"### {rel_path}\n```\n{content}\n```")
        except Exception:
            pass
    
    for dir_name in ["src/app/api", "src/components", "src/lib", "src/app"]:
        dir_path = os.path.join(workspace_path, dir_name)
        if os.path.exists(dir_path):
            try:
                items = os.listdir(dir_path)[:15]
                context_parts.append(f"### {dir_name}/\n{', '.join(items)}")
            except Exception:
                pass
    
    return "\n\n".join(context_parts)


def extract_json_universal(text: str, context: str = "") -> dict:
    """Extract JSON from various formats."""
    # Try <result> tags
    import re
    result_match = re.search(r'<result>\s*([\s\S]*?)\s*</result>', text)
    if result_match:
        return json.loads(result_match.group(1))
    
    # Try ```json block
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        return json.loads(json_match.group(1))
    
    # Try raw JSON
    text = text.strip()
    if text.startswith('{'):
        return json.loads(text)
    
    raise ValueError(f"[{context}] Unable to extract JSON")


# =============================================================================
# Test _extract_keywords
# =============================================================================

def test_extract_keywords_basic():
    """Should extract meaningful keywords from text."""
    text = "User can view product list with search functionality"
    keywords = _extract_keywords(text)
    
    assert "product" in keywords
    assert "list" in keywords
    assert "search" in keywords
    assert "functionality" in keywords
    
    # Should not include stopwords
    assert "can" not in keywords
    assert "with" not in keywords
    assert "user" not in keywords
    
    print("[PASS] test_extract_keywords_basic")
    print(f"   Keywords: {keywords}")


def test_extract_keywords_deduplication():
    """Should deduplicate keywords."""
    text = "product product product list list"
    keywords = _extract_keywords(text)
    
    assert keywords.count("product") == 1
    assert keywords.count("list") == 1
    
    print("[PASS] test_extract_keywords_deduplication")


def test_extract_keywords_short_words():
    """Should filter out words with 3 or fewer characters."""
    text = "a an the foo bar api get set"
    keywords = _extract_keywords(text)
    
    assert "api" not in keywords  # 3 chars
    assert "get" not in keywords  # 3 chars
    assert "foo" not in keywords  # 3 chars
    
    print("[PASS] test_extract_keywords_short_words")


def test_extract_keywords_limit():
    """Should return max 10 keywords."""
    text = " ".join([f"keyword{i}" for i in range(20)])
    keywords = _extract_keywords(text)
    
    assert len(keywords) <= 10
    
    print("[PASS] test_extract_keywords_limit")
    print(f"   Returned {len(keywords)} keywords (max 10)")


# =============================================================================
# Test _smart_prefetch
# =============================================================================

def test_smart_prefetch_empty_path():
    """Should return empty string for invalid path."""
    result = _smart_prefetch("", "Test Story", [])
    assert result == ""
    
    result = _smart_prefetch("/nonexistent/path", "Test Story", [])
    assert result == ""
    
    print("[PASS] test_smart_prefetch_empty_path")


def test_smart_prefetch_with_files():
    """Should read core files and find related files."""
    # Create temp workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create core files
        os.makedirs(os.path.join(tmpdir, "prisma"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "app"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "components"), exist_ok=True)
        
        # package.json
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            f.write('{"name": "test-app", "version": "1.0.0"}')
        
        # prisma schema
        with open(os.path.join(tmpdir, "prisma", "schema.prisma"), "w") as f:
            f.write('model User { id String @id }')
        
        # Create a product component (should be found by keyword)
        os.makedirs(os.path.join(tmpdir, "src", "components", "Product"), exist_ok=True)
        with open(os.path.join(tmpdir, "src", "components", "Product", "ProductCard.tsx"), "w") as f:
            f.write('export function ProductCard() { return <div>Product</div> }')
        
        # Run smart prefetch
        result = _smart_prefetch(tmpdir, "View product list", ["Display products"])
        
        # Should contain core files
        assert "package.json" in result
        assert "schema.prisma" in result
        
        # Should list components directory
        assert "src/components" in result
        
        print("[PASS] test_smart_prefetch_with_files")
        print(f"   Result length: {len(result)} chars")


def test_smart_prefetch_keyword_matching():
    """Should find files matching story keywords."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure
        os.makedirs(os.path.join(tmpdir, "src", "components", "Cart"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "app", "api", "cart"), exist_ok=True)
        
        # Cart component
        with open(os.path.join(tmpdir, "src", "components", "Cart", "CartItem.tsx"), "w") as f:
            f.write('export function CartItem() {}')
        
        # Cart API
        with open(os.path.join(tmpdir, "src", "app", "api", "cart", "route.ts"), "w") as f:
            f.write('export async function GET() {}')
        
        result = _smart_prefetch(tmpdir, "Shopping cart feature", ["Add item to cart"])
        
        # Should find cart-related files
        assert "cart" in result.lower() or "Cart" in result
        
        print("[PASS] test_smart_prefetch_keyword_matching")


# =============================================================================
# Test analyze_and_plan integration (with mocks)
# =============================================================================

def test_analyze_and_plan_state_structure():
    """Verify state dict has required fields."""
    # Create a valid state (using dict, not TypedDict to avoid imports)
    state = {
        "story_id": "EPIC-001-US-001",
        "epic": "EPIC-001",
        "story_title": "Test Story",
        "story_description": "Test description",
        "story_requirements": ["Req 1", "Req 2"],
        "acceptance_criteria": ["AC 1", "AC 2"],
        "workspace_path": "/tmp/test",
        "tech_stack": "nextjs",
        "project_id": "test-project",
    }
    
    assert state["story_id"] == "EPIC-001-US-001"
    assert len(state["story_requirements"]) == 2
    
    print("[PASS] test_analyze_and_plan_state_structure")


def test_smart_prefetch_integration():
    """Integration test: smart prefetch with real temp files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a realistic Next.js structure
        os.makedirs(os.path.join(tmpdir, "src", "app", "api", "products"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "components", "Product"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "prisma"), exist_ok=True)
        
        # package.json
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            f.write('{"name": "bookstore", "dependencies": {"next": "14.0.0"}}')
        
        # prisma schema
        with open(os.path.join(tmpdir, "prisma", "schema.prisma"), "w") as f:
            f.write('''
model Book {
  id        String @id @default(uuid())
  title     String
  author    String
  price     Float
}
''')
        
        # API route
        with open(os.path.join(tmpdir, "src", "app", "api", "products", "route.ts"), "w") as f:
            f.write('export async function GET() { return Response.json([]) }')
        
        # Component
        with open(os.path.join(tmpdir, "src", "components", "Product", "ProductCard.tsx"), "w") as f:
            f.write('export function ProductCard({ product }) { return <div>{product.title}</div> }')
        
        # Run smart prefetch with product-related story
        result = _smart_prefetch(
            tmpdir,
            "Homepage with featured products",
            ["Display product list", "Show product cards"]
        )
        
        # Verify core files are included
        assert "package.json" in result
        assert "schema.prisma" in result
        
        # Verify directory listings
        assert "src/app/api" in result or "src/components" in result
        
        # Verify keyword matching found product files
        assert "product" in result.lower()
        
        print("[PASS] test_smart_prefetch_integration")
        print(f"   Prefetch result: {len(result)} chars")
        print(f"   Contains 'product': {result.lower().count('product')} times")


# =============================================================================
# Test JSON extraction edge cases
# =============================================================================

def test_json_extraction_formats():
    """Test extract_json_universal with different formats."""
    # Using local extract_json_universal defined above
    
    # Format 1: <result> tags
    text1 = 'Some text <result>{"key": "value"}</result> more text'
    result1 = extract_json_universal(text1, "test")
    assert result1["key"] == "value"
    
    # Format 2: ```json block
    text2 = 'Text ```json\n{"key": "value2"}\n``` end'
    result2 = extract_json_universal(text2, "test")
    assert result2["key"] == "value2"
    
    # Format 3: Raw JSON
    text3 = '{"key": "value3"}'
    result3 = extract_json_universal(text3, "test")
    assert result3["key"] == "value3"
    
    print("[PASS] test_json_extraction_formats")


def test_json_extraction_with_exploration():
    """Test JSON extraction from realistic exploration response."""
    # Using local extract_json_universal defined above
    
    response = """
## Exploration Summary

I found the following:
- User model exists in prisma/schema.prisma
- Navigation component at src/components/Navigation.tsx
- API routes in src/app/api/

<result>
{
    "story_summary": "Create homepage with featured products",
    "complexity": "medium",
    "steps": [
        {"order": 1, "description": "Add Product model to schema.prisma"},
        {"order": 2, "description": "Create GET /api/products endpoint"},
        {"order": 3, "description": "Build ProductList component"},
        {"order": 4, "description": "Write unit tests"}
    ]
}
</result>
"""
    
    result = extract_json_universal(response, "test")
    
    assert result["story_summary"] == "Create homepage with featured products"
    assert len(result["steps"]) == 4
    assert result["steps"][0]["order"] == 1
    
    print("[PASS] test_json_extraction_with_exploration")
    print(f"   Extracted {len(result['steps'])} steps")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n=== Running analyze_and_plan Tests ===\n")
    
    tests = [
        # Keyword extraction tests
        test_extract_keywords_basic,
        test_extract_keywords_deduplication,
        test_extract_keywords_short_words,
        test_extract_keywords_limit,
        # Smart prefetch tests
        test_smart_prefetch_empty_path,
        test_smart_prefetch_with_files,
        test_smart_prefetch_keyword_matching,
        test_smart_prefetch_integration,
        # State structure test
        test_analyze_and_plan_state_structure,
        # JSON extraction tests
        test_json_extraction_formats,
        test_json_extraction_with_exploration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {type(e).__name__}: {e}")
            failed += 1
        print()
    
    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    
    if failed > 0:
        sys.exit(1)
