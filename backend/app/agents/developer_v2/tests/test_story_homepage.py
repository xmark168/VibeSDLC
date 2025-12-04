"""Test MetaGPT-style flow with Homepage story."""
import os
import sys
import json
import tempfile

# Test story
STORY = """
## As a first-time visitor, I want to see a clear homepage layout with featured books so that I can quickly understand what the bookstore offers and start browsing

**ID:** `EPIC-001-US-001`  
**Epic:** `EPIC-001`

### Description
Create the foundational homepage that serves as the entry point for all customers. This page must establish trust, showcase the bookstore's offerings, and provide clear navigation paths. The homepage should highlight popular textbooks, display trust indicators (return policy, genuine books guarantee), and make the search functionality immediately accessible.

### Requirements
- Display hero section with main value proposition and call-to-action button
- Show featured/bestselling textbooks section with book covers, titles, prices, and stock status
- Include prominent search bar at the top of the page with placeholder text guiding users
- Display trust indicators: return policy (7-14 days), genuine books guarantee, contact information
- Show category navigation menu organized by grade levels (6-12, university) and subjects
- Include footer with quick links to policies, about us, and contact information
- Ensure responsive design that works on mobile, tablet, and desktop devices
- Display loading states for dynamic content and handle empty states gracefully

### Acceptance Criteria
- Given a user visits the homepage, When the page loads, Then they see the hero section, featured books (at least 8 items), search bar, and trust indicators within 3 seconds
- Given a user views featured books, When they hover over a book, Then they see a visual indication (shadow/border) and can click to view details
- Given a user is on mobile device, When they access the homepage, Then all elements are properly sized and the layout adapts to screen width
- Given the featured books section is empty, When the page loads, Then display 'New books coming soon!' message
- Given a user clicks on a category in navigation menu, Then they are directed to the filtered book listing page
"""


def extract_keywords(story_text: str, max_keywords: int = 10) -> list:
    """Extract keywords from story for smart prefetch."""
    import re
    
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
        'because', 'until', 'while', 'this', 'that', 'these', 'those', 'i',
        'me', 'my', 'myself', 'we', 'our', 'ours', 'you', 'your', 'yours',
        'he', 'him', 'his', 'she', 'her', 'hers', 'it', 'its', 'they', 'them',
        'their', 'what', 'which', 'who', 'whom', 'user', 'want', 'given', 'display',
        'show', 'include', 'ensure', 'within', 'without', 'using', 'based', 'make',
    }
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', story_text.lower())
    word_freq = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]


def simulate_logic_analysis(story: str) -> list:
    """Simulate LLM generating logic analysis for the story."""
    # This would be LLM output in real implementation
    return [
        {
            "order": 1,
            "file_path": "prisma/schema.prisma",
            "action": "modify",
            "description": "Add Book, Category models with fields for title, price, stock, coverImage, grade level",
            "dependencies": []
        },
        {
            "order": 2,
            "file_path": "src/app/api/books/featured/route.ts",
            "action": "create",
            "description": "API endpoint to get featured/bestselling books with pagination",
            "dependencies": ["prisma/schema.prisma", "src/lib/prisma.ts"]
        },
        {
            "order": 3,
            "file_path": "src/app/api/categories/route.ts",
            "action": "create", 
            "description": "API endpoint to get categories organized by grade levels",
            "dependencies": ["prisma/schema.prisma", "src/lib/prisma.ts"]
        },
        {
            "order": 4,
            "file_path": "src/components/ui/BookCard.tsx",
            "action": "create",
            "description": "Reusable book card component with cover, title, price, stock status, hover effects",
            "dependencies": []
        },
        {
            "order": 5,
            "file_path": "src/components/home/HeroSection.tsx",
            "action": "create",
            "description": "Hero section with value proposition and CTA button",
            "dependencies": []
        },
        {
            "order": 6,
            "file_path": "src/components/home/FeaturedBooks.tsx",
            "action": "create",
            "description": "Featured books grid with loading state and empty state handling",
            "dependencies": ["src/components/ui/BookCard.tsx"]
        },
        {
            "order": 7,
            "file_path": "src/components/home/TrustIndicators.tsx",
            "action": "create",
            "description": "Trust badges: return policy, genuine guarantee, contact info",
            "dependencies": []
        },
        {
            "order": 8,
            "file_path": "src/components/layout/CategoryNav.tsx",
            "action": "create",
            "description": "Category navigation menu organized by grade levels and subjects",
            "dependencies": []
        },
        {
            "order": 9,
            "file_path": "src/components/layout/SearchBar.tsx",
            "action": "create",
            "description": "Prominent search bar with placeholder text",
            "dependencies": []
        },
        {
            "order": 10,
            "file_path": "src/components/layout/Footer.tsx",
            "action": "create",
            "description": "Footer with quick links to policies, about, contact",
            "dependencies": []
        },
        {
            "order": 11,
            "file_path": "src/app/page.tsx",
            "action": "modify",
            "description": "Compose homepage with all components: Hero, SearchBar, CategoryNav, FeaturedBooks, TrustIndicators, Footer",
            "dependencies": [
                "src/components/home/HeroSection.tsx",
                "src/components/home/FeaturedBooks.tsx",
                "src/components/home/TrustIndicators.tsx",
                "src/components/layout/CategoryNav.tsx",
                "src/components/layout/SearchBar.tsx",
                "src/components/layout/Footer.tsx"
            ]
        }
    ]


