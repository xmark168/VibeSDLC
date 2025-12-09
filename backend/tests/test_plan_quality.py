"""Test Plan Quality with 10 diverse user stories.

Evaluates zero-shot planning quality across different story types.

Usage:
    python backend/tests/test_plan_quality.py
    python backend/tests/test_plan_quality.py --story 1  # Test single story
"""
import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Add backend path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

logging.basicConfig(level=logging.WARNING)
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

# 100 Diverse User Stories
STORIES = [
    {
        "id": 1,
        "name": "Homepage Featured",
        "story": "As a first-time visitor, I want to see featured products, bestsellers, and categories on the homepage so I can discover products quickly",
        "needs_db": True,
        "complexity": "medium",
        "expected_steps": (8, 20),
    },
    {
        "id": 2,
        "name": "Search & Filters",
        "story": "As a user, I want to search for products by name and filter by category, price range, and rating so I can find exactly what I need",
        "needs_db": True,
        "complexity": "medium",
        "expected_steps": (5, 16),
    },
    {
        "id": 3,
        "name": "User Authentication",
        "story": "As a visitor, I want to register and login with email/password using the existing User model so I can access my account",
        "needs_db": False,
        "complexity": "medium",
        "expected_steps": (3, 14),
    },
    {
        "id": 4,
        "name": "Shopping Cart",
        "story": "As a shopper, I want to add products to cart, update quantities, and see cart total so I can manage my purchases before checkout",
        "needs_db": True,
        "complexity": "high",
        "expected_steps": (6, 22),
    },
    {
        "id": 5,
        "name": "Product Detail",
        "story": "As a shopper, I want to view product details with images, description, specs, and customer reviews so I can make informed decisions",
        "needs_db": True,
        "complexity": "medium",
        "expected_steps": (5, 16),
    },
    {
        "id": 6,
        "name": "User Profile",
        "story": "As a logged-in user, I want to view and edit my profile, change password, and manage notification preferences",
        "needs_db": True,
        "complexity": "medium",
        "expected_steps": (5, 18),
    },
    {
        "id": 7,
        "name": "Checkout Flow",
        "story": "As a shopper, I want to enter shipping address, select payment method, and complete purchase so I can buy products",
        "needs_db": True,
        "complexity": "high",
        "expected_steps": (5, 22),
    },
    {
        "id": 8,
        "name": "Admin Dashboard",
        "story": "As an admin, I want to see sales stats, recent orders, and low stock alerts on a dashboard so I can monitor business health",
        "needs_db": True,
        "complexity": "high",
        "expected_steps": (5, 24),
    },
    {
        "id": 9,
        "name": "Blog Articles",
        "story": "As a visitor, I want to browse blog articles by category and read full articles with comments so I can learn about products",
        "needs_db": True,
        "complexity": "low",
        "expected_steps": (5, 18),
    },
    {
        "id": 10,
        "name": "Contact Form",
        "story": "As a visitor, I want to submit a contact form with name, email, and message so I can reach customer support",
        "needs_db": True,
        "complexity": "low",
        "expected_steps": (4, 10),
    },
    # E-commerce stories (11-20)
    {"id": 11, "name": "Wishlist", "story": "As a user, I want to add products to wishlist and view my saved items", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 12, "name": "Order History", "story": "As a customer, I want to view my past orders with status and tracking info", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 13, "name": "Product Reviews", "story": "As a buyer, I want to write and read product reviews with ratings", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 14, "name": "Coupon System", "story": "As a shopper, I want to apply discount coupons at checkout", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 15, "name": "Product Compare", "story": "As a shopper, I want to compare multiple products side by side", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 16, "name": "Recently Viewed", "story": "As a user, I want to see my recently viewed products", "needs_db": False, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 17, "name": "Stock Alerts", "story": "As a shopper, I want to get notified when out-of-stock items are available", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 18, "name": "Gift Cards", "story": "As a user, I want to purchase and redeem gift cards", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 19, "name": "Product Bundles", "story": "As a shopper, I want to buy product bundles at discounted prices", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 20, "name": "Size Guide", "story": "As a shopper, I want to view size guides for clothing products", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    # Social features (21-30)
    {"id": 21, "name": "User Feed", "story": "As a user, I want to see a feed of posts from people I follow", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 22, "name": "Comments", "story": "As a user, I want to comment on posts and reply to other comments", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 23, "name": "Likes System", "story": "As a user, I want to like posts and see like counts", "needs_db": True, "complexity": "low", "expected_steps": (4, 12)},
    {"id": 24, "name": "Follow Users", "story": "As a user, I want to follow other users and see followers count", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 25, "name": "User Mentions", "story": "As a user, I want to mention other users in posts with @username", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 26, "name": "Notifications", "story": "As a user, I want to receive notifications for likes, comments, and follows", "needs_db": True, "complexity": "medium", "expected_steps": (5, 16)},
    {"id": 27, "name": "Direct Messages", "story": "As a user, I want to send private messages to other users", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 28, "name": "Share Posts", "story": "As a user, I want to share posts to my profile or external platforms", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 29, "name": "Hashtags", "story": "As a user, I want to add hashtags to posts and browse by hashtag", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 30, "name": "Story Feature", "story": "As a user, I want to post stories that disappear after 24 hours", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    # Content management (31-40)
    {"id": 31, "name": "Rich Text Editor", "story": "As an author, I want to write articles with rich text formatting", "needs_db": True, "complexity": "medium", "expected_steps": (4, 14)},
    {"id": 32, "name": "Image Gallery", "story": "As a user, I want to upload and view images in a gallery with lightbox", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 33, "name": "Video Player", "story": "As a user, I want to watch videos with play controls and fullscreen", "needs_db": False, "complexity": "medium", "expected_steps": (2, 12)},
    {"id": 34, "name": "File Downloads", "story": "As a user, I want to download files like PDFs and documents", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 35, "name": "Content Tags", "story": "As a reader, I want to filter content by tags and categories", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 36, "name": "Bookmarks", "story": "As a user, I want to bookmark articles to read later", "needs_db": True, "complexity": "low", "expected_steps": (4, 12)},
    {"id": 37, "name": "Reading Progress", "story": "As a reader, I want to see my reading progress on articles", "needs_db": True, "complexity": "medium", "expected_steps": (3, 12)},
    {"id": 38, "name": "Related Content", "story": "As a reader, I want to see related articles at the end of each post", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 39, "name": "Newsletter Signup", "story": "As a visitor, I want to subscribe to newsletter with email", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 40, "name": "RSS Feed", "story": "As a user, I want to access RSS feed of latest content", "needs_db": True, "complexity": "low", "expected_steps": (2, 8)},
    # Booking & scheduling (41-50)
    {"id": 41, "name": "Appointment Booking", "story": "As a client, I want to book appointments with available time slots", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 42, "name": "Calendar View", "story": "As a user, I want to view my bookings in a calendar format", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 43, "name": "Recurring Events", "story": "As a user, I want to create recurring events weekly or monthly", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 44, "name": "Event Reminders", "story": "As a user, I want to receive reminders before my appointments", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 45, "name": "Room Booking", "story": "As an employee, I want to book meeting rooms for specific times", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 46, "name": "Service Selection", "story": "As a client, I want to select services and see duration and price", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 47, "name": "Staff Availability", "story": "As a client, I want to see staff availability and choose provider", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 48, "name": "Booking Cancellation", "story": "As a client, I want to cancel or reschedule my bookings", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 49, "name": "Waitlist", "story": "As a client, I want to join waitlist when no slots available", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 50, "name": "Check-in System", "story": "As a receptionist, I want to check-in clients when they arrive", "needs_db": True, "complexity": "low", "expected_steps": (4, 12)},
    # Analytics & reporting (51-60)
    {"id": 51, "name": "Sales Reports", "story": "As a manager, I want to view sales reports with charts and filters", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 52, "name": "User Analytics", "story": "As an admin, I want to see user engagement metrics and trends", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 53, "name": "Export Data", "story": "As a user, I want to export reports as CSV or PDF", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 54, "name": "Custom Dashboards", "story": "As a user, I want to create custom dashboards with widgets", "needs_db": True, "complexity": "high", "expected_steps": (6, 20)},
    {"id": 55, "name": "Real-time Stats", "story": "As an admin, I want to see real-time visitor statistics", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 56, "name": "Conversion Funnel", "story": "As a marketer, I want to see conversion funnel analytics", "needs_db": True, "complexity": "high", "expected_steps": (5, 16)},
    {"id": 57, "name": "A/B Test Results", "story": "As a product manager, I want to view A/B test performance", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 58, "name": "Revenue Charts", "story": "As a business owner, I want to see revenue trends over time", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 59, "name": "Inventory Report", "story": "As a warehouse manager, I want to see inventory levels and alerts", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 60, "name": "Performance Metrics", "story": "As a team lead, I want to track team performance KPIs", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    # User management (61-70)
    {"id": 61, "name": "User Roles", "story": "As an admin, I want to assign roles and permissions to users", "needs_db": True, "complexity": "high", "expected_steps": (6, 16)},
    {"id": 62, "name": "Team Management", "story": "As a manager, I want to create teams and assign members", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 63, "name": "Invite Users", "story": "As an admin, I want to invite new users via email", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 64, "name": "User Directory", "story": "As an employee, I want to search and view colleague profiles", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 65, "name": "Activity Log", "story": "As an admin, I want to view user activity audit logs", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 66, "name": "Account Settings", "story": "As a user, I want to manage my account settings and preferences", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 67, "name": "Two-Factor Auth", "story": "As a user, I want to enable 2FA for extra security", "needs_db": True, "complexity": "high", "expected_steps": (5, 16)},
    {"id": 68, "name": "Password Reset", "story": "As a user, I want to reset my password via email link", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 69, "name": "Session Management", "story": "As a user, I want to view and revoke active sessions", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 70, "name": "Account Deletion", "story": "As a user, I want to delete my account and all data", "needs_db": False, "complexity": "low", "expected_steps": (2, 10)},
    # Communication (71-80)
    {"id": 71, "name": "Email Templates", "story": "As an admin, I want to create and manage email templates", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 72, "name": "Push Notifications", "story": "As a user, I want to receive push notifications on my device", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 73, "name": "In-app Chat", "story": "As a user, I want to chat with support in real-time", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 74, "name": "Announcement Banner", "story": "As an admin, I want to show announcement banners to users", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 75, "name": "Feedback Form", "story": "As a user, I want to submit feedback and suggestions", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 76, "name": "Help Center", "story": "As a user, I want to browse FAQ and help articles", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 77, "name": "Ticket System", "story": "As a user, I want to create support tickets and track status", "needs_db": True, "complexity": "high", "expected_steps": (6, 16)},
    {"id": 78, "name": "Chat History", "story": "As a user, I want to view my past chat conversations", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 79, "name": "Broadcast Messages", "story": "As an admin, I want to send messages to all users", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 80, "name": "Status Updates", "story": "As an admin, I want to post system status updates", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    # Location & maps (81-85)
    {"id": 81, "name": "Store Locator", "story": "As a customer, I want to find nearby stores on a map", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 82, "name": "Delivery Tracking", "story": "As a customer, I want to track my delivery on a map", "needs_db": True, "complexity": "high", "expected_steps": (6, 16)},
    {"id": 83, "name": "Address Autocomplete", "story": "As a user, I want address suggestions while typing", "needs_db": False, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 84, "name": "Geofencing", "story": "As a user, I want to get alerts when entering specific areas", "needs_db": True, "complexity": "high", "expected_steps": (5, 16)},
    {"id": 85, "name": "Route Planning", "story": "As a driver, I want to see optimized routes for deliveries", "needs_db": True, "complexity": "high", "expected_steps": (5, 16)},
    # Payments (86-90)
    {"id": 86, "name": "Payment Methods", "story": "As a user, I want to save and manage payment methods", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 87, "name": "Invoice Generation", "story": "As a seller, I want to generate invoices for orders", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 88, "name": "Refund Request", "story": "As a customer, I want to request refunds for orders", "needs_db": True, "complexity": "medium", "expected_steps": (5, 14)},
    {"id": 89, "name": "Subscription Plans", "story": "As a user, I want to subscribe to monthly or yearly plans", "needs_db": True, "complexity": "high", "expected_steps": (6, 18)},
    {"id": 90, "name": "Payment History", "story": "As a user, I want to view my payment transaction history", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    # Misc features (91-100)
    {"id": 91, "name": "Dark Mode", "story": "As a user, I want to toggle between light and dark themes", "needs_db": False, "complexity": "low", "expected_steps": (2, 8)},
    {"id": 92, "name": "Language Selector", "story": "As a user, I want to change the app language", "needs_db": False, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 93, "name": "Keyboard Shortcuts", "story": "As a power user, I want keyboard shortcuts for common actions", "needs_db": False, "complexity": "low", "expected_steps": (2, 8)},
    {"id": 94, "name": "Print View", "story": "As a user, I want a print-friendly view of content", "needs_db": False, "complexity": "low", "expected_steps": (2, 8)},
    {"id": 95, "name": "QR Code Scanner", "story": "As a user, I want to scan QR codes to access content", "needs_db": False, "complexity": "medium", "expected_steps": (3, 10)},
    {"id": 96, "name": "Voice Search", "story": "As a user, I want to search using voice commands", "needs_db": False, "complexity": "medium", "expected_steps": (3, 10)},
    {"id": 97, "name": "Drag and Drop", "story": "As a user, I want to reorder items by drag and drop", "needs_db": True, "complexity": "medium", "expected_steps": (4, 12)},
    {"id": 98, "name": "Infinite Scroll", "story": "As a user, I want content to load as I scroll down", "needs_db": True, "complexity": "low", "expected_steps": (3, 10)},
    {"id": 99, "name": "Skeleton Loading", "story": "As a user, I want to see skeleton screens while content loads", "needs_db": False, "complexity": "low", "expected_steps": (2, 8)},
    {"id": 100, "name": "Error Handling", "story": "As a user, I want to see friendly error pages when things go wrong", "needs_db": False, "complexity": "low", "expected_steps": (2, 8)},
]

# Boilerplate files that should NOT be created
BOILERPLATE_FILES = {
    "src/lib/prisma.ts",
    "src/lib/utils.ts", 
    "src/auth.ts",
}


def evaluate_plan(steps: list, story: dict) -> dict:
    """Evaluate plan quality and return scores."""
    issues = []
    
    # Extract file paths and info
    file_paths = [s.get("file_path", "") for s in steps]
    
    # 1. Has schema if needs DB
    has_schema = any("schema.prisma" in fp for fp in file_paths)
    if story["needs_db"] and not has_schema:
        issues.append("Missing schema")
    
    # 2. Has seed after schema
    has_seed = any("seed.ts" in fp for fp in file_paths)
    schema_idx = next((i for i, fp in enumerate(file_paths) if "schema.prisma" in fp), -1)
    seed_idx = next((i for i, fp in enumerate(file_paths) if "seed.ts" in fp), -1)
    seed_after_schema = seed_idx > schema_idx if schema_idx >= 0 and seed_idx >= 0 else True
    if has_schema and has_seed and not seed_after_schema:
        issues.append("Seed before schema")
    
    # 3. Correct order: schema < api < component < page
    def get_layer(fp):
        if "schema.prisma" in fp: return 1
        if "seed.ts" in fp: return 2
        if "/api/" in fp: return 5
        if "/components/" in fp: return 7
        if "page.tsx" in fp: return 8
        return 6
    
    layers = [get_layer(fp) for fp in file_paths]
    correct_order = layers == sorted(layers)
    if not correct_order:
        issues.append("Wrong order")
    
    # 4. Components have API dependencies (components that fetch data)
    api_routes = [fp for fp in file_paths if "/api/" in fp]
    components = [s for s in steps if "/components/" in s.get("file_path", "")]
    
    api_deps_ok = True
    for comp in components:
        comp_fp = comp.get("file_path", "")
        comp_deps = comp.get("dependencies", [])
        # Check if component name suggests it fetches data
        fetch_keywords = ["Section", "List", "Grid", "Carousel", "Feed"]
        if any(kw in comp_fp for kw in fetch_keywords):
            has_api_dep = any("/api/" in dep for dep in comp_deps)
            if not has_api_dep and api_routes:
                api_deps_ok = False
                issues.append(f"Missing API dep: {comp_fp.split('/')[-1]}")
                break
    
    # 5. Pages have component dependencies
    pages = [s for s in steps if "page.tsx" in s.get("file_path", "")]
    page_deps_ok = True
    for page in pages:
        page_deps = page.get("dependencies", [])
        has_comp_dep = any("/components/" in dep for dep in page_deps)
        # Homepage and main pages should have component deps
        if "app/page.tsx" in page.get("file_path", "") or "/app/" in page.get("file_path", ""):
            if components and not has_comp_dep:
                page_deps_ok = False
                issues.append(f"Missing comp dep: {page.get('file_path', '').split('/')[-1]}")
                break
    
    # 6. No boilerplate files
    no_boilerplate = not any(fp in BOILERPLATE_FILES for fp in file_paths)
    if not no_boilerplate:
        issues.append("Creates boilerplate")
    
    # 7. Reasonable step count
    min_steps, max_steps = story["expected_steps"]
    reasonable_steps = min_steps <= len(steps) <= max_steps
    if not reasonable_steps:
        issues.append(f"Steps: {len(steps)} (expect {min_steps}-{max_steps})")
    
    # Calculate score
    checks = {
        "has_schema": has_schema if story["needs_db"] else True,
        "seed_order": seed_after_schema,
        "correct_order": correct_order,
        "api_deps": api_deps_ok,
        "page_deps": page_deps_ok,
        "no_boilerplate": no_boilerplate,
        "reasonable_steps": reasonable_steps,
    }
    
    score = sum(1 for v in checks.values() if v) / len(checks)
    
    return {
        "score": score,
        "checks": checks,
        "issues": issues,
    }


async def test_single_story(story: dict, workspace_path: str) -> dict:
    """Test planning for a single story."""
    from app.agents.developer_v2.src.nodes.plan import plan
    from app.agents.developer_v2.src.state import DeveloperState
    from app.agents.developer_v2.src.skills.registry import SkillRegistry
    
    # Setup state
    state = DeveloperState(
        story_id=f"TEST-{story['id']:03d}",
        story_title=story["story"],
        workspace_path=workspace_path,
        template="nextjs",
        skill_registry=SkillRegistry("nextjs"),
    )
    
    start = time.time()
    result_state = await plan(state)
    elapsed = time.time() - start
    
    steps = result_state.get("implementation_plan", [])
    evaluation = evaluate_plan(steps, story)
    
    return {
        "story_id": story["id"],
        "story_name": story["name"],
        "time": elapsed,
        "steps": len(steps),
        "score": evaluation["score"],
        "issues": evaluation["issues"],
        "checks": evaluation["checks"],
        "plan": steps,
    }


async def run_all_tests():
    """Run plan quality tests for all stories."""
    print("=" * 70)
    print("PLAN QUALITY TEST - 10 STORIES")
    print("=" * 70)
    print()
    
    # Use a temp workspace (just needs to exist for FileRepository)
    workspace_path = str(backend_path / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate")
    
    results = []
    
    for story in STORIES:
        print(f"Testing {story['id']:2d}. {story['name']:<20} ... ", end="", flush=True)
        
        try:
            result = await test_single_story(story, workspace_path)
            results.append(result)
            
            status = "PASS" if result["score"] >= 0.85 else "FAIL"
            issues_str = ", ".join(result["issues"][:2]) if result["issues"] else "-"
            print(f"{status} {result['time']:5.1f}s  {result['steps']:2d} steps  {result['score']:.2f}  {issues_str}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "story_id": story["id"],
                "story_name": story["name"],
                "time": 0,
                "steps": 0,
                "score": 0,
                "issues": [str(e)],
                "error": True,
            })
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Story':<30} {'Time':>6} {'Steps':>6} {'Score':>6} {'Issues'}")
    print("-" * 70)
    
    for r in results:
        issues_str = ", ".join(r["issues"][:2]) if r["issues"] else "-"
        print(f"{r['story_id']:2d}. {r['story_name']:<26} {r['time']:5.1f}s {r['steps']:>6} {r['score']:>6.2f}  {issues_str}")
    
    print("-" * 70)
    
    avg_time = sum(r["time"] for r in results) / len(results)
    avg_steps = sum(r["steps"] for r in results) / len(results)
    avg_score = sum(r["score"] for r in results) / len(results)
    passed = sum(1 for r in results if r["score"] >= 0.85)
    
    print(f"{'AVERAGE':<30} {avg_time:5.1f}s {avg_steps:>6.1f} {avg_score:>6.2f}")
    print()
    print(f"PASS: {passed}/{len(results)} stories ({100*passed/len(results):.0f}%)")
    print(f"Average Score: {avg_score:.2f}")
    print()
    
    # Detailed issues
    all_issues = []
    for r in results:
        for issue in r["issues"]:
            all_issues.append(issue)
    
    if all_issues:
        print("Common Issues:")
        from collections import Counter
        for issue, count in Counter(all_issues).most_common(5):
            print(f"  - {issue}: {count}x")
    
    return results


async def test_single(story_id: int):
    """Test a single story by ID."""
    story = next((s for s in STORIES if s["id"] == story_id), None)
    if not story:
        print(f"Story {story_id} not found")
        return
    
    workspace_path = str(backend_path / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate")
    
    print(f"Testing: {story['name']}")
    print(f"Story: {story['story']}")
    print()
    
    result = await test_single_story(story, workspace_path)
    
    print(f"Time: {result['time']:.1f}s")
    print(f"Steps: {result['steps']}")
    print(f"Score: {result['score']:.2f}")
    print(f"Issues: {result['issues'] or 'None'}")
    print()
    
    print("Plan:")
    for i, step in enumerate(result.get("plan", []), 1):
        deps = step.get("dependencies", [])
        deps_str = f" <- {deps}" if deps else ""
        print(f"  {i:2d}. [{step.get('action', '?')}] {step.get('file_path', '?')}{deps_str}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", type=int, help="Test single story by ID (1-10)")
    args = parser.parse_args()
    
    if args.story:
        asyncio.run(test_single(args.story))
    else:
        asyncio.run(run_all_tests())
