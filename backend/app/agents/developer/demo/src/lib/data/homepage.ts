export interface CourseCategory {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  link: string;
}

export interface HighlightedSection {
  id: string;
  title: string;
  description: string;
  icon: string;
}

export const courseCategories: CourseCategory[] = [
  {
    id: "web-development",
    title: "Web Development",
    description: "Learn to build beautiful, responsive websites and web applications using modern technologies like React, Vue, and Node.js.",
    imageUrl: "/images/categories/web-development.jpg",
    link: "/categories/web-development",
  },
  {
    id: "mobile-apps",
    title: "Mobile Applications",
    description: "Create stunning mobile apps for iOS and Android using frameworks like React Native, Flutter, and native development.",
    imageUrl: "/images/categories/mobile-apps.jpg",
    link: "/categories/mobile-apps",
  },
  {
    id: "data-science",
    title: "Data Science",
    description: "Unlock the power of data with machine learning, statistics, and visualization tools to make data-driven decisions.",
    imageUrl: "/images/categories/data-science.jpg",
    link: "/categories/data-science",
  },
  {
    id: "design",
    title: "UI/UX Design",
    description: "Master the art of user experience and interface design, creating intuitive and beautiful digital products.",
    imageUrl: "/images/categories/design.jpg",
    link: "/categories/design",
  },
  {
    id: "cloud-devops",
    title: "Cloud & DevOps",
    description: "Learn cloud infrastructure, automation, and deployment strategies with AWS, Docker, and Kubernetes.",
    imageUrl: "/images/categories/cloud-devops.jpg",
    link: "/categories/cloud-devops",
  },
  {
    id: "cybersecurity",
    title: "Cybersecurity",
    description: "Protect digital assets and build secure applications with modern security practices and tools.",
    imageUrl: "/images/categories/cybersecurity.jpg",
    link: "/categories/cybersecurity",
  },
];

export const highlightedSections: HighlightedSection[] = [
  {
    id: "learn-at-your-pace",
    title: "Learn at Your Own Pace",
    description: "Access courses anytime, anywhere. Our flexible learning platform adapts to your schedule and learning style.",
    icon: "clock",
  },
  {
    id: "expert-instructors",
    title: "Expert Instructors",
    description: "Learn from industry professionals and experienced developers who are passionate about sharing their knowledge.",
    icon: "users",
  },
  {
    id: "hands-on-projects",
    title: "Hands-on Projects",
    description: "Apply your skills with real-world projects and build a portfolio that showcases your abilities to employers.",
    icon: "laptop",
  },
  {
    id: "career-support",
    title: "Career Support",
    description: "Get guidance on career paths, resume building, and interview preparation to advance your tech career.",
    icon: "briefcase",
  },
];