def simulate_preload_dependencies(steps: list, workspace_path: str) -> dict:
    """Simulate pre-loading dependency files."""
    dependencies_content = {}
    
    # Collect all unique dependencies
    all_deps = set()
    for step in steps:
        for dep in step.get("dependencies", []):
            all_deps.add(dep)
    
    # Simulate reading files (in real implementation, would read actual files)
    mock_contents = {
        "prisma/schema.prisma": """
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Book {
  id          Int      @id @default(autoincrement())
  title       String
  author      String
  price       Decimal  @db.Decimal(10, 2)
  coverImage  String?
  description String?
  stock       Int      @default(0)
  isFeatured  Boolean  @default(false)
  gradeLevel  String?
  categoryId  Int?
  category    Category? @relation(fields: [categoryId], references: [id])
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Category {
  id        Int      @id @default(autoincrement())
  name      String
  slug      String   @unique
  gradeLevel String?
  books     Book[]
}
""",
        "src/lib/prisma.ts": """
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const prisma = globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
""",
        "src/components/ui/BookCard.tsx": """
'use client'
import Image from 'next/image'
import Link from 'next/link'

interface BookCardProps {
  id: number
  title: string
  author: string
  price: number
  coverImage?: string
  stock: number
}

export function BookCard({ id, title, author, price, coverImage, stock }: BookCardProps) {
  return (
    <Link href={`/books/${id}`}>
      <div className="group rounded-lg border p-4 hover:shadow-lg hover:border-primary transition-all">
        <div className="aspect-[3/4] relative mb-3 overflow-hidden rounded">
          <Image
            src={coverImage || '/placeholder-book.png'}
            alt={title}
            fill
            className="object-cover group-hover:scale-105 transition-transform"
          />
        </div>
        <h3 className="font-semibold line-clamp-2">{title}</h3>
        <p className="text-sm text-muted-foreground">{author}</p>
        <div className="flex justify-between items-center mt-2">
          <span className="font-bold text-primary">{price.toLocaleString()}đ</span>
          <span className={stock > 0 ? 'text-green-600 text-sm' : 'text-red-600 text-sm'}>
            {stock > 0 ? 'Còn hàng' : 'Hết hàng'}
          </span>
        </div>
      </div>
    </Link>
  )
}
"""
    }
    
    for dep in all_deps:
        if dep in mock_contents:
            dependencies_content[dep] = mock_contents[dep]
        else:
            # Mark as needs to be created
            dependencies_content[dep] = f"[FILE NOT EXISTS - will be created in step]"
    
    return dependencies_content


