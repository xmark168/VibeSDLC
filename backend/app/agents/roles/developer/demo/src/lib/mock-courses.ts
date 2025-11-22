/**
 * Mock Course Data
 * Sample course categories for the landing page
 */

import type { CourseCategory, Benefit, HeroSection } from "@/types/course.types";

export const mockCourseCategories: CourseCategory[] = [
  {
    id: "web-development",
    title: "Web Development",
    description: "Master modern web technologies and build beautiful, responsive websites and applications.",
    imageUrl: "/images/categories/web-development.jpg",
    slug: "web-development",
    color: "from-blue-500 to-cyan-500",
    icon: "💻",
    featured: true,
    courseCount: 24,
  },
  {
    id: "mobile-apps",
    title: "Mobile Apps",
    description: "Create stunning mobile applications for iOS and Android using cutting-edge frameworks.",
    imageUrl: "/images/categories/mobile-apps.jpg",
    slug: "mobile-apps",
    color: "from-green-500 to-emerald-500",
    icon: "📱",
    featured: true,
    courseCount: 18,
  },
  {
    id: "data-science",
    title: "Data Science",
    description: "Unlock the power of data with machine learning, statistics, and visualization techniques.",
    imageUrl: "/images/categories/data-science.jpg",
    slug: "data-science",
    color: "from-purple-500 to-violet-500",
    icon: "📊",
    featured: true,
    courseCount: 16,
  },
  {
    id: "cybersecurity",
    title: "Cybersecurity",
    description: "Protect digital assets and master the skills needed to secure modern systems.",
    imageUrl: "/images/categories/cybersecurity.jpg",
    slug: "cybersecurity",
    color: "from-red-500 to-orange-500",
    icon: "🔒",
    featured: false,
    courseCount: 12,
  },
  {
    id: "cloud-computing",
    title: "Cloud Computing",
    description: "Deploy scalable applications and master cloud platforms like AWS, Azure, and Google Cloud.",
    imageUrl: "/images/categories/cloud-computing.jpg",
    slug: "cloud-computing",
    color: "from-indigo-500 to-blue-500",
    icon: "☁️",
    featured: false,
    courseCount: 20,
  },
  {
    id: "artificial-intelligence",
    title: "Artificial Intelligence",
    description: "Build intelligent systems and explore the future of AI with practical projects.",
    imageUrl: "/images/categories/ai.jpg",
    slug: "artificial-intelligence",
    color: "from-pink-500 to-rose-500",
    icon: "🤖",
    featured: false,
    courseCount: 14,
  },
];

export const platformBenefits: Benefit[] = [
  {
    id: "learn-at-your-pace",
    title: "Learn At Your Pace",
    description: "Complete courses on your schedule with lifetime access to materials and updates.",
    icon: "⏱️",
  },
  {
    id: "expert-instructors",
    title: "Expert Instructors",
    description: "Learn from industry professionals and experienced developers in their field.",
    icon: "👥",
  },
  {
    id: "hands-on-projects",
    title: "Hands-On Projects",
    description: "Build real-world projects that you can showcase in your portfolio.",
    icon: "🔨",
  },
  {
    id: "career-support",
    title: "Career Support",
    description: "Get guidance on career paths, resume building, and job placement.",
    icon: "💼",
  },
];

export const heroSectionData: HeroSection = {
  title: "Master Tech Skills Your Way",
  subtitle: "Join thousands of learners building in-demand tech skills",
  description: "Learn from industry experts with hands-on courses, real-world projects, and personalized guidance. Start your journey to a better career today.",
  ctaText: "Explore Courses",
  ctaLink: "/courses",
};