"""End-to-End Test for Developer V2 - Create Learning Website.

This test simulates a real scenario where the DeveloperV2 agent
processes a story to create a beautiful learning website.
"""

import asyncio
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.graph import DeveloperGraph
from app.agents.developer_v2.src.nodes import (
    router, analyze, plan, implement, 
    code_review, run_code, debug_error,
    merge_to_main, cleanup_workspace, respond
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def learning_website_story():
    """Story for creating a learning website."""
    return {
        "story_id": str(uuid4()),
        "story_title": "Tạo Website Học Tập Online",
        "story_content": """
## User Story
As a student, I want to have a beautiful online learning platform
so that I can learn programming effectively.

## Description
Tạo một website học tập online đẹp mắt với các tính năng:
- Trang chủ giới thiệu các khóa học
- Danh sách khóa học với card design đẹp
- Trang chi tiết khóa học với video player
- Hệ thống đăng ký/đăng nhập
- Dashboard học viên với tiến độ học tập
- Responsive design cho mobile

## Technical Stack
- Frontend: React + TailwindCSS
- Components: shadcn/ui
- Icons: Lucide React
- Animations: Framer Motion

## Design Requirements
- Modern, clean UI với color scheme: Blue (#3B82F6) + White + Gray
- Card-based layout cho khóa học
- Gradient backgrounds
- Smooth animations
- Dark mode support
""",
        "acceptance_criteria": [
            "Trang chủ hiển thị hero section với call-to-action",
            "Danh sách khóa học với filter theo category",
            "Card khóa học có thumbnail, title, instructor, rating",
            "Trang chi tiết có video player và curriculum",
            "Form đăng ký/đăng nhập với validation",
            "Dashboard có progress bars và statistics",
            "Responsive trên mobile, tablet, desktop",
            "Dark mode toggle hoạt động"
        ],
        "project_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": str(uuid4()),
    }


@pytest.fixture
def mock_developer_agent():
    """Create mock DeveloperV2 agent with full capabilities."""
    agent = MagicMock()
    agent.name = "TestDeveloper"
    agent.role_type = "developer"
    agent.project_id = uuid4()
    agent.message_user = AsyncMock()
    agent.context = MagicMock()
    agent.context.ensure_loaded = AsyncMock()
    
    # Mock workspace manager
    agent.workspace_manager = MagicMock()
    agent.main_workspace = Path(tempfile.gettempdir()) / "test_workspace"
    agent.git_tool = MagicMock()
    
    return agent


@pytest.fixture
def temp_project_workspace():
    """Create temporary project workspace."""
    tmpdir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    workspace = Path(tmpdir_obj.name)
    
    # Create project structure
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "components").mkdir()
    (workspace / "src" / "pages").mkdir()
    (workspace / "src" / "styles").mkdir()
    (workspace / "public").mkdir()
    
    # Create package.json
    (workspace / "package.json").write_text(json.dumps({
        "name": "learning-website",
        "version": "0.1.0",
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "test": "jest",
            "lint": "eslint ."
        },
        "dependencies": {
            "react": "^18.2.0",
            "next": "^14.0.0",
            "tailwindcss": "^3.3.0"
        }
    }, indent=2))
    
    # Create tailwind.config.js
    (workspace / "tailwind.config.js").write_text("""
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6',
      },
    },
  },
  plugins: [],
}
""")
    
    yield workspace
    
    try:
        tmpdir_obj.cleanup()
    except (PermissionError, OSError):
        pass


# =============================================================================
# MOCK LLM RESPONSES
# =============================================================================

def create_router_response(action="ANALYZE"):
    """Create mock router response."""
    return MagicMock(content=json.dumps({
        "action": action,
        "task_type": "feature",
        "complexity": "high",
        "message": "Analyzing learning website story...",
        "reason": "new_feature_request",
        "confidence": 0.95
    }))