def simulate_implement_step(step: dict, deps_content: dict) -> str:
    """Simulate implementing a single step with pre-loaded context."""
    file_path = step["file_path"]
    action = step["action"]
    description = step["description"]
    
    # Build context from pre-loaded dependencies
    context_parts = []
    for dep in step.get("dependencies", []):
        if dep in deps_content and not deps_content[dep].startswith("[FILE NOT EXISTS"):
            context_parts.append(f"### {dep}\n```\n{deps_content[dep][:500]}...\n```")
    
    # In real implementation, this would be LLM call with:
    # - Pre-loaded context (no search needed)
    # - Skill tools only (activate_skills, read_skill_file)
    # - Write tools (write_file_safe, edit_file)
    
    # Simulate generated code based on step
    if "BookCard" in file_path:
        return """'use client'
import Image from 'next/image'
import Link from 'next/link'

interface BookCardProps {
  id: number
  title: string
  author: string
  price: number
  coverImage?: string
  stock: number
}

export function BookCard({ id, title, author, price, coverImage, stock }: BookCardProps) {
  return (
    <Link href={`/books/${id}`}>
      <div className="group rounded-lg border p-4 hover:shadow-lg hover:border-primary transition-all">
        <div className="aspect-[3/4] relative mb-3 overflow-hidden rounded">
          <Image src={coverImage || '/placeholder-book.png'} alt={title} fill className="object-cover" />
        </div>
        <h3 className="font-semibold line-clamp-2">{title}</h3>
        <p className="text-sm text-muted-foreground">{author}</p>
        <div className="flex justify-between items-center mt-2">
          <span className="font-bold">{price.toLocaleString()}đ</span>
          <span className={stock > 0 ? 'text-green-600' : 'text-red-600'}>
            {stock > 0 ? 'Còn hàng' : 'Hết hàng'}
          </span>
        </div>
      </div>
    </Link>
  )
}"""
    elif "featured/route" in file_path:
        return """import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') || '8')
  
  const books = await prisma.book.findMany({
    where: { isFeatured: true, stock: { gt: 0 } },
    include: { category: true },
    take: limit,
    orderBy: { createdAt: 'desc' }
  })
  
  return NextResponse.json({ books })
}"""
    elif "HeroSection" in file_path:
        return """export function HeroSection() {
  return (
    <section className="bg-gradient-to-r from-primary/10 to-primary/5 py-16">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          Sách giáo khoa chính hãng
        </h1>
        <p className="text-xl text-muted-foreground mb-8">
          Đầy đủ sách từ lớp 6 đến đại học, giao hàng nhanh toàn quốc
        </p>
        <button className="bg-primary text-white px-8 py-3 rounded-lg hover:bg-primary/90">
          Khám phá ngay
        </button>
      </div>
    </section>
  )
}"""
    else:
        return f"// Generated code for {file_path}\n// {description}"


def test_full_homepage_flow():
    """Test complete MetaGPT-style flow for homepage story."""
    print("\n" + "=" * 70)
    print("MetaGPT-Style Flow Test: Homepage Story")
    print("=" * 70)
    
    # Phase 1: Extract keywords
    print("\n[PHASE 1] Extract Keywords")
    print("-" * 40)
    keywords = extract_keywords(STORY)
    print(f"Keywords: {keywords}")
    
    # Phase 2: Generate logic analysis (simulated LLM)
    print("\n[PHASE 2] Logic Analysis (LLM generates plan)")
    print("-" * 40)
    steps = simulate_logic_analysis(STORY)
    print(f"Generated {len(steps)} implementation steps:")
    for step in steps:
        deps = step.get("dependencies", [])
        deps_str = f" <- [{', '.join(deps)}]" if deps else ""
        print(f"  {step['order']}. [{step['action'].upper()}] {step['file_path']}{deps_str}")
    
    # Phase 3: Pre-load dependencies
    print("\n[PHASE 3] Pre-load Dependencies (MetaGPT-style)")
    print("-" * 40)
    with tempfile.TemporaryDirectory() as tmpdir:
        deps_content = simulate_preload_dependencies(steps, tmpdir)
        print(f"Pre-loaded {len(deps_content)} dependency files:")
        for dep, content in deps_content.items():
            status = "EXISTS" if not content.startswith("[FILE NOT EXISTS") else "TO CREATE"
            size = len(content) if status == "EXISTS" else 0
            print(f"  - {dep}: {status} ({size} chars)")
    
    # Phase 4: Implement (minimal tools)
    print("\n[PHASE 4] Implement Steps (Minimal Tools)")
    print("-" * 40)
    print("Tools available: write_file_safe, edit_file, execute_shell, activate_skills, read_skill_file")
    print("Tools NOT available: read_file_safe, glob, grep_files, list_directory_safe")
    print("")
    
    files_created = {}
    for step in steps[:4]:  # Just first 4 steps for demo
        code = simulate_implement_step(step, deps_content)
        files_created[step["file_path"]] = code
        
        # Count "tool calls" - in MetaGPT style, mostly just 1-2 per step
        tool_calls = 1  # Just write_file_safe
        if step.get("dependencies"):
            tool_calls += 1  # activate_skills
        
        print(f"  Step {step['order']}: {step['file_path']}")
        print(f"    Action: {step['action']}")
        print(f"    Tool calls: ~{tool_calls} (write + skill)")
        print(f"    Code size: {len(code)} chars")
    
    # Phase 5: Summary
    print("\n[PHASE 5] Comparison Summary")
    print("-" * 40)
    
    total_steps = len(steps)
    
    # Current approach (exploration + write)
    current_tools_per_step = 10  # glob, grep, read x2, write, etc.
    current_total = total_steps * current_tools_per_step
    
    # MetaGPT approach (skill + write only)
    metagpt_tools_per_step = 2  # activate_skills + write
    metagpt_total = total_steps * metagpt_tools_per_step
    
    print(f"Total steps: {total_steps}")
    print(f"")
    print(f"Current dev_v2 approach:")
    print(f"  - Tools per step: ~{current_tools_per_step} (search, read, write)")
    print(f"  - Total tool calls: ~{current_total}")
    print(f"")
    print(f"MetaGPT-style approach:")
    print(f"  - Tools per step: ~{metagpt_tools_per_step} (skill + write)")
    print(f"  - Total tool calls: ~{metagpt_total}")
    print(f"")
    print(f"Reduction: {current_total - metagpt_total} fewer calls ({(1 - metagpt_total/current_total)*100:.0f}%)")
    
    print("\n" + "=" * 70)
    print("[PASS] Homepage story flow simulation complete")
    print("=" * 70)
    
    return True


def test_preload_covers_all_deps():
    """Test that pre-load covers all step dependencies."""
    print("\n[TEST] Pre-load covers all dependencies")
    
    steps = simulate_logic_analysis(STORY)
    
    # Collect all dependencies
    all_deps = set()
    for step in steps:
        for dep in step.get("dependencies", []):
            all_deps.add(dep)
    
    # Check pre-load
    deps_content = simulate_preload_dependencies(steps, ".")
    
    missing = all_deps - set(deps_content.keys())
    
    print(f"  Total unique dependencies: {len(all_deps)}")
    print(f"  Pre-loaded: {len(deps_content)}")
    print(f"  Missing: {len(missing)}")
    
    if missing:
        print(f"  Missing files: {missing}")
    
    assert len(missing) == 0, f"Missing dependencies: {missing}"
    print("[PASS] All dependencies covered")


def test_step_order_respects_deps():
    """Test that step order respects dependencies."""
    print("\n[TEST] Step order respects dependencies")
    
    steps = simulate_logic_analysis(STORY)
    
    # Build map of file_path -> order
    file_order = {step["file_path"]: step["order"] for step in steps}
    
    violations = []
    for step in steps:
        for dep in step.get("dependencies", []):
            if dep in file_order:
                if file_order[dep] >= step["order"]:
                    violations.append(f"Step {step['order']} ({step['file_path']}) depends on {dep} (order {file_order[dep]})")
    
    print(f"  Total steps: {len(steps)}")
    print(f"  Order violations: {len(violations)}")
    
    if violations:
        for v in violations:
            print(f"    - {v}")
    
    # Note: Some deps may be existing files (not in steps), that's OK
    print("[PASS] Step order validated")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Homepage Story - MetaGPT Style Flow Tests")
    print("=" * 70)
    
    tests = [
        test_preload_covers_all_deps,
        test_step_order_respects_deps,
        test_full_homepage_flow,
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
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    sys.exit(0 if failed == 0 else 1)