def create_analyze_response():
    """Create mock analyze response for learning website."""
    return MagicMock(content=json.dumps({
        "task_type": "feature",  # Must be one of: feature, bugfix, refactor, enhancement, documentation
        "complexity": "high",
        "summary": "Create a modern learning website with React and TailwindCSS",
        "affected_files": [
            "src/pages/index.tsx",
            "src/pages/courses.tsx",
            "src/pages/course/[id].tsx",
            "src/components/Navbar.tsx",
            "src/components/CourseCard.tsx",
            "src/components/HeroSection.tsx",
            "src/components/Footer.tsx"
        ],
        "dependencies": ["react", "next", "tailwindcss", "framer-motion", "lucide-react"],
        "risks": ["Complex UI requires careful component design"],
        "suggested_approach": "Start with layout components, then build pages",
        "estimated_hours": 8  # Must be <= 100
    }))


def create_plan_response():
    """Create mock plan response with implementation steps."""
    return MagicMock(content=json.dumps({
        "story_summary": "Learning website with modern UI",
        "steps": [
            {
                "order": 1,
                "description": "Create Navbar component with logo, nav links, dark mode toggle",
                "file_path": "src/components/Navbar.tsx",
                "action": "create",
                "estimated_hours": 1
            },
            {
                "order": 2,
                "description": "Create HeroSection with gradient background and CTA buttons",
                "file_path": "src/components/HeroSection.tsx",
                "action": "create",
                "estimated_hours": 1
            },
            {
                "order": 3,
                "description": "Create CourseCard component with thumbnail, info, rating",
                "file_path": "src/components/CourseCard.tsx",
                "action": "create",
                "estimated_hours": 1
            },
            {
                "order": 4,
                "description": "Create Footer component",
                "file_path": "src/components/Footer.tsx",
                "action": "create",
                "estimated_hours": 0.5
            },
            {
                "order": 5,
                "description": "Create homepage with hero, featured courses, testimonials",
                "file_path": "src/pages/index.tsx",
                "action": "create",
                "estimated_hours": 2
            },
            {
                "order": 6,
                "description": "Create courses listing page with filters",
                "file_path": "src/pages/courses.tsx",
                "action": "create",
                "estimated_hours": 2
            }
        ],
        "total_estimated_hours": 7.5,
        "files_to_create": [
            "src/components/Navbar.tsx",
            "src/components/HeroSection.tsx",
            "src/components/CourseCard.tsx",
            "src/components/Footer.tsx",
            "src/pages/index.tsx",
            "src/pages/courses.tsx"
        ],
        "files_to_modify": []
    }))


def create_implement_response(file_path: str, step_order: int):
    """Create mock implement response for each step."""
    
    code_templates = {
        "src/components/Navbar.tsx": '''
import React, { useState } from 'react';
import { Moon, Sun, Menu, X, BookOpen } from 'lucide-react';
import Link from 'next/link';

interface NavbarProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ darkMode, toggleDarkMode }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <nav className="fixed top-0 w-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-md z-50 border-b border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <BookOpen className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              LearnHub
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center space-x-8">
            <Link href="/courses" className="text-gray-700 dark:text-gray-300 hover:text-primary transition">
              Khóa học
            </Link>
            <Link href="/about" className="text-gray-700 dark:text-gray-300 hover:text-primary transition">
              Về chúng tôi
            </Link>
            <Link href="/pricing" className="text-gray-700 dark:text-gray-300 hover:text-primary transition">
              Bảng giá
            </Link>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
            >
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            
            <Link href="/login" className="hidden md:block px-4 py-2 text-primary border border-primary rounded-lg hover:bg-primary hover:text-white transition">
              Đăng nhập
            </Link>
            
            <Link href="/register" className="hidden md:block px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 transition">
              Đăng ký
            </Link>

            {/* Mobile menu button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="md:hidden p-2 rounded-lg"
            >
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
          <div className="px-4 py-4 space-y-3">
            <Link href="/courses" className="block py-2 text-gray-700 dark:text-gray-300">Khóa học</Link>
            <Link href="/about" className="block py-2 text-gray-700 dark:text-gray-300">Về chúng tôi</Link>
            <Link href="/login" className="block py-2 text-primary">Đăng nhập</Link>
            <Link href="/register" className="block py-2 bg-primary text-white text-center rounded-lg">Đăng ký</Link>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
''',
        "src/components/HeroSection.tsx": '''
import React from 'react';
import { motion } from 'framer-motion';
import { Play, Users, BookOpen, Award } from 'lucide-react';
import Link from 'next/link';

export const HeroSection: React.FC = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-blue-900" />
      
      {/* Animated circles */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob" />
      <div className="absolute top-40 right-10 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000" />
      <div className="absolute bottom-20 left-1/2 w-72 h-72 bg-pink-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="inline-block px-4 py-2 bg-blue-100 dark:bg-blue-900 text-primary rounded-full text-sm font-medium mb-6">
            [Run] Khám phá hơn 1000+ khóa học
          </span>
          
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
            Học Lập Trình
            <span className="block bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Dễ Dàng & Hiệu Quả
            </span>
          </h1>
          
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
            Nền tảng học tập trực tuyến hàng đầu với các khóa học chất lượng cao,
            được thiết kế bởi các chuyên gia hàng đầu trong ngành.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <Link href="/courses" className="w-full sm:w-auto px-8 py-4 bg-primary text-white rounded-xl font-semibold hover:bg-blue-700 transition shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2">
              <BookOpen className="h-5 w-5" />
              Khám phá khóa học
            </Link>
            <button className="w-full sm:w-auto px-8 py-4 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition border border-gray-200 dark:border-gray-700 flex items-center justify-center gap-2">
              <Play className="h-5 w-5" />
              Xem demo
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary mb-1">10K+</div>
              <div className="text-gray-600 dark:text-gray-400 text-sm">Học viên</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary mb-1">500+</div>
              <div className="text-gray-600 dark:text-gray-400 text-sm">Khóa học</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary mb-1">50+</div>
              <div className="text-gray-600 dark:text-gray-400 text-sm">Giảng viên</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary mb-1">95%</div>
              <div className="text-gray-600 dark:text-gray-400 text-sm">Hài lòng</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default HeroSection;
''',
        "src/components/CourseCard.tsx": '''
import React from 'react';
import { motion } from 'framer-motion';
import { Star, Clock, Users, Play } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';

interface CourseCardProps {
  id: string;
  title: string;
  instructor: string;
  thumbnail: string;
  rating: number;
  students: number;
  duration: string;
  price: number;
  originalPrice?: number;
  category: string;
}

export const CourseCard: React.FC<CourseCardProps> = ({
  id,
  title,
  instructor,
  thumbnail,
  rating,
  students,
  duration,
  price,
  originalPrice,
  category,
}) => {
  return (
    <motion.div
      whileHover={{ y: -5 }}
      className="group bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300"
    >
      {/* Thumbnail */}
      <div className="relative h-48 overflow-hidden">
        <Image
          src={thumbnail}
          alt={title}
          fill
          className="object-cover group-hover:scale-110 transition-transform duration-300"
        />
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <button className="p-4 bg-white rounded-full">
            <Play className="h-6 w-6 text-primary" fill="currentColor" />
          </button>
        </div>
        <span className="absolute top-4 left-4 px-3 py-1 bg-primary text-white text-xs font-medium rounded-full">
          {category}
        </span>
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="font-semibold text-lg text-gray-900 dark:text-white mb-2 line-clamp-2 group-hover:text-primary transition">
          {title}
        </h3>
        
        <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
          bởi <span className="font-medium">{instructor}</span>
        </p>

        {/* Meta info */}
        <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-4">
          <div className="flex items-center gap-1">
            <Star className="h-4 w-4 text-yellow-500" fill="currentColor" />
            <span className="font-medium text-gray-900 dark:text-white">{rating}</span>
          </div>
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            <span>{students.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>{duration}</span>
          </div>
        </div>

        {/* Price */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-primary">
              {price.toLocaleString()}đ
            </span>
            {originalPrice && (
              <span className="text-sm text-gray-400 line-through">
                {originalPrice.toLocaleString()}đ
              </span>
            )}
          </div>
          <Link
            href={`/course/${id}`}
            className="px-4 py-2 bg-primary/10 text-primary rounded-lg font-medium hover:bg-primary hover:text-white transition"
          >
            Xem chi tiết
          </Link>
        </div>
      </div>
    </motion.div>
  );
};

export default CourseCard;
''',
        "src/components/Footer.tsx": '''
import React from 'react';
import { BookOpen, Facebook, Twitter, Youtube, Mail } from 'lucide-react';
import Link from 'next/link';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-1">
            <Link href="/" className="flex items-center space-x-2 mb-4">
              <BookOpen className="h-8 w-8 text-primary" />
              <span className="text-xl font-bold text-white">LearnHub</span>
            </Link>
            <p className="text-sm text-gray-400 mb-4">
              Nền tảng học tập trực tuyến hàng đầu Việt Nam với hơn 1000+ khóa học chất lượng cao.
            </p>
            <div className="flex space-x-4">
              <a href="#" className="hover:text-primary transition"><Facebook className="h-5 w-5" /></a>
              <a href="#" className="hover:text-primary transition"><Twitter className="h-5 w-5" /></a>
              <a href="#" className="hover:text-primary transition"><Youtube className="h-5 w-5" /></a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-semibold mb-4">Khóa học</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/courses/web" className="hover:text-primary transition">Web Development</Link></li>
              <li><Link href="/courses/mobile" className="hover:text-primary transition">Mobile Development</Link></li>
              <li><Link href="/courses/ai" className="hover:text-primary transition">AI & Machine Learning</Link></li>
              <li><Link href="/courses/data" className="hover:text-primary transition">Data Science</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-white font-semibold mb-4">Công ty</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/about" className="hover:text-primary transition">Về chúng tôi</Link></li>
              <li><Link href="/careers" className="hover:text-primary transition">Tuyển dụng</Link></li>
              <li><Link href="/blog" className="hover:text-primary transition">Blog</Link></li>
              <li><Link href="/contact" className="hover:text-primary transition">Liên hệ</Link></li>
            </ul>
          </div>

          {/* Newsletter */}
          <div>
            <h3 className="text-white font-semibold mb-4">Đăng ký nhận tin</h3>
            <p className="text-sm text-gray-400 mb-4">
              Nhận thông tin về khóa học mới và ưu đãi đặc biệt.
            </p>
            <form className="flex">
              <input
                type="email"
                placeholder="Email của bạn"
                className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-l-lg focus:outline-none focus:border-primary"
              />
              <button className="px-4 py-2 bg-primary text-white rounded-r-lg hover:bg-blue-700 transition">
                <Mail className="h-5 w-5" />
              </button>
            </form>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800 text-center text-sm text-gray-400">
          <p>© 2024 LearnHub. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
''',
        "src/pages/index.tsx": '''
import React, { useState } from 'react';
import Head from 'next/head';
import { Navbar } from '@/components/Navbar';
import { HeroSection } from '@/components/HeroSection';
import { CourseCard } from '@/components/CourseCard';
import { Footer } from '@/components/Footer';

const featuredCourses = [
  {
    id: '1',
    title: 'React & Next.js - Xây dựng Website Chuyên Nghiệp',
    instructor: 'Nguyễn Văn A',
    thumbnail: '/images/courses/react.jpg',
    rating: 4.9,
    students: 5420,
    duration: '32 giờ',
    price: 599000,
    originalPrice: 1299000,
    category: 'Web Development',
  },
  {
    id: '2',
    title: 'Python cho Data Science & Machine Learning',
    instructor: 'Trần Thị B',
    thumbnail: '/images/courses/python.jpg',
    rating: 4.8,
    students: 3210,
    duration: '45 giờ',
    price: 799000,
    originalPrice: 1599000,
    category: 'Data Science',
  },
  {
    id: '3',
    title: 'Flutter - Lập trình Mobile Cross-Platform',
    instructor: 'Lê Văn C',
    thumbnail: '/images/courses/flutter.jpg',
    rating: 4.7,
    students: 2180,
    duration: '28 giờ',
    price: 499000,
    originalPrice: 999000,
    category: 'Mobile',
  },
];

export default function HomePage() {
  const [darkMode, setDarkMode] = useState(false);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <div className={darkMode ? 'dark' : ''}>
      <Head>
        <title>LearnHub - Nền tảng học tập trực tuyến</title>
        <meta name="description" content="Khám phá hơn 1000+ khóa học chất lượng cao" />
      </Head>

      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="min-h-screen bg-white dark:bg-gray-900">
        <HeroSection />

        {/* Featured Courses Section */}
        <section className="py-20 bg-gray-50 dark:bg-gray-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Khóa học nổi bật
              </h2>
              <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                Các khóa học được đánh giá cao nhất và được nhiều học viên lựa chọn
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {featuredCourses.map((course) => (
                <CourseCard key={course.id} {...course} />
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
''',
        "src/pages/courses.tsx": '''
import React, { useState } from 'react';
import Head from 'next/head';
import { Search, Filter, ChevronDown } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { CourseCard } from '@/components/CourseCard';
import { Footer } from '@/components/Footer';

const categories = ['Tất cả', 'Web Development', 'Mobile', 'Data Science', 'AI & ML', 'DevOps'];

const allCourses = [
  // ... course data
];

export default function CoursesPage() {
  const [darkMode, setDarkMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('Tất cả');
  const [sortBy, setSortBy] = useState('popular');

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <div className={darkMode ? 'dark' : ''}>
      <Head>
        <title>Khóa học - LearnHub</title>
      </Head>

      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Khám phá khóa học
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Hơn 500+ khóa học chất lượng cao đang chờ bạn
            </p>
          </div>

          {/* Filters */}
          <div className="flex flex-col lg:flex-row gap-4 mb-8">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Tìm kiếm khóa học..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                    selectedCategory === cat
                      ? 'bg-primary text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Course Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Course cards would be rendered here */}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
''',
    }
    
    code = code_templates.get(file_path, f"// Component for {file_path}")
    
    return MagicMock(content=json.dumps({
        "file_path": file_path,
        "code": code,
        "explanation": f"Created {file_path} with modern React and TailwindCSS",
        "imports_added": ["react", "next/link", "lucide-react", "framer-motion"],
        "tests_to_write": [f"test_{Path(file_path).stem}.test.tsx"]
    }))


def create_code_review_response(file_path: str, result="LGTM"):
    """Create mock code review response."""
    return MagicMock(content=json.dumps({
        "filename": file_path,
        "result": result,
        "issues": [] if result == "LGTM" else ["Minor: Consider adding more comments"],
        "rewritten_code": ""
    }))


def create_run_code_response(status="PASS"):
    """Create mock run code analysis response."""
    return MagicMock(content=json.dumps({
        "status": status,
        "summary": "All components render correctly, no errors found" if status == "PASS" else "Build error in component",
        "file_to_fix": "" if status == "PASS" else "src/components/Navbar.tsx",
        "send_to": "NoOne" if status == "PASS" else "Engineer"
    }))


# =============================================================================
# E2E TEST
# =============================================================================

class TestE2ELearningWebsite:
    """End-to-End test for creating a learning website."""
    
    @pytest.mark.asyncio
    async def test_create_learning_website_full_flow(
        self, 
        learning_website_story, 
        mock_developer_agent, 
        temp_project_workspace
    ):
        """Test the complete flow of creating a learning website.
        
        Flow: router → analyze → plan → implement (6 steps) → code_review → run_code → merge → respond
        """
        # Setup initial state
        initial_state = {
            **learning_website_story,
            "langfuse_handler": None,
            "workspace_path": str(temp_project_workspace),
            "branch_name": "story_learning_website",
            "main_workspace": str(temp_project_workspace),
            "workspace_ready": True,
            "index_ready": False,
            "merged": False,
            "action": None,
            "task_type": None,
            "complexity": None,
            "analysis_result": None,
            "implementation_plan": [],
            "code_changes": [],
            "files_created": [],
            "files_modified": [],
            "current_step": 0,
            "total_steps": 0,
            "code_review_k": 2,
            "code_review_passed": False,
            "code_review_iteration": 0,
            "code_review_results": [],
            "run_status": None,
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "test_command": None,
            "debug_count": 0,
            "max_debug": 3,
            "debug_history": [],
            "validation_result": None,
            "message": None,
            "confidence": None,
        }
        
        print("\n" + "="*60)
        print("[E2E] Create Learning Website")
        print("="*60)
        
        # Step 1: Router
        print("\n[Step 1] Router - Analyzing story...")
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=create_router_response("ANALYZE"))
            result = await router(initial_state, mock_developer_agent)
            assert result["action"] == "ANALYZE"
            print(f"   [OK] Decision: {result['action']}, Type: {result.get('task_type')}")
        
        initial_state.update(result)
        
        # Step 2: Analyze (uses _code_llm)
        print("\n[Step 2] Analyze - Understanding requirements...")
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=create_analyze_response())
            result = await analyze(initial_state, mock_developer_agent)
            assert result["analysis_result"] is not None
            print(f"   [OK] Analysis: {result['analysis_result'].get('summary', '')[:50]}...")
            print(f"   [Files] Affected files: {len(result['analysis_result'].get('affected_files', []))}")
        
        initial_state.update(result)
        
        # Step 3: Plan
        print("\n[Step] Step 3: Plan - Creating implementation plan...")
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=create_plan_response())
            result = await plan(initial_state, mock_developer_agent)
            assert len(result["implementation_plan"]) > 0
            print(f"   [OK] Plan: {result['total_steps']} steps to implement")
            for step in result["implementation_plan"][:3]:
                print(f"      - Step {step['order']}: {step['description'][:40]}...")
        
        initial_state.update(result)
        
        # Step 4: Implement (multiple steps)
        print("\n[Step] Step 4: Implement - Creating components...")
        files_created = []
        for step in initial_state["implementation_plan"]:
            file_path = step["file_path"]
            print(f"   [Create] Creating {file_path}...")
            
            with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
                 patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
                mock_llm.ainvoke = AsyncMock(return_value=create_implement_response(file_path, step["order"]))
                
                initial_state["current_step"] = step["order"]
                result = await implement(initial_state, mock_developer_agent)
                
                # Simulate file creation
                full_path = temp_project_workspace / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(f"// Auto-generated: {file_path}\n// Component implementation")
                
                files_created.append(file_path)
                initial_state.update(result)
        
        print(f"   [OK] Created {len(files_created)} files")
        initial_state["files_created"] = files_created
        initial_state["code_changes"] = [{"file_path": f, "code_snippet": "..."} for f in files_created]
        
        # Step 5: Code Review
        print("\n[Step] Step 5: Code Review - Reviewing code quality...")
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=create_code_review_response("src/components/Navbar.tsx", "LGTM"))
            result = await code_review(initial_state, mock_developer_agent)
            print(f"   [OK] Review passed: {result['code_review_passed']}")
        
        initial_state.update(result)
        
        # Step 6: Run Code
        print("\n[Step] Step 6: Run Code - Testing the application...")
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"), \
             patch('app.agents.developer_v2.tools.execute_command_async') as mock_exec:
            mock_llm.ainvoke = AsyncMock(return_value=create_run_code_response("PASS"))
            mock_exec.return_value = MagicMock(stdout="Build succeeded", stderr="", returncode=0, success=True)
            result = await run_code(initial_state, mock_developer_agent)
            print(f"   [OK] Tests: {result['run_status']}")
        
        initial_state.update(result)
        
        # Step 7: Respond (skip merge for test)
        print("\n[Step] Step 7: Respond - Generating response...")
        initial_state["message"] = f"""
[OK] **Website Học Tập đã được tạo thành công!**

[Files] **Các file đã tạo:**
{chr(10).join(f'- {f}' for f in files_created)}

[Features] **Tính năng đã implement:**
- Navbar với dark mode toggle
- Hero section với animations
- Course cards với hover effects
- Footer với newsletter form
- Homepage với featured courses
- Courses page với filters

[Run] **Hướng dẫn chạy:**
```bash
npm install
npm run dev
```

Truy cập http://localhost:3000 để xem website!
"""
        
        with patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            result = await respond(initial_state, mock_developer_agent)
        
        print("\n" + "="*60)
        print("[OK] E2E Test Completed Successfully!")
        print("="*60)
        print(f"\n[Summary]:")
        print(f"   - Files created: {len(files_created)}")
        print(f"   - Code review: PASSED")
        print(f"   - Tests: PASSED")
        print(f"   - Story: Learning Website")
        
        # Assertions
        assert len(files_created) >= 4
        assert initial_state["code_review_passed"] == True
        assert initial_state["run_status"] == "PASS"
        assert mock_developer_agent.message_user.called
    
    @pytest.mark.asyncio
    async def test_learning_website_with_debug_flow(
        self,
        learning_website_story,
        mock_developer_agent,
        temp_project_workspace
    ):
        """Test flow with debugging when tests fail."""
        initial_state = {
            **learning_website_story,
            "langfuse_handler": None,
            "workspace_path": str(temp_project_workspace),
            "branch_name": "story_debug_test",
            "main_workspace": str(temp_project_workspace),
            "workspace_ready": True,
            "files_created": ["src/components/BuggyComponent.tsx"],
            "files_modified": [],
            "code_changes": [{"file_path": "src/components/BuggyComponent.tsx", "code_snippet": "..."}],
            "code_review_passed": True,
            "code_review_k": 2,
            "code_review_iteration": 0,
            "run_status": None,
            "run_result": None,
            "run_stdout": "",
            "run_stderr": "",
            "debug_count": 0,
            "max_debug": 3,
            "debug_history": [],
        }
        
        print("\n" + "="*60)
        print("[Debug] E2E Test: Debug Flow")
        print("="*60)
        
        # Create buggy component
        buggy_file = temp_project_workspace / "src" / "components" / "BuggyComponent.tsx"
        buggy_file.parent.mkdir(parents=True, exist_ok=True)
        buggy_file.write_text("// Buggy component with error")
        
        # Run code - FAIL
        print("\n[Step] Step 1: Run Code - Tests fail...")
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"), \
             patch('app.agents.developer_v2.tools.execute_command_async') as mock_exec:
            mock_llm.ainvoke = AsyncMock(return_value=create_run_code_response("FAIL"))
            mock_exec.return_value = MagicMock(
                stdout="", 
                stderr="Error: Cannot find module 'missing-dep'", 
                returncode=1, 
                success=False
            )
            result = await run_code(initial_state, mock_developer_agent)
            assert result["run_status"] == "FAIL"
            print(f"   [FAIL] Tests failed: {result['run_result'].get('summary', '')[:50]}...")
        
        initial_state.update(result)
        
        # Debug error
        print("\n[Step] Step 2: Debug Error - Fixing the bug...")
        with patch('app.agents.developer_v2.src.nodes._code_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"):
            mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps({
                "analysis": "Missing import statement",
                "root_cause": "Module not imported correctly",
                "fix_description": "Added missing import",
                "fixed_code": "import React from 'react';\n// Fixed component"
            })))
            result = await debug_error(initial_state, mock_developer_agent)
            assert result["debug_count"] == 1
            print(f"   [Debug] Debug iteration: {result['debug_count']}")
            print(f"   [Create] Fixed file: {result.get('last_debug_file', 'N/A')}")
        
        initial_state.update(result)
        
        # Run code again - PASS
        print("\n[Step] Step 3: Run Code Again - Tests pass...")
        with patch('app.agents.developer_v2.src.nodes._fast_llm') as mock_llm, \
             patch('app.agents.developer_v2.src.nodes._build_system_prompt', return_value="System prompt"), \
             patch('app.agents.developer_v2.tools.execute_command_async') as mock_exec:
            mock_llm.ainvoke = AsyncMock(return_value=create_run_code_response("PASS"))
            mock_exec.return_value = MagicMock(stdout="All tests passed", stderr="", returncode=0, success=True)
            result = await run_code(initial_state, mock_developer_agent)
            assert result["run_status"] == "PASS"
            print(f"   [OK] Tests passed after fix!")
        
        print("\n" + "="*60)
        print("[OK] Debug Flow Test Completed!")
        print("="*60)


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
